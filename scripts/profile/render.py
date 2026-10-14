"""Render and parse every asset before atomic per-file replacement."""

import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET
from .tokens import THEMES
from .model import validate
from .cover import cover
from .cards import card
from .editorial import FEATURED
from .ecosystem import ecosystem_map
from .toolkit import TOOLKIT,toolkit_icon
from .charts import activity,kpis,project_commits,language_mix,cadence,version_shelf,release_radar,heatmap

ROOT=Path(__file__).resolve().parents[2]
CHARTS={'kpis':kpis,'activity':activity,'projects':project_commits,'languages':language_mix,
        'cadence':cadence,'versions':version_shelf,'heatmap':heatmap,'releases':release_radar}
RETIRED_ASSETS=tuple(f'assets/profile/{stem}-{theme}.svg'
                    for stem in ('ecosystem','ecosystem-mobile','spotlight-crates') for theme in THEMES)


def render(data,root=ROOT):
    validate(data)
    root=Path(root)
    outputs={'data/profile.json':json.dumps(data,indent=2,ensure_ascii=False)+'\n'}
    readme=root/'README.md'
    if readme.exists():
        # Refresh generated image metadata only; editorial text and links are untouched.
        original=readme.read_text(encoding='utf-8')
        outputs['README.md']=re.sub(r'(alt="[^"\n]*Snapshot: )\d{4}-\d{2}-\d{2}(\.)',
                                   lambda match:match[1]+data['as_of']+match[2],original)
    for theme in THEMES:
        for mobile in (False,True):
            suffix=f'{"mobile-" if mobile else ""}{theme}.svg'
            outputs[f'assets/profile/workspace-{suffix}']=cover(theme,mobile)
            outputs[f'assets/profile/architecture-{suffix}']=ecosystem_map(data,theme,mobile)
            for kind,name,category in FEATURED:
                outputs[f'assets/profile/spotlight-{kind}-{suffix}']=card(data,theme,kind,name,category,mobile)
            for name,renderer in CHARTS.items():
                outputs[f'assets/profile/{name}-{suffix}']=renderer(data,theme,mobile)
        for key in TOOLKIT:
            outputs[f'assets/profile/toolkit-{key}-{theme}.svg']=toolkit_icon(theme,key)
    total=0
    # No destination is touched until every document passes validation.
    for filename,contents in outputs.items():
        if filename.endswith('.svg'):
            tree=ET.fromstring(contents)
            if tree.tag!='{http://www.w3.org/2000/svg}svg':
                raise ValueError('Invalid SVG root')
            size=len(contents.encode('utf-8'));total+=size
            if size>300_000:
                raise ValueError(f'SVG exceeds 300 KB: {filename}')
    if total>4_000_000:
        raise ValueError('Profile SVGs exceed the 4 MB budget')
    staged=[]
    try:
        for filename,contents in outputs.items():
            destination=root/filename
            destination.parent.mkdir(parents=True,exist_ok=True)
            temporary=destination.with_suffix(destination.suffix+'.tmp')
            temporary.write_text(contents,encoding='utf-8')
            staged.append((temporary,destination))
        for temporary,destination in staged:
            temporary.replace(destination)
        for filename in RETIRED_ASSETS:
            (root/filename).unlink(missing_ok=True)
    finally:
        for temporary,_ in staged:
            temporary.unlink(missing_ok=True)
    return outputs
