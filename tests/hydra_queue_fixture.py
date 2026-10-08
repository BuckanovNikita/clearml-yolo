"""Importable child-process fixture for queue launcher integration tests."""

import json
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, override

from hydra.core.utils import JobReturn
from hydra.experimental.callback import Callback
from omegaconf import DictConfig, OmegaConf


def _execute_fixture(
    _name: str,
    config: DictConfig,
    function: Callable[..., None],
) -> None:
    values = OmegaConf.to_container(config, resolve=True, throw_on_missing=True)
    if not isinstance(values, dict):
        raise TypeError("Fixture configuration must be a mapping")
    function(**{str(key): value for key, value in values.items()})


# ``python -m clearml_yolo.entrypoints.hydra.worker`` binds execute_owned before importing the
# payload function. Patch that private worker boundary only inside the test child.
sys.modules["__main__"].__dict__["execute_owned"] = _execute_fixture


class RecordingCallback(Callback):
    """Record the real Hydra run_job callback context in the job's own file."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def _write(self, event: str, *, status: str | None = None) -> None:
        records = [] if not self.path.exists() else json.loads(self.path.read_text())
        records.append(
            {
                "event": event,
                "pid": os.getpid(),
                "cwd": str(Path.cwd()),
                "marker": os.environ.get("HYDRA_QUEUE_MARKER"),
                "status": status,
            }
        )
        self.path.write_text(json.dumps(records), encoding="utf-8")

    @override
    def on_job_start(self, config: DictConfig, **_kwargs: Any) -> None:
        self._write("start")

    @override
    def on_job_end(
        self, config: DictConfig, job_return: JobReturn, **_kwargs: Any
    ) -> None:
        self._write("end", status=job_return.status.name)


def record_job(
    ultralytics_predict: dict[str, object],
    receipt: str,
    value: str,
    delay: float,
    fail: bool,
) -> None:
    """Record fresh-process identity and overlap timing without touching services."""
    if ultralytics_predict.get("device") != "cpu":
        raise ValueError("The launcher fixture must remain CPU-only")
    started = time.monotonic()
    path = Path(receipt)
    path.write_text(
        json.dumps(
            {
                "value": value,
                "pid": os.getpid(),
                "cwd": str(Path.cwd()),
                "marker": os.environ.get("HYDRA_QUEUE_MARKER"),
                "started": started,
                "finished": None,
            }
        ),
        encoding="utf-8",
    )
    time.sleep(delay)
    record = json.loads(path.read_text(encoding="utf-8"))
    record["finished"] = time.monotonic()
    path.write_text(json.dumps(record), encoding="utf-8")
    if fail:
        raise RuntimeError(f"fixture failure: {value}")
