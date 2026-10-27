# Release pair verification

Date: 2026-10-27. Scope: fresh CY 0.41.0 / cy-queue 0.1.2 release checks,
following the [paired gate](../../../docs/development.md#paired-cy-and-queue-release-check).
Earlier [single-GPU pair evidence](single-gpu-queue.md) remains historical.
The user requested a release after receiving the physical YOLO/DDP gaps; these
ordinary checks do not establish native GPU execution or ClearML publication.

## Frozen inputs and isolation

The parent fetched both remotes before capture. Source bases matched the fetched
remote default branches: CY `9fd2294ab219c534fcce87b59eea7b56e9d01173`
(`v0.40.0`) and queue `9a6fccd86b8958a77809e4d2e7e2cc178d0a73ee`
(no queue tags). The real queue source version was promoted to its already tested
0.1.2 proposal before freezing all queue inputs. Its bound remains
`clearml-yolo>=0.38,<0.42`; no queue runtime or test change was made for this release.
The pre-existing eleven-case null-batch regression is included.

Capture copied tracked and nonignored untracked files, preserving symlinks and
rejecting racing changes with before/after hashes. Original manifest identities:

| Source | Files | SHA-256 of original manifest |
| --- | --- | --- |
| CY | 692 | `48dd797023e46af2fb6de6ec7d25d6c7f7bfa4cd3c9cf68692c5dabd052142b4` |
| Queue | 90 | `f99813cd1ec6349447c38039a602d1cfee2019762d3dd4da2b110c44555e0865` |

Approved external copies remained unchanged: digital-metrics
`6e801be1564dce458294eb23592cc1aa0939c4d9` and report-generator
`d10aa395d08f738e92e04e076cee93b3a993bf8f`.
Only CY snapshot project/root-lock versions changed from 0.40.0 to proposed 0.41.0;
parsed TOML equality checked all other metadata. Queue snapshot version was already
0.1.2. The snapshot initially retained the complete local uv source section.
The parent subsequently removed that section for canonical verification and release;
the final actual-version refresh must match that released metadata.

The disposable environment uses Python 3.12.13 and uv 0.11.32. All commands set
`CUDA_VISIBLE_DEVICES=''` and `UV_LINK_MODE=copy`. Copy mode prevents dependency
installation or eventual cleanup from changing operational-environment file identities.
Neither operational environment nor original dependency source was modified.

## Proposed release pair

From the CY snapshot, with approved external copies present:

```bash
uv export --frozen --no-hashes --no-emit-project --format requirements-txt \
  --output-file ../../requirements.txt
uv venv --python /path/to/prepared/python ../../venv
uv pip install --python ../../venv/bin/python -r ../../requirements.txt \
  -e . -e ../cy-queue
uv pip check --python ../../venv/bin/python
```

Normal joint dependency resolution passed without `--no-deps` or dependency
replacement. All 282 installed packages were compatible. Explicit assertions from
outside both checkouts confirmed exact source/installed CY 0.41.0 and queue 0.1.2,
imports from isolated snapshots, and a queue requirement admitting 0.41.0 while
rejecting 0.42.0. From the queue snapshot with isolated executables:

| Check | Result |
| --- | --- |
| `ruff check .` | Passed |
| `ruff format --check .` | 82 files already formatted |
| `mypy .` | No issues in 68 source files |
| `lint-imports` | 2 contracts kept, 0 broken |
| `python -m pytest -q` | 512 passed, 7 physical GPU tests deselected, 4 warnings in 120.99 s |
| `cy-queue --help` outside both checkouts | Passed |

The warnings are the existing hydra-zen/Pydantic deprecation. The full ordinary suite
covers metadata identity, the eleven null-batch integration cases, negative import
contracts, immutable snapshots, ownership, handoff and process cleanup. Controlled
GPU boundaries do not prove physical accelerator behavior.

Post-run audit found no queue or external-source drift. CY differed only by the
parent's required removal of the local uv source section. Queue task Markdown
validation passed (two files, zero issues); architecture plan and acceptance
structure validators and scoped diff whitespace checks passed. The architecture
validator reuses the prior accepted compatibility-preparation review; fresh release
review remains parent-owned.

## Final actual-version refresh

The normal CY hooks produced feature commit
`6ff30fe` and version commit `e12114535caf399b9e8db9d3dc9693eb64581587`; annotated
`v0.41.0` points to that version commit. The final refresh read actual committed
`HEAD:pyproject.toml` and `HEAD:uv.lock` with `git show`, then copied those exact
bytes into the existing isolated snapshot. Their SHA-256 identities are recorded
in private `actual-committed-metadata.json`. The committed metadata has no local
uv source overrides; the working checkout's restored overrides were preserved.

Normal joint resolution and reinstall again passed for 282 packages with
`UV_LINK_MODE=copy`, using the existing frozen requirement list and approved copied
external sources. No dependency entry or approved source revision changed. Exact
source/installed CY 0.41.0 and queue 0.1.2 and isolated import origins passed again;
`uv pip check` found all 282 packages compatible. Final checks all exited 0:

| Actual-version check | Result |
| --- | --- |
| `ruff check .` | Passed |
| `ruff format --check .` | 82 files already formatted |
| `mypy .` | No issues in 68 source files |
| `lint-imports` | 2 contracts kept, 0 broken |
| `python -m pytest -q` | 512 passed, 7 physical GPU tests deselected, 4 warnings in 115.85 s |
| `cy-queue --help` outside both checkouts | Passed |

Before and after the refresh, source audits confirmed zero queue or external-source
drift. CY differences from the original capture were confined to release metadata,
Markdown and feature records; runtime source, packaged configuration, tests and
verification configuration remained identical. Thus final runtime inputs match the
released source with the exact committed release metadata. Test processes completed
and installed metadata remained 0.41.0/0.1.2; no operational install occurred.
Fresh parent-owned independent reviewers accepted the integrated CY and companion
change conditional on this final pair check; that condition now passes. The parent
still owns final evidence inspection, acceptance and authorized delivery.

## Evidence and delivery boundary

Raw logs, commands/exit codes, manifests, metadata and source-drift reports are in
ignored `.tmp/queue-release-vduuee6i/`. All proposed-check test processes completed;
only retained task-owned files remain. Queue files stay frozen while the parent
canonical verifier runs. Parent evidence inspection, commits and remote ref verification remain separate
delivery steps. Final actual metadata refresh and full paired checks passed above. No queue tag, GitHub Release,
asset/package publication, deployment or operational installation is included.
