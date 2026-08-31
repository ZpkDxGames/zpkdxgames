import copy
from datetime import date
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

SPEC = importlib.util.spec_from_file_location("profile_metrics", Path(__file__).resolve().parents[1] / "scripts/profile_metrics.py")
metrics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(metrics)


def repository(name, **changes):
    result = dict(name=name, owner={"login": "ZpkDxGames"}, private=False, visibility="public",
                  fork=False, archived=False, disabled=False, size=1,
                  pushed_at="2026-08-31T12:00:00Z", html_url=f"https://github.com/ZpkDxGames/{name}")
    result.update(changes)
    return result


def commit(sha, timestamp, author="Tonim"):
    return {"sha": sha, "author": {"login": author, "type": "User"},
            "commit": {"author": {"name": author, "email": "never-publish@example.test"},
                       "message": "Do not publish commit text", "committer": {"date": timestamp}}}


def release(tag, published, **changes):
    result = dict(tag_name=tag, published_at=published, draft=False, prerelease=False,
                  assets=[], html_url=f"https://github.com/ZpkDxGames/Example/releases/tag/{tag}")
    result.update(changes)
    return result


class FixtureAPI:
    def __init__(self):
        self.calls = []
        self.repositories = [repository("Example"), repository("Empty", size=0),
                             repository("PrivateSecret", private=True, visibility="private"),
                             repository("Fork", fork=True), repository("Archived", archived=True),
                             repository("zpkdxgames"), repository("NotMine", owner={"login": "elsewhere"})]
        shared = commit("shared", "2026-08-10T10:00:00Z")
        self.branches = {"tip-main": [shared, commit("start", "2026-06-03T00:00:00Z"),
                                       commit("old", "2026-06-02T23:59:59Z"),
                                       commit("bot", "2026-08-11T12:00:00Z", "github-actions[bot]")],
                         "tip-release": [shared, commit("latest", "2026-08-31T23:59:59Z"),
                                          commit("future", "2026-09-01T00:00:00Z")]}
        self.releases = [release("v1.0", "2026-07-01T00:00:00Z"),
                         release("Release", "2026-08-31T10:00:00Z", assets=[{"name": "Example-2.0.1.jar"}]),
                         release("v2.1-beta", "2026-08-30T10:00:00Z", prerelease=True),
                         release("draft", "2026-08-31T11:00:00Z", draft=True),
                         release("old", "2026-01-01T00:00:00Z"), release("unpublished", None)]

    def items(self, path, **params):
        self.calls.append((path, params))
        if path.startswith("/users/"):
            return iter(self.repositories)
        self._check_project(path)
        if path.endswith("/branches"):
            return iter([{"name": name, "commit": {"sha": sha}} for name, sha in
                         [("main", "tip-main"), ("release/2.0", "tip-release")]])
        if path.endswith("/commits"):
            return iter(self.branches[params["sha"]])
        if path.endswith("/releases"):
            return iter(self.releases if "/Example/" in path else [])
        raise AssertionError(path)

    def get(self, path, **params):
        self.calls.append((path, params))
        self._check_project(path)
        if path.endswith("/languages"):
            return {"Java": 120, "HTML": 30} if "/Example/" in path else {}
        raise AssertionError(path)

    def _check_project(self, path):
        if path.split("/")[3] not in {"Example", "Empty"}:
            raise AssertionError(f"Out-of-scope API read: {path}")


class ProfileMetricsTests(unittest.TestCase):
    def snapshot(self):
        return metrics.collect("ZpkDxGames", date(2026, 8, 31), FixtureAPI())

    def test_public_scope_and_no_sensitive_payloads(self):
        data = self.snapshot()
        self.assertEqual([p["name"] for p in data["projects"]], ["Empty", "Example"])
        encoded = json.dumps(data)
        for sensitive in ["PrivateSecret", "never-publish", "commit text", "NotMine"]:
            self.assertNotIn(sensitive, encoded)
        unknown = repository("Unknown")
        unknown.pop("private")
        self.assertFalse(metrics.eligible(unknown, "ZpkDxGames"))

    def test_deduplication_window_and_bot_exclusion(self):
        data = self.snapshot()
        self.assertEqual(len(data["daily"]), 90)
        days = {d["date"]: d["commits"] for d in data["daily"]}
        self.assertEqual(sum(days.values()), 3)
        self.assertEqual(days["2026-06-03"], 1)
        self.assertEqual(days["2026-08-31"], 1)
        self.assertEqual(days["2026-08-10"], 1)
        self.assertEqual(days["2026-08-11"], 0)
        self.assertEqual(sum(p["commits"] for p in data["projects"]), 3)

    def test_committer_dates_are_converted_to_utc(self):
        row = commit("offset", "2026-08-31T00:30:00+03:00")
        self.assertEqual(metrics.commit_day(row), date(2026, 8, 30))

    def test_release_order_uses_publication_time_and_retains_prereleases(self):
        rows = self.snapshot()["releases"]
        self.assertEqual([r["version"] for r in rows], ["2.0.1", "2.1-beta", "1.0"])
        self.assertTrue(rows[1]["prerelease"])

    def test_languages_are_byte_counts_not_repo_counts(self):
        self.assertEqual(self.snapshot()["languages"], {"Java": 120, "HTML": 30})

    def test_real_pagination_reads_next_page(self):
        api = metrics.GitHub()
        calls = []
        def fake_get(path, **params):
            calls.append(params["page"])
            return list(range(100)) if params["page"] == 1 else [100]
        api.get = fake_get
        self.assertEqual(list(api.items("/test")), list(range(101)))
        self.assertEqual(calls, [1, 2])

    def test_empty_window_renders_without_division_by_zero(self):
        api = FixtureAPI()
        api.repositories = []
        data = metrics.collect("ZpkDxGames", date(2026, 8, 31), api)
        with tempfile.TemporaryDirectory() as temporary:
            outputs = metrics.render(data, Path(temporary))
        self.assertEqual(len(outputs), 9)
        self.assertIn("No published releases", outputs["assets/profile/releases-dark.svg"])

    def test_svg_is_valid_accessible_and_deterministic(self):
        data = self.snapshot()
        data["projects"][1]["name"] = 'A & B <test>'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = metrics.render(data, root)
            second = metrics.render(data, root)
            self.assertEqual(first, second)
            for path, contents in first.items():
                if not path.endswith(".svg"):
                    continue
                tree = ET.fromstring(contents)
                self.assertEqual(tree.attrib["role"], "img")
                self.assertIn("prefers-reduced-motion:reduce", contents)
                self.assertNotIn("<script", contents)
                self.assertNotIn("<foreignObject", contents)
                self.assertNotIn("https://", contents)

    def test_bad_snapshot_cannot_replace_last_good_files(self):
        data = self.snapshot()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = metrics.render(data, root)
            broken = copy.deepcopy(data)
            broken["daily"][0]["commits"] += 1
            with self.assertRaises(ValueError):
                metrics.render(broken, root)
            for path, contents in original.items():
                self.assertEqual((root / path).read_text(), contents)


if __name__ == "__main__":
    unittest.main()
