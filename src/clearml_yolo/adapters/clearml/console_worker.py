"""Attach to an existing task, batch durable console/scalars, acknowledge flushes.

This worker never initializes, closes or changes the status of a task. A crash or
timeout is an uncertain delivery, and the supervisor never automatically replays it.
"""

import codecs
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from clearml_yolo.adapters.observability.capture import write_offsets

_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_CONTROL_ARGUMENT = 4


def publish_batch(
    paths: dict[str, Path],
    offsets: dict[str, int],
    sink: Any,
    *,
    final: bool = False,
    limits: dict[str, int] | None = None,
) -> dict[str, int]:
    acknowledged = offsets.copy()
    for name, path in paths.items():
        with path.open("rb") as stream:
            stream.seek(offsets[name])
            size = min(1024 * 1024, limits[name] - offsets[name]) if limits else 1024 * 1024
            payload = stream.read(size)
        reached_final = (
            final and limits is not None and offsets[name] + len(payload) == limits[name]
        )
        if name == "scalars":
            complete = payload.rfind(b"\n") + 1
            if reached_final and complete != len(payload):
                raise ValueError("Incomplete native scalar journal")
            for line in payload[:complete].splitlines():
                record = json.loads(line)
                if set(record) != {"title", "series", "value", "iteration"}:
                    raise ValueError("Invalid native scalar journal")
                sink.report_scalar(**record)
            acknowledged[name] += complete
        else:
            decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
            text = decoder.decode(payload, final=final and (limits is None or reached_final))
            trailing = len(decoder.getstate()[0])
            # Preserve raw bytes locally; only the latest carriage-return rewrite
            # belongs in each console batch, rather than every native bar frame.
            for console_line in _ANSI.sub("", text).split("\n"):
                latest = console_line.split("\r")[-1]
                if latest:
                    sink.report_text(latest, print_console=False)
            acknowledged[name] += len(payload) - trailing
    if sink.flush(wait=True) is not True:
        raise RuntimeError("ClearML console/scalar flush was not confirmed")
    return acknowledged


class _OfflineSink:
    """Append offline events to the already-owned SDK task folder, without init."""

    def __init__(self, folder: Path, task_id: str) -> None:
        self.path = folder / "log.jsonl"
        self.task_id = task_id
        self.events: list[dict[str, object]] = []

    def report_text(self, message: str, *, print_console: bool) -> None:
        del print_console
        self.events.append(
            {
                "task": self.task_id,
                "type": "log",
                "level": "info",
                "msg": message,
                "timestamp": int(time.time() * 1000),
                "worker": "console-publisher",
            }
        )

    def report_scalar(self, **record: object) -> None:
        self.events.append(
            {
                "task": self.task_id,
                "type": "training_stats_scalar",
                **record,
                "timestamp": int(time.time() * 1000),
            }
        )

    def flush(self, *, wait: bool) -> bool:
        del wait
        if self.events:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(self.events) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            self.events.clear()
        return True


def run(
    task_id: str,
    directory: Path,
    offline_folder: Path | None = None,
    control_directory: Path | None = None,
) -> None:
    sink: Any
    if offline_folder is not None:
        sink = _OfflineSink(offline_folder, task_id)
    else:
        from clearml import Task

        task: Any = Task.get_task(task_id=task_id)
        sink = task.get_logger()
        sink.set_flush_period(2)
    paths = {
        name: directory / filename
        for name, filename in (
            ("stdout", "stdout.log"),
            ("stderr", "stderr.log"),
            ("scalars", "scalars.jsonl"),
        )
    }
    controls = control_directory or directory
    initial = controls / "publisher-initial.json"
    offsets = json.loads(initial.read_text()) if initial.is_file() else dict.fromkeys(paths, 0)
    while True:
        stop = controls / "publisher-final.json"
        limits = json.loads(stop.read_text()) if stop.is_file() else None
        offsets = publish_batch(paths, offsets, sink, final=limits is not None, limits=limits)
        write_offsets(controls / "publisher-receipt.json", offsets)
        if limits is not None and offsets == limits:
            return
        if limits is not None:
            continue
        # A short stop poll bounds shutdown without changing the two-second batch.
        until = time.monotonic() + 2
        while time.monotonic() < until and not stop.is_file():
            time.sleep(0.05)


def main() -> None:
    run(
        sys.argv[1],
        Path(sys.argv[2]),
        Path(sys.argv[3]) if sys.argv[3] else None,
        Path(sys.argv[_CONTROL_ARGUMENT]) if len(sys.argv) > _CONTROL_ARGUMENT else None,
    )


if __name__ == "__main__":
    main()
