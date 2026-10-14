"""Weekly publication cadence, stable versions, and timestamp-ordered radar."""

from datetime import date
import math
from html import escape
from ..draw import text, rect, path, shell, heading, footer, stagger
from ..model import weekly_releases, latest_stable, age_of_latest_release, ordered_releases, publication_time
from ..editorial import SHELF_PROJECTS, short_name


def cadence(data,theme,mobile=False):
    w,h=(500,590) if mobile else (1000,513)
    rows=weekly_releases(data)
    stable=sum(r['stable'] for r in rows)
    pre=sum(r['prerelease'] for r in rows)
    body=heading(data,w,'Release cadence','Published, week by week.',mobile)
    body+=text(28,133 if mobile else 110,f'{stable} stable · {pre} prerelease · {stable+pre} total',18,'text-muted')
    by=168 if mobile else 143
    body+=rect(28,by-11,13,13,'violet',2)+text(50,by,'Stable',16,'text-muted')
    body+=rect(146,by-11,13,13,'cyan',0,extra='stroke="var(--cyan)"')+text(168,by,'Prerelease',16,'text-muted')
    x0,y0,pw,ph=(62,203,409,232) if mobile else (70,179,902,175)
    peak=max((r['stable']+r['prerelease'] for r in rows),default=0)
    maximum=max(4,math.ceil(peak/4)*4)
    for i in range(5):
        val=maximum*i/4;y=y0+ph*(1-i/4)
        body+=path(f'M{x0} {y}h{pw}',extra='stroke-dasharray="3 5"')
        body+=text(x0-12,y+5,int(val),14,'text-muted',anchor='end')
    step=pw/len(rows)
    for i,r in enumerate(rows):
        x=x0+(i+.17)*step;bw=step*.66
        hs=ph*r['stable']/maximum;hp=ph*r['prerelease']/maximum
        body+=f'<g class="bar-y" {stagger(i)}><title>Week of {r["start"]}: {r["stable"]} stable, {r["prerelease"]} prerelease'+('; partial window week' if r['partial'] else '')+'</title>'
        body+=rect(x,y0+ph-hs,bw,hs,'violet',0)+rect(x,y0+ph-hs-hp,bw,hp,'cyan',0)
        body+='</g>'
        if r['partial']:
            body+=text(x+bw/2,y0+ph+22,'*',18,'text-muted',anchor='middle')
        if i in (0,len(rows)//2,len(rows)-1):
            body+=text(x0+(i+.5)*step,y0+ph+44,r['start'].strftime('%d %b'),15 if mobile else 14,'text-muted',anchor='start' if i==0 else 'end' if i==len(rows)-1 else 'middle')
    if not peak:
        body+=text(x0+pw/2,y0+ph/2,'No published releases in this window.',16,'text-muted',anchor='middle')
    body+=text(28,h-88,'Monday-first UTC weeks · * partial edge week',16 if mobile else 14,'text-muted')
    body+=footer(data,h-55,mobile,'releases')
    return shell(theme,w,h,'Weekly published releases — stable and prerelease',
                 f"{data['start']} to {data['as_of']}: {stable} stable and {pre} prerelease publications. "
                 +'GitHub prerelease flags, not inferred tag names. Linear stacked weekly counts; partial edge weeks marked. '
                 +'Publication is not production-readiness certification.',body)


def version_shelf(data,theme,mobile=False):
    w=500 if mobile else 1000
    present={p['name'] for p in data['projects']}
    names=[n for n in SHELF_PROJECTS if n in present]
    if not names:
        names=[p['name'] for p in data['projects'][:12]]
    stable=latest_stable(data)
    cols=2 if mobile else 4
    count=(len(names)+cols-1)//cols
    h=(167+count*121+78) if mobile else (139+count*110+72)
    h=max(h,305)
    body=heading(data,w,'Version shelf','Stable versions in the window.',mobile,
                 'Latest by publication time · not source version')
    for i,n in enumerate(names):
        x=28+(i%cols)*(226 if mobile else 239)
        y=(164 if mobile else 131)+(i//cols)*(121 if mobile else 110)
        cw,ch=(218,107) if mobile else (227,96)
        body+=rect(x,y,cw,ch,'surface',9,True)
        body+=text(x+15,y+27,short_name(n),18 if mobile else 17,weight=550,max_width=cw-30)
        release=stable.get(n)
        version=release['version'] if release else '—'
        body+=text(x+15,y+57,version,24,'violet',650,max_width=cw-30)
        body+=text(x+15,y+85 if mobile else y+81,publication_time(release).date().isoformat() if release else 'No stable publication',14,'text-muted',max_width=cw-30)
    if not names:
        body+=text(28,175,'No projects in this snapshot.',17,'text-muted')
    body+=footer(data,h-49,mobile,'releases')
    return shell(theme,w,h,'Latest stable publications for selected major projects',
                 f"As of {data['as_of']}, latest non-prerelease publication between {data['start']} and {data['as_of']}. "
                 +'No publication is shown as —; a source version or newer branch is not substituted. '
                 +'; '.join(n+': '+(stable[n]['version'] if n in stable else 'no stable publication in window') for n in names),body)


def release_radar(data,theme,mobile=False):
    w=500 if mobile else 1000
    rows=ordered_releases(data)[:6]
    h=max(360,(217+len(rows)*101+79) if mobile else (165+len(rows)*59+75))
    body=heading(data,w,'Release radar','Recent published milestones.',mobile)
    age=age_of_latest_release(data)
    label=f'Last release {age} days before snapshot' if age is not None else 'No published releases in this window'
    body+=text(28,133 if mobile else 108,label,17,'warm' if age is not None else 'text-muted',550)
    active=[r['date'] for r in data['daily'] if r['commits']]
    if active:
        body+=text(28,161 if mobile else 134,'Project activity through '+active[-1],17 if mobile else 15,'text-muted')
    for i,r in enumerate(rows):
        y=216+i*101 if mobile else 178+i*59
        flag='PRERELEASE' if r['prerelease'] else 'STABLE'
        if mobile:
            body+=text(28,y,r['project'],20,weight=600,max_width=444)
            body+=text(28,y+28,r['version'],19,'violet',600,max_width=265)
            body+=text(472,y+28,publication_time(r).date().isoformat(),16,'text-muted',anchor='end')
            body+=text(28,y+54,flag,14,'cyan' if r['prerelease'] else 'violet',650,extra='letter-spacing="1"')
            body+=path(f'M28 {y+74}H472')
        else:
            body+=text(28,y,r['project'],18,weight=600,max_width=265)
            body+=text(315,y,r['version'],19,'violet',600,max_width=252)
            body+=text(633,y,flag,14,'cyan' if r['prerelease'] else 'violet',650)
            body+=text(972,y,publication_time(r).date().isoformat(),16,'text-muted',anchor='end')
            body+=path(f'M28 {y+23}H972')
    body+=footer(data,h-49,mobile,'releases')
    return shell(theme,w,h,'Six most recent published GitHub releases',
                 f"Window {data['start']} to {data['as_of']}. {label}. Sorted by actual UTC publication timestamp. "
                 +'; '.join(f"{r['project']} {r['version']}, {publication_time(r).date()}, {'prerelease' if r['prerelease'] else 'stable'}" for r in rows)
                 +'. Stable labels reflect the GitHub flag; publication does not certify live deployment.',body)
