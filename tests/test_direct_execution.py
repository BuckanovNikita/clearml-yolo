"""Calling-process execution, interruption and standard Hydra sweep integration."""

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from omegaconf import OmegaConf


@pytest.mark.parametrize("fail", [False, True])
def test_owned_execution_waits_before_runtime_and_keeps_original_failure(
    monkeypatch: pytest.MonkeyPatch, fail: bool
) -> None:
    from clearml_yolo.entrypoints.hydra import common

    events: list[object] = []
    expected = RuntimeError("workflow failure")
    task = SimpleNamespace(running_locally=lambda: True)

    def wait(count: int) -> tuple[int, ...]:
        events.append(("wait", count))
        return (2,)

    @contextmanager
    def runtime() -> Iterator[None]:
        events.append("native")
        yield

    @contextmanager
    def invocation(*args: Any, **kwargs: Any) -> Iterator[Any]:
        events.append("task")
        try:
            yield task
        finally:
            events.append("finalize")

    def workflow(ultralytics_predict: dict[str, Any], clearml: dict[str, Any]) -> None:
        events.append(("execute", os.getpid(), ultralytics_predict["device"]))
        if fail:
            raise expected

    monkeypatch.setattr(common, "initialize_filesystem", lambda: None)
    monkeypatch.setattr(common, "wait_for_available_gpus", wait)
    monkeypatch.setattr(common, "native_runtime", runtime)
    monkeypatch.setattr(common, "invocation", invocation)
    monkeypatch.setattr(common, "replay_configuration", lambda task, values: values)
    monkeypatch.setattr(common, "initialize_naming", lambda task: None)
    monkeypatch.setattr(common, "release_training_memory", lambda: events.append("release"))
    from clearml_yolo.adapters.clearml import session

    monkeypatch.setattr(session, "record_run_configuration", lambda *args: None)
    config = OmegaConf.create({"ultralytics_predict": {"device": -1}, "clearml": {}})
    if fail:
        with pytest.raises(RuntimeError) as caught:
            common.execute_owned("predict", config, workflow)
        assert caught.value is expected
    else:
        common.execute_owned("predict", config, workflow)
    assert events == [
        ("wait", 1),
        "native",
        "task",
        ("execute", os.getpid(), [2]),
        "release",
        "finalize",
    ]


def test_interruption_while_waiting_does_not_initialize_runtime_or_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from clearml_yolo.entrypoints.hydra import common

    def interrupt(count: int) -> tuple[int, ...]:
        raise KeyboardInterrupt

    monkeypatch.setattr(common, "initialize_filesystem", lambda: None)
    monkeypatch.setattr(common, "wait_for_available_gpus", interrupt)
    monkeypatch.setattr(common, "native_runtime", lambda: pytest.fail("native runtime started"))
    monkeypatch.setattr(common, "invocation", lambda *a, **kw: pytest.fail("task created"))
    with pytest.raises(KeyboardInterrupt):
        common.execute_owned(
            "train", OmegaConf.create({"ultralytics": {"device": 0}}), lambda ultralytics: None
        )


def test_gpu_cleanup_does_not_replace_primary_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from clearml_yolo.entrypoints.hydra import common

    expected = ValueError("computation failed")

    def fail() -> None:
        raise RuntimeError("cleanup failed")

    monkeypatch.setattr(common, "release_training_memory", fail)
    with pytest.raises(ValueError, match="computation failed") as caught, common._gpu_cleanup(True):
        raise expected
    assert caught.value is expected


@pytest.mark.parametrize("fail", [False, True])
def test_standard_multirun_executes_sequentially_in_calling_process(
    tmp_path: Path, fail: bool
) -> None:
    script = tmp_path / "direct_sweep.py"
    script.write_text(
        """\
import json
import os
from pathlib import Path
from hydra.core.hydra_config import HydraConfig
from clearml_yolo.entrypoints.hydra import common

root = Path(os.environ["TEST_DIRECT_ROOT"])
pid = os.getpid()
(root / "pid").write_text(str(pid))

def record(name, config, function):
    value = config.model_label
    output = Path(HydraConfig.get().runtime.output_dir)
    with (root / "events.jsonl").open("a") as stream:
        stream.write(json.dumps({"event": "start", "value": value, "pid": os.getpid(),
            "cwd": str(Path.cwd()), "output": str(output),
            "marker": os.environ.get("DIRECT_MARKER")}) + "\\n")
        stream.write(json.dumps({"event": "end", "value": value}) + "\\n")
    if value == "first" and os.environ["TEST_DIRECT_FAIL"] == "1":
        raise RuntimeError("direct workflow failure")

common.execute_owned = record
common.launch("predict", lambda: None)
assert "DIRECT_MARKER" not in os.environ
""",
        encoding="utf-8",
    )
    completed = subprocess.run(  # noqa: S603 - current interpreter and task-owned fixture
        [
            sys.executable,
            str(script),
            "--multirun",
            "model_label=first,second",
            "ground_truth=unused.csv",
            "ultralytics_predict.device=cpu",
            f"hydra.sweep.dir={tmp_path}/sweep",
            "hydra.job.chdir=true",
            "+hydra.job.env_set.DIRECT_MARKER=sweep-marker",
        ],
        env=os.environ
        | {
            "CY_HOME": str(tmp_path),
            "TEST_DIRECT_ROOT": str(tmp_path),
            "TEST_DIRECT_FAIL": str(int(fail)),
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == int(fail), completed.stdout + completed.stderr
    records = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert [(record["event"], record["value"]) for record in records] == [
        ("start", "first"),
        ("end", "first"),
        ("start", "second"),
        ("end", "second"),
    ]
    pid = int((tmp_path / "pid").read_text())
    for index, record in enumerate(records[::2]):
        assert record["pid"] == pid
        assert record["cwd"] == record["output"] == str(tmp_path / "sweep" / str(index))
        assert record["marker"] == "sweep-marker"
    if fail:
        assert "direct workflow failure" in completed.stderr
        assert "BaseExceptionGroup" not in completed.stderr
