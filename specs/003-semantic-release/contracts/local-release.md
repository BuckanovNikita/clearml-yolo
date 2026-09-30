# Local Release Contract

`uv run --locked --no-sync python scripts/local_release.py` is the post-commit entrypoint
and the manual retry command. It runs from the repository root. Development dependencies
must be installed. It creates no application entrypoint.

`--changelog` is the always-running pre-commit entrypoint, with no filename arguments.
It regenerates English CHANGELOG.md from full committed Conventional Commit history,
including Unreleased entries and historical releases, excluding generated release
commits. The pending commit is included by the next refresh or its release preparation.
The file is generated in full; manual edits are replaced. It never stages changes.
Exit 1 means changed output (including initial creation) requiring review/staging and
another commit attempt, or a reported generation error. Exit 0 means unchanged output
or preservation of a recorded release attempt. Shallow history is rejected without fetch.
Named feature branches can refresh history without receiving automatic release tags;
detached HEAD refresh is skipped.

Exit 0: release complete or an explained benign skip (branch, recursion, history operation,
no release changes, already completed). Exit 1: preflight/command/metadata/tag failure,
dirty-tree deferral, or concurrent lock. Failures explain that the original commit remains
and name the retry command. Post-commit failures cannot change Git's successful commit status.

`--install-hooks` installs standard pre-commit checks and a project-owned post-commit
launcher using `pre_commit run --hook-stage post-commit --all-files`. Existing custom
post-commit hooks are refused without replacement. Reinstalling an owned launcher is safe.
Plain `pre-commit install` installs only pre-commit and does not install the release launcher.

The hook is post-commit-only, always runs, accepts no filenames and supplies `--post-commit`.
This mode also skips completed amend/cherry-pick/rewrite reflog actions; manual retry
is available after those operations finish. Existing quality hooks
are pre-commit-only. Release commits run those checks normally. The private
`CLEARML_YOLO_RELEASE_ACTIVE=1` environment variable suppresses nested release execution
and changelog refresh; quality checks still run. A recovery record also preserves the
prepared changelog during manual pre-commit invocations before the tag exists.

Version policy: master only; vX.Y.Z; fix/perf → patch; feat → minor; breaking → minor below
1.0; non-release types alone → no release. All unreleased reachable history is included.

An operation writes only pyproject.toml, uv.lock, CHANGELOG.md and private Git metadata, creates one
release commit and annotated tag, and never rewrites prior refs. No push/fetch/build/
publication occurs. Manual pushes explicitly name the desired tag. Release preparation
uses PSR's versioned changelog rendering, including the source commit. Recovery metadata
stores its SHA-256 before the checked commit; validation rejects changed content.

A failed metadata preparation leaves files for inspection. Resolve the reported cause,
inspect the diff, and finish only the intended version changes and prepared changelog as
`chore(release): VERSION`. The installed hook then revalidates that matching release
commit and creates its tag; run the retry command explicitly when the hook is absent or
tagging still fails. A completed attempt is a no-op. Changed history or unrelated file
changes are rejected rather than guessed safe.

Legacy recovery records without a changelog checksum cannot tag automatically under
this contract; inspect and resolve that attempt explicitly before starting another.
