# Profile dashboard

A complete replacement of the previous profile layout. The visual system uses midnight navy, electric blue, cyan, a precise spacing system, layered glass surfaces, and restrained beveled edges. Native Markdown provides the introduction, links, and text alternatives. Every graphic has a 900-unit desktop layout and a separately composed 420-unit mobile layout, selected through a GitHub-compatible `picture` element at 600px.

## Maintain

Edit the biography, portfolio URL, and project selection in `config/dashboard.json`. Project descriptions are authored summaries of the public source READMEs; they deliberately avoid release or production-readiness claims. Illustrations are conceptual vector artwork, not screenshots or server telemetry.

```sh
python3 scripts/dashboard.py --refresh
python3 scripts/dashboard.py --check
python3 -m unittest discover -s tests -v
```

Rendering without `--refresh` uses the committed, dated snapshot and needs no network. The workflow refreshes twice daily and can be run manually from Actions. Source/config changes trigger the first sync. Snapshot timestamps and content-derived image URLs make updates visible without relying on a third-party statistics host.

## Metric definitions

- **Public repos:** public repositories owned by the profile, including this profile repository and forks.
- **Original projects:** public, non-fork repositories, excluding this profile repository. Archived originals remain included.
- **Profile contributions:** the contribution calendar's count for the most recent 365 calendar days, including today (UTC). This is GitHub's contribution definition, not a commit count. It may include anonymized private activity if the owner publishes that count on their profile.
- **Active days:** days with at least one profile contribution in the same window.
- **Activity chart:** twelve calendar weeks beginning Monday; the current week is incomplete. The heatmap uses the same days and a monotonic intensity scale. Future days are visibly unfilled.
- **Language mix:** GitHub language bytes aggregated over public original repositories, excluding this profile repository. This measures checked-in code, not proficiency or time spent. The five largest languages are shown individually; the remainder is grouped as Other.

The collector paginates repositories, never includes private repositories, and checks full calendar coverage. It uses GraphQL when an Actions token is available; the public HTML contribution calendar is a validated fallback. Calendar tooltips supply exact counts, never inferred counts from color levels. An unavailable API or incomplete response fails the refresh before any generated assets are replaced. The last dated snapshot stays visible.

## Geometry and composition

Architectural illustrations use a shared 30-degree isometric projection. Hardware faces, stacked platforms, and voxel character parts derive from the same coordinates so perspective remains consistent. Project artwork occupies a separate framed area; text and badges use aligned margins across cards. The mobile hero has its own illustration space instead of placing graphics behind the biography.

## Rendering and motion

SVGs contain only self-contained vector shapes, text, gradients, and CSS animations. There is no script, `foreignObject`, embedded HTML, external font, or external image. Fonts use Arial/Helvetica with a monospace system fallback for labels. All meaningful values appear immediately; motion is limited to decorative signal paths, floating hardware, and soft highlights. `prefers-reduced-motion: reduce` disables motion and preserves the full design.

Minimum mobile body size is 20 units on a 420-unit artboard (about 16px at 336px display width). Desktop labels are at least 16 units. Clickable project cards link to their actual repository. The README includes a native text version of the metrics and descriptions for accessibility.

The repository contents were rebuilt from an empty file tree. Earlier Git history remains available for rollback.
