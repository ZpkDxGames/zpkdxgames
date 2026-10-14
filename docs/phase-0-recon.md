# Phase 0 — Repository recon

Recon was performed before the new dashboard assets were generated. The target is the GitHub profile repository `ZpkDxGames/zpkdxgames`; the public metrics snapshot used for the delivered static render is dated **2026-10-13** and was generated at **2026-10-13T14:28:56Z**.

## Existing profile repository

The previous profile was already generated rather than fully hand-authored. It contained a Python standard-library collector/renderer, repository-hosted SVG assets, tests, preview PNGs, and a scheduled GitHub Actions refresh. That engineering foundation was worth retaining conceptually, but the presentation was an editorial portfolio/card system rather than the requested command-center architecture.

The new implementation therefore does **not** preserve the old README layout. It replaces the presentation system, data schema, generated-asset namespace, responsive compositions, project-preview model, chart suite, and motion vocabulary while retaining the sound principles of deterministic generation, repository-hosted assets, public-data boundaries, and scheduled refreshes.

## Verified snapshot baseline

The frozen snapshot contains:

| Measure | Verified value | Meaning |
| --- | ---: | --- |
| Public projects in scope | 30 | Owned, public, non-fork, non-archived/non-disabled; profile repo excluded |
| Project-wide commits · 90d | 4,419 | Non-bot commits across current branch histories, SHA-deduplicated per repository |
| Project-wide commits · 30d | 1,112 | Same definition, last 30 UTC calendar days |
| Active projects · 30d | 10 | Repositories with at least one qualifying commit in the recent 30-day window |
| Published releases · 90d | 192 | 136 stable + 56 prerelease; drafts excluded |
| GitHub language bytes | 11,018,100 | Default-branch source volume, not proficiency |
| Peak aggregate activity | 711 commits | 2026-09-12, project-wide snapshot aggregation |

All README-facing values are snapshot facts. None are presented as live server telemetry, personal contribution streaks, deployment state, uptime, user count, latency, or production health.

## Project-source review

Featured candidates were checked against their current repository documentation and relevant source/configuration before copy and preview concepts were locked.

- **PlexonPanel** documents a multi-component Paper/Host/dashboard control system using signed Protocol 3. Its source is prepared for a 5.0 line, but stable publication and production rollout remain gated by migration/runtime/security checks. The README therefore uses a conceptual authority/coordination topology and never labels it as live or deployed 5.0 telemetry.
- **PlexonTools** documents unique tool identity, in-memory progression authority, public progress events, natural/player-placed provenance, and bounded asynchronous SQLite persistence. Its preview uses that identity → progression → event → persistence pipeline.
- **PlexonQuests** documents an explicit join-based Daily/Weekly/Milestone board, guarded active-quest state, reward/claim behavior, persisted history, and asynchronous storage. Its preview uses those states rather than generic quest art.
- **PlexonChats** documents LOCAL/GLOBAL/private communication, persistent Chat Events, participant-owned Bingo, and optional Discord presentation. Its preview shows input routing → policy → events → optional presentation.
- **AI-Desktop-Companion** is an Alpha.6 local-first Minecraft-skin desktop experiment using skinview3d/Three.js and a deterministic `BehaviorController`. AI, screen observation, shell/tool execution, and accessibility actions remain absent; the preview explicitly renders the AI-action node as not implemented.
- **PlexonCore** documents shared runtime/event-routing infrastructure, immutable contexts, origin state, persistence helpers, lifecycle/diagnostic surfaces, and performance counters. Its preview focuses on the shared runtime path, not gameplay ownership.

Additional repository review established two important historical states: **PlexonCrates** is retired/maintenance-ended and retained as historical source, while **PlexonGriefPreventionAddon** is deprecated in favor of **PlexonGPFlags**. Both remain visible in the ecosystem overview because historical truth is useful; neither is promoted as an active featured system.

## Existing links retained

Existing public profile links were retained only where already supplied by the profile repository: portfolio, creator hub, LinkedIn, SpigotMC, Modrinth, and email. GitHub project links were verified through the connected repository account. Modrinth was independently reachable during QA; the execution environment could not reliably fetch the other external sites, so those links are documented as requiring a final browser click-check before publication rather than being silently claimed as validated.

## Data gap discovered

The prior schema-2 snapshot stores exact per-project 90-day/30-day totals and one aggregate daily series, but **not 90 explicit daily values per repository**. Historical project-wide daily timelines cannot be reconstructed exactly after branch tips change without replaying the original collection state.

The new schema-3 collector solves this for future refreshes by persisting `daily_commits` for every project. For the frozen 2026-10-13 delivery, featured mini-sparklines use separately collected, real **main-branch** daily histories bounded to the original snapshot timestamp and are visibly labeled `MAIN BRANCH · 90D`. They are not represented as project-wide. When a native schema-3 refresh runs, the renderer automatically switches those labels and values to `PROJECT-WIDE · 90D`.

This is the closest technically valid implementation that preserves the old snapshot totals without inventing historical branch-level detail.