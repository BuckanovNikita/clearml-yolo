"""Recover described native checkpoints using only ZIP bytes and a stub ClearML SDK."""

import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from zipfile import ZipFile

import pytest

from clearml_yolo.adapters.clearml.models import (
    resolve_task_model,
    resolve_weights_with_identity,
    source_model_links,
)
from clearml_yolo.adapters.storage.checkpoint import (
    bind_checkpoint,
    read_checkpoint_descriptor,
)
from clearml_yolo.adapters.storage.identity import checkpoint_sha256
from clearml_yolo.application.contracts import ModelRef
from clearml_yolo.application.use_cases.compare import _resolve_model
from clearml_yolo.core.models import CheckpointDescriptor, CheckpointMetadata, Preprocessing
from clearml_yolo.entrypoints.composition import build_dependencies

TASK_ID = "a" * 32
TRAINING_TASK_ID = "b" * 32
NATIVE_CASES = [
    ("deimv2", "s", ".pth"),
    ("rfdetr", "small", ".ckpt"),
    ("fasterrcnn", "resnet50_fpn", ".pth"),
]


class DownloadedModel:
    def __init__(self, path: Path, *, role: str | None = "best") -> None:
        self.id = path.stem
        self.name = "published-native-detector"
        self.original_task = TRAINING_TASK_ID
        self.url = f"https://files.example/models/{path.name}?download=1"
        self.path = path
        self.downloads = 0
        self.metadata = {
            "clearml_yolo_effective_model_name": "trained-native-detector",
            "clearml_yolo_training_task_id": TRAINING_TASK_ID,
            "clearml_yolo_checkpoint_sha256": checkpoint_sha256(path),
        }
        if role is not None:
            self.metadata["clearml_yolo_checkpoint_role"] = role

    def get_metadata(self, name: str) -> str | None:
        return self.metadata.get(name)

    def get_local_copy(self) -> str:
        self.downloads += 1
        return str(self.path)


class DownloadedArtifact:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.url = f"https://files.example/artifacts/{path.name}"
        self.downloads = 0

    def get_local_copy(self) -> str:
        self.downloads += 1
        return str(self.path)


class RecoveryTask:
    def __init__(
        self,
        outputs: list[DownloadedModel],
        artifacts: dict[str, DownloadedArtifact] | None = None,
    ) -> None:
        self.id = TASK_ID
        self.name = "report-that-references-original-training"
        self.outputs = outputs
        self.artifacts = artifacts or {}

    def get_models(self) -> dict[str, list[DownloadedModel]]:
        return {"output": self.outputs}

    def get_output_log_web_page(self) -> str:
        return f"https://app.example/tasks/{self.id}"


@pytest.fixture
def install_sdk(monkeypatch: pytest.MonkeyPatch) -> Callable[[RecoveryTask], None]:
    def install(task: RecoveryTask) -> None:
        sdk = ModuleType("clearml")

        class Task:
            @staticmethod
            def get_task(*, task_id: str) -> RecoveryTask:
                assert task_id == task.id
                return task

        def model(*, model_id: str) -> DownloadedModel:
            return next(output for output in task.outputs if output.id == model_id)

        sdk.Task = Task  # type: ignore[attr-defined]
        sdk.Model = model  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "clearml", sdk)

    return install


def standalone_checkpoint(
    directory: Path, backend: str, preset: str, suffix: str
) -> tuple[Path, CheckpointDescriptor]:
    source = directory / ("native-best" + suffix)
    with ZipFile(source, "w") as archive:
        archive.writestr("weights/data.pkl", b"tiny-native-checkpoint-fixture")
    metadata = CheckpointMetadata.model_validate(
        {
            "backend": backend,
            "preset": preset,
            "class_names": ("0001", "施工"),
            "preprocessing": Preprocessing(resize="stretch", size=64),
            "dependencies": {"fixture": "1"},
        }
    )
    descriptor = bind_checkpoint(source, metadata)
    downloaded = directory / ("downloaded-model" + suffix)
    shutil.copyfile(source, downloaded)
    assert not downloaded.with_name(downloaded.name + ".model.json").exists()
    return downloaded, descriptor


@pytest.mark.parametrize(("backend", "preset", "suffix"), NATIVE_CASES)
@pytest.mark.parametrize("route", ["task", "model"])
def test_native_download_recovers_embedded_descriptor_and_original_identity(
    tmp_path: Path,
    install_sdk: Callable[[RecoveryTask], None],
    backend: str,
    preset: str,
    suffix: str,
    route: str,
) -> None:
    downloaded, descriptor = standalone_checkpoint(tmp_path, backend, preset, suffix)
    model = DownloadedModel(downloaded)
    install_sdk(RecoveryTask([model]))
    path, identity = resolve_weights_with_identity(
        TASK_ID if route == "task" else f"clearml://{model.id}"
    )
    assert path == downloaded
    assert isinstance(path, Path)
    assert read_checkpoint_descriptor(path) == descriptor
    assert descriptor.class_names == ("0001", "施工")
    assert identity is not None
    assert identity.model_name == "trained-native-detector"
    assert identity.training_task_id == TRAINING_TASK_ID
    assert identity.model_id == model.id
    assert identity.checkpoint_sha256 == descriptor.checkpoint_sha256 == checkpoint_sha256(path)
    assert model.downloads == 1


@pytest.mark.parametrize("suffix", [".pth", ".ckpt"])
def test_marked_native_best_outweighs_legacy_best_filename_and_later_epoch(
    tmp_path: Path, install_sdk: Callable[[RecoveryTask], None], suffix: str
) -> None:
    downloaded, descriptor = standalone_checkpoint(tmp_path, "deimv2", "s", suffix)
    legacy_path = tmp_path / "best.pt"
    legacy_path.write_bytes(b"legacy")
    epoch_path = tmp_path / "epoch-99.ckpt"
    epoch_path.write_bytes(b"unmarked epoch")
    legacy = DownloadedModel(legacy_path, role=None)
    native = DownloadedModel(downloaded)
    epoch = DownloadedModel(epoch_path, role=None)
    install_sdk(RecoveryTask([legacy, native, epoch]))
    before_download = source_model_links(TASK_ID)
    assert before_download["model_id"] == native.id
    assert sum(model.downloads for model in (legacy, native, epoch)) == 0
    path, links = resolve_task_model(TASK_ID)
    assert path == downloaded
    assert links == before_download
    assert links["checkpoint_sha256"] == descriptor.checkpoint_sha256
    assert (legacy.downloads, native.downloads, epoch.downloads) == (0, 1, 0)


def test_duplicate_native_best_markers_fail_without_download(
    tmp_path: Path, install_sdk: Callable[[RecoveryTask], None]
) -> None:
    downloaded, _ = standalone_checkpoint(tmp_path, "rfdetr", "small", ".ckpt")
    first, second = DownloadedModel(downloaded), DownloadedModel(downloaded)
    install_sdk(RecoveryTask([first, second]))
    with pytest.raises(ValueError, match="Ambiguous best output"):
        resolve_task_model(TASK_ID)
    assert first.downloads == second.downloads == 0


@pytest.mark.parametrize("route", ["task", "model"])
def test_native_download_rejects_changed_bytes_even_without_descriptor_sidecar(
    tmp_path: Path, install_sdk: Callable[[RecoveryTask], None], route: str
) -> None:
    downloaded, _ = standalone_checkpoint(tmp_path, "rfdetr", "small", ".ckpt")
    model = DownloadedModel(downloaded)
    with ZipFile(downloaded, "a") as archive:
        archive.writestr("weights/data/0", b"replacement-tensor")
    install_sdk(RecoveryTask([model]))
    with pytest.raises(ValueError, match="SHA-256"):
        resolve_weights_with_identity(TASK_ID if route == "task" else f"clearml://{model.id}")


@pytest.mark.parametrize("suffix", [".pth", ".ckpt"])
@pytest.mark.parametrize("route", ["task", "model"])
def test_native_download_requires_embedded_detector_metadata(
    tmp_path: Path, install_sdk: Callable[[RecoveryTask], None], suffix: str, route: str
) -> None:
    downloaded = tmp_path / ("undescribed" + suffix)
    with ZipFile(downloaded, "w") as archive:
        archive.writestr("weights/data.pkl", b"undescribed-native-weights")
    model = DownloadedModel(downloaded)
    install_sdk(RecoveryTask([model]))
    with pytest.raises(ValueError, match=r"described|descriptor|metadata"):
        resolve_weights_with_identity(TASK_ID if route == "task" else f"clearml://{model.id}")


@pytest.mark.parametrize("suffix", [".pth", ".ckpt"])
def test_explicit_task_reference_can_bind_raw_native_metadata(
    tmp_path: Path, install_sdk: Callable[[RecoveryTask], None], suffix: str
) -> None:
    downloaded = tmp_path / ("external" + suffix)
    downloaded.write_bytes(b"raw external native checkpoint")
    original = downloaded.read_bytes()
    install_sdk(RecoveryTask([DownloadedModel(downloaded)]))
    reference = ModelRef(
        source="clearml",
        task_id=TASK_ID,
        thresholds={"0001": 0.4},
        backend="fasterrcnn",
        preset="resnet50_fpn",
        class_names=("0001",),
        preprocessing=Preprocessing(resize="letterbox", size=64),
    )
    dependencies = build_dependencies()
    resolved = _resolve_model(
        reference,
        "recovery-tests",
        exclude_task_id=None,
        automatic_absence_is_skip=False,
        deps=dependencies,
    )
    assert resolved.weights == downloaded
    assert resolved.backend_assertions["class_names"] == ["0001"]
    assert resolved.identity is not None
    assert resolved.identity.checkpoint_sha256 == checkpoint_sha256(downloaded)
    assert dependencies.model.trained_imgsz(downloaded) == 64
    assert read_checkpoint_descriptor(downloaded) is None
    assert downloaded.read_bytes() == original


def test_raw_task_assertions_cannot_replace_embedded_vocabulary(
    tmp_path: Path, install_sdk: Callable[[RecoveryTask], None]
) -> None:
    downloaded, descriptor = standalone_checkpoint(tmp_path, "rfdetr", "small", ".ckpt")
    install_sdk(RecoveryTask([DownloadedModel(downloaded)]))
    assertions = CheckpointMetadata.model_validate(
        descriptor.model_dump(exclude={"checkpoint_sha256"}) | {"class_names": ("other",)}
    )
    with pytest.raises(ValueError, match="assertions disagree"):
        resolve_task_model(TASK_ID, raw_metadata=assertions)


@pytest.mark.parametrize("route", ["task", "model"])
def test_legacy_pt_remains_recoverable_without_invented_detector_metadata(
    tmp_path: Path, install_sdk: Callable[[RecoveryTask], None], route: str
) -> None:
    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"historical-nonzip-checkpoint")
    model = DownloadedModel(checkpoint, role=None)
    install_sdk(RecoveryTask([model]))
    path, identity = resolve_weights_with_identity(
        TASK_ID if route == "task" else f"clearml://{model.id}"
    )
    assert path == checkpoint
    assert read_checkpoint_descriptor(checkpoint) is None
    assert identity is not None
    assert identity.checkpoint_sha256 == checkpoint_sha256(checkpoint)


@pytest.mark.parametrize("suffix", [".pth", ".ckpt"])
def test_generic_checkpoint_artifact_recovers_standalone_native_descriptor(
    tmp_path: Path, install_sdk: Callable[[RecoveryTask], None], suffix: str
) -> None:
    downloaded, descriptor = standalone_checkpoint(tmp_path, "deimv2", "s", suffix)
    artifact = DownloadedArtifact(downloaded)
    install_sdk(RecoveryTask([], {"checkpoint": artifact}))
    path, links = resolve_task_model(TASK_ID)
    assert path == downloaded
    assert read_checkpoint_descriptor(path) == descriptor
    assert links["artifact_name"] == "checkpoint"
    assert links["checkpoint_sha256"] == descriptor.checkpoint_sha256
    assert "model_id" not in links
    assert artifact.downloads == 1


@pytest.mark.parametrize("suffix", [".pth", ".ckpt"])
def test_native_best_filename_is_selected_before_last_registered_epoch(
    tmp_path: Path, install_sdk: Callable[[RecoveryTask], None], suffix: str
) -> None:
    downloaded, descriptor = standalone_checkpoint(tmp_path, "deimv2", "s", suffix)
    best_path = tmp_path / ("best" + suffix)
    shutil.copyfile(downloaded, best_path)
    best = DownloadedModel(best_path, role=None)
    epoch = DownloadedModel(downloaded, role=None)
    install_sdk(RecoveryTask([best, epoch]))
    path, links = resolve_task_model(TASK_ID)
    assert path == best_path
    assert links["model_id"] == best.id
    assert read_checkpoint_descriptor(path) == descriptor
    assert (best.downloads, epoch.downloads) == (1, 0)


@pytest.mark.parametrize("suffix", [".pth", ".ckpt"])
def test_native_best_artifact_filename_is_recoverable_without_output_models(
    tmp_path: Path, install_sdk: Callable[[RecoveryTask], None], suffix: str
) -> None:
    downloaded, descriptor = standalone_checkpoint(tmp_path, "deimv2", "s", suffix)
    best = DownloadedArtifact(downloaded)
    epoch = DownloadedArtifact(downloaded)
    install_sdk(RecoveryTask([], {"epoch-99" + suffix: epoch, "best" + suffix: best}))
    path, links = resolve_task_model(TASK_ID)
    assert path == downloaded
    assert links["artifact_name"] == "best" + suffix
    assert read_checkpoint_descriptor(path) == descriptor
    assert (best.downloads, epoch.downloads) == (1, 0)


@pytest.mark.parametrize("suffix", [".pth", ".ckpt"])
def test_duplicate_native_best_filenames_are_ambiguous(
    tmp_path: Path, install_sdk: Callable[[RecoveryTask], None], suffix: str
) -> None:
    downloaded, _ = standalone_checkpoint(tmp_path, "deimv2", "s", suffix)
    first, second = DownloadedModel(downloaded, role=None), DownloadedModel(downloaded, role=None)
    first.url = f"https://files.example/run-one/best{suffix}"
    second.url = f"https://files.example/run-two/best{suffix}?signature=opaque"
    install_sdk(RecoveryTask([first, second]))
    with pytest.raises(ValueError, match="Ambiguous"):
        resolve_task_model(TASK_ID)
    assert first.downloads == second.downloads == 0


def test_unmarked_native_outputs_keep_last_registered_fallback(
    tmp_path: Path, install_sdk: Callable[[RecoveryTask], None]
) -> None:
    downloaded, _ = standalone_checkpoint(tmp_path, "rfdetr", "small", ".ckpt")
    earlier_path = tmp_path / "epoch-1.ckpt"
    shutil.copyfile(downloaded, earlier_path)
    earlier, latest = (
        DownloadedModel(earlier_path, role=None),
        DownloadedModel(downloaded, role=None),
    )
    install_sdk(RecoveryTask([earlier, latest]))
    path, links = resolve_task_model(TASK_ID)
    assert path == downloaded
    assert links["model_id"] == latest.id
    assert (earlier.downloads, latest.downloads) == (0, 1)


def test_legacy_preferred_artifact_alias_keeps_priority_over_native_filename(
    tmp_path: Path, install_sdk: Callable[[RecoveryTask], None]
) -> None:
    downloaded, _ = standalone_checkpoint(tmp_path, "rfdetr", "small", ".ckpt")
    legacy_path = tmp_path / "legacy.pt"
    legacy_path.write_bytes(b"historical-checkpoint")
    legacy, native = DownloadedArtifact(legacy_path), DownloadedArtifact(downloaded)
    install_sdk(RecoveryTask([], {"best.ckpt": native, "train_weights_best.pt": legacy}))
    path, links = resolve_task_model(TASK_ID)
    assert path == legacy_path
    assert links["artifact_name"] == "train_weights_best.pt"
    assert (legacy.downloads, native.downloads) == (1, 0)
