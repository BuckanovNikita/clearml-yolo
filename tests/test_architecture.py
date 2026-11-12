"""Execute product imports and generated configuration targets."""

import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cache_projection_import_and_call_are_inert_in_fresh_process() -> None:
    source = """
import json
import os
import sys

class DenySdk:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "clearml" or fullname.startswith("clearml."):
            raise AssertionError("Projection imported the ClearML SDK")

sys.meta_path.insert(0, DenySdk())
calling = False
def audit(event, args):
    if event.startswith(("socket.", "subprocess.")) or event in {
        "os.system", "os.mkdir", "os.remove", "os.rename", "os.rmdir"
    }:
        raise AssertionError(event)
    if event == "open":
        mode, flags = args[1:3]
        if calling or (mode and any(char in mode for char in "wax+")) or (
            flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
        ):
            raise AssertionError("Projection performed file IO")

sys.addaudithook(audit)
from clearml_yolo.adapters.clearml.cache import normalize_task_hash
from clearml_yolo.adapters.clearml.parameters import project_native_parameters
calling = True
run = {"ultralytics": {"device": [0, 1]}, "prepared_dataset": {
    "root": "/generated", "cache_identity": "a" * 64
}}
value = {"script": {"entry_point": "-m clearml_yolo.entrypoints.train"},
    "configs": {"run": json.dumps(run), "dataset": "path: /generated\\nnames: {0: cat}"}}
projected = normalize_task_hash(value)
assert json.loads(projected["configs"]["run"])["ultralytics"]["device"] == {
    "type": "cuda", "count": 2
}
assert project_native_parameters({"device": [0, 1], "epochs": 2}) == {"epochs": 2}
assert "clearml" not in sys.modules
"""
    completed = subprocess.run(  # noqa: S603 - fixed interpreter and literal probe source
        [sys.executable, "-B", "-c", source],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_public_root_import_is_inert_in_fresh_interpreter() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import clearml_yolo; "
                "forbidden={'hydra','hydra_zen','clearml','ultralytics',"
                "'torch','fiftyone','pandera','pandas'}; "
                "loaded=forbidden.intersection(sys.modules); assert not loaded, loaded"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == ""


def _config_targets(value: object) -> set[str]:
    """Collect dynamically generated Hydra targets without instantiating them."""
    targets: set[str] = set()
    if isinstance(value, Mapping):
        target = value.get("_target_")
        if isinstance(target, str) and target.startswith(("clearml_yolo",)):
            targets.add(target)
        for child in value.values():
            targets.update(_config_targets(child))
    elif isinstance(value, list | tuple):
        for child in value:
            targets.update(_config_targets(child))
    return targets


def test_generated_hydra_targets_resolve_after_export_and_composition(
    tmp_path: Path,
) -> None:
    from hydra import compose, initialize_config_dir
    from hydra.utils import get_object
    from omegaconf import OmegaConf

    from clearml_yolo.entrypoints.hydra.config_tree import COMMAND_OF_CONFIG, dump_config_tree

    for command in COMMAND_OF_CONFIG.values():
        dump_config_tree(tmp_path, command=command, overwrite=True)
    targets: set[str] = set()
    for path in tmp_path.glob("cy*.yaml"):
        with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
            config = compose(config_name=path.stem)
        targets.update(_config_targets(OmegaConf.to_container(config)))
    assert "clearml_yolo.application.contracts.ClearMLConfig" in targets
    assert "clearml_yolo.core.publication.FiftyOneConfig" in targets
    assert "clearml_yolo.core.evaluation.models.EvaluationConfig" in targets
    for target in targets:
        assert callable(get_object(target)), target
