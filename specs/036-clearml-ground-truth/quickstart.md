# Acceptance scenarios

Compose each selector using cy --cfg job and the ordinary ground_truth override.
Create a task-owned finalized ClearML dataset containing only dataset.csv with
external absolute image references. Consume it by ID, project/name and explicit
version; compare bytes and downstream results with the same local CSV. Check the
local warning, owner provenance and absence of duplicate lookup in composed stages.
Exercise missing root CSV, invalid selector, lookup/download failure and optional
export ground truth. Queue snapshot and replay checks must not perform eager lookup.

Build a wheel and install it without project extras on Python 3.12.13 and 3.13.
Inspect metadata and run CLI/configuration/backend/export/TUI smoke checks. Run a
separate lowest-direct resolution and compatibility suite for each minor, recording
actual resolved versions and every floor adjustment. Retain normal lock provenance.
