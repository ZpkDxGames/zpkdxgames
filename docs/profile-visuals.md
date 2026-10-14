# Profile visuals and measurement

## Editorial design

The profile is an engineering portfolio front page: a compact cover, a dated four-metric strip, six selected projects, a separate web/interface lane, a complete Plexon overview, measured charts, a refined toolkit, background and contact. It uses the existing midnight-blue, violet and cyan family. [Design tokens](design-tokens.md) define colours, contrast, typography and motion; [recon](recon-note.md) and [design decisions](design-decisions.md) record the source checks and choices.

The featured projects are PlexonPanel, PlexonTools, PlexonQuests, PlexonChats, AI Desktop Companion and PlexonCore. Current source explicitly retires PlexonCrates, so it remains historical work in the ecosystem and statistics rather than a headline product. PlexonGriefPreventionAddon is labelled deprecated, with GPFlags identified as its replacement. These editorial statuses do not override GitHub's archive/fork metadata for metrics.

All 21 Plexon repositories in the 2026-10-13 snapshot appear in the overview and native link table. The overview groups responsibilities; it is **not a dependency contract**. Core adoption and each module's actual runtime requirements belong to its README. The generator places any future unknown Plexon module in an additional group; the native table remains curated and must be reviewed when projects change.

Project art is conceptual, not screenshots or live telemetry. Each card has native title, description and links beside generated vitals: latest stable **within the snapshot window**, project-wide 90-day commits and primary language by byte volume. A dash means no qualifying stable publication. AI Desktop Companion remains an alpha with AI actions disabled; Panel rollout remains subject to its recorded gates.

Web/interface work includes Panel Dashboard, Neural Core Dashboard, Conan Gray Bot's interface source and Triangle Area. Existing portfolio and creator-hub links remain visible. No functioning Conan Gray Bot public demo was verified: the repository's advertised homepage returned 404, so it is omitted.

## Generator structure

Python **3.10+**, standard library only. `scripts/profile_metrics.py` remains the workflow entry point and import-compatible collection facade. The package contains:

| File | Responsibility |
| --- | --- |
| `collector.py` | Public API reads, pagination, bounded retries, immutable branch tips, SHA deduplication |
| `model.py` | Snapshot validation, derived release/version/language metrics |
| `tokens.py` | Theme, contrast, heatmap and motion tokens |
| `scales.py` | Square-root transform, raw-count ticks, arithmetic rolling mean, fixed bins |
| `draw.py` | Escaped SVG primitives, system fonts, cover paths, accessibility and motion |
| `cover.py`, `cards.py`, `ecosystem.py` | Artwork and dedicated narrow layouts |
| `charts/` | Eight measured chart families from the same snapshot |
| `editorial.py` | Explicit project classification and curation |
| `toolkit.py` | Static wrappers around unchanged vendored marks |
| `render.py` | Validate, render, parse, stage and replace outputs |

There are **94 generated SVGs**. Every full-width chart, cover, map and selected-work card has light/dark and desktop/mobile variants. The 30 toolkit assets share compact static layouts. Toolkit sources and [credits](toolkit-icons.md) remain intact. Cover-outline font licensing is stored separately.

The `<picture>` source order is dark+mobile, mobile, dark, default light. Mobile is selected below 600 px; every chart preserves its data and meaning. The six-card table uses GitHub-safe HTML and wrapping native text. No README styles, scripts, classes, inline CSS, badges, tracking images or remote widgets are used. Calendar and radar are collapsed in `<details>`.

## Data boundaries

- Only **public, owned, non-fork, non-archived, enabled repositories** are included. The profile repository is excluded so its refresh commits and Python generator do not distort the graphs.
- The window contains **90 UTC calendar days**, including the snapshot date. The last day can be incomplete.
- Activity counts **project commits**, not personal GitHub contributions. All authors are included except identifiable bot authors. Each SHA is counted once per repository across its current branch histories. Deleted branches and unreferenced commits are not reconstructed.
- Branch tips are resolved to immutable SHAs before commits are fetched. The UTC **committer date** determines the day. Repositories not pushed since the window began skip commit lookups.
- Language mix comes from GitHub's language byte totals on each repository's **default branch**. Release branches may contain newer code. Language percentages describe public source volume, not skill or time spent.
- Release counts include published releases and pre-releases within the window. Drafts are excluded. Ordering uses **publication timestamp**, not tag name or API response order. Numeric tags supply versions; nonnumeric tags can use a version in a published JAR filename. Source branches without a published release are not counted.
- Stable means GitHub's `prerelease` flag is false. It does **not** certify production readiness or deployment. “Prerelease” includes all flagged releases, not only tags named RC.
- `data/profile.json` stores only public project names, links, aggregate counts, language bytes and published release metadata. No tokens, commit messages, SHAs, author emails or private repository details are retained.
- Fork exclusion follows GitHub metadata. Upstream-derived work not marked as a fork may remain in totals; known upstream-based work is credited separately.

These collection boundaries and 90-day definitions are unchanged. The schema addition and heatmap display change below are explicit.

## Schema 2 and the 30-day metric

Schema 1 had per-project 90-day counts but only a global daily timeline; it could not answer how many projects were active in the last 30 days. Schema 2 adds one integer, `projects[].commits_30d`, for the **30 UTC calendar days including `as_of`**. A project is active if that integer is positive. Future collection computes it from the same deduplicated per-project day counter; no additional API endpoints are required.

The supplied snapshot was enriched by reading public commits against **394 distinct immutable branch tips**, bounded to 2026-09-14 through the profile snapshot's commit at 2026-10-13T14:28:56Z. Both transient read errors were retried successfully. All **30 individual daily totals** reconciled with the original global series: 1,112 recent commits in 10 projects. The 4,419 total commits, 192 releases, language bytes, window and as-of date remain unchanged.

Validation requires nonnegative integers, `commits_30d ≤ commits`, agreement of recent project sums with the final 30 daily rows, agreement of all 90-day totals, matching global/project byte sums, unique projects, consecutive dates and releases within the window. Schema-1 offline input is still supported; its unavailable 30-day value displays `—`, never a substituted estimate.

## Charts

| Asset | Measure and design |
| --- | --- |
| `kpis` | Public project count; 90-day project commits; 90-day stable+prerelease publication count; 30-day active project count. Exact values and date. |
| `activity` | All 90 daily bars on a **square-root** axis with raw-count ticks. Trailing seven-calendar-day arithmetic mean is computed **before** transforming; at the window start it uses available days only. Peak annotation is date/count only. No caps or dropped days. |
| `projects` | Top ten project commits, zero-based linear bars, names and exact counts. A zero window renders valid empty bars and text. |
| `languages` | Total byte share, then server/plugin, web/interface and other-project views. Percentages are rounded to 0.1%. Languages below 1% **within each view** become Other; the exact total is preserved. |
| `cadence` | Monday-first UTC weekly stable/prerelease counts; partial first/last weeks marked. Exact stable, prerelease and total counts. Linear stacked heights. |
| `versions` | Latest stable publication by timestamp per selected major project, **within the window**, with publication date. Missing stable releases display `—`. |
| `heatmap` | Same 90 daily counts, Monday-first UTC calendar. Fixed bins **0 / 1–2 / 3–5 / 6–10 / 11–50 / 51+**. This intentionally replaces the prior top bin `11+`. Nonzero counts print in cells; all values also remain in titles/data. Active days are nonzero dates, not a coding streak. |
| `releases` | Six latest publications sorted by UTC timestamp, explicit stable/prerelease flags, computed age and latest activity date. Publication is not deployment certification. |

Every measured chart states its window and as-of date, includes `<title>`/`<desc>`, has a meaningful README alt label and keeps all information visible with motion off.

### Repository-purpose language split

The split partitions **all source bytes**, not selected languages. Server/plugin includes the 20 non-dashboard Plexon projects plus GhostBlocks, DropsEditor and Rankup-1.2Fixer (23 projects). Web/interface includes AI-Desktop-Companion, ConanGrayBot-Page, Neural-Core-Dashboard, PlexonPanel-Dashboard, Trabalho-III-Eng.-Prompt and Triangle-Area (6). ConanGrayBot-Core is Other (1). Unknown future repositories go to Other until classification is verified.

A web/interface repository may include native or backend code. No files are moved between groups based on their language. Each group shows its own exact byte total and within-group share; it does not imply an equal-sized portfolio slice or skill level.

## Refresh and write safety

`.github/workflows/profile-metrics.yml` retains daily **06:23 UTC**, manual dispatch, contents-only write access, pinned checkout, concurrency protection, change-only commits and normal pushes. The package glob `scripts/profile/**` is added to push triggers. Generated paths cannot retrigger the workflow. Scheduled runs may be delayed; GitHub may disable inactive public-repository schedules. The printed date and Actions history show freshness.

The built-in `GITHUB_TOKEN` supplies public API read quota. No PAT or new secret is required. Pagination is complete; transient reads have bounded retries. Incomplete reads fail rather than publish partial figures. All assets are fully rendered and XML-parsed, and budgets checked, before any output replaces a last-good file. Writes are staged then atomically replaced per file. Known obsolete SVGs are removed only after successful generation. Normal push never overwrites concurrent work.

Daily refresh changes data, images and only the **generated `Snapshot: YYYY-MM-DD` metadata in image alt text**. Editorial copy and links remain unchanged. The workflow stages README solely for these generated date updates.

## Local use

```sh
python3 -m unittest discover -s tests -v
python3 scripts/profile_metrics.py --snapshot data/profile.json
```

Live collection:

```sh
python3 scripts/profile_metrics.py
```

An optional `GH_TOKEN` environment variable raises public API quota; never put it in a file or argument. Unauthenticated limits may be insufficient for all histories. The workflow has its own token.

Rendering/PNG QA uses a development-only headless renderer; it is not part of the Python generator or daily workflow. [Validation notes](validation.md) report measured checks and limits. The SVG source remains usable as static imagery in viewers without animation support.

## API references

The collector uses GitHub's [public repository/language endpoints](https://docs.github.com/en/rest/repos/repos), [branch listing](https://docs.github.com/en/rest/branches/branches), [commit listing](https://docs.github.com/en/rest/commits/commits) and [published release listing](https://docs.github.com/en/rest/releases/releases). Schedule behavior follows [workflow event documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
