"""Deterministic GitHub snapshot collector. Network is used only at generation time."""
from __future__ import annotations
import json, os, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone

API='https://api.github.com'
BOT_SUFFIXES=('[bot]','-bot')

def eligible_repo(repo, owner):
    return (repo.get('private') is False
            and repo.get('fork') is False
            and not repo.get('archived')
            and not repo.get('disabled')
            and (repo.get('owner') or {}).get('login','').lower()==owner.lower()
            and (repo.get('name') or '').lower()!=owner.lower())

def _get(path, token=None):
    req=urllib.request.Request(API+path, headers={'Accept':'application/vnd.github+json','User-Agent':'zpkdxgames-profile-dashboard','X-GitHub-Api-Version':'2022-11-28',**({'Authorization':f'Bearer {token}'} if token else {})})
    with urllib.request.urlopen(req, timeout=30) as r: return json.load(r)

def _pages(path, token=None):
    out=[]; page=1
    while True:
        sep='&' if '?' in path else '?'
        batch=_get(f'{path}{sep}per_page=100&page={page}',token)
        out.extend(batch)
        if len(batch)<100: return out
        page+=1

def _is_bot(commit):
    u=commit.get('author') or {}; raw=commit.get('commit') or {}; name=((raw.get('author') or {}).get('name') or '').lower(); login=(u.get('login') or '').lower()
    return u.get('type')=='Bot' or login.endswith(BOT_SUFFIXES) or name.endswith(BOT_SUFFIXES)

def collect(owner='ZpkDxGames', days=90, token=None, now=None):
    token=token or os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    end=now.date(); start=end-timedelta(days=days-1); dates=[start+timedelta(days=i) for i in range(days)]; index={d.isoformat():i for i,d in enumerate(dates)}
    repos=_pages(f'/users/{owner}/repos?type=owner&sort=full_name',token)
    repos=[r for r in repos if eligible_repo(r,owner)]
    projects=[]; all_releases=[]; languages={}; aggregate=[0]*days
    since=f'{start.isoformat()}T00:00:00Z'; until=now.isoformat().replace('+00:00','Z')
    for repo in sorted(repos,key=lambda x:x['name'].lower()):
        name=repo['name']; enc=urllib.parse.quote(name,safe=''); langs=_get(f'/repos/{owner}/{enc}/languages',token)
        for k,v in langs.items(): languages[k]=languages.get(k,0)+int(v)
        daily=[0]*days; seen=set()
        for branch in _pages(f'/repos/{owner}/{enc}/branches',token):
            sha=(branch.get('commit') or {}).get('sha');
            if not sha: continue
            path=f'/repos/{owner}/{enc}/commits?sha={urllib.parse.quote(sha)}&since={urllib.parse.quote(since)}&until={urllib.parse.quote(until)}'
            for c in _pages(path,token):
                if not c.get('sha') or c['sha'] in seen: continue
                seen.add(c['sha'])
                if _is_bot(c): continue
                ts=(((c.get('commit') or {}).get('committer') or {}).get('date'))
                if not ts: continue
                day=datetime.fromisoformat(ts.replace('Z','+00:00')).astimezone(timezone.utc).date().isoformat()
                if day in index: daily[index[day]]+=1
        for i,v in enumerate(daily): aggregate[i]+=v
        rels=[]
        for r in _pages(f'/repos/{owner}/{enc}/releases',token):
            if r.get('draft') or not r.get('published_at'): continue
            pub=datetime.fromisoformat(r['published_at'].replace('Z','+00:00')).astimezone(timezone.utc)
            if pub.date()<start or pub>now: continue
            rel={'project':name,'version':(r.get('tag_name') or '').lstrip('v'),'tag':r.get('tag_name') or '', 'published_at':r['published_at'],'prerelease':bool(r.get('prerelease')),'url':r.get('html_url')}
            rels.append(rel); all_releases.append(rel)
        stable=[r for r in sorted(rels,key=lambda x:x['published_at'],reverse=True) if not r['prerelease']]
        projects.append({'name':name,'url':repo['html_url'],'commits_90d':sum(daily),'commits_30d':sum(daily[-30:]),'daily_commits':daily,'language_bytes':langs,'primary_language':max(langs,key=langs.get) if langs else None,'latest_stable_release':stable[0] if stable else None})
    all_releases.sort(key=lambda r:(r['published_at'],r['project'],r['tag']),reverse=True)
    weekly={}
    for r in all_releases:
        dt=datetime.fromisoformat(r['published_at'].replace('Z','+00:00')).date(); monday=dt-timedelta(days=dt.weekday()); w=weekly.setdefault(monday.isoformat(),{'week':monday.isoformat(),'stable':0,'prerelease':0}); w['prerelease' if r['prerelease'] else 'stable']+=1
    stable_count=sum(not r['prerelease'] for r in all_releases); pre_count=len(all_releases)-stable_count
    return {'schema':3,'owner':owner,'as_of':end.isoformat(),'generated_at':until,'window':{'days':days,'start':start.isoformat(),'end':end.isoformat(),'timezone':'UTC'},'scope':{'repositories':'Public, owned, non-fork, non-archived, non-disabled repositories; profile repository excluded','commits':'Project-wide current branch histories, SHA-deduplicated per repository; known bots excluded; UTC committer timestamp','languages':'GitHub Linguist byte totals on default branches; source volume, not proficiency','releases':'Published releases in the window; drafts excluded; prerelease classification preserved'},'totals':{'projects':len(projects),'commits_90d':sum(p['commits_90d'] for p in projects),'commits_30d':sum(p['commits_30d'] for p in projects),'active_30d':sum(p['commits_30d']>0 for p in projects),'published_releases_90d':len(all_releases),'stable_releases_90d':stable_count,'prereleases_90d':pre_count,'language_bytes':sum(languages.values())},'projects':projects,'daily':[{'date':dates[i].isoformat(),'commits':aggregate[i]} for i in range(days)],'languages':dict(sorted(languages.items(),key=lambda kv:(-kv[1],kv[0]))),'release_cadence_weekly':[weekly[k] for k in sorted(weekly)],'releases':all_releases,'recent_releases':all_releases[:20]}