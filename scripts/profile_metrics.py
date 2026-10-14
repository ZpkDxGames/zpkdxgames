#!/usr/bin/env python3
"""Generate repository-hosted profile visuals from public GitHub data (stdlib only)."""

import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import sys

# Keep imports working when loaded by the existing tests through importlib.
SCRIPTS=Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0,str(SCRIPTS))
from profile import DAYS,ROOT,THEMES,GitHub,collect,commit_day,eligible,release_version,render
from profile.toolkit import toolkit_icon


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner',default='ZpkDxGames')
    parser.add_argument('--snapshot',type=Path,help='Render a saved public snapshot without network access')
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})',args.owner):
        parser.error('Invalid GitHub username')
    data=json.loads(args.snapshot.read_text(encoding='utf-8')) if args.snapshot else collect(args.owner,datetime.now(timezone.utc).date())
    outputs=render(data)
    print(f"Rendered {len(outputs)} files for {data['owner']} as of {data['as_of']}.")


if __name__=='__main__':
    main()
