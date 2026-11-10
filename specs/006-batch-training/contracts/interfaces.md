# Interfaces

The current estimator and training-lookup interface is maintained in
[batch estimation](../../../docs/batch-estimation.md). Feature 012 supersedes this
feature's strict training-cache lookup and eight-image minimum: the editable YAML
table is authoritative, the workload uses fixed 150 classes, and the versioned search
supports integer batches below eight. Historical JSON replay and keys remain intact.

Independent cases run in separate processes pinned to their assigned GPUs. Candidate
and optimizer trials within a case remain sequential. Every trial and confirmation
uses one GPU; output counts do not launch distributed probes. Only the parent accepts
matching receipts after successful exit and owned cleanup. Unverifiable cleanup
quarantines that GPU for the invocation. Ordinary case failures leave peers running;
unsafe supervision stops the invocation. Cancellation cleans only owned processes.

Worker requests carry backend configuration, prepared dataset, output, optional
augmentation and world-size/rank settings. Workers never create ClearML tasks. Typed
results carry native evidence and scalar events for owner publication. Rank failure
terminates its cooperating owned rank group before any subsequent trial or queue
contraction; this does not apply fail-fast semantics to independent estimator cases.

Fresh configuration trees include ordinary YAML command bases and transitive defaults;
explicit distinct schema references retain validation without automatic matching.
