import json
from pathlib import Path

def load_snapshot(path):
    d=json.loads(Path(path).read_text())
    validate_snapshot(d)
    return d

def validate_snapshot(d):
    assert d['schema'] >= 3
    assert d['owner']=='ZpkDxGames'
    assert len(d['daily'])==d['window']['days']==90
    assert len(d['projects'])==d['totals']['projects']
    assert sum(p['commits_90d'] for p in d['projects'])==d['totals']['commits_90d']
    assert sum(p['commits_30d'] for p in d['projects'])==d['totals']['commits_30d']
    assert sum(d['languages'].values())==d['totals']['language_bytes']
    assert sum(x['commits'] for x in d['daily'])==d['totals']['commits_90d']
    assert d['totals']['stable_releases_90d']+d['totals']['prereleases_90d']==d['totals']['published_releases_90d']
    return d

def project_map(d): return {p['name']:p for p in d['projects']}