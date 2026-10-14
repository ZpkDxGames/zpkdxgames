def buckets(projects):
    out={'Active in 30d':[],'Activity in 90d only':[],'No commits in 90d':[]}
    for p in projects:
        if p['commits_30d']>0: out['Active in 30d'].append(p['name'])
        elif p['commits_90d']>0: out['Activity in 90d only'].append(p['name'])
        else: out['No commits in 90d'].append(p['name'])
    return out