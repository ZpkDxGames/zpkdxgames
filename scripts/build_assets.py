#!/usr/bin/env python3
"""
build_assets.py - generates every custom SVG used by the ZpkDxGames profile README.

Outputs (all written under ./assets, plus stubs under ./metrics):
  assets/header.svg            animated server-console banner (typewriter boot log, redstone circuits)
  assets/divider.svg           redstone wire divider with travelling pulse
  assets/section-<key>.svg     numbered section banners (from config/profile.json -> sections)
  assets/overview.svg          engineering pillars and animated delivery loop
  assets/stack.svg             compact engineering loadout rail
  assets/mc-stats.svg          live telemetry dashboard (GitHub GraphQL/REST + optional Modrinth/Spiget/bStats)
  assets/footer.svg            /tps style footer with build timestamp
  metrics/<name>.svg           live public-data fallbacks or intentional token-gated states

Standard library only (Python 3.9+). Network is optional: with --offline, or when an API call fails,
the dashboard degrades to "n/a" values instead of crashing.

Environment:
  GITHUB_TOKEN / GH_TOKEN   enables GraphQL (commit totals, heatmap, streak). REST works without it
                            (rate limited).
Usage:
  python3 scripts/build_assets.py              # normal run
  python3 scripts/build_assets.py --offline    # no network at all (used for the initial commit)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.request
from html import escape
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
UA = "zpkdxgames-profile-builder/2.1"
FONT = "ui-monospace, SFMono-Regular, 'JetBrains Mono', Menlo, Consolas, 'Liberation Mono', monospace"

METRIC_STUBS = [
    "isocalendar", "skyline", "languages", "habits",
    "activity", "achievements", "repositories", "lines", "snake",
]


_CLIP_N = 0


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


# --------------------------------------------------------------------------------------
# generic helpers
# --------------------------------------------------------------------------------------
def fmt(n) -> str:
    if n is None:
        return "n/a"
    n = float(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 10_000:
        return f"{n / 1000:.0f}k"
    if n >= 1000:
        return f"{n / 1000:.1f}k".replace(".0k", "k")
    return str(int(n))


def cw(size: float) -> float:
    """advance width of one monospace glyph"""
    return size * 0.602


def trunc(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def f4(x: float) -> str:
    return f"{x:.4f}".rstrip("0").rstrip(".") if "." in f"{x:.4f}" else f"{x:.4f}"


def fade_in(delay: float, dur: float = 0.5) -> str:
    """opacity 0 -> 1 after `delay` seconds. Base attribute stays 1 so non-SMIL renderers still show content."""
    total = delay + dur
    if delay <= 0:
        return f'<animate attributeName="opacity" values="0;1" dur="{dur}s" fill="freeze"/>'
    return (f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;{f4(delay / total)};1" '
            f'dur="{f4(total)}s" fill="freeze"/>')


def load_config() -> dict:
    with open(ROOT / "config" / "profile.json", "r", encoding="utf-8") as fh:
        return json.load(fh)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    log(f"[write] {path.relative_to(ROOT)} ({len(content):,} bytes)")


def svg_open(w: int, h: int, label: str, extra: str = "") -> str:
    attrs = f" {extra.strip()}" if extra.strip() else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{escape(label, quote=True)}"{attrs}>'
            f'<style>text{{font-family:{FONT};}}</style>')


# --------------------------------------------------------------------------------------
# network
# --------------------------------------------------------------------------------------
def http_json(url: str, headers: dict | None = None, body: dict | None = None, timeout: int = 25):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - we want to degrade gracefully on ANY failure
        log(f"[warn] {url} -> {exc}")
        return None


def gh_headers(token: str | None) -> dict:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def gh_rest(path: str, token: str | None):
    return http_json("https://api.github.com" + path, gh_headers(token))


def gh_graphql(query: str, variables: dict, token: str | None):
    if not token:
        return None
    res = http_json("https://api.github.com/graphql", gh_headers(token), {"query": query, "variables": variables})
    if res and res.get("errors"):
        log(f"[warn] graphql errors: {res['errors']}")
    return res.get("data") if res else None


GQL = """
query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    createdAt
    contributionsCollection(from:$from,to:$to){
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ date contributionCount contributionLevel } }
      }
    }
  }
}
"""

LEVELS = {"NONE": 0, "FIRST_QUARTER": 1, "SECOND_QUARTER": 2, "THIRD_QUARTER": 3, "FOURTH_QUARTER": 4}


def collect_github(cfg: dict, token: str | None, offline: bool) -> dict:
    out = {
        "ok": False, "followers": None, "public_repos": None, "stars": None, "forks": None,
        "plugin_repos": None, "jvm_repos": None, "top_repos": [], "commits_total": None, "commits_year": None,
        "prs_year": None, "streak_now": None, "streak_best": None, "contribs_year": None,
        "weeks": [], "events": [], "languages": [],
    }
    if offline:
        return out
    user = cfg["username"]
    tz = ZoneInfo(cfg.get("timezone", "UTC")) if ZoneInfo else dt.timezone.utc

    prof = gh_rest(f"/users/{user}", token)
    if prof:
        out["ok"] = True
        out["followers"] = prof.get("followers")
        out["public_repos"] = prof.get("public_repos")

    repos: list = []
    for page in range(1, 6):
        chunk = gh_rest(f"/users/{user}/repos?per_page=100&type=owner&sort=pushed&page={page}", token)
        if not chunk:
            break
        repos += chunk
        if len(chunk) < 100:
            break
    if repos:
        out["ok"] = True
        excl = {r.lower() for r in cfg.get("exclude_repos", [])}
        own = [r for r in repos if not r.get("fork") and r["name"].lower() not in excl]
        out["stars"] = sum(r.get("stargazers_count", 0) for r in own)
        out["forks"] = sum(r.get("forks_count", 0) for r in own)
        topics = {t.lower() for t in cfg.get("plugin_repo_topics", [])}
        hints = [h.lower() for h in cfg.get("plugin_repo_name_hints", [])]
        plugin_like = []
        for r in own:
            rt = {t.lower() for t in r.get("topics") or []}
            text = f"{r['name']} {r.get('description') or ''}".lower()
            by_topic = bool(rt & topics)
            by_hint = (r.get("language") in ("Java", "Kotlin")) and any(h in text for h in hints)
            if by_topic or by_hint:
                plugin_like.append(r)
        out["plugin_repos"] = len(plugin_like)
        out["jvm_repos"] = sum(1 for r in own if r.get("language") in ("Java", "Kotlin"))
        ranked = sorted(own, key=lambda r: (r.get("stargazers_count", 0), r.get("pushed_at") or ""), reverse=True)
        out["top_repos"] = [
            {
                "name": r["name"],
                "stars": r.get("stargazers_count", 0),
                "language": r.get("language") or "Other",
                "description": r.get("description") or "",
            }
            for r in ranked[:6]
        ]
        lang_counts: dict[str, int] = {}
        for repo in own:
            language = repo.get("language") or "Other"
            lang_counts[language] = lang_counts.get(language, 0) + 1
        out["languages"] = sorted(lang_counts.items(), key=lambda item: (-item[1], item[0]))

    now = dt.datetime.now(dt.timezone.utc)
    data = gh_graphql(GQL, {"login": user, "from": (now - dt.timedelta(days=364)).strftime("%Y-%m-%dT00:00:00Z"),
                            "to": now.strftime("%Y-%m-%dT%H:%M:%SZ")}, token)
    if data and data.get("user"):
        u = data["user"]
        cc = u["contributionsCollection"]
        out["commits_year"] = cc["totalCommitContributions"]
        out["prs_year"] = cc["totalPullRequestContributions"]
        cal = cc["contributionCalendar"]
        out["contribs_year"] = cal["totalContributions"]
        weeks = []
        flat = []
        for w in cal["weeks"]:
            col = []
            for d in w["contributionDays"]:
                col.append((d["date"], d["contributionCount"], LEVELS.get(d["contributionLevel"], 0)))
                flat.append((d["date"], d["contributionCount"]))
            weeks.append(col)
        out["weeks"] = weeks
        # streaks
        flat.sort()
        best = cur = 0
        for _, c in flat:
            cur = cur + 1 if c > 0 else 0
            best = max(best, cur)
        today = now.astimezone(tz).date().isoformat()
        tail = [c for d, c in flat if d <= today]
        streak = 0
        for i, c in enumerate(reversed(tail)):
            if c > 0:
                streak += 1
            elif i == 0:
                continue  # today may not have a contribution yet
            else:
                break
        out["streak_now"], out["streak_best"] = streak, best

        # lifetime commits: one query per calendar year since account creation
        created_year = int(u["createdAt"][:4])
        total = 0
        for yr in range(created_year, now.year + 1):
            y = gh_graphql(GQL, {"login": user, "from": f"{yr}-01-01T00:00:00Z",
                                 "to": f"{yr}-12-31T23:59:59Z" if yr < now.year else now.strftime("%Y-%m-%dT%H:%M:%SZ")}, token)
            if y and y.get("user"):
                total += y["user"]["contributionsCollection"]["totalCommitContributions"]
        out["commits_total"] = total

    ev = gh_rest(f"/users/{user}/events/public?per_page=40", token) or []
    lines = []
    for e in ev:
        t = e.get("type")
        repo = (e.get("repo", {}).get("name") or "").split("/")[-1]
        p = e.get("payload", {})
        when = dt.datetime.strptime(e["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).astimezone(tz)
        stamp = when.strftime("%m-%d %H:%M")
        if t == "PushEvent":
            n = p.get("size") or len(p.get("commits") or []) or 1
            lines.append((stamp, "PUSH", f"{repo} (+{n} commit{'s' if n != 1 else ''})"))
        elif t == "CreateEvent":
            lines.append((stamp, "CREATE", f"{p.get('ref_type', 'ref')} {repo}"))
        elif t == "PullRequestEvent":
            lines.append((stamp, "PR", f"{p.get('action', '')} #{p.get('number', '')} {repo}"))
        elif t == "IssuesEvent":
            lines.append((stamp, "ISSUE", f"{p.get('action', '')} {repo}"))
        elif t == "ReleaseEvent":
            lines.append((stamp, "RELEASE", f"{repo} {((p.get('release') or {}).get('tag_name') or '')}".strip()))
        elif t == "WatchEvent":
            lines.append((stamp, "STAR", repo))
        elif t == "ForkEvent":
            lines.append((stamp, "FORK", repo))
        if len(lines) >= 7:
            break
    out["events"] = lines
    return out


def collect_hosting(cfg: dict, offline: bool) -> dict:
    out = {"downloads": None, "servers": None, "players": None, "sources": []}
    if offline:
        return out
    h = cfg.get("hosting", {}) or {}
    dls = []
    mod = (h.get("modrinth_user") or "").strip()
    if mod:
        res = http_json(f"https://api.modrinth.com/v2/user/{mod}/projects")
        if isinstance(res, list):
            dls.append(sum(int(p.get("downloads", 0)) for p in res))
            out["sources"].append("modrinth")
    sp = h.get("spiget_author_id")
    if sp:
        res = http_json(f"https://api.spiget.org/v2/authors/{sp}/resources?size=100&fields=downloads")
        if isinstance(res, list):
            dls.append(sum(int(r.get("downloads", 0)) for r in res))
            out["sources"].append("spigot")
    if dls:
        out["downloads"] = sum(dls)
    servers = players = 0
    seen = False
    for pid in h.get("bstats_plugin_ids") or []:
        s = http_json(f"https://bstats.org/api/v1/plugins/{pid}/charts/servers/data/?maxElements=1")
        p = http_json(f"https://bstats.org/api/v1/plugins/{pid}/charts/players/data/?maxElements=1")
        if isinstance(s, list) and s:
            servers += int(s[-1][1])
            seen = True
        if isinstance(p, list) and p:
            players += int(p[-1][1])
            seen = True
    if seen:
        out["servers"], out["players"] = servers, players
        out["sources"].append("bstats")
    return out


# --------------------------------------------------------------------------------------
# svg builders
# --------------------------------------------------------------------------------------
def typed_line(x, y, text, t0, per_char, fill, size, total, last=False) -> str:
    """Typewriter line built from SMIL: a clip rect grows one glyph at a time and a block cursor follows it."""
    n = len(text)
    c = cw(size)
    global _CLIP_N
    _CLIP_N += 1
    cid = f"tw{_CLIP_N}"
    key_times = ["0"]
    widths = ["0"]
    cur_x = [f4(x)]
    for k in range(1, n + 1):
        key_times.append(f4((t0 + (k - 1) * per_char) / total))
        widths.append(f4(k * c))
        cur_x.append(f4(x + k * c))
    key_times.append("1")
    widths.append(f4(n * c))
    cur_x.append(f4(x + n * c))
    kt = ";".join(key_times)
    t_end = t0 + n * per_char
    ch = size * 1.25
    top = y - size * 0.95
    s = []
    s.append(f'<clipPath id="{cid}"><rect x="{x}" y="{f4(top)}" width="{f4(n * c)}" height="{f4(ch)}">'
             f'<animate attributeName="width" calcMode="discrete" values="{";".join(widths)}" keyTimes="{kt}" '
             f'dur="{f4(total)}s" fill="freeze"/></rect></clipPath>')
    s.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" clip-path="url(#{cid})" xml:space="preserve">{escape(text)}</text>')
    # cursor
    s.append(f'<rect x="{x}" y="{f4(top)}" width="{f4(c * 0.9)}" height="{f4(ch)}" fill="{fill}" opacity="0">'
             f'<animate attributeName="x" calcMode="discrete" values="{";".join(cur_x)}" keyTimes="{kt}" dur="{f4(total)}s" fill="freeze"/>')
    if last:
        s.append(f'<animate attributeName="opacity" calcMode="discrete" values="0;1" keyTimes="0;{f4(t0 / total)}" dur="{f4(total)}s" fill="freeze"/>')
        s.append(f'<animate attributeName="fill-opacity" calcMode="discrete" values="1;0" keyTimes="0;0.5" dur="1s" begin="{f4(t_end)}s" repeatCount="indefinite"/>')
    else:
        s.append(f'<animate attributeName="opacity" calcMode="discrete" values="0;1;0" keyTimes="0;{f4(t0 / total)};{f4(t_end / total)}" dur="{f4(total)}s" fill="freeze"/>')
    s.append('</rect>')
    return "".join(s)


def circuit(paths, P) -> str:
    out = []
    for i, (d, color, begin) in enumerate(paths):
        out.append(f'<path d="{d}" fill="none" stroke="#0e3b1f" stroke-width="3" stroke-linejoin="round" opacity=".9"/>')
        out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" '
                   f'stroke-dasharray="16 240" filter="url(#glow)">'
                   f'<animate attributeName="stroke-dashoffset" from="256" to="0" dur="{3 + i * 0.7:.1f}s" begin="{begin}s" repeatCount="indefinite"/></path>')
    return "".join(out)


def build_header(cfg: dict, P: dict) -> str:
    W, H = 1000, 280
    lines = cfg["boot_lines"]
    colors = [P["lime"], P["muted"], P["cyan"]]
    per_char, gap, t0 = 0.028, 0.35, 0.5
    starts, t = [], t0
    for ln in lines:
        starts.append(t)
        t += len(ln) * per_char + gap
    total = t + 1.0
    name = escape(cfg["display_name"])
    tagline = escape(cfg["tagline"])

    s = [svg_open(W, H, f"{cfg['display_name']} - {cfg['tagline']}")]
    s.append(f'''<defs>
<radialGradient id="gG" cx="12%" cy="0%" r="65%"><stop offset="0" stop-color="{P['emerald']}" stop-opacity=".20"/><stop offset="1" stop-color="{P['emerald']}" stop-opacity="0"/></radialGradient>
<radialGradient id="gC" cx="100%" cy="100%" r="65%"><stop offset="0" stop-color="{P['cyan']}" stop-opacity=".16"/><stop offset="1" stop-color="{P['cyan']}" stop-opacity="0"/></radialGradient>
<linearGradient id="nameG" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="{P['emerald']}"/><stop offset="1" stop-color="{P['cyan']}"/></linearGradient>
<linearGradient id="lineG" x1="0" x2="1"><stop offset="0" stop-color="{P['emerald']}"/><stop offset=".6" stop-color="{P['cyan']}"/><stop offset="1" stop-color="{P['cyan']}" stop-opacity="0"/></linearGradient>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="blur"><feGaussianBlur stdDeviation="9"/></filter>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{P['grid']}" stroke-width="1"/></pattern>
<clipPath id="round"><rect width="{W}" height="{H}" rx="14"/></clipPath>
</defs>''')
    s.append('<g clip-path="url(#round)">')
    s.append(f'<rect width="{W}" height="{H}" fill="{P["bg"]}"/>')
    s.append(f'<g><rect x="-40" y="-40" width="{W + 80}" height="{H + 80}" fill="url(#grid)"/>'
             f'<animateTransform attributeName="transform" type="translate" from="0 0" to="40 40" dur="10s" repeatCount="indefinite"/></g>')
    s.append(f'<rect width="{W}" height="{H}" fill="url(#gG)"/><rect width="{W}" height="{H}" fill="url(#gC)"/>')

    paths = [
        ("M1000 92H880V138H780V196H690", P["emerald"], 0.2),
        ("M1000 188H940V236H830V262H640", P["cyan"], 0.9),
        ("M740 56V108H660V160H596", P["emerald"], 1.6),
        ("M1000 250H968V280", P["redstone"], 2.1),
    ]
    s.append(circuit(paths, P))
    for (x, y, col) in [(880, 92, P["emerald"]), (780, 138, P["emerald"]), (690, 196, P["emerald"]), (940, 188, P["cyan"]),
                        (830, 236, P["cyan"]), (660, 108, P["emerald"]), (596, 160, P["emerald"])]:
        s.append(f'<rect x="{x - 4}" y="{y - 4}" width="8" height="8" fill="{P["bg"]}" stroke="{col}" stroke-width="1.5" opacity=".85"/>')

    # compact architecture map: enough structure to read as a systems dashboard without competing with the identity
    s.append(f'<text x="690" y="70" font-size="10.5" fill="{P["muted"]}" letter-spacing="2.2">RUNTIME TOPOLOGY</text>')
    nodes = [
        (690, 82, 112, "PAPER", P["emerald"]),
        (842, 82, 112, "PLUGINS", P["cyan"]),
        (690, 166, 112, "DATA", P["cyan"]),
        (842, 166, 112, "CI / CD", P["emerald"]),
    ]
    for i, (nx, ny, nw, label, col) in enumerate(nodes):
        s.append(f'<g>{fade_in(.35 + i * .12, .45)}'
                 f'<rect x="{nx}" y="{ny}" width="{nw}" height="28" rx="6" fill="{P["panel"]}" stroke="{col}" stroke-opacity=".45"/>'
                 f'<circle cx="{nx + 15}" cy="{ny + 14}" r="3.5" fill="{col}"><animate attributeName="opacity" values="1;.35;1" dur="{1.7 + i * .2:.1f}s" repeatCount="indefinite"/></circle>'
                 f'<text x="{nx + 27}" y="{ny + 18}" font-size="10.5" fill="{P["text"]}" letter-spacing="1.1">{label}</text></g>')
    s.append(f'<path d="M802 96H842M746 110V166M898 110V166M802 180H842" fill="none" stroke="{P["border"]}" stroke-width="2"/>')
    s.append(f'<circle r="3.5" fill="{P["cyan"]}" filter="url(#glow)"><animateMotion path="M802 96H842V180H802" dur="3.8s" repeatCount="indefinite"/></circle>')
    s.append(f'<rect x="0" y="40" width="1000" height="20" fill="{P["cyan"]}" opacity=".025">'
             f'<animate attributeName="y" values="40;260;40" dur="7s" repeatCount="indefinite"/></rect>')

    # window chrome
    s.append(f'<rect width="{W}" height="40" fill="{P["panel_alt"]}"/><rect y="40" width="{W}" height="1" fill="{P["border"]}"/>')
    for i, col in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        s.append(f'<circle cx="{26 + i * 20}" cy="20" r="6" fill="{col}" opacity=".9"/>')
    s.append(f'<text x="{W // 2}" y="25" font-size="12.5" fill="{P["muted"]}" text-anchor="middle" letter-spacing=".5">'
             f'{escape(cfg["username"].lower())}@server: ~/profile — java · spigot · paper</text>')
    px = W - 214
    s.append(f'<rect x="{px}" y="9" width="196" height="22" rx="11" fill="#0b2a17" stroke="{P["emerald"]}" stroke-opacity=".55"/>')
    s.append(f'<circle cx="{px + 18}" cy="20" r="4" fill="{P["emerald"]}"><animate attributeName="r" values="3.5;5.5;3.5" dur="1.6s" repeatCount="indefinite"/>'
             f'<animate attributeName="opacity" values="1;.35;1" dur="1.6s" repeatCount="indefinite"/></circle>')
    s.append(f'<text x="{px + 32}" y="24.5" font-size="12" font-weight="700" fill="{P["emerald"]}" letter-spacing="1.6">SERVER ONLINE</text>')

    # boot log
    size = 14
    for i, ln in enumerate(lines):
        s.append(typed_line(40, 78 + i * 24, ln, starts[i], per_char, colors[i % 3], size, total, last=(i == len(lines) - 1)))

    # name + tagline
    s.append(f'<text x="38" y="204" font-size="64" font-weight="800" fill="{P["emerald"]}" opacity=".55" filter="url(#blur)">{name}</text>')
    s.append(f'<text x="38" y="204" font-size="64" font-weight="800" fill="url(#nameG)" letter-spacing="-1">{name}'
             f'{fade_in(0.1, 0.8)}</text>')
    s.append(f'<text x="40" y="238" font-size="15" fill="{P["text"]}" letter-spacing=".35">{tagline}{fade_in(1.0, 0.8)}</text>')
    s.append(f'<rect x="40" y="258" width="520" height="2" fill="url(#lineG)"/>')
    s.append('</g>')
    s.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="none" stroke="{P["border"]}"/>')
    s.append('</svg>')
    return "".join(s)


def build_divider(P: dict) -> str:
    W, H = 1000, 28
    s = [svg_open(W, H, "divider")]
    s.append(f'<defs><filter id="glow" x="-50%" y="-200%" width="200%" height="500%"><feGaussianBlur stdDeviation="2.5" result="b"/>'
             f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>')
    s.append(f'<path d="M0 14H1000" stroke="{P["border"]}" stroke-width="2"/>')
    for i in range(0, 9):
        x = 62 + i * 109
        s.append(f'<rect x="{x - 4}" y="10" width="8" height="8" fill="{P["bg"]}" stroke="{P["gh_green"]}" stroke-width="1.5" opacity=".8"/>')
    s.append(f'<path d="M0 14H1000" stroke="{P["emerald"]}" stroke-width="2" stroke-dasharray="40 1000" filter="url(#glow)">'
             f'<animate attributeName="stroke-dashoffset" from="1040" to="0" dur="4s" repeatCount="indefinite"/></path>')
    s.append('</svg>')
    return "".join(s)


def build_section(sec: dict, P: dict) -> str:
    W, H = 1000, 64
    size = 14
    cmd = "$ " + sec["cmd"]
    x_end = W - 44
    x_cmd = x_end - len(cmd) * cw(size)
    s = [svg_open(W, H, f"{sec['index']} {sec['title']}")]
    s.append(f'<defs><linearGradient id="u" x1="0" x2="1"><stop offset="0" stop-color="{P["emerald"]}"/><stop offset=".55" stop-color="{P["cyan"]}" stop-opacity=".8"/>'
             f'<stop offset="1" stop-color="{P["cyan"]}" stop-opacity="0"/></linearGradient></defs>')
    s.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="{P["panel"]}" stroke="{P["border"]}"/>')
    s.append(f'<rect x="16" y="16" width="52" height="32" rx="6" fill="#06222a" stroke="{P["cyan"]}" stroke-opacity=".6"/>')
    s.append(f'<text x="42" y="37" font-size="15" font-weight="700" fill="{P["cyan"]}" text-anchor="middle">{escape(sec["index"])}</text>')
    s.append(f'<text x="86" y="41" font-size="24" font-weight="800" fill="{P["emerald"]}" letter-spacing="3">{escape(sec["title"])}</text>')
    s.append(f'<text x="{f4(x_cmd)}" y="38" font-size="{size}" fill="{P["muted"]}" xml:space="preserve">{escape(cmd)}</text>')
    s.append(f'<rect x="{f4(x_end + 3)}" y="26" width="8" height="15" fill="{P["emerald"]}">'
             f'<animate attributeName="fill-opacity" calcMode="discrete" values="1;0" keyTimes="0;.5" dur="1.1s" repeatCount="indefinite"/></rect>')
    s.append(f'<rect x="16" y="60" width="968" height="2" fill="url(#u)"/>')
    s.append('</svg>')
    return "".join(s)


def build_overview(cfg: dict, P: dict) -> str:
    W, H = 1000, 286
    s = [svg_open(W, H, "Engineering profile and delivery loop")]
    s.append(f'''<defs>
<linearGradient id="ovLine" x1="0" x2="1"><stop offset="0" stop-color="{P['emerald']}"/><stop offset=".55" stop-color="{P['cyan']}"/><stop offset="1" stop-color="{P['cyan']}" stop-opacity="0"/></linearGradient>
<filter id="ovGlow" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<pattern id="ovGrid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="{P['grid']}" stroke-width="1"/></pattern>
</defs>''')
    s.append(f'<rect width="{W}" height="{H}" rx="14" fill="{P["bg"]}"/>'
             f'<rect width="{W}" height="{H}" rx="14" fill="url(#ovGrid)" opacity=".35"/>'
             f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="none" stroke="{P["border"]}"/>')
    s.append(f'<text x="24" y="32" font-size="11" fill="{P["cyan"]}" letter-spacing="2.4">SYSTEM PROFILE</text>'
             f'<text x="145" y="32" font-size="11" fill="{P["muted"]}">// ENGINEERING OPERATING MODEL</text>')
    pillars = cfg.get("pillars") or []
    cols = [P["emerald"], P["cyan"], P["gold"]]
    for i, pillar in enumerate(pillars[:3]):
        x = 20 + i * 326
        col = cols[i]
        s.append(f'<g>{fade_in(.12 * i, .5)}'
                 f'<rect x="{x + .5}" y="50.5" width="306" height="112" rx="10" fill="{P["panel"]}" stroke="{P["border"]}"/>'
                 f'<rect x="{x + .5}" y="66" width="3" height="80" rx="1.5" fill="{col}"/>'
                 f'<text x="{x + 20}" y="77" font-size="10.5" fill="{col}" letter-spacing="1.8">0{i + 1} / {escape(pillar["title"])}</text>'
                 f'<text x="{x + 20}" y="108" font-size="18" font-weight="700" fill="{P["text"]}">{escape(pillar["subtitle"])}</text>'
                 f'<text x="{x + 20}" y="136" font-size="11.5" fill="{P["muted"]}">{escape(pillar["detail"])}</text>'
                 f'<rect x="{x + 264}" y="69" width="20" height="20" rx="4" fill="{col}" opacity=".08" stroke="{col}" stroke-opacity=".55"/>'
                 f'<path d="M{x + 270} 79h8M{x + 274} 75v8" stroke="{col}" stroke-width="1.5"/></g>')

    s.append(f'<text x="24" y="196" font-size="10.5" fill="{P["muted"]}" letter-spacing="2">DELIVERY LOOP</text>')
    stages = cfg.get("workflow") or ["DESIGN", "BUILD", "OBSERVE", "ITERATE"]
    base_x, y, step = 176, 182, 202
    s.append(f'<path d="M{base_x} {y + 28}H{base_x + step * (len(stages) - 1)}" stroke="{P["border"]}" stroke-width="2"/>')
    for i, stage in enumerate(stages):
        x = base_x + i * step
        col = P["emerald"] if i % 2 == 0 else P["cyan"]
        s.append(f'<g>{fade_in(.45 + i * .12, .45)}'
                 f'<circle cx="{x}" cy="{y + 28}" r="19" fill="{P["panel_alt"]}" stroke="{col}" stroke-opacity=".65"/>'
                 f'<text x="{x}" y="{y + 32}" text-anchor="middle" font-size="11" font-weight="700" fill="{col}">{i + 1:02d}</text>'
                 f'<text x="{x}" y="{y + 66}" text-anchor="middle" font-size="11.5" fill="{P["text"]}" letter-spacing="1.4">{escape(stage)}</text></g>')
    loop_end = base_x + step * (len(stages) - 1)
    s.append(f'<circle r="5" fill="{P["emerald"]}" filter="url(#ovGlow)"><animateMotion path="M{base_x} {y + 28}H{loop_end}" dur="3.2s" repeatCount="indefinite"/></circle>')
    s.append(f'<rect x="20" y="271" width="960" height="2" fill="url(#ovLine)"/>')
    s.append('</svg>')
    return "".join(s)


def build_stack(cfg: dict, P: dict) -> str:
    W = 1000
    size, ch, gap = 11.5, 28, 8
    items = cfg["stack"]
    cx, cy = 20, 42
    placed = []
    for i, it in enumerate(items):
        w = len(it) * cw(size) + 32
        if cx + w > W - 20:
            cx, cy = 20, cy + ch + gap
        placed.append((it, cx, cy, w, i))
        cx += w + gap
    H = cy + ch + 16
    s = [svg_open(W, int(H), "loadout")]
    s.append(f'<rect width="{W}" height="{H}" rx="12" fill="{P["panel_alt"]}"/>'
             f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="{P["border"]}"/>')
    s.append(f'<text x="20" y="24" font-size="10.5" fill="{P["cyan"]}" letter-spacing="2.1">ENGINEERING LOADOUT</text>'
             f'<text x="980" y="24" text-anchor="end" font-size="10.5" fill="{P["muted"]}">toolchain / runtime / delivery</text>')
    for it, px, py, w, i in placed:
        col = P["emerald"] if i % 2 == 0 else P["cyan"]
        s.append(f'<g>{fade_in(0.08 * i, 0.4)}'
                 f'<rect x="{f4(px + .5)}" y="{py + .5}" width="{f4(w)}" height="{ch}" rx="6" fill="{P["panel"]}" stroke="{col}" stroke-opacity=".45"/>'
                 f'<rect x="{f4(px + 10)}" y="{py + 10}" width="7" height="7" rx="1" fill="{col}" opacity=".9"/>'
                 f'<text x="{f4(px + 24)}" y="{py + 18.5}" font-size="{size}" fill="{P["text"]}">{escape(it)}</text></g>')
    s.append('</svg>')
    return "".join(s)


def pixel_icon(rows, x, y, cell, color) -> str:
    out = []
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "#":
                out.append(f'<rect x="{x + c * cell}" y="{y + r * cell}" width="{cell}" height="{cell}" fill="{color}"/>')
    return f'<g opacity=".85">{"".join(out)}</g>'


ICONS = {
    "plugin": ["..####..", ".######.", "########", "##.##.##", "##.##.##", "########", ".######.", "..####.."],
    "star": ["...##...", "...##...", "########", ".######.", "..####..", "..#..#..", ".##..##.", "........"],
    "commit": ["..#.....", "..#.....", ".####...", "##..##..", "##..##..", ".####...", "..#.....", "..#....."],
    "flame": ["...#....", "..##....", "..###.#.", ".#####.#", ".######.", ".######.", "..####..", "........"],
}


def card(x, y, w, h, label, value, sub, color, icon, P, delay) -> str:
    muted = value in ("n/a", "—")
    vcol = P["muted"] if muted else color
    return (f'<g>{fade_in(delay, 0.5)}'
            f'<rect x="{x + .5}" y="{y + .5}" width="{w}" height="{h}" rx="10" fill="{P["panel"]}" stroke="{P["border"]}"/>'
            f'<rect x="{x + .5}" y="{y + 14}" width="3" height="{h - 28}" rx="1.5" fill="{color}"/>'
            f'<text x="{x + 20}" y="{y + 30}" font-size="11" fill="{P["muted"]}" letter-spacing="1.8">{escape(label)}</text>'
            f'<text x="{x + 20}" y="{y + 76}" font-size="40" font-weight="800" fill="{vcol}">{escape(str(value))}</text>'
            f'<text x="{x + 20}" y="{y + 100}" font-size="12" fill="{P["muted"]}">{escape(trunc(sub, 27))}</text>'
            f'{pixel_icon(ICONS[icon], x + w - 44, y + 16, 3, color)}</g>')


def build_stats(cfg: dict, P: dict, gh: dict, host: dict, offline: bool, now: dt.datetime) -> str:
    W = 1000
    card_y, card_h, card_w = 62, 112, 225
    row2_y, row2_h = card_y + card_h + 20, 206
    row3_y = row2_y + row2_h + 20
    H = row3_y + 84 + 20
    live = gh["ok"] and not offline
    stamp = now.strftime("%Y-%m-%d %H:%M UTC")

    s = [svg_open(W, H, "Live telemetry dashboard")]
    s.append(f'<defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2" result="b"/>'
             f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
             f'<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="{P["grid"]}" stroke-width="1"/></pattern></defs>')
    s.append(f'<rect width="{W}" height="{H}" rx="14" fill="{P["bg"]}"/><rect width="{W}" height="{H}" rx="14" fill="url(#grid)" opacity=".55"/>')
    s.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="none" stroke="{P["border"]}"/>')

    # title bar
    s.append(f'<text x="24" y="38" font-size="15" font-weight="800" fill="{P["emerald"]}" letter-spacing="2.5">TELEMETRY</text>')
    s.append(f'<text x="136" y="38" font-size="12.5" fill="{P["muted"]}">// {escape(cfg["username"])} · synced {stamp}</text>')
    pill_col = P["emerald"] if live else P["gold"]
    pill_txt = "LIVE" if live else "OFFLINE SNAPSHOT"
    pw = len(pill_txt) * 8 + 40
    px = W - 24 - pw
    s.append(f'<rect x="{px}" y="20" width="{pw}" height="24" rx="12" fill="{P["panel_alt"]}" stroke="{pill_col}" stroke-opacity=".6"/>')
    s.append(f'<circle cx="{px + 17}" cy="32" r="4" fill="{pill_col}"><animate attributeName="opacity" values="1;.3;1" dur="1.6s" repeatCount="indefinite"/></circle>')
    s.append(f'<text x="{px + 30}" y="36.5" font-size="11.5" font-weight="700" fill="{pill_col}" letter-spacing="1.5">{pill_txt}</text>')

    # cards
    streak_val = "n/a" if gh["streak_now"] is None else f'{gh["streak_now"]}d'
    best = "n/a" if gh["streak_best"] is None else f'{gh["streak_best"]}d'
    pubs = "n/a" if gh["public_repos"] is None else str(gh["public_repos"])
    cards = [
        ("JVM REPOSITORIES", fmt(gh["jvm_repos"]), f"Java / Kotlin · {pubs} total", P["emerald"], "plugin"),
        ("PUBLIC STARS", fmt(gh["stars"]), f'{fmt(gh["forks"])} forks · {fmt(gh["followers"])} followers', P["gold"], "star"),
        ("COMMITS (ALL TIME)", fmt(gh["commits_total"]), f'{fmt(gh["commits_year"])} in last 12 months', P["cyan"], "commit"),
        ("CURRENT STREAK", streak_val, f"longest in 12 mo: {best}", P["lime"], "flame"),
    ]
    for i, (lab, val, sub, col, ic) in enumerate(cards):
        s.append(card(20 + i * (card_w + 20), card_y, card_w, card_h, lab, val, sub, col, ic, P, 0.1 * i))

    # heatmap panel
    hx, hy, hw = 20, row2_y, 470
    s.append(f'<rect x="{hx + .5}" y="{hy + .5}" width="{hw}" height="{row2_h}" rx="10" fill="{P["panel"]}" stroke="{P["border"]}"/>')
    s.append(f'<text x="{hx + 20}" y="{hy + 30}" font-size="11" fill="{P["muted"]}" letter-spacing="1.8">CONTRIBUTION HEATMAP · LAST 24 WEEKS</text>')
    shades = ["#161b22", "#0e4429", "#006d32", "#26a641", P["emerald"]]
    weeks = gh["weeks"][-24:] if gh["weeks"] else []
    gx, gy, step, cell = hx + 22, hy + 48, 17, 14
    total_cols = 24
    pad = total_cols - len(weeks)
    for ci in range(total_cols):
        col = weeks[ci - pad] if (weeks and ci >= pad) else None
        for ri in range(7):
            lvl = 0
            if col is not None and ri < len(col):
                lvl = col[ri][2]
            fill = shades[lvl]
            delay = 0.03 * ci
            dur = 0.4
            tot = delay + dur
            anim = (f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;{f4(delay / tot)};1" dur="{f4(tot)}s" fill="freeze"/>'
                    if delay > 0 else f'<animate attributeName="opacity" values="0;1" dur="{dur}s" fill="freeze"/>')
            extra = f' filter="url(#glow)"' if lvl == 4 else ""
            s.append(f'<rect x="{gx + ci * step}" y="{gy + ri * step}" width="{cell}" height="{cell}" rx="3" fill="{fill}"{extra}>{anim}</rect>')
    ly = hy + row2_h - 16
    s.append(f'<text x="{gx}" y="{ly}" font-size="10.5" fill="{P["muted"]}">less</text>')
    for i, c in enumerate(shades):
        s.append(f'<rect x="{gx + 34 + i * 17}" y="{ly - 10}" width="12" height="12" rx="3" fill="{c}"/>')
    s.append(f'<text x="{gx + 34 + 5 * 17 + 6}" y="{ly}" font-size="10.5" fill="{P["muted"]}">more</text>')
    if gh["contribs_year"] is not None:
        s.append(f'<text x="{hx + hw - 20}" y="{ly}" font-size="10.5" fill="{P["muted"]}" text-anchor="end">{gh["contribs_year"]} contributions / 12 mo</text>')
    elif not live:
        s.append(f'<text x="{hx + hw - 20}" y="{ly}" font-size="10.5" fill="{P["muted"]}" text-anchor="end">awaiting first sync</text>')

    # console panel
    cx0 = 510
    s.append(f'<rect x="{cx0 + .5}" y="{hy + .5}" width="{hw}" height="{row2_h}" rx="10" fill="{P["panel_alt"]}" stroke="{P["border"]}"/>')
    s.append(f'<text x="{cx0 + 20}" y="{hy + 30}" font-size="11" fill="{P["muted"]}" letter-spacing="1.8">SERVER LOG · latest.log</text>')
    events = gh["events"]
    if not events:
        events = [("--:--", "INFO", "awaiting first sync — run the profile-sync workflow")]
    lvl_col = {"PUSH": P["cyan"], "CREATE": P["lime"], "PR": P["emerald"], "ISSUE": P["gold"],
               "RELEASE": P["lime"], "STAR": P["gold"], "FORK": P["cyan"], "INFO": P["muted"]}
    size = 12.5
    for i, (stamp_l, tag, msg) in enumerate(events[:7]):
        yy = hy + 62 + i * 20
        s.append(f'<text x="{cx0 + 20}" y="{yy}" font-size="{size}" xml:space="preserve">{fade_in(0.15 * i + 0.3, 0.4)}'
                 f'<tspan fill="{P["muted"]}">[{escape(stamp_l)}]</tspan>'
                 f'<tspan fill="{lvl_col.get(tag, P["muted"])}" font-weight="700"> {escape(tag.ljust(7))}</tspan>'
                 f'<tspan fill="{P["text"]}"> {escape(trunc(msg, 34))}</tspan></text>')
    cur_y = hy + 62 + min(len(events), 7) * 20 - 11
    s.append(f'<text x="{cx0 + 20}" y="{hy + row2_h - 16}" font-size="{size}" fill="{P["emerald"]}">&gt;</text>'
             f'<rect x="{cx0 + 34}" y="{hy + row2_h - 27}" width="8" height="14" fill="{P["emerald"]}">'
             f'<animate attributeName="fill-opacity" calcMode="discrete" values="1;0" keyTimes="0;.5" dur="1.1s" repeatCount="indefinite"/></rect>')

    # hosting tiles
    tiles = [
        ("DOWNLOADS", host["downloads"], " + ".join(host["sources"][:2]) if host["downloads"] is not None else "set hosting ids in config/profile.json", P["emerald"]),
        ("SERVERS (bStats)", host["servers"], "servers running your plugins" if host["servers"] is not None else "add bstats_plugin_ids to enable", P["cyan"]),
        ("PLAYERS (bStats)", host["players"], "players on those servers" if host["players"] is not None else "add bstats_plugin_ids to enable", P["lime"]),
    ]
    for i, (lab, val, sub, col) in enumerate(tiles):
        tx = 20 + i * 330
        v = fmt(val)
        s.append(f'<g>{fade_in(0.2 * i + 0.5, 0.5)}'
                 f'<rect x="{tx + .5}" y="{row3_y + .5}" width="300" height="84" rx="10" fill="{P["panel"]}" stroke="{P["border"]}"/>'
                 f'<rect x="{tx + .5}" y="{row3_y + 14}" width="3" height="56" rx="1.5" fill="{col}"/>'
                 f'<text x="{tx + 20}" y="{row3_y + 28}" font-size="11" fill="{P["muted"]}" letter-spacing="1.8">{lab}</text>'
                 f'<text x="{tx + 20}" y="{row3_y + 62}" font-size="30" font-weight="800" fill="{P["muted"] if v == "n/a" else col}">{v}</text>'
                 f'<text x="{tx + 20}" y="{row3_y + 78}" font-size="11" fill="{P["muted"]}">{escape(trunc(sub, 38))}</text></g>')
    s.append('</svg>')
    return "".join(s)


def build_footer(cfg: dict, P: dict, now: dt.datetime) -> str:
    W, H = 1000, 118
    stamp = now.strftime("%Y-%m-%d %H:%M UTC")
    s = [svg_open(W, H, "footer")]
    s.append(f'<defs><filter id="glow" x="-50%" y="-200%" width="200%" height="500%"><feGaussianBlur stdDeviation="2.5" result="b"/>'
             f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>')
    s.append(f'<path d="M0 10H1000" stroke="{P["border"]}" stroke-width="2"/>')
    s.append(f'<path d="M0 10H1000" stroke="{P["emerald"]}" stroke-width="2" stroke-dasharray="40 1000" filter="url(#glow)">'
             f'<animate attributeName="stroke-dashoffset" from="1040" to="0" dur="5s" repeatCount="indefinite"/></path>')
    s.append(f'<text x="500" y="46" font-size="13" text-anchor="middle" fill="{P["emerald"]}" font-weight="700" letter-spacing="1.5">[ SERVER ONLINE ]</text>')
    s.append(f'<text x="500" y="68" font-size="12.5" text-anchor="middle" fill="{P["text"]}">TPS 20.0 (*) · MSPT 0.42 · no lag detected · tick-rate respected</text>')
    s.append(f'<text x="500" y="90" font-size="11.5" text-anchor="middle" fill="{P["muted"]}">assets regenerated {stamp} by profile-sync</text>')
    s.append(f'<text x="500" y="108" font-size="12.5" text-anchor="middle" fill="{P["cyan"]}">{escape(cfg["username"].lower())}@server:~$ '
             f'<tspan fill="{P["emerald"]}">▌<animate attributeName="fill-opacity" calcMode="discrete" values="1;0" keyTimes="0;.5" dur="1.1s" repeatCount="indefinite"/></tspan></text>')
    s.append('</svg>')
    return "".join(s)


def metric_shell(w: int, h: int, title: str, subtitle: str, P: dict, status: str = "PUBLIC DATA") -> list[str]:
    s = [svg_open(w, h, f"{title}: {subtitle}", 'data-fallback="true"')]
    s.append(f'''<defs>
<linearGradient id="mAccent" x1="0" x2="1"><stop offset="0" stop-color="{P['emerald']}"/><stop offset=".6" stop-color="{P['cyan']}"/><stop offset="1" stop-color="{P['cyan']}" stop-opacity="0"/></linearGradient>
<filter id="mGlow" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<pattern id="mGrid" width="28" height="28" patternUnits="userSpaceOnUse"><path d="M28 0H0V28" fill="none" stroke="{P['grid']}" stroke-width="1"/></pattern>
</defs>''')
    s.append(f'<rect width="{w}" height="{h}" rx="14" fill="{P["bg"]}"/>'
             f'<rect width="{w}" height="{h}" rx="14" fill="url(#mGrid)" opacity=".25"/>'
             f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="none" stroke="{P["border"]}"/>')
    s.append(f'<text x="20" y="28" font-size="11" font-weight="700" fill="{P["emerald"]}" letter-spacing="1.8">{escape(title)}</text>'
             f'<text x="20" y="46" font-size="9.5" fill="{P["muted"]}">{escape(subtitle)}</text>')
    pill_w = len(status) * 6.7 + 24
    s.append(f'<rect x="{w - pill_w - 16}" y="15" width="{pill_w}" height="22" rx="11" fill="{P["panel_alt"]}" stroke="{P["cyan"]}" stroke-opacity=".35"/>'
             f'<circle cx="{w - pill_w - 3}" cy="26" r="3" fill="{P["cyan"]}"><animate attributeName="opacity" values="1;.35;1" dur="1.8s" repeatCount="indefinite"/></circle>'
             f'<text x="{w - pill_w + 7}" y="29.5" font-size="8.5" fill="{P["cyan"]}" letter-spacing="1.1">{escape(status)}</text>')
    return s


def build_calendar_fallback(gh: dict, P: dict) -> str:
    W, H = 470, 250
    s = metric_shell(W, H, "CONTRIBUTION MATRIX", "52-week public activity surface", P)
    weeks = gh.get("weeks") or []
    weeks = weeks[-52:]
    shades = ["#161b22", "#0e4429", "#006d32", "#26a641", P["emerald"]]
    cell, gap, x0, y0 = 6, 1.5, 38, 74
    for ci in range(52):
        col = weeks[ci - (52 - len(weeks))] if weeks and ci >= 52 - len(weeks) else []
        for ri in range(7):
            lvl = col[ri][2] if ri < len(col) else 0
            delay = (ci + ri) * .006
            s.append(f'<rect x="{f4(x0 + ci * (cell + gap))}" y="{f4(y0 + ri * (cell + gap))}" width="{cell}" height="{cell}" rx="1.5" fill="{shades[lvl]}" opacity=".95">'
                     f'<animate attributeName="opacity" values=".15;.95" dur=".45s" begin="{f4(delay)}s" fill="freeze"/></rect>')
    total = fmt(gh.get("contribs_year"))
    commits = fmt(gh.get("commits_year"))
    s.append(f'<text x="38" y="154" font-size="9" fill="{P["muted"]}">LESS</text>')
    for i, col in enumerate(shades):
        s.append(f'<rect x="{75 + i * 15}" y="146" width="10" height="10" rx="2" fill="{col}"/>')
    s.append(f'<text x="154" y="154" font-size="9" fill="{P["muted"]}">MORE</text>')
    s.append(f'<rect x="24" y="178" width="196" height="48" rx="8" fill="{P["panel"]}" stroke="{P["border"]}"/>'
             f'<text x="38" y="198" font-size="9" fill="{P["muted"]}" letter-spacing="1.3">CONTRIBUTIONS</text>'
             f'<text x="38" y="217" font-size="17" font-weight="700" fill="{P["emerald"]}">{total}</text>'
             f'<rect x="250" y="178" width="196" height="48" rx="8" fill="{P["panel"]}" stroke="{P["border"]}"/>'
             f'<text x="264" y="198" font-size="9" fill="{P["muted"]}" letter-spacing="1.3">COMMITS / 12 MO</text>'
             f'<text x="264" y="217" font-size="17" font-weight="700" fill="{P["cyan"]}">{commits}</text>')
    s.append('</svg>')
    return "".join(s)


def build_skyline_fallback(gh: dict, P: dict) -> str:
    W, H = 470, 250
    s = metric_shell(W, H, "ACTIVITY SKYLINE", "24-week contribution velocity", P)
    weeks = (gh.get("weeks") or [])[-24:]
    totals = [sum(day[1] for day in week) for week in weeks]
    if len(totals) < 24:
        totals = [0] * (24 - len(totals)) + totals
    peak = max(totals) if totals and max(totals) else 1
    x0, floor, bw, gap = 28, 196, 12, 5.5
    points = []
    for i, val in enumerate(totals):
        height = 8 + (val / peak) * 108 if val else 5
        x = x0 + i * (bw + gap)
        y = floor - height
        col = P["emerald"] if i > 18 else P["cyan"]
        s.append(f'<rect x="{f4(x)}" y="{f4(y)}" width="{bw}" height="{f4(height)}" rx="2" fill="{col}" opacity=".28">'
                 f'<animate attributeName="y" from="{floor}" to="{f4(y)}" dur=".65s" begin="{f4(i * .025)}s" fill="freeze"/>'
                 f'<animate attributeName="height" from="0" to="{f4(height)}" dur=".65s" begin="{f4(i * .025)}s" fill="freeze"/></rect>')
        s.append(f'<rect x="{f4(x)}" y="{f4(y)}" width="{bw}" height="2" fill="{col}" filter="url(#mGlow)"/>')
        points.append(f"{f4(x + bw / 2)},{f4(y)}")
    s.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{P["cyan"]}" stroke-width="1.2" opacity=".5"/>')
    s.append(f'<path d="M24 {floor + 1}H446" stroke="{P["border"]}" stroke-width="1"/>'
             f'<text x="24" y="224" font-size="9" fill="{P["muted"]}">-24 WEEKS</text>'
             f'<text x="446" y="224" text-anchor="end" font-size="9" fill="{P["muted"]}">NOW</text>')
    s.append('</svg>')
    return "".join(s)


def build_repositories_fallback(gh: dict, P: dict) -> str:
    W, H = 900, 282
    s = metric_shell(W, H, "SELECTED REPOSITORIES", "Public portfolio ranked by stars and recency", P)
    repos = gh.get("top_repos") or []
    while len(repos) < 6:
        repos.append({"name": "Public repository", "stars": 0, "language": "—", "description": "Live repository data unavailable"})
    for i, repo in enumerate(repos[:6]):
        col, row = i % 2, i // 2
        x, y = 20 + col * 440, 64 + row * 67
        accent = P["emerald"] if i % 2 == 0 else P["cyan"]
        s.append(f'<g>{fade_in(.08 * i, .4)}'
                 f'<rect x="{x + .5}" y="{y + .5}" width="420" height="55" rx="8" fill="{P["panel"]}" stroke="{P["border"]}"/>'
                 f'<text x="{x + 16}" y="{y + 22}" font-size="12" font-weight="700" fill="{P["text"]}">{escape(trunc(repo["name"], 28))}</text>'
                 f'<text x="{x + 16}" y="{y + 41}" font-size="9.5" fill="{P["muted"]}">{escape(trunc(repo.get("description") or "Public project", 48))}</text>'
                 f'<circle cx="{x + 330}" cy="{y + 20}" r="3.5" fill="{accent}"/>'
                 f'<text x="{x + 340}" y="{y + 23}" font-size="9.5" fill="{P["muted"]}">{escape(repo.get("language") or "Other")}</text>'
                 f'<text x="{x + 404}" y="{y + 42}" text-anchor="end" font-size="10" fill="{P["gold"]}">★ {fmt(repo.get("stars"))}</text></g>')
    s.append('</svg>')
    return "".join(s)


def build_languages_fallback(gh: dict, P: dict) -> str:
    W, H = 470, 250
    s = metric_shell(W, H, "LANGUAGE FOOTPRINT", "Primary language across owned repositories", P)
    languages = (gh.get("languages") or [])[:6]
    if not languages:
        languages = [("No public data", 1)]
    peak = max(v for _, v in languages) or 1
    colors = [P["emerald"], P["cyan"], P["gold"], P["lime"], P["gh_green"], P["muted"]]
    for i, (name, value) in enumerate(languages):
        y = 76 + i * 27
        width = 250 * value / peak
        col = colors[i % len(colors)]
        s.append(f'<text x="24" y="{y + 10}" font-size="10.5" fill="{P["text"]}">{escape(name)}</text>'
                 f'<rect x="132" y="{y}" width="270" height="12" rx="6" fill="{P["panel"]}"/>'
                 f'<rect x="132" y="{y}" width="{f4(width)}" height="12" rx="6" fill="{col}" opacity=".75">'
                 f'<animate attributeName="width" from="0" to="{f4(width)}" dur=".7s" begin="{f4(.08 * i)}s" fill="freeze"/></rect>'
                 f'<text x="430" y="{y + 10}" text-anchor="end" font-size="9.5" fill="{P["muted"]}">{value} repos</text>')
    s.append('</svg>')
    return "".join(s)


def build_activity_fallback(gh: dict, P: dict) -> str:
    W, H = 900, 266
    s = metric_shell(W, H, "RECENT ACTIVITY", "Public GitHub event stream", P)
    events = gh.get("events") or [("--:--", "INFO", "No public activity available")]
    colors = {"PUSH": P["cyan"], "CREATE": P["lime"], "PR": P["emerald"], "ISSUE": P["gold"],
              "RELEASE": P["lime"], "STAR": P["gold"], "FORK": P["cyan"], "INFO": P["muted"]}
    x_line = 44
    s.append(f'<path d="M{x_line} 72V236" stroke="{P["border"]}" stroke-width="2"/>')
    for i, (stamp, tag, message) in enumerate(events[:5]):
        y = 76 + i * 34
        col = colors.get(tag, P["muted"])
        s.append(f'<g>{fade_in(.08 * i, .4)}'
                 f'<circle cx="{x_line}" cy="{y}" r="6" fill="{P["bg"]}" stroke="{col}" stroke-width="2"/>'
                 f'<circle cx="{x_line}" cy="{y}" r="2.5" fill="{col}"/>'
                 f'<text x="66" y="{y + 4}" font-size="10" fill="{P["muted"]}">[{escape(stamp)}]</text>'
                 f'<rect x="168" y="{y - 10}" width="74" height="20" rx="5" fill="{P["panel"]}" stroke="{col}" stroke-opacity=".4"/>'
                 f'<text x="205" y="{y + 4}" text-anchor="middle" font-size="9.5" font-weight="700" fill="{col}">{escape(tag)}</text>'
                 f'<text x="260" y="{y + 4}" font-size="11" fill="{P["text"]}">{escape(trunc(message, 72))}</text></g>')
    s.append(f'<circle r="4" fill="{P["cyan"]}" filter="url(#mGlow)"><animateMotion path="M{x_line} 72V236" dur="3s" repeatCount="indefinite"/></circle>')
    s.append('</svg>')
    return "".join(s)


def build_locked_fallback(name: str, P: dict) -> str:
    W, H = 470, 230
    detail = {
        "habits": ("CODING RHYTHM", "30-day hourly and weekday patterns"),
        "lines": ("CHANGE VOLUME", "Repository additions and removals"),
        "achievements": ("ENGINEERING SIGNALS", "Achievement classification and milestones"),
        "snake": ("CONTRIBUTION FLOW", "Animated contribution path"),
    }.get(name, (name.upper(), "Extended analytics channel"))
    s = metric_shell(W, H, detail[0], detail[1], P, "OPTIONAL CHANNEL")
    # Deliberately designed data-channel state, not a blank placeholder.
    for i, height in enumerate([28, 54, 38, 78, 48, 92, 64, 104, 70, 118, 84, 98]):
        x = 28 + i * 29
        y = 172 - height
        col = P["emerald"] if i % 3 else P["cyan"]
        s.append(f'<rect x="{x}" y="{y}" width="14" height="{height}" rx="3" fill="{col}" opacity=".12"/>'
                 f'<rect x="{x}" y="{y}" width="14" height="2" fill="{col}" opacity=".45"/>')
    s.append(f'<rect x="24" y="184" width="422" height="28" rx="7" fill="{P["panel"]}" stroke="{P["border"]}"/>'
             f'<text x="235" y="202" text-anchor="middle" font-size="9.5" fill="{P["muted"]}" letter-spacing=".4">ADD METRICS_TOKEN TO ENABLE THE DEEP-DIVE RENDER</text>')
    s.append('</svg>')
    return "".join(s)


def build_metric_fallback(name: str, gh: dict, P: dict) -> str:
    builders = {
        "isocalendar": build_calendar_fallback,
        "skyline": build_skyline_fallback,
        "repositories": build_repositories_fallback,
        "languages": build_languages_fallback,
        "activity": build_activity_fallback,
    }
    if name in builders:
        return builders[name](gh, P)
    return build_locked_fallback(name, P)


def should_refresh_fallback(path: Path) -> bool:
    if not path.exists():
        return True
    try:
        head = path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001 - unreadable placeholder should be replaced
        return True
    return "AWAITING FIRST SYNC" in head or 'data-fallback="true"' in head


# --------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="never touch the network")
    ap.add_argument("--token", default=os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"))
    args = ap.parse_args()

    cfg = load_config()
    P = cfg["palette"]
    now = dt.datetime.now(dt.timezone.utc)

    gh = collect_github(cfg, args.token, args.offline)
    host = collect_hosting(cfg, args.offline)

    A = ROOT / "assets"
    write(A / "header.svg", build_header(cfg, P))
    write(A / "divider.svg", build_divider(P))
    for sec in cfg["sections"]:
        write(A / f"section-{sec['key']}.svg", build_section(sec, P))
    write(A / "overview.svg", build_overview(cfg, P))
    write(A / "stack.svg", build_stack(cfg, P))
    write(A / "mc-stats.svg", build_stats(cfg, P, gh, host, args.offline, now))
    write(A / "footer.svg", build_footer(cfg, P, now))

    for name in METRIC_STUBS:
        p = ROOT / "metrics" / f"{name}.svg"
        if should_refresh_fallback(p):
            write(p, build_metric_fallback(name, gh, P))
    log("[done]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
