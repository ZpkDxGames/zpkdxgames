import json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from profile_dashboard.model import load_snapshot
from profile_dashboard.collector import _is_bot

class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d=load_snapshot(ROOT/'data/profile.json')
        cls.e=json.loads((ROOT/'data/project-editorial.json').read_text())
        cls.a=json.loads((ROOT/'data/project-main-activity.json').read_text())
    def test_scope_and_totals(self):
        self.assertEqual(self.d['totals']['projects'],30)
        self.assertEqual(self.d['totals']['commits_90d'],4419)
        self.assertEqual(self.d['totals']['commits_30d'],1112)
        self.assertEqual(self.d['totals']['active_30d'],10)
        self.assertEqual(sum(x['commits'] for x in self.d['daily']),4419)
        self.assertNotIn('zpkdxgames',{p['name'].lower() for p in self.d['projects']})
    def test_release_summary_reconciles(self):
        t=self.d['totals']; self.assertEqual(t['stable_releases_90d']+t['prereleases_90d'],t['published_releases_90d'])
        self.assertEqual(sum(w['stable']+w['prerelease'] for w in self.d['release_cadence_weekly']),192)
        self.assertEqual(t['published_releases_90d'],self.d['legacy_release_index']['published_count'])
    def test_languages_reconcile(self): self.assertEqual(sum(self.d['languages'].values()),11018100)
    def test_featured_activity_arrays_are_exact_window(self):
        self.assertEqual(set(self.a['projects']),{x['repo'] for x in self.e['featured']})
        self.assertTrue(all(len(v)==90 and all(isinstance(x,int) and x>=0 for x in v) for v in self.a['projects'].values()))
    def test_editorial_has_no_numeric_metric_fields(self):
        forbidden={'commits','stars','downloads','uptime','latency','users','percentage','releases'}
        for item in self.e['featured']:
            self.assertFalse(forbidden.intersection(item))
    def test_bot_detection(self):
        self.assertTrue(_is_bot({'author':{'type':'Bot','login':'x[bot]'},'commit':{'author':{'name':'x'}}}))
        self.assertFalse(_is_bot({'author':{'type':'User','login':'tonim'},'commit':{'author':{'name':'Tonim'}}}))
    def test_release_order_and_prerelease_shape(self):
        rr=self.d['recent_releases']; self.assertEqual(rr,sorted(rr,key=lambda r:r['published_at'],reverse=True))
        self.assertTrue(all(isinstance(r['prerelease'],bool) for r in rr))

if __name__=='__main__': unittest.main()