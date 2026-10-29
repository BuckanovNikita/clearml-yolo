# Source installation outside the checkout

Date: 2026-10-29. Feature: [local Russian reference](../spec.md).

## Method and scope

Verified a noneditable installation of the current working CY source snapshot,
version `0.41.0`, using Python `3.12.13`. The checkout baseline was
`0037059dcf8a8ed16582f256b98036480cabd842`; the snapshot also included current
uncommitted features `007` and `008`. This is pre-release installation evidence,
not evidence for a later version or source change.

Created a task-owned temporary source tree, virtual environment and unrelated
working directory outside the checkout. Copied the current package source,
`pyproject.toml` and README into the source snapshot, excluding Python caches.
Installed that source **noneditably** into the temporary environment:

```text
uv venv --python <prepared-interpreter> <temporary-environment>
uv pip install --python <temporary-environment>/bin/python --no-deps <source-snapshot>
```

The installer used its internal ephemeral source-build artifact; no project wheel
or source archive was produced or retained as a release deliverable. After the
local CY installation, a task-owned `.pth` attached the prepared environment's
dependency site-packages. That reused the approved dependencies without copying
or modifying them. CY's own package remained in the temporary environment's
site-packages and took precedence over the original editable source.

The install-only `--no-deps` step intentionally tests source packaging/imports,
not clean dependency resolution. The separate [paired check](paired.md) ran normal
resolution without `--no-deps` and verified metadata compatibility.

## Observations

Under `python -I`, asserted that both `clearml_yolo.__file__` and the documentation
worker module resolve inside temporary **site-packages**, not either source tree.
Installed direct-URL metadata reports a noneditable source installation.

Compared every source package file with its installed counterpart: all **336**
files were byte-identical. The deterministic path/content package digest was
`13168b45e89e2c073bca488805cd29f4540a412d688266596fa3e8398b09cbbb`.
Verified packaged HTML, CSS, JavaScript, tutorial inventory and generated tutorial
pages through `importlib.resources`.

From the unrelated working directory, with `PYTHONPATH` removed and a task-owned
workspace for any ordinary CLI scratch, all checks passed:

- Installed `cy-docs --check`: 452 fields, 156 configurations and 8 tutorials.
- Installed `cy-docs --help`, `cy-init-config --help`, `cy-train --help` and `cy --help`.
- Installed interpreter `-I -m clearml_yolo.entrypoints.documentation.worker`,
  submitting a train preview with an absent CSV path, CPU and one epoch: one job,
  no worker/schema errors, and the original CSV string retained in composed YAML.

The worker test used the separately installed package and did not access the
absent dataset or launch training. It confirms installed worker/module and asset
availability, not native workload success.

## Cleanup and limitations

The task-owned source snapshot, virtual environment and unrelated working directory
were removed after successful checks. No existing environment or dependency source
was changed by the isolated installation. The authorized editable pair refresh is
recorded separately in [paired verification](paired.md).

Dependencies were deliberately reused; this was not an independent clean-machine
or minimum-version dependency test. Browser interaction, GPU execution, artifact
publication and final proposed-version release checks remain separate gates. A
later package-data or runtime-source change requires reconsidering this snapshot's
installation evidence.

## Refreshed source snapshot, 2026-10-29 10:22 UTC

The observations above describe the earlier snapshot. This appendix records a new
noneditable installation after the later feature changes; it does not replace the
historical results. Verification ran from `2026-10-29T10:21:49.353141Z` through
`2026-10-29T10:22:29.005299Z`, using Python `3.12.13` and CY version `0.41.0`.
The checkout baseline remained `0037059dcf8a8ed16582f256b98036480cabd842`, with
uncommitted features `007` and `008` included.

The copy completed at `2026-10-29T10:21:49.425315Z`; the latest package-source
modification timestamp was `2026-10-29T10:16:21.940445Z`. The source inventory
matched before copying, after copying and after verification. All **337** package
files, including package data and excluding Python caches, were byte-identical
between the source snapshot and installed package, with no missing or extra files.
The SHA-256 package digest was
`10a9731e15e120db308dc8f7112c5c2a2dacf208bc5206cd383ca1df4aeb0941`.
Its input is the UTF-8 concatenation of sorted records
`relative_posix_path + NUL + sha256(file_bytes) + newline`.
The copied `pyproject.toml` SHA-256 was
`8b7a5bb6249e7b195fd6d1a7b8c8fce9617c4aa9a145584849b4b55b2c558fe4`.

Repeated the method above in a newly created temporary source tree, virtual
environment and unrelated working directory. The following commands all exited 0;
placeholders denote task-owned temporary paths:

```text
uv venv --python <prepared-python-3.12.13> <refresh-environment>
uv pip install --python <refresh-environment>/bin/python --no-deps <source-snapshot>
<refresh-environment>/bin/python -I -c <identity-and-package-resource-check>
<refresh-environment>/bin/cy-docs --check
<refresh-environment>/bin/cy-docs --help
<refresh-environment>/bin/cy-init-config --help
<refresh-environment>/bin/cy-train --help
<refresh-environment>/bin/cy --help
<refresh-environment>/bin/python -I -m clearml_yolo.entrypoints.documentation.worker
```

A temporary `.pth` reused the prepared dependency site-packages only after the
noneditable CY install. With `PYTHONPATH` removed, identity checks under `-I`
confirmed that `clearml_yolo.__file__` and the documentation worker module both
resolved beneath the new environment's `lib/python3.12/site-packages`, not either
source tree. Installed metadata reported version `0.41.0` and a source direct URL
with empty `dir_info`, confirming a noneditable installation. Explicit resource
reads succeeded for the HTML entry page, JavaScript, CSS, tutorial inventory and
all eight rendered tutorial pages.

Installed `cy-docs --check` reported:

```text
Documentation OK: 467 fields, 156 configurations, 8 tutorials
```

Ran the worker command twice as real fresh subprocesses, each receiving one JSON
request on stdin from the unrelated working directory:

- YOLO train preview with an absent CSV path, `ultralytics.device=cpu` and
  `ultralytics.epochs=1`: one job, no worker or schema errors, the original CSV
  path retained in YAML, and the input still absent afterward.
- Faster R-CNN train preview with `model=fasterrcnn/resnet50_fpn`,
  `model.train.device=cpu`, `model.train.epochs=1`, a dataset CSV path,
  `model.train.weights` and `transforms=albumentations` with
  `transforms.pipeline_file`: one job, no worker or schema errors, and all three
  supplied paths retained in YAML.

For the second request, created three task-owned sentinel files containing invalid
dataset, weight and augmentation data. A Linux inotify observer watched each file
for `IN_OPEN`, `IN_ACCESS` and `IN_MODIFY`. A deliberate parent-process read first
produced both open and access events, validating the observer. After draining that
positive control, the real worker produced **zero events** on all three files.
The production worker/imports were not patched. This establishes that the tested
preview did not open, read or modify those supplied inputs; package, dependency
and internal configuration reads remain necessary for composition.

This evidence-only appendix adds no module, interface, dependency rule or runtime
effect. Inspection covered the documentation CLI, worker, preview, validation,
package-resource adapter and existing feature architecture record. Module
acceptance and the parent canonical checks remain governed by that record.

The temporary source, environment, logs, input sentinels, ordinary-command scratch
and unrelated working directory were removed after verification, and no task-owned
worker processes remained. No project archive was retained as a deliverable and no
dependency source, version, lockfile or shared environment was deliberately changed.
Markdown and local links for this evidence file were checked successfully with
`python scripts/check_docs.py specs/008-local-docs/evidence/installation.md`.

The same limitations apply: reused dependencies do not establish clean dependency
resolution or a clean-machine install; the [paired check](paired.md) supplies
separate normal-resolution evidence. This is source version `0.41.0` evidence,
not a later proposed release version. Browser, native/GPU and ClearML publication
results remain separate gates, and later package-source changes require another
installation assessment.

## Post-review source refresh, 2026-10-29 11:21 UTC

Repeated the complete isolated source-install sequence after review fixes to
preview guards, document filenames, clickable examples, native batch descriptions
and parent-owned worker temporary directories. Earlier snapshots remain historical
evidence. This successful run started at `2026-10-29T11:20:29.042679Z` and finished
at `2026-10-29T11:21:12.930634Z`; the source copy completed at
`2026-10-29T11:20:29.104804Z`. The latest package-source modification timestamp
was `2026-10-29T11:17:04.541837Z`.

Python remained `3.12.13`, installed CY metadata remained `0.41.0`, and the checkout
baseline remained `0037059dcf8a8ed16582f256b98036480cabd842`, including the current
uncommitted features `007` and `008`. All **337** source package files matched the
noneditable installation byte for byte, without missing or extra files. Using the
same path/content digest algorithm documented above, the package SHA-256 was
`a8d169843d0b16dfecb83e2c4c1639e9751bf908f89a7c290b45151fea2497b7`.
The checkout inventory matched before copying, after copying and after all checks.
The copied `pyproject.toml` SHA-256 remained
`8b7a5bb6249e7b195fd6d1a7b8c8fce9617c4aa9a145584849b4b55b2c558fe4`.

The fresh `uv venv` and noneditable `uv pip install --no-deps` succeeded; dependency
reuse used only the temporary environment's `.pth`. Under `python -I`, the CY
package, worker entrypoint and `PreviewWorkers` adapter resolved beneath the new
environment's site-packages. Direct-URL metadata again had empty `dir_info`.
Resource reads verified all 12 entry-page, JavaScript, CSS, inventory and rendered
tutorial assets checked in the previous refresh.

From an unrelated working directory, every installed command in the previous
refresh sequence exited 0. The documentation check again reported **467 fields,
156 configurations and 8 tutorials**. `cy-docs --help`, `cy-init-config --help`,
`cy-train --help` and `cy --help` all produced help successfully.

Both fresh `python -I -m clearml_yolo.entrypoints.documentation.worker` previews
were repeated. The absent-CSV YOLO preview and the Faster R-CNN preview with
dataset, weight and augmentation sentinels each produced one job with no worker
or schema errors. Submitted paths remained in YAML. Linux inotify again detected
the positive-control read, then recorded **zero open, access or modification
events** on all three supplied input files during the real preview.

An additional isolated installed-interpreter check imported `PreviewWorkers` and
supplied its `worker_command("clearml_yolo.entrypoints.documentation.worker")`.
It submitted a real `PreviewRequest` containing `example.yaml` with train defaults
and an absent CSV path, plus CPU and one-epoch overrides. The successful response
had one job, no worker/schema errors and `--config-name example` in its command.
The parent process used a dedicated task-owned `TMPDIR`. Inotify observed matching
directory creation and deletion for `cy-docs-worker-djsqcwbn`; the directory root
was empty both immediately after the request and after `workers.close()`.
Neither the production worker nor its imports were patched.

The initial observer assertion also counted Python's temporary-directory
writability probe file, despite the installed worker succeeding and leaving an
empty directory. Inspection of the prepared interpreter's `tempfile` implementation
confirmed that probe. The successful full rerun counted `IN_ISDIR` creation/deletion
events for the worker directory separately; the probe file was also removed.
This corrects the verification harness, not application code.

Three further fresh installed-worker requests returned explicit errors and no jobs:
`hydra.job.chdir=true`, a submitted YAML `hydra` runtime block, and a document named
`example.yml`. The filename diagnostic required `.yaml`. These checks exercise
the reviewed rejection paths in the noneditable installation.

This appendix changes evidence only; the existing architecture record continues
to govern module acceptance. Both temporary verification environments, copied
sources, logs, sentinels and scratch directories were removed, with no owned worker
processes left. No source code, shared environment, dependency, version or lockfile
was deliberately changed. The evidence Markdown/local-link check passed with zero
issues. The dependency-resolution, proposed-release-version, browser and native
execution limitations stated above remain unchanged; successful worker cleanup
here covers real normal completion, with failure-path checks owned by the parent
canonical suite.

## Option-metadata refresh, 2026-10-29 11:43 UTC

After the catalog correction to use inert argparse defaults and boolean flag
shapes, repeated the isolated noneditable source installation with Python `3.12.13`
and CY version `0.41.0`. The run started at `2026-10-29T11:42:45.367655Z`, copied
the source by `2026-10-29T11:42:45.426917Z`, and finished at
`2026-10-29T11:43:15.480389Z`. The latest package-source modification timestamp
was `2026-10-29T11:40:35.430835Z`. The checkout baseline remained
`0037059dcf8a8ed16582f256b98036480cabd842`, including current features `007` and
`008`.

All **337** source package files matched the installed files byte for byte, with
no missing or extra files. The path/content SHA-256 defined above was
`0911f08f850d5b420d09bcbe809b58f990a1d5a4142b020ed189229017d03ba2`.
Inventories matched before copying, after copying and after verification.
The copied `pyproject.toml` hash remained
`8b7a5bb6249e7b195fd6d1a7b8c8fce9617c4aa9a145584849b4b55b2c558fe4`.

The fresh `uv venv`, source `uv pip install --no-deps`, installed `python -I`
identity/catalog check, `cy-docs --check` and focused installed worker checks all
exited 0. The package, worker entrypoint and worker-owner adapter resolved beneath
the new environment's site-packages. Installed direct-URL metadata remained
noneditable, and the 12 packaged documentation resources remained readable.
The documentation check reported **467 fields, 156 configurations and 8 tutorials**.

Assertions against the actual installed `build_catalog()` output and
`parser_for("cy-docs").parse_args([])` agreed:

| Catalog field | Constraint default | Shape | Argparse default |
| --- | --- | --- | --- |
| `cy-docs.--no-browser` | `default=False` | `flag (boolean)` | `False` |
| `cy-docs.--port` | `default=0` | `int` | `0` |

The previous temporary per-file manifest had been removed during cleanup, so
worker coverage was repeated rather than assuming individual hashes matched the
earlier snapshot. The fresh Faster R-CNN worker produced one valid job and zero
inotify open/access/modification events for the three supplied input sentinels,
after a successful positive-control read. A real installed `PreviewWorkers` call
with `example.yaml` produced one valid job; inotify observed matching creation and
deletion of `cy-docs-worker-r_2z3gpr`, and the dedicated temporary root was empty
after the request and `close()`.

For later comparisons, these verified file hashes are relative to
`src/clearml_yolo/`:

| File | SHA-256 |
| --- | --- |
| `adapters/documentation/worker.py` | `e0010cedf1739efaff2d1be8a14955c41a294688fd911745594ca6199d10fb2e` |
| `entrypoints/documentation/worker.py` | `124f1eb6b32435babe944e1ec42b15e8164cbcca739d45f01ce31827a589351f` |
| `entrypoints/documentation/preview.py` | `3075639f302c08482670aaaba996489bc13b631a66b13abc820ca4f54969ed94` |
| `adapters/documentation/files.py` | `9d6eba07dfce4398fe8db909456d1d73e362afe6bd41add0d3b85ddab2922ae6` |

This metadata-focused refresh did not rerun ordinary CLI helps or the three guard
rejection cases; their executed results remain recorded in the earlier refresh.
The task changed only this evidence appendix, leaving module acceptance with the
existing feature architecture record. Markdown/local-link validation passed with
zero issues. Temporary sources, environment, scripts, logs and fixtures were
removed, with no task-owned worker processes left. Source/shared dependencies,
versions and lockfile were not deliberately changed. Reused-dependency and
pre-release limitations remain as described above.

## Proposed 0.43.0 installation, 2026-10-29 15:03 UTC

Refreshed the noneditable installation after integration onto released feature
`007`, baseline `f8eb8a3c198806c08c0a41161aa4e8034dec0273`, with current feature
`008` included. Verification started at `2026-10-29T15:03:03.339698Z` and finished
at `2026-10-29T15:03:47.182258Z`. The source copy completed at
`2026-10-29T15:03:03.395798Z`; the latest package-source modification timestamp
was `2026-10-29T14:56:54.670170Z`.

The checkout remained at source version `0.42.0`. Only the copied root
`pyproject.toml` version was changed to the proposed release version `0.43.0`;
dependencies and their pins were preserved. Python was `3.12.13`. The source
`pyproject.toml` SHA-256 was
`0df497549cb28f609a82b88bf3294d2f57eac798cc0e15be60eee69e4b40c1d7`;
the proposed-version copy's SHA-256 was
`53939c39f561a06c34762991b711f08f33f8502cf0093bb50469bf10e389846b`.

All **337** package files, including package data and excluding Python caches,
matched the installed package by their individual content hashes, without missing
or extra files. The deterministic path/content SHA-256, using the algorithm
defined above, was
`881ce43b3977c4f2f5dd6bfccbe4e7dd04c639662b23a2e9e9c0b8b817322762`.
The inventories matched before copying, after copying and after verification;
the checkout's `pyproject.toml` bytes also remained unchanged during the run.

The task-owned source copy, new virtual environment and unrelated working directory
were outside the checkout. All commands below exited 0; placeholders identify
private verification paths:

```text
uv venv --python <prepared-python-3.12.13> <temporary-environment>
uv --no-cache pip install --python <temporary-environment>/bin/python --no-deps <source-copy>
<temporary-environment>/bin/cy-docs --check
<temporary-environment>/bin/cy-docs --help
<temporary-environment>/bin/cy-init-config --help
<temporary-environment>/bin/cy-train --help
<temporary-environment>/bin/cy --help
<temporary-environment>/bin/python -I <installed-identity-and-preview-check>
```

After installing CY noneditably, a temporary `.pth` exposed the prepared
environment's dependency site-packages. With `PYTHONPATH` removed, `python -I`
confirmed that the CY package, documentation worker entrypoint and `PreviewWorkers`
adapter all resolved inside the new environment's site-packages. Installed metadata
reported `0.43.0`, with empty direct-URL `dir_info`. All 12 previously enumerated
documentation resources were readable through `importlib.resources`.
Installed `cy-docs --check` reported:

```text
Documentation OK: 467 fields, 156 configurations, 8 tutorials
```

The installed `PreviewWorkers` adapter launched the real installed worker through
`worker_command("clearml_yolo.entrypoints.documentation.worker")`. Each named YAML
request produced one job, no worker/schema errors, the expected `--config-name`
argument and unchanged input-path strings in composed YAML:

- `example.yaml`: YOLO train with an absent CSV, CPU and one epoch.
- `native.yaml`: Faster R-CNN train with CPU, one epoch, and dataset, native-weight
  and augmentation sentinel files; `transforms=albumentations` selected the supplied
  augmentation path.
- `missing-native.yaml`: the same native train selection with all three supplied
  input paths absent.

A Linux inotify observer watched each sentinel for `IN_OPEN`, `IN_ACCESS` and
`IN_MODIFY`. A deliberate read produced open and access events for every file
before the production workers ran. After draining that positive control, all
requests together produced **zero events** on those files. Their contents remained
unchanged, and all absent input paths remained absent. Neither the production
worker nor its imports were patched.

Three additional real worker requests rejected `hydra.job.chdir=true`, a submitted
YAML `hydra` runtime block and an `example.yml` filename, each with explicit errors
and no jobs. The filename diagnostic required `.yaml`. Inotify recorded matching
creation/deletion events for all six `cy-docs-worker-*` directories. The dedicated
temporary root was empty after each successful preview and after `workers.close()`.

The source identities, exact command arguments and exit codes, per-file source
inventories, installed-check output and verification scripts are retained in
Git-private verification storage under `installation-release`. The temporary
source, environment, sentinels, ordinary-command scratch and working directory
were removed after capture; no owned interpreter or worker processes remained.
The installer used an internal ephemeral build artifact with its cache disabled;
no project distribution was retained as a release deliverable. No shared
environment, dependency source, repository version or lockfile was changed by
this bounded verification task.

This appendix has no module, interface, import-contract or runtime-effect impact.
Inspection covered the installed documentation CLI, worker entrypoint and owner,
preview composition, package resources and the existing feature architecture record.
Parent integration, canonical checks and fresh independent review remain governed
by that record. Markdown/local-link validation for this evidence file passed with
`python scripts/check_docs.py specs/008-local-docs/evidence/installation.md`.

The install-only `--no-deps` command verifies source packaging and installed
behavior with reused dependencies. It does not establish clean dependency
resolution; the [paired check](release-pair.md) supplies that separate evidence for the
proposed release pair. These observations cover a proposed-version source snapshot,
not a completed release or a later package-source change. Browser interaction,
native/GPU workloads and ClearML publication remain separate checks.
