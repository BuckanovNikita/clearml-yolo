# Quickstart: Validate the Identity Footer

## Prerequisites

`external/report-generator` contains the feature commit; `uv sync --frozen --dev` is done.

## Automated checks

```bash
(cd external/report-generator && uv run pytest tests/test_v2_workbook.py)   # prepend + bottom modes
uv run --frozen --no-sync pytest tests/test_workbook_identity.py tests/test_identity_flows.py \
  tests/test_evaluation_identity.py tests/test_report.py tests/test_shared_extraction_compatibility.py
uv run --frozen --no-sync pytest --testmon-noselect
prek run --all-files
```

Expected outcomes:
- Every worksheet has its original header in row 1 and unchanged cells.
- The footer starts after the last used row or drawing anchor, plus one empty row.
- Hyperlinks resolve to the injected URLs. With no links, the plain lines appear.
- The page footer is present and no print titles are added.
- Original recovery and edit rejection behave as before.

## Live check (stand)

Use the `clearml-yolo-environment` and `running-end-to-end-tests` skills. Run a metrics
evaluation and a compare/report run with tagged project overrides. Open the uploaded
dashboard, evaluation, comparison and dev/business workbooks. Confirm that:

- the footers are below the data;
- `<Role>: <name>` opens the ClearML model page;
- `Training task: open in ClearML` opens the training task;
- no identifier is visible.

Clean up with the tagged cleanup.
