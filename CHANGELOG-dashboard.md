# GitHub profile dashboard changelog

## 2026-10-13 snapshot rebuild

Rebuilt the profile presentation as a GitHub-native engineering command center rather than iterating on the previous portfolio/card layout.

### Data and generation

- Introduced schema-3 collection with explicit per-project daily commit timelines for future refreshes.
- Preserved the verified 2026-10-13 snapshot totals: 30 projects, 4,419 project-wide 90-day commits, 1,112 30-day commits across 10 active projects, 192 published releases, and 11,018,100 GitHub Linguist bytes.
- Kept bot exclusion, UTC committer-date handling, per-repository SHA deduplication, release draft exclusion, and stable/prerelease separation.
- Added a documented compatibility layer for the prior schema-2 snapshot. Featured historical sparklines use verified main-branch timelines and are labeled accordingly; native schema-3 refreshes automatically switch them to project-wide timelines.
- Moved all changing metrics into the snapshot/data model and kept editorial project copy numeric-free.
- Added rollback-capable staged installation so a failed render/install cannot destroy the last valid generated asset tree, README, or snapshot.

### Visual system

- Added a completely new command-center cover and engineering-status rail.
- Added six project-specific animated system modules: PlexonPanel, PlexonTools, PlexonQuests, PlexonChats, AI Desktop Companion, and PlexonCore.
- Added a complete project matrix, Plexon responsibility topology, and technology topology.
- Added nine observatory views: activity timeline, activity leaderboard, 90d/30d matrix, language volume, release cadence, stable version shelf, activity heatmap, publication radar, and activity-window board.
- Generated dedicated desktop/mobile and dark/light variants for every major visual.
- Centralized palette, type, and motion tokens and added complete `prefers-reduced-motion` final states.

### Source-driven status corrections

- Kept PlexonPanel 5.0 presentation explicitly rollout-gated rather than implying stable/production deployment.
- Kept AI Desktop Companion explicitly Alpha.6/local-first with AI/screen/tool actions not implemented.
- Kept PlexonCrates visible only as retired/historical work.
- Kept PlexonGriefPreventionAddon visible as deprecated and superseded by PlexonGPFlags.

### QA and automation

- Added data-scope, bot, UTC, SHA-deduplication, release filtering, reconciliation, rendering, contrast, budget, deterministic output, empty-state, responsive variant, README path, and rollback tests.
- Added a scheduled/manual workflow using the new generator and a change-only normal push.
- Added Playwright preview QA for 1440px desktop and 390px mobile in both themes, including browser-level reduced-motion checks on every generated SVG.
- Final generated set: 80 SVG files, 657,430 bytes total; largest SVG 22,347 bytes.