# Dashboard design system

## Layout

Major generated assets use rounded bordered panels, a restrained grid, compact coordinate/status labels, and system-safe typography. Content density is deliberately high, but critical labels keep a stable position and do not animate.

Desktop coordinate width is 1000 units. Mobile coordinate width is 500 units with dedicated recomposition. Generated assets are referenced through GitHub-safe `<picture>` elements only; no JavaScript, canvas, iframe, client-side fetch, or hover-only information is required.

## Type

Primary UI labels use:

```text
ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace
```

Body-oriented labels use:

```text
-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif
```

No font binaries are bundled.

## Color tokens

See `scripts/profile_dashboard/tokens.py` for the single source of truth. Text/background pairs are automatically tested to WCAG AA-style 4.5:1 minimum contrast; primary/secondary meaningful graphics are tested at 3:1 or better against the base background.

Color is not the only carrier of meaning where status categories matter. The publication radar, for example, distinguishes stable publications with circles and prereleases with diamonds in addition to color.

## Motion tokens

```text
fast      220 ms
standard  480 ms
reveal    900 ms
scene     1200 ms
ambient   24000 ms
```

Animation classes are centralized in `scripts/profile_dashboard/motion.py`. Reduced motion disables every animation class and leaves a complete final state.

## Texture rules

Allowed visual texture is limited to thin grids, subtle borders, status rails, sparklines, bar/line charts, conceptual topology connectors, and restrained node signals. Decorative elements are not allowed to imply measurements or system state.

The system intentionally excludes typing effects, external stat cards, streak widgets, contribution snakes, visitor counters, rainbow borders, skill percentages, Matrix rain, starfields, CRT scanlines, fabricated terminal output, fake request rates, or uptime/status indicators.