from html import escape
from ..draw import svg_shell
from ..tokens import THEMES

def render(snapshot,theme='dark',mobile=False):
    c=THEMES[theme]; w=500 if mobile else 1000; h=610 if mobile else 480
    t=snapshot['totals']; asof=snapshot['as_of']
    b=[f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="22" fill="{c["surface"]}" stroke="{c["border"]}"/>']
    # thin engineering grid
    step=40 if mobile else 50
    for x in range(step,w,step): b.append(f'<line x1="{x}" y1="1" x2="{x}" y2="{h-1}" stroke="{c["grid"]}" opacity=".45"/>')
    for y in range(step,h,step): b.append(f'<line x1="1" y1="{y}" x2="{w-1}" y2="{y}" stroke="{c["grid"]}" opacity=".45"/>')
    b.append(f'<rect x="20" y="20" width="{w-40}" height="{h-40}" rx="17" fill="none" stroke="{c["border"]}" class="trace" pathLength="1"/>')
    tx=36 if mobile else 54
    b.append(f'<text x="{tx}" y="64" font-family="ui-monospace,monospace" font-size="11" letter-spacing="1.6" fill="{c["secondary"]}" class="reveal">TONIM / ZPKDXGAMES</text>')
    title_size=34 if mobile else 42
    title_y=112 if mobile else 132
    if mobile:
        b.append(f'<text x="{tx}" y="{title_y}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="{title_size}" font-weight="800" fill="{c["text"]}" class="reveal" style="animation-delay:90ms">Engineering systems.</text>')
        b.append(f'<text x="{tx}" y="{title_y+42}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="{title_size}" font-weight="800" fill="{c["text"]}" class="reveal" style="animation-delay:140ms">Building experiences.</text>')
        suby=192
    else:
        b.append(f'<text x="{tx}" y="{title_y}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="{title_size}" font-weight="800" fill="{c["text"]}" class="reveal" style="animation-delay:90ms">Engineering systems. Building experiences.</text>')
        suby=168
    if mobile:
        b.append(f'<text x="{tx}" y="{suby}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="12" fill="{c["muted"]}" class="reveal" style="animation-delay:190ms">Minecraft infrastructure · web interfaces</text>')
        b.append(f'<text x="{tx}" y="{suby+18}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="12" fill="{c["muted"]}" class="reveal" style="animation-delay:220ms">developer tooling · desktop experiments</text>')
    else:
        b.append(f'<text x="{tx}" y="{suby}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="13" fill="{c["muted"]}" class="reveal" style="animation-delay:190ms">Minecraft infrastructure · web interfaces · developer tooling · desktop experiments</text>')
    b.append(f'<text x="{w-tx}" y="64" text-anchor="end" font-family="ui-monospace,monospace" font-size="10" fill="{c["muted"]}">SNAPSHOT · {asof}</text>')
    metrics=[(t['projects'],'PROJECTS','IN SCOPE'),(f"{t['commits_90d']:,}",'COMMITS','90 UTC DAYS'),(t['active_30d'],'ACTIVE','30 DAYS'),(t['published_releases_90d'],'RELEASES','PUBLISHED')]
    if mobile:
        yy=244
        for i,(v,l,s) in enumerate(metrics):
            xx=34+(i%2)*220; y=yy+(i//2)*92
            b.append(f'<rect x="{xx}" y="{y}" width="202" height="76" rx="10" fill="{c["raised"]}" stroke="{c["border"]}" class="reveal" style="animation-delay:{260+i*70}ms"/>')
            b.append(f'<text x="{xx+14}" y="{y+31}" font-family="ui-monospace,monospace" font-size="24" font-weight="700" fill="{c["text"]}">{v}</text><text x="{xx+14}" y="{y+50}" font-family="ui-monospace,monospace" font-size="9" letter-spacing="1" fill="{c["muted"]}">{l}</text><text x="{xx+188}" y="{y+50}" text-anchor="end" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{s}</text>')
        sy=444
    else:
        yy=215
        for i,(v,l,s) in enumerate(metrics):
            xx=54+i*225
            b.append(f'<rect x="{xx}" y="{yy}" width="205" height="78" rx="10" fill="{c["raised"]}" stroke="{c["border"]}" class="reveal" style="animation-delay:{260+i*70}ms"/>')
            b.append(f'<text x="{xx+14}" y="{yy+32}" font-family="ui-monospace,monospace" font-size="25" font-weight="700" fill="{c["text"]}">{v}</text><text x="{xx+14}" y="{yy+52}" font-family="ui-monospace,monospace" font-size="9" letter-spacing="1" fill="{c["muted"]}">{l}</text><text x="{xx+190}" y="{yy+52}" text-anchor="end" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{s}</text>')
        sy=344
    # topology signal
    if mobile:
        xs=[62,178,322,438]; labels=['PAPER','HOST','RELAY','WEB']; cy=514
    else:
        xs=[105,345,655,895]; labels=['PAPER','HOST','CONTROL','DASHBOARD']; cy=372
    for i in range(len(xs)-1): b.append(f'<line x1="{xs[i]}" y1="{cy}" x2="{xs[i+1]}" y2="{cy}" stroke="{c["primary"]}" stroke-width="2" class="flow" opacity=".65"/>')
    for i,x in enumerate(xs):
        b.append(f'<circle cx="{x}" cy="{cy}" r="13" fill="{c["raised"]}" stroke="{c["secondary"]}" class="signal"/><circle cx="{x}" cy="{cy}" r="4" fill="{c["secondary"]}"/>')
        b.append(f'<text x="{x}" y="{cy+31}" text-anchor="middle" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{labels[i]}</text>')
    b.append(f'<text x="{tx}" y="{h-32}" font-family="ui-monospace,monospace" font-size="9" fill="{c["muted"]}">STATIC GITHUB SNAPSHOT · NOT REALTIME TELEMETRY</text>')
    return svg_shell(w,h,theme,'Tonim / ZpkDxGames engineering command center','Profile command-center cover with a dated GitHub snapshot, high-level repository metrics, and a conceptual system topology. Static data is not realtime telemetry.',''.join(b))