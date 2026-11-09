# Contract: Release

1. Accept: clean branch tip, `task acceptance` (plus `release-acceptance` before delivery),
   mutation report against `master` for code changes, independent review. Record `ACCEPTED_TIP`.
2. Without push authorization: stop.
3. Under `flock -n <git-common-dir>/clearml-yolo-release.lock`: verify tip, clean tree,
   `git fetch origin`, `merge --ff-only origin/master`, `merge --ff-only <branch>`,
   `semantic-release version --print`, then
   `CY_RELEASE_CHECK=1 SKIP=verify semantic-release version --no-push --no-vcs-release`
   (its build command runs `uv lock --upgrade-package clearml-yolo` and `release-commit-check`),
   `git push origin master --follow-tags`; confirm with `git ls-remote`.
4. No releasable commits → no version, success.
5. Failure leaves staged version files: restore only this attempt's changes, fix on branch,
   re-accept. Never hand-edit versions or tags.
Weight releases (`weights-*`) follow `docs/development.md#model-weight-releases` unchanged.
