import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from profile_dashboard.tokens import THEMES
from profile_dashboard.accessibility import contrast
from profile_dashboard.charts.heatmap import bin_for
from profile_dashboard.charts.activity import rolling,scaled

class DesignTests(unittest.TestCase):
    def test_contrast(self):
        for name,c in THEMES.items():
            self.assertGreaterEqual(contrast(c['text'],c['bg']),4.5,name)
            self.assertGreaterEqual(contrast(c['muted'],c['bg']),4.5,name)
            self.assertGreaterEqual(contrast(c['primary'],c['bg']),3,name)
            self.assertGreaterEqual(contrast(c['secondary'],c['bg']),3,name)
    def test_heatmap_fixed_bins(self):
        self.assertEqual([bin_for(x) for x in [0,1,2,3,5,6,10,11,50,51]],[0,1,1,2,2,3,3,4,4,5])
    def test_activity_math(self):
        self.assertEqual(rolling([1,2,3],2),[1,1.5,2.5])
        self.assertEqual(scaled(0,100,200),0); self.assertAlmostEqual(scaled(25,100,200),100)
    def test_peak_preserved(self):
        text=(ROOT/'assets/profile-dashboard/activity-dark.svg').read_text(); self.assertIn('PEAK 711 · 2026-09-12',text)
    def test_cliche_exclusions(self):
        text=(ROOT/'README.md').read_text().lower()
        for phrase in ['contribution snake','typing-text','visitor counter','matrix rain','proficiency bar','realtime system monitoring']:
            self.assertNotIn(phrase,text)

if __name__=='__main__': unittest.main()