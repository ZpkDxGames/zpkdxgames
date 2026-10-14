from math import pow

def _rgb(hexv):
    h=hexv.lstrip('#'); return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))
def luminance(hexv):
    def f(c): return c/12.92 if c<=.04045 else pow((c+.055)/1.055,2.4)
    r,g,b=_rgb(hexv); return .2126*f(r)+.7152*f(g)+.0722*f(b)
def contrast(a,b):
    l1,l2=sorted((luminance(a),luminance(b)), reverse=True); return (l1+.05)/(l2+.05)
def validate_palette(theme):
    checks=[('text/bg',theme['text'],theme['bg'],4.5),('muted/bg',theme['muted'],theme['bg'],4.5),('primary/bg',theme['primary'],theme['bg'],3.0),('secondary/bg',theme['secondary'],theme['bg'],3.0)]
    return [(name,contrast(a,b),target) for name,a,b,target in checks]