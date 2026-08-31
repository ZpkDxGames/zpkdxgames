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
    .flow {{stroke-dasharray:5 13;animation:flow 12s linear infinite}}
    .pulse {{animation:pulse 4s ease-in-out infinite;transform-box:fill-box;transform-origin:center}}
    @keyframes draw {{from{{stroke-dashoffset:{draw_length:.2f}}}to{{stroke-dashoffset:0}}}}
    @keyframes rise {{from{{opacity:0;transform:translateY(7px)}}to{{opacity:1;transform:translateY(0)}}}}
    @keyframes fade {{from{{opacity:0}}to{{opacity:1}}}}
    @keyframes flow {{to{{stroke-dashoffset:-108}}}}
    @keyframes pulse {{50%{{opacity:.45;transform:scale(.9)}}}}
    @media (prefers-reduced-motion:reduce) {{.draw,.rise,.fade,.flow,.pulse{{animation:none!important}}}}
  </style>
  <rect class="frame" x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="22"/>
  {body}
</svg>
'''
    # Concrete paint values also work in SVG thumbnailers without CSS-variable support.
    for key, value in THEMES[theme].items():
        document = document.replace(f"var(--{key})", value)
    return document


def workspace_header(theme):
    """An animated profile illustration, not a live terminal or interactive UI."""
    typed_line = "building the Plexon ecosystem"
    type_width = len(typed_line) * 8.4
    body = '''
    <defs>
      <clipPath id="workspace-typing">
        <rect class="workspace-type-mask" x="74" y="274" width="__TYPE_WIDTH__" height="24"/>
      </clipPath>
    </defs>
    <style>
      .workspace-mono {font-family:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace}
      .workspace-edge {stroke-dasharray:110 2523.7;animation:workspace-border 14s linear infinite}
      .workspace-scene {opacity:0;animation:workspace-scene 18s linear infinite}
      .workspace-scene-0 {opacity:1}
      .workspace-scene-1 {animation-delay:-12s}
      .workspace-scene-2 {animation-delay:-6s}
      .workspace-type-mask {width:__TYPE_WIDTH__px;animation:workspace-type 6s steps(__CHARS__,end) infinite}
      .workspace-caret {transform:translateX(__TYPE_WIDTH__px);animation:workspace-caret 6s steps(__CHARS__,end) infinite,workspace-blink .8s step-end infinite}
      .workspace-timer {width:344px;animation:workspace-timer 6s linear infinite}
      .workspace-static-label {display:none}
      @keyframes workspace-border {to{stroke-dashoffset:-2633.7}}
      @keyframes workspace-scene {0%,28%{opacity:1}33.333%,94.667%{opacity:0}100%{opacity:1}}
      @keyframes workspace-type {0%,8%{width:0}40%,82%{width:__TYPE_WIDTH__px}94%,100%{width:0}}
      @keyframes workspace-caret {0%,8%{transform:translateX(0)}40%,82%{transform:translateX(__TYPE_WIDTH__px)}94%,100%{transform:translateX(0)}}
      @keyframes workspace-blink {50%{opacity:0}}
      @keyframes workspace-timer {from{width:0}to{width:344px}}
      @media (prefers-reduced-motion:reduce) {
        .workspace-edge,.workspace-scene,.workspace-type-mask,.workspace-caret,.workspace-timer {animation:none!important}
        .workspace-scene {opacity:0!important}
        .workspace-scene-0 {opacity:1!important}
        .workspace-caret {opacity:1}
        .workspace-cycle-label {display:none}
        .workspace-static-label {display:inline}
      }
    </style>
    '''.replace("__TYPE_WIDTH__", f"{type_width:.1f}").replace("__CHARS__", str(len(typed_line)))
    body += '<path d="M23 1H977Q999 1 999 23V57H1V23Q1 1 23 1Z" fill="var(--panel)"/>'
    body += '<path d="M1 57H999" stroke="var(--border)"/>'
    for x, color in [(27, "border"), (41, "muted"), (55, "accent")]:
        body += f'<circle cx="{x}" cy="29" r="3.5" fill="var(--{color})"/>'
    body += text(77, 34, "tonim / developer.workspace", 13, "muted", 500, 'class="workspace-mono"')
    body += rect(758, 17, 216, 25, "bg", 12)
    body += '<circle cx="773" cy="29.5" r="3" fill="var(--green)"/>'
    body += text(786, 33.5, "OPEN TO COLLABORATE", 10, "green", 650, 'letter-spacing=".8"')

    body += rect(20, 109, 525, 29, radius=6, extra='opacity=".7"')
    code_lines = [
        [("const ", "blue"), ("profile", "text"), (" = {", "muted")],
        [("  name", "text"), (": ", "muted"), ('"Tonim"', "accent"), (",", "muted")],
        [("  handle", "text"), (": ", "muted"), ('"ZpkDxGames"', "accent"), (",", "muted")],
        [("  focus", "text"), (": [", "muted"), ('"Java"', "green"), (", ", "muted"),
         ('"Paper"', "green"), (", ", "muted"), ('"Web"', "green"), ("],", "muted")],
        [("  ecosystem", "text"), (": ", "muted"), ('"Plexon"', "accent")],
        [("};", "muted")],
    ]
    for i, segments in enumerate(code_lines):
        y = 99 + i * 28
        body += text(35, y, f"{i + 1:02d}", 12, "muted", extra='class="workspace-mono" opacity=".6"')
        body += f'<text class="workspace-mono" x="74" y="{y}" font-size="16" xml:space="preserve">'
        body += "".join(f'<tspan fill="var(--{color})">{escape(value)}</tspan>' for value, color in segments)
        body += '</text>'
    body += '<path d="M34 261H534" stroke="var(--border)"/>'
    body += text(43, 291, ">", 18, "accent", 600, 'class="workspace-mono"')
    body += text(74, 291, typed_line, 14, "muted", extra='class="workspace-mono" clip-path="url(#workspace-typing)"')
    body += '<rect class="workspace-caret" x="74" y="277" width="8" height="17" rx="1" fill="var(--accent)"/>'

    body += rect(570, 80, 402, 236, radius=16, extra='stroke="var(--border)"')
    body += text(596, 110, "PROJECT SPOTLIGHT", 10, "muted", 650, 'letter-spacing="1.4"')
    spotlights = [
        ("PlexonTools", "accent", ["Custom tools with shared progression,", "world controls, and editable GUIs."],
         ["PROGRESSION", "WORLD GUIs", "SQLITE"]),
        ("GhostBlocks", "blue", ["Collision-free block models for", "creative builds and custom maps."],
         ["BLOCK MODELS", "BUILDING", "MINIMESSAGE"]),
        ("PlexonChats", "green", ["Configurable server chat, rich text,", "and optional Discord integration."],
         ["CHAT", "ADMIN GUIs", "DISCORDSRV"]),
    ]
    for i, (name, color, description, labels) in enumerate(spotlights):
        body += f'<g id="workspace-scene-{i}" class="workspace-scene workspace-scene-{i}">'
        body += text(946, 110, f"0{i + 1} / 03", 11, color, 500, 'class="workspace-mono" text-anchor="end"')
        body += text(596, 153, name, 28, color, 700, 'letter-spacing="-.5"')
        for line, value in enumerate(description):
            body += text(596, 183 + line * 20, value, 14, "muted")
        x = 596
        for label in labels:
            width = len(label) * 6 + 20
            body += rect(x, 225, width, 24, "bg", 6)
            body += text(x + 10, 241, label, 9, color, 600, 'class="workspace-mono" letter-spacing=".3"')
            x += width + 7
        for dot in range(3):
            body += f'<circle cx="{916 + dot * 13}" cy="275" r="3" fill="var(--{color if dot == i else "border"})"/>'
        body += '</g>'
    body += text(596, 279, "NEXT PROJECT", 9, "muted", 500, 'class="workspace-cycle-label" letter-spacing="1"')
    body += text(596, 279, "FEATURED PROJECT", 9, "muted", 500, 'class="workspace-static-label" letter-spacing="1"')
    body += rect(596, 296, 344, 2, "border", 1)
    body += rect(596, 296, 344, 2, "accent", 1, 'class="workspace-timer"')
    body += '<rect class="workspace-edge" x="1.5" y="1.5" width="997" height="337" rx="20" fill="none" stroke="var(--accent)" stroke-width="1.4" opacity=".65"/>'
    return svg(theme, 1000, 340, "Tonim's developer workspace",
               "Animated profile illustration for Tonim / ZpkDxGames: Java, Paper, and Web. Rotating project highlights feature PlexonTools, GhostBlocks, and PlexonChats. Not a live terminal. Reduced motion shows PlexonTools without animation.", body)


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
        for (x, y), row in zip(points, data["daily"]):
            if row["commits"]:
                body += f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.5" fill="var(--accent)"><title>{row["date"]}: {row["commits"]} commits</title></circle>'
        for index in sorted({0, len(values) // 3, len(values) * 2 // 3, len(values) - 1}):
            label = date.fromisoformat(data["daily"][index]["date"]).strftime("%d %b")
            body += text(points[index][0], 419, label, 12, "muted", extra='text-anchor="middle"')
    body += text(32, 457, "Public originals only · all authors except bots · UTC · profile repository excluded", 12, "muted")
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
        body += rect(32, y + 9, round(442 * project["commits"] / maximum, 2), 7, "accent", 3, 'class="rise"')
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


def render(data, root=ROOT):
    if data.get("schema") != 1 or len(data.get("daily", [])) != DAYS:
        raise ValueError("Unexpected profile snapshot format")
    if sum(d["commits"] for d in data["daily"]) != sum(p["commits"] for p in data["projects"]):
        raise ValueError("Daily and project totals do not agree")
    outputs = {"data/profile.json": json.dumps(data, indent=2, ensure_ascii=False) + "\n"}
    for theme in THEMES:
        outputs[f"assets/profile/workspace-{theme}.svg"] = workspace_header(theme)
        for name, renderer in [("activity", activity), ("ecosystem", ecosystem), ("releases", release_radar)]:
            outputs[f"assets/profile/{name}-{theme}.svg"] = renderer(data, theme)
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
