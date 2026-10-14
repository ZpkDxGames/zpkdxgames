from html import escape

def _node(x,y,w,h,label,c,sub=None,kind='normal'):
    stroke=c['danger'] if kind=='disabled' else c['border']; fill=c['raised']
    s=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}"/>'
    s+=f'<text x="{x+12}" y="{y+22}" font-family="ui-monospace,monospace" font-size="11" font-weight="700" fill="{c["text"]}">{escape(label)}</text>'
    if sub:s+=f'<text x="{x+12}" y="{y+39}" font-family="ui-monospace,monospace" font-size="9" fill="{c["muted"]}">{escape(sub)}</text>'
    return s

def _edge(x1,y1,x2,y2,c,delay=0):
    return f'<path d="M{x1} {y1} L{x2} {y2}" fill="none" stroke="{c["primary"]}" stroke-width="2" class="flow" style="animation-delay:{delay}ms" opacity=".8"/>'

def scene(kind,c,x=28,y=190,w=944,h=175,mobile=False):
    if mobile: x,y,w,h=24,210,452,210
    parts=[f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{c["bg"]}" stroke="{c["border"]}"/>',f'<text x="{x+16}" y="{y+20}" font-family="ui-monospace,monospace" font-size="9" letter-spacing="1" fill="{c["muted"]}">SYSTEM PREVIEW · CONCEPTUAL</text>']
    if mobile:
        nx=x+22; nw=w-44; nh=40; gap=9; sy=y+35
        labels={
          'panel-topology':[('PAPER SERVER','pairing · telemetry'),('LINUX HOST','service · backups'),('COORDINATION','relay / worker'),('DASHBOARD','browser surface')],
          'tool-pipeline':[('TOOL IDENTITY','uuid · owner · world'),('PROGRESSION','in-memory authority'),('EVENT CONTRACT','progress events'),('SQLITE','async bounded writes')],
          'quest-state':[('AVAILABLE','daily / weekly / milestone'),('JOINED','active selection'),('PROGRESS','guarded updates'),('HISTORY / CLAIM','persistent state')],
          'chat-routing':[('INPUT','local · global · private'),('ROUTER','channel policy'),('CHAT EVENTS','event coordinator'),('DISCORD','optional presentation')],
          'companion-state':[('SKIN SOURCE','minecraft skin'),('LOCAL RENDERER','skinview3d · three.js'),('BEHAVIOR','deterministic controller'),('AI ACTIONS','NOT IMPLEMENTED')],
          'core-runtime':[('EVENT GATEWAY','block outcomes'),('CONTEXT','immutable routing'),('ORIGIN / STORAGE','PDC · SQLite'),('DIAGNOSTICS','lifecycle reporting')]
        }[kind]
        for i,(a,b) in enumerate(labels):
            yy=sy+i*(nh+gap); parts.append(_node(nx,yy,nw,nh,a,c,b,'disabled' if kind=='companion-state' and i==3 else 'normal'))
            if i<len(labels)-1: parts.append(_edge(nx+nw/2,yy+nh,nx+nw/2,yy+nh+gap,c,i*160))
        return ''.join(parts)
    labels={
      'panel-topology':[(80,'PAPER SERVER','pairing · telemetry'),(300,'LINUX HOST','service · backups'),(520,'COORDINATION','relay / worker'),(740,'DASHBOARD','browser surface')],
      'tool-pipeline':[(80,'TOOL IDENTITY','uuid · owner · world'),(300,'PROGRESSION','memory authority'),(520,'EVENT CONTRACT','progress events'),(740,'SQLITE','bounded writes')],
      'quest-state':[(80,'AVAILABLE','board lanes'),(300,'JOINED','selection'),(520,'PROGRESS','guarded update'),(740,'HISTORY / CLAIM','persistent state')],
      'chat-routing':[(80,'INPUT','local/global/private'),(300,'ROUTER','channel policy'),(520,'CHAT EVENTS','coordinator'),(740,'DISCORD','optional presentation')],
      'companion-state':[(80,'SKIN SOURCE','minecraft skin'),(300,'LOCAL RENDERER','skinview3d'),(520,'BEHAVIOR','deterministic'),(740,'AI ACTIONS','NOT IMPLEMENTED')],
      'core-runtime':[(80,'EVENT GATEWAY','block outcomes'),(300,'CONTEXT','immutable'),(520,'ORIGIN / STORAGE','PDC · SQLite'),(740,'DIAGNOSTICS','lifecycle')]
    }[kind]
    base=x
    node_w=168; node_h=64; yy=y+56
    for i,(xx,label,sub) in enumerate(labels):
        px=base+xx; disabled=kind=='companion-state' and i==3
        parts.append(_node(px,yy,node_w,node_h,label,c,sub,'disabled' if disabled else 'normal'))
        if i<len(labels)-1: parts.append(_edge(px+node_w,yy+32,base+labels[i+1][0],yy+32,c,i*180))
    return ''.join(parts)