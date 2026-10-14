#!/usr/bin/env python3
"""Render full-page README QA previews with Playwright.

Optional QA dependency only: Playwright + Chromium and Pillow. The core README
renderer stays standard-library only. SVG assets are embedded as data URIs so QA
works even in sandboxes where file:// and loopback navigation are blocked.
"""
from pathlib import Path
import base64, html, re

ROOT=Path(__file__).resolve().parents[1]
PRE=ROOT/'previews'; PRE.mkdir(exist_ok=True)


def links(s):
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)',lambda m:f'<a href="{html.escape(m.group(2),quote=True)}">{html.escape(m.group(1))}</a>',s)


def to_html(md):
    lines=md.splitlines(); out=[]; i=0
    while i<len(lines):
        line=lines[i]
        if line.startswith('<!--'):
            while i<len(lines) and '-->' not in lines[i]: i+=1
        elif line.startswith('<picture>'):
            block=[]
            while i<len(lines):
                block.append(lines[i])
                if lines[i].startswith('</picture>'): break
                i+=1
            out.append('\n'.join(block))
        elif line.startswith('<p ') or line.startswith('<sub>'):
            block=[]
            while i<len(lines):
                block.append(lines[i])
                if lines[i].startswith('</p>') or '</sub>' in lines[i]: break
                i+=1
            out.append('\n'.join(block))
        elif line.startswith('### '): out.append(f'<h3>{links(line[4:])}</h3>')
        elif line.startswith('## '): out.append(f'<h2 id="{re.sub("[^a-z0-9-]","",line[3:].lower().replace(" ","-"))}">{links(line[3:])}</h2>')
        elif line.startswith('> '): out.append(f'<blockquote>{links(line[2:])}</blockquote>')
        elif line.strip(): out.append(f'<p>{links(line)}</p>')
        i+=1
    return '\n'.join(out)


def inline_assets(body):
    cache={}
    def repl(m):
        path=m.group(0)
        if path not in cache:
            data=(ROOT/path).read_bytes()
            cache[path]='data:image/svg+xml;base64,'+base64.b64encode(data).decode('ascii')
        return cache[path]
    return re.sub(r'assets/profile-dashboard/[A-Za-z0-9._-]+\.svg',repl,body)


def build_html():
    body=inline_assets(to_html((ROOT/'README.md').read_text(encoding='utf-8')))
    css='''
:root{color-scheme:light dark}*{box-sizing:border-box}html,body{margin:0;overflow-x:hidden}body{background:#fff;color:#1f2328;font:16px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.markdown-body{width:min(900px,calc(100vw - 32px));margin:0 auto;padding:32px 0 80px}.markdown-body img{display:block;max-width:100%;height:auto}.markdown-body picture{display:block;margin:14px 0 26px}.markdown-body h2{font-size:24px;border-bottom:1px solid #d0d7de;padding-bottom:8px;margin-top:38px}.markdown-body h3{font-size:18px;margin-top:28px}.markdown-body p{line-height:1.55}.markdown-body blockquote{border-left:4px solid #d0d7de;color:#59636e;margin:20px 0;padding:6px 16px}.markdown-body a{color:#0969da;text-decoration:none}.markdown-body sub{color:#59636e}@media(max-width:600px){.markdown-body{width:calc(100vw - 20px);padding-top:10px}.markdown-body h2{font-size:20px}.markdown-body h3{font-size:16px}.markdown-body p{font-size:14px}}@media(prefers-color-scheme:dark){body{background:#0d1117;color:#f0f6fc}.markdown-body h2{border-color:#30363d}.markdown-body blockquote{border-color:#30363d;color:#8b949e}.markdown-body a{color:#58a6ff}.markdown-body sub{color:#8b949e}}
'''
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body><main class="markdown-body">{body}</main></body></html>'


def render():
    from playwright.sync_api import sync_playwright
    html_text=build_html(); (PRE/'preview.html').write_text(html_text,encoding='utf-8')
    cases=[('desktop-light.png',1440,1200,'light'),('desktop-dark.png',1440,1200,'dark'),('mobile-light.png',390,844,'light'),('mobile-dark.png',390,844,'dark')]
    checks=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
        for name,w,h,scheme in cases:
            page=browser.new_page(viewport={'width':w,'height':h},color_scheme=scheme)
            page.set_content(html_text,wait_until='load'); page.wait_for_timeout(1400)
            overflow=page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')
            if overflow: raise RuntimeError(f'horizontal overflow: {name}')
            page.screenshot(path=str(PRE/name),full_page=True)
            checks.append((name,page.evaluate('document.documentElement.scrollWidth'),page.evaluate('document.documentElement.clientWidth'),page.evaluate('document.documentElement.scrollHeight')))
            page.close()

        # Browser-level reduced-motion + text-fit audit on every generated SVG.
        svg_names=sorted(x.name for x in (ROOT/'assets/profile-dashboard').glob('*.svg'))
        page=browser.new_page(viewport={'width':1000,'height':800},color_scheme='dark',reduced_motion='reduce')
        active=[]; text_overflow=[]
        bbox_script="""() => {
          const svg=document.querySelector('svg');
          if(!svg) return ['missing-svg'];
          const vb=svg.viewBox.baseVal, out=[];
          for (const el of document.querySelectorAll('text')) {
            const b=el.getBBox();
            if (b.x < -1 || b.y < -1 || b.x+b.width > vb.width+1 || b.y+b.height > vb.height+1)
              out.push(el.textContent || '<empty>');
          }
          return out.slice(0,5);
        }"""
        for name in svg_names:
            source=(ROOT/'assets/profile-dashboard'/name).read_text(encoding='utf-8')
            page.set_content(source,wait_until='load'); page.wait_for_timeout(25)
            count=page.evaluate('document.getAnimations().filter(a=>a.playState === "running" || a.playState === "pending").length')
            if count: active.append((name,count))
            bad=page.evaluate(bbox_script)
            if bad: text_overflow.append((name,bad))
        page.close(); browser.close()
        if active: raise RuntimeError(f'active animations under reduced motion: {active[:8]}')
        if text_overflow: raise RuntimeError(f'SVG text outside viewBox: {text_overflow[:8]}')

    from PIL import Image,ImageDraw
    imgs=[Image.open(PRE/name).convert('RGB') for name,_,_,_ in cases]
    thumbs=[]
    for im in imgs:
        ratio=min(620/im.width,820/im.height); thumbs.append(im.resize((max(1,int(im.width*ratio)),max(1,int(im.height*ratio)))))
    sheet=Image.new('RGB',(1320,1760),'white'); d=ImageDraw.Draw(sheet); labels=['DESKTOP · LIGHT','DESKTOP · DARK','MOBILE · LIGHT','MOBILE · DARK']; positions=[(20,60),(680,60),(20,920),(680,920)]
    for label,im,(x,y) in zip(labels,thumbs,positions): d.text((x,y-34),label,fill='black'); sheet.paste(im,(x,y))
    sheet.save(PRE/'preview-sheet.png',quality=92)
    print('\n'.join(f'{n}: scroll {sw}/{cw}, full height {sh}' for n,sw,cw,sh in checks))
    print(f'reduced-motion: 0 active animations across {len(svg_names)} SVGs')
    print('text-fit: all SVG text bounding boxes remain inside their viewBox')


if __name__=='__main__': render()