"""Conceptual static illustrations plus measured project vitals."""

from html import escape
from .draw import text, rect, path, dot, shell
from .editorial import FEATURED
from .model import latest_stable, primary_language


def concept(kind):
    """Art uses no made-up statuses, counts, telemetry, or product screenshots."""
    b = ""
    if kind == "panel":
        for x, y, label in ((36, 62, 'PAPER'), (204, 80, 'HOST'), (366, 54, 'WEB')):
            b += rect(x, y, 96, 62, "surface", 8, True)
            b += text(x+48, y+37, label, 14, "violet", 650, "middle")
        b += path("M132 93H174V111H204M300 111H331V85H366", "cyan", 2)
        b += dot(174, 93, "cyan", 4)+dot(331, 111, "cyan", 4)
    elif kind == "tools":
        b += path("M145 133L208 63", "violet", 13, 'stroke-linecap="square"')
        b += '<path d="M171 49H223L251 77V96L209 66H179Z" fill="var(--surface)" stroke="var(--cyan)" stroke-width="3"/>'
        b += path("M285 54H431M285 90H393M285 126H357", "border", 3)
        for x, y in ((283,54), (283,90), (283,126)):
            b += rect(x, y-7, 14, 14, "violet", 3)
    elif kind == "quests":
        b += path("M89 91H410", "cyan", 2)
        for i, label in enumerate(('CHOOSE', 'PLAY', 'CLAIM')):
            x = 47+i*151
            b += rect(x, 61, 103, 63, "surface", 8, True)
            b += text(x+52, 99, label, 13, "violet", 650, "middle")
    elif kind == "chats":
        for x, y, color in ((73,54,'violet'), (219,76,'cyan'), (336,48,'violet')):
            b += f'<path d="M{x} {y}h93v53h-43l-17 16v-16h-33Z" fill="var(--surface)" stroke="var(--{color})" stroke-width="2"/>'
            b += path(f"M{x+18} {y+19}h56M{x+18} {y+34}h35", color, 2)
    elif kind == "companion":
        b += '<g stroke="var(--violet)" stroke-width="2"><path d="M206 40h49v43h-49Z" fill="var(--surface)"/><path d="M196 83h69v59h-69Z" fill="var(--surface)"/><path d="M180 84h16v45h-16ZM265 84h16v45h-16Z" fill="var(--surface-2)"/></g>'
        b += rect(216, 57, 6, 6, "cyan", 0)+rect(238, 57, 6, 6, "cyan", 0)
        b += path("M322 53v31m-9-21 9-10 9 10M344 107h43M108 90h35", "cyan", 2)
        b += path("M323 90v43M111 57v19M102 66h19", "border", 2)
    else:
        b += rect(196, 74, 108, 58, "surface", 8, True)
        b += text(250, 109, "CORE", 17, "violet", 650, "middle")
        for x, y in ((95,54), (357,54), (95,116), (357,116)):
            b += rect(x, y, 49, 28, "surface-2", 5, True)
            b += path(f"M{144 if x==95 else 357} {y+14}H{175 if x==95 else 327}V103H{196 if x==95 else 304}", "cyan", 2)
            b += dot(x+24, y+14, "violet", 4)
    return b


def card(data, theme, kind, project_name, category, mobile=False):
    project = next((p for p in data["projects"] if p["name"] == project_name), None)
    stable = latest_stable(data).get(project_name)
    version = stable["version"] if stable else "—"
    commits = str(project["commits"]) if project else "—"
    language = primary_language(project)
    w, h = (240, 286) if mobile else (500, 256)
    if mobile:
        body = text(16, 25, "CONCEPTUAL STUDY", 12, "text-muted", 550, extra='letter-spacing=".7"')
        body += f'<g transform="translate(0 13) scale(.48)">{concept(kind)}</g>'
        body += path("M16 98H224")
        for y, label, value in ((127,'Stable¹',version), (169,'Commits²',commits), (211,'Lang.',language)):
            body += text(16, y, label, 19, "text-muted")
            body += text(224, y, value, 22, "violet" if label=='Commits²' else 'text', 650, 'end', max_width=123)
        body += text(16, 252, "¹ In window · ² 90 days", 13, "text-muted")
        body += text(16, 273, data["as_of"], 16, "text-muted")
    else:
        body = text(20, 27, category, 13, "violet", 650, extra='letter-spacing="1.4"')
        body += text(480, 27, "CONCEPTUAL", 12, "text-muted", 500, "end")
        body += concept(kind)
        body += path("M20 156H480")
        for x, label, val, color in ((20,'STABLE¹',version,'text'), (181,'COMMITS²',commits,'violet'), (341,'LANGUAGE',language,'text')):
            body += text(x, 184, label, 13, "text-muted", 500)
            body += text(x, 214, val, 24 if label!='LANGUAGE' else 19, color, 650, max_width=139)
        body += text(20, 242, "¹ In snapshot window · ² Project-wide, 90 days", 12, "text-muted")
        body += text(480, 242, data["as_of"], 12, "text-muted", anchor="end")
    desc = (f"Conceptual illustration for {project_name}, not a screenshot. As of {data['as_of']}, "
            f"latest stable in the 90-day snapshot window: {version}; project-wide commits: {commits}; "
            f"primary source language by byte volume: {language}. Not proficiency or production-readiness evidence.")
    return shell(theme, w, h, project_name+" — conceptual illustration and measured vitals", desc, body)
