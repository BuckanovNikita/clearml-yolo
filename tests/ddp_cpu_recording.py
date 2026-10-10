"""Local SDK boundary for real distributed training integration tests."""

import math
import os
from pathlib import Path
from typing import Any, ClassVar


class RecordingTask:
    """Record native callback publications without contacting ClearML."""

    current: ClassVar["RecordingTask | None"] = None

    def __init__(self, *, fail_callback: bool) -> None:
        self.id = "cpu-ddp-owner"
        self.parameters: dict[str, Any] = {}
        self.publications: list[dict[str, Any]] = []
        self.scalars: list[dict[str, Any]] = []
        self.output_models: list[dict[str, Any]] = []
        self.fail_callback = fail_callback
        self.callback_failed = False

    @classmethod
    def current_task(cls) -> "RecordingTask | None":
        return cls.current

    def _record(self, kind: str, **values: Any) -> dict[str, Any]:
        result = {"kind": kind, "pid": os.getpid(), **values}
        self.publications.append(result)
        return result

    def connect(
        self, values: dict[str, Any], name: str, ignore_remote_overrides: bool
    ) -> dict[str, Any]:
        assert name == "General"
        assert ignore_remote_overrides
        self.parameters.update({f"General/{key}": value for key, value in values.items()})
        self._record("configuration")
        return values

    def get_parameters(self) -> dict[str, Any]:
        return self.parameters.copy()

    def get_logger(self) -> "RecordingTask":
        return self

    def report_scalar(self, title: str, series: str, value: float, iteration: int) -> None:
        if self.fail_callback and not self.callback_failed:
            self.callback_failed = True
            raise RuntimeError("Injected owner callback failure")
        assert math.isfinite(float(value)), (title, series, value)
        self.scalars.append(
            self._record(
                "scalar", title=title, series=series, value=float(value), iteration=iteration
            )
        )

    def report_single_value(self, name: str, value: float) -> None:
        assert math.isfinite(float(value)), (name, value)
        self._record("value", name=name, value=float(value))

    def report_image(self, **kwargs: Any) -> None:
        raise AssertionError(f"Unexpected image publication with plots=False: {kwargs}")

    def report_matplotlib_figure(self, **kwargs: Any) -> None:
        raise AssertionError(f"Unexpected plot publication with plots=False: {kwargs}")

    def update_output_model(self, model_path: str, model_name: str, auto_delete_file: bool) -> None:
        assert not auto_delete_file
        path = Path(model_path)
        self.output_models.append(
            self._record("model", path=str(path), name=model_name, bytes=path.stat().st_size)
        )


class CallbackModel:
    """Carry the production capture callbacks across a real serialization boundary."""

    def __init__(self) -> None:
        from ultralytics.utils.callbacks import base

        self.callbacks = {event: values.copy() for event, values in base.default_callbacks.items()}
        self.trainer: Any = None

    def add_callback(self, event: str, callback: Any) -> None:
        self.callbacks[event].append(callback)
