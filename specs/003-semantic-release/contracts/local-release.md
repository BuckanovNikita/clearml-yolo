# Local Release Contract

`uv run --locked --no-sync python scripts/local_release.py` is the post-commit entrypoint
and the manual retry command. It runs from the repository root. Development dependencies
must already be installed. It creates no application entrypoint.

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
`CLEARML_YOLO_RELEASE_ACTIVE=1` environment variable suppresses only nested release execution.

Version policy: master only; vX.Y.Z; fix/perf → patch; feat → minor; breaking → minor below
1.0; non-release types alone → no release. All unreleased reachable history is included.

An operation writes only pyproject.toml, uv.lock and private Git metadata, creates one
release commit and annotated tag, and never rewrites prior refs. No push/fetch/build/
changelog/publication occurs. Manual pushes explicitly name the desired tag.

A failed metadata preparation leaves files for inspection. Resolve the reported cause,
inspect the diff, finish only the intended version changes and commit them as
`chore(release): VERSION`, then retry. A clean matching completed release commit is
revalidated and tagged directly; a completed attempt is a no-op. Changed history or
unrelated file changes are rejected rather than guessed safe.
