# Stable parameter and cache contract

## Publication and replay

The native General projection omits `device`, `project`, `name`, `save_dir`,
`exist_ok` and CSV-owned generated `data`. Other native arguments remain unchanged.
`parameters.py` exposes `NATIVE_EXECUTION_KEYS` and
`project_native_parameters(values: Mapping[str, Any]) -> dict[str, Any]`.
The projection is detached. The existing session boundary exposes
`prepare_native_parameters` to combine projection with credential sanitization,
including for the native callback bridge.
The shared CLI's canonical run retains full native input groups, including `ultralytics`; General
scientific overrides remain authoritative on remote training replay. Excluded values
come from full replay inputs, with existing current output routing protections.
New canonical run snapshots use JSON text, accepted by the SDK's existing replay
parser. Historical HOCON remains replayable but is preserved verbatim by the cache
helper; no custom HOCON interpreter or new parser dependency is introduced.
Embedding callers must explicitly supply or record their full resolved inputs within
the invocation; direct use-case calls do not construct complete replay snapshots.
For remote YOLO training with absent `run` or a historical run without `ultralytics`,
restore execution settings from legacy General before storing a full new snapshot.
A present native group, including an empty mapping, retains authority. Current output
routing remains protected. JSON publication preserves Unicode characters literally
for compatibility with the SDK's replay parser.

Filtering newly connected values does not delete parameters inherited from historical
templates. Such clones can retain old General execution keys; the canonical replay
path and cache helper still handle them. No parameter-history cleanup is performed.

## Prepared dataset identity

`PreparedDataset.cache_identity: str | None = None` exposes the existing cache key
without recomputing/changing its algorithm. Training records
`run.prepared_dataset = {cache_identity, root}` when identity exists, where root is
the parent directory of prepared.data. Cache projection retains cache_identity and
normalizes only path values under this root to identity plus relative path. It never
normalizes unrelated source/checkpoint paths by basename. Source input references,
dataset format, class mappings and split definitions remain significant.

## Controller API

`clearml_yolo.adapters.clearml.cache.normalize_task_hash(representation: dict[str, Any])`
returns a detached dictionary compatible with `ClearmlJob.register_hashing_callback`.
No registration, SDK import, filesystem or network operation occurs at import/call.
Normalize only canonical `-m clearml_yolo.entrypoints.<execution-command>` scripts.
Preserve SDK-supplied script/container fields, unknown representation members and
unknown configs. The helper cannot restore identity fields the SDK excludes before
invoking its callback.
Recognized run/dataset documents are parsed conservatively; malformed or unsupported
documents retain their original representation. Normalized known documents serialize
deterministically. Inject an explicit normalization-policy version.

Native device values normalize only in native groups, General and known inference
settings: accepted explicit CUDA ordinals become type/count, CPU/MPS remain distinct,
unresolved or invalid selections remain distinct. Selector grammar depends on the
consumer: detector/export settings must not inherit YOLO's permissive spelling
rules, and inference with an unknown checkpoint backend uses only a common safe
subset. Native routing keys, run output
destinations/cache roots, ClearML task/project/tags/output_uri and recorded display
names do not contribute. Preserve source model selection fields, class names,
unknown settings and scientific normalization. Exclude only explicitly enumerated
output-only provenance. Do not remove arbitrary `name`, `path` or `*_result` fields.

The routing exclusions apply only where those fields are output-only. Retain
`clearml.project_name` when comparison model references use it as their fallback
input lookup project, including a pipeline's default baseline. Retain pipeline
`run_dir` and `run_id` when a skipped stage may consume existing files. Controllers
should pin concrete source task IDs and immutable inputs before caching; the pure
helper cannot resolve changes behind latest-task/tag selectors or mutable paths.

Existing callbacks must be composed explicitly by the controller. No new runner is
provided. A cache hit reuses old remote outputs and has no new local output effect.
Pass `run` configuration overrides as JSON text (`json.dumps(..., ensure_ascii=False)`);
the SDK serializes dictionary overrides as JSON with ASCII escaping, which its replay
parser does not decode reliably for Unicode. Marker-shaped invalid
device inputs and caller-supplied generated-path tokens retain their entire original
representation instead of being allowed to collide with valid normalized inputs.
Active JSON Unicode, slash, backspace and formfeed escapes also refuse projection
because their SDK replay meaning differs from standard JSON. Literal escaped
backslashes remain supported.
