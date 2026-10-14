from .tokens import MONO,SANS

def base_css(c):
    return f'''.mono{{font-family:{MONO}}}.sans{{font-family:{SANS}}}.label{{font:600 12px {MONO};letter-spacing:1.1px;fill:{c['muted']}}}.body{{font:500 14px {SANS};fill:{c['text']}}}.small{{font:500 11px {MONO};fill:{c['muted']}}}.value{{font:700 30px {MONO};fill:{c['text']}}}'''