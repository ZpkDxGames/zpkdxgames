# README redesign · October 2026

Built from `main` at `9927d83cdc06538a8ed2d98b38875f193d1c68cb`, following the supplied brief. Metrics retain the **2026-10-13** snapshot: 30 projects, 4,419 project-wide non-bot commits, 192 publications and 11,018,100 source bytes.

- Rebuilt the cover, six-project showcase, web/interface lane, complete 21-repository Plexon overview, charts, toolkit and contact layout.
- Featured **PlexonCore in place of PlexonCrates** after verifying Crates' discontinued status. Crates remains historical work; the old GriefPrevention addon is marked deprecated in favor of GPFlags.
- Added measured card vitals and all eight requested chart families: KPIs, square-root daily activity with a 7-day mean, top-ten commits, honest total/group language views, weekly publication cadence, stable version shelf, six-bin calendar and recent-release radar.
- Preserved the existing palette, led with violet, and restricted motion to one slow cover signal and one-time data reveals. Dedicated mobile and theme variants retain the same values.
- Split the standard-library generator into `scripts/profile/` while preserving the entry point, offline mode, collection scope, parse-before-replace safety and daily 06:23 UTC schedule. Updated workflow paths for the package and generated alt dates.
- Added schema-2 `commits_30d`: **10 active projects / 1,112 recent commits**, independently verified and reconciled against each original UTC daily total. Other snapshot values are unchanged.
- Preserved all vendored icon sources, MIT license and toolkit credits. Added local cover-lettering outlines and their font license.
- Added recon/design notes, tokens, measurement documentation and validation notes. PNG previews cover desktop/mobile in light/dark, plus a preview sheet.

The repository's Conan Gray Bot demo homepage returned 404 and is omitted; its verified source remains linked. LinkedIn blocks automated requests, so its existing contact link is retained with that verification limit recorded.

## Apply

Copy this ZIP's repository-root files into `ZpkDxGames/zpkdxgames`, then run:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/profile_metrics.py --snapshot data/profile.json
```

This delivery does not publish or change the GitHub bio. Six obsolete SVG files are intentionally retired: `ecosystem-{light,dark}.svg`, `ecosystem-mobile-{light,dark}.svg`, and `spotlight-crates-{light,dark}.svg`. The generator removes them after successful rendering, so copying over an existing tree is sufficient. Review the diff and commit the resulting tree normally.

## Owner choices for later · defaults already applied

- Featured six are Panel, Tools, Quests, Chats, AI Desktop Companion and Core.
- No real screenshots were supplied; conceptual art is labelled. Verified screenshots could replace it later.
- Existing public Discord/email/contact links are retained.
- Current public bio still reads “Just an ordinary amateur programmer.” Suggested replacement: **“I build Minecraft server systems, web interfaces and useful tools.”** Bio changes remain the owner's choice.
- English only; a PT-BR summary can be added later if wanted.
- A working public Conan Gray Bot demo URL was not verified. LinkedIn requires a manual check because it rejects automated requests.
