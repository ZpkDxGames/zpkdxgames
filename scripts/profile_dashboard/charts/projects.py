def leaderboard(projects,limit=10):
    return sorted(projects,key=lambda p:(-p['commits_90d'],p['name'].lower()))[:limit]