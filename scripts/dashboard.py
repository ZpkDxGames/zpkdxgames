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
NAVY, PANEL, BORDER = "#080e1a", "#101d30", "#25364d"
WHITE, MUTED, CYAN, BLUE = "#edf4ff", "#a5b6cc", "#67e8f9", "#5698ff"
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
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#111e31"/><stop offset=".55" stop-color="{NAVY}"/><stop offset="1" stop-color="#102337"/></linearGradient>
  <linearGradient id="accent"><stop stop-color="{BLUE}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
  <linearGradient id="bar" x1="0" y1="1" x2="0" y2="0"><stop stop-color="#255795"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
  <linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#67e8f9" stop-opacity=".19"/><stop offset="1" stop-color="#5698ff" stop-opacity=".015"/></linearGradient>
  <linearGradient id="polish" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#ffffff" stop-opacity=".28"/><stop offset=".45" stop-color="#ffffff" stop-opacity="0"/><stop offset="1" stop-color="#06101f" stop-opacity=".20"/></linearGradient>
  <radialGradient id="aura"><stop stop-color="#2386b5" stop-opacity=".17"/><stop offset="1" stop-color="#2386b5" stop-opacity="0"/></radialGradient>
  <linearGradient id="surface" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#203c58"/><stop offset="1" stop-color="#112238"/></linearGradient>
  <linearGradient id="glass" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#22364f" stop-opacity=".75"/><stop offset="1" stop-color="#0b1526" stop-opacity=".9"/></linearGradient>
  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#57829d" stop-opacity=".7"/><stop offset=".5" stop-color="#25364d"/><stop offset="1" stop-color="#315570"/></linearGradient>
  <radialGradient id="sphere" cx=".3" cy=".2" r=".8"><stop stop-color="#e0fbff"/><stop offset=".3" stop-color="#67e8f9"/><stop offset="1" stop-color="#2064a3"/></radialGradient>
  <filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="3"/></filter>
  <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M 32 0 H 0 V 32" fill="none" stroke="#1d3753" stroke-width=".65"/></pattern>
  <clipPath id="panel"><rect x="1" y="1" width="{width-2}" height="{height-2}" rx="18"/></clipPath>
</defs>
<style>
text{{font-family:Arial,'Helvetica Neue',sans-serif;fill:{WHITE};}}
.mono{{font-family:Consolas,'Liberation Mono',monospace;letter-spacing:.7px;}}
.spin{{transform-box:fill-box;transform-origin:center;animation:orbit 48s linear infinite;}}
.flow{{stroke-dasharray:28 180;animation:flow 12s linear infinite;}}
.trace{{stroke-dasharray:70 930;animation:trace 16s linear infinite;}}
.halo{{animation:halo 7s cubic-bezier(.45,0,.55,1) infinite;}}
.reveal{{animation:reveal 1.4s cubic-bezier(.22,1,.36,1) both;}}
.soft{{animation:soft 7s cubic-bezier(.45,0,.55,1) infinite;}}
.float{{animation:float 8s cubic-bezier(.45,0,.55,1) infinite;}}
@keyframes trace{{to{{stroke-dashoffset:-1000;}}}}
@keyframes halo{{0%,100%{{opacity:.2;}}50%{{opacity:.65;}}}}
@keyframes reveal{{from{{opacity:0;}}to{{opacity:1;}}}}
@keyframes orbit{{to{{transform:rotate(360deg);}}}}
@keyframes flow{{to{{stroke-dashoffset:-416;}}}}
@keyframes soft{{0%,100%{{opacity:.45;}}50%{{opacity:1;}}}}
@keyframes float{{0%,100%{{transform:translateY(0);}}50%{{transform:translateY(-4px);}}}}
@media (prefers-reduced-motion:reduce){{.spin,.flow,.soft,.float,.trace,.halo,.reveal{{animation:none;}}}}
</style>
<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="18" fill="url(#bg)" stroke="url(#edge)"/>
<g clip-path="url(#panel)"><rect width="{width}" height="{height}" fill="url(#grid)" opacity=".045"/>
<ellipse cx="{width*.91}" cy="0" rx="{width*.47}" ry="{height*.88}" fill="url(#aura)"/>
<path d="M24,1 H{min(width-24, 225)}" stroke="url(#accent)" stroke-opacity=".7"/>
<path d="M24,{height-1} H{width-24}" stroke="#15293c"/>
</g>''']

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


def polygon(c, points, fill, stroke="#47718b", width=1):
    c.add('<polygon points="' + ' '.join(f"{x:.2f},{y:.2f}" for x,y in points) + f'" fill="{fill}" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round"/>')


def iso(x, y, z):
    """Shared 30-degree isometric projection for every architectural object."""
    return (.8660254*(x-y), .5*(x+y)-z)


def prism(c, x, y, z, dx, dy, dz, top="url(#surface)", left="#12243a", right="#19334c", stroke="#3c607c"):
    p=lambda a,b,d: iso(x+a,y+b,z+d)
    polygon(c, [p(0,dy,0),p(dx,dy,0),p(dx,dy,dz),p(0,dy,dz)], left, stroke)
    polygon(c, [p(dx,0,0),p(dx,dy,0),p(dx,dy,dz),p(dx,0,dz)], right, stroke)
    polygon(c, [p(0,0,dz),p(dx,0,dz),p(dx,dy,dz),p(0,dy,dz)], top, stroke)


def architecture(c, x, y, scale=1):
    c.add(f'<g transform="translate({x},{y}) scale({scale})">')
    c.add('<ellipse cx="0" cy="67" rx="145" ry="72" fill="url(#aura)"/>')
    for k in range(-3,4):
        c.line(*iso(-150,k*45,-72), *iso(150,k*45,-72), "#25405b", .7, 'opacity=".5"')
        c.line(*iso(k*45,-150,-72), *iso(k*45,150,-72), "#25405b", .7, 'opacity=".5"')
    prism(c,-83,-83,-56,166,166,9,top="#0f2237",left="#0c1728",right="#142e45")
    prism(c,-70,-70,-29,140,140,10,top="url(#surface)",stroke="#55829c")
    for sign in [-1,1]:
        for lane in [-27,0,27]:
            pts=[iso(sign*51,lane,-18),iso(sign*60,lane,-18),iso(sign*60,lane+9,-18),iso(sign*70,lane+9,-18)]
            c.add('<polyline points="'+' '.join(f"{xx:.2f},{yy:.2f}" for xx,yy in pts)+'" fill="none" stroke="#467a94" stroke-width="1"/>')
    for a,b in [((-70,-70,-18),(70,-70,-18)),((70,-70,-18),(70,70,-18))]:
        c.line(*iso(*a),*iso(*b),CYAN,2, 'class="flow"')
    for x0,y0 in [(-58,-58),(58,-58),(-58,58),(58,58)]:
        c.line(*iso(x0,y0,-18),*iso(x0,y0,13),"#3a7693",1,'stroke-dasharray="2 5"')
    c.add('<g class="float">')
    prism(c,-48,-48,16,96,96,30,top="url(#surface)",left="#12304a",right="#1d4960",stroke="#5c97b0")
    for i in range(6):
        px,py=iso(-35+i*14,48,26)
        c.line(px,py,px,py+9,CYAN,2,'opacity=".7"')
        px,py=iso(48,-35+i*14,26)
        c.line(px,py,px,py+9,BLUE,2,'opacity=".8"')
    c.add('<g transform="matrix(.8660254 .5 -.8660254 .5 0 -47)">')
    c.rect(-34,-34,68,68,fill="#132f47",stroke="#5aa7bd",radius=8)
    c.add(f'<path d="M-11,-11 L-23,0 L-11,11 M11,-11 L23,0 L11,11 M5,-17 L-5,17" fill="none" stroke="{CYAN}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>')
    c.add('</g></g>')
    for xx,yy in [(-132,18),(123,14),(0,131)]:
        c.circle(xx,yy,9,fill=CYAN,stroke="none",extra='opacity=".3" filter="url(#glow)" class="soft"')
        c.circle(xx,yy,3,fill=CYAN,stroke="none")
    c.add('</g>')


def hero(config, mobile):
    w,h=(420,625) if mobile else (900,420)
    c=Canvas(w,h,"ZpkDxGames — Tonim's developer dashboard", "Minecraft systems, developer tools, and local-first interactive apps. Layered isometric computing architecture is decorative.")
    pad=26 if mobile else 36
    c.circle(pad+4,36,4,CYAN,"none",extra='class="soft"')
    c.text(pad+19,42,"TONIM / DEVELOPER",20 if mobile else 16,CYAN,cls="mono")
    if not mobile:
        c.text(864,42,"BASED IN BRAZIL",16,MUTED,anchor="end")
    c.line(pad,63,w-pad,63)
    c.text(pad,125 if mobile else 145,config['username'],43 if mobile else 64,weight=700,spacing=-2)
    c.text(pad,179 if mobile else 209,"Minecraft worlds.",34 if mobile else 41,weight=500,spacing=-1)
    c.text(pad,220 if mobile else 260,"Real-world tools.",34 if mobile else 41,CYAN,weight=500,spacing=-1)
    if mobile:
        c.text(pad,262,"Systems, software, and interfaces",21,MUTED)
        c.text(pad,291,"with purpose.",21,MUTED)
        architecture(c,210,411,.85)
        c.line(pad,548,w-pad,548)
        c.text(pad,578,"JAVA / TYPESCRIPT",20,CYAN,cls="mono")
        c.text(pad,605,"JAVASCRIPT / BRAZIL",20,MUTED,cls="mono")
    else:
        c.text(pad,304,"Systems, software, and interfaces with purpose.",20,MUTED)
        c.rect(605,83,259,255,fill="url(#glass)",stroke="#263c53",radius=14)
        c.add('<defs><clipPath id="hero-art"><rect x="606" y="84" width="257" height="253" rx="13"/></clipPath></defs><g clip-path="url(#hero-art)">')
        architecture(c,734,201,.78)
        c.add('</g>')
        c.line(pad,354,w-pad,354)
        c.text(pad,391,"JAVA / TYPESCRIPT / JAVASCRIPT",16,CYAN,cls="mono")
        c.text(864,391,"BUILD. REFINE. REPEAT.",16,MUTED,cls="mono",anchor="end")
    return c.finish()


def metric_icon(c, x, y, index):
    c.add(f'<g transform="translate({x},{y})" fill="none" stroke="{CYAN}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">')
    icons=["M-7,-9 H5 L9,-5 V9 H-7 Z M5,-9 V-5 H9 M-3,-1 H5 M-3,3 H5", "M-8,-7 V6 Q-8,9 -5,9 H8 V-4 H-8 M-8,-7 H0 L3,-4", "M-10,1 H-6 L-2,-7 L2,8 L6,-2 H10", "M-8,-7 H8 V9 H-8 Z M-8,-2 H8 M-4,-10 V-5 M4,-10 V-5 M-4,3 H0"]
    c.add(f'<path d="{icons[index]}"/></g>')


def metrics(snapshot, mobile):
    c=Canvas(420 if mobile else 900,496 if mobile else 288,"GitHub at a glance", f"{snapshot['public_repos']} public repositories; {snapshot['original_repos']} original repositories excluding the profile; {snapshot['contributions']} profile contributions and {snapshot['active_days']} active days in the last 365 calendar days. Snapshot {snapshot['captured_at']}.")
    date=dt.date.fromisoformat(snapshot['calendar_end']).strftime('%d %b %Y').upper()
    c.text(26 if mobile else 36,47 if mobile else 43,"GitHub at a glance",28 if mobile else 26,weight=600)
    c.text(26 if mobile else 864,79 if mobile else 43,date+' / UTC',20 if mobile else 16,MUTED,cls='mono',anchor='start' if mobile else 'end')
    labels=[('public_repos','Public repos','Owned + forks'),('original_repos','Original repos','Excludes profile'),('contributions','Contributions','Past 365 days'),('active_days','Active days','Past 365 days')]
    for i,(key,label,sub) in enumerate(labels):
        x=26+i%2*192 if mobile else 36+i*212
        y=108+i//2*178 if mobile else 84
        width,height=(176,162) if mobile else (192,162)
        c.rect(x,y,width,height,fill='url(#glass)',stroke='url(#edge)',radius=10)
        metric_icon(c,x+width-24,y+25,i)
        c.text(x+16,y+65,pretty(snapshot[key]),40 if mobile else 45,weight=600,spacing=-1.7)
        c.text(x+16,y+105,label,20,weight=500)
        c.text(x+16,y+139,'Excl. profile' if mobile and key=='original_repos' else sub,20 if mobile else 16,MUTED)
    c.text(26 if mobile else 36,476 if mobile else 274,'Dated GitHub snapshot' if mobile else 'PUBLIC REPOSITORIES / PROFILE CONTRIBUTION CALENDAR',20 if mobile else 16,MUTED,cls='' if mobile else 'mono')
    return c.finish()


def chart_tile(c, x, y, size, color, future=False):
    """Depth is decorative; face color alone encodes the contribution bucket."""
    c.rect(x,y+2,size,size,fill="#050b14",stroke="none",radius=3)
    c.rect(x,y,size,size,fill=color,stroke=BORDER if future else "none",radius=3)
    if not future:
        c.line(x+3,y+1.5,x+size-3,y+1.5,"#d9f7ff",.8,'opacity=".18"')


def activity(snapshot, mobile):
    weeks=weekly_activity(snapshot)
    total=sum(w['count'] for w in weeks)
    peak=max(w['count'] for w in weeks)
    c=Canvas(420 if mobile else 900,504 if mobile else 428,"Weekly contribution totals",f"Twelve calendar weeks through {snapshot['calendar_end']}: {total} contributions. Columns only, with a linear zero-based scale. Current week is incomplete.")
    pad=26 if mobile else 36
    c.text(pad,47 if mobile else 43,"Weekly contributions",28 if mobile else 26,weight=600)
    c.text(pad,79 if mobile else 76,"12 weeks · current week in progress",20 if mobile else 18,MUTED)
    if mobile:
        c.text(pad,132,pretty(total),38,CYAN,weight=600,spacing=-1)
        c.text(394,132,"contributions",20,MUTED,anchor="end")
        c.rect(26,156,368,280,fill="url(#glass)",stroke="url(#edge)",radius=12)
        x,y,pw,ph=100,196,272,176
    else:
        c.text(864,76,pretty(total)+" contributions",23,CYAN,weight=600,anchor="end")
        c.rect(36,104,828,252,fill="url(#glass)",stroke="url(#edge)",radius=12)
        x,y,pw,ph=100,144,740,166
    cap=max(4,math.ceil(max(peak,1)/4)*4)
    for tick in range(5):
        gy=y+ph-ph*tick/4
        c.line(x,gy,x+pw,gy,"#30465f",.8,'stroke-dasharray="2 6"')
        value=round(cap*tick/4)
        label=f"{value/1000:.1f}k" if value>=1000 else str(value)
        c.text(x-12,gy+6,label,20 if mobile else 16,MUTED,anchor="end")
    for i,w in enumerate(weeks):
        bx=x+(i+.5)*pw/12;bh=ph*w['count']/cap;by=y+ph-bh;bw=14 if mobile else 30
        c.rect(bx-bw/2,by,bw,bh,fill="url(#bar)",stroke="none",radius=min(3,bh/2),extra=f'data-count="{w["count"]}" data-cap="{cap}" data-scale="{ph}"')
        if bh>0:
            c.rect(bx+bw/2-3,by,3,bh,fill="#0a2948",stroke="none",radius=0,extra='opacity=".3"')
            c.rect(bx-bw/2+2,by,bw-4,min(2,bh),fill="#b7f5ff",stroke="none",radius=1,extra='opacity=".65" class="soft"')
        if not mobile:
            c.text(bx,by-10,pretty(w['count']),16,CYAN if w['count']==peak else MUTED,anchor="middle")
        if not mobile or i in (0,5,11):
            c.text(x+pw if mobile and i==11 else bx,y+ph+32,w['date'].strftime('%d %b'),20 if mobile else 16,MUTED,anchor='end' if mobile and i==11 else 'middle')
    c.text(pad,474 if mobile else 398,'Peak week: '+pretty(peak)+' contributions',20 if mobile else 18,MUTED)
    return c.finish()


def calendar(snapshot, mobile):
    weeks=weekly_activity(snapshot)
    observed=[v for w in weeks for v in w['days'] if v is not None]
    active=sum(v>0 for v in observed)
    c=Canvas(420 if mobile else 900,440 if mobile else 420,"Daily contribution calendar",f"Daily contributions across twelve calendar weeks through {snapshot['calendar_end']}. {active} of {len(observed)} elapsed days have contributions. Future dates are unfilled. Color intensity uses a logarithmic scale.")
    pad=26 if mobile else 36
    c.text(pad,47 if mobile else 43,"Daily contribution map",27 if mobile else 26,weight=600)
    c.text(pad,79 if mobile else 76,"One tile per day · 12-week window",20 if mobile else 18,MUTED)
    if mobile:
        c.rect(26,104,368,258,fill="url(#glass)",stroke="url(#edge)",radius=12)
        hx,hy,step,cell=82,150,24,17
    else:
        c.rect(304,104,560,268,fill="url(#glass)",stroke="url(#edge)",radius=12)
        hx,hy,step,cell=392,152,36,26
        c.text(36,166,str(active),56,CYAN,weight=600,spacing=-1)
        c.text(36,201,"active days",22,MUTED)
        c.line(36,229,268,229)
        c.text(36,271,str(len(observed)),40,weight=600)
        c.text(36,305,"elapsed days",20,MUTED)
    maximum=max(observed+[1]);tones=["#20334a","#1c4f77","#2779a8","#35accd",CYAN]
    # Desktop uses shorter rows to keep its calendar compact.
    rowstep=24 if mobile else 25
    for wi,w in enumerate(weeks):
        for di,count in enumerate(w['days']):
            level=0 if not count else 1+min(3,int(math.log1p(count)/math.log1p(maximum)*3))
            chart_tile(c,hx+wi*step,hy+di*rowstep,cell if mobile else 19,NAVY if count is None else tones[level],count is None)
        if wi in ((0,5,11) if mobile else (0,4,8,11)):
            c.text(hx+wi*step+(cell/2),hy-18,w['date'].strftime('%d %b'),20 if mobile else 16,MUTED,anchor='middle')
    for di,label in enumerate(['Mon','Tue','Wed','Thu','Fri','Sat','Sun']):
        if not mobile or di in (0,2,4,6):c.text(hx-14,hy+di*rowstep+15,label,20 if mobile else 16,MUTED,anchor="end")
    ly=342 if mobile else 348
    c.text(hx,ly,"Less",20 if mobile else 16,MUTED)
    for i,tone in enumerate(tones):chart_tile(c,hx+51+i*21,ly-16,15,tone)
    c.text(hx+166,ly,"More",20 if mobile else 16,MUTED)
    if mobile:
        c.text(pad,394,f"{active} active / {len(observed)} elapsed days",20,MUTED)
        c.text(pad,422,"Future dates remain unfilled.",20,MUTED)
    else:
        c.text(pad,398,"COLOR INTENSITY / LOG SCALE · FUTURE DATES UNFILLED",16,MUTED,cls="mono")
    return c.finish()


def weekday_totals(snapshot):
    totals=[0]*7
    for day in snapshot['days']:
        totals[dt.date.fromisoformat(day['date']).weekday()]+=day['count']
    return totals


def weekdays(snapshot, mobile):
    totals=weekday_totals(snapshot);maximum=max(max(totals),1)
    cap=max(4,math.ceil(maximum/4)*4)
    c=Canvas(420 if mobile else 900,524 if mobile else 436,"Contributions by weekday","Contribution totals grouped by weekday across the same 365-day calendar as the headline metrics. "+'; '.join(f"{n}: {v}" for n,v in zip(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'],totals))+". Dot positions use a linear scale starting at zero; these are contributions, not hours worked.")
    pad=26 if mobile else 36
    c.text(pad,47 if mobile else 43,"Activity by weekday",28 if mobile else 26,weight=600)
    c.text(pad,79 if mobile else 76,"Contribution totals · past 365 days",20 if mobile else 18,MUTED)
    c.rect(pad,104,368 if mobile else 828,326 if mobile else 264,fill="url(#glass)",stroke="url(#edge)",radius=12)
    x,pw,first,step=(106,192,164,38) if mobile else (216,514,162,30)
    for fraction in [0,.5,1]:
        gx=x+fraction*pw
        c.line(gx,first-16,gx,first+6*step+14,"#30465f",.8,'stroke-dasharray="2 6"')
        v=round(cap*fraction);label=f'{v/1000:.1f}k' if v>=1000 else str(v)
        c.text(gx,132,label,20 if mobile else 16,MUTED,anchor='middle')
    names=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'] if mobile else ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    for i,(name,count) in enumerate(zip(names,totals)):
        yy=first+i*step;px=x+pw*count/cap
        c.text(46 if mobile else 56,yy+6,name,20,MUTED)
        c.line(x,yy,x+pw,yy,"#2a4058",1)
        c.circle(px,yy,6,fill='url(#sphere)',stroke='#b8f5ff',width=.8,extra=f'data-weekday="{i}" data-count="{count}" data-cap="{cap}"')
        c.text(374 if mobile else 840,yy+6,pretty(count),20,CYAN if count==max(totals) else MUTED,anchor='end')
    if mobile:
        c.text(pad,468,"Each dot = a weekday total.",20,MUTED)
        c.text(pad,499,"Contributions, not hours worked.",20,MUTED)
    else:
        c.text(pad,408,"ONE DOT PER WEEKDAY / CONTRIBUTIONS, NOT HOURS WORKED",16,MUTED,cls="mono")
    return c.finish()


def languages(snapshot, mobile):
    rows=language_shares(snapshot)
    c=Canvas(420 if mobile else 900,800 if mobile else 496,"Repository language mix","Language bytes from public original repositories, excluding this profile. "+'; '.join(f"{n}: {percent(v)}" for n,v in rows)+". Ring angles and bar lengths encode exact shares; motion is decorative.")
    pad=26 if mobile else 36
    c.text(pad,47 if mobile else 43,"Repository language mix",27 if mobile else 26,weight=600)
    c.text(pad,79 if mobile else 76,"Code bytes · public original repos" if mobile else "Share of code bytes · public original repositories",20 if mobile else 18,MUTED)
    if mobile:
        c.rect(26,104,368,258,fill="url(#glass)",stroke="url(#edge)",radius=12)
        cx,cy,radius=210,229,86
    else:
        c.rect(36,104,292,316,fill="url(#glass)",stroke="url(#edge)",radius=12)
        cx,cy,radius=182,254,94
    # Fixed circular data face; the lowered dark rim supplies depth without distorting angles.
    c.circle(cx,cy+7,radius,stroke="#050c16",width=30)
    c.circle(cx,cy,radius+21,stroke="#2d465e",width=1)
    c.circle(cx,cy,radius-21,fill="url(#glass)",stroke="#35536d",width=1)
    c.circle(cx,cy,radius,stroke="#172c43",width=26)
    length,offset=math.tau*radius,0
    for i,(_,share) in enumerate(rows):
        c.circle(cx,cy,radius,stroke=LANG_COLORS[i],width=26,extra=f'data-share="{share}" stroke-dasharray="{share*length:.6f} {length:.6f}" stroke-dashoffset="{-offset:.6f}" transform="rotate(-90 {cx} {cy})"')
        offset+=share*length
    c.add(f'<defs><mask id="ring-face"><circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="white" stroke-width="26"/></mask></defs>')
    c.circle(cx,cy,radius+14,fill="url(#polish)",stroke="none",extra='mask="url(#ring-face)" class="reveal"')
    c.circle(cx,cy,radius+14,stroke="#b9efff",width=.7,extra='opacity=".35"')
    # The orbit is outside the data ring, so its motion cannot imply changing shares.
    c.add(f'<g transform="translate({cx},{cy})"><g class="spin">')
    c.circle(0,0,radius+21,stroke=CYAN,width=2,extra=f'stroke-dasharray="30 {math.tau*(radius+21)-30}" opacity=".8"')
    c.add('</g></g>')
    leader,share=rows[0] if rows else ('No code',0)
    c.text(cx,cy-9,leader,22,MUTED,anchor="middle")
    c.text(cx,cy+32,percent(share),36,weight=600,anchor="middle",spacing=-1)
    if not mobile:c.text(cx,394,"LEADING LANGUAGE",16,MUTED,cls="mono",anchor="middle")
    for i,(name,share) in enumerate(rows):
        rx,ry,rw=(26,386+i*58,368) if mobile else (352,104+i*54,512)
        c.rect(rx,ry,rw,48 if mobile else 46,fill="url(#glass)",stroke="#263c53",radius=7)
        c.circle(rx+16,ry+18,4.5,fill=LANG_COLORS[i],stroke="none")
        c.text(rx+30,ry+25,name,20,weight=500)
        c.text(rx+rw-14,ry+25,percent(share),20,MUTED,anchor="end")
        bw=rw-28;by=ry+35
        c.rect(rx+14,by,bw,5,fill="#071322",stroke="none",radius=2)
        c.rect(rx+14,by,bw*share,5,fill=LANG_COLORS[i],stroke="none",radius=2,extra=f'data-language-share="{share}"')
        if share>0:c.rect(rx+14,by,bw*share,1.2,fill="#e0faff",stroke="none",radius=1,extra='opacity=".35"')
    c.text(pad,772 if mobile else 468,"Language share, not proficiency.",20 if mobile else 16,MUTED)
    return c.finish()


def project_art(c, kind, x, y, scale=1):
    c.add(f'<g transform="translate({x},{y}) scale({scale})">')
    c.add('<ellipse cx="0" cy="78" rx="110" ry="36" fill="url(#aura)"/>')
    if kind == 'servers':
        prism(c,-65,-65,-65,130,130,7,top="#0d2238",stroke="#2a526f")
        for z in [-38,5,48]:
            prism(c,-45,-45,z,90,90,27,top='url(#surface)',left='#12273d',right='#1b3b53',stroke='#4e7791')
            for v in [-21,-7,7,21]:
                c.line(*iso(-24,v,z+27.5),*iso(24,v,z+27.5),'#3f6680',1.1)
            for i in range(4):
                a=iso(-28+i*15,45,z+11);b=iso(-22+i*15,45,z+11)
                c.line(*a,*b,'#5883a0',3)
            for i in range(2):
                a=iso(45,-27+i*15,z+11)
                c.circle(*a,2.6,CYAN,'none',extra='class="soft"')
        for sign in [-1,1]:
            c.add(f'<path d="M{sign*80},-7 L{sign*105},8 V71 L{sign*35},112" fill="none" stroke="#2c5771" stroke-width="1.5"/>')
            c.add(f'<path d="M{sign*80},-7 L{sign*105},8 V71 L{sign*35},112" fill="none" stroke="{CYAN}" stroke-width="1.5" class="flow"/>')
    elif kind == 'companion':
        prism(c,-59,-45,-66,118,90,5,top='#102940',stroke='#36627f')
        c.add('<g class="float">')
        # One projection and shared coordinates keep all voxel faces aligned.
        for xx in [-24,3]:
            prism(c,xx,-13,-52,21,26,47,top='#315f86',left='#193a60',right='#25517b')
        prism(c,-26,-16,-4,52,32,52,top='#318caa',left='#176180',right='#248ca5',stroke='#6ab0c5')
        for xx in [-43,29]:
            prism(c,xx,-14,1,14,28,44,top='#397894',left='#254960',right='#35748a')
        prism(c,-24,-24,53,48,48,48,top='#2d5572',left='#1e3c57',right='#376984',stroke='#78b3c9')
        for xx in [-13,7]:
            polygon(c,[iso(xx,24,72),iso(xx+7,24,72),iso(xx+7,24,80),iso(xx,24,80)],CYAN,'none')
        c.add('</g>')
        c.add(f'<path d="M-95,-36 V-64 H-73 M73,72 H95 V44" fill="none" stroke="{CYAN}" stroke-width="1.5" opacity=".65"/>')
    elif kind == 'dashboard':
        c.rect(-88,-87,193,130,fill='#0c1b2e',stroke='#2e5876',radius=7)
        c.rect(-103,-69,193,142,fill='url(#surface)',stroke='#6594ae',radius=7)
        c.line(-102,-44,89,-44,'#547a94')
        for i in range(3): c.circle(-88+i*11,-56,2.5,CYAN if i==0 else '#47728f','none')
        c.rect(-93,-33,33,94,fill='#11283f',stroke='none',radius=3)
        for i in range(5): c.line(-85,-22+i*16,-70,-22+i*16,CYAN if i==0 else '#3a5e7b',2)
        for i in range(3):
            c.rect(-49+i*43,-33,35,26,fill='#183951',stroke='#365b76',radius=3)
            c.line(-41+i*43,-20,-27+i*43,-20,CYAN,3)
        c.rect(-49,4,121,57,fill='#10243b',stroke='#2d526c',radius=3)
        for i in range(3): c.line(-42,17+i*15,64,17+i*15,'#25435b')
        c.add(f'<path d="M-42,47 L-26,35 L-10,41 L6,23 L22,30 L38,13 L55,20 L64,11" fill="none" stroke="{CYAN}" stroke-width="2" stroke-linejoin="round"/>')
        c.circle(64,11,3,CYAN,'none',extra='class="soft"')
        c.add('<path d="M-21,74 V90 H21 V74 M-43,95 H43" fill="none" stroke="#537f9c" stroke-width="3"/>')
    else:
        c.add('<ellipse cx="0" cy="5" rx="106" ry="38" transform="rotate(-28)" fill="none" stroke="#305873"/>')
        c.add('<ellipse cx="0" cy="5" rx="106" ry="38" transform="rotate(55)" fill="none" stroke="#23415c"/>')
        nodes=[(-76,-46),(-10,-89),(76,-43),(-90,33),(-34,83),(57,64),(0,0),(95,22)]
        for a,b in [(0,1),(0,3),(0,6),(1,2),(1,6),(2,6),(2,7),(3,4),(3,6),(4,5),(4,6),(5,6),(5,7),(6,7)]:
            c.line(*nodes[a],*nodes[b],'#365d7b',1.2)
        for a,b in [(0,6),(6,5),(1,2)]: c.line(*nodes[a],*nodes[b],CYAN,1.7,'class="flow"')
        for i,(nx,ny) in enumerate(nodes):
            r=15 if i==6 else 7 if i%2 else 10
            c.circle(nx,ny,r+5,fill=CYAN,stroke='none',extra='opacity=".12" filter="url(#glow)"')
            c.circle(nx,ny,r,fill='url(#sphere)',stroke='#81d8ee',width=.7)
        c.circle(0,0,25,stroke=CYAN,extra='class="soft" opacity=".4"')
    c.add('</g>')


def project_card(config, project, mobile):
    title_lines=textwrap.wrap(project['title'],width=18) if len(project['title'])>20 else [project['title']]
    body_lines=textwrap.wrap(project['description'],width=35,break_long_words=False,break_on_hyphens=False)
    mobile_description_y=350+36*(len(title_lines)-1)
    mobile_tag_y=mobile_description_y+27*(len(body_lines)-1)+26
    c=Canvas(420 if mobile else 900,mobile_tag_y+56 if mobile else 300, project['title'],project['description']+' Built with '+', '.join(project['tags'])+'. Conceptual vector illustration; open the card to see the source repository.')
    pad=26 if mobile else 36
    c.text(pad,40,project['category'],20 if mobile else 16,CYAN,cls='mono')
    if mobile:
        c.rect(26,61,368,204,fill='url(#glass)',stroke='#294057',radius=10)
        project_art(c,project['visual'],210,163,.74)
        if len(project['title'])>20:
            for i,line in enumerate(textwrap.wrap(project['title'],width=18)):
                c.text(pad,309+i*36,line,31,weight=600,spacing=-.8)
            desc_y=mobile_description_y
        else:
            c.text(pad,309,project['title'],32,weight=600,spacing=-.8)
            desc_y=mobile_description_y
        c.lines(pad,desc_y,project['description'],35,20,27)
        ty=mobile_tag_y
    else:
        c.rect(601,60,263,210,fill='url(#glass)',stroke='#2c435a',radius=11)
        project_art(c,project['visual'],733,163,.75)
        c.text(pad,107,project['title'],35,weight=600,spacing=-1)
        c.lines(pad,149,project['description'],50,20,29)
        ty=237
        c.text(818,40,'SOURCE',16,MUTED,cls='mono',anchor='end')
        c.add(f'<path d="M844,42 L857,29 M845,29 H857 V41" fill="none" stroke="{CYAN}" stroke-width="1.5"/>')
    tx=pad
    for tag in project['tags']:
        width=len(tag)*(10 if mobile else 9)+26
        c.rect(tx,ty,width,30,fill='#102338',stroke='#29445c',radius=5)
        c.text(tx+13,ty+(23 if mobile else 21),tag,20 if mobile else 16,MUTED)
        tx+=width+9
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
    content = f'<a href="{href}">\n{html}\n</a>' if href else html
    return f'<p align="center">\n{content}\n</p>'


def render(snapshot, config):
    ASSETS.mkdir(exist_ok=True)
    all_assets = {}
    for mobile in [False, True]:
        variant = "mobile" if mobile else "wide"
        for name, builder in [("hero",lambda:hero(config,mobile)), ("metrics",lambda:metrics(snapshot,mobile)),
                              ("activity",lambda:activity(snapshot,mobile)), ("calendar",lambda:calendar(snapshot,mobile)),
                              ("weekdays",lambda:weekdays(snapshot,mobile)), ("languages",lambda:languages(snapshot,mobile)),
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
        picture("activity", "Weekly contribution totals: twelve columns on a linear scale. Current week is in progress.", config),
        picture("calendar", "Daily contribution calendar: one tile per day, with future dates unfilled.", config),
        picture("weekdays", "Contributions by weekday: seven dots comparing totals across the past 365 days.", config),
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
    details += ["", "| Weekday | Contributions (365 days) |", "| :--- | ---: |"]
    details += [f"| {name} | {pretty(value)} |" for name,value in zip(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'],weekday_totals(snapshot))]
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
    assert len(svg_paths) == (7+len(config["projects"]))*2
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
    assert readme.count('<source media="(max-width: 600px)"') == 7+len(config["projects"])
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
