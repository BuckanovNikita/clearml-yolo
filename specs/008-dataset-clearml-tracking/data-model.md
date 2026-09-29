# Data model

## Dataset cache entry

Identity: CSV SHA-256 + format (`ndjson` or `flat`) + preparation version.
Paths: data.yaml, cleaned ground_truth.csv, local NDJSON/diagnostics, images and labels.
Completion: version/identity, split counts, required relative file inventory. Required files
must exist; every requested split must have at least one image. No image content/mtime checks.
States: absent -> locked staging -> atomic complete -> locked consumer -> reusable.
Failed staging is never complete; recover under the same lock. Corrupt complete entries fail
validation and rebuild safely. Cache root must not be nested in the invocation output.

## Invocation publication state

One task, owner PID, stage names, expected publications, uploaded canonical paths and CSV
content identities, internal aliases, native best model identity and verification barrier.
Only owner mutates remote state. Failure at any barrier fails command and task.

## Model record

One native best model with source task/project associations, labels, framework, architecture,
tags, description, known lineage only, and checkpoint/version/input metadata. Exact available
fields are mapped in [model metadata](contracts/model-metadata.md). Server IDs/times remain owned
by ClearML. Model does not become production-ready automatically.

## Comparison source

Source kind (`local` or `clearml`), weights path, exact nonempty threshold map,
optional task/model IDs and URLs. Local references require existing weights and thresholds.
New task thresholds are validation CSV rows `(class_name, confidence)` with finite values
in [0,1], unique nonempty class names, and full float round-trip precision.

## Readable publications

One CSV per distinct table bytes; canonical names retained for cross-task readers.
Evaluation workbook per split; comparison workbook per paired split; final reports only.
Configurations are nonempty, sanitized, consumed and never duplicated as artifacts.
