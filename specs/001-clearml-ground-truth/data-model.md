# Source records

ClearMLDatasetRef is a strict project-owned validated record with optional dataset_id,
project_name, name and version strings. Exactly ID or project/name is required;
version applies only to project/name. Whitespace-only values and extra fields fail.
GroundTruthInput accepts a local str/Path, dataset-reference mapping/model or an
internal ResolvedGroundTruth record. The resolved record contains a Path and optional
remote dataset metadata (ID/project/name/version/digest). It is passed between nested
stages; replacing its path after training preserves its original provenance.
