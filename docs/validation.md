# Validation notes

Baseline: `9927d83cdc06538a8ed2d98b38875f193d1c68cb`. Snapshot: **2026-10-13**.

| Check | Result |
| --- | --- |
| Offline unit suite | **26 tests pass**, including all nine original integrity tests. |
| Determinism | Same snapshot rendered twice in an isolated directory; all 95 data/SVG outputs identical. Existing-root runs additionally refresh only generated README alt dates. |
| XML and budget | **94 SVGs** parse; **696,929 bytes total**, largest **25,072 bytes**. Below 150 KB ideal / 300 KB hard per-asset and 4 MB total budgets. |
| SVG geometry | All 94 assets rendered to PNG and reviewed; headless-browser text bounds show **zero clipped labels or text collisions**. |
| Theme/layout parity | All eight charts, cover, ecosystem and six cards have dark/light and desktop/mobile compositions from the same data. |
| README viewports | Desktop 1040 px / content 830 px; mobile 390 px / content 358 px. Both themes: **no page or table horizontal overflow**, no missing images, correct picture sources. |
| Reduced motion | Forced in the browser for every SVG: **zero animations**. Six animated families also tested with motion enabled, then disabled: final transforms, zero line offset and no hidden labels. Full-page PNGs force reduced motion and completed reveals. |
| Contrast | All 30 text/surface pairs ≥4.5:1; meaningful accent graphics ≥3:1; heatmap count inks separately checked. Lowest text pair approximately 4.52:1. |
| 30-day enrichment | 394 immutable tips checked; both transient read failures retried successfully. **Every recent UTC day** reconciles with the original timeline: 1,112 commits, 10 active projects. |
| Snapshot preservation | Original snapshot equals new snapshot after removing schema-2 recent fields. No 90-day count, release, language, date or public-scope field changed. |
| Credits | Vendored icon sources and `docs/toolkit-icons.md` retained; credits file is byte-identical to baseline. Cover paths carry the font license. |
| Native markup | Relative asset paths resolve; nav anchors match real headings; picture order checked; no README styles/scripts/iframes/classes/inline CSS. |
| External URLs | **42 final URLs checked: 41 HTTP 200; LinkedIn returns anti-automation HTTP 999.** No known 404 remains. Email links checked syntactically; no email sent. |

## Source-driven choices and limits

- Current PlexonCrates documentation says maintenance ended, so Core replaces it in selected work. Crates remains clearly historical and still contributes eligible snapshot data.
- GriefPreventionAddon is deprecated in favor of GPFlags. Both appear in the overview and native table.
- The snapshot contains 21 Plexon repositories; all are covered. New unknown modules can enter the generated map, but native editorial tables still need review.
- Stable shelf/vitals versions are publications **inside this rolling window**, not necessarily the current default-branch version or an approved live deployment. AI Desktop Companion has no stable publication in the window.
- Conan Gray Bot's advertised demo returned 404. The source link is kept; no replacement demo URL is guessed. LinkedIn remains an existing owner-provided contact link and needs a manual check because it rejects automation.
- The current public bio still says “Just an ordinary amateur programmer.” A suggested replacement appears in the changelog; it was not changed.
- Previews use a local GitHub-style GFM renderer. GitHub sanitization constraints are respected, but the new tree has not been published to the profile. Site chrome, installed system fonts and GitHub layout can vary. Cover display lettering uses paths.
- Native Windows behavior, Minecraft runtime performance and production readiness of linked projects are outside this README task and are never inferred from commits or release labels.

## Commands

```sh
python3 -m unittest discover -s tests -v
python3 scripts/profile_metrics.py --snapshot data/profile.json
```

PNG previews are in `previews/`; design and data definitions are in [profile-visuals.md](profile-visuals.md). Generator runtime remains Python 3.10+ and standard library only.
