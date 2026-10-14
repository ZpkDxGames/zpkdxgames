def rows(projects,limit=12):
    return sorted(projects,key=lambda p:(-p['commits_90d'],p['name'].lower()))[:limit]