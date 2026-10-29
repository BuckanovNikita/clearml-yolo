"""Pure, immutable trust records for independently versioned weight archives."""

import hashlib
import re
from pathlib import PurePosixPath
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Etag = Annotated[str, Field(pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")]
Size = Annotated[int, Field(strict=True, gt=0)]


def safe_member(value: str) -> str:
    """Require a normalized relative POSIX path without platform escapes."""
    if (
        not value
        or "\\" in value
        or ":" in value
        or PurePosixPath(value).is_absolute()
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ValueError("Unsafe bundle path")
    return value


class BundleRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BundleConfig(BundleRecord):
    member: str
    size: Size
    sha256: Digest
    etag: Etag

    _member = field_validator("member")(safe_member)


class BundleHub(BundleRecord):
    repository: str
    revision: str
    commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    filename: str
    etag: Etag
    config: BundleConfig

    _paths = field_validator("repository", "revision", "filename")(safe_member)


class BundleArchive(BundleRecord):
    name: str
    size: Annotated[int, Field(strict=True, gt=0, lt=2**31)]
    sha256: Digest

    @field_validator("name")
    @classmethod
    def archive_name(cls, value: str) -> str:
        safe_member(value)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*\.tar", value):
            raise ValueError("Expected a single tar filename")
        return value


class BundleAsset(BundleRecord):
    identity: Annotated[str, Field(pattern=r"^[0-9a-f]{24}$")]
    backend: str
    preset: str
    filename: str
    source_url: str
    source_revision: str | None
    kind: Literal["weights", "deim-source"]
    archive: str
    member: str
    size: Size
    sha256: Digest
    hub: BundleHub | None

    _paths = field_validator("member", "filename", "backend", "preset")(safe_member)


class BundleManifest(BundleRecord):
    schema_version: Literal[1]
    repository: Literal["BuckanovNikita/clearml-yolo"]
    release_tag: str
    archives: tuple[BundleArchive, ...]
    assets: tuple[BundleAsset, ...]

    @field_validator("release_tag")
    @classmethod
    def release_name(cls, value: str) -> str:
        if not re.fullmatch(r"weights-[A-Za-z0-9][A-Za-z0-9._-]*", value):
            raise ValueError("Invalid immutable weights release tag")
        return value

    @model_validator(mode="after")
    def references(self) -> Self:
        names = {archive.name for archive in self.archives}
        if len(names) != len(self.archives):
            raise ValueError("Duplicate bundle archive")
        if len({asset.identity for asset in self.assets}) != len(self.assets):
            raise ValueError("Duplicate bundle asset")
        members: set[tuple[str, str]] = set()
        for asset in self.assets:
            if asset.archive not in names:
                raise ValueError("Missing bundle archive")
            expected = f"assets/{asset.identity}/"
            if asset.member != expected + (asset.hub.filename if asset.hub else asset.filename):
                raise ValueError("Unexpected asset member")
            paths = [asset.member]
            if asset.hub is not None:
                if asset.hub.config.member != expected + "config.json":
                    raise ValueError("Unexpected config member")
                paths.append(asset.hub.config.member)
            for path in paths:
                key = (asset.archive, path)
                if key in members:
                    raise ValueError("Duplicate bundle member")
                members.add(key)
        return self

    @property
    def identity(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()
