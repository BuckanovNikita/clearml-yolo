"""Published native settings are detached and retain semantic nested fields."""

from copy import deepcopy
from typing import Any

from clearml_yolo.adapters.clearml.parameters import project_native_parameters


def test_native_projection_preserves_unknown_nested_names_paths_and_explicit_empty_values() -> None:
    values: dict[str, Any] = {
        "device": [2, 3],
        "name": "temporary-run",
        "project": "/output",
        "save_dir": "/output/temporary-run",
        "exist_ok": True,
        "data": "/generated/data.yaml",
        "epochs": 3,
        "classes": [],
        "pretrained": False,
        "weights": None,
        "source": "",
        "model": {"name": "detector", "path": "checkpoint.pt", "device": "semantic"},
        "names": ["thing"],
        "unknown_path": "custom/input",
    }
    original = deepcopy(values)

    projected = project_native_parameters(values)

    assert projected == {
        "epochs": 3,
        "classes": [],
        "pretrained": False,
        "weights": None,
        "source": "",
        "model": {"name": "detector", "path": "checkpoint.pt", "device": "semantic"},
        "names": ["thing"],
        "unknown_path": "custom/input",
    }
    projected["model"]["name"] = "changed-by-sdk"
    projected["names"].append("another-class")
    assert values == original
