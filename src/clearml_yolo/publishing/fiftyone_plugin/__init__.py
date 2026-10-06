"""Explicitly installed FiftyOne Python plugin entrypoint."""

from typing import Any


def register(plugin: Any) -> None:
    """Register project panels at FiftyOne's untyped plugin boundary."""
    from clearml_yolo.publishing.fiftyone_panel import (
        EvaluationReportsPanel,
        NativeEvaluationPanel,
    )

    plugin.register(NativeEvaluationPanel)
    plugin.register(EvaluationReportsPanel)
