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

Source and generated-release commits must run the installed ordinary hooks.
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
