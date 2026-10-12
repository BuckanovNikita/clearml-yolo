"""Application-owned model identity schema over generic reversible OOXML mechanics."""

import json
import textwrap
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast
from xml.etree import ElementTree as ET

import pandas as pd
from report_generator.v2 import (
    MetadataFormat,
    original_workbook,
    read_metadata,
)
from report_generator.v2 import annotate_workbook as annotate_package

from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.storage.filesystem import temporary_root
from clearml_yolo.core.identity import ModelIdentity

_META = "customXml/clearml-yolo-identity.xml"
_IDENTITY_NS = "https://clearml-yolo/model-identity/v1"
_FORMAT = MetadataFormat(_META, _IDENTITY_NS, "identity", "1", "clearmlYoloIdentity")


def _metadata(content: bytes) -> ET.Element | None:
    return cast(ET.Element | None, read_metadata(content, _FORMAT, _model_metadata))


def _model_metadata(root: ET.Element) -> dict[str, ModelIdentity]:
    text = root.findtext(f"{{{_IDENTITY_NS}}}models")
    if text is None:
        raise ValueError("Workbook identity metadata has no models")
    try:
        return _validate_models(json.loads(text))
    except (ValueError, TypeError) as error:
        raise ValueError("Invalid workbook model identity metadata") from error


def _validate_models(raw: Any) -> dict[str, ModelIdentity]:
    if (
        not isinstance(raw, dict)
        or not raw
        or any(not isinstance(role, str) or not role.strip() for role in raw)
    ):
        raise ValueError("Workbook identities must be a nonempty role mapping")
    return {role: ModelIdentity.model_validate(value) for role, value in raw.items()}


def workbook_identities(path: str | Path) -> dict[str, ModelIdentity]:
    """Recover model identities, or return empty for historical workbooks."""
    root = _metadata(Path(path).read_bytes())
    if root is None:
        return {}
    return _model_metadata(root)


def _original(content: bytes) -> bytes:
    return cast(bytes, original_workbook(content, _FORMAT, _model_metadata))


@contextmanager
def deannotated_workbook(path: str | Path) -> Iterator[Path]:
    """Yield the original layout; reject edits that would make original metrics stale."""
    source = Path(path)
    content = source.read_bytes()
    if _metadata(content) is None:
        yield source
        return
    with TemporaryDirectory(prefix="clearml-yolo-dashboard-", dir=temporary_root()) as directory:
        original = Path(directory) / source.name
        original.write_bytes(_original(content))
        yield original


@trace_operation("report.dashboard.read")
def read_dashboard(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Read historical or annotated digital-metrics dashboards with pandas."""
    with deannotated_workbook(path) as source:
        frame = pd.read_excel(source, **kwargs)
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("Dashboard reader requires one worksheet")
    return frame


def _banner_lines(identities: Mapping[str, ModelIdentity]) -> list[str]:
    lines: list[str] = []
    for role, identity in identities.items():
        # Fixed-width chunks preserve every character, including whitespace and
        # formula-like prefixes. Inline strings never become Excel formulas.
        for label in (
            f"{role}: {identity.model_name}",
            f"Training task: {identity.training_task_id or 'unavailable'}",
        ):
            lines.extend(
                textwrap.wrap(
                    label,
                    width=90,
                    expand_tabs=False,
                    replace_whitespace=False,
                    drop_whitespace=False,
                )
                or [""]
            )
    return lines


@trace_operation("report.workbook.annotate")
def annotate_workbook(path: str | Path, identities: Mapping[str, ModelIdentity]) -> None:
    """Prepend literal identities, preserving metadata v1 and byte-exact recovery."""
    if not identities:
        raise ValueError("Workbook annotation requires at least one model identity")
    annotate_package(
        path,
        banner_lines=_banner_lines(identities),
        metadata_texts={
            "models": json.dumps(
                {role: identity.model_dump() for role, identity in identities.items()},
                ensure_ascii=False,
            )
        },
        format=_FORMAT,
        validate=_model_metadata,
    )
