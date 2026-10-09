"""Prove inward dependencies against the real graph and hypothetical violations."""

import ast
import json
import subprocess
import sys
import tomllib
from copy import deepcopy
from pathlib import Path

import grimp
import pytest
from importlinter.configuration import configure
from importlinter.contracts.forbidden import ForbiddenContract
from importlinter.contracts.layers import LayersContract

import architecture_helpers as architecture

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


@pytest.fixture(scope="module")
def graph() -> grimp.ImportGraph:
    imported = grimp.build_graph(
        "clearml_yolo", include_external_packages=True, cache_dir=None
    )
    architecture.add_dynamic_imports(imported, SRC)
    return imported


def test_actual_graph_obeys_classification_direction_sdk_ownership_and_cycles(
    graph: grimp.ImportGraph,
) -> None:
    assert architecture.graph_findings(graph) == []


@pytest.mark.parametrize(
    ("importer", "imported", "message"),
    [
        ("clearml_yolo.core.identity", "clearml_yolo.adapters.storage.identity", "direction"),
        ("clearml_yolo.application.ports", "clearml_yolo.entrypoints.composition", "direction"),
        (
            "clearml_yolo.application.use_cases.train",
            "clearml_yolo.adapters.yolo.inference",
            "direction",
        ),
        (
            "clearml_yolo.adapters.storage.dataset",
            "clearml_yolo.application.use_cases.train",
            "direction",
        ),
        (
            "clearml_yolo.adapters.yolo.inference",
            "clearml_yolo.entrypoints.composition",
            "direction",
        ),
        ("clearml_yolo.core.identity", "loguru", "core dependency"),
        ("clearml_yolo.application.use_cases.metrics", "loguru", "application effects"),
        ("clearml_yolo.core.identity", "digital_metrics", "SDK ownership"),
        ("clearml_yolo.application.contracts", "clearml", "SDK ownership"),
        ("clearml_yolo.application.contracts", "openpyxl", "SDK ownership"),
        ("clearml_yolo.adapters.storage.dataset", "ultralytics", "SDK ownership"),
        ("clearml_yolo.adapters.clearml.models", "report_generator", "SDK ownership"),
        ("clearml_yolo.adapters.yolo.inference", "fiftyone", "SDK ownership"),
        ("clearml_yolo.adapters.storage.dataset", "hydra", "SDK ownership"),
        ("clearml_yolo.entrypoints.composition", "torch", "SDK ownership"),
    ],
)
def test_injected_forbidden_dependencies_are_rejected(
    importer: str, imported: str, message: str
) -> None:
    candidate = grimp.ImportGraph()
    candidate.add_module(importer)
    candidate.add_module(imported)
    candidate.add_import(importer=importer, imported=imported)
    findings = architecture.graph_findings(candidate)
    assert any(message in finding for finding in findings), findings


def test_transitive_adapter_escape_cannot_hide_behind_application_helper() -> None:
    candidate = grimp.ImportGraph()
    for module in (
        "clearml_yolo.application.use_cases.train",
        "clearml_yolo.application.helper",
        "clearml_yolo.adapters.yolo.inference",
    ):
        candidate.add_module(module)
    candidate.add_import(
        importer="clearml_yolo.application.use_cases.train",
        imported="clearml_yolo.application.helper",
    )
    candidate.add_import(
        importer="clearml_yolo.application.helper", imported="clearml_yolo.adapters.yolo.inference"
    )
    assert any("direction" in finding for finding in architecture.graph_findings(candidate))


@pytest.mark.parametrize(
    "module",
    ["clearml_yolo.misc", "clearml_yolo.adapters.misc.helper", "clearml_yolo.application.misc"],
)
def test_unclassified_module_is_rejected(module: str) -> None:
    candidate = grimp.ImportGraph()
    candidate.add_module(module)
    assert any("unclassified" in finding for finding in architecture.graph_findings(candidate))


@pytest.mark.parametrize("prefix", ["core", "adapters.storage", "entrypoints.hydra"])
def test_injected_helper_cycle_is_rejected(prefix: str) -> None:
    candidate = grimp.ImportGraph()
    first, second = f"clearml_yolo.{prefix}.first", f"clearml_yolo.{prefix}.second"
    candidate.add_module(first)
    candidate.add_module(second)
    candidate.add_import(importer=first, imported=second)
    candidate.add_import(importer=second, imported=first)
    assert any("cycle" in finding for finding in architecture.graph_findings(candidate))


def test_allowed_scientific_dependencies_and_explicit_native_bridge() -> None:
    candidate = grimp.ImportGraph()
    for imported in ("pydantic", "pandera", "pandas", "numpy", "scipy", "math"):
        candidate.add_module(imported)
        candidate.add_module("clearml_yolo.core.identity")
        candidate.add_import(importer="clearml_yolo.core.identity", imported=imported)
    candidate.add_module("clearml_yolo.adapters.runtime.gpu_probe")
    candidate.add_module("torch")
    candidate.add_import(importer="clearml_yolo.adapters.runtime.gpu_probe", imported="torch")
    assert architecture.graph_findings(candidate) == []


@pytest.mark.parametrize(
    "source",
    [
        "open('data.csv')",
        "Path('data.csv').read_text()",
        "pd.read_csv('data.csv')",
        "subprocess.run(['ls'])",
        "importlib.import_module('clearml')",
    ],
)
def test_core_effectful_calls_are_rejected(source: str) -> None:
    assert architecture.core_effect_findings(ast.parse(source)), source


def test_actual_core_contains_no_io_network_process_or_dynamic_import_calls() -> None:
    findings: list[str] = []
    for path in (SRC / "clearml_yolo/core").rglob("*.py"):
        findings.extend(
            f"{path.relative_to(ROOT)}: {finding}"
            for finding in architecture.core_effect_findings(ast.parse(path.read_text()))
        )
    assert findings == []


def test_package_initializers_do_not_execute_operations_or_eagerly_load_sdks() -> None:
    findings: list[str] = []
    for path in SRC.rglob("__init__.py"):
        findings.extend(
            f"{path.relative_to(ROOT)}: {finding}"
            for finding in architecture.initializer_findings(ast.parse(path.read_text()))
        )
    assert findings == []
    assert architecture.initializer_dependency_findings(SRC) == []


@pytest.mark.parametrize(
    "source",
    [
        "client = create_client()",
        "initialize()",
        "from ultralytics import YOLO",
        "from clearml import Task",
    ],
)
def test_effectful_initializers_are_rejected(source: str) -> None:
    assert architecture.initializer_findings(ast.parse(source)), source


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
    assert "clearml_yolo.entrypoints.hydra.worker" not in targets
    assert "clearml_yolo.adapters.runtime.gpu_probe" in targets
    assert "hydra_plugins.cy_queue.launcher.QueueLauncher" not in targets
    assert architecture.target_findings(targets, graph, SRC) == []
    migration = json.loads((ROOT / "specs/021-clean-architecture/migration-map.json").read_text())
    assert not set(migration).intersection(graph.modules)
    for legacy in migration:
        path = SRC.joinpath(*legacy.split("."))
        assert not path.with_suffix(".py").exists(), legacy
        assert not (path / "__init__.py").exists(), legacy


@pytest.mark.parametrize(
    "target",
    [
        "clearml_yolo.apps.metrics.main",
        "clearml_yolo.entrypoints.hydra.missing.callback",
        "clearml_yolo.entrypoints.metrics.missing",
    ],
)
def test_legacy_missing_module_and_missing_attribute_targets_are_rejected(
    target: str,
    graph: grimp.ImportGraph,
) -> None:
    assert architecture.target_findings({target}, graph, SRC)


def test_all_ten_console_commands_are_independent_entrypoints(graph: grimp.ImportGraph) -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    commands = {target.split(":")[0] for target in config["project"]["scripts"].values()}
    assert len(commands) == 10
    for importer in commands:
        for imported in commands - {importer}:
            assert graph.find_shortest_chain(importer, imported) is None, (importer, imported)


@pytest.mark.parametrize(
    ("name", "importer", "imported"),
    [
        (
            "Clean architecture inward layers",
            "clearml_yolo.application.use_cases.train",
            "clearml_yolo.adapters.yolo.inference",
        ),
        ("clearml SDK has explicit owners", "clearml_yolo.application.contracts", "clearml"),
        (
            "Core and application have no logging or rendering dependency",
            "clearml_yolo.application.contracts",
            "loguru",
        ),
    ],
)
def test_actual_configured_import_linter_contract_rejects_mutated_graph(
    name: str,
    importer: str,
    imported: str,
    graph: grimp.ImportGraph,
) -> None:
    # import-linter's public bootstrap is untyped; contract/check APIs are typed.
    configure()  # type: ignore[no-untyped-call]
    session = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["importlinter"]
    options = next(contract for contract in session["contracts"] if contract["name"] == name)
    parsed_options = {
        key: str(value).lower() if isinstance(value, bool) else value
        for key, value in options.items()
    }
    contract_class = LayersContract if options["type"] == "layers" else ForbiddenContract
    contract = contract_class(name=name, session_options=session, contract_options=parsed_options)
    actual = contract.check(deepcopy(graph), verbose=False)
    assert actual.kept
    mutated = deepcopy(graph)
    mutated.add_import(importer=importer, imported=imported)
    assert not contract.check(mutated, verbose=False).kept


@pytest.mark.parametrize(
    ("name", "module"),
    [
        ("Exhaustive root layer classification", "clearml_yolo.misc"),
        ("Exhaustive adapter responsibility classification", "clearml_yolo.adapters.misc"),
        ("Exhaustive application classification", "clearml_yolo.application.misc"),
    ],
)
def test_actual_exhaustive_contract_rejects_new_unclassified_module(
    name: str,
    module: str,
    graph: grimp.ImportGraph,
) -> None:
    configure()  # type: ignore[no-untyped-call]
    session = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["importlinter"]
    options = next(contract for contract in session["contracts"] if contract["name"] == name)
    parsed_options = {
        key: str(value).lower() if isinstance(value, bool) else value
        for key, value in options.items()
    }
    contract = LayersContract(name=name, session_options=session, contract_options=parsed_options)
    assert contract.check(deepcopy(graph), verbose=False).kept
    mutated = deepcopy(graph)
    mutated.add_module(module)
    assert not contract.check(mutated, verbose=False).kept


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Path('x').stat()", True),
        ("path.read_text()", True),
        ("pd.read_csv('x')", True),
        ("deps.storage.read_text(path)", False),
        ("deps.storage.stat(path)", False),
        ("deps.storage.read_csv(path)", False),
        ("pd.ExcelWriter('x.xlsx')", True),
    ],
)
def test_application_io_requires_explicit_storage_port(source: str, expected: bool) -> None:
    assert bool(architecture.application_effect_findings(ast.parse(source))) == expected


def test_actual_application_uses_ports_for_io() -> None:
    findings: list[str] = []
    for path in (SRC / "clearml_yolo/application").rglob("*.py"):
        findings.extend(
            f"{path.relative_to(ROOT)}: {finding}"
            for finding in architecture.application_effect_findings(ast.parse(path.read_text()))
        )
    assert findings == []


@pytest.mark.parametrize(
    ("importer", "imported"),
    [
        ("clearml_yolo.adapters.evaluation.scoring", "clearml_yolo.adapters.reporting.evaluation"),
        ("clearml_yolo.adapters.evaluation.scoring", "clearml_yolo.adapters.clearml.session"),
        ("clearml_yolo.adapters.storage.dataset", "clearml_yolo.adapters.yolo.inference"),
        ("clearml_yolo.adapters.fiftyone.publisher", "clearml_yolo.adapters.clearml.session"),
    ],
)
def test_adapter_peer_escapes_are_rejected(importer: str, imported: str) -> None:
    candidate = grimp.ImportGraph()
    candidate.add_module(importer)
    candidate.add_module(imported)
    candidate.add_import(importer=importer, imported=imported)
    assert any("adapter peer" in finding for finding in architecture.graph_findings(candidate))


def test_generated_hydra_targets_resolve_after_export_and_composition(
    tmp_path: Path,
    graph: grimp.ImportGraph,
) -> None:
    from hydra import compose, initialize_config_dir
    from omegaconf import OmegaConf

    from clearml_yolo.entrypoints.hydra.config_tree import dump_config_tree

    dump_config_tree(tmp_path)
    targets: set[str] = set()
    for path in tmp_path.glob("cy*.yaml"):
        with initialize_config_dir(config_dir=str(tmp_path), version_base="1.3"):
            config = compose(config_name=path.stem)
        targets.update(architecture.config_targets(OmegaConf.to_container(config)))
    assert "clearml_yolo.application.contracts.ClearMLConfig" in targets
    assert "clearml_yolo.core.publication.FiftyOneConfig" in targets
    assert "clearml_yolo.core.evaluation.models.EvaluationConfig" in targets
    assert architecture.target_findings(targets, graph, SRC) == []


def test_initializer_cannot_eagerly_load_sdk_through_internal_reexport(tmp_path: Path) -> None:
    package = tmp_path / "clearml_yolo"
    package.mkdir()
    (package / "__init__.py").write_text("from clearml_yolo.adapters.yolo import inference\n")
    adapter = package / "adapters/yolo"
    adapter.mkdir(parents=True)
    (adapter / "inference.py").write_text("from ultralytics import YOLO\n")
    findings = architecture.initializer_dependency_findings(tmp_path)
    assert findings
    assert "ultralytics" in findings[0]


def test_dynamic_sdk_import_is_checked_at_its_owner(tmp_path: Path) -> None:
    package = tmp_path / "clearml_yolo/adapters/storage"
    package.mkdir(parents=True)
    (package / "helper.py").write_text(
        "from importlib import import_module\nclient = import_module('clearml')\n"
    )
    candidate = grimp.ImportGraph()
    candidate.add_module("clearml_yolo.adapters.storage.helper")
    architecture.add_dynamic_imports(candidate, tmp_path)
    assert any("SDK ownership" in finding for finding in architecture.graph_findings(candidate))
