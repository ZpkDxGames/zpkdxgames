"""Exact KPIs, square-root daily activity and zero-based project bars."""

from datetime import date
from html import escape
import math
from ..draw import text, rect, path, shell, heading, footer, stagger
from ..scales import sqrt_fraction, sqrt_ticks, rolling_average


def kpis(data, theme, mobile=False):
    w, h = (500, 396) if mobile else (1000, 221)
    body = text(28, 35, 'AT A GLANCE', 16 if mobile else 14, 'violet', 650, extra='letter-spacing="1.8"')
    body += text(28 if mobile else w-28, 63 if mobile else 35,
                 'AS OF '+data['as_of'], 17 if mobile else 14, 'text-muted', anchor='start' if mobile else 'end')
    recent = sum(p['commits_30d'] > 0 for p in data['projects']) if data['schema']==2 else '—'
    rows = [(len(data['projects']), 'Public projects'), (sum(p['commits'] for p in data['projects']), 'Commits · 90d'),
            (len(data['releases']), 'Releases · 90d'), (recent, 'Active projects · 30d')]
    for i, (v, label) in enumerate(rows):
        x, y, cw = (28+(i%2)*226, 91+(i//2)*117, 218) if mobile else (28+i*239, 64, 227)
        body += rect(x, y, cw, 101, 'surface', 10, True)
        body += text(x+18, y+46, f'{v:,}' if isinstance(v,int) else v, 38, 'violet' if i==1 else 'text', 650,
                     extra=f'class="reveal" {stagger(i)}')
        body += text(x+18, y+78, label, 16 if mobile else 17, 'text-muted')
    body += footer(data, h-49, mobile)
    if data['schema']==1:
        body += text(28, h-73, '30-day activity unavailable in schema 1.', 14, 'text-muted')
    return shell(theme,w,h,'Public project metrics at a glance',
                 f"As of {data['as_of']}: {rows[0][0]} tracked public projects; {rows[1][0]} project-wide non-bot commits "
                 f"and {rows[2][0]} published releases in 90 UTC days; {recent} projects with non-bot commits in the last 30 UTC days.",body)


def activity(data, theme, mobile=False):
    w, h = (500, 606) if mobile else (1000, 552)
    body = heading(data,w,'Build activity','Every day, at its real scale.',mobile)
    body += text(28, 131 if mobile else 108, 'Square-root axis · ticks show raw counts', 17 if mobile else 16, 'text-muted')
    values = [r['commits'] for r in data['daily']]
    mean = rolling_average(values)
    peak = max(values,default=0)
    peak_row = data['daily'][values.index(peak)] if peak else None
    if peak_row:
        body += text(28 if mobile else 972, 159 if mobile else 108,
                     f"Peak: {peak:,} · {peak_row['date']}", 17 if mobile else 16, 'warm', 600, 'start' if mobile else 'end')
    legend_y = 190 if mobile else 143
    body += rect(28,legend_y-11,13,13,'violet',2)
    body += text(50,legend_y,'Daily project commits',16 if mobile else 15,'text-muted')
    body += path(f'M{28 if mobile else 276} {legend_y+23 if mobile else legend_y-5}h24','cyan',2.5)
    body += text(63 if mobile else 310,legend_y+28 if mobile else legend_y,'Trailing 7-day mean',16 if mobile else 15,'text-muted')
    x0,y0,pw,ph = (63,249,409,195) if mobile else (70,181,902,226)
    ticks = sqrt_ticks(peak)
    maximum = ticks[-1]
    for tick in ticks:
        y = y0+ph*(1-sqrt_fraction(tick,maximum))
        body += path(f'M{x0} {y:.2f}h{pw}',extra='stroke-dasharray="3 5"')
        body += text(x0-13,y+5,tick,14 if mobile else 13,'text-muted',anchor='end')
    step = pw/len(values)
    points=[]
    for i,(v,av,row) in enumerate(zip(values,mean,data['daily'])):
        bh = ph*sqrt_fraction(v,maximum)
        x = x0+i*step+.6
        body += rect(x,y0+ph-bh,max(.8,step-1.3),bh,'violet',.6,
                     extra=f'data-day="{row["date"]}" data-count="{v}"')[:-2]+f'><title>{row["date"]}: {v} project commits; 7-day mean {av:.3f}</title></rect>'
        points.append((x0+(i+.5)*step,y0+ph*(1-sqrt_fraction(av,maximum))))
    d = 'M'+' L'.join(f'{x:.2f} {y:.2f}' for x,y in points)
    length = sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(points,points[1:]))+1
    body += path(d,'cyan',2.5,'class="draw" stroke-linejoin="round"')
    for i in (0,len(values)//2,len(values)-1):
        row=data['daily'][i]
        label=date.fromisoformat(row['date']).strftime('%d %b')
        body += text(x0+(i+.5)*step,y0+ph+25,label,15 if mobile else 14,'text-muted',anchor='start' if i==0 else 'end' if i==len(values)-1 else 'middle')
    body += text(28, h-80, 'Mean: up to 7 available days at window start.', 15 if mobile else 14, 'text-muted')
    body += footer(data,h-51,mobile)
    return shell(theme,w,h,'90-day daily project commits — square-root scale',
                 f"Window {data['start']} to {data['as_of']}. Square-root vertical scale, raw-count tick labels, all 90 daily bars, "
                 f"trailing 7-calendar-day arithmetic mean with available-day warm-up; no counts capped or dropped. "
                 +(f"Peak {peak} on {peak_row['date']}. " if peak_row else 'No qualifying commits. ')
                 +'All authors except bots, project-wide, not personal contributions.',body,length)


def project_commits(data, theme, mobile=False):
    w = 500 if mobile else 1000
    rows = sorted(data['projects'],key=lambda p:(-p['commits'],p['name']))[:10]
    h = (178+len(rows)*53+72) if mobile else (141+len(rows)*38+77)
    h = max(h, 315)
    body = heading(data,w,'Project momentum','Where the work happens.',mobile,
                   'Top 10 projects · project-wide commits')
    maximum = max((p['commits'] for p in rows),default=0)
    for i,p in enumerate(rows):
        y=178+i*53 if mobile else 148+i*38
        if mobile:
            body += text(28,y,p['name'],18,weight=550,max_width=378)
            body += text(472,y,f"{p['commits']:,}",18,'violet',650,'end')
            bx,by,bw = 28,y+12,444
        else:
            body += text(28,y,p['name'],17,weight=550,max_width=237)
            body += text(972,y,f"{p['commits']:,}",17,'violet',650,'end')
            bx,by,bw = 280,y-12,616
        body += rect(bx,by,bw,9,'surface-2',3)
        amount=bw*p['commits']/maximum if maximum else 0
        body += rect(bx,by,amount,9,'violet',3,extra=f'class="grow" {stagger(i)}')
    if not maximum:
        body += text(28,h-84,'No qualifying commits in this window.',16,'text-muted')
    body += footer(data,h-50,mobile)
    return shell(theme,w,h,'Top ten projects by 90-day commits',
                 f"As of {data['as_of']}, zero-based linear bars: "+'; '.join(f"{p['name']}: {p['commits']}" for p in rows)+
                 '. Project-wide non-bot commits, not personal contribution counts.',body)
