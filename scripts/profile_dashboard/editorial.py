import json
from pathlib import Path

def load_editorial(path): return json.loads(Path(path).read_text())
def featured_map(e): return {x['repo']:x for x in e['featured']}