"""Check product dependency boundaries, runtime targets and inert imports."""

import ast
import json
import subprocess
import sys
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path

import grimp
import pytest
from importlinter.application.user_options import UserOptions
from importlinter.domain.contract import Contract

import architecture_helpers as architecture

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def test_actual_graph_obeys_every_configured_contract_including_dynamic_imports(
    graph: grimp.ImportGraph,
    import_options: UserOptions,
    configured_contract: Callable[[str], Contract],
) -> None:
    for options in import_options.contracts_options:
        contract = configured_contract(options["name"])
        # Contracts remove ignored edges, so each gets its own graph.
        result = contract.check(deepcopy(graph), verbose=False)
        assert result.kept, (contract.name, result.metadata)
    assert architecture.graph_findings(graph) == []


@pytest.mark.parametrize("layer", ["core", "application"])
def test_actual_inner_layers_have_no_direct_effects(layer: str) -> None:
    check = {
        "core": architecture.core_effect_findings,
        "application": architecture.application_effect_findings,
    }[layer]
    assert [
        f"{path.relative_to(ROOT)}: {finding}"
        for path in (SRC / "clearml_yolo" / layer).rglob("*.py")
        for finding in check(ast.parse(path.read_text()))
    ] == []


@pytest.mark.parametrize("module", architecture.PURE_ADAPTERS)
def test_pure_cache_projection_adapters_have_no_effects(module: str) -> None:
    path = SRC.joinpath(*module.split(".")).with_suffix(".py")
    assert architecture.pure_adapter_effect_findings(module, ast.parse(path.read_text())) == []


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


def test_package_initializers_do_not_execute_operations_or_eagerly_load_sdks() -> None:
    assert [
        f"{path.relative_to(ROOT)}: {finding}"
        for path in SRC.rglob("__init__.py")
        for finding in architecture.initializer_findings(ast.parse(path.read_text()))
    ] == []
    assert architecture.initializer_dependency_findings(SRC) == []


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


def test_runtime_targets_resolve_to_shipped_modules_and_no_legacy_paths(
    graph: grimp.ImportGraph,
) -> None:
    targets = architecture.runtime_targets(SRC, ROOT / "pyproject.toml")
    assert not any(target.startswith("cy_queue") for target in targets)
    assert architecture.target_findings(targets, graph, SRC) == []
    assert architecture.runtime_boundary_findings(SRC) == []
    migration = json.loads((ROOT / "tests/fixtures/legacy-module-map.json").read_text())
    assert not set(migration).intersection(graph.modules)
    for legacy in migration:
        path = SRC.joinpath(*legacy.split("."))
        assert not path.with_suffix(".py").exists(), legacy
        assert not (path / "__init__.py").exists(), legacy


def test_generated_hydra_targets_resolve_after_export_and_composition(
    tmp_path: Path,
    graph: grimp.ImportGraph,
) -> None:
    from hydra import compose, initialize_config_dir
    from omegaconf import OmegaConf

    from clearml_yolo.entrypoints.hydra.config_tree import COMMAND_OF_CONFIG, dump_config_tree

    for command in COMMAND_OF_CONFIG.values():
        dump_config_tree(tmp_path, command=command, overwrite=True)
    targets: set[str] = set()
    for path in tmp_path.glob("cy*.yaml"):
        with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
            config = compose(config_name=path.stem)
        targets.update(architecture.config_targets(OmegaConf.to_container(config)))
    assert "clearml_yolo.application.contracts.ClearMLConfig" in targets
    assert "clearml_yolo.core.publication.FiftyOneConfig" in targets
    assert "clearml_yolo.core.evaluation.models.EvaluationConfig" in targets
    assert architecture.target_findings(targets, graph, SRC) == []
