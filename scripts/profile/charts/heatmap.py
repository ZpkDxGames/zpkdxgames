"""A fixed-bin, Monday-first UTC calendar. Every daily value is retained."""

from datetime import date,timedelta
from ..draw import text,rect,shell,heading,footer
from ..tokens import HEAT_BINS,HEAT_COLORS,contrast
from ..scales import heat_level


def heatmap(data,theme,mobile=False):
    w,h=(500,596) if mobile else (1000,480)
    body=heading(data,w,'Build rhythm','A calendar of project activity.',mobile)
    body+=text(28,133 if mobile else 106,'Monday-first UTC weeks · fixed intensity bins',16,'text-muted')
    first=date.fromisoformat(data['start']);last=date.fromisoformat(data['as_of'])
    monday=first-timedelta(days=first.weekday())
    x0,y0,pitchx,pitchy,cell=(56,173,30,31,23) if mobile else (80,150,39,34,27)
    for i,label in enumerate(('M','T','W','T','F','S','S')):
        body+=text(x0-27,y0+i*pitchy+18,label,14 if mobile else 13,'text-muted')
    for row in data['daily']:
        d=date.fromisoformat(row['date']);col=(d-monday).days//7
        x,y=x0+col*pitchx,y0+d.weekday()*pitchy
        color=HEAT_COLORS[theme][heat_level(row['commits'])]
        body+=f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="4" fill="{color}" stroke="var(--text-muted)" data-day="{row["date"]}" data-count="{row["commits"]}"><title>{row["date"]}: {row["commits"]} project commits</title></rect>'
        if row['commits']:
            # Exact counts encode magnitude without relying on colour alone.
            ink=max(('#000000','#FFFFFF'),key=lambda c:contrast(c,color))
            digits=str(row['commits']);fs=min(11,(cell-3)/(len(digits)*.62))
            body+=f'<text x="{x+cell/2}" y="{y+cell/2+fs*.34}" font-size="{fs}" font-weight="650" text-anchor="middle" fill="{ink}">{digits}</text>'
    endx=x0+((last-monday).days//7)*pitchx+cell
    body+=text(x0,y0+7*pitchy+22,first.strftime('%d %b'),15,'text-muted')
    body+=text(endx,y0+7*pitchy+22,last.strftime('%d %b'),15,'text-muted',anchor='end')
    active=sum(r['commits']>0 for r in data['daily']);peak=max(r['commits'] for r in data['daily'])
    if mobile:
        body+=text(28,435,f'{active} active days',20,'violet',650)
        body+=text(472,435,f'{peak} peak / day',20,'text',650,'end')
        for i,(_,label) in enumerate(HEAT_BINS):
            x=28+(i%3)*153;y=464+(i//3)*42
            body+=f'<rect x="{x}" y="{y}" width="22" height="18" rx="3" fill="{HEAT_COLORS[theme][i]}" stroke="var(--text-muted)"/>'
            body+=text(x+33,y+15,label,16,'text-muted')
    else:
        body+=text(675,181,str(active),43,'violet',650)+text(675,209,'Active days in this window',16,'text-muted')
        body+=text(675,272,str(peak),43,weight=650)+text(675,300,'Peak commits per UTC day',16,'text-muted')
        for i,(_,label) in enumerate(HEAT_BINS):
            x=675+(i%3)*102;y=335+(i//3)*36
            body+=f'<rect x="{x}" y="{y}" width="20" height="17" rx="3" fill="{HEAT_COLORS[theme][i]}" stroke="var(--text-muted)"/>'
            body+=text(x+29,y+14,label,14,'text-muted')
    body+=footer(data,h-48,mobile)
    return shell(theme,w,h,'90-day build rhythm — project commit calendar',
                 f"{data['start']} to {data['as_of']}, Monday-first UTC weeks. {active} nonzero days; peak {peak}. "
                 +'Fixed bins 0, 1–2, 3–5, 6–10, 11–50, 51+. Days outside the window omitted. '
                 +'Every cell retains its exact count in its title. All authors except bots, not a personal coding streak.',body)
