# Native evaluation contract

One evaluation per task/split; native type detection and method digital_metrics. Stored
views include exactly the payload's images, including backgrounds. Counts/statuses use
source matches; canonical confusion tuples use existing claimed-GT rules. The receipt
field inventory names `evaluated_predictions`, the native prediction field containing
only active detections (status other than `filtered`), and `matched_ground_truth`, the
native GT field. `matched_predictions` retains the complete audit overlay including
filtered boxes, which have no native evaluated status. Native evaluation patches must
not count filtered predictions as unmatched FP. Native IDs refer to persisted labels.

Saved results support standard discovery/loading/report/confusion/patch APIs and native
rename/delete. Custom AP methods expose existing AP50/AP75/AP50_95; mAP means mean
AP50_95 over classes with GT. PR plots use only existing IoU .50 curves. mAR and restricted
subset AP are unavailable. Native fixed-threshold subset semantics apply; all aligned
arrays restore after exiting context. No rematching, monkeypatch, or synthetic sweep.

UI extension reuses native rendering, overrides exact counts/navigation/caches, and adds
an AP/PR companion panel. Installation is explicit, not a publisher side effect. Old
runs upgrade only on publication; missing reports remain unavailable. Errors retain
optional-publication warning behavior and cannot fail otherwise successful computation.
