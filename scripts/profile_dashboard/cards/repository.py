from datetime import datetime, timezone
from html import escape
from ..draw import svg_shell
from ..tokens import THEMES
from .system_preview import scene

def _fmt(n): return f'{n:,}'
def _release(project):
    r=project.get('latest_stable_release'); return ('—','No stable publication in snapshot') if not r else ('v'+r['version'].lstrip('v'), r['published_at'][:10])
def _spark(values,x,y,w,h,c):
    m=max(values) if values else 0
    if m<=0:return f'<line x1="{x}" y1="{y+h}" x2="{x+w}" y2="{y+h}" stroke="{c["border"]}"/>'
    pts=[]
    for i,v in enumerate(values):
        px=x+i*w/max(1,len(values)-1); py=y+h-(v/m)*h; pts.append(f'{px:.1f},{py:.1f}')
    return f'<polyline points="{" ".join(pts)}" fill="none" stroke="{c["secondary"]}" stroke-width="2" vector-effect="non-scaling-stroke" class="trace" pathLength="1"/>'

def render(project, editorial, activity, theme='dark', mobile=False, activity_label='PROJECT-WIDE · 90D'):
    c=THEMES[theme]; w=500 if mobile else 1000; h=560 if mobile else 390
    ver,pub=_release(project)
    title=f"{project['name']} · system module"
    desc=f"Featured repository dashboard for {project['name']}, showing verified 90-day and 30-day project-wide commit totals, latest stable publication from the snapshot, source language, and a conceptual technical preview."
    b=[]
    b.append(f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{c["surface"]}" stroke="{c["border"]}"/>')
    b.append(f'<rect x="20" y="18" width="6" height="62" rx="3" fill="{c["primary"]}" class="signal"/>')
    b.append(f'<text x="40" y="42" font-family="ui-monospace,monospace" font-size="11" letter-spacing="1.2" fill="{c["muted"]}">{escape(editorial["category"].upper())}</text>')
    fs=25 if mobile else 29
    b.append(f'<text x="40" y="70" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="{fs}" font-weight="750" fill="{c["text"]}">{escape(project["name"])}</text>')
    state_x=40 if mobile else 760; state_y=100 if mobile else 50
    b.append(f'<rect x="{state_x}" y="{state_y-20}" width="{w-state_x-24}" height="28" rx="14" fill="{c["raised"]}" stroke="{c["border"]}"/>')
    b.append(f'<text x="{state_x+12}" y="{state_y-1}" font-family="ui-monospace,monospace" font-size="10" fill="{c["secondary"]}">{escape(editorial["state"].upper())}</text>')
    ty=126 if mobile else 110; maxw=420 if mobile else 900
    # compact wrap at word boundaries
    words=editorial['tagline'].split(); lines=[]; cur=''
    limit=54 if mobile else 110
    for word in words:
        if len(cur)+len(word)+1>limit: lines.append(cur); cur=word
        else: cur=(cur+' '+word).strip()
    if cur:lines.append(cur)
    for i,line in enumerate(lines[:3]): b.append(f'<text x="40" y="{ty+i*18}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="12" fill="{c["muted"]}">{escape(line)}</text>')
    if mobile:
        ky=172
        metrics=[(_fmt(project['commits_90d']),'PROJECT COMMITS','90 UTC days'),(_fmt(project['commits_30d']),'PROJECT COMMITS','30 UTC days'),(ver,'STABLE PUBLICATION',pub),(project.get('primary_language') or '—','PRIMARY LANGUAGE','by source bytes')]
        for i,(v,l,s) in enumerate(metrics):
            xx=24+(i%2)*232; yy=ky+(i//2)*78
            b.append(f'<rect x="{xx}" y="{yy}" width="220" height="68" rx="10" fill="{c["raised"]}" stroke="{c["border"]}"/>')
            b.append(f'<text x="{xx+12}" y="{yy+26}" font-family="ui-monospace,monospace" font-size="19" font-weight="700" fill="{c["text"]}">{escape(v)}</text><text x="{xx+12}" y="{yy+44}" font-family="ui-monospace,monospace" font-size="8" letter-spacing=".8" fill="{c["muted"]}">{l}</text><text x="{xx+12}" y="{yy+58}" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{escape(s)}</text>')
        # scene begins lower; override scene y via module fixed 210, so shift card concept: use group translated
        sc=scene(editorial['preview'],c,mobile=True)
        b.append(f'<g transform="translate(0,118)">{sc}</g>')
        # sparkline overlay in top metrics area
        b.append(_spark(activity,270,147,190,18,c)); b.append(f'<text x="460" y="143" text-anchor="end" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{escape(activity_label)}</text>')
    else:
        metrics=[(_fmt(project['commits_90d']),'PROJECT COMMITS','90 UTC days'),(_fmt(project['commits_30d']),'PROJECT COMMITS','30 UTC days'),(ver,'STABLE PUBLICATION',pub),(project.get('primary_language') or '—','PRIMARY LANGUAGE','by source bytes')]
        for i,(v,l,s) in enumerate(metrics):
            xx=28+i*235; yy=145
            b.append(f'<rect x="{xx}" y="{yy}" width="220" height="62" rx="10" fill="{c["raised"]}" stroke="{c["border"]}"/>')
            b.append(f'<text x="{xx+12}" y="{yy+26}" font-family="ui-monospace,monospace" font-size="20" font-weight="700" fill="{c["text"]}">{escape(v)}</text><text x="{xx+12}" y="{yy+43}" font-family="ui-monospace,monospace" font-size="8" letter-spacing=".8" fill="{c["muted"]}">{l}</text><text x="{xx+210}" y="{yy+43}" text-anchor="end" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{escape(s)}</text>')
        b.append(_spark(activity,730,112,230,22,c)); b.append(f'<text x="960" y="107" text-anchor="end" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{escape(activity_label)}</text>')
        b.append(scene(editorial['preview'],c,mobile=False))
    return svg_shell(w,h,theme,title,desc,''.join(b))