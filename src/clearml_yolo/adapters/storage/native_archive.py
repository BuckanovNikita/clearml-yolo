"""Concrete workflow operations behind application ports."""

import json
import zipfile
from pathlib import Path

import yaml

from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.core import artifact_names
from clearml_yolo.core.redaction import sanitize_configuration


@trace_operation("storage.native.archive")
def archive_native_outputs(save_dir: Path, destination: Path, *, role: str, split: str) -> Path:
    """Archive native tabular/text outputs without copying source-derived images."""
    archive = destination / f"native_outputs_{role}_{artifact_names.split_component(split)}.zip"
    allowed = {".csv", ".json", ".txt", ".yaml", ".yml"}
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        if save_dir.is_dir():
            for path in sorted(save_dir.rglob("*")):
                if path.is_file() and path.suffix.lower() in allowed:
                    relative = path.relative_to(save_dir)
                    suffix = path.suffix.lower()
                    if suffix == ".json":
                        content = json.loads(path.read_text(encoding="utf-8"))
                        bundle.writestr(
                            relative.as_posix(),
                            json.dumps(
                                sanitize_configuration(content), indent=2, ensure_ascii=False
                            )
                            + "\n",
                        )
                    elif suffix in {".yaml", ".yml"}:
                        content = yaml.safe_load(path.read_text(encoding="utf-8"))
                        bundle.writestr(
                            relative.as_posix(),
                            yaml.safe_dump(
                                sanitize_configuration(content), sort_keys=False, allow_unicode=True
                            ),
                        )
                    else:
                        bundle.write(path, relative)
    return archive
