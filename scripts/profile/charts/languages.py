"""Byte-volume language view with an exhaustive, documented project split."""

from ..draw import text, rect, shell, heading, footer
from ..model import language_groups, language_parts


def percent(amount,total):
    return f'{100*amount/total:.1f}%' if total else '0.0%'


def shares(counts,x,y,width,mobile=False,animate=False):
    parts=language_parts(counts)
    total=sum(counts.values())
    body=rect(x,y,width,16,'surface-2',2)
    if animate:
        body+='<g class="grow">'
    offset=0
    colors=('violet','cyan','text-muted','violet','cyan','text-muted','border')
    for i,(language,amount) in enumerate(parts):
        span=width*amount/total if total else 0
        body+=rect(x+offset,y,span,16,colors[i%len(colors)],0,
                   extra=f'data-language="{language}" data-bytes="{amount}"')[:-2]+f'><title>{language}: {amount:,} bytes, {percent(amount,total)}</title></rect>'
        if i:
            body+=f'<path d="M{x+offset:.2f} {y}v16" stroke="var(--bg)" stroke-width="1.5"/>'
        offset+=span
    if animate:
        body+='</g>'
    return body,parts


def language_mix(data,theme,mobile=False):
    w=500 if mobile else 1000
    total=sum(data['languages'].values())
    body=heading(data,w,'Source languages','Source, in perspective.',mobile)
    body+=text(28,132 if mobile else 105,'Default branches · GitHub language bytes',17,'text-muted')
    body+=text(28,170 if mobile else 143,f'{total:,} bytes in total',23 if mobile else 22,weight=650)
    bar_y=189 if mobile else 163
    bars,parts=shares(data['languages'],28,bar_y,w-56,mobile,True)
    body+=bars
    for i,(language,amount) in enumerate(parts):
        cols=2 if mobile else 4
        x=28+(i%cols)*(226 if mobile else 239)
        y=bar_y+48+(i//cols)*28
        body+=text(x,y,f'{language}  {percent(amount,total)}',17 if mobile else 16,'text-muted')
    list_rows=(len(parts)+(1 if mobile else 3))//(2 if mobile else 4)
    start=bar_y+68+list_rows*28
    groups=language_groups(data)
    if mobile:
        y=start+16
        for label,counts,count in groups:
            rows=language_parts(counts)
            gh=128+max(1,(len(rows)+1)//2)*28
            body+=rect(28,y,444,gh,'surface',10,True)
            body+=text(46,y+31,label,23,weight=650)
            group_total=sum(counts.values())
            body+=text(46,y+59,f'{count} projects · {group_total:,} bytes',17,'text-muted')
            b,rows=shares(counts,46,y+79,408,True)
            body+=b
            for i,(lang,amount) in enumerate(rows):
                body+=text(46+(i%2)*208,y+124+(i//2)*28,f'{lang} {percent(amount,group_total)}',17,'text-muted')
            if not rows:
                body+=text(46,y+124,'No language bytes.',17,'text-muted')
            y+=gh+15
        h=y+118
    else:
        y=start+10
        gh=137+max(1,max((len(language_parts(c))+1)//2 for _,c,_ in groups))*26
        for index,(label,counts,count) in enumerate(groups):
            x=28+index*320
            body+=rect(x,y,304,gh,'surface',10,True)
            body+=text(x+18,y+32,label,21,weight=650)
            group_total=sum(counts.values())
            body+=text(x+18,y+59,f'{count} projects · {group_total:,} bytes',15,'text-muted')
            b,rows=shares(counts,x+18,y+81,268)
            body+=b
            for i,(lang,amount) in enumerate(rows):
                body+=text(x+18+(i%2)*139,y+128+(i//2)*26,f'{lang} {percent(amount,group_total)}',14,'text-muted',max_width=132)
            if not rows:
                body+=text(x+18,y+128,'No language bytes.',15,'text-muted')
        h=y+gh+103
    body+=text(28,h-82,'Other = languages below 1% within each view.',16 if mobile else 14,'text-muted')
    body+=footer(data,h-51,mobile,'languages')
    return shell(theme,w,h,'Source-language byte share and project-group comparison',
                 f"As of {data['as_of']}, {total:,} default-branch bytes. The overall share includes all projects. "
                 +'Repository groups partition server/plugin, web/interface and other projects; a web project may contain backend or native code. '
                 +'Each group is normalized within itself and retains its true byte total. Other groups languages below 1% in that view. '
                 +'Source volume, not proficiency or time spent.',body)
