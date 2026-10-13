"""Append native FD output locally; mirror through an independent local process.

File descriptors point directly at append-only files. Neither a stopped mirror nor
a blocked network publisher can backpressure training or destroy captured bytes.
"""

import io
import json
import math
import os
import subprocess
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from clearml_yolo.adapters.runtime.bootstrap import project_write_path

_ACTIVE: tuple[int, "OutputCapture"] | None = None
_TTY_ENV = "CY_CAPTURE_STDERR_TTY"
_SCALAR_ENV = "CY_SCALAR_JOURNAL"


def active_capture() -> "OutputCapture | None":
    return _ACTIVE[1] if _ACTIVE is not None and _ACTIVE[0] == os.getpid() else None


def terminal_isatty() -> bool:
    """Use the caller's capability even after FD redirection or worker spawning."""
    selected = os.environ.get(_TTY_ENV)
    return selected == "1" if selected is not None else sys.stderr.isatty()


def write_offsets(path: Path, offsets: dict[str, int]) -> None:
    _write_json_state(path, offsets)


def _write_json_state(path: Path, values: Mapping[str, object]) -> None:
    path = project_write_path(path)
    temporary: Path | None = None
    try:
        # Exclusive temporary creation is private from its first byte and cannot
        # follow a pre-existing sibling symlink or collide with another writer.
        with NamedTemporaryFile(
            mode="w",
            prefix=f".{path.name}-",
            suffix=".pending",
            dir=path.parent,
            delete=False,
            encoding="utf-8",
        ) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(values))
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_progress(**fields: str | int) -> None:
    """Publish optional local status without knowing which caller consumes it."""
    selected = os.environ.get("CY_PROGRESS_FILE")
    if selected is None:
        return
    path = project_write_path(selected)
    path.parent.mkdir(parents=True, exist_ok=True)
    values = json.loads(path.read_text()) if path.is_file() else {}
    if not isinstance(values, dict):
        raise TypeError("Local progress state must be a JSON object")
    values.update(fields)
    _write_json_state(path, values)


def append_scalar(title: str, series: str, value: float, iteration: int) -> bool:
    """Return False when no capture is bound, preserving embedding fallbacks."""
    selected = os.environ.get(_SCALAR_ENV)
    if selected is None:
        return False
    if not math.isfinite(value):
        raise ValueError("Native scalar must be finite")
    record = {"title": title, "series": series, "value": value, "iteration": iteration}
    payload = (json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n").encode()
    descriptor = os.open(project_write_path(selected), os.O_WRONLY | os.O_APPEND)
    try:
        if os.write(descriptor, payload) != len(payload):
            raise OSError("Incomplete scalar journal write")
    finally:
        os.close(descriptor)
    write_progress(progress=f"Training step {iteration}", iteration=iteration)
    return True


class OutputCapture:
    def __init__(self, directory: Path) -> None:
        directory = project_write_path(directory).resolve()
        self.directory = directory
        self.paths = {
            "stdout": directory / "stdout.log",
            "stderr": directory / "stderr.log",
            "scalars": directory / "scalars.jsonl",
        }
        self.saved: list[int] = []
        self.buffering: list[tuple[io.TextIOWrapper, bool, bool]] = []
        self.mirror: subprocess.Popen[bytes] | None = None
        self.publication_started = False
        self.mirror_control = directory / f"mirror-{uuid4().hex}"

    def prepare(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        for path in self.paths.values():
            descriptor = os.open(
                project_write_path(path), os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600
            )
            os.close(descriptor)

    def offsets(self) -> dict[str, int]:
        for stream in (sys.stdout, sys.stderr):
            stream.flush()
        return {name: path.stat().st_size for name, path in self.paths.items()}

    def start(self) -> None:
        self.mirror_control.mkdir(mode=0o700)
        write_offsets(self.mirror_control / "initial.json", self.offsets())
        for descriptor, stream, name in ((1, sys.stdout, "stdout"), (2, sys.stderr, "stderr")):
            stream.flush()
            self.saved.append(os.dup(descriptor))
            target = os.open(self.paths[name], os.O_WRONLY | os.O_APPEND)
            try:
                os.dup2(target, descriptor)
            finally:
                os.close(target)
            if isinstance(stream, io.TextIOWrapper):
                self.buffering.append((stream, stream.line_buffering, stream.write_through))
                stream.reconfigure(line_buffering=True, write_through=True)
        diagnostics_path = project_write_path(self.directory / "mirror-diagnostics.log")
        with diagnostics_path.open("ab", buffering=0) as diagnostics:
            self.mirror = subprocess.Popen(  # noqa: S603 - fixed local module and explicit descriptors
                [
                    sys.executable,
                    "-u",
                    "-m",
                    "clearml_yolo.adapters.observability.mirror_worker",
                    str(self.directory),
                    str(os.getpid()),
                    *(str(fd) for fd in self.saved),
                    str(self.mirror_control),
                ],
                pass_fds=tuple(self.saved),
                stdout=diagnostics,
                stderr=diagnostics,
            )

    def restore(self) -> None:
        for descriptor, original in enumerate(self.saved, start=1):
            os.dup2(original, descriptor)
        for stream, line_buffering, write_through in self.buffering:
            stream.reconfigure(line_buffering=line_buffering, write_through=write_through)

    def stop(self) -> None:
        try:
            try:
                write_offsets(self.mirror_control / "final.json", self.offsets())
            finally:
                self.restore()
        finally:
            try:
                if self.mirror is not None:
                    try:
                        self.mirror.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.mirror.kill()
                        self.mirror.wait(timeout=2)
                    if self.mirror.returncode != 0:
                        raise RuntimeError(
                            "Local console mirror failed; captured logs are retained"
                        )
            finally:
                for original in self.saved:
                    os.close(original)


@contextmanager
def capture_output(directory: Path) -> Iterator[OutputCapture]:
    """Own FD capture once per process, with bounded mirror shutdown and restoration."""
    global _ACTIVE  # noqa: PLW0603 - explicit process-owned capture lifetime
    existing = active_capture()
    if existing is not None:
        yield existing
        return
    capture = OutputCapture(directory)
    capture.prepare()
    previous_active = _ACTIVE
    previous = {key: os.environ.get(key) for key in (_TTY_ENV, _SCALAR_ENV, "PYTHONUNBUFFERED")}
    primary: BaseException | None = None
    try:
        os.environ[_TTY_ENV] = "1" if terminal_isatty() else "0"
        os.environ[_SCALAR_ENV] = str(capture.paths["scalars"].resolve())
        os.environ["PYTHONUNBUFFERED"] = "1"
        capture.start()
        _ACTIVE = (os.getpid(), capture)
        yield capture
    except BaseException as error:
        primary = error
        raise
    finally:
        try:
            capture.stop()
        except BaseException:
            if primary is None:
                raise
        finally:
            _ACTIVE = previous_active
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
