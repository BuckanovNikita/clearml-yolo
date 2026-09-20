"""Native training forwards settings and reads actual parent-process outputs."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

import pytest

from clearml_yolo.clearml_session import ClearMLConfig
from clearml_yolo.tasks.train import train


@pytest.mark.parametrize("device", ["cpu", [0, 1]])
def test_native_forwarding_and_actual_checkpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    device: Any,
) -> None:
    calls: dict[str, Any] = {}
    source = tmp_path / "original.yaml"
    source.write_text("path: original\n")
    override = tmp_path / "override.yaml"
    override.write_text("path: override\n")
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.connect_config_file", lambda *args, **kwargs: override
    )
    actual = tmp_path / "native-incremented"
    (actual / "weights").mkdir(parents=True)
    (actual / "weights/best.pt").write_bytes(b"checkpoint")
    (actual / "weights/last.pt").write_bytes(b"last")

    class Model:
        def __init__(self, model: str) -> None:
            calls["model"] = model
            self.trainer = types.SimpleNamespace(
                save_dir=actual, args=types.SimpleNamespace(), data={}
            )

        def train(self, **kwargs: Any) -> None:
            calls.update(kwargs)
            self.trainer.args = types.SimpleNamespace(**kwargs)

    module = types.ModuleType("ultralytics.models")
    module.YOLO = Model  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ultralytics.models", module)
    monkeypatch.setattr("clearml_yolo.tasks.train.init_task", lambda *a, **k: object())
    monkeypatch.setattr("clearml_yolo.tasks.train.expect_artifacts", lambda *a, **k: None)
    monkeypatch.setattr(
        "clearml_yolo.tasks.train.upload_artifact", lambda *a, **k: None, raising=False
    )
    result = train(
        ultralytics={
            "model": "architecture.pt",
            "data": str(source),
            "device": device,
            "batch": -1,
            "amp": False,
            "compile": False,
            "project": str(tmp_path),
            "name": "asked",
        },
        clearml=ClearMLConfig(),
    )
    assert calls["data"] == str(override)
    assert calls["device"] == device
    assert calls["batch"] == -1
    assert calls["amp"] is False
    assert calls["compile"] is False
    assert result.weights == actual / "weights/best.pt"


def test_native_ddp_children_inherit_tracking_isolation() -> None:
    import os
    import subprocess

    from clearml_yolo.native_runtime import native_runtime

    with native_runtime():
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from ultralytics.utils import SETTINGS; "
                    "from ultralytics.utils.callbacks import clearml; "
                    "assert SETTINGS['clearml'] is False; assert not clearml.callbacks"
                ),
            ],
            env=dict(os.environ, LOCAL_RANK="-1"),
            capture_output=True,
            text=True,
            check=False,
        )
    assert result.returncode == 0, result.stderr
