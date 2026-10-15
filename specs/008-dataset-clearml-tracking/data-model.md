# Data model

## Dataset cache entry

Identity: CSV SHA-256 + ordered resolved image references + format (`ndjson` or `flat`)
+ preparation version 2. Source-directory moves reuse only when the resolved references
remain identical; old version entries are preserved.
Paths: data.yaml, cleaned ground_truth.csv, local NDJSON/diagnostics, images and labels.
Completion: version/identity, split counts, required relative file inventory. Required files
must exist; every requested split must have at least one image. No image content/mtime checks.
States: absent -> locked staging -> atomic complete -> locked consumer -> reusable.
Failed staging is never complete. Builders may remove only their own unpublished staging;
peer or abandoned staging remains untouched. Existing incomplete/corrupt entries fail
validation and are preserved with an actionable error. Repair or removal requires deliberate
maintenance while the cache is idle; consumers never rebuild an existing invalid entry.
Entry locks are native process locks retained through consumption; unsupported native locks
or acquisition failures fail without a soft-lock fallback. Cache root must not be nested in
the invocation output. These current rules supersede former automatic recovery/rebuild
expectations; see [filesystem ownership](../../docs/filesystem-policy.md#dataset-cache-and-temporary-ownership).

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
