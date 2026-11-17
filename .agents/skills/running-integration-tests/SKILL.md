---
name: running-integration-tests
description: Use when running live tests or manual native checks, managing an owned test environment, or investigating its failures.
---

# Verify live outcomes

Paths start at the repository root. First read the module docstring of
`tests/integration/lifecycle.py` (environment selection, ownership, deletion guard, exit
statuses), `.agents/skills/running-integration-tests/references/machine-workflow.md` and
the affected `docs/feature/` files.

1. Check host capacity, then run `task infra-check` and classify its exit status by
   `docs/development.md#acceptance-tiers`. Run the selected stage (`integration`,
   `acceptance` or `release-acceptance`); a focused run establishes only what it selected.
2. Severstal suite (`pytest -m severstal_gpu`, or `CY_SEVERSTAL_ARGS` for
   `release-acceptance`): `--run-severstal-gpu`, `--severstal-dataset` (a corpus prepared
   by `scripts/severstal.py`; the harness requires its frozen seed-0 160/40/40 subset),
   `--severstal-artifacts`, `--severstal-clearml-project` and `--severstal-tags` are
   required. Pick `--severstal-device` and a `--severstal-free-vram-mib` reserve from
   current host load; the reserve applies to measurement and training, a breach cancels the
   scenario, and the allocator cap cannot protect it from external allocations.
   `--severstal-home` reuses a prepared cache and requires the artifacts inside it;
   `--severstal-backbone MODEL=PATH` supplies a local backbone. Each scenario trains one
   registered preset in the native, JSON or JSON+Mosaic variant for two FP32 epochs. It
   measures capacity afresh (product trial deadline 300 seconds), trains with the largest
   backend-valid batch within both capacity and 160 images, records raw capacity and the
   chosen batch separately, and fails rather than fall back to batch one or accept a
   native batch or epoch change; `--severstal-timeout` (default 1800 seconds) bounds the
   scenario. It checks execution, checkpoint reload, held-out predictions and ClearML
   records, not accuracy or equivalence between recipes.
3. By hand: `task infra-up` (`COMPONENTS=clearml` or `fiftyone` limits it); capture
   `infra-env` output, check its exit status, then evaluate it, never printing it (it
   holds credentials). Live tests use these session credentials, never the user's SDK
   configuration. Put `INTEGRATION_RUN_TAG` in explicit ClearML project names and tags and
   choose the local output directory. Provision optional SDK decoders beforehand; a check
   never installs or updates packages.
4. Before teardown keep logs, task and model IDs and readback results. The creator runs
   `task infra-down` and checks its deletion proof; an adopting session never deletes.
   `python -m tests.integration.lifecycle stop --dry-run` shows what would be deleted.
   `INTEGRATION_KEEP_DATA=1` keeps the environment `integration` created; remove it with
   `task infra-down ENV=<id>` within its 48-hour lifetime. Local run outputs stay until
   you remove them deliberately.

Observations automation does not prove; select only the affected ones:

- Native execution: CPU and GPU runs with disjoint validation and test inputs and empty
  images; direct and queued runs with identical settings when the queue is affected.
- Publication: independent API readback, forced artifact and model downloads, checkpoint
  loading, identity and threshold comparison; console lines and epoch scalars visible
  remotely within about ten seconds while training runs. Command completion proves no
  upload.
- Batch capacity: with an isolated `CY_HOME` and an idle GPU, run
  `cy-batch-estimate --imgsz 640 --models <model> --devices <index> --search-limit 3`;
  the editable table entry appears only after worker cleanup, and `batch=null` then
  resolves to it with its source recorded.
- Charts: standalone HTML exercising each affected normalization, legend, empty or unknown
  case, hover, caption and slot identity.
- FiftyOne App: install its plugin explicitly and inspect the affected views alongside
  database, panel and containment checks.
- Detector and export: the affected rows of `docs/feature/detector-families.md` and
  `docs/feature/export.md`; real export and target compatibility are separate from
  numerical quality.

For non-finite training values, keep the native results and failing configuration.
Check inputs, model and EMA state and the first failing computation separately (finite
checkpoint tensors do not prove finite AMP activations). Compare imported preprocessing
paths, native binary hashes and prepared tensors, not only package versions. Run any
precision comparison apart from the scientific run: changing precision, optimizer, batch
or data makes a different recipe.

Leave source data and the user's SDK settings untouched. Record commands, source
identities, task and model IDs, observations, limitations and cleanup in the Linear issue.
