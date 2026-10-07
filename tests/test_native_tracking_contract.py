"""Installed native callbacks own epoch telemetry and final model publication."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import matplotlib.pyplot as plt
import pytest

from clearml_yolo.native_runtime import native_runtime


class RecordingLogger:
    def __init__(self) -> None:
        self.scalars: list[tuple[str, str, float, int]] = []
        self.images: list[dict[str, Any]] = []
        self.figures: list[dict[str, Any]] = []
        self.single_values: dict[str, float] = {}

    def report_scalar(self, title: str, series: str, value: float, iteration: int) -> None:
        self.scalars.append((title, series, value, iteration))

    def report_image(self, **kwargs: Any) -> None:
        self.images.append(kwargs)

    def report_matplotlib_figure(self, **kwargs: Any) -> None:
        self.figures.append(kwargs)
        plt.close(kwargs["figure"])

    def report_single_value(self, title: str, value: float) -> None:
        self.single_values[title] = value


@pytest.mark.parametrize("plots", [False, True])
def test_installed_callbacks_report_native_epochs_and_one_best_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, plots: bool
) -> None:
    import clearml
    from ultralytics.utils import SETTINGS
    from ultralytics.utils.callbacks import clearml as integration

    logger = RecordingLogger()
    models: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []

    class Task:
        @staticmethod
        def current_task() -> type["Task"]:
            return Task

        @staticmethod
        def get_logger() -> RecordingLogger:
            return logger

        @staticmethod
        def update_output_model(**kwargs: Any) -> None:
            models.append(kwargs)

        @staticmethod
        def upload_artifact(**kwargs: Any) -> None:
            artifacts.append(kwargs)

    monkeypatch.setattr(clearml, "Task", Task)
    monkeypatch.delenv("LOCAL_RANK", raising=False)
    monkeypatch.delenv("CY_CLEARML_OWNER_PID", raising=False)
    original_callbacks = integration.callbacks
    original_setting = SETTINGS["clearml"]
    best = tmp_path / "best.pt"
    best.write_bytes(b"native best checkpoint")
    plot = tmp_path / "results.png"
    confusion_matrix = tmp_path / "confusion_matrix.png"
    trainer_pr = tmp_path / "BoxPR_curve.png"
    validator_pr = tmp_path / "MaskPR_curve.png"
    confidence_curve = tmp_path / "BoxF1_curve.png"
    mosaic = tmp_path / "train_batch0.jpg"
    validation = tmp_path / "val_batch0_labels.jpg"
    if plots:
        figure = plt.figure()
        for path in (plot, confusion_matrix, trainer_pr, validator_pr, confidence_curve):
            figure.savefig(path)
        plt.close(figure)
        mosaic.write_bytes(b"native sample")
        validation.write_bytes(b"native sample")
    trainer = SimpleNamespace(
        args=SimpleNamespace(name="native-detector", plots=plots),
        epoch=1,
        epoch_time=2.5,
        save_dir=tmp_path,
        tloss=[0.25, 0.5, 0.75],
        label_loss_items=lambda values, prefix: dict(
            zip(
                [f"{prefix}/box_loss", f"{prefix}/cls_loss", f"{prefix}/dfl_loss"],
                values,
                strict=True,
            )
        ),
        lr={"lr/pg0": 0.01},
        metrics={"metrics/mAP50(B)": 0.9, "val/box_loss": 0.2},
        plots={plot: {}, mosaic: {}, trainer_pr: {}} if plots else {},
        best=best,
        validator=SimpleNamespace(
            save_dir=tmp_path,
            plots={confusion_matrix: {}, validation: {}, validator_pr: {}, confidence_curve: {}}
            if plots
            else {},
            metrics=SimpleNamespace(results_dict={"metrics/mAP50(B)": 0.95}),
        ),
    )
    trainer_plots = trainer.plots
    validator_plots = trainer.validator.plots

    with native_runtime():
        for name in ("on_train_epoch_end", "on_fit_epoch_end", "on_val_end"):
            assert integration.callbacks[name] is getattr(integration, name)
        for epoch in (1, 2):
            trainer.epoch = epoch
            integration.callbacks["on_train_epoch_end"](trainer)
            integration.callbacks["on_fit_epoch_end"](trainer)
        integration.callbacks["on_val_end"](trainer.validator)
        integration.callbacks["on_train_end"](trainer)
        assert trainer.plots is trainer_plots
        assert trainer.validator.plots is validator_plots

    expected_epoch = [
        ("train", "train/box_loss", 0.25),
        ("train", "train/cls_loss", 0.5),
        ("train", "train/dfl_loss", 0.75),
        ("lr", "lr/pg0", 0.01),
        ("Epoch Time", "Epoch Time", 2.5),
        ("metrics", "metrics/mAP50(B)", 0.9),
        ("val", "val/box_loss", 0.2),
    ]
    assert logger.scalars == [(*value, epoch) for epoch in (1, 2) for value in expected_epoch]
    assert logger.single_values == {"metrics/mAP50(B)": 0.95}
    assert models == [
        {"model_path": str(best), "model_name": "native-detector", "auto_delete_file": False}
    ]
    assert best.read_bytes() == b"native best checkpoint"
    assert artifacts == []
    assert [entry["title"] for entry in logger.figures] == (
        ["results", "confusion_matrix", "BoxF1_curve"] if plots else []
    )
    assert [entry["title"] for entry in logger.images] == (
        ["Mosaic", "Validation"] if plots else []
    )
    assert integration.callbacks is original_callbacks
    assert SETTINGS["clearml"] is original_setting


@pytest.mark.parametrize("failure", ["plot", "model"])
def test_native_plot_filter_restores_state_after_publication_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    import clearml
    from ultralytics.utils import SETTINGS
    from ultralytics.utils.callbacks import clearml as integration

    logger = RecordingLogger()

    class Task:
        @staticmethod
        def current_task() -> type["Task"]:
            return Task

        @staticmethod
        def get_logger() -> RecordingLogger:
            return logger

        @staticmethod
        def update_output_model(**_kwargs: Any) -> None:
            raise RuntimeError("model upload failed")

    monkeypatch.setattr(clearml, "Task", Task)
    monkeypatch.delenv("LOCAL_RANK", raising=False)
    monkeypatch.delenv("CY_CLEARML_OWNER_PID", raising=False)
    original_callbacks = integration.callbacks
    original_setting = SETTINGS["clearml"]
    trainer_plots = {tmp_path / "PR_curve.png": {"timestamp": 1}}
    if failure == "plot":
        trainer_plots[tmp_path / "results.png"] = {"timestamp": 2}
    validator_plots = {tmp_path / "PosePR_curve.png": {"timestamp": 3}}
    trainer = SimpleNamespace(
        plots=trainer_plots,
        validator=SimpleNamespace(
            plots=validator_plots,
            metrics=SimpleNamespace(results_dict={"mAP": 0.8}),
        ),
        args=SimpleNamespace(name="native"),
        best=tmp_path / "best.pt",
    )
    expected_error = FileNotFoundError if failure == "plot" else RuntimeError

    with pytest.raises(expected_error), native_runtime():
        integration.callbacks["on_train_end"](trainer)

    assert trainer.plots is trainer_plots
    assert trainer.validator.plots is validator_plots
    assert trainer_plots[tmp_path / "PR_curve.png"] == {"timestamp": 1}
    assert validator_plots[tmp_path / "PosePR_curve.png"] == {"timestamp": 3}
    assert integration.callbacks is original_callbacks
    assert SETTINGS["clearml"] is original_setting
