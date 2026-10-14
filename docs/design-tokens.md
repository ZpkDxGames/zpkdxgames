# Profile design tokens

The existing midnight-blue/violet/cyan family is retained. Violet leads; cyan supports. Warm appears at most once per chart. The generator's single source of truth is `scripts/profile/tokens.py`.

| Token | Dark | Light | Use |
| --- | --- | --- | --- |
| `bg` | `#0D111C` | `#F6F8FF` | Framed asset background |
| `surface` | `#151C2E` | `#FFFFFF` | Cards and panels |
| `surface-2` | `#172043` | `#EEF0FA` | Inset panels and tracks |
| `border` | `#2B3650` | `#D6DDEF` | Decorative hairlines |
| `text` | `#F1F5FF` | `#18233E` | Primary text |
| `text-muted` | `#A5B2CC` | `#53637E` | Secondary text |
| `violet` | `#B2A0FF` | `#7051C1` | Lead accent, recorded counts |
| `cyan` | `#68E1F4` | `#08788E` | Supporting accent, mean / prerelease |
| `warm` | `#FFC780` | `#966016` | Single peak or latest-release annotation |
| GitHub page | `#0D1117` | `#FFFFFF` | Preview background; controlled by GitHub |

Only `surface-2` is new; other palette values come from the previous generator. The old green accent is removed from charts. Vendored technology marks retain their original colours and licenses.

## Contrast and redundant meaning

All five text tokens are tested against all three asset surfaces: **30 combinations**, each ≥4.5:1. The lowest is light-theme cyan on `surface-2` at approximately **4.52:1**. Meaningful bars and strokes use the accent or text tokens, each ≥3:1. Hairlines and empty tracks are decorative, not sole carriers of data.

Heatmap colours use one violet intensity family with fixed thresholds. Each cell has a visible outline; nonzero cells also print their exact count. Count text selects black or white to maximize contrast against that cell's fill; these pairs are separately tested at ≥4.5:1. Labels, magnitude, position and exact values remain available without colour matching. SVG titles/descriptions and native README context identify each measure.

| Bin | Dark fill | Light fill |
| --- | --- | --- |
| 0 | `#172043` | `#EEF0FA` |
| 1–2 | `#454169` | `#DED6F3` |
| 3–5 | `#635388` | `#BDA9E5` |
| 6–10 | `#8370B8` | `#987CCC` |
| 11–50 | `#B2A0FF` | `#7051C1` |
| 51+ | `#DED6FF` | `#46288D` |

## Type and layout

- SVG labels: `"Inter", "Segoe UI", system-ui, -apple-system, sans-serif`; installed fonts only, no font requests.
- Cover display text: pre-extracted **DejaVu Sans Bold paths**, stored in `scripts/profile/lettering.json`. This is not a font dependency at generation or display time. Its license is preserved in `assets/vendor/display-font/LICENSE.txt`.
- Native README copy: GitHub's text renderer. Paragraphs, project names and links remain searchable and copyable.
- Full desktop assets: width 1000, displayed at about 830 px. Mobile assets: width 500, selected below 600 px.
- Cards: desktop width 500, mobile width 240; the narrow composition uses three readable vitals rows. The GitHub table retains two columns without unsupported responsive CSS.
- Panel radius: 16; inset cards: 9–12; generous 28 px page insets.

## Motion

| Token | Value |
| --- | --- |
| Reveal | 900 ms |
| Easing | `cubic-bezier(0.22, 1, 0.36, 1)` |
| Per-item stagger | 30 ms |
| Maximum total stagger | 800 ms |
| Cover signal | One 24-second linear loop |

Only the cover has an ambient loop. KPI values fade once; the activity mean draws once; project bars and weekly releases grow once; total language share reveals once. Cards, ecosystem overview, version shelf, heatmap, release radar and toolkit stay static. Animation defaults to the final state, and `prefers-reduced-motion: reduce` disables it. No essential value, label or shape depends on animation. No heavy filters, remote scripts, fonts or images are embedded.
