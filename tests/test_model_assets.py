"""Exercise asset HTTP, cache identity and recovery using an isolated local server."""

import hashlib
import io
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar, override

import pytest
import torch

from clearml_yolo.adapters.assets import http, resolver
from clearml_yolo.core.assets import AssetSpec


class _Handler(BaseHTTPRequestHandler):
    payload: ClassVar[bytes] = b""
    hits: ClassVar[list[str]] = []

    def do_GET(self) -> None:
        self.hits.append(self.path)
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/weights.pth")
            self.end_headers()
            return
        if self.path == "/slow":
            time.sleep(0.15)
        if self.path == "/auth" and self.headers.get("Authorization") != "Basic dXNlcjpzZWNyZXQ=":
            self.send_error(401)
            return
        if self.path == "/denied":
            self.send_error(401)
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()
        if self.path == "/interrupted":
            self.wfile.write(self.payload[:10])
        else:
            # The timeout client intentionally closes before the slow response.
            with suppress(BrokenPipeError):
                self.wfile.write(self.payload)

    @override
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
def http_asset() -> Iterator[tuple[str, bytes]]:
    buffer = io.BytesIO()
    torch.save({"weight": torch.ones(2)}, buffer)
    _Handler.payload = buffer.getvalue()
    _Handler.hits = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", _Handler.payload
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _spec(url: str, payload: bytes) -> AssetSpec:
    return AssetSpec(
        backend="fasterrcnn",
        preset="resnet50_fpn",
        filename="weights.pth",
        canonical_url=url,
        checksum=hashlib.sha256(payload).hexdigest(),
        checksum_algorithm="sha256",
        override="model.train.backbone_weights",
    )


def test_proxy_roots_preserve_release_and_vcs_paths() -> None:
    assert (
        resolver.release_proxy_url(
            "https://github.com/org/repo/releases/download/v1/file.pth",
            "https://mirror.example/artifactory/releases/",
        )
        == "https://mirror.example/artifactory/releases/org/repo/releases/download/v1/file.pth"
    )
    assert (
        resolver.source_proxy_url(
            "https://github.com/org/repo/archive/abc.tar.gz",
            "abc",
            "https://mirror.example/artifactory/vcs/",
        )
        == "https://mirror.example/artifactory/api/vcs/downloadCommit/vcs/org/repo/abc?ext=tar.gz"
    )
    assert resolver.release_proxy_url("https://download.pytorch.org/a.pth", "https://m/r") is None


def test_concurrent_download_and_offline_placement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    http_asset: tuple[str, bytes],
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    url, payload = http_asset
    spec = _spec(url + "/weights.pth", payload)
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(lambda _: resolver.resolve_asset(spec), range(4)))
    assert len(_Handler.hits) == 1
    assert all(record.path == records[0].path for record in records)
    assert records[0].path.read_bytes() == payload
    records[0].path.unlink()
    records[0].path.write_bytes(payload)
    monkeypatch.setattr(resolver, "_download", lambda *args: pytest.fail("offline cache hit"))
    assert resolver.resolve_asset(spec).sha256 == hashlib.sha256(payload).hexdigest()


def test_redirect_and_aggregated_failure_details(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    http_asset: tuple[str, bytes],
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    url, payload = http_asset
    assert resolver.resolve_asset(_spec(url + "/redirect", payload)).path.is_file()
    denied = _spec(url + "/denied", payload)
    corrupt = _spec(url + "/corrupt", b"unexpected")
    with pytest.raises(resolver.AssetResolutionError) as caught:
        resolver.resolve_assets((denied, corrupt))
    message = str(caught.value)
    for spec in (denied, corrupt):
        assert spec.canonical_url in message
        assert str(resolver.asset_destination(spec)) in message
        assert spec.override in message


@pytest.mark.parametrize("value", [None, "", " "])
def test_unset_proxy_uses_original_only(value: str | None, monkeypatch: pytest.MonkeyPatch) -> None:
    if value is None:
        monkeypatch.delenv("GHR", raising=False)
    else:
        monkeypatch.setenv("GHR", value)
    spec = _spec("https://github.com/owner/repo/releases/download/tag/asset.pth", b"anything")
    assert resolver.source_urls(spec) == (spec.canonical_url,)


def test_proxy_failure_falls_back_and_redacts_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    http_asset: tuple[str, bytes],
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    root, payload = http_asset
    spec = _spec(root + "/weights.pth", payload)
    monkeypatch.setattr(resolver, "source_urls", lambda _: (root + "/denied", spec.canonical_url))
    assert resolver.resolve_asset(spec).path.read_bytes() == payload
    assert _Handler.hits == ["/denied", "/denied", "/weights.pth"]
    redacted = http.redacted_url("https://user:secret@mirror.example/repo?token=secret")
    assert "secret" not in redacted
    assert "user" not in redacted


def test_invalid_cached_content_is_atomically_replaced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    http_asset: tuple[str, bytes],
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    root, payload = http_asset
    spec = _spec(root + "/weights.pth", payload)
    destination = resolver.asset_destination(spec)
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"corrupt")
    assert resolver.resolve_asset(spec).path.read_bytes() == payload
    assert not list(destination.parent.glob(".asset-*"))


def test_asset_identity_excludes_proxy_and_local_cache_locations() -> None:
    spec = _spec("https://example.org/weight.pth", b"native")
    assert spec.identity == spec.model_copy(update={"cache_candidates": (Path("/cache"),)}).identity
    assert spec.identity != spec.model_copy(update={"revision": "other"}).identity
    assert spec.identity != spec.model_copy(update={"checksum": "0" * 64}).identity


def test_standard_basic_auth_and_local_read_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    http_asset: tuple[str, bytes],
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    root, payload = http_asset
    authenticated = root.replace("http://", "http://user:secret@") + "/auth"
    output = tmp_path / "authenticated.pth"
    http.download(authenticated, output)
    assert output.read_bytes() == payload
    monkeypatch.setattr(http, "_READ_TIMEOUT", 0.03)
    spec = _spec(root + "/slow", payload)
    with pytest.raises(resolver.AssetResolutionError, match="ReadTimeout"):
        resolver.resolve_asset(spec)
    assert not resolver.asset_destination(spec).exists()
    assert not list(resolver.asset_destination(spec).parent.glob(".asset-*"))


def test_interrupted_body_is_never_published(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    http_asset: tuple[str, bytes],
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    root, payload = http_asset
    spec = _spec(root + "/interrupted", payload)
    with pytest.raises(resolver.AssetResolutionError, match="ChunkedEncodingError"):
        resolver.resolve_asset(spec)
    assert not resolver.asset_destination(spec).exists()
    assert not list(resolver.asset_destination(spec).parent.glob(".asset-*"))
