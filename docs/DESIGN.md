# ZpkDxGames profile — responsive visual system

## Design objective

The profile must read comfortably at GitHub's default 100% scale on both desktop and a narrow mobile viewport. It should feel like an engineering portfolio—not a miniature monitoring dashboard.

## Layout rules

- Use native Markdown for body copy, project descriptions, principles, and links.
- Use one-column flow only. Never place image cards in HTML tables.
- Keep every generated graphic on a 760 px-wide viewBox and display it at `width="100%"`.
- Use at least 18 px for secondary SVG copy, 24 px for card headings, and 42 px for hero text.
- Limit the page to four generated graphics: hero, capabilities, live pulse, activity, plus a compact footer.
- Keep critical information out of animation. Motion adds hierarchy but never carries meaning by itself.

## Visual language

The aesthetic combines a dark editorial surface with violet, cyan, and mint signals. The block-based hero illustration nods to Minecraft without using game assets or turning the page into a themed terminal. Soft glows, moving signal paths, and staggered bars provide restrained motion.

## Accessibility and resilience

- All graphics have descriptive alt text.
- Text and key lines meet high-contrast targets against opaque surfaces.
- SVG animation is disabled by `prefers-reduced-motion`.
- The generator uses only Python's standard library.
- Network failures degrade to honest `syncing` values; the workflow never fabricates metrics.
- Public GitHub data is collected with the workflow's scoped `GITHUB_TOKEN`; no personal access token is required.

## Generated data

`scripts/build_profile.py` reads `config/profile.json`, queries the public GitHub REST and GraphQL APIs, then writes:

- `assets/hero.svg`
- `assets/capabilities.svg`
- `assets/pulse.svg`
- `assets/activity.svg`
- `assets/footer.svg`

The scheduled workflow refreshes these files twice per day and commits only when public data changes.
