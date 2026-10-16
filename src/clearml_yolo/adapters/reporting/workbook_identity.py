"""Application-owned model identity schema over generic reversible OOXML mechanics."""

import io
import json
import textwrap
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
from report_generator.v2 import (
    MetadataFormat,
    original_workbook,
    package_fingerprint,
    read_metadata,
)
from report_generator.v2 import annotate_workbook as annotate_package

from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.storage.filesystem import temporary_root, write_path
from clearml_yolo.core.identity import ModelIdentity
from clearml_yolo.core.presentation import human_labels, human_text

_META = "customXml/clearml-yolo-identity.xml"
_IDENTITY_NS = "https://clearml-yolo/model-identity/v1"
_FORMAT = MetadataFormat(_META, _IDENTITY_NS, "identity", "1", "clearmlYoloIdentity")
_DISPLAY_NS = "https://clearml-yolo/readable-workbook/v1"
_DISPLAY_FORMAT = MetadataFormat(
    "customXml/clearml-yolo-presentation.xml",
    _DISPLAY_NS,
    "presentation",
    "1",
    "clearmlYoloPresentation",
)
_SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_DRAWING_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_CHART_NS = "http://schemas.openxmlformats.org/drawingml/2006/chart"


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
    content = Path(path).read_bytes()
    root = _metadata(content)
    if root is None:
        read_metadata(content, _DISPLAY_FORMAT, _presentation_labels)
        return {}
    return _model_metadata(root)


def _original(content: bytes) -> bytes:
    identity_original = original_workbook(content, _FORMAT, _model_metadata)
    return cast(bytes, original_workbook(identity_original, _DISPLAY_FORMAT, _presentation_labels))


@contextmanager
def deannotated_workbook(path: str | Path) -> Iterator[Path]:
    """Yield the original layout; reject edits that would make original metrics stale."""
    source = Path(path)
    content = source.read_bytes()
    restored = _original(content)
    if restored == content:
        yield source
        return
    with TemporaryDirectory(prefix="clearml-yolo-dashboard-", dir=temporary_root()) as directory:
        original = Path(directory) / source.name
        write_path(original).write_bytes(restored)
        yield original


@trace_operation("report.dashboard.read")
def read_dashboard(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Read historical or annotated digital-metrics dashboards with pandas."""
    with deannotated_workbook(path) as source:
        frame = pd.read_excel(source, **kwargs)
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("Dashboard reader requires one worksheet")
    return frame


def _presentation_labels(root: ET.Element) -> dict[str, str]:
    text = root.findtext(f"{{{_DISPLAY_NS}}}labels")
    if text is None:
        raise ValueError("Readable workbook metadata has no label mapping")
    labels = json.loads(text)
    if not isinstance(labels, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in labels.items()
    ):
        raise ValueError("Invalid readable workbook label mapping")
    return labels


def _literal_groups(root: ET.Element) -> Iterator[list[ET.Element]]:
    """Select displayed string runs; formulas, references and numeric cells stay exact."""
    for element in root.iter():
        if element.tag in {f"{{{_SHEET_NS}}}si", f"{{{_SHEET_NS}}}is"}:
            yield list(element.iter(f"{{{_SHEET_NS}}}t"))
        elif element.tag == f"{{{_SHEET_NS}}}c" and element.get("t") == "str":
            yield list(element.iter(f"{{{_SHEET_NS}}}v"))
        elif element.tag == f"{{{_DRAWING_NS}}}p":
            yield list(element.iter(f"{{{_DRAWING_NS}}}t"))
        elif element.tag == f"{{{_CHART_NS}}}strCache":
            for value in element.iter(f"{{{_CHART_NS}}}v"):
                yield [value]


def _parse_display_xml(content: bytes) -> ET.Element:
    text = content.decode("utf-8")
    if "<!DOCTYPE" in text or "<!ENTITY" in text:
        raise ValueError("Workbook display XML must not declare entities")
    return ET.fromstring(text)  # noqa: S314 - DTD and entity declarations rejected above


def _visible_parts(entries: Mapping[str, bytes]) -> dict[str, ET.Element]:
    return {
        name: _parse_display_xml(content)
        for name, content in entries.items()
        if name.endswith(".xml")
        and (
            name == "xl/sharedStrings.xml"
            or name.startswith(("xl/worksheets/", "xl/charts/", "xl/drawings/"))
        )
    }


def humanize_workbook(path: str | Path) -> None:
    """Make displayed strings readable with integrity-checked original recovery."""
    path = write_path(path)
    content = path.read_bytes()
    identity = _metadata(content)
    if identity is not None:
        annotate_workbook(path, _model_metadata(identity))
        return
    if read_metadata(content, _DISPLAY_FORMAT, _presentation_labels) is not None:
        return
    with ZipFile(io.BytesIO(content)) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    labels = human_labels(
        "".join(node.text or "" for node in group)
        for root in _visible_parts(entries).values()
        for group in _literal_groups(root)
    )
    if all(original == display for original, display in labels.items()):
        return
    # Generic annotation owns relationships, shifted formulas and the original bytes.
    # The second envelope is separate from the established model-identity schema.
    annotate_package(
        path,
        banner_lines=["Class labels use readable aliases; original values are retained."],
        metadata_texts={"labels": json.dumps(labels, ensure_ascii=False)},
        format=_DISPLAY_FORMAT,
        validate=_presentation_labels,
    )
    with ZipFile(path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    for name, root in _visible_parts(entries).items():
        changed = False
        for group in _literal_groups(root):
            value = "".join(node.text or "" for node in group)
            display = labels.get(value, human_text(value))
            if group and display != value:
                group[0].text = display
                for node in group[1:]:
                    node.text = ""
                changed = True
        if changed:
            entries[name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    metadata = _parse_display_xml(entries[_DISPLAY_FORMAT.path])
    metadata.set("package_sha256", package_fingerprint(entries, _DISPLAY_FORMAT))
    entries[_DISPLAY_FORMAT.path] = ET.tostring(metadata, encoding="utf-8", xml_declaration=True)
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)


def _banner_lines(identities: Mapping[str, ModelIdentity]) -> list[str]:
    lines: list[str] = []
    for role, identity in identities.items():
        # Fixed-width chunks preserve every character, including whitespace and
        # formula-like prefixes. Inline strings never become Excel formulas.
        for label in (
            f"{human_text(role)}: {identity.label}",
            f"Training source: {'recorded' if identity.training_task_id else 'unavailable'}",
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
    path = write_path(path)
    if not identities:
        raise ValueError("Workbook annotation requires at least one model identity")
    path.write_bytes(_original(path.read_bytes()))
    humanize_workbook(path)
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
