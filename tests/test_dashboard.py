"""Regression checks for truthful statistics and complete calendar fallbacks."""
import datetime as dt
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("dashboard", Path(__file__).resolve().parents[1]/"scripts/dashboard.py")
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)


class DataTests(unittest.TestCase):
    def test_tooltips_use_exact_counts_not_color_levels(self):
        parser = dashboard.ContributionParser()
        parser.feed('''<td id="a" data-date="2026-01-01" data-level="1"></td>
          <tool-tip for="a">1,204 contributions on January 1st.</tool-tip>
          <td id="b" data-date="2026-01-02" data-level="4"></td>
          <tool-tip for="b">1 contribution on January 2nd.</tool-tip>
          <td id="c" data-date="2026-01-03" data-level="0"></td>
          <tool-tip for="c">No contributions on January 3rd.</tool-tip>''')
        self.assertEqual(parser.days(), {"2026-01-01":1204,"2026-01-02":1,"2026-01-03":0})

    def test_unrecognized_tooltip_fails_coverage(self):
        parser = dashboard.ContributionParser()
        parser.feed('<td id="a" data-date="2026-01-01"></td><tool-tip for="a">Unexpected tooltip</tool-tip>')
        with self.assertRaises(ValueError):
            dashboard.validate_calendar(parser.days(), dt.date(2026,1,1), dt.date(2026,1,1))

    def test_incomplete_calendar_does_not_become_zeros(self):
        with self.assertRaises(ValueError):
            dashboard.validate_calendar({"2026-01-01":5}, dt.date(2026,1,1), dt.date(2026,1,2))

    def test_calendar_filters_extra_days_and_keeps_real_zero(self):
        days = dashboard.validate_calendar({"2025-12-31":999,"2026-01-01":0,"2026-01-02":6},
                                          dt.date(2026,1,1),dt.date(2026,1,2))
        self.assertEqual(days,[{"date":"2026-01-01","count":0},{"date":"2026-01-02","count":6}])

    def test_originals_exclude_private_forks_other_owners_and_profile(self):
        def repo(name, owner="ZpkDxGames", private=False, fork=False):
            return {"name":name,"owner":{"login":owner},"private":private,"fork":fork}
        repos = [repo("Original"),repo("ZPKDXGAMES"),repo("Secret",private=True),repo("Fork",fork=True),repo("Other",owner="Other")]
        self.assertEqual([r["name"] for r in dashboard.original_repositories(repos,"ZpkDxGames",["zpkdxgames"])],["Original"])

    def test_current_week_future_days_stay_unknown(self):
        snapshot={"calendar_end":"2026-10-14","days":[{"date":"2026-10-12","count":4},
                  {"date":"2026-10-13","count":7},{"date":"2026-10-14","count":0}]}
        weeks=dashboard.weekly_activity(snapshot)
        self.assertEqual(len(weeks),12)
        self.assertEqual(weeks[-1]["date"],dt.date(2026,10,12))
        self.assertEqual(weeks[-1]["days"],[4,7,0,None,None,None,None])
        self.assertEqual(weeks[-1]["count"],11)

    def test_language_other_preserves_denominator(self):
        snapshot={"language_bytes":dict(zip("ABCDEFG",[100,70,50,30,20,10,5]))}
        shares=dashboard.language_shares(snapshot)
        self.assertEqual(shares[-1],("Other",15/285))
        self.assertAlmostEqual(sum(share for _,share in shares),1)

    def test_xml_escapes_text_and_preserves_meaning(self):
        import xml.etree.ElementTree as ET
        canvas=dashboard.Canvas(420,200,"A & B","<source>")
        canvas.text(26,40,"<Java> & TypeScript",20)
        root=ET.fromstring(canvas.finish())
        self.assertEqual(root.find("{http://www.w3.org/2000/svg}text").text,"<Java> & TypeScript")


if __name__ == "__main__":
    unittest.main()
