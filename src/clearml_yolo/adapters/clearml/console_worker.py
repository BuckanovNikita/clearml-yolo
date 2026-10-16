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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from clearml_yolo.adapters.observability.capture import write_offsets
from clearml_yolo.core.presentation import HumanSeriesRegistry, HumanTextStream

_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_CONTROL_ARGUMENT = 4


@dataclass
class _ConsoleStream:
    decoder: codecs.IncrementalDecoder = field(
        default_factory=lambda: codecs.getincrementaldecoder("utf-8")(errors="surrogateescape")
    )
    text: HumanTextStream = field(default_factory=HumanTextStream)

    @property
    def pending_bytes(self) -> int:
        return len(self.decoder.getstate()[0]) + len(
            self.text.pending.encode("utf-8", errors="surrogateescape")
        )


@dataclass
class PublicationState:
    """Unpublished text tails, kept separate from durable delivery receipts."""

    streams: dict[str, _ConsoleStream] = field(default_factory=dict)
    scalar_labels: HumanSeriesRegistry = field(default_factory=HumanSeriesRegistry)


def _publish_text(
    stream: _ConsoleStream, payload: bytes, sink: Any, *, final: bool, checkpoint: bool
) -> None:
    text = stream.text.feed(stream.decoder.decode(payload, final=final), final=final)
    if checkpoint and not stream.decoder.getstate()[0]:
        text += stream.text.checkpoint()
    # Invalid original UTF-8 remains byte-exact in capture; SDK strings must be valid.
    text = text.encode("utf-8", errors="surrogateescape").decode("utf-8", errors="replace")
    for console_line in _ANSI.sub("", text).split("\n"):
        latest = console_line.split("\r")[-1]
        if latest:
            sink.report_text(latest, print_console=False)


def _complete_checkpoint_character(
    console: _ConsoleStream,
    path: Path,
    position: int,
    sink: Any,
) -> int:
    """Read at most the remaining bytes of one UTF-8 character past a watermark."""
    consumed = 0
    with path.open("rb") as stream:
        stream.seek(position)
        for _ in range(3):
            if not console.decoder.getstate()[0]:
                break
            continuation = stream.read(1)
            if not continuation:
                break
            consumed += len(continuation)
            _publish_text(console, continuation, sink, final=False, checkpoint=True)
    return consumed


def publish_batch(
    paths: dict[str, Path],
    offsets: dict[str, int],
    sink: Any,
    *,
    final: bool = False,
    limits: dict[str, int] | None = None,
    state: PublicationState | None = None,
    checkpoint: bool = False,
) -> dict[str, int]:
    state = state if state is not None else PublicationState()
    acknowledged = offsets.copy()
    for name, path in paths.items():
        console = state.streams.setdefault(name, _ConsoleStream()) if name != "scalars" else None
        read_from = offsets[name] + (console.pending_bytes if console else 0)
        with path.open("rb") as stream:
            stream.seek(read_from)
            size = min(1024 * 1024, max(0, limits[name] - read_from)) if limits else 1024 * 1024
            payload = stream.read(size)
        reached_limit = limits is not None and read_from + len(payload) >= limits[name]
        reached_final = final and (limits is None or reached_limit)
        if name == "scalars":
            complete = payload.rfind(b"\n") + 1
            if reached_final and complete != len(payload):
                raise ValueError("Incomplete native scalar journal")
            for line in payload[:complete].splitlines():
                record = json.loads(line)
                if set(record) != {"title", "series", "value", "iteration"}:
                    raise ValueError("Invalid native scalar journal")
                record["title"], record["series"] = state.scalar_labels.resolve(
                    record["title"],
                    record["series"],
                )
                sink.report_scalar(**record)
            acknowledged[name] += complete
        else:
            if console is None:
                raise RuntimeError("Console stream state is unavailable")
            _publish_text(
                console,
                payload,
                sink,
                final=reached_final,
                checkpoint=checkpoint and reached_limit,
            )
            consumed = len(payload)
            if checkpoint and reached_limit and console.decoder.getstate()[0]:
                # A watermark may bisect one UTF-8 character. Finish only that
                # character beyond it; never acknowledge undecoded original bytes.
                consumed += _complete_checkpoint_character(
                    console,
                    path,
                    read_from + consumed,
                    sink,
                )
            acknowledged[name] = read_from + consumed - console.pending_bytes
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
    state = PublicationState()
    while True:
        stop = controls / "publisher-final.json"
        final = stop.is_file()
        barrier = controls / "publisher-barrier.json"
        limits = json.loads(stop.read_text()) if final else None
        if not final and barrier.is_file():
            requested = json.loads(barrier.read_text())
            if any(offsets[name] < value for name, value in requested.items()):
                limits = requested
        offsets = publish_batch(
            paths,
            offsets,
            sink,
            final=final,
            limits=limits,
            state=state,
            checkpoint=limits is not None and not final,
        )
        write_offsets(controls / "publisher-receipt.json", offsets)
        if final and offsets == limits:
            return
        if final:
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
