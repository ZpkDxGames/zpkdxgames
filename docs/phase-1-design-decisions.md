# Phase 1 — Dashboard design decisions

These decisions were locked before the final SVG set was generated.

## Experience and information architecture

The profile is designed as a **personal engineering command center** rather than a conventional badge/profile page. The reading order is:

1. command-center cover;
2. native navigation;
3. engineering status rail;
4. six featured system modules;
5. complete repository matrix;
6. Plexon system topology;
7. project observatory with nine factual views;
8. technology topology;
9. native engineering-approach copy;
10. contact links.

Critical context remains in native Markdown even when images fail: the snapshot window, non-live nature of the data, project names/links, concise project descriptions, methodology caveats, approach, and contacts.

## Featured systems

The featured set is fixed to:

| Project | Preview concept | Source-backed boundary |
| --- | --- | --- |
| PlexonPanel | Paper → Linux Host → coordination → dashboard | Conceptual component/authority flow; 5.0 rollout remains gated |
| PlexonTools | tool identity → progression → public event → SQLite | In-memory authority and bounded async persistence |
| PlexonQuests | available → joined → progress → history/claim | Explicit join-based normal participation |
| PlexonChats | input → router → chat events → optional Discord | Discord is presentation-only, not gameplay authority |
| AI-Desktop-Companion | skin → local renderer → deterministic behavior → disabled AI actions | Alpha desktop/avatar foundation; external agency not implemented |
| PlexonCore | event gateway → immutable context → origin/storage → diagnostics | Shared infrastructure; gameplay remains in modules |

Every scene is labeled `SYSTEM PREVIEW · CONCEPTUAL`; movement illustrates documented flow/state rather than claiming a live connection.

## Dashboard palette

The design uses the brief's new neutral blue/teal control-center language instead of the former violet-led portfolio identity.

| Token | Dark | Light |
| --- | --- | --- |
| background | `#080B12` | `#F5F7FB` |
| surface | `#0E1420` | `#FFFFFF` |
| raised surface | `#151E2F` | `#EEF2F8` |
| border | `#263247` | `#D3DBE8` |
| text | `#E8EEF8` | `#172033` |
| muted text | `#8C9AB0` | `#5D6B80` |
| primary | `#6EA8FF` | `#2F68C7` |
| secondary | `#55DFC1` | `#087D6B` |
| highlight | `#F2B866` | `#92601D` |
| danger-muted | `#E47C8C` | `#A94759` |

No remote font binaries are required. System-safe sans and monospace stacks are used throughout generated SVGs.

## Motion system

Motion is restricted to four semantic families:

- **Reveal** — first-load opacity/position resolution;
- **Trace** — one-time line/path draw for charts and architecture;
- **Signal** — slow ambient packet/breathing indicator;
- **State** — project-preview progress/state transition.

Shared timing tokens are `220 ms`, `480 ms`, `900 ms`, `1200 ms`, and `24 s`, using `cubic-bezier(0.22, 1, 0.36, 1)` for UI reveals. No bounce/elastic loops, scanlines, Matrix rain, fake terminals, typing headers, contribution snakes, flashing LEDs, or animated fake metrics are used.

Every SVG contains `@media (prefers-reduced-motion: reduce)` and forces the complete final state with animation disabled, opacity restored, transforms reset, and dash offsets completed.

## Responsive strategy

Every major visual has four generated variants:

- desktop light;
- desktop dark;
- mobile light;
- mobile dark.

Desktop assets use a 1000-unit viewBox; mobile assets use a dedicated 500-unit composition. Mobile does not merely scale the desktop drawing: featured modules restack their metrics and technical scene, version shelves become 2-column cards, publication radar becomes a readable list, and project-matrix columns are reduced to the information that can remain legible.

README `<picture>` source order is fixed to mobile-dark → mobile-light → desktop-dark → light fallback.

## Observatory views

Nine factual generated views are included:

1. aggregate 90-day activity bars + 7-day arithmetic mean;
2. project 90-day activity leaderboard with 30-day marker;
3. 90-day vs 30-day activity matrix;
4. GitHub Linguist language-byte volume;
5. stable/prerelease publication cadence;
6. featured-project latest stable publication shelf;
7. Monday-first fixed-bin activity heatmap;
8. recent publication radar using shape + color for stable/prerelease distinction;
9. activity-window board (`active in 30d`, `activity in 90d only`, `no commits in 90d`) explicitly described as recency, not health.

The project matrix and two topology views are additional generated information surfaces beyond those nine charts.

## Data boundaries

- Commit metrics are **project-wide** unless a featured compatibility sparkline is explicitly labeled `MAIN BRANCH · 90D`.
- The common window is 90 UTC calendar days.
- Bots are excluded and commit SHAs are deduplicated per repository by the collector.
- Language totals are bytes/source volume, never skill scores.
- Release publication is not deployment status.
- Editorial configuration contains project category/state/copy only; changing numeric metrics never live in editorial JSON.
- Historical/deprecated project state is maintained editorially only when verified from repository documentation.
- No stars, downloads, uptime, latency, users, issue counts, benchmarks, or invented maturity scores are shown.