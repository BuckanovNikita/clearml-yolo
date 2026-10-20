"""Resolve finalized annotation datasets without modifying their CSV or media paths."""

import hashlib
from pathlib import Path

from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.application.contracts import ClearMLDatasetRef, ResolvedGroundTruth


class ClearMLGroundTruthRepository:
    def resolve(self, reference: ClearMLDatasetRef) -> ResolvedGroundTruth:
        """Use SDK caching for root dataset.csv and retain exact source provenance."""
        from clearml import Dataset

        selector = (
            {"dataset_id": reference.dataset_id}
            if reference.dataset_id is not None
            else {"dataset_project": reference.project_name, "dataset_name": reference.name}
        )
        if reference.version is not None:
            selector["dataset_version"] = reference.version
        with trace_operation("clearml.dataset.resolve", context=selector):
            dataset = Dataset.get(**selector, only_completed=True, auto_create=False)
            if not dataset.is_final():
                raise ValueError("Ground-truth ClearML dataset must be finalized")
            files = set(dataset.list_files())
            if "dataset.csv" not in files:
                raise FileNotFoundError("Ground-truth ClearML dataset requires root dataset.csv")
            if files != {"dataset.csv"}:
                raise ValueError(
                    "Ground-truth ClearML dataset must contain only root dataset.csv; "
                    "store images and other files outside the dataset"
                )
            # Soft links can move the CSV's effective parent to an SDK archive cache,
            # changing existing source-relative image-path interpretation.
            directory = dataset.get_local_copy(
                files=["dataset.csv"], raise_on_error=True, use_soft_links=False
            )
            path = Path(directory) / "dataset.csv"
            if not path.is_file():
                raise FileNotFoundError(f"Downloaded ClearML dataset has no dataset.csv: {path}")
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            return ResolvedGroundTruth(
                path=path,
                dataset_id=dataset.id,
                project_name=dataset.project,
                name=dataset.name,
                version=dataset.version,
                csv_sha256=digest,
            )
