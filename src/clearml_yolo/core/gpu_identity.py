"""Readable GPU labels without exposing persistent device identifiers."""

import hashlib
import re
from collections.abc import Mapping

_GPU_ID = re.compile(r"(?:MIG-)?GPU-[A-Za-z0-9-]+(?:/\d+/\d+)?")


def identity_label(identifier: str) -> str:
    return "gpu-" + hashlib.sha256(identifier.encode()).hexdigest()[:12]


def redact_gpu_ids(text: str, labels: Mapping[str, str] | None = None) -> str:
    def replace(match: re.Match[str]) -> str:
        identifier = match[0]
        return (labels or {}).get(identifier, identity_label(identifier))

    return _GPU_ID.sub(replace, text)
