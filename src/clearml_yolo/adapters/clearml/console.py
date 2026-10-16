"""Supervise attach-only telemetry outside the native computation process."""

import json
import os
import signal
import subprocess
import sys
from contextlib import suppress
from pathlib import Path
from time import monotonic, sleep
from uuid import uuid4

from clearml_yolo.adapters.observability.capture import OutputCapture, write_offsets


class ConsolePublicationError(RuntimeError):
    """Required telemetry did not reach the acknowledged final byte offsets."""


class ConsolePublisher:
    def __init__(
        self,
        task_id: str,
        capture: OutputCapture,
        *,
        timeout: float = 8.0,
        command: list[str] | None = None,
        offline_folder: Path | None = None,
    ) -> None:
        self.capture = capture
        self.directory = capture.directory / f"publisher-{uuid4().hex}"
        self.directory.mkdir(mode=0o700)
        initial = (
            capture.offsets() if capture.publication_started else dict.fromkeys(capture.paths, 0)
        )
        capture.publication_started = True
        write_offsets(self.directory / "publisher-initial.json", initial)
        self.timeout = timeout
        self.process: subprocess.Popen[bytes] | None = None
        self._finished = False
        self.command = command or [
            sys.executable,
            "-u",
            "-m",
            "clearml_yolo.adapters.clearml.console_worker",
            task_id,
            str(capture.directory.resolve()),
            str(offline_folder) if offline_folder else "",
            str(self.directory),
        ]

    def start(self) -> None:
        with (self.directory / "publisher-diagnostics.log").open("ab", buffering=0) as diagnostics:
            self.process = subprocess.Popen(  # noqa: S603 - explicit local worker or injected test command
                self.command,
                stdout=diagnostics,
                stderr=diagnostics,
                start_new_session=True,
            )

    def _stop_owned_process(self) -> None:
        if self.process is not None and self.process.poll() is None:
            with suppress(ProcessLookupError):
                os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait(timeout=2)

    def _acknowledges(self, target: dict[str, int]) -> bool:
        receipt = self.directory / "publisher-receipt.json"
        if not receipt.is_file():
            return False
        try:
            values = json.loads(receipt.read_text())
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ConsolePublicationError("Console publisher barrier receipt is corrupt") from error
        if (
            not isinstance(values, dict)
            or set(values) != set(target)
            or any(type(value) is not int or value < 0 for value in values.values())
        ):
            raise ConsolePublicationError("Console publisher barrier receipt is invalid")
        return all(values[name] >= offset for name, offset in target.items())

    def _wait_for_barrier(self, target: dict[str, int]) -> None:
        deadline = monotonic() + self.timeout
        while monotonic() < deadline:
            if self.process is None or self.process.poll() is not None:
                raise ConsolePublicationError(
                    "Console publisher stopped before publication barrier"
                )
            if self._acknowledges(target):
                return
            sleep(0.025)
        raise ConsolePublicationError("Console publication barrier deadline expired; logs retained")

    def barrier(self) -> None:
        """Confirm workload bytes before SDK close can mark the task completed."""
        target = self.capture.offsets()
        write_offsets(self.directory / "publisher-barrier.json", target)
        try:
            self._wait_for_barrier(target)
        except BaseException:
            # An uncertain checkpoint is terminal: never restart or replay its bytes.
            self._stop_owned_process()
            raise

    def finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        if self.process is None:
            raise ConsolePublicationError("Console publisher did not start")
        try:
            final = self.capture.offsets()
            write_offsets(self.directory / "publisher-final.json", final)
            self.process.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired as error:
            self._stop_owned_process()
            raise ConsolePublicationError(
                "Console publication deadline expired; local logs retained"
            ) from error
        except BaseException:
            self._stop_owned_process()
            raise
        receipt = self.directory / "publisher-receipt.json"
        if self.process.returncode != 0 or not receipt.is_file():
            raise ConsolePublicationError(
                "Console publisher failed; delivery is uncertain and logs retained"
            )
        if json.loads(receipt.read_text()) != final:
            raise ConsolePublicationError("Console publication did not acknowledge final offsets")
