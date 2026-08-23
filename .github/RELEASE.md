# Release recovery

The normal release flow is driven by `release/vX.Y.Z` pull requests into `main`.

If release finalization fails before the tag is created, fix the underlying workflow problem first, then recreate the same `release/vX.Y.Z` branch from the current `main` and open a small recovery PR. Merging that PR retriggers `finalize-release.yml` with the fixed workflow while preserving the original version.

Do not rerun an old failed finalizer after changing the workflow: GitHub Actions reruns the workflow definition associated with the original run.
