from datetime import datetime

def recent(snapshot,limit=10): return snapshot.get('recent_releases',snapshot.get('releases',[]))[:limit]
def stable_shelf(snapshot,names):
    pm={p['name']:p for p in snapshot['projects']}; return [(n,pm[n].get('latest_stable_release')) for n in names if n in pm]
def week_rows(snapshot): return snapshot.get('release_cadence_weekly',[])