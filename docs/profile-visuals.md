# Profile visuals

The profile uses small, repository-hosted SVGs instead of a shared statistics-card service. The hero has subtle animated paths; the charts animate when loaded. Every graphic has a light and dark variant, a descriptive title, and a reduced-motion fallback. No JavaScript, remote fonts, or external images are embedded in the SVGs.

## Data boundaries

- Only **public, owned, non-fork, non-archived, enabled repositories** are included. The profile repository is excluded so its refresh commits and Python generator do not distort the graphs.
- The window contains **90 UTC calendar days**, including the snapshot date. The last day can be incomplete.
- Activity counts **project commits**, not personal GitHub contributions. All authors are included except identifiable bot authors. Each SHA is counted once per repository across its current branch histories. Deleted branches and unreferenced commits are not reconstructed.
- Branch tips are resolved to immutable SHAs before commits are fetched. The UTC **committer date** determines the day. Repositories not pushed since the window began skip commit lookups.
- Language mix comes from GitHub's language byte totals on each repository's **default branch**. Release branches may contain newer code. Language percentages describe public source volume, not skill or time spent.
- The release count includes published releases and pre-releases within the window. Drafts are excluded. The timeline shows the most recent six, sorted by **publication timestamp**, not tag name or API response order.
- A numeric tag supplies the displayed version. For tags such as `Release`, the version is read from the published JAR filename when possible. A source branch without a GitHub release is never counted as one. `PUBLISHED` means a GitHub release exists; it does not certify production readiness.
- `data/profile.json` contains only public project names, links, aggregate counts, language bytes, and published release metadata. It stores no tokens, commit messages, author emails, or private repository details.

The accompanying README project descriptions are an editorial snapshot from August 2026. Their links intentionally point to the documented release or source branch, which may differ from the default branch. Daily generation updates **only** the charts and their data, not the project descriptions.

## Refresh behavior

`.github/workflows/profile-metrics.yml` runs daily at **06:23 UTC**, when its generator/workflow/tests change on `main`, or through **Actions → Refresh profile visuals → Run workflow**. Scheduled runs may be delayed by GitHub; public-repository schedules can be disabled after 60 days of inactivity. The activity card's date and the workflow history show whether a refresh has occurred.

The workflow uses the built-in `GITHUB_TOKEN`; no personal access token or extra secret is needed. Write permission is limited to repository contents. The checkout action is pinned to a verified commit. API reads are paginated, transient failures have bounded retries, and incomplete reads fail the run rather than publish partial statistics.

All output is rendered and parsed before files are replaced. A failed run leaves the last committed images available. Commits are made only when output changes, are authored by `github-actions[bot]`, and cannot retrigger the workflow because generated paths are not push triggers. The workflow uses a normal push; concurrent changes to `main` are never force-overwritten.

## Local use

Python 3.10 or newer is sufficient; there are no third-party Python dependencies.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/profile_metrics.py
```

An optional `GH_TOKEN` environment variable raises the API request limit for public reads. Never put a token into a file or command argument. Without authentication, GitHub's public API request limit may be too small for all branch histories; the workflow has its own token.

To change the visuals without making network requests:

```sh
python3 scripts/profile_metrics.py --snapshot data/profile.json
```

The palettes and SVG layouts are in `scripts/profile_metrics.py`. GitHub READMEs cannot run interactive JavaScript, so the motion is pure SVG/CSS and every chart also works as a static image.

## API references

The collector uses GitHub's [public repository and language endpoints](https://docs.github.com/en/rest/repos/repos), [branch listing](https://docs.github.com/en/rest/branches/branches), [commit listing](https://docs.github.com/en/rest/commits/commits), and [published release listing](https://docs.github.com/en/rest/releases/releases). Scheduling follows GitHub's [workflow event documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
