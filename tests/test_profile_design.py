"""Integrity checks for the redesign's derived metrics and rendering contracts."""

import copy
from datetime import date
import json
from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from test_profile_metrics import metrics,FixtureAPI,release
from profile.model import (validate,latest_stable,weekly_releases,language_groups,
                           language_parts,age_of_latest_release,primary_language)
from profile.scales import sqrt_fraction,sqrt_ticks,rolling_average,heat_level
from profile.tokens import (THEMES,TEXT_TOKENS,TEXT_BACKGROUNDS,GRAPHIC_TOKENS,contrast,HEAT_BINS,HEAT_COLORS,MOTION)
from profile.editorial import GROUPS

ROOT=Path(__file__).resolve().parents[1]


class DesignIntegrityTests(unittest.TestCase):
    def snapshot(self):
        return metrics.collect('ZpkDxGames',date(2026,8,31),FixtureAPI())

    def test_every_text_surface_pair_has_required_contrast(self):
        for theme,tokens in THEMES.items():
            for foreground in TEXT_TOKENS:
                for background in TEXT_BACKGROUNDS:
                    with self.subTest(theme=theme,text=foreground,surface=background):
                        self.assertGreaterEqual(contrast(tokens[foreground],tokens[background]),4.5)
            for foreground in GRAPHIC_TOKENS:
                for background in TEXT_BACKGROUNDS:
                    self.assertGreaterEqual(contrast(tokens[foreground],tokens[background]),3)
        for colors in HEAT_COLORS.values():
            for background in colors:
                self.assertGreaterEqual(max(contrast(ink,background) for ink in ('#000000','#FFFFFF')),4.5)

    def test_square_root_scale_preserves_endpoints_and_small_counts(self):
        self.assertEqual(sqrt_fraction(0,0),0)
        self.assertEqual(sqrt_fraction(0,711),0)
        self.assertEqual(sqrt_fraction(711,711),1)
        self.assertGreater(sqrt_fraction(10,711),10/711)
        self.assertEqual(sorted(sqrt_fraction(v,711) for v in (0,1,10,100,711)),
                         [sqrt_fraction(v,711) for v in (0,1,10,100,711)])
        self.assertGreaterEqual(sqrt_ticks(711)[-1],711)
        with self.assertRaises(ValueError):sqrt_fraction(-1,711)

    def test_rolling_mean_is_arithmetic_before_transform_and_has_warmup(self):
        self.assertEqual(rolling_average([0,2,7,3],3),[0,1,3,4])
        self.assertEqual(rolling_average([0]*6+[70,0]),[0,0,0,0,0,0,10,10])
        self.assertEqual(rolling_average([]),[])

    def test_heatmap_bins_are_fixed_and_distinguish_high_days(self):
        self.assertEqual([heat_level(n) for n in (0,1,2,3,5,6,10,11,50,51,711)],
                         [0,1,1,2,2,3,3,4,4,5,5])
        self.assertEqual([label for _,label in HEAT_BINS],['0','1–2','3–5','6–10','11–50','51+'])

    def test_collector_adds_30_day_counts_without_changing_90_day_measure(self):
        data=self.snapshot()
        self.assertEqual(data['schema'],2)
        self.assertEqual([p['commits_30d'] for p in data['projects']],[0,2])
        self.assertEqual(sum(p['commits'] for p in data['projects']),3)
        self.assertEqual(sum(p['commits_30d'] for p in data['projects']),sum(d['commits'] for d in data['daily'][-30:]))

    def test_30_day_boundary_includes_first_day_and_excludes_prior_day(self):
        from test_profile_metrics import commit
        api=FixtureAPI()
        api.branches['tip-main']=[commit('prior','2026-08-01T23:59:59Z'),commit('first','2026-08-02T00:00:00Z')]
        api.branches['tip-release']=[]
        data=metrics.collect('ZpkDxGames',date(2026,8,31),api)
        self.assertEqual(data['projects'][1]['commits_30d'],1)
        self.assertEqual(data['projects'][1]['commits'],2)

    def test_stable_shelf_uses_publication_not_version_or_input_order(self):
        data=self.snapshot()
        data['releases']=[{'project':'Example','version':'9.0','tag':'v9.0','published_at':'2026-07-01T00:00:00Z','prerelease':False},
                          {'project':'Example','version':'1.0','tag':'v1.0','published_at':'2026-08-30T00:00:00Z','prerelease':False},
                          {'project':'Example','version':'10.0-rc.1','tag':'v10.0-rc.1','published_at':'2026-08-31T00:00:00Z','prerelease':True}]
        self.assertEqual(latest_stable(data)['Example']['version'],'1.0')
        self.assertNotIn('Empty',latest_stable(data))
        self.assertEqual(age_of_latest_release(data),0)

    def test_weekly_cadence_keeps_all_flags_and_partial_edge_weeks(self):
        data=self.snapshot();rows=weekly_releases(data)
        self.assertEqual(sum(r['stable'] for r in rows),2)
        self.assertEqual(sum(r['prerelease'] for r in rows),1)
        self.assertTrue(all(r['start'].weekday()==0 for r in rows))
        self.assertTrue(rows[0]['partial']);self.assertTrue(rows[-1]['partial'])

    def test_language_groups_partition_all_bytes_including_unknown_projects(self):
        data=json.loads((ROOT/'data/profile.json').read_text())
        groups=language_groups(data)
        self.assertEqual(sum(count for _,_,count in groups),len(data['projects']))
        self.assertEqual(sum(sum(c.values()) for _,c,_ in groups),sum(data['languages'].values()))
        self.assertEqual([count for _,_,count in groups],[23,6,1])
        self.assertEqual(language_parts({'A':990,'B':9,'C':1}),[('A',990),('Other',10)])
        self.assertEqual(language_parts({'A':99,'B':1}),[('A',99),('B',1)])
        self.assertEqual(primary_language({'languages':{}}),'—')

    def test_invalid_dates_counts_and_aggregates_fail_before_writing(self):
        for key in ('date','recent','language','negative'):
            data=self.snapshot()
            if key=='date':data['daily'][1]['date']=data['daily'][0]['date']
            if key=='recent':data['projects'][1]['commits_30d']=0
            if key=='language':data['languages']['Java']+=1
            if key=='negative':data['daily'][0]['commits']=-1
            with self.subTest(case=key),self.assertRaises(ValueError):validate(data)

    def test_every_chart_has_all_themes_and_layouts(self):
        data=self.snapshot()
        with tempfile.TemporaryDirectory() as tmp:outputs=metrics.render(data,Path(tmp))
        for stem in ('workspace','architecture','kpis','activity','projects','languages','cadence','versions','heatmap','releases'):
            for theme in THEMES:
                for mobile in ('','mobile-'):
                    name=f'assets/profile/{stem}-{mobile}{theme}.svg'
                    root=ET.fromstring(outputs[name])
                    self.assertIsNotNone(root.find('{http://www.w3.org/2000/svg}title'))
                    self.assertIsNotNone(root.find('{http://www.w3.org/2000/svg}desc'))
                    self.assertEqual(root.attrib['viewBox'].split()[2],'500' if mobile else '1000')

    def test_empty_and_zero_projects_do_not_invent_counts_or_versions(self):
        api=FixtureAPI();api.branches={'tip-main':[],'tip-release':[]};api.releases=[]
        data=metrics.collect('ZpkDxGames',date(2026,8,31),api)
        with tempfile.TemporaryDirectory() as tmp:outputs=metrics.render(data,Path(tmp))
        self.assertIn('No qualifying commits',outputs['assets/profile/projects-light.svg'])
        self.assertIn('No published releases',outputs['assets/profile/cadence-mobile-dark.svg'])
        self.assertIn('No stable publication',outputs['assets/profile/versions-light.svg'])
        self.assertEqual(age_of_latest_release(data),None)

    def test_svg_parse_failure_cannot_replace_good_files(self):
        data=self.snapshot()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);metrics.render(data,root)
            previous=(root/'assets/profile/workspace-light.svg').read_bytes()
            with patch('profile.render.cover',return_value='<svg>'):
                with self.assertRaises(ET.ParseError):metrics.render(data,root)
            self.assertEqual((root/'assets/profile/workspace-light.svg').read_bytes(),previous)

    def test_svg_budget_and_cover_display_paths(self):
        data=self.snapshot()
        with tempfile.TemporaryDirectory() as tmp:outputs=metrics.render(data,Path(tmp))
        sizes=[len(s.encode()) for name,s in outputs.items() if name.endswith('.svg')]
        self.assertLess(sum(sizes),4_000_000)
        self.assertLess(max(sizes),150_000)
        svg=outputs['assets/profile/workspace-light.svg']
        self.assertNotRegex(svg,r'<text[^>]*>Tonim')
        self.assertIn('aria-label="Tonim."',svg)
        self.assertEqual(svg.count('class="signal"'),1)
        self.assertGreaterEqual(MOTION['ambient_s'],14)

    def test_readme_paths_anchors_and_allowed_markup(self):
        source=(ROOT/'README.md').read_text()
        self.assertNotRegex(source,r'<(?:style|script|iframe)\b|\s(?:style|class)=')
        for p in re.findall(r'(?:src|srcset)="([^"]+)"',source):self.assertTrue((ROOT/p).exists(),p)
        anchors={'#'+re.sub(r'[^\w\- ]','',h.lower()).replace(' ','-') for h in re.findall(r'^#{1,6} (.+)$',source,re.M)}
        for anchor in re.findall(r'href="(#[^"]+)"',source):self.assertIn(anchor,anchors)
        for match in re.finditer(r'<picture>(.*?)</picture>',source,re.S):
            sources=re.findall(r'<source media="([^"]+)"',match[1])
            if len(sources)==3:
                self.assertEqual(sources,['(prefers-color-scheme: dark) and (max-width: 600px)','(max-width: 600px)','(prefers-color-scheme: dark)'])

    def test_generated_alt_date_refresh_preserves_editorial_and_links(self):
        source='<p>Editorial copy</p><a href="https://example.test">Link</a><img alt="Measured commits. Snapshot: 2020-01-01.">\n'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'README.md').write_text(source)
            outputs=metrics.render(self.snapshot(),root)
            self.assertEqual(outputs['README.md'],source.replace('2020-01-01','2026-08-31'))

    def test_all_snapshot_plexon_modules_are_listed_in_map_and_table(self):
        data=json.loads((ROOT/'data/profile.json').read_text())
        names={p['name'] for p in data['projects'] if p['name'].startswith('Plexon')}
        self.assertEqual(names,{n for _,rows in GROUPS for n in rows}|{'PlexonCore'})
        source=(ROOT/'README.md').read_text()
        for name in names:
            self.assertIn('https://github.com/ZpkDxGames/'+name,source)
            self.assertIn(name,(ROOT/'assets/profile/architecture-light.svg').read_text())


if __name__=='__main__':unittest.main()
