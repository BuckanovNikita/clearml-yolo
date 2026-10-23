# Cross-package and startup interfaces

Queue imports CY process supervision and lifecycle adapters directly at documented module paths. CY execution_lifecycle owns inherited descriptor handling, training-complete acknowledgement and task-result reporting; queue owns reservations and process cleanup. CY process_tree/supervision remain shared Linux process effects, never importing queue.

Queue Hydra integration composes pipeline or train using CY registered roots, validation and sweep helpers, writes an execution snapshot and launches the matching existing entrypoint. Stored config names, lock namespaces and record formats remain compatible. Changed package identity requires resubmission, not implicit migration or execution of stale pending snapshots.

Agent replay fetch occurs once before mandatory-input validation/backend selection. A detached snapshot is applied to a copied launch configuration. The selected runtime initializes before invocation joins that same remote task. Canonical settings retain selected paths/nulls; remote General scientific overrides apply only to YOLO training. Agent CUDA visibility is not modified by a scheduler.

Asset integration accepts ModelConfig and returns an execution ModelConfig plus detached provenance. It is called only for actual execution, after canonical publication, with no new fields required in user config. Explicit paths fail if missing. Outer asset resolution owns network/filesystem effects; backend loading uses native supported file interfaces without SDK monkeypatching or global cache mutation.

Resolved asset provenance is published in the separate `model_assets` Configuration Object, outside canonical `run` inputs and their cache projection.
