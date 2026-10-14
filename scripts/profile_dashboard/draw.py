from html import escape
from .tokens import THEMES
from .motion import css as motion_css
from .typography import base_css

def svg_shell(width,height,theme,title,desc,body):
    c=THEMES[theme]
    style=f'''<style>{base_css(c)}{motion_css()}svg{{background:{c['bg']}}}.panel{{fill:{c['surface']};stroke:{c['border']};stroke-width:1}}.raised{{fill:{c['raised']};stroke:{c['border']};stroke-width:1}}.grid{{stroke:{c['grid']};stroke-width:1}}.p{{fill:{c['primary']}}}.s{{fill:{c['secondary']}}}.h{{fill:{c['highlight']}}}.d{{fill:{c['danger']}}}</style>'''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc" viewBox="0 0 {width} {height}"><title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>{style}{body}</svg>\n'''
def text(x,y,value,cls='body',anchor='start',extra=''):
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}" {extra}>{escape(str(value))}</text>'
def line(x1,y1,x2,y2,stroke,width=1,extra=''):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{width}" {extra}/>'
def rect(x,y,w,h,fill=None,rx=0,cls=None,extra=''):
    attrs=[]
    if fill: attrs.append(f'fill="{fill}"')
    if cls: attrs.append(f'class="{cls}"')
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" {" ".join(attrs)} {extra}/>'
def circle(cx,cy,r,fill,extra=''):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" {extra}/>'