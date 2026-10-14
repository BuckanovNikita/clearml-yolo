# Local release: 2026-10-15

The user requested completion of all started local work, commits and release pushes.
This authorizes local delivery with the previously disclosed physical multi-GPU
acceptance still pending. It does not change the result of that unexecuted check.

## Scope and preservation

Feature implementation and prior verification are recorded in
[verification.md](verification.md). Upstream documentation commits `38dada3` and
`e1b6346` were incorporated before release. Content fingerprints confirmed that
only `docs/development.md` changed during integration; the feature code, local
overrides and unrelated grid-search draft were preserved exactly.

The release continuation adds workflow evidence and generated version/changelog
metadata, with no additional module or dependency changes. The existing
[architecture record](architecture.json) remains authoritative and keeps the
physical check as not run. Its complete acceptance remains pending, while local
implementation, architecture checks and independent review have passed.

## Local checks and delivery

Implementation commit `c450411b6ba7dc0cb4fbde2259cd79f43ffdd2d7` passed every
applicable installed pre-commit hook, including full pytest, Ruff, mypy,
import-linter and Vulture. The post-commit release check correctly deferred
version creation on the temporary release branch. The staged package had no
local source overrides or test-tool runtime dependencies; exact working overrides
were restored afterward and the index was empty.

Fresh independent release review accepted the local scope and companion guidance,
subject to actual generated-release, build and remote-ref checks. Its one minor
record omission was corrected by adding the generated changelog to architecture
scope. Markdown lint passed 13 files and validation passed 190 local links.

Source and generated-release commits run the installed ordinary hooks.
`UV_NO_SYNC=1` preserves the prepared optional-backend environment and prevents
dependency synchronization; it does not disable any check. Temporarily remove
the exact local `[tool.uv.sources]` section for each commit and restore it
unstaged after hooks finish, including failures.

The native release helper completed successfully and created `v0.29.0` at
`28db0665127e966e4dfe802d891a7c4df14cdce4`. The generated release commit passed
its ordinary hooks, including full pytest; only the root package version in
`pyproject.toml` and `uv.lock`, plus the generated changelog, changed. Dependency
versions and sources were preserved.

Wheel and source distribution builds passed from an immutable candidate tree.
The annotated tag's tree matched that exact built tree. Archive checks confirmed
the queue control, guardian, queue runner and supervision modules, the declared
console entrypoints, version metadata, absence of test tools from runtime
dependencies and absence of local source overrides. Both GPU help commands
passed using the extracted wheel rather than the editable source package.

An atomic push published `master` and `v0.29.0`. Remote readback confirmed the
branch and peeled tag at the release commit above and annotated tag object
`c8c4257ac43eed59ad7aa7c8280af49c49568abb`. Exact local source overrides and the
unrelated draft were preserved, the index was empty, and release locks/recovery
metadata were cleaned. A frozen inexact sync updated only the local project
installation from `0.28.0` to `0.29.0`, preserving optional backend packages.

The companion usage-skill collection was then committed and atomically published
as `v0.2.1`, commit `755e9860cc8dd46431accd260890cc653a292326`, annotated tag
object `95da65bce06dfb6743f69dceadb5915d00e90ef7`. Remote branch and peeled-tag
readback matched that commit. GitHub reported the collection's new location as
[custom-opencode-skills](https://github.com/BuckanovNikita/custom-opencode-skills/tree/v0.2.1);
the same refs were also verified directly at that destination. The existing
`corp-skills` checkout and origin alias were retained.

Companion discovery found all four packages; Markdown lint passed all 30 files,
frontmatter and six package/evidence links passed, architecture record validation
passed, and final independent review accepted all eight task-owned files. The
collection worktree is clean. The primary repository retains only the exact
pre-existing local dependency overrides and unrelated untracked draft after
its final evidence commit; the task-owned temporary release branch was deleted.

The full feature architecture acceptance check still returns exit 1 solely for
the unexecuted physical GPU check. The user-authorized local release does not
convert this to a pass or close T015/T016. No GitHub Release object, package upload,
deployment or skill installation was performed.

The [remote GPU instructions](../../docs/ddp-testing.md) remain the next step for
physical multi-GPU/NCCL, compiled CUDA and actual ClearML publication/download
acceptance.
