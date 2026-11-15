# Ticket 86: actual Agent replay and sweep — 2026-11-15

Requirements: [ticket 86](../../../.scratch/verification-gap-closure/issues/86-verify-configuration-and-actual-agent-replay.md),
[configuration/replay](../../../docs/experiment-records.md#configuration-resolution-and-replay),
and [baseline multirun grouping](../spec.md). Blockers 01 and 02 were independently
accepted before execution. Source: `bce7df823f85f4c52ad7785ca2800dce691e20c1` with
the unrelated count-fix diff present; none of the affected replay paths changed.
No remote fetch, product changes, SDK mocks, GPU work, or training occurred.

## Executed checks

All checks below **passed** on owned environment `cy-it-e3dd8d`, Python 3.12.13,
ClearML SDK 2.1.10 and Agent 4.0.17, with nice 19 and two CPU-library threads.
Fresh independent review passed; all 143 retained evidence hashes and the scoped execution claims were checked.

- Production `cy-init-config` exported the `cy-predict` wrapper, command defaults,
  Faster R-CNN ResNet50-FPN preset, and native groups. Production `cy-predict
  --config-dir … --config-name cy-predict --cfg job --resolve` reloaded the tree
  with explicit checkpoint, two frozen corpus images, CPU device, image size 128,
  project/tags and output. The resolved YAML is retained.
- A real ClearML task received canonical `run` configuration through the server.
  Before enqueueing, its remote output changed from `local-default.csv` to
  `remote-observed.csv`, and `model.predict.max_det` changed from 2 to 1. The
  Agent's bare entrypoint called production `predict.main()` without command-line
  overrides or local native-backend selection. It restored Faster R-CNN before
  runtime initialization, loaded the checkpoint, and wrote exactly one detection
  to the remote output; the local-default output was absent.
- Task `47ee2eada10f4ab6a78397c05e9db39c` moved from queued to in-progress to
  completed on queue `ticket86-attempt2-cy-it-e3dd8d`. The task completed after
  22.61 seconds; the probe additionally waited for the Agent's explicit worker
  exit status 0 before stopping the owned Agent group. Backend, preset, CPU device,
  maximum detections and output in freshly downloaded canonical configuration
  matched worker observations. Agent-provided `CUDA_VISIBLE_DEVICES=none` remained
  unchanged before and after the production command.
- Production Hydra BasicLauncher executed a two-case CPU sweep with
  `model.predict.max_det=1,2`, the same checkpoint and inputs, explicit ownership
  tags, and automatic isolated outputs. Tasks `81840896366647ad952dc79443e3a5b0`
  and `ea0184aa70c7405488b865ba1726711e` completed with distinct IDs and names.
  Both retained the same newly generated `multirun-20261115-201456-…` tag,
  while their downloaded canonical configurations retained values 1 and 2.
- A separate readback process forced fresh downloads of `gt_csv` and
  `predicts_csv` for all three accepted tasks. Every downloaded byte hash matched
  its server artifact hash. Canonical `run` JSON was independently downloaded for
  every task. Each combined prediction artifact has three rows (two ground-truth
  rows and one prediction); this is distinct from the one-row native prediction CSV.

The task wording's "configuration artifacts" refers here to the maintained ClearML
configuration objects: canonical `run` is stored/downloaded as a configuration,
not as an extra artifact. No duplicate configuration publication was introduced.

The historical checkpoint has hash
`26d604d4119aaf9a24a3b0339ee283fe8ba50b23eae76bc7d1ca8700ab2e1020`, native
ResNet50-FPN descriptor, one `square` class and 128×128 preprocessing. It establishes
checkpoint/backend replay only. Its vocabulary is incompatible with the Severstal
quality corpus; these runs do not qualify export quality or claim meaningful defect
detection. Ticket 68 retains that separate gate. The sweep uses the contracted local
sequential launcher, while actual Agent scheduling is demonstrated by the remote run.

## Probe correction, evidence and cleanup

The first task `559883f7baa149d68af92e4d4cf2bb4d` completed prediction/readback,
but its probe terminated the Agent after task completion before the process monitor
reported a worker exit. Its process-exit observation is incomplete and is not used
for acceptance. The second attempt above explicitly waits for worker exit 0;
no production change was needed. Both owned Agent groups stopped afterward.

Durable evidence lives under `runs/verification-gap-closure/replay-evidence/`:
generated/reloaded YAML, canonical downloads, scripts, redacted Agent/sweep logs,
transitions, device observations, local outputs, and forced artifact downloads.
`sha256.json` covers all retained members and was independently checked before any
cleanup. Credentials are obtained from the lifecycle in memory; credential-bearing
Agent diagnostics are redacted in both staging and retained logs. Source fixture
and checkpoint bytes remain unchanged.

After independent review, all four owned replay task records and their owned artifacts were deleted, and a fresh query found none of those task IDs. Both temporary queues were deleted. The 181,780-byte local replay arena, including SDK caches and transient outputs, was removed. The checksummed `cleanup.json` receipt was added to the durable bundle. The first cleanup verification used `Task.get_tasks(task_ids=…)`, which raises for deleted IDs; a fresh `Task.query_tasks` confirmed absence. This probe correction did not change product behavior. Ticket 86 is accepted. The shared environment belongs to the
campaign coordinator and is not deleted by this consumer. No unrelated tasks,
services, source assets or user SDK settings were changed.
