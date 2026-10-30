"""Bounded streamed downloads with standard Requests authentication and TLS settings."""

import math
import os
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit, urlunsplit

import requests

_CHUNK_SIZE = 1024 * 1024
_MAX_WEIGHT_BYTES = 4 * 1024 * 1024 * 1024
_DOWNLOAD_SECONDS = 300
_CONNECT_TIMEOUT = 10
_READ_TIMEOUT = 30


def redacted_url(url: str) -> str:
    parts = urlsplit(url)
    host = parts.netloc.rsplit("@", 1)[-1]
    return urlunsplit((parts.scheme, host, parts.path, "redacted" if parts.query else "", ""))


def asset_source_url(url: str) -> str:
    """Keep public Drive asset IDs usable while hiding authentication material."""
    parts = urlsplit(url)
    if (
        parts.hostname == "drive.usercontent.google.com"
        and parts.path == "/download"
        and all(key in {"id", "export", "confirm"} for key, _ in parse_qsl(parts.query))
    ):
        return urlunsplit(
            (parts.scheme, parts.netloc.rsplit("@", 1)[-1], parts.path, parts.query, "")
        )
    return redacted_url(url)


def _headers(url: str) -> dict[str, str]:
    result = {"User-Agent": "clearml-yolo-model-assets"}
    if urlsplit(url).hostname == "huggingface.co":
        # Respect the library's standard token/cache locations without changing them.
        token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        if not token:
            default = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
            root = Path(os.environ.get("HF_HOME") or default / "huggingface")
            token_path = Path(os.environ.get("HF_TOKEN_PATH") or root / "token")
            if token_path.is_file():
                token = token_path.read_text(encoding="utf-8").strip()
        if token:
            result["Authorization"] = f"Bearer {token}"
    return result


def download(url: str, destination: Path, *, max_seconds: float = _DOWNLOAD_SECONDS) -> None:
    if not math.isfinite(max_seconds) or max_seconds <= 0:
        raise ValueError("Download time limit must be positive and finite")
    if urlsplit(url).scheme not in {"http", "https"}:
        raise ValueError("Asset downloads require HTTP or HTTPS")
    started = time.monotonic()
    # Requests honors netrc, URL basic auth, HTTP(S)_PROXY and CA bundle variables;
    # its redirect policy strips Authorization when the origin changes.
    with (
        requests.Session() as session,
        session.get(
            url,
            stream=True,
            timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
            headers=_headers(url),
            verify=os.environ.get("SSL_CERT_FILE") or True,
        ) as response,
    ):
        response.raise_for_status()
        expected = response.headers.get("Content-Length")
        total = 0
        with destination.open("wb") as target:
            for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
                total += len(chunk)
                if total > _MAX_WEIGHT_BYTES or time.monotonic() - started > max_seconds:
                    raise TimeoutError("Asset download exceeded its size or time bound")
                target.write(chunk)
            target.flush()
            os.fsync(target.fileno())
        if (
            expected is not None
            and not response.headers.get("Content-Encoding")
            and total != int(expected)
        ):
            raise ValueError("Asset download ended before the declared content length")
