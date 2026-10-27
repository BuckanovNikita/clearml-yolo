"""Owner event draining preserves the last worker metrics after process exit."""

from pathlib import Path

import pytest

from clearml_yolo.adapters.integrations.distributed_training import _WorkerEvents
from clearml_yolo.application.training_workers import WorkerScalar


def test_final_events_and_complete_console_output_are_drained(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    reported: list[tuple[str, float, int]] = []
    events = _WorkerEvents(tmp_path, lambda *event: reported.append(event), 2)
    events.poll(lambda: (1, 2))
    message = "a" * 140000
    (tmp_path / "rank-1.log").write_text(message)
    event = WorkerScalar(name="val/map", value=0.8, step=2)
    (tmp_path / "rank-0.jsonl").write_text(event.model_dump_json() + "\n")
    events.finish()
    assert reported == [("val/map", 0.8, 2)]
    assert capfd.readouterr().out == message
    events.finish()
    assert reported == [("val/map", 0.8, 2)]
    assert capfd.readouterr().out == ""


def test_event_polling_does_not_request_unused_process_ownership(tmp_path: Path) -> None:
    events = _WorkerEvents(tmp_path, lambda *_: None, 1)

    def forbidden() -> tuple[int, ...]:
        pytest.fail("Scalar replay does not need to inspect process ownership")

    events.poll(forbidden)
