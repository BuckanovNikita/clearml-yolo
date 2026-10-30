"""Artifactory route/auth/fallback checks using loopback HTTP only."""

import base64
import hashlib
import io
import threading
from collections.abc import Iterator
from contextlib import nullcontext
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, override
from urllib.parse import urlsplit

import pytest
import requests
from loguru import logger

from clearml_yolo.adapters.assets import bundles, http, resolver
from clearml_yolo.core.assets import AssetSpec, PreparationFailure, PreparationResult
from clearml_yolo.core.weight_bundles import BundleArchive, BundleAsset, BundleManifest
from clearml_yolo.entrypoints import download_weights

WEIGHT = b"\x80\x02\x8a\x0a\x6c\xfc\x9c\x46\xf9\x20\x6a\xa8\x50\x19payload"


@dataclass
class LocalArtifactory:
    root: str
    routes: dict[str, tuple[int, bytes, dict[str, str]]] = field(default_factory=dict)
    requests: list[tuple[str, str | None]] = field(default_factory=list)


@pytest.fixture
def artifactory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[LocalArtifactory]:
    state = LocalArtifactory(root="")
    original_send = requests.Session.send

    def local_send(
        session: requests.Session, request: requests.PreparedRequest, **kwargs: Any
    ) -> requests.Response:
        assert request.url is not None
        assert urlsplit(request.url).hostname in {"127.0.0.1", "localhost"}, (
            "These checks permit loopback HTTP only"
        )
        return original_send(session, request, **kwargs)

    monkeypatch.setattr(requests.Session, "send", local_send)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            state.requests.append((self.path, self.headers.get("Authorization")))
            status, body, headers = state.routes.get(self.path, (404, b"missing", {}))
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        @override
        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state.root = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    credentials = tmp_path / "http.netrc"
    credentials.write_text("machine 127.0.0.1 login mirror-user password mirror-password\n")
    credentials.chmod(0o600)
    monkeypatch.setenv("NETRC", str(credentials))
    monkeypatch.setenv("HF_TOKEN", "hub-token-must-stay-at-hub")
    monkeypatch.setattr(bundles, "write_path", lambda path: path)
    monkeypatch.setattr(bundles, "cy_home", lambda: tmp_path)
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _bundle() -> tuple[AssetSpec, BundleManifest, bytes]:
    import tarfile

    spec = AssetSpec(
        backend="example",
        preset="small",
        filename="model.pt",
        canonical_url="https://github.com/upstream/models/releases/download/v1/model.pt",
        override="model.weights",
    )
    member = f"assets/{spec.identity}/model.pt"
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        entry = tarfile.TarInfo(member)
        entry.size = len(WEIGHT)
        archive.addfile(entry, io.BytesIO(WEIGHT))
    payload = stream.getvalue()
    manifest = BundleManifest(
        schema_version=1,
        repository="BuckanovNikita/clearml-yolo",
        release_tag="weights-2026-10-29",
        archives=(
            BundleArchive(
                name="weights.tar", size=len(payload), sha256=hashlib.sha256(payload).hexdigest()
            ),
        ),
        assets=(
            BundleAsset(
                identity=spec.identity,
                backend=spec.backend,
                preset=spec.preset,
                filename=spec.filename,
                source_url=spec.canonical_url,
                source_revision=None,
                kind="weights",
                archive="weights.tar",
                member=member,
                size=len(WEIGHT),
                sha256=hashlib.sha256(WEIGHT).hexdigest(),
                hub=None,
            ),
        ),
    )
    return spec, manifest, payload


def _own_path() -> str:
    return "/BuckanovNikita/clearml-yolo/releases/download/weights-2026-10-29/weights.tar"


def test_own_bundle_uses_prefixed_ghr_and_netrc_without_hub_token(
    artifactory: LocalArtifactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, manifest, payload = _bundle()
    path = "/artifactory/github-files" + _own_path()
    artifactory.routes[path] = (200, payload, {})
    monkeypatch.setenv("GHR", artifactory.root + "/artifactory/github-files/")
    monkeypatch.setenv("GH", artifactory.root + "/artifactory/github-vcs/")
    bundles.seed_bundle_asset(spec, manifest)
    assert resolver.asset_destination(spec).read_bytes() == WEIGHT
    expected_auth = "Basic " + base64.b64encode(b"mirror-user:mirror-password").decode()
    assert artifactory.requests == [(path, expected_auth)]
    assert manifest.assets[0].source_url == spec.canonical_url
    result = resolver.resolve_asset(spec)
    assert result.canonical_url == spec.canonical_url


@pytest.mark.parametrize("failure", ["unauthorized", "unavailable", "corrupt", "malformed"])
def test_own_bundle_proxy_failure_recovers_at_original_release(
    artifactory: LocalArtifactory,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    spec, manifest, payload = _bundle()
    path = "/artifactory/github-releases" + _own_path()
    status = 401 if failure == "unauthorized" else 503
    artifactory.routes[path] = (
        (200, b"corrupt archive", {}) if failure == "corrupt" else (status, b"denied", {})
    )
    artifactory.routes["/original-release"] = (200, payload, {})
    root = (
        "http://[malformed"
        if failure == "malformed"
        else (artifactory.root + "/artifactory/github-releases")
    )
    monkeypatch.setenv("GHR", root)
    original = "https://github.com" + _own_path()
    attempts: list[str] = []

    def download(url: str, target: Path, **kwargs: object) -> None:
        attempts.append(url)
        if url == original:
            http.download(artifactory.root + "/original-release", target)
        else:
            assert urlsplit(url).hostname == "127.0.0.1", "Only loopback requests permitted"
            http.download(url, target)

    monkeypatch.setattr(bundles, "download", download)
    bundles.seed_bundle_asset(spec, manifest)
    if failure == "malformed":
        # Invalid mirror configuration is detached; normal resolver recovery is retained.
        assert not resolver.asset_destination(spec).exists()
        assert attempts == []
        artifactory.routes["/native-upstream"] = (200, WEIGHT, {})

        def native_download(url: str, target: Path) -> None:
            assert url == spec.canonical_url
            http.download(artifactory.root + "/native-upstream", target)

        monkeypatch.setattr(resolver, "_download", native_download)
        restored = resolver.resolve_asset(spec)
        assert restored.path.read_bytes() == WEIGHT
        assert restored.canonical_url == spec.canonical_url
    else:
        assert resolver.asset_destination(spec).read_bytes() == WEIGHT
        assert attempts[-1] == original
        assert len(attempts) == 3
    assert spec.canonical_url == "https://github.com/upstream/models/releases/download/v1/model.pt"


def test_gh_vcs_downloadcommit_route_retains_original_source(
    artifactory: LocalArtifactory, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    revision = "a" * 40
    spec = AssetSpec(
        backend="deimv2",
        preset="source",
        filename="source.tar.gz",
        kind="deim-source",
        canonical_url=f"https://github.com/Intellindust-AI-Lab/DEIMv2/archive/{revision}.tar.gz",
        revision=revision,
        override="model.source_dir",
    )
    monkeypatch.setenv("GH", artifactory.root + "/artifactory/github-vcs/")
    expected = (
        "/artifactory/api/vcs/downloadCommit/github-vcs/Intellindust-AI-Lab/DEIMv2/"
        f"{revision}?ext=tar.gz"
    )
    artifactory.routes[expected] = (200, b"source transport fixture", {})
    proxy, original = resolver.source_urls(spec)
    assert proxy == artifactory.root + expected
    assert original == spec.canonical_url
    target = tmp_path / "source.tar.gz"
    http.download(proxy, target)
    assert target.read_bytes() == b"source transport fixture"
    assert artifactory.requests[0][0] == expected
    assert artifactory.requests[0][1] is not None
    assert spec.revision == revision


def test_native_upstream_release_still_uses_ghr(
    artifactory: LocalArtifactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, _, _ = _bundle()
    monkeypatch.setenv("GHR", artifactory.root + "/artifactory/github-releases")
    path = "/artifactory/github-releases/upstream/models/releases/download/v1/model.pt"
    artifactory.routes[path] = (200, WEIGHT, {})
    result = resolver.resolve_asset(spec)
    assert result.path.read_bytes() == WEIGHT
    assert result.canonical_url == spec.canonical_url
    assert artifactory.requests[0][0] == path


def test_netrc_auth_is_not_forwarded_to_redirect_host(
    artifactory: LocalArtifactory, tmp_path: Path
) -> None:
    redirected = artifactory.root.replace("127.0.0.1", "localhost") + "/public"
    artifactory.routes["/private"] = (302, b"", {"Location": redirected})
    artifactory.routes["/public"] = (200, WEIGHT, {})
    target = tmp_path / "download.pt"
    http.download(artifactory.root + "/private", target)
    assert artifactory.requests[0][1] is not None
    assert artifactory.requests[1] == ("/public", None)
    assert target.read_bytes() == WEIGHT


def test_mirror_failure_warning_never_contains_transport_secrets(
    artifactory: LocalArtifactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, manifest, _ = _bundle()
    monkeypatch.setenv("GHR", "https://username:password@private.example/repo?token=secret")
    messages: list[str] = []
    sink = logger.add(lambda message: messages.append(str(message)))

    def unavailable(url: str, target: Path, **kwargs: object) -> None:
        raise OSError(f"private transport: {url}")

    monkeypatch.setattr(bundles, "download", unavailable)
    try:
        bundles.seed_bundle_asset(spec, manifest)
    finally:
        logger.remove(sink)
    assert messages
    assert all(
        secret not in "".join(messages)
        for secret in (
            "username",
            "password",
            "private.example",
            "token=secret",
            "hub-token-must-stay-at-hub",
        )
    )


@pytest.mark.parametrize("failed", [False, True])
def test_manual_failure_prints_static_setup_and_retry_only_when_needed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], failed: bool
) -> None:
    result = PreparationResult(
        fingerprint="fixture",
        failures=(PreparationFailure(selection="example", message="unavailable"),)
        if failed
        else (),
    )
    monkeypatch.setattr(download_weights, "runtime_environment", nullcontext)
    monkeypatch.setattr(download_weights, "prepare_catalogue", lambda *, automatic: result)
    monkeypatch.setenv("GHR", "https://private-user:private-password@private.example/repo")
    monkeypatch.setenv("GH", "https://private.example/secret-vcs")
    monkeypatch.setenv("HF_TOKEN", "private-hub-token")
    if failed:
        with pytest.raises(SystemExit) as exit_info:
            download_weights.main([])
        assert exit_info.value.code == 1
    else:
        download_weights.main([])
    output = capsys.readouterr().out
    assert "export GHR=" in output if failed else "export GHR=" not in output
    if failed:
        assert "export GH=" not in output
        assert "export HF_ENDPOINT=" not in output
        assert "Files remote of https://github.com" in output
        assert "GH (VCS) and HF_ENDPOINT apply only to standalone" in output
        assert "CY_WEIGHTS_DOWNLOAD_TIMEOUT=3600" in output
        assert "pinned release only" in output
        assert "per-host ~/.netrc" in output
        assert "Retry: cy-download-weights" in output
    assert all(
        secret not in output
        for secret in (
            "private-user",
            "private-password",
            "private.example",
            "private-hub-token",
            "secret-vcs",
        )
    )
