#!/usr/bin/env python3
"""Collect real public GitHub data and build a self-contained SVG profile."""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
import textwrap
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html import escape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SNAPSHOT = ROOT / "data" / "github.json"
NAVY, PANEL, BORDER = "#070e1d", "#101e33", "#223b55"
WHITE, MUTED, CYAN, BLUE = "#f0f7ff", "#afc4da", "#55e1ee", "#4b91ff"
LANG_COLORS = [CYAN, BLUE, "#80b5ff", "#45bda9", "#ccdffe", "#527087"]


def fetch(url: str, token: str | None = None, body: dict | None = None,
          as_text: bool = False):
    headers = {"User-Agent": "ZpkDxGames-profile-dashboard", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        headers["Content-Type"] = "application/json"
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers=headers,
                data=json.dumps(body).encode() if body is not None else None)
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
            return raw if as_text else json.loads(raw)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


class ContributionParser(HTMLParser):
    """Read exact contribution counts from public calendar tooltips."""
    def __init__(self):
        super().__init__()
        self.dates: dict[str, str] = {}
        self.counts: dict[str, int] = {}
        self.target: str | None = None
        self.fragments: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("data-date") and a.get("id"):
            self.dates[a["id"]] = a["data-date"]
        if tag == "tool-tip" and a.get("for"):
            self.target, self.fragments = a["for"], []

    def handle_data(self, data):
        if self.target is not None:
            self.fragments.append(data)

    def handle_endtag(self, tag):
        if tag == "tool-tip" and self.target is not None:
            text = "".join(self.fragments).strip()
            match = re.match(r"(No|[\d,]+) contributions? on\b", text)
            if match:
                self.counts[self.target] = 0 if match[1] == "No" else int(match[1].replace(",", ""))
            self.target = None

    def days(self):
        return {self.dates[key]: count for key, count in self.counts.items() if key in self.dates}


def validate_calendar(days: dict[str, int], start: dt.date, end: dt.date):
    expected = {(start + dt.timedelta(days=i)).isoformat() for i in range((end - start).days + 1)}
    filtered = {date: count for date, count in days.items() if date in expected}
    if set(filtered) != expected or any(type(count) is not int or count < 0 for count in filtered.values()):
        raise ValueError("Contribution calendar is incomplete; keep the last valid snapshot.")
    return [{"date": date, "count": filtered[date]} for date in sorted(filtered)]


def calendar(login: str, now: dt.datetime, token: str | None):
    end, start = now.date(), now.date() - dt.timedelta(days=364)
    if token:
        try:
            query = """query($login:String!,$from:DateTime!,$to:DateTime!){
              user(login:$login){contributionsCollection(from:$from,to:$to){
                contributionCalendar{weeks{contributionDays{date contributionCount}}}
              }}
            }"""
            result = fetch("https://api.github.com/graphql", token, {
                "query": query, "variables": {"login": login,
                    "from": start.isoformat() + "T00:00:00Z", "to": now.isoformat().replace("+00:00", "Z")}})
            if result.get("errors"):
                raise ValueError("GraphQL did not return a complete calendar")
            weeks = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
            days = {day["date"]: day["contributionCount"] for week in weeks for day in week["contributionDays"]}
            return validate_calendar(days, start, end), "GitHub GraphQL contributionCalendar"
        except Exception as error:
            print(f"Calendar API unavailable ({type(error).__name__}); reading the public calendar.", file=sys.stderr)
    days = {}
    # GitHub's public endpoint returns a single calendar year, even for cross-year ranges.
    for year in range(start.year, end.year + 1):
        parser = ContributionParser()
        parser.feed(fetch(f"https://github.com/users/{login}/contributions?from={year}-01-01&to={year}-12-31",
                          as_text=True))
        days.update(parser.days())
    return validate_calendar(days, start, end), "GitHub public contribution calendar (exact tooltip counts)"


def original_repositories(repos: list[dict], login: str, excluded: list[str]):
    exclusions = {name.casefold() for name in excluded}
    return [repo for repo in repos if not repo.get("private") and not repo.get("fork")
            and repo["owner"]["login"].casefold() == login.casefold()
            and repo["name"].casefold() not in exclusions]


def collect(config: dict):
    login = config["username"]
    if not re.fullmatch(r"[A-Za-z0-9-]+", login):
        raise ValueError("Invalid GitHub username")
    token = os.getenv("GITHUB_TOKEN")
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    profile = fetch(f"https://api.github.com/users/{login}", token)
    repos, page = [], 1
    while True:
        batch = fetch(f"https://api.github.com/users/{login}/repos?per_page=100&type=owner&page={page}", token)
        if not isinstance(batch, list):
            raise ValueError("Repository API returned an invalid response")
        repos.extend(repo for repo in batch if not repo.get("private") and repo["owner"]["login"].casefold() == login.casefold())
        if len(batch) < 100:
            break
        page += 1
    owned = original_repositories(repos, login, config["exclude_languages"])
    languages: dict[str, int] = {}
    def repo_languages(repo):
        return fetch(f"https://api.github.com/repos/{login}/{urllib.parse.quote(repo['name'])}/languages", token)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for stats in pool.map(repo_languages, owned):
            for language, size in stats.items():
                if type(size) is not int or size < 0:
                    raise ValueError("Invalid repository language count")
                languages[language] = languages.get(language, 0) + size
    days, source = calendar(login, now, token)
    if not sum(languages.values()):
        raise ValueError("No code-language data returned; keep the last valid snapshot.")
    public = [{"name": repo["name"], "url": repo["html_url"], "fork": repo["fork"],
               "archived": repo["archived"], "language": repo["language"],
               "stars": repo["stargazers_count"], "pushed_at": repo["pushed_at"]}
              for repo in sorted(repos, key=lambda repo: repo["name"].casefold())]
    missing = {project["repo"] for project in config["projects"]} - {repo["name"] for repo in repos}
    if missing:
        raise ValueError(f"Selected project is not public: {', '.join(sorted(missing))}")
    return {"schema": 1, "username": profile["login"], "captured_at": now.isoformat().replace("+00:00", "Z"),
            "public_repos": len(public), "original_repos": len(owned), "repositories": public,
            "language_bytes": dict(sorted(languages.items(), key=lambda pair: (-pair[1], pair[0]))),
            "calendar_source": source, "calendar_start": days[0]["date"], "calendar_end": days[-1]["date"],
            "contributions": sum(day["count"] for day in days),
            "active_days": sum(day["count"] > 0 for day in days), "days": days}


def weekly_activity(snapshot: dict):
    end = dt.date.fromisoformat(snapshot["calendar_end"])
    start = end - dt.timedelta(days=end.weekday() + 77)
    by_date = {day["date"]: day["count"] for day in snapshot["days"]}
    weeks = []
    for week in range(12):
        monday = start + dt.timedelta(days=week * 7)
        values = [by_date.get((monday + dt.timedelta(days=day)).isoformat()) for day in range(7)]
        weeks.append({"date": monday, "days": values, "count": sum(value or 0 for value in values)})
    return weeks


def language_shares(snapshot: dict):
    pairs = sorted(snapshot["language_bytes"].items(), key=lambda pair: (-pair[1], pair[0]))
    top = pairs[:5]
    if len(pairs) > 5:
        top.append(("Other", sum(value for _, value in pairs[5:])))
    total = sum(value for _, value in pairs)
    return [(name, value / total) for name, value in top]


def pretty(value: int):
    return f"{value:,}"


def percent(share: float):
    return "<0.1%" if 0 < share < .001 else f"{share * 100:.1f}%"


class Canvas:
    def __init__(self, width, height, title, description):
        self.width, self.height = width, height
        self.parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#101e35"/><stop offset=".5" stop-color="{NAVY}"/><stop offset="1" stop-color="#0d2136"/></linearGradient>
  <linearGradient id="accent"><stop stop-color="{BLUE}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
  <linearGradient id="bar" x1="0" y1="1" x2="0" y2="0"><stop stop-color="#255795"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
  <radialGradient id="aura"><stop stop-color="#2386b5" stop-opacity=".25"/><stop offset="1" stop-color="#2386b5" stop-opacity="0"/></radialGradient>
  <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M 32 0 H 0 V 32" fill="none" stroke="#1d3753" stroke-width=".65"/></pattern>
  <clipPath id="panel"><rect x="1" y="1" width="{width-2}" height="{height-2}" rx="22"/></clipPath>
</defs>
<style>
text{{font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;fill:{WHITE};}}
.mono{{font-family:Consolas,'Liberation Mono',monospace;letter-spacing:.7px;}}
.spin{{transform-box:fill-box;transform-origin:center;animation:orbit 48s linear infinite;}}
.flow{{stroke-dasharray:28 180;animation:flow 8s linear infinite;}}
.soft{{animation:soft 5s ease-in-out infinite;}}
.float{{animation:float 6s ease-in-out infinite;}}
@keyframes orbit{{to{{transform:rotate(360deg);}}}}
@keyframes flow{{to{{stroke-dashoffset:-416;}}}}
@keyframes soft{{0%,100%{{opacity:.45;}}50%{{opacity:1;}}}}
@keyframes float{{0%,100%{{transform:translateY(0);}}50%{{transform:translateY(-4px);}}}}
@media (prefers-reduced-motion:reduce){{.spin,.flow,.soft,.float{{animation:none;}}}}
</style>
<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="22" fill="url(#bg)" stroke="{BORDER}"/>
<g clip-path="url(#panel)"><rect width="{width}" height="{height}" fill="url(#grid)" opacity=".16"/>
<ellipse cx="{width*.91}" cy="0" rx="{width*.47}" ry="{height*.88}" fill="url(#aura)"/></g>''']

    def add(self, content):
        self.parts.append(content)

    def text(self, x, y, value, size=20, color=WHITE, weight=400, cls="", anchor="start", spacing=None):
        extra = f' letter-spacing="{spacing}"' if spacing is not None else ""
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" class="{cls}" text-anchor="{anchor}" style="fill:{color}"{extra}>{escape(str(value))}</text>')

    def rect(self, x, y, w, h, fill=PANEL, stroke=BORDER, radius=12, extra=""):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" {extra}/>')

    def line(self, x1, y1, x2, y2, color=BORDER, width=1, extra=""):
        self.add(f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{color}" stroke-width="{width}" {extra}/>')

    def circle(self, x, y, r, fill="none", stroke=BORDER, width=1, extra=""):
        self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" {extra}/>')

    def lines(self, x, y, value, chars, size=20, step=28, color=MUTED):
        for i, line in enumerate(textwrap.wrap(value, width=chars, break_long_words=False, break_on_hyphens=False)):
            self.text(x, y + i * step, line, size, color)

    def finish(self):
        return "\n".join(self.parts) + "\n</svg>\n"


def code_orbit(c, x, y, scale=1, opacity=1):
    c.add(f'<g transform="translate({x},{y}) scale({scale})" opacity="{opacity}">')
    c.circle(0, 0, 112, stroke="#315477", width=1.3)
    c.circle(0, 0, 137, stroke=CYAN, extra='stroke-dasharray="2 20" class="spin" opacity=".55"')
    c.add(f'<path d="M-94,-58 A111,111 0 0 1 75,-81" fill="none" stroke="url(#accent)" stroke-width="4" stroke-linecap="round" class="soft"/>')
    c.add(f'<path d="M0,-76 L66,-38 V38 L0,76 L-66,38 V-38 Z" fill="#0f243c" stroke="{BLUE}" stroke-width="2"/>')
    c.add(f'<path d="M-12,-76 L54,-38 V38 L-12,76" fill="none" stroke="#244963" stroke-width="1"/>')
    c.add(f'<path d="M-27,-18 L-45,0 L-27,18 M27,-18 L45,0 L27,18 M12,-26 L-12,26" fill="none" stroke="{CYAN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>')
    for nx, ny in [(-96,-62),(105,41),(-41,103)]:
        c.line(nx, ny, nx*.57, ny*.57, BLUE, 1.5)
        c.circle(nx, ny, 9, NAVY, CYAN, 2)
        c.circle(nx, ny, 3, CYAN, "none", extra='class="soft"')
    c.add('</g>')


def hero(config, mobile):
    w, h = (420, 410) if mobile else (900, 352)
    c = Canvas(w, h, "ZpkDxGames — Tonim's developer dashboard", "Minecraft systems, developer tools, and local-first interactive apps. Blue and cyan orbital code artwork is decorative.")
    if mobile:
        code_orbit(c, 352, 182, .63, .23)
        c.text(26, 40, "TONIM / DEVELOPER", 20, CYAN, cls="mono")
        c.circle(380, 34, 5, CYAN, "none", extra='class="soft"')
        c.text(26, 100, config["username"], 43, weight=700, spacing=-1.6)
        c.text(26, 161, "Minecraft worlds.", 34, weight=600, spacing=-.8)
        c.text(26, 206, "Real-world tools.", 34, CYAN, weight=600, spacing=-.8)
        c.text(26, 259, "Minecraft systems, developer tools", 21, MUTED)
        c.text(26, 290, "and local-first interactive apps.", 21, MUTED)
        c.line(26, 326, 394, 326)
        c.text(26, 362, "JAVA / TYPESCRIPT", 20, CYAN, cls="mono")
        c.text(26, 389, "JAVASCRIPT / BRAZIL", 20, MUTED, cls="mono")
    else:
        code_orbit(c, 728, 187)
        c.text(36, 39, "TONIM / DEVELOPER DASHBOARD", 16, CYAN, cls="mono")
        c.text(860, 39, "PUBLIC GITHUB", 16, MUTED, cls="mono", anchor="end")
        c.text(36, 111, config["username"], 60, weight=700, spacing=-2)
        c.text(36, 174, "Minecraft worlds.", 43, weight=600, spacing=-1)
        c.text(36, 227, "Real-world tools.", 43, CYAN, weight=600, spacing=-1)
        c.text(36, 274, "Systems, software, and interfaces with purpose.", 21, MUTED)
        c.line(36, 297, 524, 297)
        c.text(36, 326, "JAVA / TYPESCRIPT / JAVASCRIPT", 16, CYAN, cls="mono")
        c.text(860, 326, "BRAZIL", 16, MUTED, cls="mono", anchor="end")
    return c.finish()


def metrics(snapshot, mobile):
    c = Canvas(420 if mobile else 900, 480 if mobile else 264,
               "GitHub at a glance", f"{snapshot['public_repos']} public repositories; {snapshot['original_repos']} original repositories excluding the profile; {snapshot['contributions']} profile contributions and {snapshot['active_days']} active days in the last 365 calendar days. Snapshot {snapshot['captured_at']}.")
    date = dt.date.fromisoformat(snapshot["calendar_end"]).strftime("%d %b %Y").upper()
    c.text(26 if mobile else 36, 47 if mobile else 43, "GitHub at a glance", 28 if mobile else 26, weight=600)
    c.text(26 if mobile else 864, 79 if mobile else 43, date + " / UTC", 20 if mobile else 16, MUTED, cls="mono", anchor="start" if mobile else "end")
    labels = [("public_repos", "Public repos", "Owned + forks"), ("original_repos", "Original repos", "Excludes profile"),
              ("contributions", "Contributions", "Past 365 days"), ("active_days", "Active days", "Past 365 days")]
    for i, (key, label, sub) in enumerate(labels):
        x = 24 + (i % 2) * 194 if mobile else 36 + i * 217
        y = 108 + (i // 2) * 173 if mobile else 81
        width, height = (178, 155) if mobile else (177, 149)
        c.rect(x, y, width, height, fill="#0d1b2e")
        c.line(x+16, y+1, x+width-16, y+1, CYAN if i % 2 == 0 else BLUE, 2)
        c.text(x+16, y+58, pretty(snapshot[key]), 43 if mobile else 42, weight=650, spacing=-1.5)
        c.text(x+16, y+98, label, 20 if mobile else 19, weight=600)
        c.text(x+16, y+128, sub, 20 if mobile else 16, MUTED)
    c.text(26 if mobile else 36, 466 if mobile else 252, "Dated GitHub snapshot" if mobile else "PUBLIC REPOSITORIES / PROFILE CONTRIBUTION CALENDAR", 20 if mobile else 16, MUTED, cls="" if mobile else "mono")
    return c.finish()


def activity(snapshot, mobile):
    weeks = weekly_activity(snapshot)
    total = sum(week["count"] for week in weeks)
    c = Canvas(420 if mobile else 900, 595 if mobile else 378,
               "Contribution rhythm", f"Twelve calendar weeks of real GitHub profile contributions, from {weeks[0]['date']} through {snapshot['calendar_end']}. {total} contributions in this interval. Current week is in progress. Weekly bars and daily heatmap use identical calendar data.")
    c.text(26 if mobile else 36, 47 if mobile else 43, "Contribution rhythm", 28 if mobile else 26, weight=600)
    c.text(26 if mobile else 36, 79 if mobile else 76, "12 weeks · current week in progress", 20 if mobile else 18, MUTED)
    if mobile:
        c.text(26, 130, pretty(total), 36, CYAN, weight=650)
        c.text(394, 130, "contributions", 20, MUTED, anchor="end")
        x, y, pw, ph = 75, 187, 312, 146
        c.text(26, 165, "Weekly contributions", 20, MUTED)
    else:
        c.text(864, 74, pretty(total) + " contributions", 23, CYAN, weight=600, anchor="end")
        x, y, pw, ph = 76, 131, 479, 181
        c.text(36, 110, "WEEKLY CONTRIBUTIONS", 16, MUTED, cls="mono")
    maximum = max(max(week["count"] for week in weeks), 1)
    cap = max(4, math.ceil(maximum / 4) * 4)
    for tick in range(5):
        gy = y + ph - ph * tick / 4
        c.line(x, gy, x+pw, gy, BORDER, .8)
        value = round(cap * tick / 4)
        label = f"{value / 1000:.1f}k" if value >= 1000 else str(value)
        c.text(x-10, gy+6, label, 20 if mobile else 16, MUTED, anchor="end")
    points = []
    for i, week in enumerate(weeks):
        bx = x + (i + .5) * pw / 12
        bh = ph * week["count"] / cap
        c.rect(bx-(8 if mobile else 12), y+ph-bh, 16 if mobile else 24, bh, fill="url(#bar)", stroke="none", radius=3, extra='opacity=".85"')
        points.append((bx, y+ph-bh))
        if i in (0, 4, 8, 11):
            c.text(bx, y+ph+30, week["date"].strftime("%d %b"), 20 if mobile else 16, MUTED, anchor="middle")
    c.add('<polyline points="' + " ".join(f"{px:.2f},{py:.2f}" for px, py in points) + f'" fill="none" stroke="{CYAN}" stroke-width="2" stroke-linejoin="round"/>')
    c.circle(*points[-1], 5, CYAN, NAVY, 2, extra='class="soft"')
    hx, hy, step, cell = (112, 411, 22, 17) if mobile else (616, 143, 20, 15)
    c.text(26 if mobile else hx, 394 if mobile else 117, "Daily density" if mobile else "DAILY DENSITY", 20 if mobile else 16, MUTED, cls="" if mobile else "mono")
    day_max = max([value for week in weeks for value in week["days"] if value is not None] + [1])
    tones = ["#12233a", "#1c4f77", "#2779a8", "#35accd", CYAN]
    for wi, week in enumerate(weeks):
        for di, count in enumerate(week["days"]):
            if count is None:
                fill, stroke = NAVY, BORDER
            else:
                level = 0 if count == 0 else 1 + min(3, int(math.log1p(count) / math.log1p(day_max) * 3))
                fill, stroke = tones[level], "none"
            c.rect(hx+wi*step, hy+di*step, cell, cell, fill, stroke, 3)
    for di, label in [(0, "M"), (2, "W"), (4, "F")]:
        c.text(hx-14, hy+di*step+cell-2, label, 20 if mobile else 16, MUTED, anchor="end")
    ly = 582 if mobile else 317
    c.text(112 if mobile else 616, ly, "Less", 20 if mobile else 16, MUTED)
    for i, tone in enumerate(tones):
        c.rect((163 if mobile else 662)+i*21, ly-16, 16, 16, tone, "none", 3)
    c.text(276 if mobile else 776, ly, "More", 20 if mobile else 16, MUTED)
    if not mobile:
        c.text(36, 355, f"{weeks[0]['date'].strftime('%d %b')} — {dt.date.fromisoformat(snapshot['calendar_end']).strftime('%d %b %Y')} / GitHub profile calendar", 16, MUTED)
    return c.finish()


def languages(snapshot, mobile):
    rows = language_shares(snapshot)
    c = Canvas(420 if mobile else 900, 620 if mobile else 346,
               "Repository language mix", "Language bytes from public original repositories, excluding this profile. " + "; ".join(f"{name}: {percent(share)}" for name, share in rows) + ". This is code share, not proficiency.")
    c.text(26 if mobile else 36, 47 if mobile else 43, "Repository language mix", 27 if mobile else 26, weight=600)
    c.text(26 if mobile else 36, 80 if mobile else 76, "Code bytes · public original repos" if mobile else "Share of code bytes · public original repositories", 20 if mobile else 18, MUTED)
    cx, cy, radius = (210, 192, 79) if mobile else (171, 190, 83)
    c.circle(cx, cy, radius, stroke="#162c44", width=23)
    length, offset = math.tau * radius, 0
    for i, (_, share) in enumerate(rows):
        c.circle(cx, cy, radius, stroke=LANG_COLORS[i], width=23,
                 extra=f'stroke-dasharray="{share*length:.4f} {length:.4f}" stroke-dashoffset="{-offset:.4f}" transform="rotate(-90 {cx} {cy})"')
        offset += share * length
    c.circle(cx, cy, radius+27, stroke=BLUE, extra='stroke-dasharray="1 15" class="spin" opacity=".6"')
    c.text(cx, cy-6, "CODE", 22 if mobile else 19, MUTED, cls="mono", anchor="middle")
    c.text(cx, cy+31, "100%", 34, weight=600, anchor="middle")
    for i, (name, share) in enumerate(rows):
        yy = 324+i*43 if mobile else 118+i*34
        tx = 26 if mobile else 350
        c.circle(tx+5, yy-7, 5, LANG_COLORS[i], "none")
        c.text(tx+20, yy, name, 20, weight=500)
        c.text(394 if mobile else 864, yy, percent(share), 20, MUTED, anchor="end")
        if mobile:
            c.rect(26, yy+9, 368, 5, fill="#193149", stroke="none", radius=2)
            c.rect(26, yy+9, 368*share, 5, fill=LANG_COLORS[i], stroke="none", radius=2)
        else:
            c.rect(570, yy-10, 187, 7, fill="#193149", stroke="none", radius=3)
            c.rect(570, yy-10, 187*share, 7, fill=LANG_COLORS[i], stroke="none", radius=3)
    c.text(26 if mobile else 350, 599 if mobile else 326, "Language share, not proficiency.", 20 if mobile else 16, MUTED)
    return c.finish()


def project_art(c, kind, x, y, scale=1):
    c.add(f'<g transform="translate({x},{y}) scale({scale})">')
    c.circle(0, 0, 110, stroke=BLUE, extra='stroke-dasharray="2 15" class="spin" opacity=".35"')
    c.circle(0, 0, 83, fill="url(#aura)", stroke="#21435f")
    if kind == "servers":
        for i in range(3):
            sy = -76 + i*51
            c.rect(-66, sy, 132, 37, fill="#0d2239", stroke="#356383", radius=7)
            c.rect(-51, sy+11, 65, 5, fill="#356687", stroke="none", radius=2)
            c.rect(-51, sy+22, 43, 4, fill="#203e5b", stroke="none", radius=2)
            c.circle(46, sy+18, 4, CYAN, "none", extra='class="soft"')
        for sign in [-1, 1]:
            c.add(f'<path d="M{sign*66},-30 H{sign*101} V63 H{sign*43}" fill="none" stroke="#315779" stroke-width="2"/>')
            c.add(f'<path d="M{sign*66},-30 H{sign*101} V63 H{sign*43}" fill="none" stroke="{CYAN}" stroke-width="2" class="flow"/>')
        c.circle(0, 83, 7, CYAN, "none")
    elif kind == "companion":
        c.add('<g class="float">')
        c.add(f'<path d="M-28,-68 L0,-83 L31,-68 V-25 L0,-9 L-28,-25Z" fill="#194468" stroke="{CYAN}" stroke-width="1.7"/>')
        c.add(f'<path d="M0,-83 V-40 L31,-25 M-28,-68 L0,-40 L31,-68" fill="none" stroke="#3c86a6"/>')
        c.rect(-17, -51, 7, 7, CYAN, "none", 0)
        c.rect(7, -51, 7, 7, CYAN, "none", 0)
        c.add(f'<path d="M-33,-14 L0,-1 L33,-14 V46 L0,61 L-33,46Z" fill="#146985" stroke="{BLUE}" stroke-width="1.5"/>')
        c.add(f'<path d="M-50,-13 L-35,-6 V41 L-50,34Z M36,-6 L54,-17 V30 L36,41Z" fill="#1a4d75" stroke="#67aec9"/>')
        c.add(f'<path d="M-30,49 L-4,60 V91 L-30,80Z M4,60 L30,49 V80 L4,92Z" fill="#173956" stroke="#3d77a0"/>')
        c.add('</g>')
        c.add(f'<ellipse cx="0" cy="101" rx="59" ry="9" fill="{CYAN}" opacity=".07"/>')
    elif kind == "dashboard":
        c.rect(-97, -64, 194, 123, fill="#0d2037", stroke="#477fa8", radius=9)
        c.line(-97, -44, 97, -44, "#477fa8")
        for i in range(3):
            c.circle(-81+i*12, -54, 2.7, CYAN if i==0 else "#477fa8", "none")
        c.rect(-83, -32, 28, 78, fill="#17354e", stroke="none", radius=3)
        for i in range(4):
            c.line(-77, -21+i*15, -62, -21+i*15, BLUE if i==0 else "#38617d", 3)
        for i in range(3):
            c.rect(-42+i*43, -32, 34, 29, fill="#162e47", stroke="#365a76", radius=3)
            c.line(-35+i*43, -22, -19+i*43, -22, CYAN, 2)
            c.line(-35+i*43, -12, -25+i*43, -12, "#43698a", 2)
        for i in range(3):
            c.rect(-42, 8+i*12, 121, 7, fill="#1b3d59", stroke="none", radius=2)
        c.line(-25, 70, 25, 70, BLUE, 4)
        c.line(0, 59, 0, 70, BLUE, 4)
        c.line(-63, 89, 63, 89, CYAN, 2, extra='class="flow"')
    else:
        nodes = [(-65,-44),(-2,-79),(70,-36),(-81,26),(-30,75),(43,58),(3,-5),(82,38)]
        for a, b in [(0,1),(0,3),(0,6),(1,2),(1,6),(2,6),(2,7),(3,4),(3,6),(4,5),(4,6),(5,6),(5,7),(6,7)]:
            c.line(*nodes[a], *nodes[b], "#285976", 1.6)
        for a, b in [(0,6),(6,5),(1,2)]:
            c.line(*nodes[a], *nodes[b], CYAN, 2, extra='class="flow"')
        for i, (nx,ny) in enumerate(nodes):
            c.circle(nx,ny,10 if i==6 else 6, CYAN if i==6 else BLUE, "#92e8f5", 1.3)
            if i in (1,5,6):
                c.circle(nx,ny,17 if i==6 else 12, stroke=CYAN, extra='class="soft" opacity=".4"')
    c.add('</g>')


def project_card(config, project, mobile):
    c = Canvas(420 if mobile else 900, 500 if mobile else 264,
               project["title"], project["description"] + " Built with " + ", ".join(project["tags"]) + ". Conceptual vector illustration; open the card to see the source repository.")
    c.text(26 if mobile else 36, 38, project["category"], 20 if mobile else 16, CYAN, cls="mono")
    if mobile:
        project_art(c, project["visual"], 210, 161, .84)
        if len(project["title"]) > 20:
            for i, line in enumerate(textwrap.wrap(project["title"], width=18)):
                c.text(26, 270+i*36, line, 30, weight=600, spacing=-.7)
            c.lines(26, 345, project["description"], 35, 20, 27)
        else:
            c.text(26, 287, project["title"], 30, weight=600, spacing=-.7)
            c.lines(26, 326, project["description"], 35, 20, 27)
        ty = 450
    else:
        project_art(c, project["visual"], 734, 151, .85)
        c.text(36, 94, project["title"], 35, weight=600, spacing=-.8)
        c.lines(36, 133, project["description"], 51, 20, 29)
        ty = 215
        c.circle(853, 35, 16, fill="#142c42", stroke="#345e78")
        c.add(f'<path d="M847,41 L858,30 M847,30 H858 V41" fill="none" stroke="{CYAN}" stroke-width="1.7"/>')
    tx = 26 if mobile else 36
    for tag in project["tags"]:
        width = len(tag) * (10 if mobile else 9) + 26
        c.rect(tx, ty, width, 34 if mobile else 30, fill="#112a40", stroke="#28495f", radius=7)
        c.text(tx+13, ty+(24 if mobile else 21), tag, 20 if mobile else 16, MUTED)
        tx += width + 9
    return c.finish()


def footer(mobile):
    c = Canvas(420 if mobile else 900, 151 if mobile else 115,
               "Let's build something useful", "Explore the source. Follow the build.")
    c.text(26 if mobile else 36, 51 if mobile else 49, "Let's build something" if mobile else "Let's build something useful.", 27 if mobile else 30, weight=600, spacing=-.5)
    if mobile:
        c.text(26, 87, "useful.", 27, CYAN, weight=600)
    c.text(26 if mobile else 36, 126 if mobile else 83, "Explore the source. Follow the build.", 20, MUTED)
    if not mobile:
        c.line(682, 58, 848, 58, "#315371", 2)
        c.line(682, 58, 848, 58, CYAN, 2.5, extra='class="flow"')
        c.add(f'<path d="M835,44 L850,58 L835,72" fill="none" stroke="{CYAN}" stroke-width="2.5" stroke-linecap="round"/>')
    return c.finish()


def picture(name, alt, config, href=None):
    base = f"https://raw.githubusercontent.com/{config['username']}/{config['username'].lower()}/main/assets"
    def url(variant):
        path = ASSETS / f"{name}-{variant}.svg"
        version = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        return f"{base}/{path.name}?v={version}"
    html = f'''<picture>
  <source media="(max-width: 600px)" srcset="{url('mobile')}">
  <img src="{url('wide')}" width="100%" alt="{escape(alt, quote=True)}">
</picture>'''
    return f'<a href="{href}">\n{html}\n</a>' if href else html


def render(snapshot, config):
    ASSETS.mkdir(exist_ok=True)
    all_assets = {}
    for mobile in [False, True]:
        variant = "mobile" if mobile else "wide"
        for name, builder in [("hero",lambda:hero(config,mobile)), ("metrics",lambda:metrics(snapshot,mobile)),
                              ("activity",lambda:activity(snapshot,mobile)), ("languages",lambda:languages(snapshot,mobile)),
                              ("footer",lambda:footer(mobile))]:
            all_assets[f"{name}-{variant}.svg"] = builder()
        for project in config["projects"]:
            all_assets[f"project-{project['visual']}-{variant}.svg"] = project_card(config,project,mobile)
    for name, svg in all_assets.items():
        ET.fromstring(svg)
        (ASSETS/name).write_text(svg, encoding="utf-8")
    login = config["username"]
    overview = f"{snapshot['public_repos']} public repos · {snapshot['original_repos']} original repos · {pretty(snapshot['contributions'])} contributions · {snapshot['active_days']} active days"
    sections = ["<!-- Generated from config/dashboard.json and the dated public snapshot. -->",
        picture("hero", f"{login} — Tonim. Minecraft worlds. Real-world tools.", config),
        f"I'm **{config['name']}** ({login}), a programmer based in Brazil. {config['bio']}",
        f"[Explore repositories](https://github.com/{login}?tab=repositories) · [Portfolio]({config['portfolio']}) · [Follow the work](https://github.com/{login}?tab=followers)",
        picture("metrics", overview + f". Profile calendar: {snapshot['calendar_start']} through {snapshot['calendar_end']}.", config),
        picture("activity", "Real GitHub contributions: twelve weekly totals and a matching daily heatmap. Current week is in progress.", config),
        picture("languages", "Code language share across public original repositories: " + ", ".join(f"{name} {percent(share)}" for name,share in language_shares(snapshot)) + ".", config),
        "## Selected projects", "Minecraft infrastructure, desktop interaction, and useful web interfaces. Open a card to explore its source."]
    for project in config["projects"]:
        sections.append(picture(f"project-{project['visual']}", project["title"]+" — "+project["description"], config, f"https://github.com/{login}/{project['repo']}"))
    details = ["<details>", "<summary>Dashboard data and project descriptions</summary>", "",
        f"Snapshot: **{snapshot['captured_at']}**. Profile calendar: **{snapshot['calendar_start']}–{snapshot['calendar_end']}**.", "",
        "| Metric | Value |", "| :--- | ---: |", f"| Public repositories (including forks/profile) | {snapshot['public_repos']} |",
        f"| Original repositories (excluding profile) | {snapshot['original_repos']} |",
        f"| Profile contributions (365 days) | {pretty(snapshot['contributions'])} |", f"| Active days (365 days) | {snapshot['active_days']} |", "",
        "| Language | Share of code bytes |", "| :--- | ---: |"]
    details += [f"| {name} | {percent(share)} |" for name, share in language_shares(snapshot)]
    details += ["", "Language share measures checked-in code, not proficiency. The calendar uses GitHub's contribution definition, which may include anonymized private activity displayed on the public profile. The current activity week is incomplete. Project artwork is conceptual.", ""]
    details += [f"- **[{project['title']}](https://github.com/{login}/{project['repo']}):** {project['description']}" for project in config["projects"]]
    details += ["", "[Metric definitions and maintenance](docs/DASHBOARD.md)", "", "</details>"]
    sections += ["\n".join(details), "## Build philosophy", "Make the interface clear. Keep state explicit. Validate the real behavior. Leave a path to recover.",
        picture("footer", "Let's build something useful. Explore the source. Follow the build.", config, f"https://github.com/{login}?tab=repositories"),
        f"<sub>GitHub snapshot · {snapshot['captured_at']} · [Refresh status](https://github.com/{login}/{login.lower()}/actions/workflows/dashboard-sync.yml)</sub>"]
    (ROOT/"README.md").write_text("\n\n".join(sections)+"\n", encoding="utf-8")


def check():
    snapshot = json.loads(SNAPSHOT.read_text())
    days = validate_calendar({day["date"]:day["count"] for day in snapshot["days"]},
                             dt.date.fromisoformat(snapshot["calendar_start"]), dt.date.fromisoformat(snapshot["calendar_end"]))
    assert len(days) == 365
    assert snapshot["contributions"] == sum(day["count"] for day in days)
    assert snapshot["active_days"] == sum(day["count"] > 0 for day in days)
    assert len(snapshot["repositories"]) == snapshot["public_repos"]
    svg_paths = list(ASSETS.glob("*.svg"))
    config = json.loads((ROOT/"config/dashboard.json").read_text())
    assert len(svg_paths) == (5+len(config["projects"]))*2
    for path in svg_paths:
        root = ET.fromstring(path.read_text())
        viewbox = root.attrib["viewBox"].split()
        assert viewbox[:2] == ["0", "0"]
        assert int(viewbox[2]) == (420 if "mobile" in path.stem else 900)
        assert root.find("{http://www.w3.org/2000/svg}title") is not None
        assert "prefers-reduced-motion:reduce" in path.read_text()
        for node in root.iter():
            assert node.tag.rsplit("}",1)[-1] not in {"script","foreignObject","image","a"}
            assert not any(key.startswith("on") for key in node.attrib)
            if node.tag.endswith("}text"):
                assert int(node.attrib["font-size"]) >= (20 if "mobile" in path.stem else 16), (path, node.text)
    readme = (ROOT/"README.md").read_text()
    for name, digest in re.findall(r"/assets/([\w-]+\.svg)\?v=([a-f0-9]+)", readme):
        assert hashlib.sha256((ASSETS/name).read_bytes()).hexdigest().startswith(digest)
    assert readme.count('<source media="(max-width: 600px)"') == 5+len(config["projects"])
    print(f"Validated {len(svg_paths)} SVGs, full calendar coverage, metric totals, motion fallbacks, and README references.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Collect a new verified public snapshot")
    parser.add_argument("--check", action="store_true", help="Validate committed outputs without network")
    args = parser.parse_args()
    if args.check:
        check()
        return
    config = json.loads((ROOT/"config/dashboard.json").read_text())
    if args.refresh:
        snapshot = collect(config)
        SNAPSHOT.parent.mkdir(exist_ok=True)
        SNAPSHOT.write_text(json.dumps(snapshot, indent=2)+"\n")
    else:
        snapshot = json.loads(SNAPSHOT.read_text())
    render(snapshot, config)
    check()
    print(f"Built desktop/mobile dashboard from snapshot {snapshot['captured_at']}.")


if __name__ == "__main__":
    main()
