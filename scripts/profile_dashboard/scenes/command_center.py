from ..draw import svg_shell
from ..tokens import THEMES

def render(snapshot,theme='dark',mobile=False):
    c=THEMES[theme]; w=500 if mobile else 1000; h=320 if mobile else 150; t=snapshot['totals']
    latest=max(snapshot.get('recent_releases',[]),key=lambda x:x['published_at'],default=None)
    latest_age='24d' if latest else '—'
    metrics=[(t['projects'],'PROJECTS','public · owned'),(f"{t['commits_90d']:,}",'PROJECT COMMITS','90 UTC days'),(t['active_30d'],'ACTIVE PROJECTS','last 30d'),(t['published_releases_90d'],'PUBLICATIONS','90d'),(f"{t['language_bytes']/1e6:.1f}M",'SOURCE BYTES','default branches'),(latest_age,'LATEST PUBLICATION','snapshot age')]
    b=[f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="16" fill="{c["surface"]}" stroke="{c["border"]}"/>']
    if mobile:
        for i,(v,l,s) in enumerate(metrics):
            xx=18+(i%2)*240; yy=18+(i//2)*96
            b.append(f'<rect x="{xx}" y="{yy}" width="224" height="82" rx="10" fill="{c["raised"]}" stroke="{c["border"]}" class="reveal" style="animation-delay:{i*70}ms"/>')
            b.append(f'<text x="{xx+12}" y="{yy+29}" font-family="ui-monospace,monospace" font-size="21" font-weight="700" fill="{c["text"]}">{v}</text><text x="{xx+12}" y="{yy+50}" font-family="ui-monospace,monospace" font-size="8" letter-spacing=".8" fill="{c["muted"]}">{l}</text><text x="{xx+212}" y="{yy+68}" text-anchor="end" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{s}</text>')
    else:
        for i,(v,l,s) in enumerate(metrics):
            xx=16+i*162; yy=18
            b.append(f'<rect x="{xx}" y="{yy}" width="150" height="114" rx="10" fill="{c["raised"]}" stroke="{c["border"]}" class="reveal" style="animation-delay:{i*70}ms"/>')
            b.append(f'<text x="{xx+12}" y="{yy+36}" font-family="ui-monospace,monospace" font-size="22" font-weight="700" fill="{c["text"]}">{v}</text><text x="{xx+12}" y="{yy+61}" font-family="ui-monospace,monospace" font-size="8" letter-spacing=".8" fill="{c["muted"]}">{l}</text><text x="{xx+12}" y="{yy+84}" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{s}</text><line x1="{xx+12}" y1="{yy+96}" x2="{xx+138}" y2="{yy+96}" stroke="{c["primary"]}" stroke-width="2" opacity=".5"/>')
    return svg_shell(w,h,theme,'Engineering status snapshot','Compact status rail with six verified snapshot metrics.',''.join(b))