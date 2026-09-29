# Data Model: FiftyOne Integration

- **EvaluationPayload**: `schema_version=1`, split, image names, thresholds, evaluated ground truth, evaluated predictions, matches.
- **EvaluatedBox**: source index, image name, label, `(x1,y1,x2,y2)`, optional confidence, status.
- **EvaluationMatch**: nullable GT/pred indices and labels, optional confidence/IoU, status.
- **DatasetIdentity**: prefix, adapter schema, effective-GT SHA, resolved path map, optional original-GT SHA provenance.
- **PublicationReceipt**: task ID, dataset identity, separate dataset/run complete flags, payload paths, timestamp.

Raw predictions are distinct from run-specific evaluated collections. Reuse validates every resolved path. Only the current task's incomplete namespace may be recovered under the dataset lock.
