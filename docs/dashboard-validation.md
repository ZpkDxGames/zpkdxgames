# Dashboard validation report

Status: **PASS with one documented historical-snapshot compatibility limitation and one external-link verification limitation.**

No repository publication or GitHub mutation was performed as part of this delivery.

## Automated test suite

Command:

```bash
python3 -m unittest discover -s tests -v
```

Result: **25 / 25 tests passed**.

Coverage includes:

- public/owned repository scope filtering;
- fork, archived, disabled, profile-repository, and other-owner exclusion;
- bot detection;
- per-repository SHA deduplication;
- UTC committer-date behavior;
- 90-day / 30-day reconciliation;
- release draft exclusion and prerelease preservation;
- language-byte reconciliation;
- frozen-snapshot total reconciliation;
- editorial separation from numeric metrics;
- exact featured fallback timeline length;
- fixed heatmap bins;
- activity scaling / rolling-average math;
- dark/light text and meaningful-graphic contrast;
- SVG parsing and accessibility metadata;
- forbidden SVG runtime content (`script`, `foreignObject`, remote dependencies);
- required light/dark/mobile/desktop variants;
- README relative asset resolution;
- `<picture>` source ordering;
- deterministic byte-identical rendering;
- zero/empty language and release states;
- native schema-3 project-wide sparkline selection;
- asset-size budgets;
- rollback after a simulated partial install failure.

## Data integrity

Frozen snapshot: **2026-10-13**, exact generation bound **2026-10-13T14:28:56Z**.

Verified reconciled totals:

| Metric | Result |
| --- | ---: |
| Public projects in scope | 30 |
| Project-wide commits · 90d | 4,419 |
| Project-wide commits · 30d | 1,112 |
| Active projects · 30d | 10 |
| Published releases · 90d | 192 |
| Stable releases · 90d | 136 |
| Prereleases · 90d | 56 |
| GitHub Linguist bytes | 11,018,100 |
| Aggregate peak | 711 commits on 2026-09-12 |

The 90-day daily series sums to the same 4,419 project-wide commit total. Language bytes reconcile exactly to project totals. Weekly release cadence sums to 192 publications.

## Historical snapshot compatibility

The source snapshot predates schema 3 and therefore does not contain a 90-element daily series for every repository. Exact historical project-wide per-day timelines cannot be reconstructed after branch tips move without inventing data.

The delivered compatibility model therefore keeps the original project-wide totals and aggregate daily series untouched. Featured repository mini-sparklines use separately collected **real main-branch histories** bounded through the exact original generation timestamp and are visibly labeled `MAIN BRANCH · 90D`. The schema-3 collector persists `daily_commits` for every repository on future refreshes; the renderer automatically switches to `PROJECT-WIDE · 90D` whenever those native arrays are present.

This limitation is explicit in `data/profile.json`, `data/project-main-activity.json`, the README native text, Phase 0 recon, and the data-model documentation.

## SVG / asset validation

Generated SVG count: **80**.

- total generated SVG bytes: **657,430 bytes**;
- largest SVG: **22,347 bytes** (`project-matrix-dark.svg`);
- hard per-SVG budget: 300,000 bytes;
- aggregate budget: 5,000,000 bytes;
- all SVGs parse as XML;
- every SVG has `<title>`, `<desc>`, `role="img"`, and `aria-labelledby`;
- no generated SVG contains JavaScript, `foreignObject`, or remote image/script dependency;
- all major visual modules have desktop/mobile + light/dark variants;
- a browser geometry audit verified every SVG text bounding box stays inside its viewBox.

## Reduced motion

Every SVG includes:

```css
@media (prefers-reduced-motion: reduce)
```

The rule removes animation, restores opacity/transforms, and completes path dash offsets. A Chromium/Playwright reduced-motion audit loaded **all 80 SVGs** and found **0 running or pending animations**.

## Responsive / theme visual QA

The README was programmatically rendered with Chromium at the requested widths and both color schemes. SVG assets were embedded as data URIs in the QA harness only; the real README continues to use repository-relative asset paths.

| Preview | Viewport | Full-page result | Horizontal overflow |
| --- | --- | ---: | --- |
| `desktop-light.png` | 1440 × 1200 | 1440 × 9449 | none |
| `desktop-dark.png` | 1440 × 1200 | 1440 × 9449 | none |
| `mobile-light.png` | 390 × 844 | 390 × 10629 | none |
| `mobile-dark.png` | 390 × 844 | 390 × 10629 | none |

`preview-sheet.png` is **1320 × 1760** and places all four renders on one comparison sheet.

The visual QA pass caught and fixed internal clipping in the cover, desktop heatmap legend, mobile activity-window board, and mobile ecosystem before final delivery.

## Contrast

Automated tests enforce:

- normal text vs base background: **≥ 4.5:1**;
- muted text vs base background: **≥ 4.5:1**;
- primary/secondary meaningful graphics vs base background: **≥ 3:1**.

Stable vs prerelease meaning in the publication radar is also encoded with shape (circle vs diamond), not color alone.

## Determinism and failure safety

Rendering the same snapshot into two clean temporary directories produces byte-identical SVG hashes.

The entry point renders and validates the entire SVG tree before installation. Installation backs up the existing asset tree, README, and online snapshot before placing replacements. A test injects an install failure after partial replacement and verifies that all three previous versions are restored.

## GitHub README constraints

The final README uses only:

- Markdown;
- GitHub-safe native HTML;
- `<picture>` responsive sources;
- repository-hosted SVG;
- semantic headings and native links.

It does **not** depend on JavaScript, React, canvas, iframe, client-side API fetch, remote stat cards, remote fonts, hover-only content, or runtime metric collection.

## Project-fact review

Featured descriptions and preview boundaries were reviewed against current repository documentation/source. In particular:

- PlexonPanel 5.0 source remains rollout-gated rather than represented as deployed/stable telemetry;
- AI Desktop Companion remains Alpha.6/local-first and explicitly marks AI actions as not implemented;
- PlexonCrates is historical/retired;
- PlexonGriefPreventionAddon is deprecated in favor of PlexonGPFlags;
- release publication is never equated to deployment.

## External links

All featured GitHub repository targets were read through the connected GitHub account during recon. The Modrinth profile was independently reachable during final link QA.

The validation environment could not reliably fetch the portfolio, creator-hub, LinkedIn, or SpigotMC URLs due environment/network restrictions. They are retained because they were already owner-provided public links in the profile repository, but a final manual click-through is recommended immediately before publication. This report does not claim those four destinations were network-validated.

## Delivery acceptance

The finished tree includes the final README, 80 generated dashboard SVGs, six animated project modules, nine observatory views, ecosystem and technology topologies, schema/data files, deterministic generator, expanded tests, scheduled workflow, Phase 0/1 docs, design/data docs, validation report, changelog, four full-page PNG previews, combined preview sheet, and cleanup manifest.

Publication remains intentionally pending explicit authorization.