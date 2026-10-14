from __future__ import annotations
from pathlib import Path
from html import escape
from datetime import date, datetime
from math import sqrt
from .tokens import THEMES
from .draw import svg_shell
from .charts.activity import rolling, scaled
from .charts.projects import leaderboard
from .charts.languages import top_languages
from .charts.releases import recent, stable_shelf, week_rows
from .charts.heatmap import bin_for
from .charts.recency import buckets
from .cards.repository import render as render_repository
from .scenes.cover import render as render_cover
from .scenes.command_center import render as render_status
from .scenes.architecture import ecosystem as render_ecosystem, stack as render_stack

VARIANTS=(('light',False,'light'),('dark',False,'dark'),('light',True,'mobile-light'),('dark',True,'mobile-dark'))

def _title(c,heading,caption,w):
    return f'<text x="28" y="40" font-family="ui-monospace,monospace" font-size="11" letter-spacing="1.1" fill="{c["secondary"]}">{escape(heading)}</text><text x="28" y="62" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="11" fill="{c["muted"]}">{escape(caption)}</text>'

def _empty(c,w,h,message):
    return f'<text x="{w/2:.1f}" y="{h/2:.1f}" text-anchor="middle" font-family="ui-monospace,monospace" font-size="11" fill="{c["muted"]}">{escape(message)}</text>'

def activity(snapshot,theme='dark',mobile=False):
    c=THEMES[theme]; w=500 if mobile else 1000; h=390 if mobile else 350; vals=[x['commits'] for x in snapshot['daily']]; avg=rolling(vals,7); m=max(vals) or 1
    x0=42 if mobile else 54; x1=w-24; y0=96; base=h-54; chart_h=base-y0; bw=(x1-x0)/len(vals)
    b=[f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{c["surface"]}" stroke="{c["border"]}"/>',_title(c,'90-DAY ACTIVITY TIMELINE',f"Project-wide commits · {snapshot['window']['start']} → {snapshot['window']['end']} UTC · sqrt vertical scale",w)]
    for frac in (0,.25,.5,.75,1):
        yy=base-frac*chart_h; raw=round((sqrt(m)*frac)**2)
        b.append(f'<line x1="{x0}" y1="{yy:.1f}" x2="{x1}" y2="{yy:.1f}" stroke="{c["grid"]}"/><text x="{x0-8}" y="{yy+4:.1f}" text-anchor="end" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{raw}</text>')
    for i,v in enumerate(vals):
        bh=scaled(v,m,chart_h); xx=x0+i*bw+.5; yy=base-bh; b.append(f'<rect x="{xx:.2f}" y="{yy:.2f}" width="{max(1,bw-1):.2f}" height="{bh:.2f}" fill="{c["primary"]}" opacity=".58" class="bar-y" style="animation-delay:{min(600,i*5)}ms"/>')
    pts=[]
    for i,v in enumerate(avg):
        px=x0+(i+.5)*bw; py=base-scaled(v,m,chart_h); pts.append(f'{px:.2f},{py:.2f}')
    b.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{c["secondary"]}" stroke-width="2" class="trace" pathLength="1" style="animation-delay:650ms"/>')
    pi=max(range(len(vals)),key=lambda i:vals[i]); px=x0+(pi+.5)*bw; py=base-scaled(vals[pi],m,chart_h)
    b.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{c["highlight"]}"/><text x="{min(x1-4,px+8):.1f}" y="{max(86,py-8):.1f}" font-family="ui-monospace,monospace" font-size="9" fill="{c["highlight"]}">PEAK {vals[pi]} · {snapshot["daily"][pi]["date"]}</text>')
    b.append(f'<text x="{x0}" y="{h-24}" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">bars: raw daily count · line: trailing 7-day arithmetic mean</text>')
    return svg_shell(w,h,theme,'90-day project activity timeline','All daily project-wide non-bot commit totals in the 90-day UTC window, with a square-root vertical transform, raw peak annotation, and trailing seven-day arithmetic mean.',''.join(b))

def leaderboard_svg(snapshot,theme='dark',mobile=False):
    c=THEMES[theme]; rows=leaderboard(snapshot['projects'],10 if not mobile else 8); w=500 if mobile else 1000; h=(390 if mobile else 430); x0=170 if mobile else 250; x1=w-50; y0=92
    b=[f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{c["surface"]}" stroke="{c["border"]}"/>',_title(c,'PROJECT ACTIVITY', 'Top projects by project-wide commits in the same 90-day window',w)]
    if not rows:
        b.append(_empty(c,w,h,'No in-scope repositories in this snapshot'))
        return svg_shell(w,h,theme,'Project activity leaderboard','No repositories are available for the project activity leaderboard.',''.join(b))
    gap=(h-y0-30)/len(rows); m=max(p['commits_90d'] for p in rows) or 1
    for i,p in enumerate(rows):
        y=y0+i*gap; val=p['commits_90d']; ww=(x1-x0)*val/m; m30=(x1-x0)*p['commits_30d']/m
        name=p['name'] if len(p['name'])<=22 or not mobile else p['name'][:20]+'…'
        b.append(f'<text x="{x0-10}" y="{y+10:.1f}" text-anchor="end" font-family="ui-monospace,monospace" font-size="9" fill="{c["text"]}">{escape(name)}</text><rect x="{x0}" y="{y}" width="{ww:.1f}" height="14" rx="3" fill="{c["primary"]}" class="bar-x"/><rect x="{x0}" y="{y+17}" width="{m30:.1f}" height="4" rx="2" fill="{c["secondary"]}" class="bar-x"/><text x="{min(x1+5,x0+ww+6):.1f}" y="{y+11:.1f}" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{val}</text>')
    b.append(f'<text x="{x0}" y="{h-18}" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">main bar: 90d · lower marker: 30d · zero baseline</text>')
    return svg_shell(w,h,theme,'Project activity leaderboard','Horizontal bars ranking repositories by exact project-wide 90-day commit totals, with a secondary 30-day activity marker.',''.join(b))

def velocity_svg(snapshot,theme='dark',mobile=False):
    c=THEMES[theme]; rows=leaderboard(snapshot['projects'],8); w=500 if mobile else 1000; h=410 if mobile else 360; x0=175 if mobile else 240; x1=w-40; y0=92
    b=[f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{c["surface"]}" stroke="{c["border"]}"/>',_title(c,'WINDOW ACTIVITY MATRIX','90-day total vs 30-day recent activity · counts are not normalized as growth',w)]
    if not rows:
        b.append(_empty(c,w,h,'No in-scope repositories in this snapshot'))
        return svg_shell(w,h,theme,'Project window activity matrix','No repositories are available for window comparison.',''.join(b))
    gap=(h-y0-28)/len(rows); max90=max(p['commits_90d'] for p in rows) or 1
    for i,p in enumerate(rows):
        y=y0+i*gap; a=(x1-x0)*p['commits_90d']/max90; b30=(x1-x0)*p['commits_30d']/max90
        name=p['name'][:20]+'…' if mobile and len(p['name'])>21 else p['name']
        b.append(f'<text x="{x0-10}" y="{y+12:.1f}" text-anchor="end" font-family="ui-monospace,monospace" font-size="9" fill="{c["text"]}">{escape(name)}</text><rect x="{x0}" y="{y}" width="{a:.1f}" height="9" rx="3" fill="{c["primary"]}" opacity=".65" class="bar-x"/><rect x="{x0}" y="{y+14}" width="{b30:.1f}" height="9" rx="3" fill="{c["secondary"]}" class="bar-x"/><text x="{x1}" y="{y+11:.1f}" text-anchor="end" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{p["commits_90d"]} / {p["commits_30d"]}</text>')
    return svg_shell(w,h,theme,'Project window activity matrix','Two bars per project compare exact 90-day and 30-day project-wide commit counts without presenting the difference as growth.',''.join(b))

def languages_svg(snapshot,theme='dark',mobile=False):
    c=THEMES[theme]; rows=top_languages(snapshot['languages'],7); w=500 if mobile else 1000; h=380 if mobile else 330; x0=150 if mobile else 210; x1=w-46; y0=92
    b=[f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{c["surface"]}" stroke="{c["border"]}"/>',_title(c,'LANGUAGE VOLUME','Default-branch GitHub Linguist bytes · source volume, not proficiency',w)]
    if not rows or snapshot['totals']['language_bytes']==0:
        b.append(_empty(c,w,h,'No language-byte data in this snapshot'))
        return svg_shell(w,h,theme,'Language source volume','No GitHub Linguist language byte data is available in this snapshot.',''.join(b))
    gap=(h-y0-30)/len(rows); m=max(v for _,v in rows) or 1
    for i,(name,val) in enumerate(rows):
        y=y0+i*gap; ww=(x1-x0)*val/m; pct=val/snapshot['totals']['language_bytes']*100
        b.append(f'<text x="{x0-10}" y="{y+12:.1f}" text-anchor="end" font-family="ui-monospace,monospace" font-size="9" fill="{c["text"]}">{escape(name)}</text><rect x="{x0}" y="{y}" width="{ww:.1f}" height="14" rx="3" fill="{c["secondary"]}" class="bar-x"/><text x="{x1}" y="{y+12:.1f}" text-anchor="end" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{val:,} B · {pct:.1f}%</text>')
    return svg_shell(w,h,theme,'Language source volume','Repository language byte totals from GitHub Linguist on default branches. The chart measures source volume, not skill or proficiency.',''.join(b))

def cadence_svg(snapshot,theme='dark',mobile=False):
    c=THEMES[theme]; rows=week_rows(snapshot); w=500 if mobile else 1000; h=340 if mobile else 310; x0=45 if mobile else 70; x1=w-35; y0=92; base=h-55; chart_h=base-y0
    b=[f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{c["surface"]}" stroke="{c["border"]}"/>',_title(c,'RELEASE CADENCE','Published releases by week · stable + prerelease · publication ≠ deployment',w)]
    if not rows:
        b.append(_empty(c,w,h,'No published releases in this window'))
        return svg_shell(w,h,theme,'Release publication cadence','No published releases are present in the selected window.',''.join(b))
    bw=(x1-x0)/len(rows); m=max(r['stable']+r['prerelease'] for r in rows) or 1
    for i,r in enumerate(rows):
        x=x0+i*bw+bw*.18; ww=bw*.62; hs=chart_h*r['stable']/m; hp=chart_h*r['prerelease']/m; y=base-hs-hp
        b.append(f'<rect x="{x:.1f}" y="{base-hs:.1f}" width="{ww:.1f}" height="{hs:.1f}" fill="{c["primary"]}" class="bar-y"/><rect x="{x:.1f}" y="{y:.1f}" width="{ww:.1f}" height="{hp:.1f}" fill="{c["highlight"]}" class="bar-y"/><text x="{x+ww/2:.1f}" y="{base+18}" text-anchor="middle" font-family="ui-monospace,monospace" font-size="{7 if mobile else 8}" fill="{c["muted"]}">{r["week"][5:]}</text><text x="{x+ww/2:.1f}" y="{max(84,y-6):.1f}" text-anchor="middle" font-family="ui-monospace,monospace" font-size="8" fill="{c["text"]}">{r["stable"]+r["prerelease"]}</text>')
    b.append(f'<text x="{x0}" y="{h-20}" font-family="ui-monospace,monospace" font-size="8" fill="{c["primary"]}">■ stable</text><text x="{x0+76}" y="{h-20}" font-family="ui-monospace,monospace" font-size="8" fill="{c["highlight"]}">■ prerelease</text>')
    return svg_shell(w,h,theme,'Release publication cadence','Weekly published release counts split into stable releases and prereleases. Release publication is not represented as deployment.',''.join(b))

def versions_svg(snapshot,theme='dark',mobile=False):
    c=THEMES[theme]; names=['PlexonPanel','PlexonTools','PlexonQuests','PlexonChats','PlexonCore','AI-Desktop-Companion']; rows=stable_shelf(snapshot,names); w=500 if mobile else 1000; h=500 if mobile else 225
    b=[f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{c["surface"]}" stroke="{c["border"]}"/>',_title(c,'STABLE VERSION SHELF','Latest stable publication present in the 90-day snapshot',w)]
    if mobile:
        for i,(name,r) in enumerate(rows):
            x=22+(i%2)*238; y=90+(i//2)*126
            b.append(f'<rect x="{x}" y="{y}" width="224" height="108" rx="10" fill="{c["raised"]}" stroke="{c["border"]}"/>')
            ver='—' if not r else 'v'+r['version'].lstrip('v'); pub='no stable publication' if not r else r['published_at'][:10]
            b.append(f'<text x="{x+12}" y="{y+26}" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{escape(name.upper())}</text><text x="{x+12}" y="{y+58}" font-family="ui-monospace,monospace" font-size="20" font-weight="700" fill="{c["text"]}">{escape(ver)}</text><text x="{x+12}" y="{y+82}" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{escape(pub)}</text>')
    else:
        for i,(name,r) in enumerate(rows):
            x=20+i*161; y=88
            ver='—' if not r else 'v'+r['version'].lstrip('v'); pub='no stable pub.' if not r else r['published_at'][:10]
            b.append(f'<rect x="{x}" y="{y}" width="148" height="110" rx="10" fill="{c["raised"]}" stroke="{c["border"]}"/><text x="{x+10}" y="{y+24}" font-family="ui-monospace,monospace" font-size="7.6" fill="{c["muted"]}">{escape(name.upper())}</text><text x="{x+10}" y="{y+58}" font-family="ui-monospace,monospace" font-size="18" font-weight="700" fill="{c["text"]}">{escape(ver)}</text><text x="{x+10}" y="{y+84}" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{escape(pub)}</text>')
    return svg_shell(w,h,theme,'Stable version shelf','Latest stable publication in the snapshot for the six featured systems; a dash is shown where no stable release appears in the selected window.',''.join(b))

def heatmap_svg(snapshot,theme='dark',mobile=False):
    c=THEMES[theme]; w=500 if mobile else 1000; h=330 if mobile else 340; daily=snapshot['daily']; start=date.fromisoformat(daily[0]['date']); offset=start.weekday(); cols=(offset+len(daily)+6)//7; cell=22 if mobile else 25; gap=4; gridw=cols*(cell+gap); x0=(w-gridw)//2; y0=90
    palette=[c['raised'],c['grid'],c['border'],c['primary'],c['secondary'],c['highlight']]
    b=[f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{c["surface"]}" stroke="{c["border"]}"/>',_title(c,'ACTIVITY HEATMAP','Project activity · not a personal contribution streak · Monday-first',w)]
    for i,item in enumerate(daily):
        pos=offset+i; col=pos//7; row=pos%7; x=x0+col*(cell+gap); y=y0+row*(cell+gap); k=bin_for(item['commits'])
        b.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="4" fill="{palette[k]}" opacity="{.75 if k else 1}"/>')
    labels=['0','1–2','3–5','6–10','11–50','51+']; ly=y0+7*(cell+gap)+20
    for i,l in enumerate(labels):
        x=x0+i*62; b.append(f'<rect x="{x}" y="{ly-10}" width="10" height="10" rx="2" fill="{palette[i]}"/><text x="{x+15}" y="{ly-1}" font-family="ui-monospace,monospace" font-size="7" fill="{c["muted"]}">{l}</text>')
    return svg_shell(w,h,theme,'Project activity heatmap','Monday-first heatmap of daily project-wide commit totals using fixed bins from zero through 51 or more.',''.join(b))

def radar_svg(snapshot,theme='dark',mobile=False):
    c=THEMES[theme]; rows=recent(snapshot,10); w=500 if mobile else 1000; h=390 if mobile else 335; x0=40; x1=w-40; y0=100; span=max(1,len(rows)-1)
    b=[f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{c["surface"]}" stroke="{c["border"]}"/>',_title(c,'PUBLICATION RADAR','Ten most recent published releases in the snapshot · stable and prerelease use shape + color',w),f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="{c["border"]}" stroke-width="2"/>']
    if not rows:
        b.append(_empty(c,w,h,'No published releases in this window'))
        return svg_shell(w,h,theme,'Recent publication radar','No published releases are present in the selected window.',''.join(b))
    if mobile:
        for i,r in enumerate(rows):
            y=100+i*26; shape='◆' if r['prerelease'] else '●'; col=c['highlight'] if r['prerelease'] else c['secondary']; name=r['project'][:17]+'…' if len(r['project'])>18 else r['project']
            b.append(f'<text x="28" y="{y}" font-family="ui-monospace,monospace" font-size="9" fill="{col}">{shape}</text><text x="45" y="{y}" font-family="ui-monospace,monospace" font-size="8" fill="{c["text"]}">{escape(name)}</text><text x="260" y="{y}" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">v{escape(r["version"].lstrip("v"))}</text><text x="470" y="{y}" text-anchor="end" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{r["published_at"][:10]}</text>')
    else:
        for i,r in enumerate(rows):
            x=x0+i*(x1-x0)/span; up=(i%2==0); yy=y0-16 if up else y0+18; col=c['highlight'] if r['prerelease'] else c['secondary'];
            if r['prerelease']: b.append(f'<rect x="{x-5:.1f}" y="{y0-5}" width="10" height="10" transform="rotate(45 {x:.1f} {y0})" fill="{col}"/>')
            else:b.append(f'<circle cx="{x:.1f}" cy="{y0}" r="5" fill="{col}"/>')
            b.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{200+i%3*32}" stroke="{c["grid"]}"/><text x="{x:.1f}" y="{216+i%3*32}" text-anchor="middle" font-family="ui-monospace,monospace" font-size="7.3" fill="{c["text"]}">{escape(r["project"][:16])}</text><text x="{x:.1f}" y="{229+i%3*32}" text-anchor="middle" font-family="ui-monospace,monospace" font-size="7" fill="{c["muted"]}">v{escape(r["version"].lstrip("v"))}</text>')
    return svg_shell(w,h,theme,'Recent publication radar','Recent published releases positioned in snapshot order. Stable releases use circles and prereleases use diamonds, so meaning is not encoded by color alone.',''.join(b))

def window_board_svg(snapshot,theme='dark',mobile=False):
    c=THEMES[theme]; w=500 if mobile else 1000; h=470 if mobile else 310; groups=buckets(snapshot['projects']); items=list(groups.items())
    b=[f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{c["surface"]}" stroke="{c["border"]}"/>',_title(c,'ACTIVITY WINDOW BOARD','Factual recency classes supported by the frozen snapshot; not repository health',w)]
    if mobile:
        y=88
        for label,names in items:
            shown=[(n[:20]+'…') if len(n)>21 else n for n in names]
            lines=[', '.join(shown[i:i+3]) for i in range(0,min(6,len(shown)),3)]
            more=max(0,len(shown)-6); bh=82+max(0,len(lines)-1)*18+(16 if more else 0)
            b.append(f'<rect x="22" y="{y}" width="456" height="{bh}" rx="10" fill="{c["raised"]}" stroke="{c["border"]}"/><text x="36" y="{y+24}" font-family="ui-monospace,monospace" font-size="9" fill="{c["highlight"]}">{escape(label.upper())} · {len(names)}</text>')
            for li,line in enumerate(lines):
                b.append(f'<text x="36" y="{y+49+li*18}" font-family="ui-monospace,monospace" font-size="7.4" fill="{c["muted"]}">{escape(line)}</text>')
            if more: b.append(f'<text x="36" y="{y+49+len(lines)*18}" font-family="ui-monospace,monospace" font-size="7.4" fill="{c["muted"]}">+{more} more</text>')
            y+=bh+10
    else:
        for i,(label,names) in enumerate(items):
            x=24+i*318; y=90
            b.append(f'<rect x="{x}" y="{y}" width="300" height="190" rx="11" fill="{c["raised"]}" stroke="{c["border"]}"/><text x="{x+14}" y="{y+26}" font-family="ui-monospace,monospace" font-size="9" fill="{c["highlight"]}">{escape(label.upper())} · {len(names)}</text>')
            for j,n in enumerate(names[:7]): b.append(f'<text x="{x+16}" y="{y+52+j*18}" font-family="ui-monospace,monospace" font-size="8" fill="{c["text"]}">{escape(n)}</text>')
            if len(names)>7:b.append(f'<text x="{x+16}" y="{y+178}" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">+{len(names)-7} more</text>')
    return svg_shell(w,h,theme,'Repository activity window board','Repositories grouped by whether they have project-wide commits in the last 30 days, only in the 90-day window, or none in the window. This is not a health score.',''.join(b))

def matrix_svg(snapshot,theme='dark',mobile=False):
    c=THEMES[theme]; rows=sorted(snapshot['projects'],key=lambda p:(-p['commits_90d'],p['name'].lower())); w=500 if mobile else 1000; rowh=25 if mobile else 24; h=105+len(rows)*rowh
    b=[f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{c["surface"]}" stroke="{c["border"]}"/>',_title(c,'PROJECT MATRIX','All in-scope public repositories · sorted by 90-day activity, not quality',w)]
    y=86
    if mobile:
        b.append(f'<text x="24" y="{y}" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">PROJECT</text><text x="388" y="{y}" text-anchor="end" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">90D</text><text x="470" y="{y}" text-anchor="end" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">LANG</text>')
        for i,p in enumerate(rows):
            yy=y+20+i*rowh; name=p['name'][:31]+'…' if len(p['name'])>32 else p['name']; lang=p.get('primary_language') or '—'
            b.append(f'<line x1="22" y1="{yy+6}" x2="478" y2="{yy+6}" stroke="{c["grid"]}"/><text x="24" y="{yy}" font-family="ui-monospace,monospace" font-size="8" fill="{c["text"]}">{escape(name)}</text><text x="388" y="{yy}" text-anchor="end" font-family="ui-monospace,monospace" font-size="8" fill="{c["text"]}">{p["commits_90d"]}</text><text x="470" y="{yy}" text-anchor="end" font-family="ui-monospace,monospace" font-size="7.5" fill="{c["muted"]}">{escape(lang)}</text>')
    else:
        cols=[(24,'PROJECT','start'),(570,'90D','end'),(650,'30D','end'),(820,'LATEST STABLE','end'),(968,'LANGUAGE','end')]
        for x,l,a in cols:b.append(f'<text x="{x}" y="{y}" text-anchor="{a}" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{l}</text>')
        for i,p in enumerate(rows):
            yy=y+20+i*rowh; r=p.get('latest_stable_release'); ver='—' if not r else 'v'+r['version'].lstrip('v'); lang=p.get('primary_language') or '—'
            b.append(f'<line x1="22" y1="{yy+6}" x2="978" y2="{yy+6}" stroke="{c["grid"]}"/><text x="24" y="{yy}" font-family="ui-monospace,monospace" font-size="8" fill="{c["text"]}">{escape(p["name"])}</text><text x="570" y="{yy}" text-anchor="end" font-family="ui-monospace,monospace" font-size="8" fill="{c["text"]}">{p["commits_90d"]}</text><text x="650" y="{yy}" text-anchor="end" font-family="ui-monospace,monospace" font-size="8" fill="{c["text"]}">{p["commits_30d"]}</text><text x="820" y="{yy}" text-anchor="end" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{escape(ver)}</text><text x="968" y="{yy}" text-anchor="end" font-family="ui-monospace,monospace" font-size="8" fill="{c["muted"]}">{escape(lang)}</text>')
    return svg_shell(w,h,theme,'Project matrix','Compact overview of every in-scope public repository with exact 90-day and 30-day project-wide commit totals, stable publication when present, and primary language by source bytes.',''.join(b))

RENDERERS={
 'cover':render_cover,'status':render_status,'activity':activity,'leaderboard':leaderboard_svg,'velocity':velocity_svg,'languages':languages_svg,'cadence':cadence_svg,'versions':versions_svg,'heatmap':heatmap_svg,'publication-radar':radar_svg,'activity-window':window_board_svg,'project-matrix':matrix_svg
}

def write_all(snapshot,editorial,main_activity,out_dir):
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True); generated=[]
    for name,fn in RENDERERS.items():
        for theme,mobile,suffix in VARIANTS:
            path=out/f'{name}-{suffix}.svg'; path.write_text(fn(snapshot,theme,mobile),encoding='utf-8'); generated.append(path)
    for name,fn in [('ecosystem',lambda s,t,m:render_ecosystem(s,editorial,t,m)),('stack-topology',lambda s,t,m:render_stack(editorial,t,m))]:
        for theme,mobile,suffix in VARIANTS:
            path=out/f'{name}-{suffix}.svg'; path.write_text(fn(snapshot,theme,mobile),encoding='utf-8'); generated.append(path)
    pm={p['name']:p for p in snapshot['projects']}
    for item in editorial['featured']:
        repo=item['repo']; slug=repo.lower().replace('_','-')
        project=pm[repo]
        if 'daily_commits' in project:
            vals=project['daily_commits']; activity_label='PROJECT-WIDE · 90D'
        else:
            vals=main_activity['projects'].get(repo,[0]*90); activity_label='MAIN BRANCH · 90D'
        for theme,mobile,suffix in VARIANTS:
            path=out/f'project-{slug}-{suffix}.svg'; path.write_text(render_repository(project,item,vals,theme,mobile,activity_label),encoding='utf-8'); generated.append(path)
    return generated