#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, shutil, sys, tempfile
from pathlib import Path
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'scripts'
if str(SCRIPTS) not in sys.path: sys.path.insert(0,str(SCRIPTS))
from profile_dashboard.collector import collect
from profile_dashboard.model import load_snapshot, validate_snapshot
from profile_dashboard.editorial import load_editorial
from profile_dashboard.render import write_all
from profile_dashboard.readme import compose

MAX_SVG=300_000
MAX_SET=5_000_000


def validate_assets(paths):
    total=0
    for p in paths:
        size=p.stat().st_size; total+=size
        if size>MAX_SVG: raise ValueError(f'asset exceeds 300 KB: {p.name}')
        root=ET.fromstring(p.read_text(encoding='utf-8'))
        if root.tag.split('}')[-1]!='svg': raise ValueError(f'not SVG: {p}')
        txt=p.read_text(encoding='utf-8')
        for forbidden in ('<script','<foreignObject'):
            if forbidden in txt: raise ValueError(f'forbidden SVG content {forbidden}: {p.name}')
        if 'href="http' in txt or 'src="http' in txt: raise ValueError(f'external SVG dependency: {p.name}')
        if 'role="img"' not in txt or '<title ' not in txt or '<desc ' not in txt: raise ValueError(f'accessibility metadata missing: {p.name}')
        if 'prefers-reduced-motion: reduce' not in txt or 'animation:none!important' not in txt:
            raise ValueError(f'reduced motion missing: {p.name}')
    if total>MAX_SET: raise ValueError(f'asset set exceeds 5 MB: {total}')
    return total


def _replace_tree(staged, target, backup):
    if backup.exists(): shutil.rmtree(backup)
    if target.exists(): target.rename(backup)
    staged.rename(target)


def _replace_file(staged, target, backup):
    if backup.exists(): backup.unlink()
    if target.exists(): target.rename(backup)
    os.replace(staged,target)


def install(staged_assets, readme_text, snapshot_text=None, root=ROOT):
    """Install a fully validated render as one rollback-capable transaction."""
    root=Path(root)
    target_assets=root/'assets/profile-dashboard'; backup_assets=root/'assets/profile-dashboard.previous'
    target_readme=root/'README.md'; backup_readme=root/'README.md.previous'
    target_data=root/'data/profile.json'; backup_data=root/'data/profile.json.previous'
    staged_tree=root/'assets/profile-dashboard.next'
    staged_readme=root/'README.md.next'
    staged_data=root/'data/profile.json.next' if snapshot_text is not None else None

    for old in (backup_assets,):
        if old.exists(): shutil.rmtree(old)
    for old in (backup_readme,backup_data):
        if old.exists(): old.unlink()
    if staged_tree.exists(): shutil.rmtree(staged_tree)
    if staged_readme.exists(): staged_readme.unlink()
    if staged_data is not None and staged_data.exists(): staged_data.unlink()

    shutil.copytree(staged_assets,staged_tree)
    staged_readme.write_text(readme_text,encoding='utf-8')
    if staged_data is not None:
        staged_data.parent.mkdir(parents=True,exist_ok=True)
        staged_data.write_text(snapshot_text,encoding='utf-8')

    had_assets=target_assets.exists(); had_readme=target_readme.exists(); had_data=target_data.exists()
    try:
        # Back up every existing target before installing any replacement.
        if had_assets: target_assets.rename(backup_assets)
        if had_readme: target_readme.rename(backup_readme)
        if staged_data is not None and had_data: target_data.rename(backup_data)

        staged_tree.rename(target_assets)
        os.replace(staged_readme,target_readme)
        if staged_data is not None: os.replace(staged_data,target_data)
    except Exception:
        if target_assets.exists(): shutil.rmtree(target_assets)
        if target_readme.exists(): target_readme.unlink()
        if staged_data is not None and target_data.exists(): target_data.unlink()
        if backup_assets.exists(): backup_assets.rename(target_assets)
        if backup_readme.exists(): backup_readme.rename(target_readme)
        if staged_data is not None and backup_data.exists(): backup_data.rename(target_data)
        raise
    else:
        if backup_assets.exists(): shutil.rmtree(backup_assets)
        if backup_readme.exists(): backup_readme.unlink()
        if backup_data.exists(): backup_data.unlink()
    finally:
        if staged_tree.exists(): shutil.rmtree(staged_tree)
        if staged_readme.exists(): staged_readme.unlink()
        if staged_data is not None and staged_data.exists(): staged_data.unlink()


def main():
    ap=argparse.ArgumentParser(description='Generate the GitHub profile engineering dashboard.')
    ap.add_argument('--snapshot',help='Offline snapshot JSON. Omit to collect from GitHub.')
    ap.add_argument('--owner',default='ZpkDxGames'); ap.add_argument('--days',type=int,default=90)
    args=ap.parse_args()
    editorial=load_editorial(ROOT/'data/project-editorial.json')
    fallback_activity=json.loads((ROOT/'data/project-main-activity.json').read_text())
    online=not args.snapshot
    snapshot=collect(args.owner,args.days) if online else load_snapshot(args.snapshot)
    validate_snapshot(snapshot)
    tmp=Path(tempfile.mkdtemp(prefix='profile-dashboard-'))
    try:
        generated=write_all(snapshot,editorial,fallback_activity,tmp/'assets')
        total=validate_assets(generated)
        readme=compose(snapshot,editorial)
        # Every generated README reference must resolve in the staged tree.
        for line in readme.splitlines():
            if 'assets/profile-dashboard/' in line and ('src=' in line or 'srcset=' in line):
                rel=line.split('assets/profile-dashboard/',1)[1].split('"',1)[0]
                if not (tmp/'assets'/rel).exists(): raise ValueError(f'missing README asset: {rel}')
        snapshot_text=json.dumps(snapshot,indent=2,sort_keys=True)+'\n' if online else None
        install(tmp/'assets',readme,snapshot_text,ROOT)
        print(f'Generated {len(generated)} SVGs ({total:,} bytes) from snapshot {snapshot["as_of"]}.')
    finally:
        shutil.rmtree(tmp,ignore_errors=True)


if __name__=='__main__': main()