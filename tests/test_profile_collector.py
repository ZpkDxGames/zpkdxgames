import sys, unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from profile_dashboard import collector


def repo(name, **kw):
    d={'name':name,'private':False,'fork':False,'archived':False,'disabled':False,
       'owner':{'login':'ZpkDxGames'},'html_url':f'https://github.com/ZpkDxGames/{name}'}
    d.update(kw); return d


def commit(sha, ts, login='tonim', kind='User', author_name='Tonim'):
    return {'sha':sha,'author':{'login':login,'type':kind},
            'commit':{'author':{'name':author_name},'committer':{'date':ts}}}


class CollectorTests(unittest.TestCase):
    def test_repo_scope_filter(self):
        valid=repo('Example')
        self.assertTrue(collector.eligible_repo(valid,'ZpkDxGames'))
        for bad in [repo('P',private=True),repo('F',fork=True),repo('A',archived=True),repo('D',disabled=True),repo('zpkdxgames'),repo('O',owner={'login':'elsewhere'})]:
            self.assertFalse(collector.eligible_repo(bad,'ZpkDxGames'))

    def test_collection_deduplicates_sha_uses_utc_and_filters_releases(self):
        repos=[repo('Example'),repo('Private',private=True),repo('Fork',fork=True),repo('zpkdxgames')]
        shared=commit('same','2026-08-29T00:00:00Z')
        later=commit('later','2026-08-31T11:00:00Z')
        bot=commit('bot','2026-08-30T12:00:00Z','build[bot]','Bot','build[bot]')
        # Local date is Aug 29 but UTC date is Aug 28, outside the 3-day window.
        offset_out=commit('offset','2026-08-29T00:30:00+03:00')
        branches={'a':[shared,later,bot,offset_out],'b':[shared]}
        releases=[
            {'draft':False,'published_at':'2026-08-30T10:00:00Z','tag_name':'v1.0.0','prerelease':False,'html_url':'stable'},
            {'draft':False,'published_at':'2026-08-31T11:30:00Z','tag_name':'v1.1.0-rc.1','prerelease':True,'html_url':'pre'},
            {'draft':True,'published_at':'2026-08-31T09:00:00Z','tag_name':'v9','prerelease':False,'html_url':'draft'},
            {'draft':False,'published_at':'2026-08-31T13:00:00Z','tag_name':'v2','prerelease':False,'html_url':'future'}]

        def fake_pages(path, token=None):
            if path.startswith('/users/'): return repos
            if path.endswith('/branches'): return [{'name':'main','commit':{'sha':'a'}},{'name':'feature','commit':{'sha':'b'}}]
            if '/commits?' in path:
                sha='a' if 'sha=a' in path else 'b'; return branches[sha]
            if path.endswith('/releases'): return releases
            raise AssertionError(path)
        def fake_get(path, token=None):
            if path.endswith('/languages'): return {'Java':100,'HTML':20}
            raise AssertionError(path)

        now=datetime(2026,8,31,12,0,0,tzinfo=timezone.utc)
        with patch.object(collector,'_pages',fake_pages), patch.object(collector,'_get',fake_get):
            d=collector.collect(now=now,days=3)
        self.assertEqual(d['totals']['projects'],1)
        self.assertEqual(d['projects'][0]['daily_commits'],[1,0,1])
        self.assertEqual(d['projects'][0]['commits_90d'],2)
        self.assertEqual(d['daily'],[{'date':'2026-08-29','commits':1},{'date':'2026-08-30','commits':0},{'date':'2026-08-31','commits':1}])
        self.assertEqual(d['totals']['published_releases_90d'],2)
        self.assertEqual(d['totals']['stable_releases_90d'],1)
        self.assertEqual(d['totals']['prereleases_90d'],1)
        self.assertEqual([r['tag'] for r in d['releases']],['v1.1.0-rc.1','v1.0.0'])
        self.assertEqual(d['totals']['language_bytes'],120)

if __name__=='__main__': unittest.main()