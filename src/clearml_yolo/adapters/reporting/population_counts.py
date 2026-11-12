"""Show checkpoint-owned dataset populations separately from evaluation metrics."""

from collections.abc import Mapping
from pathlib import Path

from openpyxl import load_workbook  # type: ignore[import-untyped]

from clearml_yolo.adapters.reporting.workbook_identity import deannotated_workbook
from clearml_yolo.adapters.storage.filesystem import write_path
from clearml_yolo.core.identity import ModelIdentity

DATASET_COUNTS_SHEET = "Dataset counts"


def annotate_population_counts(
    path: Path,
    populations: Mapping[str, tuple[ModelIdentity | None, dict[str, dict[str, int]] | None]],
) -> None:
    """Append original annotation counts before the final identity annotation.

    Recover the original workbook first: editing an identity/presentation envelope
    directly would invalidate its integrity check and lose machine readability.
    Unknown populations and absent standard splits are explicitly unavailable.
    """
    with deannotated_workbook(path) as source:
        workbook = load_workbook(source)
    try:
        if DATASET_COUNTS_SHEET in workbook.sheetnames:
            del workbook[DATASET_COUNTS_SHEET]
        sheet = workbook.create_sheet(DATASET_COUNTS_SHEET)
        sheet.append(["Role", "Model", "Training task ID", "Original split", "Class", "Annotation count"])
        for role, (identity, counts) in populations.items():
            prefix = [role, identity.model_name if identity else "NA", identity.training_task_id if identity else None]
            prefix[2] = prefix[2] or "NA"
            splits = dict.fromkeys(["train", "val", "test", *sorted(counts or {})])
            classes = sorted({label for values in (counts or {}).values() for label in values})
            for split in splits:
                values = None if counts is None else counts.get(split)
                if values is None:
                    sheet.append([*prefix, split, "NA", "NA"])
                elif classes:
                    for label in classes:
                        sheet.append([*prefix, split, label, values.get(label, 0)])
                else:
                    sheet.append([*prefix, split, "NA", 0])
        # Labels and IDs are lexical strings, including formula-like names.
        for row in sheet:
            for cell in row:
                if isinstance(cell.value, str):
                    cell.data_type = "s"
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        workbook.save(write_path(path))
    finally:
        workbook.close()
