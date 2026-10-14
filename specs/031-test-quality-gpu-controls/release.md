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

Inspect the generated version, lockfile and changelog and the built distribution.
Push the intended branch and annotated Git tag explicitly and verify remote refs.
The companion usage-skill collection is published afterward under its own release
procedure. No GitHub Release object, package upload, deployment or skill
installation is part of this delivery.

Check outcomes and published refs will be recorded after those actions finish.
The [remote GPU instructions](../../docs/ddp-testing.md) remain the next step for
physical multi-GPU/NCCL, compiled CUDA and actual ClearML publication/download
acceptance.
