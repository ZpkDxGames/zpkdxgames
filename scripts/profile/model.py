"""Validation and derived aggregates; all numbers come from the snapshot."""

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from .collector import DAYS
from .editorial import SERVER_PROJECTS, WEB_PROJECTS


def publication_time(release):
    return datetime.fromisoformat(release["published_at"].replace("Z", "+00:00")).astimezone(timezone.utc)


def validate(data):
    if data.get("schema") not in (1, 2) or data.get("days") != DAYS:
        raise ValueError("Unexpected profile snapshot format")
    start, end = date.fromisoformat(data["start"]), date.fromisoformat(data["as_of"])
    if (end-start).days != DAYS-1 or len(data.get("daily", [])) != DAYS:
        raise ValueError("Expected exactly 90 consecutive UTC calendar days")
    for i, row in enumerate(data["daily"]):
        if row["date"] != (start + timedelta(days=i)).isoformat():
            raise ValueError("Daily dates must be consecutive and ordered")
        if type(row["commits"]) is not int or row["commits"] < 0:
            raise ValueError("Commit counts must be nonnegative integers")
    names = set()
    languages = Counter()
    for p in data["projects"]:
        if p["name"] in names:
            raise ValueError("Duplicate project")
        names.add(p["name"])
        if type(p["commits"]) is not int or p["commits"] < 0:
            raise ValueError("Project counts must be nonnegative integers")
        for amount in p["languages"].values():
            if type(amount) is not int or amount < 0:
                raise ValueError("Language totals must be nonnegative integers")
        languages.update(p["languages"])
        if data["schema"] == 2:
            v = p.get("commits_30d")
            if type(v) is not int or not 0 <= v <= p["commits"]:
                raise ValueError("Invalid 30-day project aggregate")
    if sum(d["commits"] for d in data["daily"]) != sum(p["commits"] for p in data["projects"]):
        raise ValueError("Daily and project totals do not agree")
    if dict(languages) != data["languages"]:
        raise ValueError("Global and project language byte totals do not agree")
    if data["schema"] == 2 and sum(p["commits_30d"] for p in data["projects"]) != sum(d["commits"] for d in data["daily"][-30:]):
        raise ValueError("Recent daily and project totals do not agree")
    for r in data["releases"]:
        if r["project"] not in names or not start <= publication_time(r).date() <= end:
            raise ValueError("Release lies outside the public project snapshot")
        if type(r["prerelease"]) is not bool:
            raise ValueError("Release must identify its prerelease flag")


def ordered_releases(data):
    return sorted(data["releases"], key=lambda r: (publication_time(r), r["project"], r["tag"]), reverse=True)


def latest_stable(data):
    result = {}
    for r in ordered_releases(data):
        if not r["prerelease"]:
            result.setdefault(r["project"], r)
    return result


def primary_language(project):
    return min(project["languages"], key=lambda k: (-project["languages"][k], k)) if project and project["languages"] else "—"


def age_of_latest_release(data):
    rows = ordered_releases(data)
    return (date.fromisoformat(data["as_of"])-publication_time(rows[0]).date()).days if rows else None


def weekly_releases(data):
    start, end = date.fromisoformat(data["start"]), date.fromisoformat(data["as_of"])
    monday = start-timedelta(days=start.weekday())
    rows = [{"start": monday+timedelta(days=7*i), "stable": 0, "prerelease": 0,
             "partial": monday+timedelta(days=7*i) < start or monday+timedelta(days=7*i+6) > end}
            for i in range((end-monday).days//7+1)]
    for r in data["releases"]:
        i = (publication_time(r).date()-monday).days//7
        rows[i]["prerelease" if r["prerelease"] else "stable"] += 1
    return rows


def language_groups(data):
    groups = [("Server & plugin", Counter(), 0), ("Web & interface", Counter(), 0), ("Other projects", Counter(), 0)]
    for p in data["projects"]:
        i = 0 if p["name"] in SERVER_PROJECTS else 1 if p["name"] in WEB_PROJECTS else 2
        label, counter, count = groups[i]
        counter.update(p["languages"])
        groups[i] = label, counter, count+1
    return groups


def language_parts(counts, threshold=.01):
    total = sum(counts.values())
    rows = sorted(((k, v) for k, v in counts.items() if v), key=lambda r: (-r[1], r[0]))
    visible = [(k, v) for k, v in rows if total and v/total >= threshold]
    small = sum(v for _, v in rows)-sum(v for _, v in visible)
    return visible+([("Other", small)] if small else [])
