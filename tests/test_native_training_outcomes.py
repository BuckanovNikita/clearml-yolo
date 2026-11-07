"""Native completion publication is recoverable, native computation remains strict."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from clearml_yolo.adapters.clearml import session
from clearml_yolo.adapters.integrations import native_ddp, native_runtime, training
from clearml_yolo.application.contracts import PreparedDataset
from test_clearml_session import FakeTask


@pytest.mark.parametrize("stage", ["pipeline", "train"])
@pytest.mark.parametrize("error_type", [ConnectionError, KeyboardInterrupt])
def test_native_end_callback_preserves_only_pipeline_publication_failure(
    tmp_path: Path,
    stage: str,
    error_type: type[BaseException],
) -> None:
    best = tmp_path / "detect" / "train" / "weights" / "best.pt"
    best.parent.mkdir(parents=True)
    best.write_bytes(b"weights")
    state = session._InvocationState(task=FakeTask(), stages=[stage], current_stage="train")
    token = session._ACTIVE_INVOCATION.set(state)

    def fail(_trainer: Any) -> None:
        raise error_type("upload failed")

    trainer = SimpleNamespace(best=best, save_dir=best.parent.parent)
    wrapped = native_runtime._completed_training_publication(fail)
    try:
        if stage == "pipeline" and error_type is ConnectionError:
            wrapped(trainer)
            assert state.pipeline_outcome is not None
            assert state.pipeline_outcome.status == "completed_with_warnings"
        else:
            with pytest.raises(error_type):
                wrapped(trainer)
    finally:
        session._ACTIVE_INVOCATION.reset(token)


@pytest.mark.parametrize("training_fails", [False, True])
@pytest.mark.parametrize("relay_fails", [False, True])
def test_relay_exit_failure_only_softens_after_native_return(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    training_fails: bool,
    relay_fails: bool,
) -> None:
    from ultralytics import models

    from clearml_yolo.adapters.integrations import batch_resolution, native_trainer

    directory = tmp_path / "detect" / "train"
    best = directory / "weights" / "best.pt"
    best.parent.mkdir(parents=True)
    best.write_bytes(b"weights")
    gt = tmp_path / "gt.csv"
    gt.write_text("split,instance_label\ntrain,a\n")
    prepared = PreparedDataset(
        data=tmp_path / "data.yaml",
        ground_truth=gt,
        manifest=tmp_path / "manifest.json",
        dataset_format="ndjson",
        artifacts=[],
    )
    trainer = SimpleNamespace(save_dir=directory, args=SimpleNamespace(name="train"), ddp=True)

    class Model:
        task = "detect"

        def __init__(self, *_args: Any) -> None:
            self.trainer = trainer

        def train(self, **_kwargs: Any) -> None:
            if training_fails:
                raise ValueError("native computation failed")

    def relay(task: Any, model: Any) -> native_ddp.NativeDDPRelay:
        instance = native_ddp.NativeDDPRelay(task, model, str(tmp_path / "relay"))
        if relay_fails:
            instance._failure = ConnectionError("relay cleanup publication failed")
        return instance

    # Exercise the real replay and __exit__ exception paths without starting a worker.
    monkeypatch.setattr(native_ddp.NativeDDPRelay, "__enter__", lambda self: self)
    if not relay_fails:

        def restore_arguments(self: native_ddp.NativeDDPRelay, value: Any) -> None:
            self._attempted = True
            value.args.name = "worker-normalized"

        monkeypatch.setattr(native_ddp.NativeDDPRelay, "replay", restore_arguments)

    monkeypatch.setattr(models, "YOLO", Model)
    monkeypatch.setattr(batch_resolution, "resolve_yolo_batch", lambda _a, s, *_args: (s, None))
    monkeypatch.setattr(native_trainer, "trainer_with_transforms", lambda _t: object)
    monkeypatch.setattr(training, "native_ddp_relay", relay)
    monkeypatch.setattr(training, "write_native_yaml", lambda *_args: None)
    monkeypatch.setattr(training, "record_run_configuration", lambda *_args: None)
    monkeypatch.setattr(training, "finalize_native_model", lambda *_args: None)
    state = session._InvocationState(task=FakeTask(), stages=["pipeline"], current_stage="train")
    token = session._ACTIVE_INVOCATION.set(state)
    try:
        if training_fails:
            with pytest.raises(ValueError, match="native computation"):
                training.execute_training(
                    state.task,
                    "yolo.pt",
                    {"project": str(directory.parent), "name": "train"},
                    prepared,
                )
            assert state.pipeline_outcome is None
        else:
            result = training.execute_training(
                state.task,
                "yolo.pt",
                {"project": str(directory.parent), "name": "train"},
                prepared,
            )
            assert result.weights == best
            assert state.pipeline_outcome is not None
            if relay_fails:
                assert state.pipeline_outcome.status == "completed_with_warnings"
            else:
                assert state.pipeline_outcome.status == "succeeded"
                assert result.effective_args["name"] == "worker-normalized"
    finally:
        session._ACTIVE_INVOCATION.reset(token)


@pytest.mark.parametrize("final", [True, False])
def test_final_validation_callback_distinguishes_epoch_publication(
    tmp_path: Path,
    final: bool,
) -> None:
    best = tmp_path / "detect" / "train" / "weights" / "best.pt"
    best.parent.mkdir(parents=True)
    best.write_bytes(b"weights")
    state = session._InvocationState(task=FakeTask(), stages=["pipeline"], current_stage="train")
    token = session._ACTIVE_INVOCATION.set(state)

    def fail(_trainer: Any) -> None:
        raise ConnectionError("scalar publication failed")

    trainer = SimpleNamespace(best=best, save_dir=best.parent.parent)
    wrapped = native_runtime._final_evaluation_publication(fail)
    try:
        if final:
            with native_runtime.final_training_evaluation():
                wrapped(trainer)
            assert state.pipeline_outcome is not None
            assert state.pipeline_outcome.status == "completed_with_warnings"
        else:
            with pytest.raises(ConnectionError):
                wrapped(trainer)
            assert state.pipeline_outcome is None
    finally:
        session._ACTIVE_INVOCATION.reset(token)
