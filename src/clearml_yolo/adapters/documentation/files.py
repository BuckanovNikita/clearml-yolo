"""Packaged documentation and confined temporary preview inputs."""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

PACKAGE = "clearml_yolo.adapters.documentation"
MAX_REQUEST_BYTES = 1024 * 1024
MAX_DOCUMENTS = 32
_MAX_NAME_LENGTH = 200
_FIRST_PRINTABLE = 32


def _relative_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if (
        not name
        or any(character in name for character in ("\\", ":", "\x00"))
        or any(ord(character) < _FIRST_PRINTABLE for character in name)
        or path.is_absolute()
        or any(part in {".", "..", ""} for part in name.split("/"))
        or len(name) > _MAX_NAME_LENGTH
    ):
        raise ValueError("Names must be relative paths without traversal or control characters")
    return path


def document_name(name: str) -> str:
    path = _relative_path(name)
    if path.suffix != ".yaml":
        raise ValueError("Document names must use .yaml, as required by the Hydra file source")
    if path.parts[0] in {"hydra", "_cy_schemas"}:
        raise ValueError("Replacing hydra or _cy_schemas documents is forbidden")
    return name


@contextmanager
def preview_directory(documents: Mapping[str, str]) -> Iterator[Path]:
    if len(documents) > MAX_DOCUMENTS:
        raise ValueError("At most 32 preview documents are allowed")
    names = [document_name(name) for name in documents]
    if sum(len(name.encode()) + len(value.encode()) for name, value in documents.items()) > (
        MAX_REQUEST_BYTES
    ):
        raise ValueError("Preview documents exceed 1 MiB")
    for name in names:
        if any(parent.as_posix() in documents for parent in PurePosixPath(name).parents):
            raise ValueError("A preview document cannot also be another document's directory")
    with TemporaryDirectory(prefix="cy-docs-preview-") as directory:
        root = Path(directory)
        for name in names:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(documents[name], encoding="utf-8")
        yield root


def asset_bytes(name: str) -> bytes:
    path = _relative_path(name)
    return files(PACKAGE).joinpath("assets", *path.parts).read_bytes()


def asset_text(name: str) -> str:
    return asset_bytes(name).decode("utf-8")
