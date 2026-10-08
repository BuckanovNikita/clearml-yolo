# Data model

Retain current serialized fields for model identity, evaluation payloads, manifests, publication requests/receipts and result CSVs. Move types to core/application contracts. Separate ComputedEvaluation scientific data from EvaluationArtifacts paths/dashboard frames. Validation findings identify stage/schema, source row, column and reason; raw rows retain original IDs and ordering. Native/SDK objects remain opaque only inside adapter implementations.
