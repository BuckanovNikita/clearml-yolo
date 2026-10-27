"""Locked atomic storage for validated local batch estimation evidence."""

import os
import tempfile
from pathlib import Path

from filelock import FileLock, SoftFileLock
from pydantic import ValidationError

from clearml_yolo.adapters.storage.filesystem import cy_home, write_path
from clearml_yolo.core.batch_estimation import EstimateCase, EstimateCatalogue, estimate_key


class FileBatchEstimateStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = write_path(path or cy_home() / ".config/clearml-yolo/batch-estimates.json")

    def read(self) -> EstimateCatalogue:
        """Atomic replacement permits lock-free readers; corruption is never a miss."""
        try:
            raw = self.path.read_bytes()
        except FileNotFoundError:
            return EstimateCatalogue()
        try:
            return EstimateCatalogue.model_validate_json(raw)
        except ValidationError as error:
            raise ValueError(
                f"Invalid batch estimate catalogue {self.path}; preserve or repair this file "
                "before retrying. Existing evidence has not been overwritten."
            ) from error

    def save(self, case: EstimateCase) -> None:
        # Revalidate copied records at the persistence boundary: model_copy is
        # intentionally not Pydantic validation and must not bypass saved evidence.
        case = EstimateCase.model_validate_json(case.model_dump_json())
        path = write_path(self.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if FileLock is SoftFileLock:
            raise RuntimeError("Batch estimates require native file locks")
        lock = FileLock(
            write_path(path.with_suffix(".json.lock")),
            timeout=30,
            fallback_to_soft=False,
            preserve_lock_file=True,
        )
        with lock:
            key = estimate_key(case.profile, case.workload, case.settings)
            cases = tuple(
                prior
                for prior in self.read().cases
                if estimate_key(prior.profile, prior.workload, prior.settings) != key
            )
            catalogue = EstimateCatalogue(cases=(*cases, case))
            self._replace(catalogue.model_dump_json(indent=2) + "\n")

    def _replace(self, payload: str) -> None:
        descriptor, name = tempfile.mkstemp(
            prefix=".batch-estimates-", suffix=".tmp", dir=self.path.parent
        )
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(write_path(self.path))
            directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)
