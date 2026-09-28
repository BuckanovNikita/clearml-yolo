# Research: Native configuration composition

## Installed defaults as the source of truth

**Decision**: Locate native default YAML through package metadata, without importing
Ultralytics/Torch during composition or initialization.

**Rationale**: Existing instructions require responsive configuration-only operations and
current installed defaults. The upstream YAML supplies comments, ordering and full key coverage.

**Alternatives considered**: A vendored copy can drift; importing runtime defaults loads model dependencies.

## Comment-preserving serialization

**Decision**: Declare a comment-aware YAML library directly and update values over the original
upstream template; render irrelevant entries as commented YAML while preserving upstream prose.

**Rationale**: Plain configuration serialization loses native comments. ClearML sanitization
must preserve these comments while removing secrets from values and credential-bearing text.

**Alternatives considered**: Appending a comment-only template duplicates parameter entries;
plain safe-dump cannot satisfy the original-comment requirement.

## Hydra groups and prediction inheritance

**Decision**: Use native root-key group files. Compose full shared defaults and expose prediction
keys through inherited values, with sparse explicit prediction values taking priority.

**Rationale**: This allows unchanged pasted native YAML and ordinary `ultralytics_predict.batch=8`
overrides, while avoiding an independent prediction default set overriding shared settings.

**Alternatives considered**: Nested stage settings conflict with the approved user interface;
raw `cfg` overlays are explicitly removed. Copying full prediction defaults breaks inheritance.

## Stage applicability and replay

**Decision**: Classify native keys explicitly against execution paths, including training's
internal validation. Persist image manifests currently used for prediction and export actual
model/mode/source/routing values for each split or comparison role.

**Rationale**: YAML section headings do not completely express runtime applicability; temporary
manifests would make exported source values unusable after execution.

**Alternatives considered**: Forwarding all native keys hides ineffective parameters; exporting
wrapper configuration requires users to translate it before native replay.

## Verification authorization

**Decision**: Run lightweight focused tests/static checks now; defer native training, GPU,
live ClearML and full heavy integration until explicit user instruction.

**Rationale**: The user restricted heavy tests after approving the implementation plan.
No mocked check can establish the deferred real-run outcomes.

**Update (2026-09-28)**: The user explicitly authorized heavy tests. Native CPU/GPU execution,
ClearML round trips and direct replay subsequently passed; see the dated verification evidence.
