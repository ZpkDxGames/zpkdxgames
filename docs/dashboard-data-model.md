# Dashboard data model

## Schema 3

The current generator emits schema 3. The top-level snapshot includes:

- `owner`;
- `as_of` and exact `generated_at`;
- `window` (`days`, `start`, `end`, `timezone`);
- explicit collection `scope` strings;
- reconciled `totals`;
- `projects`;
- aggregate `daily` activity;
- language byte totals;
- weekly release cadence;
- complete releases and a recent-release convenience slice on native refreshes.

Each native schema-3 project record contains:

```text
name
url
commits_90d
commits_30d
daily_commits[90]
language_bytes
primary_language
latest_stable_release
```

`daily_commits` is the canonical source for featured repository heartbeats after a native schema-3 collection.

## Collection scope

The collector includes only repositories that are public, owned by `ZpkDxGames`, non-fork, non-archived, non-disabled, and not the `zpkdxgames` profile repository.

Commit collection walks current branch tips, reads commits within the exact UTC window, excludes known bot identities, converts committer timestamps to UTC, and deduplicates commit SHA per repository. The resulting metric is explicitly **project-wide repository activity**, not the account owner's personal GitHub contribution count.

Language totals come from GitHub Linguist language-byte endpoints on default branches and are described as source volume. Published releases are ordered by publication timestamp; drafts are excluded and prerelease classification is preserved.

## Frozen compatibility snapshot

The delivered 2026-10-13 dataset began as a verified schema-2 snapshot. It contains exact project totals, aggregate daily activity, language bytes, and 192 complete release records at the source, but schema 2 did not persist per-project daily arrays.

`data/profile.json` is therefore a schema-3 **compatibility representation** that preserves all dashboard-facing exact totals, aggregate daily values, weekly release cadence, per-project latest stable publication, and the 20 newest release records. `legacy_release_index` records the exact original published-release count and explains that full native records return on the next schema-3 refresh.

`data/project-main-activity.json` is a narrowly scoped fallback for the six featured sparklines. It contains real daily commits reachable from each repository's `main` branch through the exact original snapshot timestamp. Those lines are visibly labeled `MAIN BRANCH · 90D`, never project-wide. The renderer ignores the fallback automatically whenever a project record contains native `daily_commits`.

This compatibility rule prevents the generator from inventing historical branch-level timelines that were not captured by the old schema.

## Editorial model

`data/project-editorial.json` contains only reviewed copy and taxonomy: category, verified state label, concise tagline, conceptual preview type, documented historical status, and technology grouping. Numeric repository metrics are deliberately excluded from editorial configuration so daily refreshes cannot drift across manually duplicated values.