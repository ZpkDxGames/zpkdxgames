#!/usr/bin/env python3
"""Build the responsive SVG visuals used by the ZpkDxGames profile README."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
CONFIG = ROOT / "config" / "profile.json"
UA = "zpkdxgames-responsive-profile/3.0"
WIDTH = 760


def log(message: str) -> None:
    print(message, file=sys.stderr)


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def write_asset(name: str, content: str) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    path = ASSETS / name
    path.write_text(content, encoding="utf-8")
    log(f"[write] assets/{name} ({len(content):,} bytes)")


def compact(value: int | None) -> str:
    if value is None:
        return "SYNCING"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M".replace(".0M", "M")
    if value >= 1_000:
        return f"{value / 1_000:.1f}k".replace(".0k", "k")
    return str(value)


def request_json(url: str, token: str | None, body: dict | None = None):
    headers = {
        "User-Agent": UA,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    try:
        request = urllib.request.Request(url, headers=headers, data=data)
        with urllib.request.urlopen(request, timeout=25) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:  # Graceful public-data fallback is intentional.
        log(f"[warn] {url}: {error}")
        return None


GRAPHQL = """
query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    createdAt
    contributionsCollection(from:$from,to:$to){
      totalCommitContributions
      contributionCalendar{
        totalContributions
        weeks{contributionDays{date contributionCount}}
      }
    }
  }
}
"""


def graphql(token: str | None, variables: dict):
    if not token:
        return None
    response = request_json(
        "https://api.github.com/graphql",
        token,
        {"query": GRAPHQL, "variables": variables},
    )
    if not response or response.get("errors"):
        if response and response.get("errors"):
            log(f"[warn] GraphQL: {response['errors']}")
        return None
    return response.get("data")


def collect_public_data(config: dict, offline: bool) -> dict:
    result = {
        "public_repos": None,
        "jvm_repos": None,
        "contributions": None,
        "commits_total": None,
        "streak": None,
        "weeks": [],
    }
    if offline:
        return result

    username = config["username"]
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    profile = request_json(f"https://api.github.com/users/{username}", token)
    if profile:
        result["public_repos"] = profile.get("public_repos")

    repositories = request_json(
        f"https://api.github.com/users/{username}/repos?per_page=100&type=owner",
        token,
    )
    if isinstance(repositories, list):
        excluded = {name.lower() for name in config.get("exclude_repos", [])}
        owned = [
            repo for repo in repositories
            if not repo.get("fork") and repo.get("name", "").lower() not in excluded
        ]
        result["jvm_repos"] = sum(
            1 for repo in owned if repo.get("language") in {"Java", "Kotlin"}
        )

    now = dt.datetime.now(dt.timezone.utc)
    year_start = now - dt.timedelta(days=364)
    current = graphql(
        token,
        {
            "login": username,
            "from": year_start.strftime("%Y-%m-%dT00:00:00Z"),
            "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
    if current and current.get("user"):
        collection = current["user"]["contributionsCollection"]
        calendar = collection["contributionCalendar"]
        result["contributions"] = calendar["totalContributions"]
        result["weeks"] = [
            sum(day["contributionCount"] for day in week["contributionDays"])
            for week in calendar["weeks"]
        ]

        days = [
            (day["date"], day["contributionCount"])
            for week in calendar["weeks"]
            for day in week["contributionDays"]
        ]
        days.sort()
        streak = 0
        for index, (_, count) in enumerate(reversed(days)):
            if count > 0:
                streak += 1
            elif index == 0:
                continue
            else:
                break
        result["streak"] = streak

        created_year = int(current["user"]["createdAt"][:4])
        commits_total = 0
        complete = True
        for year in range(created_year, now.year + 1):
            end = (
                f"{year}-12-31T23:59:59Z"
                if year < now.year
                else now.strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            yearly = graphql(
                token,
                {"login": username, "from": f"{year}-01-01T00:00:00Z", "to": end},
            )
            if not yearly or not yearly.get("user"):
                complete = False
                break
            commits_total += yearly["user"]["contributionsCollection"][
                "totalCommitContributions"
            ]
        if complete:
            result["commits_total"] = commits_total

    return result


def svg_start(height: int, label: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" width="{WIDTH}" height="{height}" role="img" aria-label="{escape(label, quote=True)}">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#101625"/><stop offset="1" stop-color="#080B12"/></linearGradient>
  <linearGradient id="signal" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#8B7CFF"/><stop offset="0.52" stop-color="#54D8E8"/><stop offset="1" stop-color="#67E8A5"/></linearGradient>
  <linearGradient id="cubeA" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#9B8FFF"/><stop offset="1" stop-color="#5E51D8"/></linearGradient>
  <linearGradient id="cubeB" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#70E6F0"/><stop offset="1" stop-color="#198CA0"/></linearGradient>
  <filter id="glow" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="160%"><feDropShadow dx="0" dy="12" stdDeviation="14" flood-color="#000" flood-opacity=".32"/></filter>
</defs>
<style>
  text{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
  .eyebrow{{font-size:18px;font-weight:700;letter-spacing:1.8px}}
  .title{{font-size:42px;font-weight:760;letter-spacing:-1.2px}}
  .section{{font-size:30px;font-weight:740;letter-spacing:-.5px}}
  .card-title{{font-size:26px;font-weight:720}}
  .body{{font-size:21px;font-weight:450}}
  .small{{font-size:18px;font-weight:650;letter-spacing:.8px}}
  .metric{{font-size:44px;font-weight:760;letter-spacing:-1px}}
  .float{{animation:float 6s ease-in-out infinite;transform-origin:center}}
  .pulse{{animation:pulse 3s ease-in-out infinite}}
  .dash{{stroke-dasharray:10 12;animation:dash 10s linear infinite}}
  .bar{{transform-box:fill-box;transform-origin:center bottom;animation:rise .85s cubic-bezier(.2,.75,.3,1) both}}
  @keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-9px)}}}}
  @keyframes pulse{{0%,100%{{opacity:.48}}50%{{opacity:1}}}}
  @keyframes dash{{to{{stroke-dashoffset:-220}}}}
  @keyframes rise{{from{{transform:scaleY(.08);opacity:.2}}to{{transform:scaleY(1);opacity:1}}}}
  @media(prefers-reduced-motion:reduce){{.float,.pulse,.dash,.bar{{animation:none!important}}}}
</style>
'''


def frame(height: int) -> str:
    return (
        f'<rect x="1" y="1" width="758" height="{height - 2}" rx="28" fill="url(#bg)" stroke="#26334A"/>'
        f'<path d="M30 {height - 28}H730" stroke="#26334A" stroke-width="2"/>'
        f'<path d="M30 {height - 28}H280" stroke="url(#signal)" stroke-width="3" class="dash"/>'
    )


def build_hero(config: dict, data: dict) -> str:
    repo_text = compact(data["public_repos"])
    parts = [svg_start(420, "ZpkDxGames — engineering reliable systems for persistent worlds"), frame(420)]
    parts += [
        '<circle cx="633" cy="118" r="112" fill="#8B7CFF" opacity=".08" filter="url(#glow)"/>',
        '<circle cx="566" cy="260" r="78" fill="#54D8E8" opacity=".06" filter="url(#glow)"/>',
        '<text x="44" y="58" class="eyebrow" fill="#54D8E8">' + escape(config["eyebrow"]) + '</text>',
        '<text x="44" y="126" class="title" fill="#F4F7FB">Reliable systems</text>',
        '<text x="44" y="180" class="title" fill="#F4F7FB">for persistent worlds.</text>',
        '<text x="44" y="232" class="body" fill="#A9B4C8">Gameplay engineering · resilient services</text>',
        '<text x="44" y="262" class="body" fill="#A9B4C8">Operator-first tooling · deliberate delivery</text>',
        '<rect x="44" y="306" width="222" height="50" rx="25" fill="#141D2E" stroke="#354664"/>',
        '<circle cx="70" cy="331" r="7" fill="#67E8A5" class="pulse" filter="url(#glow)"/>',
        '<text x="89" y="338" class="small" fill="#F4F7FB">' + repo_text + ' PUBLIC REPOSITORIES</text>',
        '<path d="M390 325C470 325 475 278 532 278" fill="none" stroke="#354664" stroke-width="2" class="dash"/>',
    ]

    # Abstract block-world core: recognizable, restrained, and decorative only.
    parts += [
        '<g class="float" filter="url(#shadow)">',
        '<path d="M560 78l72-38 72 38-72 39z" fill="url(#cubeA)"/>',
        '<path d="M560 78l72 39v78l-72-40z" fill="#5146B8"/>',
        '<path d="M704 78l-72 39v78l72-40z" fill="#342C7A"/>',
        '<path d="M524 184l58-31 58 31-58 32z" fill="url(#cubeB)"/>',
        '<path d="M524 184l58 32v64l-58-33z" fill="#197E91"/>',
        '<path d="M640 184l-58 32v64l58-33z" fill="#10515F"/>',
        '<path d="M620 236l43-23 43 23-43 24z" fill="#67E8A5"/>',
        '<path d="M620 236l43 24v48l-43-25z" fill="#318B64"/>',
        '<path d="M706 236l-43 24v48l43-25z" fill="#205C45"/>',
        '</g>',
        '<circle cx="632" cy="118" r="6" fill="#F4F7FB" class="pulse" filter="url(#glow)"/>',
        '<circle cx="582" cy="216" r="5" fill="#54D8E8" class="pulse" filter="url(#glow)"/>',
        '<circle cx="663" cy="260" r="5" fill="#67E8A5" class="pulse" filter="url(#glow)"/>',
        '<text x="716" y="384" text-anchor="end" class="small" fill="#69758A">BUILD · OBSERVE · ITERATE</text>',
        '</svg>',
    ]
    return "".join(parts)


def build_capabilities(config: dict) -> str:
    parts = [svg_start(690, "Engineering capabilities"), frame(690)]
    parts += [
        '<text x="42" y="58" class="eyebrow" fill="#8B7CFF">CAPABILITY MAP</text>',
        '<text x="42" y="99" class="section" fill="#F4F7FB">From player interaction</text>',
        '<text x="42" y="134" class="section" fill="#F4F7FB">to production recovery</text>',
    ]
    accents = ["#8B7CFF", "#54D8E8", "#67E8A5"]
    for index, capability in enumerate(config["capabilities"]):
        y = 160 + index * 154
        accent = accents[index]
        body_words = capability["body"].split()
        split = max(i for i in range(1, len(body_words)) if len(" ".join(body_words[:i])) <= 50)
        line_a = " ".join(body_words[:split])
        line_b = " ".join(body_words[split:])
        parts += [
            f'<rect x="42" y="{y}" width="676" height="132" rx="22" fill="#141D2E" stroke="#26334A"/>',
            f'<rect x="42" y="{y}" width="7" height="132" rx="3.5" fill="{accent}"/>',
            f'<rect x="66" y="{y + 24}" width="52" height="52" rx="16" fill="{accent}" opacity=".14" stroke="{accent}"/>',
            f'<text x="92" y="{y + 59}" text-anchor="middle" class="small" fill="{accent}">{escape(capability["number"])}</text>',
            f'<text x="138" y="{y + 43}" class="card-title" fill="#F4F7FB">{escape(capability["title"])}</text>',
            f'<text x="138" y="{y + 70}" class="body" fill="#A9B4C8">{escape(line_a)}</text>',
            f'<text x="138" y="{y + 96}" class="body" fill="#A9B4C8">{escape(line_b)}</text>',
            f'<text x="694" y="{y + 121}" text-anchor="end" class="small" fill="{accent}">{escape(capability["signal"])}</text>',
        ]
    parts += [
        '<path d="M92 236V314M92 390V468" stroke="url(#signal)" stroke-width="3" class="dash"/>',
        '<text x="42" y="662" class="small" fill="#69758A">CLEAR STATE · NARROW OWNERSHIP · USEFUL DIAGNOSTICS</text>',
        '</svg>',
    ]
    return "".join(parts)


def build_pulse(data: dict) -> str:
    metrics = [
        (compact(data["public_repos"]), "PUBLIC REPOSITORIES", "Owned public codebases", "#8B7CFF"),
        (compact(data["jvm_repos"]), "JVM REPOSITORIES", "Java and Kotlin codebases", "#54D8E8"),
        (compact(data["commits_total"]), "PUBLIC COMMITS", "Lifetime contribution history", "#67E8A5"),
        ((compact(data["streak"]) + "d") if data["streak"] is not None else "SYNCING", "CURRENT STREAK", "Consecutive active days", "#FFC857"),
    ]
    parts = [svg_start(500, "Live public engineering metrics"), frame(500)]
    parts += [
        '<text x="42" y="58" class="eyebrow" fill="#54D8E8">PUBLIC SIGNAL</text>',
        '<text x="42" y="99" class="section" fill="#F4F7FB">A readable snapshot,</text>',
        '<text x="42" y="134" class="section" fill="#F4F7FB">refreshed automatically</text>',
    ]
    for index, (value, label, detail, accent) in enumerate(metrics):
        col, row = index % 2, index // 2
        x = 42 + col * 344
        y = 157 + row * 142
        parts += [
            f'<rect x="{x}" y="{y}" width="330" height="122" rx="20" fill="#141D2E" stroke="#26334A"/>',
            f'<rect x="{x}" y="{y}" width="6" height="122" rx="3" fill="{accent}"/>',
            f'<circle cx="{x + 296}" cy="{y + 30}" r="7" fill="{accent}" class="pulse"/>',
            f'<text x="{x + 24}" y="{y + 39}" class="small" fill="{accent}">{label}</text>',
            f'<text x="{x + 24}" y="{y + 83}" class="metric" fill="#F4F7FB">{value}</text>',
            f'<text x="{x + 24}" y="{y + 108}" class="small" fill="#A9B4C8">{detail}</text>',
        ]
    parts += [
        '<text x="42" y="462" class="small" fill="#69758A">PUBLIC DATA · AUTOMATIC REFRESH · NO MANUAL COUNTERS</text>',
        '</svg>',
    ]
    return "".join(parts)


def build_activity(data: dict) -> str:
    weeks = list(data.get("weeks") or [])[-52:]
    has_data = bool(weeks)
    if not weeks:
        weeks = [0] * 52
    peak = max(weeks) or 1
    total = compact(data.get("contributions"))
    note = f"{total} PUBLIC CONTRIBUTIONS" if has_data else "PUBLIC SYNC PENDING"
    parts = [svg_start(310, "Twelve-month contribution rhythm"), frame(310)]
    parts += [
        '<text x="42" y="58" class="eyebrow" fill="#67E8A5">CONTRIBUTION RHYTHM</text>',
        f'<text x="716" y="58" text-anchor="end" class="small" fill="#54D8E8">{note}</text>',
        '<text x="42" y="101" class="section" fill="#F4F7FB">Twelve months of public momentum</text>',
        '<path d="M44 236H716" stroke="#26334A" stroke-width="2"/>',
    ]
    plot_x, plot_y, plot_w, plot_h = 44, 124, 672, 112
    gap = 4
    bar_w = (plot_w - gap * (len(weeks) - 1)) / len(weeks)
    for index, count in enumerate(weeks):
        height = 5 if not has_data else 8 + (count / peak) * (plot_h - 8)
        x = plot_x + index * (bar_w + gap)
        y = plot_y + plot_h - height
        ratio = count / peak if has_data else 0
        color = "#67E8A5" if ratio > 0.65 else "#54D8E8" if ratio > 0.25 else "#8B7CFF"
        opacity = 0.24 if not has_data else 0.38 + ratio * 0.62
        parts.append(
            f'<rect class="bar" x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{height:.2f}" rx="{bar_w / 2:.2f}" fill="{color}" opacity="{opacity:.2f}" style="animation-delay:{index * .018:.3f}s"/>'
        )
    parts += [
        '<text x="44" y="273" class="small" fill="#A9B4C8">52 WEEKS AGO</text>',
        '<text x="716" y="273" text-anchor="end" class="small" fill="#A9B4C8">NOW</text>',
        '</svg>',
    ]
    return "".join(parts)


def build_footer(config: dict) -> str:
    return "".join(
        [
            svg_start(128, "ZpkDxGames systems online"),
            '<rect x="1" y="1" width="758" height="126" rx="26" fill="url(#bg)" stroke="#26334A"/>',
            '<circle cx="48" cy="64" r="9" fill="#67E8A5" class="pulse" filter="url(#glow)"/>',
            '<text x="73" y="67" class="card-title" fill="#F4F7FB">Systems online</text>',
            '<text x="716" y="53" text-anchor="end" class="small" fill="#54D8E8">ZPKDXGAMES</text>',
            '<text x="716" y="94" text-anchor="end" class="small" fill="#A9B4C8">BUILD WITH INTENT · OPERATE WITH EVIDENCE</text>',
            '<path d="M34 112H726" stroke="url(#signal)" stroke-width="3" class="dash"/>',
            '</svg>',
        ]
    )


def build_all(offline: bool) -> None:
    config = load_config()
    data = collect_public_data(config, offline)
    write_asset("hero.svg", build_hero(config, data))
    write_asset("capabilities.svg", build_capabilities(config))
    write_asset("pulse.svg", build_pulse(data))
    write_asset("activity.svg", build_activity(data))
    write_asset("footer.svg", build_footer(config))


def validate() -> None:
    expected = {"hero.svg", "capabilities.svg", "pulse.svg", "activity.svg", "footer.svg"}
    actual = {path.name for path in ASSETS.glob("*.svg")}
    missing = expected - actual
    if missing:
        raise SystemExit(f"missing generated assets: {', '.join(sorted(missing))}")
    for name in sorted(expected):
        path = ASSETS / name
        ET.parse(path)
        source = path.read_text(encoding="utf-8")
        viewbox = re.search(r'viewBox="0 0 (\d+) (\d+)"', source)
        if not viewbox or int(viewbox.group(1)) != WIDTH:
            raise SystemExit(f"{name}: expected a {WIDTH}px-wide viewBox")
        small = [int(value) for value in re.findall(r'font-size:(\d+)px', source) if int(value) < 16]
        if small:
            raise SystemExit(f"{name}: font size below 16px: {small}")
    log(f"[ok] {len(expected)} responsive SVGs parsed and passed size checks")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="skip all network requests")
    parser.add_argument("--check", action="store_true", help="validate existing generated assets")
    args = parser.parse_args()
    if args.check:
        validate()
    else:
        build_all(args.offline)
        validate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
