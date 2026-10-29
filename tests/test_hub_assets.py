"""Native Hub representation, provenance, reuse and endpoint credential boundaries."""

import hashlib
import importlib
import io
import json
import logging  # noqa: TID251 -- exercise the SDK's real stdlib logging boundary
import sys
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
import torch
from huggingface_hub import constants, try_to_load_from_cache
from safetensors.torch import save_file

from clearml_yolo.adapters.torchvision import assets
from clearml_yolo.core.assets import AssetSpec, HubAsset

_COMMIT = "a" * 40


def _terminal_streams(
    monkeypatch: pytest.MonkeyPatch, terminal: bool
) -> tuple[io.StringIO, io.StringIO]:
    stdout, stderr = io.StringIO(), io.StringIO()
    for stream in (stdout, stderr):
        monkeypatch.setattr(stream, "isatty", lambda: terminal)
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)
    return stdout, stderr


def _exercise_native_xet_progress(progress_classes: list[type[Any]]) -> None:
    xet_progress = importlib.import_module("huggingface_hub.utils._xet_progress_reporting")
    # The SDK passes the same public hook to native Xet's dual-bar reporter.
    # Exercise its real update/close protocol with the classes received by both
    # actual Hub downloads, including terminal-enabled global progress settings.
    for progress_class in progress_classes:
        with xet_progress.XetDownloadProgressReporter(
            reconstruction_desc="weights?signature=NATIVE_XET_PROGRESS_SECRET",
            transfer_desc="transfer?signature=NATIVE_XET_PROGRESS_SECRET",
            total=10,
            log_level=logging.INFO,
            tqdm_class=progress_class,
        ) as reporter:
            assert reporter.reconstruction_bar.disable is True
            assert reporter.transfer_bar.disable is True
            reporter.update_progress(
                SimpleNamespace(
                    total_bytes_completed=10,
                    total_transfer_bytes_completed=10,
                    total_bytes_completion_rate=100.0,
                    total_transfer_bytes_completion_rate=100.0,
                    total_bytes=10,
                )
            )


def _signed_cdn_response(
    contents: dict[str, bytes], requested: list[tuple[str, str]], request: Any
) -> Any:
    httpx = importlib.import_module("httpx2")
    filename = request.url.path.rsplit("/", 1)[-1]
    requested.append((request.method, str(request.url)))
    data = contents[filename]
    if request.method == "HEAD":
        return httpx.Response(
            302,
            headers={
                "x-repo-commit": _COMMIT,
                "x-linked-etag": hashlib.sha256(data).hexdigest(),
                "x-linked-size": str(len(data)),
                "location": f"https://cdn.example/{filename}?signature=DOWNLOAD_SIGNATURE_SECRET",
            },
        )
    return httpx.Response(200, content=data)


@pytest.mark.parametrize("download_warning", [False, True], ids=["http-backoff", "file-download"])
def test_real_sdk_transport_diagnostics_are_redacted_before_console_and_capture(
    download_warning: bool,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    transport = importlib.import_module("huggingface_hub.utils._http")
    downloads = importlib.import_module("huggingface_hub.file_download")
    httpx = importlib.import_module("httpx2")
    console = io.StringIO()
    handler = logging.StreamHandler(console)
    sdk_logger = logging.getLogger("huggingface_hub")
    source_logger = logging.getLogger(
        downloads.__name__ if download_warning else transport.__name__
    )
    original_filters = tuple(source_logger.filters)
    url = "https://user:HF_URL_SECRET@example.test/model?token=HF_QUERY_SECRET"
    error = httpx.ConnectError("HF_DIAGNOSTIC_SECRET")

    if download_warning:
        stream = MagicMock()
        stream.__enter__.side_effect = error
        monkeypatch.setattr(downloads, "http_stream_backoff", lambda **kwargs: stream)
        operation = partial(downloads.http_get, url, io.BytesIO(), _nb_retries=0)
    else:
        client = MagicMock()
        client.request.side_effect = error
        monkeypatch.setattr(transport, "get_session", lambda: client)
        monkeypatch.setattr(transport, "close_session", lambda: None)
        operation = partial(transport.http_backoff, "HEAD", url, max_retries=0)

    sdk_logger.addHandler(handler)
    try:
        with pytest.raises(hub.HubResolutionError):
            hub._sdk_call(operation)
    finally:
        sdk_logger.removeHandler(handler)
        handler.close()

    captured = "\n".join(repr(record.__dict__) for record in caplog.records)
    assert caplog.records, "The SDK warning must remain observable after sanitization"
    for secret in ("HF_URL_SECRET", "HF_QUERY_SECRET", "HF_DIAGNOSTIC_SECRET"):
        assert secret not in captured
        assert secret not in console.getvalue()
    assert "redacted" in caplog.text
    assert tuple(source_logger.filters) == original_filters


def test_real_http_client_request_and_signed_redirect_diagnostics_are_private(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    sdk_http = importlib.import_module("huggingface_hub.utils._http")
    httpx = importlib.import_module("httpx2")
    console = io.StringIO()
    handler = logging.StreamHandler(console)
    root_logger = logging.getLogger()
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="huggingface_hub")
    monkeypatch.setattr(constants, "HF_DEBUG", True)
    requested: list[str] = []

    def response(request: Any) -> Any:
        requested.append(str(request.url))
        if request.url.host == "origin.example":
            return httpx.Response(
                302,
                headers={
                    "location": "https://cdn.example/weights?signature=SIGNED_REDIRECT_SECRET"
                },
            )
        return httpx.Response(200, content=b"checkpoint")

    with httpx.Client(
        transport=httpx.MockTransport(response),
        follow_redirects=True,
        event_hooks={"request": [sdk_http.hf_request_event_hook]},
        trust_env=False,
    ) as client:
        monkeypatch.setattr(sdk_http, "get_session", lambda: client)
        root_logger.addHandler(handler)
        try:
            result = hub._sdk_call(
                partial(
                    sdk_http.http_backoff,
                    "GET",
                    "https://origin.example/weights?token=REQUEST_QUERY_SECRET",
                    headers={"authorization": "Bearer REQUEST_HEADER_SECRET"},
                    max_retries=0,
                )
            )
        finally:
            root_logger.removeHandler(handler)
            handler.close()
    assert result.status_code == 200
    assert len(requested) == 2
    assert any(record.name == "httpx2" for record in caplog.records)
    for secret in ("REQUEST_QUERY_SECRET", "REQUEST_HEADER_SECRET", "SIGNED_REDIRECT_SECRET"):
        assert secret not in repr([record.__dict__ for record in caplog.records])
        assert secret not in console.getvalue()


@pytest.mark.parametrize("http2", [False, True], ids=["http11", "http2"])
def test_real_native_transport_header_debug_diagnostics_are_private(
    http2: bool,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    sdk_http = importlib.import_module("huggingface_hub.utils._http")
    httpx = importlib.import_module("httpx2")
    httpcore = importlib.import_module("httpcore2")
    if http2:
        h2_connection = importlib.import_module("h2.connection")
        h2_config = importlib.import_module("h2.config")
        server = h2_connection.H2Connection(config=h2_config.H2Configuration(client_side=False))
        peer = h2_connection.H2Connection()
        peer.initiate_connection()
        peer.send_headers(
            1,
            [
                (":method", "GET"),
                (":scheme", "https"),
                (":authority", "origin.example"),
                (":path", "/weights"),
            ],
            end_stream=True,
        )
        server.initiate_connection()
        server.receive_data(peer.data_to_send())
        server.send_headers(
            1,
            [
                (":status", "200"),
                ("x-native-secret", "RESPONSE_HEADER_SECRET"),
            ],
            end_stream=True,
        )
        wire_response = server.data_to_send()
    else:
        wire_response = (
            b"HTTP/1.1 200 OK\r\nx-native-secret: RESPONSE_HEADER_SECRET\r\n"
            b"content-length: 0\r\n\r\n"
        )
    transport = httpx.HTTPTransport(http2=http2)
    transport._pool = httpcore.ConnectionPool(
        http2=http2, network_backend=httpcore.MockBackend([wire_response], http2=http2)
    )
    caplog.set_level(logging.DEBUG)
    with httpx.Client(transport=transport, trust_env=False) as client:
        monkeypatch.setattr(sdk_http, "get_session", lambda: client)
        result = hub._sdk_call(
            partial(
                sdk_http.http_backoff,
                "GET",
                "https://origin.example/weights?token=NATIVE_QUERY_SECRET",
                headers={"authorization": "Bearer NATIVE_HEADER_SECRET"},
                max_retries=0,
            )
        )
    assert result.status_code == 200
    assert any(record.name.startswith("httpcore2.") for record in caplog.records)
    if http2:
        assert any(record.name.startswith("hpack.") for record in caplog.records)
    captured = repr([record.__dict__ for record in caplog.records])
    for secret in ("NATIVE_QUERY_SECRET", "NATIVE_HEADER_SECRET", "RESPONSE_HEADER_SECRET"):
        assert secret not in captured


@pytest.mark.parametrize("terminal", [False, True], ids=["redirected-output", "tty-output"])
def test_public_hub_preparation_keeps_real_sdk_metadata_and_download_diagnostics_private(
    terminal: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    sdk_http = importlib.import_module("huggingface_hub.utils._http")
    httpx = importlib.import_module("httpx2")
    progress = importlib.import_module("huggingface_hub.utils.tqdm")
    progress_classes: list[type[Any]] = []
    native_download = hub.hf_hub_download

    def observed_download(**kwargs: Any) -> Any:
        progress_classes.append(kwargs["tqdm_class"])
        return native_download(**kwargs)

    monkeypatch.setattr(hub, "hf_hub_download", observed_download)
    payload = tmp_path / "weight.safetensors"
    save_file({"weight": torch.ones(1)}, payload)
    contents = {
        "model.safetensors": payload.read_bytes(),
        "config.json": json.dumps({"architecture": "convnext_tiny", "pretrained_cfg": {}}).encode(),
    }
    endpoint = "https://mirror.example/artifactory/api/huggingfaceml/models"
    monkeypatch.setattr(constants, "ENDPOINT", endpoint)
    monkeypatch.setattr(constants, "HF_HUB_DISABLE_IMPLICIT_TOKEN", False)
    monkeypatch.setattr(constants, "HF_DEBUG", True)
    monkeypatch.setenv("HF_TOKEN", "HF_AUTHORIZATION_SECRET")
    monkeypatch.setattr(constants, "HF_HUB_DISABLE_PROGRESS_BARS", False)
    monkeypatch.setattr(progress, "HF_HUB_DISABLE_PROGRESS_BARS", False)
    progress_flags = (
        constants.HF_HUB_DISABLE_PROGRESS_BARS,
        progress.HF_HUB_DISABLE_PROGRESS_BARS,
        dict(progress.progress_bar_states),
    )
    stdout, stderr = _terminal_streams(monkeypatch, terminal)
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="huggingface_hub")
    requested: list[tuple[str, str]] = []

    response = partial(_signed_cdn_response, contents, requested)

    console = io.StringIO()
    handler = logging.StreamHandler(console)
    root_logger = logging.getLogger()
    with httpx.Client(
        transport=httpx.MockTransport(response),
        event_hooks={"request": [sdk_http.hf_request_event_hook]},
        trust_env=False,
    ) as client:
        monkeypatch.setattr(sdk_http, "get_session", lambda: client)
        root_logger.addHandler(handler)
        try:
            result = hub.resolve_hub_asset(_spec(tmp_path / "hub"))
        finally:
            root_logger.removeHandler(handler)
            handler.close()
    assert result.path.read_bytes() == contents["model.safetensors"]
    assert (result.path.parent / "config.json").read_bytes() == contents["config.json"]
    assert any(method == "GET" and "signature=" in url for method, url in requested)
    assert any(
        method == "HEAD" and f"/resolve/{_COMMIT}/config.json" in url for method, url in requested
    )
    assert len(progress_classes) == 2, (
        "Both the weight and config need per-call progress protection"
    )
    _exercise_native_xet_progress(progress_classes)
    for secret in (
        "HF_AUTHORIZATION_SECRET",
        "DOWNLOAD_SIGNATURE_SECRET",
        "NATIVE_XET_PROGRESS_SECRET",
    ):
        assert secret not in repr([record.__dict__ for record in caplog.records])
        assert secret not in console.getvalue()
        assert secret not in stdout.getvalue()
        assert secret not in stderr.getvalue()
    assert (
        constants.HF_HUB_DISABLE_PROGRESS_BARS,
        progress.HF_HUB_DISABLE_PROGRESS_BARS,
        dict(progress.progress_bar_states),
    ) == progress_flags


def test_sdk_diagnostics_discard_auxiliary_record_secrets_and_keep_existing_filters(
    caplog: pytest.LogCaptureFixture,
) -> None:
    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    logger = logging.getLogger("huggingface_hub.file_download")
    original_filter = logging.Filter()
    logger.addFilter(original_filter)
    original_filters = tuple(logger.filters)

    def operation() -> None:
        error = RuntimeError("EXCEPTION_SECRET")
        logger.warning(
            "FORMAT_SECRET %s",
            "ARG_SECRET",
            exc_info=(type(error), error, None),
            stack_info=True,
            extra={"request_url": "EXTRA_SECRET"},
        )

    try:
        hub._sdk_call(operation)
        assert tuple(logger.filters) == original_filters
    finally:
        logger.removeFilter(original_filter)
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert "SECRET" not in repr(record.__dict__)
    assert record.args == ()
    assert record.exc_info is None
    assert record.exc_text is None
    assert record.stack_info is None


@pytest.mark.parametrize(
    "logger_name",
    [
        "huggingface_hub.utils._http",
        "httpx2",
        "httpcore2.http11",
        "hpack.hpack",
    ],
)
def test_overlapping_sdk_calls_preserve_other_threads_and_restore_logger_configuration(
    logger_name: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    logger = logging.getLogger(logger_name)
    unrelated = logging.getLogger("cy007-unrelated-diagnostics")
    first_entered, second_entered, first_finished = Event(), Event(), Event()
    configuration = (
        logger.level,
        tuple(logger.handlers),
        tuple(logger.filters),
        logger.propagate,
        logger.disabled,
    )

    def first() -> None:
        first_entered.set()
        assert second_entered.wait(5)
        logger.warning("FIRST_PROTECTED_SECRET")
        unrelated.warning("other logger remains visible in the protected thread")

    def second() -> None:
        second_entered.set()
        assert first_finished.wait(5)
        logger.warning("SECOND_PROTECTED_SECRET")

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_call = pool.submit(hub._sdk_call, first)
        assert first_entered.wait(5)
        second_call = pool.submit(hub._sdk_call, second)
        assert second_entered.wait(5)
        logger.warning("same SDK logger remains visible in an unrelated thread")
        assert logger.level == configuration[0]
        assert tuple(logger.handlers) == configuration[1]
        assert logger.propagate == configuration[3]
        assert logger.disabled == configuration[4]
        try:
            first_call.result(timeout=5)
        finally:
            first_finished.set()
        second_call.result(timeout=5)

    assert "FIRST_PROTECTED_SECRET" not in caplog.text
    assert "SECOND_PROTECTED_SECRET" not in caplog.text
    assert "same SDK logger remains visible in an unrelated thread" in caplog.text
    assert "other logger remains visible in the protected thread" in caplog.text
    assert (
        logger.level,
        tuple(logger.handlers),
        tuple(logger.filters),
        logger.propagate,
        logger.disabled,
    ) == configuration


def _spec(root: Path, **updates: Any) -> AssetSpec:
    return AssetSpec(
        backend="fasterrcnn",
        preset="convnext_tiny",
        filename="original.pth",
        canonical_url="https://original.example/original.pth",
        revision="timm:test",
        override="model.train.backbone_weights",
        hub=HubAsset(repository="timm/example", cache_dir=root),
        **updates,
    )


def _cache(root: Path, filename: str, *, commit: str = _COMMIT) -> Path:
    repo = root / "models--timm--example"
    path = repo / "snapshots" / commit / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        path.unlink()
    if filename.endswith("safetensors"):
        save_file({"weight": torch.ones(1)}, path)
    elif filename == "config.json":
        path.write_text(json.dumps({"architecture": "convnext_tiny", "pretrained_cfg": {}}))
    else:
        torch.save({"weight": torch.ones(1)}, path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    blob = repo / "blobs" / digest
    blob.parent.mkdir(exist_ok=True)
    path.replace(blob)
    path.symlink_to(blob)
    reference = repo / "refs" / "main"
    reference.parent.mkdir(exist_ok=True)
    reference.write_text(commit)
    return path


@pytest.mark.parametrize("preset", ["convnext_tiny", "swin_tiny", "dinov2_small"])
def test_discovery_tracks_native_hf_source(preset: str) -> None:
    spec = assets.pretrained_asset(preset)
    assert spec.hub is not None, "native timm selects HF before its original URL"
    assert spec.hub.repository == "timm/" + assets.TIMM_MODELS[preset]
    assert spec.hub.cache_dir == Path(constants.HF_HUB_CACHE).expanduser().resolve()


def test_native_valid_cache_uses_safe_representation_and_actual_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    _cache(tmp_path, "pytorch_model.bin")
    safe = _cache(tmp_path, "model.safetensors")
    _cache(tmp_path, "config.json")
    monkeypatch.setattr(hub, "hf_hub_download", lambda **kw: pytest.fail("valid offline cache"))
    result = hub.resolve_hub_asset(_spec(tmp_path))
    assert result.path == safe
    assert result.revision == _COMMIT
    assert result.canonical_url == (
        f"https://huggingface.co/timm/example/resolve/{_COMMIT}/model.safetensors"
    )


def test_configured_artifactory_precedes_upstream_without_forwarding_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    endpoint = "https://artifactory.example/artifactory/api/huggingfaceml/models"
    monkeypatch.setattr(constants, "ENDPOINT", endpoint)
    calls: list[dict[str, Any]] = []

    def download(**kwargs: Any) -> str:
        calls.append(kwargs)
        if kwargs["endpoint"] == endpoint:
            raise OSError("secret mirror token must never appear in reports")
        return str(_cache(tmp_path, kwargs["filename"]))

    monkeypatch.setattr(hub, "hf_hub_download", download)
    result = hub.resolve_hub_asset(_spec(tmp_path))
    assert result.path.name == "model.safetensors"
    assert calls[0]["endpoint"] == endpoint
    assert calls[0]["token"] is None
    upstream = [call for call in calls if call["endpoint"] == "https://huggingface.co"]
    assert upstream
    assert all(call["token"] is False for call in upstream)
    assert any(call["filename"] == "config.json" for call in upstream)
    assert endpoint == constants.ENDPOINT


def test_corrupt_blob_is_forced_to_download_and_cannot_be_reused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    safe = _cache(tmp_path, "model.safetensors")
    safe.write_bytes(b"corrupt")
    calls: list[dict[str, Any]] = []

    def download(**kwargs: Any) -> str:
        calls.append(kwargs)
        # A download returning the old corrupt cache must not count as recovery.
        return str(safe)

    monkeypatch.setattr(hub, "hf_hub_download", download)
    with pytest.raises(hub.HubResolutionError):
        hub.resolve_hub_asset(_spec(tmp_path))
    assert any(call.get("force_download") for call in calls)


def test_blob_hash_mismatch_is_rejected_even_when_checkpoint_structure_is_valid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    safe = _cache(tmp_path, "model.safetensors")
    save_file({"weight": torch.zeros(2)}, safe.resolve())
    monkeypatch.setattr(hub, "hf_hub_download", lambda **kw: str(safe))
    with pytest.raises(hub.HubResolutionError):
        hub.resolve_hub_asset(_spec(tmp_path))


def test_corrupt_preferred_safe_file_cannot_be_hidden_by_a_valid_binary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    safe = _cache(tmp_path, "model.safetensors")
    safe.write_bytes(b"corrupt")
    binary = _cache(tmp_path, "pytorch_model.bin")
    _cache(tmp_path, "config.json")
    monkeypatch.setattr(
        hub,
        "hf_hub_download",
        lambda **kw: str(safe if kw["filename"].endswith("safetensors") else binary),
    )
    with pytest.raises(hub.HubResolutionError):
        hub.resolve_hub_asset(_spec(tmp_path))


def test_corrupt_cached_config_is_repaired_without_redownloading_weights(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    safe = _cache(tmp_path, "model.safetensors")
    config = _cache(tmp_path, "config.json")
    config.write_bytes(b"broken config")
    calls: list[dict[str, Any]] = []

    def download(**kwargs: Any) -> str:
        calls.append(kwargs)
        return str(_cache(tmp_path, kwargs["filename"]))

    monkeypatch.setattr(hub, "hf_hub_download", download)
    assert hub.resolve_hub_asset(_spec(tmp_path)).path == safe
    assert calls
    assert all(call["filename"] == "config.json" for call in calls)
    assert calls[0]["force_download"] is True


def test_failed_config_download_stays_incomplete_until_manual_retry_repairs_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    calls: list[dict[str, Any]] = []
    config_available = False

    def download(**kwargs: Any) -> str:
        calls.append(kwargs)
        if kwargs["filename"] == "config.json" and not config_available:
            raise OSError("config temporarily unavailable")
        if kwargs["filename"] == "pytorch_model.bin":
            raise OSError("only the native safe representation is published")
        return str(_cache(tmp_path, kwargs["filename"]))

    monkeypatch.setattr(hub, "hf_hub_download", download)
    spec = _spec(tmp_path)
    with pytest.raises(hub.HubResolutionError):
        hub.resolve_hub_asset(spec)
    safe = try_to_load_from_cache("timm/example", "model.safetensors", cache_dir=tmp_path)
    assert isinstance(safe, str)
    weight_stat = Path(safe).stat()
    first_attempt_calls = len(calls)

    # A second manual pass must continue to report the missing config rather
    # than treat the weight left by the first partial attempt as complete.
    with pytest.raises(hub.HubResolutionError):
        hub.resolve_hub_asset(spec)

    config_available = True
    result = hub.resolve_hub_asset(spec)
    assert result.path == Path(safe)
    assert Path(safe).stat().st_ino == weight_stat.st_ino
    assert Path(safe).stat().st_mtime_ns == weight_stat.st_mtime_ns
    assert all(call["filename"] == "config.json" for call in calls[first_attempt_calls:])
    assert all(call["revision"] == _COMMIT for call in calls[first_attempt_calls:])
    assert (result.path.parent / "config.json").is_file()


def test_historical_weight_only_cache_repairs_missing_config_without_weight_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    safe = _cache(tmp_path, "model.safetensors")
    calls: list[dict[str, Any]] = []

    def download(**kwargs: Any) -> str:
        calls.append(kwargs)
        assert kwargs["filename"] == "config.json"
        assert kwargs["revision"] == _COMMIT
        return str(_cache(tmp_path, kwargs["filename"]))

    monkeypatch.setattr(hub, "hf_hub_download", download)
    assert hub.resolve_hub_asset(_spec(tmp_path)).path == safe
    assert len(calls) == 1


def test_incompatible_legacy_checkpoint_is_not_given_native_hf_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from huggingface_hub import HfFileMetadata

    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    legacy = tmp_path / "legacy.pth"
    torch.save({"weight": torch.zeros(2)}, legacy)
    root = tmp_path / "native"
    metadata = HfFileMetadata(
        commit_hash=_COMMIT,
        etag="f" * 64,
        location="https://signed.example/blob",
        size=legacy.stat().st_size,
        xet_file_data=None,
    )
    monkeypatch.setattr(hub, "get_hf_file_metadata", lambda *a, **kw: metadata)
    monkeypatch.setattr(hub, "hf_hub_download", lambda **kw: str(_cache(root, kw["filename"])))
    result = hub.resolve_hub_asset(_spec(root, cache_candidates=(legacy,)))
    assert result.path.suffix == ".safetensors"
    assert result.path.read_bytes() != legacy.read_bytes()
    assert not (root / "models--timm--example" / "blobs" / ("f" * 64)).exists()


def test_failure_report_does_not_include_sdk_exception_or_endpoint_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    monkeypatch.setattr(constants, "ENDPOINT", "https://name:password@example.org/hf?token=secret")

    def unavailable(**kwargs: Any) -> str:
        raise OSError("private-token-and-signed-url")

    monkeypatch.setattr(hub, "hf_hub_download", unavailable)
    with pytest.raises(hub.HubResolutionError) as failure:
        hub.resolve_hub_asset(_spec(tmp_path))
    assert "password" not in str(failure.value)
    assert "secret" not in str(failure.value)
    assert "private-token" not in str(failure.value)
    assert "timm/example" in str(failure.value)


def test_lock_failure_uses_the_same_sanitized_hub_error_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from filelock import Timeout

    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")

    def locked(*args: Any, **kwargs: Any) -> Any:
        raise Timeout("private-lock-details")

    monkeypatch.setattr(hub, "FileLock", locked)
    with pytest.raises(hub.HubResolutionError) as failure:
        hub.resolve_hub_asset(_spec(tmp_path))
    assert "private-lock-details" not in str(failure.value)


def test_cached_binary_without_safe_alternative_remains_usable_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    binary = _cache(tmp_path, "pytorch_model.bin")
    _cache(tmp_path, "config.json")
    monkeypatch.setattr(hub, "hf_hub_download", lambda **kw: pytest.fail("cached binary"))
    assert hub.resolve_hub_asset(_spec(tmp_path)).path == binary


def test_compatible_legacy_cache_promotes_using_real_hub_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from huggingface_hub import HfFileMetadata

    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    legacy = tmp_path / "legacy.safetensors"
    save_file({"weight": torch.ones(1)}, legacy)
    digest = hashlib.sha256(legacy.read_bytes()).hexdigest()
    root = tmp_path / "native"
    metadata = HfFileMetadata(
        commit_hash=_COMMIT,
        etag=digest,
        location="https://signed.example/blob",
        size=legacy.stat().st_size,
        xet_file_data=None,
    )
    config_calls: list[dict[str, Any]] = []

    def download_config(**kwargs: Any) -> str:
        config_calls.append(kwargs)
        assert kwargs["filename"] == "config.json", "compatible legacy weights need no download"
        assert kwargs["revision"] == _COMMIT
        return str(_cache(root, "config.json"))

    monkeypatch.setattr(hub, "get_hf_file_metadata", lambda *args, **kwargs: metadata)
    monkeypatch.setattr(hub, "hf_hub_download", download_config)
    result = hub.resolve_hub_asset(_spec(root, cache_candidates=(legacy,)))
    cached = try_to_load_from_cache("timm/example", "model.safetensors", cache_dir=root)
    assert isinstance(cached, str)
    assert result.path == Path(cached)
    assert result.path.read_bytes() == legacy.read_bytes()
    assert legacy.is_file()
    assert result.revision == _COMMIT
    assert len(config_calls) == 1
    assert (result.path.parent / "config.json").is_file()


def test_legacy_native_cache_metadata_can_be_promoted_completely_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.core.assets import AssetCache

    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    old = _cache(tmp_path / "old", "model.safetensors")
    old_config = _cache(tmp_path / "old", "config.json")
    spec = _spec(
        tmp_path / "new",
        equivalent_caches=(
            AssetCache(
                path=old,
                canonical_url="https://huggingface.co/timm/example/resolve/main/model.safetensors",
            ),
        ),
    )
    monkeypatch.setattr(
        hub, "get_hf_file_metadata", lambda *a, **kw: pytest.fail("offline promotion")
    )
    monkeypatch.setattr(hub, "hf_hub_download", lambda **kw: pytest.fail("offline promotion"))
    result = hub.resolve_hub_asset(spec)
    assert result.path.read_bytes() == old.read_bytes()
    assert result.revision == _COMMIT
    assert result.path.is_relative_to(tmp_path / "new")
    assert (result.path.parent / "config.json").read_bytes() == old_config.read_bytes()


def test_prior_managed_cache_identity_remains_a_promotion_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from huggingface_hub import HfFileMetadata

    hub = importlib.import_module("clearml_yolo.adapters.assets.hub")
    monkeypatch.setenv("CY_HOME", str(tmp_path / "workspace"))
    spec = _spec(tmp_path / "native")
    _cache(tmp_path / "native", "config.json")
    legacy = (
        tmp_path
        / "workspace"
        / ".cache"
        / "clearml-yolo"
        / "models"
        / spec.backend
        / spec.preset
        / spec.identity
        / spec.filename
    )
    legacy.parent.mkdir(parents=True)
    torch.save({"weight": torch.ones(1)}, legacy)
    digest = hashlib.sha256(legacy.read_bytes()).hexdigest()
    metadata = HfFileMetadata(
        commit_hash=_COMMIT,
        etag=digest,
        location="https://signed.example/blob",
        size=legacy.stat().st_size,
        xet_file_data=None,
    )
    monkeypatch.setattr(hub, "get_hf_file_metadata", lambda *a, **kw: metadata)
    monkeypatch.setattr(
        hub, "hf_hub_download", lambda **kw: pytest.fail("compatible managed cache")
    )
    result = hub.resolve_hub_asset(spec)
    assert result.path.name == "pytorch_model.bin"
    assert result.path.read_bytes() == legacy.read_bytes()


def test_registry_revision_and_filename_override_follow_native_hf_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    timm = importlib.import_module("timm")
    from timm.models._pretrained import PretrainedCfg

    monkeypatch.setattr(
        timm,
        "get_pretrained_cfg",
        lambda name: PretrainedCfg(
            hf_hub_id="owner/model@release/v1", hf_hub_filename="weights.safetensors"
        ),
    )
    spec = assets.pretrained_asset("convnext_tiny")
    assert spec.hub is not None
    assert spec.hub.repository == "owner/model"
    assert spec.hub.revision == "release/v1"
    assert spec.hub.filename == "weights.safetensors"


def test_native_explicit_url_mode_remains_a_torch_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    builder = importlib.import_module("timm.models._builder")
    monkeypatch.setattr(builder, "_resolve_pretrained_source", lambda cfg: ("url", cfg["url"]))
    spec = assets.pretrained_asset("swin_tiny")
    torch_hub = importlib.import_module("torch.hub")
    assert spec.hub is None
    assert spec.native_cache == Path(torch_hub.get_dir()).resolve() / "checkpoints"
    assert spec.filename == "swin_tiny_patch4_window7_224.pth"
