# ADR-0300 · Track, replay and finalize one ClearML experiment per invocation

CY assigns one owner to the lifetime of an experiment. That owner identifies the task, freezes its inputs, collects results from every participating stage and decides whether it can confirm completion. This lets the pipeline share a checkpoint, calibration results and publication status across stages.

## Task and execution identity

Each experiment command initializes a task with `reuse_last_task_id=False`. Nested stages borrow it. Each sweep member starts its own task. Workers and distributed ranks leave task creation and uploads to the owner. On an Agent, the owner checks that the attached SDK task matches the task whose settings it read.

The requested name can already exist in the project. CY queries for collisions, tries readable adjective–noun suffixes within a bounded number of attempts, rechecks the published name and coordinates the suffix with the model name. It records requested and effective names in `run.display_names`. The frozen task identity continues to identify the output directory. The original rationale for the naming convention is undocumented.

For a local task, CY records its command module, relative working directory and an empty diff. A source installation also supplies a sanitized repository URL, branch and commit, which CY checks through a fresh SDK read. A wheel can supply the module without a checkout identity. An Agent retains its supplied script. The separate [launch directory check](0309-runtime-and-queue.md#workspace-run-directory-and-scratch) concerns the user's experiment inputs.

<details>
<summary>Sources and verification</summary>

- Share one ClearML task across experiment stages — [Owner and worker guard](../src/clearml_yolo/adapters/clearml/session.py) · [Ownership and failure cases](../tests/test_clearml_session.py) · [ClearML configuration](../docs/configuration/clearml.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/589dc4a563e8a767a3cf9b675df66820b0a3c83b)
- Resolve readable project-local task and model names — [Collision queries and recheck](../src/clearml_yolo/adapters/clearml/naming.py) · [Collision and retry cases](../tests/test_clearml_naming.py)
- Publish the package checkout as ClearML execution metadata — [Source lookup and readback](../src/clearml_yolo/adapters/clearml/script.py) · [Checkout metadata cases](../tests/test_clearml_script.py) · [Execution metadata](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/5d89443b8e1a8e63d21b3c318b2cab0242c4e418)

</details>

## Executable inputs, attachments and controller caching

The owner publishes the effective settings as sanitized JSON in `run`. A separate `run_overrides` view shows differences from packaged defaults and omits output routing. Sanitization removes recognized credential fields and sensitive URL content, including values traced through file interpolations. A private execution copy can retain values required locally. Remote failure status gives the error category and refers the operator to local diagnostics. Native programs control the bytes they emit into the [console journal](0309-runtime-and-queue.md#console-delivery-and-readable-telemetry).

An Agent reads one task snapshot, restores the canonical settings and validates them against the current workspace. Legacy tasks without `run` can fall back to composed settings. YOLO also reads eligible native `General` overrides and preserves an unspecified batch for local lookup. The reference designates `run` as the only replay input. In the implementation, ground truth conversion can consume a connected `dataset` file and report generation can consume a connected `report` file, even when the original path is absent. Training disables remote replacement of its prepared dataset. With neither a usable original nor a replacement, the operation fails. Offline Agent scenarios exercise this mapping. Operational replay requires an actual Agent. [SIP-354](https://linear.app/sip-ds-team/issue/SIP-354)

A controller can register `normalize_task_hash` before cache lookup. For a recognized CY command, it removes `run_overrides`, normalizes known routes, device selectors and prepared-dataset paths, and preserves paths or projects that select inputs. It leaves unknown scripts and ambiguous input distinctions intact. The reference also designates `run` as the sole cache input. The callback retains other hash material, including `model_assets` when present, and can normalize `General` and `dataset` fields. This projection affects cache lookup only. [SIP-350](https://linear.app/sip-ds-team/issue/SIP-350)

<details>
<summary>Sources and verification</summary>

- Publish executable settings and a redacted differences view — [Configuration publication and file attachment](../src/clearml_yolo/adapters/clearml/session.py) · [Structured redaction](../src/clearml_yolo/core/redaction.py) · [Configuration publication cases](../tests/test_configuration_publication.py) · [Configuration objects](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/fd395d34bff7f3128047e5d0c302f2c3f0720b78)
- Sanitize structured values at publication boundaries — [Contract](../DOCS.md#clearml-publication)
- Restore executable settings from the Agent task snapshot — [Direct command integration](../src/clearml_yolo/entrypoints/hydra/common.py) · [Agent scenarios](../tests/test_agent_replay.py) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/2e4b5f2fa3c3e9dc90920af75fe3edb8e346bcd0)
- Resolve attached configuration files at the point of use — [Ground-truth consumer](../src/clearml_yolo/application/use_cases/ground_truth.py) · [Report consumer](../src/clearml_yolo/application/use_cases/report.py) · [Training policy](../src/clearml_yolo/application/use_cases/train.py) · [Attachment replay scenarios](../tests/test_config_upload_commands.py) · [Configuration source decision](https://github.com/BuckanovNikita/clearml-yolo/commit/6aefaa354e2f20ef05e3d62b7901399548045133)
- Project ClearML step identity before controller cache lookup — [Controller projection and invariants](../src/clearml_yolo/adapters/clearml/cache.py) · [Cache identity tests](../tests/test_clearml_cache.py)

</details>

## Result rows and experiment views

CY registers effective ground truth once as `gt_csv` and declares the stages that will contribute predictions. Each producer adds rows and identities for its result context and split. The owner persists their index and assembles `predicts_csv` after the last declared producer finishes. A ground-truth-only run produces no prediction artifact. Rows outside the scored splits can carry their own status. Conflicting ground truth or a late contribution fails.

ClearML tables, scalars and plots draw on these same results. Confusion plots show counts and normalized views. Test precision–recall curves use the recorded observations. Comparison headline verdicts use eligible hypotheses, and unavailable inputs can suppress a scalar. Readable model identities distinguish plot series. The candidate's comparison evidence can appear alongside its evaluation, while the artifacts retain the baseline evidence. SDK-call tests establish which values CY submits. Rendering them interactively requires the ClearML UI.

<details>
<summary>Sources and verification</summary>

- Publish one set of result rows per invocation — [Result assembly](../src/clearml_yolo/adapters/clearml/results.py) · [Multi-producer and identity cases](../tests/test_clearml_results.py) · [Artifact and row formats](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/fd395d34bff7f3128047e5d0c302f2c3f0720b78)
- Publish scientific results as ClearML plots, tables and scalars — [ClearML reporting adapter](../src/clearml_yolo/adapters/clearml/report.py) · [Table and headline cases](../tests/test_clearml_report.py) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/a6a78e895cb84a2fc960d4b3f91e8327f2ea3e89)

</details>

## Artifact delivery and checkpoint-bound metadata

Stages declare required artifacts or register them during upload. The owner checks local paths, requests synchronous delivery, requires an affirmative SDK response, checks outstanding manifest entries and flushes the task. Identical table bytes may satisfy aliases. Different contents submitted under the same name receive disambiguating suffixes. The technical reference requires remote readback of every upload. The ordinary artifact path checks acknowledgement and flush without fetching the artifact. [SIP-348](https://linear.app/sip-ds-team/issue/SIP-348)

A published checkpoint has an additional verification path. CY enriches YOLO's native best-model registration or publishes another detector's best checkpoint with its descriptor. It verifies the owner task, model identity, remote weights URL, tags and metadata, then downloads the checkpoint and checks its SHA-256. A final verifier runs before the task closes. Conflicting registration, missing metadata or changed bytes fails publication. A live storage round trip requires backend evidence.

CY attaches thresholds only after validation-split calibration and only to a model verified in the same invocation. Prediction provenance must carry the matching checkpoint digest. CY validates the classes and finite thresholds, writes their mapping, per-class values, split and digest, and reads the metadata through a fresh model handle. Standalone metrics can publish threshold artifacts while leaving models owned by other experiments untouched.

<details>
<summary>Sources and verification</summary>

- Track required ClearML artifacts through finalization — [Upload and manifest implementation](../src/clearml_yolo/adapters/clearml/session.py) · [Rejected, missing and aliased artifacts](../tests/test_clearml_session.py) · [Publication reference](../DOCS.md#clearml-publication) · [Artifact catalog](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/fd395d34bff7f3128047e5d0c302f2c3f0720b78)
- Bind a ClearML Output Model to the best checkpoint — [YOLO verification](../src/clearml_yolo/adapters/clearml/native.py) · [Detector publication](../src/clearml_yolo/adapters/clearml/detectors.py) · [YOLO boundary tests](../tests/test_clearml_native.py) · [Detector boundary tests](../tests/test_detector_publication.py) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/589dc4a563e8a767a3cf9b675df66820b0a3c83b)
- Attach calibrated thresholds only to the matching owned model — [Pipeline calibration call](../src/clearml_yolo/application/use_cases/pipeline.py)

</details>

## Final status and uncertain closure

The owner runs finalizers, checks required delivery and model verifiers, flushes telemetry, closes the task and sets terminal status. An unfinished upload or rejected acknowledgement blocks normal success. An eligible pipeline that already produced a usable checkpoint can record incomplete downstream publication in its local outcome and attempt completion with warnings. If CY cannot confirm closure, it refuses to start another owner in the same process.

The reference assigns each SDK finalization step a separate 600-second timeout. The successful implementation path wraps the entire finalization sequence in one main-thread alarm, so those steps share the allowance. Recovery and cleanup blocks can have fresh alarms. [SIP-349](https://linear.app/sip-ds-team/issue/SIP-349)

<details>
<summary>Sources and verification</summary>

- Bound ClearML finalization and quarantine uncertain owners — [Owner and alarm scope](../src/clearml_yolo/adapters/clearml/session.py) · [Deadline mechanism](../src/clearml_yolo/adapters/clearml/deadline.py) · [Owner lifecycle tests](../tests/test_clearml_session.py) · [Trained pipeline failure cases](../tests/test_training_success_finalization.py) · [Technical contract](../DOCS.md#clearml-publication) · [User contract](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/d247a2e6f6d179a255ea6caaa5017ac477be8f4c)

</details>
