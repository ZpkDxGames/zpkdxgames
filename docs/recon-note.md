# Phase 0 · Repository recon

Reviewed against `main` at `9927d83cdc06538a8ed2d98b38875f193d1c68cb`, retrieved 2026-10-14 UTC. Editorial sources were read from the projects' default branches. The metrics snapshot remains dated **2026-10-13**.

- **Verified baseline:** 30 public projects, 4,419 project-wide non-bot commits, 192 published releases (136 stable / 56 prerelease), 11,018,100 language bytes, 90 UTC days from 2026-07-16 through 2026-10-13. Peak: 711 commits on 2026-09-12. Latest publication: 2026-09-19, 24 days before the snapshot.
- **Existing palette:** dark `bg #0d111c`, `panel #151c2e`, `border #2b3650`, `text #f1f5ff`, `muted #a5b2cc`, cyan `#68e1f4`, violet `#b2a0ff`, green `#6be5bb`, warm `#ffc780`; light `#f6f8ff`, `#ffffff`, `#d6ddef`, `#18233e`, `#53637e`, cyan `#08788e`, violet `#7051c1`, green `#12785b`, warm `#966016`. Preserve the blue/violet/cyan family; lead with violet and remove green as a chart accent.
- **Generator:** one 700-line standard-library script combines bounded API retries, full pagination, branch-tip resolution, SHA deduplication, collection, validation, 60 SVG layouts and atomic per-file replacement. Its entry point and offline mode are sound; split collection, validation, tokens, drawing, cards and charts into a package.
- **Tests:** all 9 baseline tests pass. They cover public scope/privacy, SHA deduplication, bot filtering, UTC conversion, publication ordering, language byte sums, pagination, empty rendering, SVG parsing, determinism and failed-render preservation. Missing: contrast, nonlinear scales, rolling averages, 30-day activity, release shelves, fixed heatmap thresholds, viewport fit and asset budgets.
- **Automation:** daily 06:23 UTC, manual dispatch, change-only commits, pinned checkout, normal push. Add `scripts/profile/**` to push triggers after the package split.
- **Coverage:** the snapshot contains **21 Plexon repositories**, including Dashboard. The new map and native table must show all 21, with historical status explicit.

## Surprises that change the design

1. **PlexonCrates is discontinued.** Its current README explicitly marks maintenance ended and the repository historical. Replace it in the featured six with PlexonCore; retain it in the ecosystem and metrics. GitHub has not necessarily marked a retired project archived, so do not silently alter metric eligibility.
2. **PlexonGriefPreventionAddon is deprecated**, replaced by PlexonGPFlags. Show both with their distinct status and point claim-policy discovery to GPFlags.
3. **The original snapshot cannot compute projects active in the last 30 days:** it has per-project 90-day totals and only an aggregate daily series. The minimal schema-2 addition is `commits_30d`. Public commit reads against 394 distinct immutable branch tips verified **10 active projects / 1,112 recent commits**, bounded to 2026-09-14 through the original snapshot commit at 2026-10-13T14:28:56Z. Every recent daily aggregate reconciles with the original snapshot. No 90-day total was changed. Future collection derives the field directly from its existing per-project daily counter.
4. **Stable versions in a rolling snapshot are not necessarily current source versions.** Label all shelf/vitals versions “stable in window”; no stable publication becomes `—`.
5. **AI Desktop Companion is an alpha desktop/avatar project; AI actions are disabled.** Preserve that boundary in copy. PlexonPanel 5.0 rollout remains gated.
6. **ConanGrayBot-Page has no README or description.** Its checked-in `index.html` verifies the bot-dashboard interface; the repository homepage supplies its public URL. Use only that narrow description.

## Sources and retained material

Read the profile README, snapshot, generator, complete test file, workflow, visuals documentation and toolkit credits. Read all 21 Plexon repository READMEs plus AI Desktop Companion, Neural Core Dashboard and Triangle Area; inspect ConanGrayBot-Page's source and repository metadata. Keep existing identity/contact copy and vendored MIT icons with credits intact. No product screenshots were supplied; artwork will be labelled conceptual.
