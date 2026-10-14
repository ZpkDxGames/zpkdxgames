"""Small SVG primitives with concrete colours and static final geometry."""

from html import escape
import json
from pathlib import Path
import textwrap
from .tokens import THEMES, MOTION


def text(x, y, value, size=18, fill="text", weight=400, anchor="start", extra="", max_width=None):
    value = str(value)
    if max_width and len(value)*size*.57 > max_width:
        size = max(11, min(size, max_width / (max(1, len(value))*.57)))
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size:.2f}" font-weight="{weight}" '
            f'fill="var(--{fill})" text-anchor="{anchor}" {extra}>{escape(value)}</text>')


def lines(x, y, value, size=17, fill="text-muted", max_chars=60, line_height=24, weight=400):
    return "".join(text(x, y+i*line_height, line, size, fill, weight)
                   for i, line in enumerate(textwrap.wrap(value, max_chars, break_long_words=False)))


def rect(x, y, width, height, fill="surface", radius=12, stroke=False, extra=""):
    return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(0,width):.2f}" height="{height:.2f}" '
            f'rx="{radius}" fill="var(--{fill})" '
            + ('stroke="var(--border)" ' if stroke else '') + f'{extra}/>')


def path(d, stroke="border", width=1, extra=""):
    return f'<path d="{d}" fill="none" stroke="var(--{stroke})" stroke-width="{width}" {extra}/>'


def dot(x, y, fill="violet", r=4, extra=""):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="var(--{fill})" {extra}/>'


def display_text(x, baseline, value, size, fill="text"):
    """Pre-extracted DejaVu Sans Bold outlines; generator needs only stdlib."""
    data = json.loads((Path(__file__).parent/"lettering.json").read_text())
    factor = size/data["units_per_em"]
    offset = 0
    body = f'<g fill="var(--{fill})" aria-label="{escape(value)}">'
    for char in value:
        advance, d = data["glyphs"][char]
        if d:
            body += f'<path d="{d}" transform="translate({x+offset:.3f} {baseline:.3f}) scale({factor:.6f} {-factor:.6f})"/>'
        offset += advance*factor
    return body+"</g>"


def shell(theme, width, height, title, description, body, draw_length=1000):
    t = THEMES[theme]
    m = MOTION
    css = f'''svg{{font-family:"Inter","Segoe UI",system-ui,-apple-system,sans-serif}}
    .reveal{{animation:reveal {m['reveal_ms']}ms {m['easing']} both}}
    .grow{{transform-box:fill-box;transform-origin:left center;animation:grow {m['reveal_ms']}ms {m['easing']} both}}
    .bar-y{{transform-box:fill-box;transform-origin:center bottom;animation:bar-y {m['reveal_ms']}ms {m['easing']} both}}
    .draw{{stroke-dasharray:{draw_length:.2f};stroke-dashoffset:0;animation:draw {m['reveal_ms']}ms {m['easing']} both}}
    .signal{{stroke-dasharray:40 340;animation:signal {m['ambient_s']}s linear infinite}}
    @keyframes reveal{{from{{opacity:0}}to{{opacity:1}}}}
    @keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
    @keyframes bar-y{{from{{transform:scaleY(0)}}to{{transform:scaleY(1)}}}}
    @keyframes draw{{from{{stroke-dashoffset:{draw_length:.2f}}}to{{stroke-dashoffset:0}}}}
    @keyframes signal{{to{{stroke-dashoffset:-760}}}}
    @media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.draw{{stroke-dashoffset:0!important}}}}
    '''
    doc = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title>
<desc id="desc">{escape(description)}</desc>
<style>{css}</style>
<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="16" fill="{t['bg']}" stroke="{t['border']}"/>
{body}
</svg>
'''
    for key, val in t.items():
        doc = doc.replace(f"var(--{key})", val)
    return "\n".join(line.rstrip() for line in doc.splitlines())+"\n"


def heading(data, width, eyebrow, title, mobile=False, subtitle=None):
    body = text(28, 35, eyebrow.upper(), 14 if not mobile else 16, "violet", 650,
                extra='letter-spacing="1.8"')
    body += text(28, 76, title, 29 if not mobile else 27, weight=650)
    if mobile:
        body += text(28, 103, "AS OF "+data["as_of"], 16, "text-muted")
        if subtitle:
            body += text(28, 132, subtitle, 17, "text-muted")
    else:
        body += text(width-28, 35, "AS OF "+data["as_of"], 14, "text-muted", anchor="end")
        if subtitle:
            body += text(28, 105, subtitle, 17, "text-muted")
    return body


def footer(data, y, mobile=False, kind="commits"):
    body = text(28, y, f"{data['start']} → {data['as_of']} · 90 UTC days", 17 if mobile else 14, "text-muted")
    if kind == "commits":
        label = "Project commits, not personal contributions."
    elif kind == "languages":
        label = "Source volume, not proficiency or time spent."
    else:
        label = "Published releases; production readiness varies."
    body += text(28, y+25 if mobile else y+23, label, 16 if mobile else 14, "text-muted")
    return body


def stagger(index):
    return f'style="animation-delay:{min(index*MOTION["stagger_ms"],MOTION["max_stagger_ms"])}ms"'
