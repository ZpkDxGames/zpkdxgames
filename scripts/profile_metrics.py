#!/usr/bin/env python3
"""Render GitHub profile SVGs from public repository data, using only the stdlib."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
import json
import math
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DAYS = 90
THEMES = {
    "dark": dict(bg="#0b111b", panel="#111c2b", border="#22354b", text="#edf5ff",
                 muted="#9fb2c9", accent="#40d6ee", green="#66e2bb", blue="#9db7ff", amber="#ffd08c"),
    "light": dict(bg="#f5f9ff", panel="#ffffff", border="#d6e3f2", text="#183149",
                  muted="#516980", accent="#087e98", green="#168361", blue="#526eb5", amber="#a16a14"),
}


class GitHub:
    def __init__(self):
        self.headers = {"Accept": "application/vnd.github+json",
                        "User-Agent": "ZpkDxGames-profile-metrics",
                        "X-GitHub-Api-Version": "2022-11-28"}
        if token := os.environ.get("GH_TOKEN"):
            self.headers["Authorization"] = f"Bearer {token}"

    def get(self, path, **params):
        url = "https://api.github.com" + path
        if params:
            url += "?" + urlencode(params)
        for attempt in range(3):
            try:
                with urlopen(Request(url, headers=self.headers), timeout=30) as response:
                    return json.load(response)
            except HTTPError as error:
                if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise RuntimeError(f"GitHub returned HTTP {error.code} for {path}") from None
            except (URLError, TimeoutError):
                if attempt == 2:
                    raise RuntimeError(f"GitHub request failed for {path}") from None
            time.sleep(2 ** attempt)
        raise RuntimeError(f"GitHub request failed for {path}")

    def items(self, path, **params):
        # Fail instead of silently publishing truncated metrics.
        for page in range(1, 101):
            batch = self.get(path, per_page=100, page=page, **params)
            if not isinstance(batch, list):
                raise ValueError(f"Expected a GitHub list for {path}")
            yield from batch
            if len(batch) < 100:
                return
        raise RuntimeError(f"Pagination limit exceeded for {path}")


def eligible(repo, owner):
    """A public profile must not reveal private repos, forks, or other owners."""
    return (repo.get("private") is False and repo.get("visibility", "public") == "public"
            and repo.get("fork") is False and not repo.get("archived")
            and not repo.get("disabled")
            and repo.get("owner", {}).get("login", "").casefold() == owner.casefold()
            and repo.get("name", "").casefold() != owner.casefold())


def commit_day(commit):
    author = commit.get("author") or {}
    raw = commit.get("commit") or {}
    author_name = (raw.get("author") or {}).get("name", "")
    if (author.get("type") == "Bot" or author.get("login", "").endswith("[bot]")
            or author_name.endswith("[bot]")):
        return None
    timestamp = (raw.get("committer") or {}).get("date")
    if not timestamp:
        raise ValueError("Commit is missing its committer timestamp")
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(timezone.utc).date()


def release_version(release):
    tag = release.get("tag_name", "")
    if re.fullmatch(r"v?\d+(?:\.\d+)+(?:[-+][\w.-]+)?", tag):
        return tag.removeprefix("v")
    for asset in release.get("assets", []):
        match = re.search(r"[-.](\d+\.\d+(?:\.\d+)?(?:-[\w.-]+)?)\.jar$", asset.get("name", ""))
        if match:
            return match.group(1)
    return tag or "untagged"


def collect(owner, today, api=None):
    api = api or GitHub()
    start = today - timedelta(days=DAYS - 1)
    all_repos = list(api.items(f"/users/{owner}/repos", type="owner", sort="full_name"))
    repos = sorted((r for r in all_repos if eligible(r, owner)), key=lambda r: r["name"].casefold())
    projects, releases = [], []
    daily, languages = Counter(), Counter()
    for repo in repos:
        path = f"/repos/{owner}/{repo['name']}"
        language_bytes = api.get(path + "/languages")
        languages.update(language_bytes)
        seen, project_days = set(), Counter()
        # Pushed-at is only a request-saving gate, never the metric itself.
        if (repo.get("size", 0) > 0 and repo.get("pushed_at")
                and repo["pushed_at"][:10] >= start.isoformat()):
            for branch in api.items(path + "/branches"):
                # Snapshot immutable tips so a branch move cannot mix histories.
                for commit in api.items(path + "/commits", sha=branch["commit"]["sha"],
                                        since=start.isoformat() + "T00:00:00Z",
                                        until=today.isoformat() + "T23:59:59Z"):
                    if commit["sha"] in seen:
                        continue
                    seen.add(commit["sha"])
                    day = commit_day(commit)
                    if day is not None and start <= day <= today:
                        project_days[day.isoformat()] += 1
        daily.update(project_days)
        projects.append({"name": repo["name"], "url": repo["html_url"],
                         "commits": sum(project_days.values()), "languages": language_bytes})
        for release in api.items(path + "/releases"):
            published = release.get("published_at")
            if release.get("draft") or not published:
                continue
            published_day = datetime.fromisoformat(published.replace("Z", "+00:00")).astimezone(timezone.utc).date()
            if start <= published_day <= today:
                releases.append({"project": repo["name"], "version": release_version(release),
                                 "tag": release["tag_name"], "published_at": published,
                                 "prerelease": bool(release.get("prerelease")), "url": release["html_url"]})
    releases.sort(key=lambda r: (r["published_at"], r["project"], r["tag"]), reverse=True)
    return {"schema": 1, "owner": owner, "as_of": today.isoformat(), "days": DAYS,
            "start": start.isoformat(), "scope": "Public, owned, non-fork, non-archived projects; profile excluded",
            "commit_scope": "All authors except bots; current branch histories deduplicated per repository; UTC committer date",
            "language_scope": "GitHub Linguist byte counts on default branches; not a measure of proficiency",
            "projects": projects,
            "daily": [{"date": (start + timedelta(days=i)).isoformat(),
                       "commits": daily[(start + timedelta(days=i)).isoformat()]} for i in range(DAYS)],
            "languages": dict(sorted(languages.items(), key=lambda x: (-x[1], x[0]))),
            "releases": releases}


def text(x, y, value, size=16, fill="text", weight=400, extra=""):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'fill="var(--{fill})" {extra}>{escape(str(value))}</text>')


def rect(x, y, w, h, fill="panel", radius=16, extra=""):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
            f'fill="var(--{fill})" {extra}/>')


def svg(theme, width, height, title, description, body, draw_length=1000):
    document = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{escape(description)}</desc>
  <defs>
    <linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop stop-color="{THEMES[theme]['accent']}" stop-opacity=".32"/><stop offset="1" stop-color="{THEMES[theme]['accent']}" stop-opacity=".01"/></linearGradient>
    <linearGradient id="line"><stop stop-color="{THEMES[theme]['accent']}"/><stop offset="1" stop-color="{THEMES[theme]['green']}"/></linearGradient>
    <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="{THEMES[theme]['border']}" stroke-opacity=".35"/></pattern>
  </defs>
  <style>
    svg {{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
    .frame {{fill:var(--bg);stroke:var(--border)}}
    .draw {{stroke-dasharray:{draw_length:.2f};stroke-dashoffset:0;animation:draw 1.8s ease-out both}}
    .rise {{animation:rise .8s ease-out both}}
    .fade {{animation:fade .8s ease-out both}}
    .grow {{transform-box:fill-box;transform-origin:left center;animation:grow 1.3s ease-out both}}
    .flow {{stroke-dasharray:5 13;animation:flow 12s linear infinite}}
    .pulse {{animation:pulse 4s ease-in-out infinite;transform-box:fill-box;transform-origin:center}}
    @keyframes draw {{from{{stroke-dashoffset:{draw_length:.2f}}}to{{stroke-dashoffset:0}}}}
    @keyframes rise {{from{{opacity:0;transform:translateY(7px)}}to{{opacity:1;transform:translateY(0)}}}}
    @keyframes fade {{from{{opacity:0}}to{{opacity:1}}}}
    @keyframes grow {{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
    @keyframes flow {{to{{stroke-dashoffset:-108}}}}
    @keyframes pulse {{50%{{opacity:.45;transform:scale(.9)}}}}
    @media (prefers-reduced-motion:reduce) {{.draw,.rise,.fade,.grow,.flow,.pulse{{animation:none!important}}}}
  </style>
  <rect class="frame" x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="22"/>
  {body}
</svg>
'''
    # Concrete paint values also work in SVG thumbnailers without CSS-variable support.
    for key, value in THEMES[theme].items():
        document = document.replace(f"var(--{key})", value)
    return "\n".join(line.rstrip() for line in document.splitlines()) + "\n"


def cube(x, y, size=70):
    """A decorative isometric voxel, not a screenshot or a telemetry value."""
    s = size
    return (f'<g transform="translate({x} {y})"><g class="showcase-float">'
            f'<path d="M0 {-s}L{s} {-s/2}V{s/2}L0 {s}L{-s} {s/2}V{-s/2}Z" '
            'fill="var(--panel)" stroke="var(--accent)" stroke-width="2"/>'
            f'<path d="M0 {-s}L{s} {-s/2}L0 0L{-s} {-s/2}Z" fill="url(#line)" opacity=".24"/>'
            f'<path d="M0 0L{s} {-s/2}V{s/2}L0 {s}Z" fill="var(--blue)" opacity=".13"/>'
            f'<path d="M{-s} {-s/2}L0 0L{s} {-s/2}M0 0V{s}" '
            'fill="none" stroke="var(--accent)" stroke-width="2"/>'
            f'<path d="M{-s*.57} {-s*.71}L{s*.44} {-s*.2}V{s*.7}" '
            'fill="none" stroke="var(--green)" stroke-width="2.5"/>'
            '</g></g>')


def showcase_style():
    return '''
    <style>
      .showcase-float {animation:showcase-float 7s ease-in-out infinite}
      .showcase-orbit {animation:showcase-orbit 36s linear infinite}
      .showcase-trace {stroke-dasharray:36 90;animation:showcase-trace 12s linear infinite}
      .showcase-glow {opacity:.8;animation:showcase-glow 6s ease-in-out infinite}
      @keyframes showcase-float {50%{transform:translateY(-7px)}}
      @keyframes showcase-orbit {to{transform:rotate(360deg)}}
      @keyframes showcase-trace {to{stroke-dashoffset:-252}}
      @keyframes showcase-glow {50%{opacity:.35}}
      @media (prefers-reduced-motion:reduce) {
        .showcase-float,.showcase-orbit,.showcase-trace,.showcase-glow {animation:none!important}
      }
    </style>
    '''


def workspace_header(theme, mobile=False):
    """Theme-aware portfolio cover; the mobile composition keeps text readable."""
    width, height = (600, 644) if mobile else (1000, 460)
    x = 40 if mobile else 50
    body = showcase_style()
    body += '''
    <defs>
      <radialGradient id="halo">
        <stop stop-color="var(--accent)" stop-opacity=".2"/>
        <stop offset="1" stop-color="var(--accent)" stop-opacity="0"/>
      </radialGradient>
      <clipPath id="cover-clip"><rect width="100%" height="100%" rx="22"/></clipPath>
    </defs>
    '''
    cx, cy = (300, 453) if mobile else (798, 229)
    body += f'<g clip-path="url(#cover-clip)"><circle cx="{cx}" cy="{cy}" r="270" fill="url(#halo)"/>'
    body += f'<rect x="{0 if mobile else 615}" y="60" width="600" height="{height}" fill="url(#grid)" opacity=".55"/></g>'
    body += text(x, 44, "ZPKDXGAMES", 15, "accent", 750, 'letter-spacing="3"')
    if not mobile:
        body += text(950, 44, "PUBLIC PROJECTS / PORTFOLIO", 11, "muted", 600,
                     'text-anchor="end" letter-spacing="1.4"')
    body += text(x - 3, 145, "TONIM", 86 if not mobile else 82, weight=800, extra='letter-spacing="-4"')
    body += text(x, 211, "Code with purpose.", 43 if not mobile else 37, weight=700, extra='letter-spacing="-1.6"')
    body += text(x, 264, "Worlds with character.", 43 if not mobile else 37, "accent", 700, 'letter-spacing="-1.6"')
    body += text(x + 1, 311, "Minecraft systems & web experiences.", 19, "muted")

    ring = 128 if mobile else 153
    body += f'<circle cx="{cx}" cy="{cy}" r="{ring}" fill="none" stroke="var(--border)"/>'
    body += f'<circle cx="{cx}" cy="{cy}" r="{ring-25}" fill="none" stroke="var(--border)" stroke-dasharray="2 10"/>'
    body += f'<g transform="translate({cx} {cy})"><g class="showcase-orbit">'
    body += f'<circle r="{ring}" fill="none" stroke="var(--accent)" stroke-width="2" stroke-dasharray="55 900"/>'
    body += f'<circle cx="{ring}" r="5" fill="var(--green)"/>'
    body += '</g></g>'
    body += cube(cx, cy, 73 if mobile else 84)
    for dx, dy, color in [(-120, -88, "green"), (122, 83, "blue"), (116, -100, "accent")]:
        body += f'<rect x="{cx+dx}" y="{cy+dy}" width="12" height="12" rx="3" fill="var(--panel)" stroke="var(--{color})"/>'
    if not mobile:
        body += '<path d="M620 355H671L700 326" fill="none" stroke="var(--border)" stroke-width="2"/>'
        body += '<path class="showcase-trace" d="M620 355H671L700 326" fill="none" stroke="var(--green)" stroke-width="2"/>'
        body += text(798, 415, "THE PLEXON ECOSYSTEM", 11, "muted", 600,
                     'text-anchor="middle" letter-spacing="1.8"')

    labels = [("JAVA + PAPER", 155, "accent"), ("WEB + UI", 121, "blue"), ("PLEXON", 110, "green")]
    bx, by = (90, 592) if mobile else (50, 365)
    for label, bw, color in labels:
        body += rect(bx, by, bw, 34, "panel", 9, 'stroke="var(--border)"')
        body += text(bx + bw / 2, by + 22, label, 11, color, 650,
                     'text-anchor="middle" letter-spacing="1"')
        bx += bw + 10
    if not mobile:
        body += text(51, 434, "CONFIGURABLE SYSTEMS. EXPRESSIVE INTERFACES.", 10, "muted", 550,
                     'letter-spacing="1.4"')
    return svg(theme, width, height, "Tonim / ZpkDxGames — public project showcase",
               "Code with purpose. Worlds with character. Minecraft systems and web experiences. "
               "An animated isometric voxel represents the Plexon ecosystem. Decorative artwork; no live status is implied.",
               body)


def spotlight(theme, kind):
    """Small editorial illustrations; README text supplies real project details."""
    names = {"panel": ("CONTROL", "accent"), "tools": ("PROGRESSION", "green"),
             "quests": ("DISCOVERY", "blue"), "crates": ("REWARDS", "amber")}
    label, color = names[kind]
    body = showcase_style()
    body += '<rect x="16" y="16" width="428" height="148" rx="16" fill="url(#grid)" opacity=".5"/>'
    body += text(24, 32, label, 10, color, 650, 'letter-spacing="2"')
    body += '<path d="M24 151H109M351 151H436" stroke="var(--border)"/>'
    body += f'<circle class="showcase-glow" cx="426" cy="28" r="3" fill="var(--{color})"/>'
    if kind == "panel":
        for y in (59, 92, 125):
            body += rect(160, y - 13, 140, 26, "panel", 7, 'stroke="var(--border)"')
            body += f'<circle cx="176" cy="{y}" r="3" fill="var(--accent)"/>'
            body += f'<path d="M190 {y}h60M270 {y}h14" stroke="var(--muted)" stroke-width="2" opacity=".65"/>'
        body += '<path d="M68 92H142M318 92H392M230 138V158" fill="none" stroke="var(--border)" stroke-width="2"/>'
        body += '<path class="showcase-trace" d="M68 92H142M318 92H392" fill="none" stroke="var(--accent)" stroke-width="2"/>'
        for cx in (58, 402):
            body += f'<rect x="{cx-9}" y="83" width="18" height="18" rx="5" fill="var(--panel)" stroke="var(--accent)"/>'
    elif kind == "tools":
        body += '<circle cx="230" cy="95" r="62" fill="none" stroke="var(--border)" stroke-width="3" stroke-dasharray="4 9"/>'
        body += '<g transform="translate(230 95)"><g class="showcase-orbit"><path d="M0-62A62 62 0 0 1 62 0" fill="none" stroke="var(--green)" stroke-width="3" stroke-linecap="round"/></g></g>'
        body += '<g class="showcase-float"><path d="M206 126L242 84" stroke="var(--green)" stroke-width="11" stroke-linecap="square"/>'
        body += '<path d="M211 67L242 62L267 85L265 110L251 84L228 77L213 82Z" fill="var(--panel)" stroke="var(--accent)" stroke-width="3" stroke-linejoin="round"/></g>'
        body += '<path d="M106 90h28m-14-14v28M326 105h18m-9-9v18" stroke="var(--green)" opacity=".6"/>'
    elif kind == "quests":
        body += '<g class="showcase-float">'
        body += rect(170, 43, 121, 103, "panel", 10, 'stroke="var(--blue)" stroke-width="2"')
        body += '<path d="M186 44V145" stroke="var(--border)" stroke-width="2"/>'
        for y in (66, 93, 120):
            body += f'<rect x="200" y="{y-6}" width="11" height="11" rx="3" fill="none" stroke="var(--blue)"/>'
            body += f'<path d="M222 {y}H273" stroke="var(--muted)" stroke-width="3" opacity=".7"/>'
        body += '<path class="showcase-glow" d="M201 64l4 4 9-10" fill="none" stroke="var(--green)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
        body += '</g><path d="M112 84h20m-10-10v20M326 118h18m-9-9v18" stroke="var(--blue)" opacity=".7"/>'
    else:
        body += '<g class="showcase-float">'
        body += '<path d="M230 44L288 73V128L230 158L172 128V73Z" fill="var(--panel)" stroke="var(--amber)" stroke-width="2"/>'
        body += '<path d="M172 73L230 103L288 73M230 103V158" fill="none" stroke="var(--amber)" stroke-width="2"/>'
        body += '<path d="M201 59L259 89V143M201 88L258 60" fill="none" stroke="var(--amber)" stroke-width="7" opacity=".6"/>'
        body += '<path d="M230 44L288 73L230 103L172 73Z" fill="var(--amber)" opacity=".13"/>'
        body += '</g><g class="showcase-glow">'
        for cx, cy, size in [(126, 66, 9), (327, 92, 11), (302, 48, 5), (140, 122, 5)]:
            body += f'<path d="M{cx-size} {cy}H{cx+size}M{cx} {cy-size}V{cy+size}" stroke="var(--amber)" stroke-width="2" stroke-linecap="round"/>'
        body += '</g>'
    return svg(theme, 460, 180, f"Plexon {label.lower()} illustration",
               "Decorative project artwork, not a product screenshot. Animation respects reduced-motion preferences.", body)


def activity(data, theme):
    values = [d["commits"] for d in data["daily"]]
    total = sum(values)
    active = sum(p["commits"] > 0 for p in data["projects"])
    body = text(32, 35, "PUBLIC PROJECT ACTIVITY", 13, "accent", 650, 'letter-spacing="1.8"')
    body += text(32, 71, "A look at the last 90 days", 28, weight=700)
    body += text(968, 35, "AS OF " + data["as_of"], 12, "muted", 500, 'text-anchor="end"')
    for i, (value, label) in enumerate([(len(data["projects"]), "public projects"), (total, "project commits"),
                                       (active, "active projects"), (len(data["releases"]), "published releases")]):
        x = 32 + i * 238
        body += rect(x, 96, 222, 86)
        body += text(x + 18, 136, f"{value:,}", 32, "accent" if i == 1 else "text", 700)
        body += text(x + 18, 160, label, 14, "muted")
    body += text(32, 215, "Commits per day", 16, weight=600)
    body += text(968, 215, "All current branches · deduplicated per project", 13, "muted", extra='text-anchor="end"')
    x0, y0, width, height = 70, 243, 880, 151
    maximum = max(4, math.ceil(max(values, default=0) / 4) * 4)
    for i in range(5):
        y = y0 + height * (1 - i / 4)
        body += f'<path d="M{x0} {y}h{width}" stroke="var(--border)" stroke-dasharray="3 6"/>'
        body += text(x0 - 13, y + 4, int(maximum * i / 4), 12, "muted", extra='text-anchor="end"')
    points = [(x0 + i * width / max(1, len(values) - 1), y0 + height * (1 - value / maximum)) for i, value in enumerate(values)]
    line = "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in points)
    if points:
        body += f'<path class="rise" d="{line} L{x0 + width} {y0 + height} L{x0} {y0 + height}Z" fill="url(#area)"/>'
        body += f'<path class="draw" d="{line}" fill="none" stroke="url(#line)" stroke-width="3" stroke-linejoin="round"/>'
        last_x, last_y = points[-1]
        body += f'<circle class="pulse" cx="{last_x:.2f}" cy="{last_y:.2f}" r="7" fill="none" stroke="var(--accent)" stroke-width="2"><title>Latest snapshot day: {values[-1]} commits</title></circle>'
        for (x, y), row in zip(points, data["daily"]):
            if row["commits"]:
                body += f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.5" fill="var(--accent)"><title>{row["date"]}: {row["commits"]} commits</title></circle>'
        for index in sorted({0, len(values) // 3, len(values) * 2 // 3, len(values) - 1}):
            label = date.fromisoformat(data["daily"][index]["date"]).strftime("%d %b")
            body += text(points[index][0], 419, label, 12, "muted", extra='text-anchor="middle"')
    body += text(32, 457, "Public owned projects · all authors except bots · UTC · profile repository excluded", 12, "muted")
    draw_length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:])) + 1
    return svg(theme, 1000, 480, "Public project activity over 90 days",
               f"{total} commits across {active} active projects; {len(data['releases'])} published releases. As of {data['as_of']}. This is project activity, not the personal contribution calendar.", body, draw_length)


def ecosystem(data, theme):
    body = text(32, 36, "WHERE THE WORK HAPPENS", 13, "accent", 650, 'letter-spacing="1.8"')
    body += text(32, 72, "Project momentum", 26, weight=700)
    body += text(32, 99, "Most active public projects · last 90 days", 14, "muted")
    body += text(545, 72, "Source language mix", 26, weight=700)
    body += text(545, 99, "Code bytes · public default branches", 14, "muted")
    body += '<path d="M510 46V391" stroke="var(--border)"/>'
    projects = sorted((p for p in data["projects"] if p["commits"]), key=lambda p: (-p["commits"], p["name"]))[:6]
    maximum = max((p["commits"] for p in projects), default=1)
    for i, project in enumerate(projects):
        y = 137 + i * 43
        body += text(32, y, project["name"], 14, weight=550)
        body += text(475, y, project["commits"], 14, "accent", 650, 'text-anchor="end"')
        body += rect(32, y + 9, 442, 7, radius=3)
        body += rect(32, y + 9, round(442 * project["commits"] / maximum, 2), 7, "accent", 3, f'class="grow" style="animation-delay:{i*.1:.1f}s"')
    if not projects:
        body += text(32, 160, "No qualifying commits in this window.", 15, "muted")
    languages = list(data["languages"].items())
    if len(languages) > 5:
        languages = languages[:4] + [("Other", sum(v for _, v in languages[4:]))]
    total = sum(v for _, v in languages)
    colors = ["accent", "green", "blue", "amber", "muted"]
    cx, cy, radius = 628, 229, 66
    circumference = 2 * math.pi * radius
    body += f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="var(--panel)" stroke-width="20"/>'
    offset = 0
    for i, (language, amount) in enumerate(languages):
        fraction = amount / total if total else 0
        length = circumference * fraction
        body += (f'<circle class="fade" cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="var(--{colors[i]})" '
                 f'stroke-width="20" stroke-dasharray="{length:.4f} {circumference:.4f}" stroke-dashoffset="{-offset:.4f}" '
                 f'transform="rotate(-90 {cx} {cy})"><title>{escape(language)}: {amount:,} bytes</title></circle>')
        offset += length
        y = 160 + i * 39
        body += f'<circle cx="734" cy="{y - 5}" r="4.5" fill="var(--{colors[i]})"/>'
        body += text(746, y, language, 14, weight=550)
        percentage = f"{fraction * 100:.1f}%" if fraction >= .001 else "<0.1%"
        body += text(968, y, percentage, 14, "muted", extra='text-anchor="end"')
    body += text(cx, cy - 3, str(len(data["languages"])), 34, weight=700, extra='text-anchor="middle"')
    body += text(cx, cy + 21, "languages", 13, "muted", extra='text-anchor="middle"')
    body += text(545, 350, f"{total / 1000:,.1f} kB of source", 15, "muted")
    body += text(545, 373, "Language share is not a skill rating.", 12, "muted")
    body += text(32, 418, "Forks, archived projects, private repositories, and profile automation are excluded.", 12, "muted")
    return svg(theme, 1000, 444, "Project momentum and source language mix",
               "Commit counts by public project and GitHub Linguist source bytes. Exact values are available in data/profile.json.", body)


def release_radar(data, theme):
    releases = data["releases"][:6]
    body = text(32, 36, "RELEASE RADAR", 13, "accent", 650, 'letter-spacing="1.8"')
    body += text(32, 72, "Recent published milestones", 26, weight=700)
    body += text(32, 100, "The latest six GitHub releases within the 90-day window", 14, "muted")
    if releases:
        body += f'<path d="M49 143V{151 + (len(releases) - 1) * 54}" stroke="var(--border)" stroke-width="2"/>'
    for i, release in enumerate(releases):
        y = 153 + i * 54
        color = "amber" if release["prerelease"] else "green"
        label = "PRE-RELEASE" if release["prerelease"] else "PUBLISHED"
        body += f'<circle cx="49" cy="{y - 4}" r="5" fill="var(--{color})"/>'
        body += text(70, y, release["project"], 17, weight=600)
        body += text(376, y, release["version"][:30], 16, "accent", 600)
        body += rect(601, y - 21, 145, 30, radius=15)
        body += text(673, y - 1, label, 11, color, 600, 'text-anchor="middle" letter-spacing=".8"')
        published = date.fromisoformat(release["published_at"][:10]).strftime("%d %b %Y")
        body += text(968, y, published, 14, "muted", extra='text-anchor="end"')
        if i < len(releases) - 1:
            body += f'<path d="M70 {y + 22}H968" stroke="var(--border)" stroke-opacity=".65"/>'
    if not releases:
        body += text(32, 170, "No published releases in this window.", 16, "muted")
    body += text(32, 480, "Sorted by publication time · source branches without a GitHub release are not counted", 12, "muted")
    return svg(theme, 1000, 502, "Recent GitHub releases",
               "; ".join(f"{r['project']} {r['version']} on {r['published_at'][:10]}" for r in releases) or "No releases in this period.", body)


TOOLKIT = {
    "java": ("Java", "Java"),
    "javascript": ("JavaScript", "JavaScript"),
    "html": ("HTML", "HTML"),
    "css": ("CSS", "CSS"),
    "python": ("Python", "Python"),
    "git": ("Git", "Git"),
    "github": ("GitHub", "Github"),
    "actions": ("Actions", "GithubActions"),
    "gradle": ("Gradle", "Gradle"),
    "maven": ("Maven", "Maven"),
    "vercel": ("Vercel", "Vercel"),
    "nextjs": ("Next.js", "NextJS"),
    "sqlite": ("SQLite", "SQLite"),
    "paper": ("Paper", None),
    "minimessage": ("MiniMessage", None),
}


def toolkit_icon(theme, key):
    """Labelled, gently floating technology icon; source logos are vendored."""
    label, source = TOOLKIT[key]
    if source:
        folder = ROOT / "assets/vendor/skill-icons"
        path = folder / f"{source}-{theme.title()}.svg"
        if not path.exists():
            path = folder / f"{source}.svg"
        root = ET.fromstring(path.read_text(encoding="utf-8"))
        root.set("x", "6")
        root.set("y", "8")
        root.set("width", "64")
        root.set("height", "64")
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        artwork = ET.tostring(root, encoding="unicode")
    else:
        artwork = rect(6, 8, 64, 64, "panel", 14, 'stroke="var(--border)"')
        if key == "paper":
            artwork += '<path d="M24 20H43L55 32V59H24Z" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round"/>'
            artwork += '<path d="M43 20V32H55M31 40H47M31 48H43" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round"/>'
        else:
            artwork += '<path d="M27 29L17 40L27 51M49 29L59 40L49 51M43 26L33 54" fill="none" stroke="var(--green)" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>'
    delay = -(sum(map(ord, key)) % 11) * .31
    body = f'''<style>
      .toolkit-float {{animation:toolkit-float 6s ease-in-out infinite;animation-delay:{delay:.2f}s}}
      @keyframes toolkit-float {{50%{{transform:translateY(-3px)}}}}
      @media (prefers-reduced-motion:reduce) {{.toolkit-float{{animation:none!important}}}}
    </style>
    <ellipse cx="38" cy="78" rx="22" ry="2" fill="var(--muted)" opacity=".13"/>
    <g class="toolkit-float">{artwork}</g>'''
    body += text(38, 96, label, 10.5 if len(label) > 10 else 11.5, "text", 550, 'text-anchor="middle"')
    title = "GitHub Actions" if key == "actions" else label
    document = svg(theme, 76, 104, title + " toolkit icon",
                   title + ". Decorative motion; no proficiency rating is implied.", body)
    # Standalone icons wrap naturally in README paragraphs, without a frame.
    document = re.sub(r'  <rect class="frame"[^>]*/>\n', '', document)
    return document


def heatmap(data, theme):
    """A 90-day project-commit calendar with Monday-first UTC weeks."""
    rows = data["daily"]
    first = date.fromisoformat(rows[0]["date"])
    monday = first - timedelta(days=first.weekday())
    last = date.fromisoformat(rows[-1]["date"])
    columns = (last - monday).days // 7 + 1
    by_date = {row["date"]: row["commits"] for row in rows}
    active_days = sum(row["commits"] > 0 for row in rows)
    peak = max((row["commits"] for row in rows), default=0)
    body = text(32, 36, "BUILD RHYTHM", 13, "accent", 650, 'letter-spacing="1.8"')
    body += text(32, 72, "Every day leaves a trace", 26, weight=700)
    body += text(968, 36, "AS OF " + data["as_of"], 12, "muted", 500, 'text-anchor="end"')
    body += text(32, 99, "90 days of public project commits · UTC", 14, "muted")
    x0, y0, pitch, cell = 82, 137, 37, 28
    for i, day_name in enumerate(["M", "T", "W", "T", "F", "S", "S"]):
        body += text(51, y0 + i * pitch + 19, day_name, 12, "muted")
    for column in range(columns):
        for weekday in range(7):
            day = monday + timedelta(days=column * 7 + weekday)
            if day.isoformat() not in by_date:
                continue
            value = by_date[day.isoformat()]
            level = 0 if value == 0 else 1 if value <= 2 else 2 if value <= 5 else 3 if value <= 10 else 4
            x, y = x0 + column * pitch, y0 + weekday * pitch
            body += rect(x, y, cell, cell, "panel", 5, 'stroke="var(--border)"')
            if level:
                opacity = [.0, .25, .48, .72, 1.0][level]
                body += (f'<rect class="fade" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="5" '
                         f'fill="var(--green)" fill-opacity="{opacity}" style="animation-delay:{column*.045:.3f}s">'
                         f'<title>{day.isoformat()}: {value} commits</title></rect>')
            else:
                body += f'<g><title>{day.isoformat()}: 0 commits</title></g>'
    body += text(x0, 418, first.strftime("%d %b"), 12, "muted")
    body += text(x0 + (columns - 1) * pitch + cell, 418, last.strftime("%d %b"), 12, "muted",
                 extra='text-anchor="end"')
    body += '<path d="M646 131V396" stroke="var(--border)"/>'
    body += text(681, 174, active_days, 42, "green", 700)
    body += text(681, 202, "active days in this window", 14, "muted")
    body += text(681, 267, peak, 42, "accent", 700)
    body += text(681, 295, "peak commits in one day", 14, "muted")
    body += text(681, 341, "COMMITS PER DAY", 10, "muted", 650, 'letter-spacing="1.2"')
    for i, label in enumerate(["0", "1–2", "3–5", "6–10", "11+"]):
        x = 681 + i * 56
        body += rect(x, 355, 36, 17, "panel", 4, 'stroke="var(--border)"')
        if i:
            body += rect(x, 355, 36, 17, "green", 4, f'fill-opacity="{[0,.25,.48,.72,1][i]}"')
        body += text(x + 18, 391, label, 11, "muted", extra='text-anchor="middle"')
    body += text(32, 457, "Project activity across current branches · all authors except bots · not a personal contribution calendar", 12, "muted")
    return svg(theme, 1000, 480, "90-day public project activity heatmap",
               f"{active_days} active days; peak {peak} project commits in one UTC day. "
               "Cells show real daily totals, with fixed bins of 0, 1–2, 3–5, 6–10, and 11 or more commits.", body)


def render(data, root=ROOT):
    if data.get("schema") != 1 or len(data.get("daily", [])) != DAYS:
        raise ValueError("Unexpected profile snapshot format")
    if sum(d["commits"] for d in data["daily"]) != sum(p["commits"] for p in data["projects"]):
        raise ValueError("Daily and project totals do not agree")
    outputs = {"data/profile.json": json.dumps(data, indent=2, ensure_ascii=False) + "\n"}
    for theme in THEMES:
        outputs[f"assets/profile/workspace-{theme}.svg"] = workspace_header(theme)
        outputs[f"assets/profile/workspace-mobile-{theme}.svg"] = workspace_header(theme, mobile=True)
        for kind in ("panel", "tools", "quests", "crates"):
            outputs[f"assets/profile/spotlight-{kind}-{theme}.svg"] = spotlight(theme, kind)
        for name, renderer in [("activity", activity), ("ecosystem", ecosystem), ("releases", release_radar)]:
            outputs[f"assets/profile/{name}-{theme}.svg"] = renderer(data, theme)
        outputs[f"assets/profile/heatmap-{theme}.svg"] = heatmap(data, theme)
        for key in TOOLKIT:
            outputs[f"assets/profile/toolkit-{key}-{theme}.svg"] = toolkit_icon(theme, key)
    # Generate and parse everything before replacing any last-known-good file.
    for name, contents in outputs.items():
        if name.endswith(".svg"):
            ET.fromstring(contents)
    for name, contents in outputs.items():
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(contents, encoding="utf-8")
        temporary.replace(destination)
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", default="ZpkDxGames")
    parser.add_argument("--snapshot", type=Path, help="Render a saved public snapshot without network access")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", args.owner):
        parser.error("Invalid GitHub username")
    if args.snapshot:
        data = json.loads(args.snapshot.read_text(encoding="utf-8"))
    else:
        data = collect(args.owner, datetime.now(timezone.utc).date())
    outputs = render(data)
    print(f"Rendered {len(outputs)} files for {data['owner']} as of {data['as_of']}.")


if __name__ == "__main__":
    main()
