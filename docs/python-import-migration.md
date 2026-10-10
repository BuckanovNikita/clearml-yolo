# Python import and configuration migration

The clean architecture release moves Python modules into four packages and removes
the former paths. CLI command names, ordinary Hydra overrides, CSV contracts, output
names, thresholds, source identities and ClearML/FiftyOne publication behavior remain
the maintained external contracts. Saved Python imports and dotted `_target_` strings
require a deliberate cutover; there are no legacy module aliases.

Use the [complete module migration map](../specs/021-clean-architecture/migration-map.json)
for former modules and the [current contract index](current-contracts.md) for behavior.
The table below also identifies interfaces extracted beyond a mechanical move.

| Former import or responsibility | Current owner |
|---|---|
| `clearml_yolo.tasks.<stage>` | `clearml_yolo.application.use_cases.<stage>`; explicit `deps` required |
| `clearml_yolo.apps.<stage>` | `clearml_yolo.entrypoints.<stage>` |
| `clearml_yolo.configs`, `config_tree`, `apps.config_resolution` | `clearml_yolo.entrypoints.hydra.configs`, `config_tree`, `config_resolution` |
| `comparison.scoring.EvaluationConfig`, `ClassCounts`, `SplitOutcome`, `EvaluatedSplit` | `clearml_yolo.core.evaluation.models` |
| `comparison.scoring.evaluate_split` | `clearml_yolo.application.evaluation.evaluate_split`; composes computation and rendering through `deps` |
| Fixed-score matching, calibration and PR/AP computation | `clearml_yolo.adapters.evaluation.scoring` and `pr_curves` |
| Dashboard/PNG generation and metric summaries | `clearml_yolo.adapters.reporting.evaluation` |
| Pure class vocabulary, split membership and confidence threshold checks | `clearml_yolo.core.evaluation.policy` |
| `comparison.assemble`, `comparison.significance` | `clearml_yolo.core.comparison.assemble`, `significance` |
| `result_schema`, `result_export`, `comparison.evaluation_payload` | `clearml_yolo.core.evaluation.schema`, `result_rows`, `payload` |
| Workflow request/result/configuration records | `clearml_yolo.application.contracts` |
| `model_identity` data and filesystem persistence | `clearml_yolo.core.identity` and `clearml_yolo.adapters.storage.identity` |
| Pure secret redaction and caught-error logging | `clearml_yolo.core.redaction` and `clearml_yolo.adapters.observability.diagnostics` |
| `clearml_*` integrations | `clearml_yolo.adapters.clearml` modules named in the migration map |
| `publishing.models` and FiftyOne integration | `clearml_yolo.core.publication` and `clearml_yolo.adapters.fiftyone` |
| Filesystem/dataset/cache/run operations | `clearml_yolo.adapters.storage` modules named in the migration map |
| GPU visibility probe and stateless availability wait | `clearml_yolo.adapters.runtime.gpu_resources`, `gpu_probe`, `gpu_wait`; former queue/runtime modules removed |
| Native training, DDP and mixed integration lifecycle | `clearml_yolo.adapters.integrations` |

Import project-owned records from their defining modules. Package initializers remain
inert: importing `clearml_yolo`, `core`, `application` or an adapter package does not
initialize storage, construct services or change the caller's logging configuration.
Composition belongs to [entrypoints.composition](../src/clearml_yolo/entrypoints/composition.py),
with [typed ports](../src/clearml_yolo/application/ports.py) defining workflow capabilities.
Dependency bundles are supplied per invocation; workflows do not discover them through
a cache, service locator or global setter.

Opt-in operation diagnostics live in
[`adapters.observability.tracing`](../src/clearml_yolo/adapters/observability/tracing.py).
Application workflows request them through `ExecutionResources.trace_operation` in
`WorkflowDependencies.resources`; an alternative dependency implementation should
provide a context manager with the same outcome-preserving behavior, including a
no-op implementation when tracing is not needed. Evaluation and FiftyOne adapters
may import observability directly; scientific core code remains independent of it.
Caller logging sinks are preserved. See [diagnostics](diagnostics.md) for TRACE setup,
watchdog output and scheduling limits.

## Regenerate saved configuration

Back up the entire editable configuration tree before replacing generated files:

```bash
cp -a cy-config cy-config.backup
cy-init-config cy-config --force
```

Choose a backup destination that does not already exist. `--force` replaces generated
examples, so carry custom paths, task identity, tags, model settings and other overrides
from the backup into the new files. Preserve the new `defaults` and Python targets.
A fresh directory is another way to compare regenerated examples before replacing files.
Do not copy obsolete `_target_` strings back into the new tree. Workflow dependencies
are composed by the invocation entrypoint and are not a user YAML setting.

Update handwritten dotted targets in notebooks, scripts, custom Hydra groups, callbacks
and plugin integrations using the migration map. Repository-managed entrypoints,
GPU probe, DDP callbacks and FiftyOne extension targets follow the new locations.
Remove saved overrides targeting `hydra_plugins.cy_queue`; local multiruns now use
Hydra's standard sequential BasicLauncher. Queue, queued worker and GPU reservation
runtime imports are removed, with no compatibility aliases. Historical ClearML files are retained as evidence; this release does
not rewrite remote artifacts or infer old training provenance.

Comparison caches now identify checkpoints by content and exclude the reuse-policy
flag from their keys. The first comparison after upgrading regenerates predictions
under the new keys. Subsequent runs retain cache hits when ClearML refreshes checkpoint
timestamps, and cached CSV parsing preserves exact confidence values at frozen thresholds.

## Explicit programmatic dependencies

A full metrics workflow still requires a ClearML invocation owner. Select initialization
at the outer boundary and pass the dependency bundle explicitly:

```python
from pathlib import Path

from clearml_yolo.application.contracts import MetricsResult


def run_metrics() -> MetricsResult:
    from clearml_yolo.adapters.storage.filesystem import initialize_filesystem

    initialize_filesystem()
    from clearml_yolo.adapters.clearml.session import invocation
    from clearml_yolo.application.contracts import ClearMLConfig
    from clearml_yolo.application.use_cases.metrics import compute_metrics
    from clearml_yolo.core.evaluation.models import EvaluationConfig
    from clearml_yolo.core.publication import FiftyOneConfig
    from clearml_yolo.entrypoints.composition import build_dependencies

    tracking = ClearMLConfig(
        project_name="detection", task_name="metrics", tags=["evaluation"]
    )
    deps = build_dependencies()
    with invocation(tracking, "metrics"):
        return compute_metrics(
            predictions=Path("predictions.csv"),
            ground_truth=Path("ground_truth.csv"),
            output_dir=Path("metrics"),
            clearml=tracking,
            evaluation=EvaluationConfig(),
            splits=["test"],
            fiftyone=FiftyOneConfig(enabled=False),
            model_label="local detector",
            deps=deps,
        )
```

Inputs must contain the validation population needed for calibration; requested test
metrics use those frozen thresholds. Keep the existing checkpoint/prediction provenance
sidecars with their data. Tests or an embedding application can provide alternative
implementations of the typed ports directly without mutating shared service state.

For evaluation composition, `compute_evaluation` returns `ComputedEvaluation` containing
project-owned metric/match values, payloads, confusion counts, PR curves and result rows.
`render_evaluation` produces `EvaluationArtifacts`; `EvaluatedSplit.from_parts` joins
them for publication. The computation adapter keeps public `digital-metrics` matching,
AP integration and confidence ordering authoritative, preserving exact thresholds,
precision and tie behavior. Only reporting writes workbooks and plots. Core comparison
functions accept observations/diagnostics explicitly without owning logging or progress.

## Stage validation

[Core Pandera schemas](../src/clearml_yolo/core/validation/schemas.py) validate scientific
DataFrames without SDK imports or filesystem operations. NumPy, pandas, SciPy, Pydantic
and Pandera are permitted scientific core dependencies. Validation returns a copy and
does not coerce, drop or renumber source rows; lexical CSV conversion and compatibility
diagnostics belong to storage adapters.

Raw prediction geometry remains source evidence, including malformed or collapsed boxes.
Evaluation preparation warns and drops invalid prediction geometry before preprocessing,
matching and AP; an all-invalid population is scored as empty. Prepared evaluation boxes
must have positive geometry. Publication retains finite ordered zero-area boxes created
by native clipping. Ground-truth background rows retain empty boxes and their image
membership. Stable source IDs and JSON relationships continue to bind original source
rows to prepared match indices. Schema failures are fatal at their applicable stage and
do not silently repair source populations.
