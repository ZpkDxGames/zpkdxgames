from html import escape
from ..draw import svg_shell
from ..tokens import THEMES

GROUPS=[
('RUNTIME / SHARED',['PlexonCore','PlexonUtility']),
('OPERATIONS',['PlexonPanel','PlexonPanel-Dashboard']),
('PROGRESSION',['PlexonTools','PlexonQuests','PlexonRanks','PlexonSkills']),
('REWARDS / ITEMS',['Plexon-DailyRewards','PlexonCrates','PlexonKeys','PlexonSpawners','PlexonBackpacks','PlexonBlacksmith']),
('COMMUNICATION',['PlexonChats']),
('ECONOMY / JOBS',['PlexonJobs','PlexonShops']),
('WORLD / TRAVEL',['PlexonHomes','PlexonTravel']),
('CLAIM POLICY',['PlexonGPFlags','PlexonGriefPreventionAddon'])]

def ecosystem(snapshot,editorial,theme='dark',mobile=False):
    c=THEMES[theme]; w=500 if mobile else 1000
    available={p['name'] for p in snapshot['projects']}; history=editorial.get('history',{})
    if mobile:
        counts=[len([n for n in names if n in available]) for _,names in GROUPS]
        h=116+sum(46+n*34+12 for n in counts)
    else:
        h=620
    b=[f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{c["surface"]}" stroke="{c["border"]}"/>']
    b.append(f'<text x="28" y="42" font-family="ui-monospace,monospace" font-size="11" letter-spacing="1" fill="{c["secondary"]}">PLEXON ECOSYSTEM · ORGANIZATIONAL OVERVIEW</text>')
    b.append(f'<text x="28" y="66" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="12" fill="{c["muted"]}">Grouped by responsibility. Containment is not a dependency assertion.</text>')
    if mobile:
        y=92
        for gi,(g,names) in enumerate(GROUPS):
            names=[n for n in names if n in available]
            gh=46+len(names)*34
            b.append(f'<rect x="22" y="{y}" width="456" height="{gh}" rx="12" fill="{c["raised"]}" stroke="{c["border"]}"/>')
            b.append(f'<text x="36" y="{y+24}" font-family="ui-monospace,monospace" font-size="9" fill="{c["highlight"]}">{g}</text>')
            for i,n in enumerate(names):
                yy=y+43+i*34; col=c['danger'] if n in history else c['text']; suffix=' · HISTORICAL' if n in history else ''
                label=n+suffix
                if len(label)>39: label=label[:38]+'…'
                b.append(f'<text x="42" y="{yy+16}" font-family="ui-monospace,monospace" font-size="10" fill="{col}">{escape(label)}</text>')
            y+=gh+12
    else:
        cols=4; cw=232; x0=20; y0=92
        for gi,(g,names) in enumerate(GROUPS):
            names=[n for n in names if n in available]; col=gi%cols; row=gi//cols; x=x0+col*(cw+12); y=y0+row*248
            b.append(f'<rect x="{x}" y="{y}" width="{cw}" height="228" rx="12" fill="{c["raised"]}" stroke="{c["border"]}"/>')
            b.append(f'<text x="{x+14}" y="{y+26}" font-family="ui-monospace,monospace" font-size="9" fill="{c["highlight"]}">{g}</text>')
            for i,n in enumerate(names[:6]):
                yy=y+48+i*27; colr=c['danger'] if n in history else c['text']; suffix=' · historical' if n in history else ''
                b.append(f'<circle cx="{x+18}" cy="{yy-4}" r="3" fill="{colr}"/><text x="{x+28}" y="{yy}" font-family="ui-monospace,monospace" font-size="9" fill="{colr}">{escape(n+suffix)}</text>')
    return svg_shell(w,h,theme,'Plexon ecosystem topology','Organizational grouping of public Plexon repositories by responsibility. Groups do not assert dependency edges; deprecated or retired projects are differentiated.',''.join(b))

def stack(editorial,theme='dark',mobile=False):
    c=THEMES[theme]; w=500 if mobile else 1000; h=510 if mobile else 290
    groups=list(editorial['technology_groups'].items())
    b=[f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{c["surface"]}" stroke="{c["border"]}"/>',f'<text x="28" y="42" font-family="ui-monospace,monospace" font-size="11" letter-spacing="1" fill="{c["secondary"]}">TECHNOLOGY TOPOLOGY</text>',f'<text x="28" y="65" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="12" fill="{c["muted"]}">Technologies grouped by verified use surface. No proficiency scores.</text>']
    if mobile:
        y=90
        for name,items in groups:
            b.append(f'<rect x="22" y="{y}" width="456" height="88" rx="12" fill="{c["raised"]}" stroke="{c["border"]}"/>')
            b.append(f'<text x="36" y="{y+25}" font-family="ui-monospace,monospace" font-size="9" fill="{c["highlight"]}">{escape(name.upper())}</text>')
            b.append(f'<text x="36" y="{y+52}" font-family="ui-monospace,monospace" font-size="10" fill="{c["text"]}">{escape(" · ".join(items))}</text>'); y+=100
    else:
        for i,(name,items) in enumerate(groups):
            x=22+i*242; y=92
            b.append(f'<rect x="{x}" y="{y}" width="228" height="166" rx="12" fill="{c["raised"]}" stroke="{c["border"]}"/>')
            b.append(f'<text x="{x+14}" y="{y+28}" font-family="ui-monospace,monospace" font-size="9" fill="{c["highlight"]}">{escape(name.upper())}</text>')
            for j,item in enumerate(items): b.append(f'<text x="{x+18}" y="{y+58+j*24}" font-family="ui-monospace,monospace" font-size="10" fill="{c["text"]}">• {escape(item)}</text>')
    return svg_shell(w,h,theme,'Technology topology','Verified technologies grouped by server runtime, web interface, desktop, and build/delivery surfaces without proficiency claims.',''.join(b))