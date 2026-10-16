"""Readable GPU labels without exposing persistent device identifiers."""

import hashlib
import re
from collections.abc import Mapping

_GPU_ID = re.compile(r"(?:MIG-)?GPU-[A-Za-z0-9-]+(?:/\d+/\d+)?")
_WORDS = (
    "amber",
    "apple",
    "aspen",
    "birch",
    "bloom",
    "brook",
    "cedar",
    "cherry",
    "cloud",
    "coral",
    "crane",
    "dawn",
    "delta",
    "dove",
    "dune",
    "elm",
    "fern",
    "field",
    "finch",
    "flint",
    "forest",
    "frost",
    "garden",
    "glade",
    "grove",
    "harbor",
    "hazel",
    "heron",
    "hill",
    "iris",
    "ivy",
    "jade",
    "lake",
    "lark",
    "laurel",
    "leaf",
    "lily",
    "maple",
    "meadow",
    "mint",
    "moon",
    "moss",
    "oak",
    "ocean",
    "olive",
    "orchid",
    "otter",
    "pearl",
    "pine",
    "plum",
    "pond",
    "reed",
    "ridge",
    "river",
    "robin",
    "rose",
    "sage",
    "sand",
    "shore",
    "sky",
    "snow",
    "star",
    "stone",
    "willow",
)


def identity_label(identifier: str) -> str:
    """Use stable words; selector resolution rejects any alias collision."""
    digest = hashlib.sha256(identifier.encode()).digest()
    return "gpu-" + "-".join(_WORDS[value % len(_WORDS)] for value in digest[:4])


def legacy_identity_label(identifier: str) -> str:
    """Retain old short-selector inputs without displaying them."""
    return "gpu-" + hashlib.sha256(identifier.encode()).hexdigest()[:12]


def redact_gpu_ids(text: str, labels: Mapping[str, str] | None = None) -> str:
    def replace(match: re.Match[str]) -> str:
        identifier = match[0]
        return (labels or {}).get(identifier, identity_label(identifier))

    return _GPU_ID.sub(replace, text)
