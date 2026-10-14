#!/usr/bin/env python3
"""Render GitHub profile SVGs from public repository data, using only the stdlib."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
import json
import math
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

DAYS = 90


class GitHub:
    def __init__(self):
        self.headers = {"Accept": "application/vnd.github+json",
                        "User-Agent": "ZpkDxGames-profile-metrics",
                        "X-GitHub-Api-Version": "2022-11-28"}
        if token := os.environ.get("GH_TOKEN"):
            self.headers["Authorization"] = f"Bearer {token}"

    def get(self, path, **params):
        url = "https://api.github.com" + path
        if params:
            url += "?" + urlencode(params)
        for attempt in range(3):
            try:
                with urlopen(Request(url, headers=self.headers), timeout=30) as response:
                    return json.load(response)
            except HTTPError as error:
                if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise RuntimeError(f"GitHub returned HTTP {error.code} for {path}") from None
            except (URLError, TimeoutError):
                if attempt == 2:
                    raise RuntimeError(f"GitHub request failed for {path}") from None
            time.sleep(2 ** attempt)
        raise RuntimeError(f"GitHub request failed for {path}")

    def items(self, path, **params):
        # Fail instead of silently publishing truncated metrics.
        for page in range(1, 101):
            batch = self.get(path, per_page=100, page=page, **params)
            if not isinstance(batch, list):
                raise ValueError(f"Expected a GitHub list for {path}")
            yield from batch
            if len(batch) < 100:
                return
        raise RuntimeError(f"Pagination limit exceeded for {path}")


def eligible(repo, owner):
    """A public profile must not reveal private repos, forks, or other owners."""
    return (repo.get("private") is False and repo.get("visibility", "public") == "public"
            and repo.get("fork") is False and not repo.get("archived")
            and not repo.get("disabled")
            and repo.get("owner", {}).get("login", "").casefold() == owner.casefold()
            and repo.get("name", "").casefold() != owner.casefold())


def commit_day(commit):
    author = commit.get("author") or {}
    raw = commit.get("commit") or {}
    author_name = (raw.get("author") or {}).get("name", "")
    if (author.get("type") == "Bot" or author.get("login", "").endswith("[bot]")
            or author_name.endswith("[bot]")):
        return None
    timestamp = (raw.get("committer") or {}).get("date")
    if not timestamp:
        raise ValueError("Commit is missing its committer timestamp")
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(timezone.utc).date()


def release_version(release):
    tag = release.get("tag_name", "")
    if re.fullmatch(r"v?\d+(?:\.\d+)+(?:[-+][\w.-]+)?", tag):
        return tag.removeprefix("v")
    for asset in release.get("assets", []):
        match = re.search(r"[-.](\d+\.\d+(?:\.\d+)?(?:-[\w.-]+)?)\.jar$", asset.get("name", ""))
        if match:
            return match.group(1)
    return tag or "untagged"


def collect(owner, today, api=None):
    api = api or GitHub()
    start = today - timedelta(days=DAYS - 1)
    all_repos = list(api.items(f"/users/{owner}/repos", type="owner", sort="full_name"))
    repos = sorted((r for r in all_repos if eligible(r, owner)), key=lambda r: r["name"].casefold())
    projects, releases = [], []
    daily, languages = Counter(), Counter()
    for repo in repos:
        path = f"/repos/{owner}/{repo['name']}"
        language_bytes = api.get(path + "/languages")
        languages.update(language_bytes)
        seen, project_days = set(), Counter()
        # Pushed-at is only a request-saving gate, never the metric itself.
        if (repo.get("size", 0) > 0 and repo.get("pushed_at")
                and repo["pushed_at"][:10] >= start.isoformat()):
            for branch in api.items(path + "/branches"):
                # Snapshot immutable tips so a branch move cannot mix histories.
                for commit in api.items(path + "/commits", sha=branch["commit"]["sha"],
                                        since=start.isoformat() + "T00:00:00Z",
                                        until=today.isoformat() + "T23:59:59Z"):
                    if commit["sha"] in seen:
                        continue
                    seen.add(commit["sha"])
                    day = commit_day(commit)
                    if day is not None and start <= day <= today:
                        project_days[day.isoformat()] += 1
        daily.update(project_days)
        projects.append({"name": repo["name"], "url": repo["html_url"],
                         "commits": sum(project_days.values()), "languages": language_bytes,
                         "commits_30d": sum(v for day, v in project_days.items()
                                            if day >= (today - timedelta(days=29)).isoformat())})
        for release in api.items(path + "/releases"):
            published = release.get("published_at")
            if release.get("draft") or not published:
                continue
            published_day = datetime.fromisoformat(published.replace("Z", "+00:00")).astimezone(timezone.utc).date()
            if start <= published_day <= today:
                releases.append({"project": repo["name"], "version": release_version(release),
                                 "tag": release["tag_name"], "published_at": published,
                                 "prerelease": bool(release.get("prerelease")), "url": release["html_url"]})
    releases.sort(key=lambda r: (r["published_at"], r["project"], r["tag"]), reverse=True)
    return {"schema": 2, "owner": owner, "as_of": today.isoformat(), "days": DAYS,
            "start": start.isoformat(), "scope": "Public, owned, non-fork, non-archived projects; profile excluded",
            "commit_scope": "All authors except bots; current branch histories deduplicated per repository; UTC committer date",
            "language_scope": "GitHub Linguist byte counts on default branches; not a measure of proficiency",
            "projects": projects,
            "daily": [{"date": (start + timedelta(days=i)).isoformat(),
                       "commits": daily[(start + timedelta(days=i)).isoformat()]} for i in range(DAYS)],
            "languages": dict(sorted(languages.items(), key=lambda x: (-x[1], x[0]))),
            "releases": releases}


