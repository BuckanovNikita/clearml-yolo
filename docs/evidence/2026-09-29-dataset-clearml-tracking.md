# Dataset reuse and native ClearML tracking verification — 2026-09-29

## Scope and baseline

Feature 008 preserves the inspected 007 working baseline and the v0.8.0 release source.
Implementation lives in an isolated feature worktree. The original checkout and feature
selection were preserved; no commits, pushes, issues, or dependency revision changes were made.
The approved digital-metrics and report-generator revisions remain unchanged.

## Implementation and regressions

CSV SHA-256, dataset format and preparation version identify shared cache entries. Tests cover
reuse without image reads/copies/conversion, changed identities, missing splits, corrupt
metadata/YAML, interrupted builders, separate-process concurrency, native-consumer serialization,
original filenames/casing and label-stem collisions. Default and explicit cache roots are rejected
inside run-owned output directories. That final FR-004 gap was appended as convergence T029,
reproduced before the fix, and verified afterward.

Native callbacks run in the existing task owner. Tests cover installed callback discovery,
worker suppression, settings restoration, sanitized General parameters, upload/registration
failures and the same-model metadata barrier. Live SDK behavior required two regressions:
tags are unordered and metadata responses may include server bookkeeping keys. Unknown package
versions are omitted. Result provenance uses separate evaluation_result/fiftyone_result roots,
so canonical remote configuration still constructs typed executable inputs. Local and remote
replay credential regressions also reproduced and fixed storage redaction leaking into execution
inputs (T030); the focused replay/session suite passed forty tests. T031 removes duplicate
prediction argument dumps from run configuration, keeping meaningful normalization differences;
its prediction suite passed fifteen tests. A final live prediction and metrics readback verified
this publication shape and native image-size normalization from 98 to [128,128].

## Executed live acceptance

A synthetic immutable dataset contained twelve images across train/val/test, including a
negative image in each split and original uppercase .JPG filenames. CPU and GPU native training
ran for two epochs with explicit device, batch=2, imgsz=96, compile=false and amp=false.

- The first preparation copied twelve images and exported once; repeated CPU/GPU and standalone
  training recorded zero copies and zero exports. One completed shared cache entry remained.
- Thirteen completed command invocations passed exact artifact inventories and force-download
  content checks: pipeline with missing automatic baseline, paired CPU/GPU pipelines, standalone
  training/validation/comparison/report/ground-truth, empty prediction/metrics, historical/local
  model comparison, and a metrics run validating replay configuration after result publication.
- Four successful training invocations each had one native output model and no checkpoint
  artifact. Force-downloaded checkpoints loaded in YOLO. Hashes, labels, architecture, task/project
  association and best-role metadata matched actual checkpoints and source tasks. Native model
  finalization additionally verified names, framework, tags, descriptions and input/version fields.
- Scalars, Plots, Debug Samples, Configuration and Artifacts tabs were inspected in the actual UI.
  Native mosaics retained original filenames; validation label/prediction samples were retrieved.
- New native tasks, a newly created historical-format fixture and explicit local models all
  completed paired current-test comparison. Existing historical tasks were never modified.
  A separate instrumented live comparison asserted exact equality between source threshold
  mappings and scoring inputs, and identical image membership for both models. Rounded dashboard
  values were deliberately excluded from the exact-threshold assertion.
- Artifact rejection, model upload failure, callback-registration failure, flush rejection and
  SIGTERM interruption each returned nonzero and had server status failed. Local evidence survived.
- Canonical run/dataset/report Configuration Objects contained no configuration-artifact copies.
  Real stored metrics configuration reconstructed the typed evaluation and FiftyOne inputs.
  Remote General override and result-root filtering are covered by the clone-boundary regression.

## DDP compatibility and final native readback

Convergence T032 found that installed Ultralytics skips native integrations in the DDP
launching parent. The new relay preserves rank-zero callback events and event-time image
snapshots locally, then executes the installed callbacks in the owner. Its tests verify
exact scalar values, preview bytes, General redaction, one native model, incomplete-output
failure, final normalized arguments and a single-process no-op.

A real two-epoch CPU subprocess captured events with rank-zero capture explicitly enabled;
it did not initialize native ClearML tracking. The owner replayed all native events, published
one model, and recovered the worker's image-size normalization from 98 to 128. This harness
exercises worker serialization and publication, not distributed computation. Its first attempt
left the single-process native rank at -1 and correctly failed for a missing event journal;
that harness failure is retained separately from the corrected successful run.

A final actual GPU `cy-train` run after relay integration completed with zero cache copies or
conversions. Both final tasks had one native best model, downloaded and loaded successfully,
with matching checkpoint hashes, labels/design, task/project association, General parameters,
native scalars/plots and train/validation preview series. The GPU command's only artifact was
its ground-truth CSV; the relay-only harness produced no artifacts.

## Verification gates

The final full pre-commit run passed all ten applicable hooks, including **587 passed,
8 skipped** in pytest, Ruff, strict mypy (89 source files), and all nine import contracts.
The skips are optional FiftyOne integration tests. Basic Markdown structure, whitespace,
fences and local links passed for 29 changed/new documents and 31 local links; `git diff
--check` passed. Parent review inspected the complete feature source/test diff and new
cache/model/relay modules against the release baseline.

The final Spec Kit convergence pass checked 37 requirements, acceptance scenarios and edge
cases, seven design decisions and five constitution principles. It found no missing, partial,
contradictory or unrequested implementation work. No tasks were appended; the task file was
byte-for-byte unchanged during that pass. T029–T034 record the earlier gaps and fixes.

## Limits and environment evidence

This is smoke-scale integration evidence, not a model-quality or performance benchmark.
Multi-process cache ownership is exercised with real processes; multi-GPU distributed training
was not run. Remote agent scheduling was not used; clone configuration behavior was verified at
the launch boundary and against downloaded real configuration. FiftyOne live publication is
outside this feature's live run; its adapter regressions remain in the suite.

The shared stand's browser cookie did not authenticate image-file requests. The UI inspection
harness supplied an in-memory bearer header only to that stand's files endpoint; no credentials
were saved and no infrastructure was changed. One historical-fixture harness hung while closing
an SDK task outside the application lifecycle; its owned process was stopped and the fixture
was recreated with explicit lifecycle calls. This was not counted as a successful command run.

Machine-specific task/model IDs, scripts, logs, screenshots and downloaded-table evidence are
retained with the global clearml-yolo-environment skill. Only resources created under this
verification's own tag are eligible for cleanup. Independent review and cleanup receipts are recorded below. Native orchestration tools expose no observed token-usage telemetry, so an
API-equivalent cost cannot be calculated.

## Independent review correction

The first fresh read-only gpt-5.6-sol/high review returned `fix-first` for FR-009:
remote native General replay included the previous trainer's effective project/name,
which conflicted with a clone's pipeline route and could reuse standalone output paths.
T033 records the finding. Four train/pipeline clone cases reproduced the failure before
the fix, including explicit current output requests. Replay now excludes prior derived
project/name/save_dir, retains current requested routing, and applies other native
parameter overrides. All 34 affected launch/train/pipeline tests passed after the fix.
The parent reran all ten pre-commit hooks with a frozen worktree: all passed, including
583 tests with eight optional skips. The first full rerun also passed its tests, but its
hook detected concurrent parent documentation edits; the clean rerun resolves that
bookkeeping failure. Documentation/link checks and the complete correction diff were
reviewed again. A fresh convergence pass found no further implementation gaps and left
tasks.md unchanged; the next independent review is recorded below.

The second independent review returned `fix-first` for a narrower current-input case:
the routing snapshot excluded a currently requested save_dir, silently dropping a
pipeline conflict only during remote execution. T034 adds save_dir to the pre-connect
snapshot when present. Inherited-only save_dir remains excluded; an explicit current
value, including null, reaches the existing pipeline rejection. Two remote regressions
failed before the fix while the matching local cases passed; all 38 affected tests
passed afterward. No other blocking finding was reported by either reviewer.

Final verification after both review corrections: all ten applicable pre-commit hooks
passed, including **587 tests passed, eight optional skips**, Ruff, strict mypy and
nine import contracts. Documentation/link checks passed again. The final convergence
pass found no remaining implementation gaps and left tasks.md byte-for-byte unchanged.
The complete correction diff has been inspected; the third fresh read-only review is recorded below.

## Final acceptance and cleanup

The third fresh read-only gpt-5.6-sol/high reviewer returned **ASTRA REVIEW / VERDICT: ship**
with no findings. It inspected the complete feature and new modules, independently passed
all 38 affected launch/train/pipeline tests, focused Ruff and the feature diff check,
confirmed unchanged external dependency pins, and inspected the full parent gate log.
Physical multi-GPU, live FiftyOne and remote-agent scheduling remain the limits stated above.
No code changed after that review; only completion markers and this receipt were updated.
Final documentation structure/link and whitespace checks passed after those updates.

Evidence was archived before the environment skill removed the task-owned test project and
scratch directory. The post-cleanup tag-scoped listing reported zero projects and zero tasks.
Unrelated shared services and historical tasks were not modified. No commits, pushes or issues
were created; the isolated implementation worktree remains available.

API-EQUIVALENT COST RECEIPT: unavailable for the parent, implementers and reviewers because
native tools exposed no observed token usage. Requested model/effort controls are recorded;
actual runtime model/effort are unobservable. No cost, repricing or savings estimate is claimed.

## Subsequent release authorization

After feature acceptance, the user authorized committing, pushing and making a release.
This supersedes the initial no-commit/no-push scope recorded above. The release follows
the repository semantic-version workflow, retains the approved dependency pins, and
includes fresh commit/release checks and distribution installation verification.
The dated release execution record is retained with the global environment evidence.
