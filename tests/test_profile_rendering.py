import hashlib, json, re, shutil, sys, tempfile, unittest
from pathlib import Path
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from profile_dashboard.model import load_snapshot
from profile_dashboard.editorial import load_editorial
from profile_dashboard.render import write_all, cadence_svg, languages_svg, radar_svg

class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.assets=ROOT/'assets/profile-dashboard'
    def test_expected_asset_count(self): self.assertEqual(len(list(self.assets.glob('*.svg'))),80)
    def test_all_svg_accessible_and_safe(self):
        for p in self.assets.glob('*.svg'):
            text=p.read_text(); root=ET.fromstring(text)
            self.assertEqual(root.tag.split('}')[-1],'svg',p.name)
            self.assertIn('role="img"',text,p.name); self.assertIn('<title ',text,p.name); self.assertIn('<desc ',text,p.name)
            self.assertIn('prefers-reduced-motion: reduce',text,p.name); self.assertIn('animation:none!important',text,p.name)
            self.assertNotIn('<script',text,p.name); self.assertNotIn('<foreignObject',text,p.name)
            self.assertNotIn('href="http',text,p.name); self.assertNotIn('src="http',text,p.name)
    def test_variants_exist(self):
        stems=['cover','status','activity','leaderboard','velocity','languages','cadence','versions','heatmap','publication-radar','activity-window','project-matrix','ecosystem','stack-topology']
        variants=['light','dark','mobile-light','mobile-dark']
        for s in stems:
            for v in variants:self.assertTrue((self.assets/f'{s}-{v}.svg').exists(),f'{s}-{v}')
    def test_asset_budgets(self):
        sizes=[p.stat().st_size for p in self.assets.glob('*.svg')]
        self.assertTrue(all(x<300_000 for x in sizes)); self.assertLess(sum(sizes),5_000_000)
    def test_readme_references_resolve(self):
        text=(ROOT/'README.md').read_text()
        refs=set(re.findall(r'assets/profile-dashboard/([^"\s>]+\.svg)',text))
        self.assertGreaterEqual(len(refs),32)
        for r in refs:self.assertTrue((self.assets/r).exists(),r)
    def test_picture_source_order(self):
        text=(ROOT/'README.md').read_text(); first=text[text.index('<picture>'):text.index('</picture>')]
        self.assertLess(first.index('mobile-dark.svg'),first.index('mobile-light.svg')); self.assertLess(first.index('mobile-light.svg'),first.rindex('-dark.svg'))
    def test_deterministic_render(self):
        d=load_snapshot(ROOT/'data/profile.json'); e=load_editorial(ROOT/'data/project-editorial.json'); a=json.loads((ROOT/'data/project-main-activity.json').read_text())
        with tempfile.TemporaryDirectory() as x, tempfile.TemporaryDirectory() as y:
            write_all(d,e,a,x); write_all(d,e,a,y)
            h=lambda base:{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(base).glob('*.svg')}
            self.assertEqual(h(x),h(y))
    def test_mobile_viewboxes(self):
        for p in self.assets.glob('*mobile*.svg'):
            self.assertRegex(p.read_text(),r'viewBox="0 0 500 \d+"')


    def test_empty_release_and_language_states_render(self):
        import copy
        from profile_dashboard.render import cadence_svg,languages_svg,radar_svg
        d=copy.deepcopy(load_snapshot(ROOT/'data/profile.json'))
        d['release_cadence_weekly']=[]; d['recent_releases']=[]
        d['totals']['published_releases_90d']=0; d['totals']['stable_releases_90d']=0; d['totals']['prereleases_90d']=0
        for p in d['projects']: p['latest_stable_release']=None
        self.assertIn('No published releases',cadence_svg(d,'dark',False))
        self.assertIn('No published releases',radar_svg(d,'light',True))
        d['languages']={}; d['totals']['language_bytes']=0
        self.assertIn('No language-byte data',languages_svg(d,'dark',False))

    def test_native_schema_uses_project_wide_sparkline_label(self):
        import copy, json, tempfile
        d=copy.deepcopy(load_snapshot(ROOT/'data/profile.json')); e=load_editorial(ROOT/'data/project-editorial.json'); a=json.loads((ROOT/'data/project-main-activity.json').read_text())
        for p in d['projects']: p['daily_commits']=[0]*90
        with tempfile.TemporaryDirectory() as tmp:
            write_all(d,e,a,tmp)
            text=(Path(tmp)/'project-plexonpanel-dark.svg').read_text()
        self.assertIn('PROJECT-WIDE · 90D',text)

if __name__=='__main__': unittest.main()
