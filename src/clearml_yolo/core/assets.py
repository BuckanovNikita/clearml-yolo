"""Immutable asset requests and detached execution provenance, without IO."""

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

DEIM_REVISION = "1d2ca42171570c713e78fc6a766ec5104b7f4724"


class AssetCache(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    canonical_url: str
    checksum: str | None = None


class AssetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    backend: str
    preset: str
    filename: str
    canonical_url: str
    override: str
    revision: str | None = None
    checksum_algorithm: Literal["sha256", "md5"] = "sha256"
    checksum: str | None = None
    kind: Literal["weights", "deim-source"] = "weights"
    access_requirement: str | None = None
    cache_candidates: tuple[Path, ...] = ()
    equivalent_caches: tuple[AssetCache, ...] = ()

    @field_validator("backend", "preset", "filename")
    @classmethod
    def path_component(cls, value: str) -> str:
        if not value or value in {".", ".."} or "/" in value or "\\" in value:
            raise ValueError("Asset path components must be single nonempty names")
        return value

    @property
    def identity(self) -> str:
        selected = (self.canonical_url, self.revision, self.checksum_algorithm, self.checksum)
        return hashlib.sha256(json.dumps(selected).encode()).hexdigest()[:24]


class ResolvedAsset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    canonical_url: str
    path: Path
    content_kind: Literal["file", "source-tree"] = "file"
    sha256: str
    override: str
    revision: str | None = None
