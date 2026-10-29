"""Real loopback and subprocess checks for bounded documentation ownership."""

import json
import os
import socket
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http import HTTPStatus
from http.client import HTTPConnection
from pathlib import Path
from threading import Event, Thread
from time import monotonic

import pytest

from clearml_yolo.adapters.documentation import server as server_module
from clearml_yolo.adapters.documentation import worker as worker_module
from clearml_yolo.adapters.documentation.files import (
    MAX_REQUEST_BYTES,
    asset_bytes,
    document_name,
    preview_directory,
)
from clearml_yolo.adapters.documentation.server import DocumentationServer, make_server
from clearml_yolo.adapters.documentation.worker import PreviewWorkers
from clearml_yolo.core.documentation import Catalog, PreviewRequest, PreviewResult


def _catalog() -> Catalog:
    return Catalog(
        version="test",
        commands={},
        models=[],
        profiles=[],
        fields=[],
        configurations=[],
        tutorials=[],
    )


@contextmanager
def _running(preview: Callable[[PreviewRequest], PreviewResult]) -> Iterator[DocumentationServer]:
    with make_server(_catalog(), preview) as server:
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            thread.join(timeout=2)
            assert not thread.is_alive()


def _request(
    server: DocumentationServer,
    method: str,
    target: str,
    body: str | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, bytes, dict[str, str]]:
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    try:
        connection.request(method, target, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, response.read(), dict(response.getheaders())
    finally:
        connection.close()


def _raw(server: DocumentationServer, request: bytes) -> bytes:
    with socket.create_connection(("127.0.0.1", server.server_port), timeout=3) as connection:
        connection.sendall(request)
        connection.shutdown(socket.SHUT_WR)
        result = bytearray()
        while chunk := connection.recv(65536):
            result.extend(chunk)
    return bytes(result)


def _until(predicate: Callable[[], bool]) -> None:
    deadline = monotonic() + 3
    pause = Event()
    while not predicate():
        if monotonic() >= deadline:
            pytest.fail("Expected asynchronous state was not reached")
        pause.wait(0.01)


def test_loopback_assets_catalog_and_preview_are_served() -> None:
    observed: list[PreviewRequest] = []

    def preview(request: PreviewRequest) -> PreviewResult:
        observed.append(request)
        return PreviewResult(command=request.command)

    with _running(preview) as server:
        assert server.server_address[0] == "127.0.0.1"
        status, body, headers = _request(server, "GET", "/")
        assert status == HTTPStatus.OK
        assert b"<html" in body
        assert "default-src 'self'" in headers["Content-Security-Policy"]
        assert headers["X-Content-Type-Options"] == "nosniff"
        status, body, _ = _request(server, "GET", "/api/catalog")
        assert status == HTTPStatus.OK
        assert json.loads(body)["version"] == "test"
        status, body, _ = _request(
            server,
            "POST",
            "/api/preview",
            '{"command":"train","overrides":["ground_truth=truth.csv"]}',
            {"Content-Type": "application/json"},
        )
        assert status == HTTPStatus.OK
        assert json.loads(body)["command"] == "train"
        assert observed[0].overrides == ["ground_truth=truth.csv"]


@pytest.mark.parametrize(
    "headers",
    [
        {"Host": "attacker.invalid"},
        {"Origin": "https://attacker.invalid"},
        {"Origin": "null"},
    ],
)
def test_foreign_host_or_origin_is_rejected(headers: dict[str, str]) -> None:
    with _running(lambda request: PreviewResult()) as server:
        assert _request(server, "GET", "/api/catalog", headers=headers)[0] == HTTPStatus.FORBIDDEN


@pytest.mark.parametrize(
    ("headers", "body"),
    [
        ("Content-Length: 2\r\nContent-Length: 2\r\n", b"{}"),
        ("Content-Length: 2\r\nTransfer-Encoding: chunked\r\n", b"{}"),
        ("Content-Length: 20\r\n", b"{}"),
        ("Content-Length: -1\r\n", b""),
        (f"Content-Length: {MAX_REQUEST_BYTES + 1}\r\n", b""),
    ],
)
def test_invalid_body_framing_is_rejected(headers: str, body: bytes) -> None:
    with _running(lambda request: PreviewResult()) as server:
        request = (
            f"POST /api/preview HTTP/1.1\r\nHost: 127.0.0.1:{server.server_port}\r\n"
            f"Content-Type: application/json\r\n{headers}\r\n"
        ).encode() + body
        assert b" 400 " in _raw(server, request).split(b"\r\n", 1)[0]


def test_duplicate_host_and_large_headers_are_rejected() -> None:
    with _running(lambda request: PreviewResult()) as server:
        address = f"127.0.0.1:{server.server_port}"
        duplicate = f"GET / HTTP/1.1\r\nHost: {address}\r\nHost: {address}\r\n\r\n".encode()
        assert b" 403 " in _raw(server, duplicate).split(b"\r\n", 1)[0]
        large = f"GET / HTTP/1.1\r\nHost: {address}\r\nX-Large: {'x' * 20000}\r\n\r\n".encode()
        assert b" 431 " in _raw(server, large).split(b"\r\n", 1)[0]


@pytest.mark.parametrize(
    "path", ["/../pyproject.toml", "/%2e%2e/pyproject.toml", "/tutorials/missing.html"]
)
def test_unlisted_assets_cannot_be_read(path: str) -> None:
    with _running(lambda request: PreviewResult()) as server:
        assert _request(server, "GET", path)[0] == HTTPStatus.NOT_FOUND


def test_missing_assets_and_callback_failure_do_not_stop_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing(_name: str) -> bytes:
        raise FileNotFoundError("missing documentation asset")

    def failing(_request: PreviewRequest) -> PreviewResult:
        raise RuntimeError("private submitted contents")

    monkeypatch.setattr(server_module, "asset_bytes", missing)
    with _running(failing) as server:
        assert _request(server, "GET", "/")[0] == HTTPStatus.INTERNAL_SERVER_ERROR
        status, body, _ = _request(
            server, "POST", "/api/preview", "{}", {"Content-Type": "application/json"}
        )
        assert status == HTTPStatus.INTERNAL_SERVER_ERROR
        assert b"private submitted contents" not in body
        assert _request(server, "GET", "/api/catalog")[0] == HTTPStatus.OK


def test_idle_connections_are_bounded_and_closed_at_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(server_module, "MAX_CONNECTIONS", 1)
    monkeypatch.setattr(server_module, "CONNECTION_TIMEOUT", 0.3)
    with _running(lambda request: PreviewResult()) as server:
        idle = socket.create_connection(("127.0.0.1", server.server_port), timeout=3)
        try:
            _until(lambda: bool(server._sockets))
            busy = _raw(server, b"GET / HTTP/1.0\r\n\r\n")
            assert b" 503 " in busy.split(b"\r\n", 1)[0]
            assert idle.recv(1) == b""
        finally:
            idle.close()
        active = socket.create_connection(("127.0.0.1", server.server_port), timeout=3)
        _until(lambda: bool(server._sockets))
    try:
        assert active.recv(1) == b""
    finally:
        active.close()


@pytest.mark.parametrize(
    "name",
    [
        "../train.yaml",
        "/train.yaml",
        "a/../train.yaml",
        "a\\train.yaml",
        "C:train.yaml",
        "a\x00.yaml",
        "hydra/config.yaml",
        "_cy_schemas/train.yaml",
        "a//b.yaml",
        "train.json",
    ],
)
def test_preview_document_names_are_confined(name: str) -> None:
    with pytest.raises(ValueError, match=r"relative|Replacing|\.yaml"):
        document_name(name)


def test_preview_files_are_cleaned_after_failure() -> None:
    roots: list[Path] = []

    def consume() -> None:
        with preview_directory({"model/custom.yaml": "backend: rfdetr\n"}) as root:
            roots.append(root)
            assert (root / "model/custom.yaml").read_text() == "backend: rfdetr\n"
            raise RuntimeError("injected")

    with pytest.raises(RuntimeError, match="injected"):
        consume()
    assert not roots[0].exists()


@pytest.mark.parametrize(
    "documents",
    [
        {"a.yaml": "{}", "a.yaml/b.yaml": "{}"},
        {f"{index}.yaml": "{}" for index in range(33)},
        {"a.yaml": "x" * (MAX_REQUEST_BYTES + 1)},
    ],
)
def test_preview_document_limits_precede_writes(documents: dict[str, str]) -> None:
    with pytest.raises(ValueError, match=r"document|1 MiB"), preview_directory(documents):
        pytest.fail("Invalid inputs reached the directory consumer")


def test_asset_paths_reject_windows_and_posix_traversal() -> None:
    for name in ("../pyproject.toml", "a\\..\\secret", "/etc/passwd", "C:secret"):
        with pytest.raises(ValueError, match="relative paths"):
            asset_bytes(name)


def _workers(source: str) -> PreviewWorkers:
    return PreviewWorkers((sys.executable, "-I", "-c", source))


def test_real_worker_transports_request_and_valid_response() -> None:
    workers = _workers(
        "import json,sys; request=json.load(sys.stdin); "
        "print(json.dumps({'command':request['command']}))"
    )
    try:
        result = workers(PreviewRequest(command="predict"))
        assert result.command == "predict"
        assert not result.errors
        assert not workers._processes
    finally:
        workers.close()


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("print('invalid JSON')", "Invalid preview worker response"),
        ("import sys; sys.stderr.write('injected'); sys.exit(7)", "failed (7): injected"),
        ("import sys; sys.stdout.buffer.write(b'\\xff')", "Invalid preview worker response"),
    ],
)
def test_real_worker_errors_are_returned(source: str, expected: str) -> None:
    workers = _workers(source)
    try:
        assert expected in workers(PreviewRequest()).errors[0]
        assert not workers._processes
    finally:
        workers.close()


def test_worker_timeout_reaps_its_process(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(worker_module, "WORKER_TIMEOUT", 0.3)
    marker = tmp_path / "pid"
    workers = _workers(
        f"import os,time,pathlib; pathlib.Path({str(marker)!r}).write_text(str(os.getpid())); "
        "time.sleep(60)"
    )
    try:
        started = monotonic()
        assert "deadline" in workers(PreviewRequest()).errors[0]
        assert monotonic() - started < 3
        with pytest.raises(ProcessLookupError):
            os.kill(int(marker.read_text()), 0)
        assert not workers._processes
    finally:
        workers.close()


@pytest.mark.parametrize("channel", ["stdout", "stderr"])
def test_worker_output_limits_apply_while_worker_is_running(
    channel: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(worker_module, "MAX_RESPONSE_BYTES", 512)
    monkeypatch.setattr(worker_module, "MAX_DIAGNOSTIC_BYTES", 512)
    workers = _workers(
        f"import sys,time; sys.{channel}.write('x'*1048576); sys.{channel}.flush(); time.sleep(60)"
    )
    try:
        started = monotonic()
        assert "exceeds" in workers(PreviewRequest()).errors[0]
        assert monotonic() - started < 3
        assert not workers._processes
    finally:
        workers.close()


def test_close_stops_owned_workers_preserves_unrelated_process_and_rejects_new_work() -> None:
    unrelated = subprocess.Popen([sys.executable, "-I", "-c", "import time; time.sleep(60)"])
    workers = _workers("import time; time.sleep(60)")
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(workers, PreviewRequest()) for _ in range(2)]
            _until(lambda: len(workers._processes) == 2)
            owned = tuple(workers._processes)
            assert "busy" in workers(PreviewRequest()).errors[0]
            workers.close()
            assert all(future.result(timeout=3).errors for future in futures)
            assert all(process.returncode is not None for process in owned)
            assert not workers._processes
        assert unrelated.poll() is None
        assert "shutting down" in workers(PreviewRequest()).errors[0]
        workers.close()
    finally:
        workers.close()
        unrelated.kill()
        unrelated.wait(timeout=3)


def test_unavailable_worker_executable_is_a_documentation_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    workers = PreviewWorkers(("/nonexistent/cy-docs-worker",))
    try:
        assert "Cannot start preview worker" in workers(PreviewRequest()).errors[0]
        assert not list(tmp_path.iterdir())
    finally:
        workers.close()


def test_successful_worker_reaps_group_children_with_closed_pipes(tmp_path: Path) -> None:
    sentinel = tmp_path / "unowned-effect"
    child = (
        f"import time; from pathlib import Path; time.sleep(0.5); Path({str(sentinel)!r}).touch()"
    )
    code = (
        "import subprocess,sys; "
        f"subprocess.Popen([sys.executable,'-c',{child!r}], "
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
        "print('{\"jobs\":[]}')"
    )
    workers = _workers(code)
    try:
        assert not workers(PreviewRequest()).errors
        Event().wait(0.7)
        assert not sentinel.exists()
    finally:
        workers.close()


def _preview_files_worker(marker: Path, sentinel: Path, outcome: str) -> PreviewWorkers:
    return _workers(
        "import json,os,sys,time\n"
        "from pathlib import Path\n"
        "from clearml_yolo.adapters.documentation.files import preview_directory\n"
        "with preview_directory({'entry.yaml': 'defaults: []\\n'}) as root:\n"
        "    temporary = Path(os.environ['TMPDIR'])\n"
        "    (temporary / 'worker-state').write_text('owned temporary data')\n"
        f"    (root / 'external-link').symlink_to({str(sentinel.parent)!r}, "
        "target_is_directory=True)\n"
        f"    marker = Path({str(marker)!r})\n"
        "    marker.with_suffix('.partial').write_text(json.dumps("
        "{'preview': str(root), 'temporary': str(temporary)}))\n"
        "    marker.with_suffix('.partial').replace(marker)\n"
        f"    outcome = {outcome!r}\n"
        "    if outcome == 'timeout':\n"
        "        time.sleep(60)\n"
        "    elif outcome == 'failure':\n"
        "        sys.exit(7)\n"
        "    elif outcome == 'malformed':\n"
        "        print('invalid JSON')\n"
        "    else:\n"
        "        print('{\"jobs\":[]}')\n"
    )


@pytest.mark.parametrize("outcome", ["success", "failure", "malformed", "timeout"])
def test_parent_cleans_worker_temporary_files_after_every_outcome(
    outcome: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    sandbox = tmp_path / "inherited-temporary"
    sandbox.mkdir()
    sentinel = tmp_path / "unrelated" / "keep"
    sentinel.parent.mkdir()
    sentinel.write_text("preserved")
    monkeypatch.setenv("TMPDIR", str(sandbox))
    environment = dict(os.environ)
    monkeypatch.setattr(worker_module, "WORKER_TIMEOUT", 1)
    marker = tmp_path / "paths.json"
    workers = _preview_files_worker(marker, sentinel, outcome)
    try:
        result = workers(PreviewRequest())
        assert bool(result.errors) is (outcome != "success")
        paths = json.loads(marker.read_text())
        assert not Path(paths["preview"]).exists()
        temporary = Path(paths["temporary"])
        assert temporary != sandbox
        assert Path(paths["preview"]).is_relative_to(temporary)
        assert not temporary.exists()
        assert sentinel.read_text() == "preserved"
        assert dict(os.environ) == environment
    finally:
        workers.close()


def test_close_removes_owned_worker_temporary_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    sandbox = tmp_path / "inherited-temporary"
    sandbox.mkdir()
    sentinel = tmp_path / "unrelated" / "keep"
    sentinel.parent.mkdir()
    sentinel.write_text("preserved")
    monkeypatch.setenv("TMPDIR", str(sandbox))
    marker = tmp_path / "paths.json"
    workers = _preview_files_worker(marker, sentinel, "timeout")
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            result = executor.submit(workers, PreviewRequest())
            _until(marker.exists)
            paths = json.loads(marker.read_text())
            assert (Path(paths["preview"]) / "entry.yaml").is_file()
            workers.close()
            assert not Path(paths["preview"]).exists()
            assert not Path(paths["temporary"]).exists()
            assert result.result(timeout=3).errors
        assert sentinel.read_text() == "preserved"
        assert os.environ["TMPDIR"] == str(sandbox)
    finally:
        workers.close()
