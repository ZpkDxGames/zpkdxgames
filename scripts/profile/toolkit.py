"""Static, labelled wrappers around the unchanged vendored technology marks."""

from pathlib import Path
import xml.etree.ElementTree as ET
from .draw import text, rect, path, shell

ROOT=Path(__file__).resolve().parents[2]
TOOLKIT={
    'java':('Java','Java'), 'javascript':('JavaScript','JavaScript'),
    'html':('HTML','HTML'), 'css':('CSS','CSS'), 'python':('Python','Python'),
    'git':('Git','Git'), 'github':('GitHub','Github'), 'actions':('Actions','GithubActions'),
    'gradle':('Gradle','Gradle'), 'maven':('Maven','Maven'), 'vercel':('Vercel','Vercel'),
    'nextjs':('Next.js','NextJS'), 'sqlite':('SQLite','SQLite'),
    'paper':('Paper',None), 'minimessage':('MiniMessage',None),
}


def toolkit_icon(theme,key):
    label,source=TOOLKIT[key]
    if source:
        folder=ROOT/'assets/vendor/skill-icons'
        filename=folder/f'{source}-{theme.title()}.svg'
        if not filename.exists():
            filename=folder/f'{source}.svg'
        root=ET.fromstring(filename.read_text(encoding='utf-8'))
        root.set('x','6');root.set('y','7');root.set('width','64');root.set('height','64')
        ET.register_namespace('','http://www.w3.org/2000/svg')
        body=ET.tostring(root,encoding='unicode')
    else:
        body=rect(6,7,64,64,'surface-2',12,True)
        if key=='paper':
            body+=path('M25 21H43L54 32V58H25ZM43 21V32H54M32 41H47M32 49H43','violet',2.5)
        else:
            body+=path('M28 29L18 39L28 49M48 29L58 39L48 49M43 26L33 52','cyan',3)
    body+=text(38,94,label,10.5 if len(label)>10 else 11.5,weight=550,anchor='middle')
    return shell(theme,76,104,label+' toolkit icon',label+'. Static technology identifier, not a proficiency rating. Original marks and license retained.',body)
