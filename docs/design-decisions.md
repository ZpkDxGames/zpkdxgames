# Phase 1 · Design decisions

**Direction:** an editorial engineering portfolio. Generous spacing, a compact wordmark, quiet technical line art, native project copy, and measured charts. Repository-hosted assets only. Decisions below are locked before SVG generation; optional questions go to delivery.

## Order and responsive wireframe

| Section | Desktop · 830 px content | Mobile · 390 px viewport |
| --- | --- | --- |
| Cover | 1000 × 338 SVG, title left / system motif right | 500 px composition, title above compact motif |
| Identity | Link bar, section nav, two short intro paragraphs | Wrapping native links and paragraphs |
| At a glance | Four exact KPIs in one strip | Same four values in a 2 × 2 grid |
| Selected work | Six cards, 2 columns × 3 rows | GitHub's same 2-column table; narrow card art and short wrapping native copy |
| Web & interfaces | Compact native project/link table | Short cells, wrapping links; no fixed-width thumbnails |
| Plexon ecosystem | All 21 repositories in grouped map, then text table | Groups stacked in SVG; complete wrapping native table |
| Observatory | Activity, project bars, language split, cadence, version shelf | Individual 500 px chart compositions; same measures |
| Details | Heatmap and recent-release radar collapsed | Same, with narrow compositions |
| Toolkit | Refined labelled icon groups | Icons wrap naturally, static |
| Approach / contact | Collapsed background, visible CTA and links | Native text, wrapping links |

## Featured six

| Project | Why it leads |
| --- | --- |
| PlexonPanel | Connects Paper, host operations and the browser dashboard; retain rollout-gate context. |
| PlexonTools | Persistent, world-scoped custom-tool progression. |
| PlexonQuests | Explicitly joined daily/weekly/milestone quest board. |
| PlexonChats | Public/private communication and persistent chat events. |
| AI Desktop Companion | Adds local desktop, 3D avatar and interface work; label alpha and disabled AI actions. |
| PlexonCore | Shared runtime foundation; replaces the now-discontinued PlexonCrates candidate. |

Web lane: PlexonPanel-Dashboard, Neural-Core-Dashboard, ConanGrayBot-Page, Triangle-Area; retain the professional portfolio and creator-hub links. AI Desktop Companion already has a featured card.

## Palette and motion

| Token | Dark | Light |
| --- | --- | --- |
| bg | #0D111C | #F6F8FF |
| surface | #151C2E | #FFFFFF |
| surface-2 | #172043 | #EEF0FA |
| border | #2B3650 | #D6DDEF |
| text | #F1F5FF | #18233E |
| text-muted | #A5B2CC | #53637E |
| violet · lead | #B2A0FF | #7051C1 |
| cyan · support | #68E1F4 | #08788E |
| warm · one highlight/chart | #FFC780 | #966016 |

Keep existing values; adopt defaults only for missing inset surfaces. Verify all actual text/surface pairs at ≥4.5:1 and meaningful strokes/bars at ≥3:1. Preserve vendored brand-logo colours as identifiers. Cover display lettering is stored as paths; all other labels use system fonts.

Reveal: 900 ms, `cubic-bezier(0.22, 1, 0.36, 1)`. Stagger: 30 ms/item, ≤800 ms total. Cover: one 24 s linear signal loop. Charts: one meaningful reveal each; cards/toolkit static. Reduced motion disables all animation and shows final geometry. No filters or fake telemetry.

## Charts and integrity

A · exact KPI strip, including verified 30-day active projects. B · square-root daily bars with raw-count ticks, trailing 7-calendar-day arithmetic mean (available-day warm-up), neutral peak label. C · top 10 project commits, zero baseline. D · honest total byte share and explicit repository-group split (server/plugins, web/interfaces, other projects); languages below 1% grouped into Other within each view. E · Monday-first weekly stable/prerelease counts with partial edge weeks marked. F · latest stable by publication timestamp **within the window**, `—` if absent. G · Monday-first heatmap with fixed bins **0 / 1–2 / 3–5 / 6–10 / 11–50 / 51+**. H · six recent publications and computed age.

Every chart has its window/as-of date, accessible title/description, static final state and light/dark/mobile variants. Commits remain project-wide, not personal contributions; byte shares remain volume, not proficiency. Add only aggregate `commits_30d` in schema 2. Keep all other collection boundaries unchanged.

**Defaults:** conceptual art; existing public contacts retained; English only; bio suggestion only. No GitHub publishing is part of the requested ZIP delivery.
