# Replacement / cleanup manifest

This delivery introduces the new dashboard namespace and is intended to replace the previous generated profile system when publication is authorized.

New authoritative paths:

```text
README.md
assets/profile-dashboard/
data/profile.json
data/project-editorial.json
data/project-main-activity.json
scripts/profile_dashboard.py
scripts/profile_dashboard/
scripts/render_previews.py
tests/test_profile_*.py
.github/workflows/profile-dashboard.yml
docs/
```

The following legacy generated paths should be removed in the publication commit so the repository does not carry two profile engines indefinitely:

```text
assets/profile/
scripts/profile/
scripts/profile_metrics.py
.github/workflows/profile-metrics.yml
tests/test_profile_metrics.py
```

If an older `tests/test_profile_design.py` belongs to the previous generator, replace it with the version in this delivery rather than keeping both. Existing unrelated repository files, licenses, and credits should remain untouched.

No deletion has been performed on GitHub as part of this delivery because publication was not authorized.