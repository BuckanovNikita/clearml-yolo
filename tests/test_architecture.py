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
from importlinter.adapters.user_options import IniFileUserOptionReader
from importlinter.application.user_options import UserOptions
from importlinter.configuration import configure
from importlinter.contracts.forbidden import ForbiddenContract
from importlinter.contracts.independence import IndependenceContract
from importlinter.contracts.layers import LayersContract

import architecture_helpers as architecture

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


@pytest.fixture(scope="module")
def import_options() -> UserOptions:
    # Use the same reader as lint-imports, including native INI list/boolean handling.
    configure()  # type: ignore[no-untyped-call]
    options = IniFileUserOptionReader().read_options(str(ROOT / ".importlinter"))
    assert options is not None
    assert options.contracts_options
    return options


@pytest.fixture(scope="module")
def graph() -> grimp.ImportGraph:
    imported = grimp.build_graph("clearml_yolo", include_external_packages=True, cache_dir=None)
    architecture.add_dynamic_imports(imported, SRC)
    return imported


def _contract(
    options: UserOptions, name: str
) -> LayersContract | ForbiddenContract | IndependenceContract:
    selected = next(contract for contract in options.contracts_options if contract["name"] == name)
    classes: dict[str, type[LayersContract | ForbiddenContract | IndependenceContract]] = {
        "layers": LayersContract,
        "forbidden": ForbiddenContract,
        "independence": IndependenceContract,
    }
    return classes[selected["type"]](
        name=name, session_options=options.session_options, contract_options=selected
    )


def test_actual_graph_obeys_every_configured_contract_including_dynamic_imports(
    graph: grimp.ImportGraph, import_options: UserOptions
) -> None:
    for options in import_options.contracts_options:
        contract = _contract(import_options, options["name"])
        # Contracts remove ignored edges, so each gets its own graph.
        result = contract.check(deepcopy(graph), verbose=False)
        assert result.kept, (contract.name, result.metadata)
    assert architecture.graph_findings(graph) == []


@pytest.mark.parametrize(
    ("importer", "imported", "rejected"),
    [
        ("clearml_yolo.core.identity", "loguru", True),
        ("clearml_yolo.core.identity", "unapproved_scientific_package", True),
        ("clearml_yolo.adapters.clearml.cache", "clearml", True),
        ("clearml_yolo.adapters.clearml.cache", "clearml_yolo.adapters.clearml.session", True),
        ("clearml_yolo.adapters.clearml.cache", "clearml_yolo.adapters.storage.filesystem", True),
        ("clearml_yolo.adapters.clearml.parameters", "yaml", True),
    ]
    + [
        ("clearml_yolo.core.identity", dependency, False)
        for dependency in ("pydantic", "pandera", "pandas", "numpy", "scipy", "math")
    ],
)
def test_unique_dependency_allowlists(importer: str, imported: str, rejected: bool) -> None:
    candidate = grimp.ImportGraph()
    candidate.add_module(importer)
    candidate.add_module(imported)
    candidate.add_import(importer=importer, imported=imported)
    assert bool(architecture.graph_findings(candidate)) == rejected


def test_dynamic_launch_targets_cannot_bypass_direct_queue_boundary() -> None:
    assert architecture.launch_target_findings(
        "clearml_yolo.entrypoints.hydra.common", {"cy_queue.adapters.queue.guardian"}
    )
    assert not architecture.launch_target_findings(
        "cy_queue.adapters.queue.runtime", {"clearml_yolo.adapters.runtime.process_tree"}
    )


@pytest.mark.parametrize("prefix", ["core", "adapters.storage", "entrypoints.hydra"])
def test_injected_helper_cycle_is_rejected(prefix: str) -> None:
    candidate = grimp.ImportGraph()
    first, second = f"clearml_yolo.{prefix}.first", f"clearml_yolo.{prefix}.second"
    candidate.add_module(first)
    candidate.add_module(second)
    candidate.add_import(importer=first, imported=second)
    candidate.add_import(importer=second, imported=first)
    assert any("cycle" in finding for finding in architecture.graph_findings(candidate))


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


@pytest.mark.parametrize("module", architecture.PURE_ADAPTERS)
@pytest.mark.parametrize(
    "source",
    [
        "def project(value):\n    return open('input').read()",
        "import socket\ndef project(value):\n    return socket.create_connection(('host', 80))",
        "import subprocess\ndef project(value):\n    return subprocess.run(['worker'])",
    ],
)
def test_pure_adapter_effect_contract_rejects_injected_io(module: str, source: str) -> None:
    tree = ast.parse(source)
    assert architecture.pure_adapter_effect_findings(module, tree)
    assert (
        architecture.pure_adapter_effect_findings("clearml_yolo.adapters.clearml.session", tree)
        == []
    )


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


def test_console_command_inventory_matches_configured_independence(
    import_options: UserOptions,
) -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    commands = {target.split(":")[0] for target in config["project"]["scripts"].values()}
    options = _contract(import_options, "Every command entrypoint stands alone").contract_options
    assert commands == set(options["modules"])


@pytest.mark.parametrize(
    ("name", "importer", "imported"),
    [
        (
            "Adapters depend only on application ports and contracts",
            "clearml_yolo.adapters.storage.dataset",
            "clearml_yolo.application.ground_truth",
        ),
        (
            "Application command composition is inward and acyclic",
            "clearml_yolo.application.use_cases.train",
            "clearml_yolo.application.use_cases.pipeline",
        ),
        (
            "CY never imports extracted queue or its private dependencies",
            "clearml_yolo.adapters.runtime.process_tree",
            "cy_queue",
        ),
        (
            "CY never imports extracted queue or its private dependencies",
            "clearml_yolo.entrypoints.pipeline",
            "textual",
        ),
        (
            "CY never imports extracted queue or its private dependencies",
            "clearml_yolo.adapters.runtime.bootstrap",
            "pynvml",
        ),
        (
            "assets adapter peer ownership",
            "clearml_yolo.adapters.assets.sources",
            "clearml_yolo.adapters.clearml.session",
        ),
        (
            "storage adapter peer ownership",
            "clearml_yolo.adapters.storage.dataset",
            "clearml_yolo.adapters.assets.sources",
        ),
        (
            "evaluation adapter peer ownership",
            "clearml_yolo.adapters.evaluation.scoring",
            "clearml_yolo.adapters.reporting.evaluation",
        ),
        (
            "Clean architecture inward layers",
            "clearml_yolo.application.use_cases.train",
            "clearml_yolo.adapters.yolo.inference",
        ),
        ("clearml SDK has explicit owners", "clearml_yolo.application.contracts", "clearml"),
        ("safetensors SDK has explicit owners", "clearml_yolo.application.ports", "safetensors"),
        ("huggingface_hub SDK has explicit owners", "clearml_yolo.core.assets", "huggingface_hub"),
        ("Exhaustive root layer classification", "clearml_yolo.misc", None),
        ("Exhaustive adapter responsibility classification", "clearml_yolo.adapters.misc", None),
        ("Exhaustive application classification", "clearml_yolo.application.misc", None),
        ("Exhaustive entrypoint classification", "clearml_yolo.entrypoints.misc", None),
        (
            "albumentations SDK has explicit owners",
            "clearml_yolo.core.transforms",
            "albumentations",
        ),
        (
            "clearml adapter peer ownership",
            "clearml_yolo.adapters.clearml.cache",
            "clearml_yolo.adapters.yolo.config",
        ),
        (
            "Clean architecture inward layers",
            "clearml_yolo.application.use_cases.train",
            "clearml_yolo.adapters.clearml.parameters",
        ),
        (
            "torchvision SDK has explicit owners",
            "clearml_yolo.application.contracts",
            "torchvision",
        ),
        ("timm SDK has explicit owners", "clearml_yolo.adapters.rfdetr.backend", "timm"),
        ("timm SDK has explicit owners", "clearml_yolo.adapters.export.metadata", "timm"),
        ("torch SDK has explicit owners", "clearml_yolo.application.training_workers", "torch"),
        (
            "Clean architecture inward layers",
            "clearml_yolo.core.batch_estimation",
            "clearml_yolo.adapters.runtime.gpu_memory",
        ),
        (
            "runtime adapter peer ownership",
            "clearml_yolo.adapters.runtime.gpu_memory",
            "clearml_yolo.adapters.yolo.batch_probe",
        ),
        (
            "yolo adapter peer ownership",
            "clearml_yolo.adapters.yolo.inference",
            "clearml_yolo.adapters.runtime.gpu_memory",
        ),
        ("rfdetr SDK has explicit owners", "clearml_yolo.adapters.deim.backend", "rfdetr"),
        (
            "Clean architecture inward layers",
            "clearml_yolo.core.batch_estimation",
            "clearml_yolo.adapters.runtime.gpu_inventory",
        ),
        (
            "Clean architecture inward layers",
            "clearml_yolo.application.use_cases.batch_estimate",
            "clearml_yolo.adapters.storage.batch_estimates",
        ),
        (
            "torchvision adapter peer ownership",
            "clearml_yolo.adapters.torchvision.training",
            "clearml_yolo.adapters.fcos.model",
        ),
        (
            "fcos adapter peer ownership",
            "clearml_yolo.adapters.fcos.backend",
            "clearml_yolo.adapters.clearml.session",
        ),
        (
            "lightning_fabric SDK has explicit owners",
            "clearml_yolo.application.training_workers",
            "lightning_fabric",
        ),
        (
            "faster_coco_eval SDK has explicit owners",
            "clearml_yolo.core.batch_estimation",
            "faster_coco_eval",
        ),
        (
            "pytorch_lightning SDK has explicit owners",
            "clearml_yolo.application.contracts",
            "pytorch_lightning",
        ),
        (
            "pycocotools SDK has explicit owners",
            "clearml_yolo.application.contracts",
            "pycocotools",
        ),
        ("onnx SDK has explicit owners", "clearml_yolo.adapters.clearml.detectors", "onnx"),
        ("tensorrt SDK has explicit owners", "clearml_yolo.entrypoints.composition", "tensorrt"),
        (
            "export adapter peer ownership",
            "clearml_yolo.adapters.export.metadata",
            "clearml_yolo.adapters.fasterrcnn.model",
        ),
        (
            "export adapter peer ownership",
            "clearml_yolo.adapters.export.verification",
            "clearml_yolo.adapters.fasterrcnn.inference",
        ),
        (
            "runtime adapter peer ownership",
            "clearml_yolo.adapters.runtime.git_workspace",
            "clearml_yolo.adapters.clearml.script",
        ),
        (
            "Every command entrypoint stands alone",
            "clearml_yolo.entrypoints.export",
            "clearml_yolo.entrypoints.train",
        ),
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
    imported: str | None,
    graph: grimp.ImportGraph,
    import_options: UserOptions,
) -> None:
    contract = _contract(import_options, name)
    actual = contract.check(deepcopy(graph), verbose=False)
    assert actual.kept
    mutated = deepcopy(graph)
    if imported is None:
        mutated.add_module(importer)
    else:
        if imported not in mutated.modules:
            mutated.add_module(imported)
        mutated.add_import(importer=importer, imported=imported)
    assert not contract.check(mutated, verbose=False).kept


def test_transitive_adapter_escape_is_rejected_by_configured_layers(
    graph: grimp.ImportGraph, import_options: UserOptions
) -> None:
    candidate = deepcopy(graph)
    candidate.add_module("clearml_yolo.application.helper")
    candidate.add_import(
        importer="clearml_yolo.application.use_cases.train",
        imported="clearml_yolo.application.helper",
    )
    candidate.add_import(
        importer="clearml_yolo.application.helper",
        imported="clearml_yolo.adapters.yolo.inference",
    )
    assert (
        not _contract(import_options, "Clean architecture inward layers")
        .check(candidate, verbose=False)
        .kept
    )


def test_type_only_imports_remain_in_the_configured_graph(
    graph: grimp.ImportGraph, import_options: UserOptions
) -> None:
    exclusion = import_options.session_options.get("exclude_type_checking_imports")
    assert str(exclusion).lower() != "true"
    assert "clearml_yolo.adapters.augmentation.pipeline" in graph.find_modules_directly_imported_by(
        "clearml_yolo.adapters.deim.transforms"
    )


def test_lazy_import_allowances_match_real_dynamic_edges(
    graph: grimp.ImportGraph, import_options: UserOptions
) -> None:
    for contract in import_options.contracts_options:
        if contract.get("unmatched_ignore_imports_alerting") != "none":
            continue
        # import-linter omits import_module calls. Its exact optional allowances
        # must still exist in our AST-enriched graph, so stale exceptions fail.
        for edge in contract.get("ignore_imports", []):
            importer, imported = edge.split(" -> ")
            assert imported in graph.find_modules_directly_imported_by(importer), edge


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Path('x').stat()", True),
        ("path.read_text()", True),
        ("pd.read_csv('x')", True),
        ("deps.storage.read_text(path)", False),
        ("deps.storage.stat(path)", False),
        ("deps.storage.read_csv(path)", False),
        ("deps.ground_truth_repository.resolve(reference)", False),
        ("deps.ground_truth_repository.read_bytes(path)", True),
        ("repository.resolve(reference)", True),
        ("pd.ExcelWriter('x.xlsx')", True),
        (
            "reader = deps.storage.read_text\nreader(path)\ndeps.storage.read_csv(path)",
            False,
        ),
    ],
)
def test_application_io_requires_explicit_storage_port(source: str, expected: bool) -> None:
    assert bool(architecture.application_effect_findings(ast.parse(source))) == expected
    assert architecture.core_effect_findings(ast.parse(source))


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


@pytest.mark.parametrize(
    "source",
    [
        "client = create_client()",
        "initialize()",
        "from ultralytics import YOLO",
        "from clearml import Task",
        "def deferred(value=initialize()): pass",
        "async def deferred(*, value=initialize()): pass",
        "@decorate()\ndef deferred(): pass",
        "@decorate\ndef deferred(): pass",
        "def deferred(value: initialize()): pass",
        "def deferred() -> initialize(): pass",
        "class Example(load_base()): pass",
        "class Example(metaclass=load_metaclass()): pass",
        "@decorate()\nclass Example: pass",
        "class Example:\n    def deferred(value=initialize()): pass",
        "callback = lambda value=initialize(): value",
        "if enabled:\n    def deferred(value=initialize()): pass",
        "try:\n    from torch import Tensor\nexcept ImportError:\n    pass",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    pass\nelse:\n    initialize()",
    ],
)
def test_initializer_checks_definition_time_operations(source: str) -> None:
    assert architecture.initializer_findings(ast.parse(source)), source


@pytest.mark.parametrize(
    "source",
    [
        "def deferred():\n    initialize()",
        "async def deferred():\n    initialize()",
        "class Example:\n    def deferred(self):\n        initialize()",
        "callback = lambda: initialize()",
        "if enabled:\n    def deferred():\n        initialize()",
        "class Example(Base, metaclass=Meta):\n    value: int = 1",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from torch import Tensor",
        "from typing import TYPE_CHECKING as checking\nif checking:\n    initialize()",
        "import typing as types\nif types.TYPE_CHECKING:\n    initialize()",
    ],
)
def test_initializer_keeps_deferred_bodies_and_plain_definitions_inert(source: str) -> None:
    assert architecture.initializer_findings(ast.parse(source)) == []


@pytest.mark.parametrize(
    "source",
    [
        "open('data.csv')",
        "Path('data.csv').read_text()",
        "pd.read_csv('data.csv')",
        "import subprocess\nsubprocess.run(['ls'])",
        "importlib.import_module('clearml')",
        "import requests as network\nnetwork.get('https://example.org')",
        "from requests import get as fetch\nfetch('https://example.org')",
        "import httpx\nclient = httpx.Client()\nclient.post('https://example.org')",
        "from urllib.request import urlopen as fetch\nfetch('https://example.org')",
        "from shutil import copyfile as copy\ncopy('source', 'target')",
        "import os as system\nsystem.listdir('.')",
        "from pathlib import Path as Location\np = Location('data')\np.touch()",
        "import subprocess as process\nlaunch = process.run\nlaunch(['program'])",
        "from subprocess import run as launch\ndef deferred():\n    launch(['program'])",
        "import socket as network\nnetwork.create_connection(('example.org', 80))",
        "import os as system\nvalue = system.environ['HOME']",
        "from os import environ as environment\nvalue = environment.get('HOME')",
        "import os\nenvironment = os.environ\nenvironment['MODE'] = 'changed'",
        "import os\ndel os.environ['MODE']",
        "import os\nvalue = dict(os.environ)",
        "import os\ndef deferred(value=os.getenv('HOME')):\n    os = {}",
        "def deferred():\n    from requests import get as fetch\n    fetch('https://example.org')",
        "import os\nclass Example:\n    os = {}\n    def deferred(self):\n        os.listdir('.')",
        "import os\ncallback = lambda: os.listdir('.')",
        "import os\nvalues = [os for os in ()]\nos.listdir('.')",
        # Nested class lookup skips enclosing class namespaces.
        "import os\nclass C:\n    os = {}\n    class D:\n        os.listdir('.')",
        (
            "from os import listdir as scan\nclass C:\n    scan = None\n"
            "    class D:\n        scan('.')"
        ),
        (
            "def enclosing():\n    import os\n    class C:\n        os = {}\n"
            "        class D:\n            os.listdir('.')"
        ),
        "class C:\n    import os\n    class D(os.listdir('.')):\n        pass",
        # Deferred callables see final module bindings; defaults execute eagerly.
        "def f():\n    os.listdir('.')\nimport os",
        "os = {}\ndef f():\n    os.listdir('.')\nimport os",
        "import os\ndef f():\n    reader('.')\nreader = os.listdir",
        "def f():\n    fetch('url')\nfrom requests import get as fetch",
        "callback = lambda: os.listdir('.')\nimport os",
        "class C:\n    def method(self):\n        os.listdir('.')\nimport os",
        "import os\ndef f(value=os.listdir('.')): pass\nos = {}",
        "import os\nclass C:\n    value = os.listdir('.')\nos = {}",
    ],
)
def test_scoped_effect_aliases_are_rejected(source: str) -> None:
    assert architecture.core_effect_findings(ast.parse(source)), source
    assert architecture.application_effect_findings(ast.parse(source)), source


@pytest.mark.parametrize(
    "source",
    [
        "def get(value): return value\nget('pure')",
        "mapping = {}\nmapping.get('key')",
        "import os\ndef pure(os):\n    return os.getenv('key')",
        "from subprocess import run\ndef pure(run):\n    return run('value')",
        "import requests\ndef pure(requests):\n    return requests.get('key')",
        "def first():\n    from requests import get\ndef second():\n    return get('key')",
        "import requests as network\nnetwork = {}\nnetwork.get('key')",
        "from os import environ\ndef pure(environ):\n    return environ['key']",
        "import os\ndef pure():\n    os = {}\n    return os.get('key')",
        (
            "class Example:\n    import requests\n"
            "    def pure(self):\n        return requests.get('key')"
        ),
        "import os\ncallback = lambda os: os.getenv('key')",
        "import os\nvalues = [os.getenv('key') for os in ()]",
        "import os\nvalues = {os.getenv('key') for os in ()}",
        "import os\nvalues = {os.getenv('key'): 1 for os in ()}",
        "import os\nvalues = (os.getenv('key') for os in ())",
        "import requests\nrequests.utils.quote('value')",
        "import subprocess\nsubprocess.list2cmdline(['value'])",
        "import socket\nsocket.inet_aton('127.0.0.1')",
        # Nested class lookup skips enclosing class namespaces.
        "class C:\n    import os\n    class D:\n        os.listdir('.')",
        "import os\nclass C:\n    class D:\n        os = {}\n        os.get('key')",
        (
            "import os\ndef enclosing(os):\n    class C:\n        import os\n"
            "        class D:\n            os.listdir('.')"
        ),
        # Deferred callables see final module bindings; defaults execute eagerly.
        "import os\ndef f(os):\n    os.listdir('.')",
        "def f():\n    os = {}\n    os.get('key')\nimport os",
        "import os\ndef f():\n    os.listdir('.')\nos = {}",
        "def f(reader):\n    reader('.')\nimport os\nreader = os.listdir",
        (
            "os = type('Pure', (), {'listdir': staticmethod(lambda _: [])})\n"
            "def f(value=os.listdir('.')): pass\nimport os"
        ),
        (
            "os = type('Pure', (), {'listdir': staticmethod(lambda _: [])})\n"
            "class C:\n    value = os.listdir('.')\nimport os"
        ),
    ],
)
def test_effect_aliases_do_not_escape_scope_or_override_shadowing(source: str) -> None:
    assert architecture.core_effect_findings(ast.parse(source)) == []
    assert architecture.application_effect_findings(ast.parse(source)) == []


@pytest.mark.parametrize(
    ("target", "valid"),
    [
        (".probe:local", False),
        (".probe:nested", False),
        (".probe:argument", False),
        (".probe:Worker.local", False),
        (".probe:Worker.missing", False),
        (".probe:Worker.run.missing", False),
        (".probe:Worker.Inner.execute.missing", False),
        (".probe:Worker", True),
        (".probe:Worker.run", True),
        (".probe:Worker.Inner.execute", True),
        (".probe:alias.run", True),
        (".probe:renamed.run", True),
        (".probe:module.Worker.run", True),
        (".probe:relative.run", True),
        (".probe:missing_export", False),
        (".probe:cycle", False),
        (".probe:annotation_only", False),
        (".probe:checking_only", False),
        (".probe:comprehension_local", False),
        (":Worker.execute", True),
        (":Worker.missing", False),
    ],
)
def test_runtime_target_resolution_respects_scopes_and_reexports(
    tmp_path: Path, target: str, valid: bool
) -> None:
    package = tmp_path / "clearml_yolo"
    package.mkdir()
    (package / "__init__.py").write_text("from .probe import Worker\n")
    (package / "probe.py").write_text(
        "def outer(argument):\n"
        "    local = 1\n"
        "    def nested(): pass\n"
        "class Worker:\n"
        "    def execute(self): pass\n"
        "    def run(self):\n"
        "        local = 1\n"
        "    class Inner:\n"
        "        def execute(self): pass\n"
        "alias = Worker\n"
        "from clearml_yolo.other import Exported as renamed\n"
        "import clearml_yolo.other as module\n"
        "from .other import Exported as relative\n"
        "from .other import absent as missing_export\n"
        "from .other import cycle\n"
        "annotation_only: str\n"
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    def checking_only(): pass\n"
        "values = [comprehension_local for comprehension_local in ()]\n"
    )
    (package / "other.py").write_text(
        "from .probe import Worker as Exported\n"
        "from .probe import Worker\n"
        "from .probe import cycle\n"
    )
    candidate = grimp.ImportGraph()
    candidate.add_module("clearml_yolo")
    candidate.add_module("clearml_yolo.probe")
    candidate.add_module("clearml_yolo.other")
    findings = architecture.target_findings({f"clearml_yolo{target}"}, candidate, tmp_path)
    assert bool(findings) is not valid, findings


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("from importlib import import_module as load\nload('torch')", True),
        ("import importlib as loader\nloader.import_module('torch')", True),
        ("import importlib\nload = importlib.import_module\nload('torch')", True),
        ("__import__('torch')", True),
        (
            (
                "from typing import TYPE_CHECKING\nfrom importlib import import_module\n"
                "if TYPE_CHECKING:\n    import_module('torch')"
            ),
            True,
        ),
        (
            (
                "from importlib import import_module\n"
                "def pure(import_module):\n    import_module('torch')"
            ),
            False,
        ),
    ],
)
@pytest.mark.parametrize(
    "sdk",
    [
        "clearml",
        "torch",
        "torchvision",
        "timm",
        "rfdetr",
        "pytorch_lightning",
        "onnx",
        "tensorrt",
        "safetensors",
    ],
)
def test_dynamic_import_graph_resolves_scoped_import_aliases(
    tmp_path: Path,
    sdk: str,
    source: str,
    expected: bool,
    graph: grimp.ImportGraph,
    import_options: UserOptions,
) -> None:
    package = tmp_path / "clearml_yolo/adapters/storage"
    package.mkdir(parents=True)
    (package / "helper.py").write_text(source.replace("torch", sdk))
    candidate = deepcopy(graph)
    candidate.add_module("clearml_yolo.adapters.storage.helper")
    architecture.add_dynamic_imports(candidate, tmp_path)
    contract = _contract(import_options, f"{sdk} SDK has explicit owners")
    assert contract.check(candidate, verbose=False).kept is not expected


def test_runtime_target_inventory_includes_nested_colon_attributes(tmp_path: Path) -> None:
    package = tmp_path / "clearml_yolo"
    package.mkdir()
    (package / "worker.py").write_text("TARGET = 'clearml_yolo.worker:Worker.execute'\n")
    config = tmp_path / "pyproject.toml"
    config.write_text("[project.scripts]\nworker='clearml_yolo.worker:Worker.execute'\n")
    assert architecture.runtime_targets(tmp_path, config) == {"clearml_yolo.worker:Worker.execute"}


@pytest.mark.parametrize(
    ("source", "target", "valid"),
    [
        ("def f(): pass\nclass C:\n    run = f", "C.run", True),
        ("def f(): pass\nclass C:\n    run = f\n    alias = run", "C.alias", True),
        ("def f(): pass\nclass C:\n    f = f\n    run = f", "C.run", True),
        ("class C:\n    def f(): pass\n    run = f", "C.run", True),
        ("class C:\n    run = missing", "C.run", False),
        ("class C:\n    run = f\n    def f(): pass", "C.run", False),
        ("class C:\n    def f(): pass\n    class D:\n        run = f", "C.D.run", False),
        (
            "def f(): pass\nclass C:\n    f = None\n    class D:\n        run = f",
            "C.D.run",
            True,
        ),
        ("def f(): pass\nclass C:\n    run = f.missing", "C.run", False),
    ],
)
def test_class_assignment_targets_follow_lexical_simple_alias_lookup(
    tmp_path: Path, source: str, target: str, valid: bool
) -> None:
    package = tmp_path / "clearml_yolo"
    package.mkdir()
    (package / "probe.py").write_text(source)
    candidate = grimp.ImportGraph()
    candidate.add_module("clearml_yolo.probe")
    findings = architecture.target_findings({f"clearml_yolo.probe:{target}"}, candidate, tmp_path)
    assert bool(findings) is not valid, findings


@pytest.mark.parametrize(
    ("source", "forbidden"),
    [
        ('if selection == "cy_queue": raise ValueError("retired")', False),
        ('importlib.import_module("cy_queue")', True),
        ('if importlib.import_module("cy_queue") == other: pass', True),
        ('subprocess.run(["python", "-m", "cy_queue.entrypoints.queue"])', True),
    ],
)
def test_dynamic_queue_imports_are_distinct_from_rejected_selector_values(
    tmp_path: Path, source: str, forbidden: bool
) -> None:
    module = tmp_path / "clearml_yolo" / "entrypoints" / "train.py"
    module.parent.mkdir(parents=True)
    module.write_text(source)
    assert bool(architecture.runtime_boundary_findings(tmp_path)) is forbidden
