"""Bulk preparation preserves native selection and durable retry semantics."""

import importlib
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

import pytest

from clearml_yolo.core.assets import AssetSpec, HubAsset, ResolvedAsset
from clearml_yolo.core.batch_estimation import ModelVariant


@dataclass
class Catalogue:
    module: ModuleType
    root: Path
    revision: str = "v1"
    selections: tuple[ModelVariant, ...] = (
        ModelVariant(
            selection="ultralytics/yolo11n",
            backend="ultralytics",
            preset="default",
            architecture="yolo11n.pt",
        ),
    )
    attempts: list[str] = field(default_factory=list)
    failures: set[str] = field(default_factory=set)
    discoveries: set[str] = field(default_factory=set)
    interrupt: bool = False

    def spec(self, filename: str, *, backend: str = "ultralytics") -> AssetSpec:
        if filename in self.discoveries:
            raise ValueError("unstructured-private-token")
        return AssetSpec(
            backend=backend,
            preset="default",
            filename=filename,
            canonical_url="https://weights.example/" + filename,
            revision=self.revision,
            override="model.train.weights",
            native_cache=self.root,
        )

    def resolve(self, spec: AssetSpec) -> ResolvedAsset:
        self.attempts.append(spec.filename)
        if self.interrupt:
            raise KeyboardInterrupt
        if spec.filename in self.failures:
            raise RuntimeError("unstructured-private-token")
        return ResolvedAsset(
            canonical_url=spec.canonical_url,
            path=self.root / spec.filename,
            sha256="a" * 64,
            override=spec.override,
        )


@pytest.fixture
def catalogue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Catalogue:
    module = importlib.import_module("clearml_yolo.adapters.assets.preparation")
    fixture = Catalogue(module, tmp_path / "native")
    monkeypatch.setattr(module, "model_catalogue", lambda: fixture.selections)
    monkeypatch.setattr(module, "yolo_asset", fixture.spec)
    monkeypatch.setattr(module, "rfdetr_asset", lambda preset: fixture.spec(preset + ".pth"))
    monkeypatch.setattr(
        module, "torchvision_asset", lambda preset, **kwargs: fixture.spec(preset + ".pth")
    )
    monkeypatch.setattr(module, "deim_backbone_asset", lambda preset: fixture.spec(preset + ".pt"))
    monkeypatch.setattr(module, "resolve_asset", fixture.resolve)
    return fixture


def test_automatic_completion_is_reused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    preparation = importlib.import_module("clearml_yolo.adapters.assets.preparation")
    from clearml_yolo.core.assets import AssetSpec, ResolvedAsset
    from clearml_yolo.core.batch_estimation import ModelVariant

    selection = ModelVariant(
        selection="ultralytics/yolo11n",
        backend="ultralytics",
        preset="default",
        architecture="yolo11n.pt",
    )
    monkeypatch.setattr(preparation, "model_catalogue", lambda: (selection,))
    monkeypatch.setattr(
        preparation,
        "yolo_asset",
        lambda filename: AssetSpec(
            backend="ultralytics",
            preset="default",
            filename=filename,
            canonical_url="https://weights.example/" + filename,
            override="ultralytics.model",
            native_cache=tmp_path / "native",
        ),
    )
    attempts: list[str] = []

    def resolve(spec: AssetSpec) -> ResolvedAsset:
        attempts.append(spec.filename)
        return ResolvedAsset(
            canonical_url=spec.canonical_url,
            path=tmp_path / spec.filename,
            sha256="a" * 64,
            override=spec.override,
        )

    monkeypatch.setattr(preparation, "resolve_asset", resolve)
    first = preparation.prepare_catalogue(automatic=True)
    second = preparation.prepare_catalogue(automatic=True)
    assert not first.skipped
    assert second.skipped
    assert attempts == ["yolo11n.pt"]
    assert second.assets == first.assets


def test_source_provenance_uses_extracted_manifest_not_archive_digest(
    catalogue: Catalogue, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalogue.selections = (
        ModelVariant(selection="deimv2/s", backend="deimv2", preset="s", architecture="deimv2/s"),
    )
    source = catalogue.spec("source.tar.gz").model_copy(update={"kind": "deim-source"})
    monkeypatch.setattr(catalogue.module, "deim_source_asset", lambda: source)
    extracted: list[Path] = []
    manifest_record = ResolvedAsset(
        canonical_url=source.canonical_url,
        path=catalogue.root / "source",
        content_kind="source-tree",
        sha256="b" * 64,
        override=source.override,
    )
    monkeypatch.setattr(
        catalogue.module, "existing_source", lambda spec: manifest_record if extracted else None
    )

    def extract(record: ResolvedAsset) -> Path:
        extracted.append(record.path)
        return manifest_record.path

    monkeypatch.setattr(catalogue.module, "extract_resolved_source", extract)
    result = catalogue.module.prepare_catalogue(automatic=False)
    sources = [asset for asset in result.assets if asset.content_kind == "source-tree"]
    assert sources == [manifest_record]


def test_resolution_failures_keep_safe_actionable_diagnostics(
    catalogue: Catalogue, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.assets.resolver import AssetResolutionError

    def fail(spec: AssetSpec) -> ResolvedAsset:
        raise AssetResolutionError("Copy checkpoint to /offline/weights/yolo11n.pt")

    monkeypatch.setattr(catalogue.module, "resolve_asset", fail)
    result = catalogue.module.prepare_catalogue(automatic=False)
    assert "/offline/weights/yolo11n.pt" in result.failures[0].message


@pytest.mark.parametrize("chain", ["cause", "context"])
def test_synthetic_chained_failure_keeps_public_report_and_discards_opaque_messages(
    catalogue: Catalogue,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    chain: str,
) -> None:
    """Inject a boundary fault; ordinary resolver transport failures discard their causes."""
    from loguru import logger

    from clearml_yolo.adapters.assets.resolver import AssetResolutionError
    from clearml_yolo.entrypoints import download_weights

    opaque_marker = "synthetic-opaque-cause-secret"
    public_marker = "synthetic-public-credential"
    destination = "/offline/weights/yolo11n.pt"

    def fail(spec: AssetSpec) -> ResolvedAsset:
        try:
            raise RuntimeError(opaque_marker)  # noqa: TRY301 - synthetic transport fault
        except RuntimeError as error:
            public = AssetResolutionError(
                f"Copy checkpoint to {destination}; "
                f"source=https://user:{public_marker}@weights.example/{spec.filename}"
            )
            if chain == "cause":
                raise public from error
            raise public  # noqa: B904 - synthetic fault deliberately retains implicit context

    monkeypatch.setattr(catalogue.module, "resolve_asset", fail)
    warnings: list[str] = []
    sink = logger.add(warnings.append, format="{message}", level="WARNING")
    try:
        result = catalogue.module.prepare_catalogue(automatic=True)
    finally:
        logger.remove(sink)
    receipt = (
        tmp_path / ".cache/clearml-yolo/preparation" / f"{result.fingerprint}.json"
    ).read_text(encoding="utf-8")
    with pytest.raises(SystemExit) as exit_info:
        download_weights.main([])
    assert exit_info.value.code == 1
    report = capsys.readouterr().out
    for observed in (result.model_dump_json(), receipt, report, "".join(warnings)):
        assert destination in observed
        assert opaque_marker not in observed
        assert public_marker not in observed


@pytest.mark.parametrize("change", ["repository", "revision", "filename", "root"])
def test_hub_receipt_covers_native_repository_revision_representation_and_location(
    catalogue: Catalogue, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    catalogue.selections = (
        ModelVariant(
            selection="fcos/dinov2_small",
            backend="fcos",
            preset="dinov2_small",
            architecture="fcos/dinov2_small",
        ),
    )
    hub = HubAsset(repository="timm/backbone", cache_dir=catalogue.root)

    def spec(preset: str, *, backend: str) -> AssetSpec:
        return catalogue.spec("pytorch_model.bin").model_copy(update={"hub": hub})

    monkeypatch.setattr(catalogue.module, "torchvision_asset", spec)
    first = catalogue.module.prepare_catalogue(automatic=True)
    assert first.locations == (catalogue.root / "models--timm--backbone",)
    updates: dict[str, object] = {
        "repository": "timm/other",
        "revision": "v2",
        "filename": "model.safetensors",
        "root": catalogue.root / "other",
    }
    hub = hub.model_copy(update={"cache_dir" if change == "root" else change: updates[change]})
    second = catalogue.module.prepare_catalogue(automatic=True)
    assert first.fingerprint != second.fingerprint
    assert not second.skipped


def test_partial_attempt_suppresses_automatic_but_manual_retries(catalogue: Catalogue) -> None:
    catalogue.failures.add("yolo11n.pt")
    first = catalogue.module.prepare_catalogue(automatic=True)
    assert len(first.failures) == 1
    assert "unstructured-private-token" not in first.model_dump_json()
    assert catalogue.module.prepare_catalogue(automatic=True).skipped
    catalogue.failures.clear()
    recovered = catalogue.module.prepare_catalogue(automatic=False)
    assert not recovered.failures
    assert not recovered.skipped
    assert catalogue.attempts == ["yolo11n.pt", "yolo11n.pt"]


@pytest.mark.parametrize("change", ["revision", "root", "selections"])
def test_changed_identity_location_or_catalogue_reopens_attempt(
    catalogue: Catalogue, change: str
) -> None:
    first = catalogue.module.prepare_catalogue(automatic=True)
    if change == "revision":
        catalogue.revision = "v2"
    elif change == "root":
        catalogue.root /= "other"
    else:
        catalogue.selections += (
            ModelVariant(
                selection="ultralytics/yolo11s",
                backend="ultralytics",
                preset="default",
                architecture="yolo11s.pt",
            ),
        )
    second = catalogue.module.prepare_catalogue(automatic=True)
    assert second.fingerprint != first.fingerprint
    assert not second.skipped
    assert len(catalogue.attempts) >= 2


def test_relative_native_cache_uses_consuming_working_directory(
    catalogue: Catalogue, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    catalogue.root = Path("weights")
    monkeypatch.chdir(tmp_path)
    first = catalogue.module.prepare_catalogue(automatic=True)
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    second = catalogue.module.prepare_catalogue(automatic=True)
    assert first.locations == (tmp_path / "weights" / "yolo11n.pt",)
    assert second.locations == (other / "weights" / "yolo11n.pt",)
    assert first.fingerprint != second.fingerprint


@pytest.mark.parametrize("previous_completed", [False, True])
def test_interrupted_manual_attempt_remains_unfinished(
    catalogue: Catalogue, previous_completed: bool
) -> None:
    if previous_completed:
        catalogue.module.prepare_catalogue(automatic=True)
    catalogue.interrupt = True
    with pytest.raises(KeyboardInterrupt):
        catalogue.module.prepare_catalogue(automatic=False)
    catalogue.interrupt = False
    result = catalogue.module.prepare_catalogue(automatic=True)
    assert not result.skipped
    assert not result.failures


def test_concurrent_automatic_starts_share_completed_pass(
    catalogue: Catalogue, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered = threading.Event()
    release = threading.Event()

    def blocked(spec: AssetSpec) -> ResolvedAsset:
        entered.set()
        assert release.wait(5)
        return catalogue.resolve(spec)

    monkeypatch.setattr(catalogue.module, "resolve_asset", blocked)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(catalogue.module.prepare_catalogue, automatic=True)
        assert entered.wait(5)
        second = executor.submit(catalogue.module.prepare_catalogue, automatic=True)
        release.set()
        results = (first.result(5), second.result(5))
    assert sum(result.skipped for result in results) == 1
    assert catalogue.attempts == ["yolo11n.pt"]


def test_discovery_failure_is_local_and_secret_safe(catalogue: Catalogue) -> None:
    catalogue.selections += (
        ModelVariant(
            selection="ultralytics/yolo11s",
            backend="ultralytics",
            preset="default",
            architecture="yolo11s.pt",
        ),
    )
    catalogue.discoveries.add("yolo11n.pt")
    result = catalogue.module.prepare_catalogue(automatic=True)
    assert catalogue.attempts == ["yolo11s.pt"]
    assert result.failures[0].selection == "ultralytics/yolo11n"
    assert "unstructured-private-token" not in result.model_dump_json()
    assert catalogue.module.prepare_catalogue(automatic=True).skipped


def test_shared_backbones_are_resolved_once_but_each_selection_changes_identity(
    catalogue: Catalogue,
) -> None:
    catalogue.selections = tuple(
        ModelVariant(
            selection=f"{backend}/resnet50_fpn",
            backend=backend,
            preset="resnet50_fpn",
            architecture=f"{backend}/resnet50_fpn",
        )
        for backend in ("fasterrcnn", "fcos")
    )
    result = catalogue.module.prepare_catalogue(automatic=False)
    assert catalogue.attempts == ["resnet50_fpn.pth"]
    assert len(result.assets) == 1
    catalogue.selections = catalogue.selections[:1]
    assert catalogue.module.prepare_catalogue(automatic=True).fingerprint != result.fingerprint


def test_bulk_catalogue_excludes_restricted_models_and_extracts_source_once(
    catalogue: Catalogue, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.core.batch_estimation import model_catalogue

    catalogue.selections = model_catalogue()
    source = catalogue.spec("source.tar.gz").model_copy(update={"kind": "deim-source"})
    monkeypatch.setattr(catalogue.module, "deim_source_asset", lambda: source)
    extracted: list[Path] = []
    monkeypatch.setattr(
        catalogue.module,
        "existing_source",
        lambda spec: (
            ResolvedAsset(
                canonical_url=source.canonical_url,
                path=catalogue.root / "source",
                content_kind="source-tree",
                sha256="b" * 64,
                override=source.override,
            )
            if extracted
            else None
        ),
    )

    def extract(record: ResolvedAsset) -> Path:
        extracted.append(record.path)
        return record.path.with_suffix("")

    monkeypatch.setattr(catalogue.module, "extract_resolved_source", extract)
    result = catalogue.module.prepare_catalogue(automatic=False)
    assert not result.failures
    assert sum(name.startswith(("yolo",)) for name in catalogue.attempts) == 44
    assert "dinov3_small.pth" not in catalogue.attempts
    assert "l.pt" not in catalogue.attempts
    assert "x.pt" not in catalogue.attempts
    assert catalogue.attempts.count("source.tar.gz") == 1
    assert len(extracted) == 1
    assert len(catalogue.attempts) == 56


def test_storage_failure_is_result_not_automatic_startup_error(
    catalogue: Catalogue, monkeypatch: pytest.MonkeyPatch
) -> None:
    def reject(path: Path) -> Path:
        raise PermissionError("unstructured-private-token")

    monkeypatch.setattr(catalogue.module, "write_path", reject)
    result = catalogue.module.prepare_catalogue(automatic=True)
    assert result.failures
    assert not catalogue.attempts
    assert "unstructured-private-token" not in result.model_dump_json()


def test_global_discovery_error_is_nonfatal_and_retryable(
    catalogue: Catalogue, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable() -> tuple[ModelVariant, ...]:
        raise RuntimeError("unstructured-private-token")

    with monkeypatch.context() as scoped:
        scoped.setattr(catalogue.module, "model_catalogue", unavailable)
        result = catalogue.module.prepare_catalogue(automatic=True)
    assert result.failures[0].selection == "catalogue"
    assert "unstructured-private-token" not in result.model_dump_json()
    recovered = catalogue.module.prepare_catalogue(automatic=True)
    assert not recovered.skipped
    assert not recovered.failures


@pytest.mark.parametrize("corruption", ["truncated", "wrong-fingerprint"])
def test_incomplete_receipt_cannot_suppress_next_attempt(
    catalogue: Catalogue, tmp_path: Path, corruption: str
) -> None:
    result = catalogue.module.prepare_catalogue(automatic=True)
    receipt = tmp_path / ".cache" / "clearml-yolo" / "preparation" / f"{result.fingerprint}.json"
    receipt.write_text(
        "{"
        if corruption == "truncated"
        else result.model_copy(update={"fingerprint": "other"}).model_dump_json(),
        encoding="utf-8",
    )
    recovered = catalogue.module.prepare_catalogue(automatic=True)
    assert not recovered.skipped
    assert catalogue.attempts == ["yolo11n.pt", "yolo11n.pt"]


def test_fresh_command_help_never_imports_clearml_or_opens_network(tmp_path: Path) -> None:
    script = """
import importlib.abc
import socket
import sys

class NoClearML(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "clearml" or fullname.startswith("clearml."):
            raise AssertionError("help imported ClearML")

def no_network(*args, **kwargs):
    raise AssertionError("help opened network")

sys.meta_path.insert(0, NoClearML())
socket.socket.connect = no_network
from clearml_yolo.entrypoints.download_weights import main
main(["--help"])
"""
    result = subprocess.run(  # noqa: S603 - fixed inert command and isolated test path
        [sys.executable, "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "cy-download-weights" in result.stdout
    assert not list(tmp_path.iterdir())


def test_command_help_does_not_prepare(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    command = importlib.import_module("clearml_yolo.entrypoints.download_weights")

    def forbidden(*, automatic: bool) -> None:
        pytest.fail("help invoked preparation")

    monkeypatch.setattr(command, "prepare_catalogue", forbidden)
    with pytest.raises(SystemExit) as exit_info:
        command.main(["--help"])
    assert exit_info.value.code == 0
    assert "cy-download-weights" in capsys.readouterr().out


def test_command_reports_destinations_and_incomplete_exit(
    catalogue: Catalogue, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    command = importlib.import_module("clearml_yolo.entrypoints.download_weights")
    monkeypatch.setattr(command, "prepare_catalogue", catalogue.module.prepare_catalogue)
    command.main([])
    assert str(catalogue.root / "yolo11n.pt") in capsys.readouterr().out
    catalogue.failures.add("yolo11n.pt")
    with pytest.raises(SystemExit) as exit_info:
        command.main([])
    assert exit_info.value.code == 1
    assert "ultralytics/yolo11n" in capsys.readouterr().out


@pytest.mark.parametrize("name", ["pipeline", "train", "predict", "val", "metrics", "export"])
@pytest.mark.parametrize("pretrained", [True, False, "relative/weights.pt"])
def test_only_actual_pipeline_execution_prepares_and_keeps_custom_values(
    name: str, pretrained: bool | str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from omegaconf import OmegaConf

    from clearml_yolo.core.assets import PreparationResult
    from clearml_yolo.entrypoints.hydra import common

    observed: list[str] = []

    def prepare(*, automatic: bool) -> PreparationResult:
        assert automatic
        observed.append("prepared")
        return PreparationResult(fingerprint="test")

    def workflow(ultralytics: dict[str, object]) -> None:
        assert ultralytics == {
            "model": "custom.yaml",
            "pretrained": pretrained,
            "resume": "resume.pt",
            "batch": 3,
        }
        observed.append("executed")

    monkeypatch.setattr(common, "prepare_catalogue", prepare)
    config = OmegaConf.create(
        {
            "ultralytics": {
                "model": "custom.yaml",
                "pretrained": pretrained,
                "resume": "resume.pt",
                "batch": 3,
            }
        }
    )
    before = OmegaConf.to_container(config, resolve=False)
    common._execute_direct(name, config, workflow)
    assert observed == (["prepared", "executed"] if name == "pipeline" else ["executed"])
    assert OmegaConf.to_container(config, resolve=False) == before
