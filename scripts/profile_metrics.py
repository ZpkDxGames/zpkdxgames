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
    "dark": dict(bg="#0d111c", panel="#151c2e", border="#2b3650", text="#f1f5ff",
                 muted="#a5b2cc", accent="#68e1f4", green="#6be5bb", blue="#b2a0ff", amber="#ffc780"),
    "light": dict(bg="#f6f8ff", panel="#ffffff", border="#d6ddef", text="#18233e",
                  muted="#53637e", accent="#08788e", green="#12785b", blue="#7051c1", amber="#966016"),
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
  <rect class="frame" x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="18"/>
  <path d="M24 1H{min(110, width-24)}" stroke="{THEMES[theme]['accent']}" stroke-width="2" opacity=".8"/>
  {body}
</svg>
'''
    # Concrete paint values also work in SVG thumbnailers without CSS-variable support.
    for key, value in THEMES[theme].items():
        document = document.replace(f"var(--{key})", value)
    return "\n".join(line.rstrip() for line in document.splitlines()) + "\n"


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
    """An editorial cover with a decorative animated circuit core."""
    width, height = (600, 690) if mobile else (1000, 430)
    x, cx, cy = (32, 300, 488) if mobile else (44, 797, 220)
    body = showcase_style()
    body += '<defs><radialGradient id="halo"><stop stop-color="var(--blue)" stop-opacity=".2"/><stop offset="1" stop-color="var(--blue)" stop-opacity="0"/></radialGradient></defs>'
    body += f'<circle cx="{cx}" cy="{cy}" r="195" fill="url(#halo)"/>'
    body += f'<rect x="{18 if mobile else 602}" y="{335 if mobile else 66}" width="{564 if mobile else 380}" height="300" rx="16" fill="url(#grid)"/>'
    body += text(x, 39, 'ZPKDXGAMES / DEVELOPER PROFILE', 12, 'accent', 650, 'letter-spacing="1.8"')
    body += text(x-3, 126, 'Tonim.', 84, weight=800, extra='letter-spacing="-4"')
    body += text(x, 182, 'Engineering systems.', 36, weight=700, extra='letter-spacing="-1.4"')
    body += text(x, 228, 'Crafting experiences.', 36, 'blue', 700, 'letter-spacing="-1.4"')
    body += text(x, 267, 'Minecraft plugins. Web interfaces. Useful tools.', 17, 'muted')
    for i, (label, color) in enumerate([('JAVA / PAPER', 'accent'), ('WEB / UI', 'blue'), ('AUTOMATION', 'green')]):
        bx = x + i*166
        body += rect(bx, 296, 154, 31, radius=7, extra='stroke="var(--border)"')
        body += text(bx+77, 316, label, 11, color, 600, 'text-anchor="middle" letter-spacing="1"')
    body += f'<g transform="translate({cx} {cy})">'
    body += '<circle r="121" fill="none" stroke="var(--border)"/><circle r="101" fill="none" stroke="var(--border)" stroke-dasharray="2 9"/>'
    body += '<g class="showcase-orbit"><circle r="121" fill="none" stroke="var(--blue)" stroke-width="2" stroke-dasharray="95 665"/><circle cx="121" r="4" fill="var(--accent)"/></g>'
    body += '<g class="showcase-float"><path d="M0-76L66-38V38L0 76L-66 38V-38Z" fill="var(--panel)" stroke="var(--blue)" stroke-width="2"/>'
    body += '<path d="M0-58L50-29V29L0 58L-50 29V-29Z" fill="none" stroke="var(--border)"/>'
    body += '<path d="M-25 22L-45 0L-25-22M25-22L45 0L25 22M10-28L-10 28" fill="none" stroke="var(--accent)" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></g></g>'
    for dx, dy, label, color in [(-125,-110,'BUILD','accent'),(70,-83,'CRAFT','blue'),(-126,95,'SHIP','green')]:
        px, py = cx+dx, cy+dy
        body += f'<path d="M{px+36} {py+12}L{cx} {cy}" fill="none" stroke="var(--border)"/>'
        body += f'<path class="showcase-trace" d="M{px+36} {py+12}L{cx} {cy}" fill="none" stroke="var(--{color})" stroke-opacity=".5"/>'
        body += rect(px,py,76,25,radius=6,extra='stroke="var(--border)"')
        body += text(px+38,py+17,label,10,color,650,'text-anchor="middle" letter-spacing="1.4"')
    fy = height-35
    body += f'<path d="M{x} {fy-23}H{width-x}" stroke="var(--border)"/>'
    body += text(x,fy,'01 / IDEAS INTO INTERFACES',10,'muted',600,'letter-spacing="1.5"')
    body += text(width-x,fy,'THE PLEXON ECOSYSTEM',10,'blue',600,'text-anchor="end" letter-spacing="1.2"')
    return svg(theme,width,height,'Tonim / ZpkDxGames — engineering systems, crafting experiences',
               'Minecraft plugins, web interfaces, and automation. Animated circuit artwork is decorative, not live telemetry.',body)


def spotlight(theme, kind):
    """Miniature technical illustrations; actual capabilities live in README text."""
    names = {'panel':('01','OPERATIONS','accent'), 'tools':('02','PROGRESSION','green'),
             'quests':('03','PLAYER JOURNEYS','blue'), 'crates':('04','REWARD DESIGN','amber')}
    number,label,color = names[kind]
    body = showcase_style()
    body += '<rect x="16" y="16" width="428" height="168" rx="10" fill="url(#grid)"/>'
    body += text(24,34,number+' / '+label,11,color,650,'letter-spacing="1.6"')
    if kind == 'panel':
        body += rect(97,54,266,117,radius=10,extra='stroke="var(--border)"')
        body += '<path d="M97 76H363M155 77V170" stroke="var(--border)"/>'
        for x in (109,119,129):
            body += f'<circle cx="{x}" cy="65" r="2" fill="var(--muted)"/>'
        for y in (91,108,125,142):
            body += f'<path d="M109 {y}H141" stroke="var(--border)" stroke-width="4"/>'
        for i in range(3):
            body += rect(168+i*61,87,51,24,'bg',5)
            body += f'<path d="M{178+i*61} 99h20" stroke="var(--{color})" stroke-width="3"/>'
        body += '<path d="M168 149L187 144L202 149L219 127L237 135L256 119L272 138L290 127L307 133L344 117" fill="none" stroke="var(--accent)" stroke-width="2.5" class="draw"/>'
    elif kind == 'tools':
        for i in range(4):
            x=108+i*71; y=139-i*21
            body += rect(x,y,49,160-y,'panel',5,extra='stroke="var(--border)"')
        body += '<path d="M93 145L165 124L236 103L307 82L353 67" fill="none" stroke="var(--green)" stroke-width="2" class="draw"/>'
        for x,y in [(93,145),(165,124),(236,103),(307,82)]:
            body += f'<circle cx="{x}" cy="{y}" r="5" fill="var(--bg)" stroke="var(--green)" stroke-width="2"/>'
        body += '<g class="showcase-float"><path d="M205 119L239 78" stroke="var(--green)" stroke-width="9"/><path d="M209 65L239 58L266 81L264 100L248 78L222 74L211 80Z" fill="var(--panel)" stroke="var(--green)" stroke-width="2"/></g>'
    elif kind == 'quests':
        body += '<path d="M102 112H358" stroke="var(--border)" stroke-width="2"/><path class="showcase-trace" d="M102 112H358" stroke="var(--blue)" stroke-width="2"/>'
        for i in range(3):
            x=103+i*87
            body += rect(x,67, 70,91,radius=9,extra='stroke="var(--border)"')
            body += f'<circle cx="{x+35}" cy="94" r="12" fill="var(--bg)" stroke="var(--blue)"/>'
            body += f'<path d="M{x+29} 94l4 4 8-9" fill="none" stroke="var(--green)" stroke-width="2"/>'
            body += f'<path d="M{x+16} 123h38M{x+16} 134h25" stroke="var(--muted)" stroke-opacity=".5" stroke-width="3"/>'
    else:
        body += '<g class="showcase-float"><path d="M230 54L282 80V132L230 158L178 132V80Z" fill="var(--panel)" stroke="var(--amber)" stroke-width="2"/><path d="M178 80L230 107L282 80M230 107V158M204 67L256 94V145" fill="none" stroke="var(--amber)" stroke-width="2"/><path d="M230 54L282 80L230 107L178 80Z" fill="var(--amber)" opacity=".16"/></g>'
        for x,y in [(144,92),(314,119),(301,67),(165,146)]:
            body += f'<path class="showcase-glow" d="M{x-5} {y}h10M{x} {y-5}v10" stroke="var(--amber)" stroke-width="2"/>'
        body += '<path class="showcase-trace" d="M89 166H153L179 140M281 140L308 166H371" fill="none" stroke="var(--amber)" stroke-opacity=".5"/>'
    return svg(theme,460,200,'Plexon '+label.lower()+' illustration',
               'Conceptual project illustration, not a screenshot or measured data.',body)


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
        body += rect(x, 96, 222, 86, radius=10, extra='stroke="var(--border)"')
        body += rect(x + 180, 111, 22, 2, ["blue", "accent", "green", "amber"][i], 1)
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
    body = rect(16, 16, 482, 385, radius=12, extra='stroke="var(--border)"')
    body += rect(514, 16, 470, 385, radius=12, extra='stroke="var(--border)"')
    body += text(32, 36, "WHERE THE WORK HAPPENS", 13, "accent", 650, 'letter-spacing="1.8"')
    body += text(32, 72, "Project momentum", 26, weight=700)
    body += text(32, 99, "Most active public projects · last 90 days", 14, "muted")
    body += text(545, 72, "Source language mix", 26, weight=700)
    body += text(545, 99, "Code bytes · public default branches", 14, "muted")
    projects = sorted((p for p in data["projects"] if p["commits"]), key=lambda p: (-p["commits"], p["name"]))[:6]
    maximum = max((p["commits"] for p in projects), default=1)
    for i, project in enumerate(projects):
        y = 137 + i * 43
        body += text(32, y, project["name"], 14, weight=550)
        body += text(475, y, project["commits"], 14, "accent", 650, 'text-anchor="end"')
        body += rect(32, y + 9, 442, 7, "bg", radius=3)
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
    document = re.sub(r'  <path d="M24 1H[^\n]+\n', '', document)
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


def architecture(theme, mobile=False):
    width, height = (600, 604) if mobile else (1000, 314)
    body = showcase_style()
    body += text(28, 37, 'ONE ECOSYSTEM. FOCUSED MODULES.', 13, 'accent', 650, 'letter-spacing="1.6"')
    body += text(28, 70, 'Designed to work together.', 26, weight=700)
    groups = [('01 / PROGRESSION', 'Tools · Quests · Ranks', 'Player goals & long-term growth', 'accent'),
              ('02 / REWARDS', 'Keys · Crates · DailyRewards', 'Earn, unlock & discover', 'green'),
              ('03 / COMMUNITY', 'Chats · Shops', 'Connection & player exchange', 'blue')]
    for i, (title, projects, subtitle, color) in enumerate(groups):
        x, y, w = (28, 94+i*121, 544) if mobile else (28+i*320, 98, 304)
        body += rect(x,y,w,105,radius=10,extra='stroke="var(--border)"')
        body += f'<path d="M{x+1} {y+20}v64" stroke="var(--{color})" stroke-width="2"/>'
        body += text(x+18,y+25,title,11,color,650,'letter-spacing="1.1"')
        body += text(x+18,y+55,projects,17,weight=650)
        body += text(x+18,y+81,subtitle,13,'muted')
    y=477 if mobile else 230
    body += rect(28,y,width-56,59,radius=10,extra='stroke="var(--border)"')
    body += text(46,y+24,'PLEXONCORE / SHARED FOUNDATION',11,'blue',650,'letter-spacing="1"')
    body += text(46,y+45,'Configuration · UI helpers · storage · diagnostics',14,'muted')
    if mobile:
        body += text(28,575,'A conceptual map. Integration varies by module.',12,'muted')
    return svg(theme,width,height,'Plexon ecosystem overview',
               'Progression: Tools, Quests, Ranks. Rewards: Keys, Crates, DailyRewards. Community: Chats and Shops. PlexonCore offers shared infrastructure; adoption varies by module.',body)


def mobile_chart(data, theme, kind):
    """Dedicated narrow-screen compositions; metrics retain the desktop meaning."""
    width=600
    body=text(28,37,'PUBLIC PROJECTS / '+data['as_of'],12,'accent',650,'letter-spacing="1.3"')
    if kind == 'activity':
        height=630
        body+=text(28,77,'The last 90 days',30,weight=700)
        values=[d['commits'] for d in data['daily']]
        stats=[(len(data['projects']),'public projects'),(sum(values),'project commits'),
               (sum(p['commits']>0 for p in data['projects']),'active projects'),(len(data['releases']),'published releases')]
        for i,(value,label) in enumerate(stats):
            x,y=28+(i%2)*280,104+(i//2)*98
            body+=rect(x,y,264,82,radius=10,extra='stroke="var(--border)"')
            body+=text(x+18,y+36,f'{value:,}',30,'accent' if i==1 else 'text',700)
            body+=text(x+18,y+62,label,15,'muted')
        body+=text(28,331,'Commits per day',17,weight=600)
        maximum=max(4,math.ceil(max(values,default=0)/4)*4)
        x0,y0,w,h=61,360,503,170
        for i in range(5):
            y=y0+h*(1-i/4)
            body+=f'<path d="M{x0} {y}h{w}" stroke="var(--border)" stroke-dasharray="3 6"/>'
            body+=text(49,y+4,int(maximum*i/4),12,'muted',extra='text-anchor="end"')
        points=[(x0+i*w/(len(values)-1),y0+h*(1-v/maximum)) for i,v in enumerate(values)]
        line='M'+' L'.join(f'{x:.2f} {y:.2f}' for x,y in points)
        body+=f'<path d="{line} L564 530L61 530Z" fill="url(#area)"/>'
        body+=f'<path class="fade" d="{line}" fill="none" stroke="url(#line)" stroke-width="2.5" stroke-linejoin="round"/>'
        body+=text(61,553,data['start'],12,'muted')+text(564,553,data['as_of'],12,'muted',extra='text-anchor="end"')
        body+=text(28,591,'All authors except bots · deduplicated across branches',13,'muted')
        body+=text(28,612,'UTC · profile repository excluded',13,'muted')
    elif kind == 'ecosystem':
        height=820
        body+=text(28,77,'Project momentum',30,weight=700)
        body+=text(28,105,'Project commits · last 90 days',15,'muted')
        projects=sorted((p for p in data['projects'] if p['commits']),key=lambda p:(-p['commits'],p['name']))[:6]
        maximum=max((p['commits'] for p in projects),default=1)
        for i,p in enumerate(projects):
            y=146+i*44
            body+=text(28,y,p['name'],16,weight=550)+text(572,y,p['commits'],16,'accent',650,'text-anchor="end"')
            body+=rect(28,y+10,544,7,radius=3)
            body+=rect(28,y+10,round(544*p['commits']/maximum,2),7,'accent',3,'class="grow"')
        if not projects:
            body+=text(28,153,'No qualifying commits in this window.',16,'muted')
        body+='<path d="M28 427H572" stroke="var(--border)"/>'
        body+=text(28,471,'Source language mix',27,weight=700)
        body+=text(28,499,'Code bytes · public default branches',15,'muted')
        languages=list(data['languages'].items())
        if len(languages)>5:
            languages=languages[:4]+[('Other',sum(v for _,v in languages[4:]))]
        total=sum(v for _,v in languages)
        colors=['accent','green','blue','amber','muted']
        offset=0
        for i,(language,amount) in enumerate(languages):
            fraction=amount/total if total else 0
            body+=rect(28+offset*544,526,fraction*544,18,colors[i],0)
            offset+=fraction
            y=580+i*36
            body+=f'<circle cx="35" cy="{y-5}" r="5" fill="var(--{colors[i]})"/>'
            body+=text(52,y,language,16,weight=550)
            percentage=f'{fraction*100:.1f}%' if fraction>=.001 else '<0.1%'
            body+=text(572,y,percentage,16,'muted',extra='text-anchor="end"')
        body+=text(28,786,'Source volume, not a skill rating. Forks excluded.',13,'muted')
    elif kind == 'heatmap':
        height=554
        rows=data['daily']; first=date.fromisoformat(rows[0]['date'])
        monday=first-timedelta(days=first.weekday())
        columns=(date.fromisoformat(rows[-1]['date'])-monday).days//7+1
        body+=text(28,77,'Build rhythm',30,weight=700)
        body+=text(28,105,'90 days of project activity · UTC',15,'muted')
        for i,label in enumerate(['M','T','W','T','F','S','S']):
            body+=text(28,151+i*32,label,12,'muted')
        for row in rows:
            day=date.fromisoformat(row['date']); col=(day-monday).days//7
            v=row['commits']; level=0 if v==0 else 1 if v<=2 else 2 if v<=5 else 3 if v<=10 else 4
            x,y=56+col*36,134+day.weekday()*32
            body+=rect(x,y,27,25,radius=4,extra='stroke="var(--border)"')
            if level:
                body+=rect(x,y,27,25,'green',4,f'fill-opacity="{[0,.25,.48,.72,1][level]}" class="fade"')
        body+=text(56,380,f"{sum(r['commits']>0 for r in rows)} active days",21,'green',700)
        body+=text(322,380,f"{max(r['commits'] for r in rows)} peak / day",21,'accent',700)
        for i,label in enumerate(['0','1–2','3–5','6–10','11+']):
            x=56+i*100
            body+=rect(x,417,38,17,radius=4,extra='stroke="var(--border)"')
            if i:
                body+=rect(x,417,38,17,'green',4,f'fill-opacity="{[0,.25,.48,.72,1][i]}"')
            body+=text(x+19,458,label,13,'muted',extra='text-anchor="middle"')
        body+=text(28,506,'Commits per day · fixed color bins',13,'muted')
        body+=text(28,531,'Project activity, not a personal contribution calendar.',13,'muted')
    return svg(theme,width,height,'Public project '+kind+' — mobile',
               f"90-day public project snapshot as of {data['as_of']}. All authors except bots. Full values in data/profile.json.",body)


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
        for name in ('activity', 'ecosystem', 'heatmap'):
            outputs[f"assets/profile/{name}-mobile-{theme}.svg"] = mobile_chart(data, theme, name)
        outputs[f"assets/profile/architecture-{theme}.svg"] = architecture(theme)
        outputs[f"assets/profile/architecture-mobile-{theme}.svg"] = architecture(theme, mobile=True)
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
