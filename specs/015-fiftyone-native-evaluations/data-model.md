# Data model

EvaluationPayload keeps schema_version=1 and adds optional report with its own version=1.
EvaluationReport contains ordered classes, ConfusionMatrixPayload, PRCurve list, and
class-keyed AP50/AP75/AP50_95 values with unavailable AP represented by null.
PublicationReceipt adds evaluation_keys: dict[split, native evaluation key], default {}.
Its field inventory includes evaluated_predictions, the active native prediction
Detections field excluding filtered boxes. matched_predictions preserves the complete
audit overlay, while matched_ground_truth supplies native GT detections.
Results persist the source payload and native label-ID mappings. The exact public shape
is defined by the typed models; FiftyOne objects never cross the neutral interface.
Existing payloads without report remain valid and expose fixed-threshold results only.
