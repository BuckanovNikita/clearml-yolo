"""Check actual RLE/component geometry, frozen identities and smoke membership."""

import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from severstal_harness import (
    MODEL_SELECTIONS,
    SeverstalOptions,
    _verify_initialization,
    parse_backbone_options,
    scenario_overrides,
    worker_environment,
)
from severstal_helpers import (
    OptimizerObservation,
    loss_values,
    validate_observation,
    write_pipeline,
)

ROOT = Path(__file__).resolve().parents[1]
with pytest.MonkeyPatch.context() as import_path:
    import_path.syspath_prepend(str(ROOT))
    from scripts import severstal


def _source(root: Path, count: int = 60, *, legacy: bool = False) -> Path:
    images = root / "train_images"
    images.mkdir(parents=True)
    with (root / "train.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = (
            ["ImageId_ClassId", "EncodedPixels"]
            if legacy
            else ["ImageId", "ClassId", "EncodedPixels"]
        )
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        for index in range(count):
            name = f"image_{index:03}.png"
            pixels = np.full((4, 7, 3), index, dtype=np.uint8)
            Image.fromarray(pixels).save(images / name)
            if index % 5:
                row = {"EncodedPixels": "1 1 6 1 28 1"}
                if legacy:
                    row["ImageId_ClassId"] = f"{name}_{index % 5}"
                else:
                    row.update(ImageId=name, ClassId=str(index % 5))
                writer.writerow(row)
    return root


def test_rle_is_one_based_column_major_and_keeps_boundary_pixels() -> None:
    result = severstal.decode_rle("1 1 4 2 12 1", height=3, width=4)
    assert result.shape == (3, 4)
    assert np.argwhere(result).tolist() == [[0, 0], [0, 1], [1, 1], [2, 3]]
    assert not severstal.decode_rle("", height=3, width=4).any()


@pytest.mark.parametrize(
    "encoded", ["1", "0 1", "1 0", "-1 2", "1 3 2 1", "5 1 1 1", "12 2", "x 1"]
)
def test_rle_rejects_malformed_or_overlapping_runs(encoded: str) -> None:
    with pytest.raises(ValueError, match="RLE"):
        severstal.decode_rle(encoded, height=3, width=4)


def test_components_use_eight_connectivity_and_half_open_boxes() -> None:
    mask = np.zeros((4, 7), dtype=np.bool_)
    mask[0, 0] = mask[1, 1] = mask[3, 6] = True
    components = severstal.component_boxes(mask, "4")
    assert [(component.box, component.area) for component in components] == [
        ((0, 0, 2, 2), 2),
        ((6, 3, 7, 4), 1),
    ]
    assert [component.class_id for component in components] == ["4", "4"]
    assert [component.component_id for component in components] == [1, 2]


@pytest.mark.parametrize("legacy", [False, True])
def test_source_conversion_preserves_backgrounds_classes_and_source_bytes(
    tmp_path: Path, legacy: bool
) -> None:
    source = _source(tmp_path / "source", count=10, legacy=legacy)
    original = (source / "train.csv").read_bytes()
    records = severstal.read_source(source)
    assert len(records) == 10
    assert sum(not record.components for record in records) == 2
    assert {component.class_id for record in records for component in record.components} == {
        "1",
        "2",
        "3",
        "4",
    }
    first_positive = records[1]
    assert (first_positive.height, first_positive.width) == (4, 7)
    assert [component.box for component in first_positive.components] == [
        (0, 0, 2, 2),
        (6, 3, 7, 4),
    ]
    assert (
        first_positive.source_sha256
        == hashlib.sha256(
            (source / "train_images" / first_positive.image_name).read_bytes()
        ).hexdigest()
    )
    assert (source / "train.csv").read_bytes() == original


def test_duplicate_image_class_annotation_is_rejected(tmp_path: Path) -> None:
    source = _source(tmp_path / "source", count=2)
    with (source / "train.csv").open("a", encoding="utf-8") as stream:
        stream.write("image_001.png,1,1 1\n")
    with pytest.raises(ValueError, match="Duplicate"):
        severstal.read_source(source)


def test_unknown_or_unsafe_image_reference_is_rejected(tmp_path: Path) -> None:
    source = _source(tmp_path / "source", count=2)
    (source / "train.csv").write_text(
        "ImageId,ClassId,EncodedPixels\n../secret.png,1,1 1\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="image"):
        severstal.read_source(source)


def test_frozen_split_is_reproducible_and_groups_identical_pixels(tmp_path: Path) -> None:
    source = _source(tmp_path / "source")
    original = source / "train_images/image_001.png"
    duplicate = source / "train_images/duplicate.png"
    duplicate.write_bytes(original.read_bytes())
    records = severstal.read_source(source)
    first = severstal.assign_splits(records, seed=0)
    second = severstal.assign_splits(tuple(reversed(records)), seed=0)
    assert first == second
    assert first["duplicate.png"] == first["image_001.png"]
    for split in severstal.SPLITS:
        members = [record for record in records if first[record.image_name] == split]
        assert any(not record.components for record in members)
        assert {component.class_id for record in members for component in record.components} == {
            "1",
            "2",
            "3",
            "4",
        }


def test_frozen_manifest_is_stable_across_fresh_python_hash_seeds(tmp_path: Path) -> None:
    source = _source(tmp_path / "source")
    with (source / "train.csv").open("a", encoding="utf-8") as stream:
        for index in range(1, 60):
            if index % 5 and index % 3 and 1 + index % 4 != index % 5:
                stream.write(f"image_{index:03}.png,{1 + index % 4},2 1\n")
    hashes = []
    for seed in (1, 42):
        output = tmp_path / str(seed)
        result = subprocess.run(  # noqa: S603 - fixed local preparation command, no shell
            [
                sys.executable,
                str(ROOT / "scripts/severstal.py"),
                "prepare",
                "--source",
                str(source),
                "--output",
                str(output),
                "--smoke-sizes",
                "30",
                "6",
                "6",
            ],
            env=os.environ | {"PYTHONHASHSEED": str(seed)},
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        hashes.append(severstal.verify_prepared(output)["sha256"])
    assert hashes[0] == hashes[1]


def test_preparation_freezes_csv_manifests_and_rejects_modified_inputs(tmp_path: Path) -> None:
    source = _source(tmp_path / "source")
    output = tmp_path / "prepared"
    manifest = severstal.prepare(source, output, smoke_sizes=(30, 6, 6))
    assert manifest["split_counts"] == {"train": 48, "val": 6, "test": 6}
    assert manifest["smoke_counts"] == {"train": 30, "val": 6, "test": 6}
    assert severstal.verify_prepared(output)["sha256"] == manifest["sha256"]
    with (output / "smoke.csv").open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len({row["image_name"] for row in rows}) == 42
    assert any(row["instance_label"] == "" for row in rows)
    assert {row["instance_label"] for row in rows} == {"", "1", "2", "3", "4"}
    assert all(Path(row["image_path"]).is_absolute() for row in rows)
    assert len(json.loads((output / "manifest.json").read_text())["images"]) == 60
    with pytest.raises(FileExistsError):
        severstal.prepare(source, output, smoke_sizes=(30, 6, 6))
    (output / "smoke.csv").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        severstal.verify_prepared(output)


def test_selected_smoke_image_content_is_verified(tmp_path: Path) -> None:
    source = _source(tmp_path / "source")
    output = tmp_path / "prepared"
    manifest = severstal.prepare(source, output, smoke_sizes=(30, 6, 6))
    member = next(image for image in manifest["images"] if image["smoke"])
    (source / "train_images" / member["image_name"]).write_bytes(b"modified")
    with pytest.raises(ValueError, match=r"image.*hash"):
        severstal.verify_prepared(output)


def test_smoke_selection_fails_instead_of_silently_shrinking(tmp_path: Path) -> None:
    source = _source(tmp_path / "source")
    with pytest.raises(ValueError, match="smoke"):
        severstal.prepare(source, tmp_path / "prepared")
    assert not (tmp_path / "prepared/manifest.json").exists()


def test_native_matrix_uses_every_registered_preset(tmp_path: Path) -> None:
    from clearml_yolo.core.models import PRESETS

    expected = {"ultralytics"} | {
        f"{backend}/{preset}"
        for backend, presets in PRESETS.items()
        if backend != "ultralytics"
        for preset in presets
    }
    assert set(MODEL_SELECTIONS) == expected
    assert len(MODEL_SELECTIONS) == 15
    options = SeverstalOptions(tmp_path, tmp_path, "acceptance", ("owned",))
    home = Path(worker_environment(tmp_path)["CY_HOME"])
    for selection in MODEL_SELECTIONS:
        for variant in ("default", "json", "json_mosaic"):
            overrides = scenario_overrides(options, tmp_path, selection, variant, "test")
            prefix = "ultralytics" if selection == "ultralytics" else "model.train"
            assert f"{prefix}.epochs=1" in overrides
            assert f"{prefix}.batch=1" in overrides
            assert f"{prefix}.seed=0" in overrides
            assert ("transforms=albumentations" in overrides) == (variant != "default")
            for key in ("run_dir", "dataset_cache_dir"):
                value = next(
                    value.partition("=")[2] for value in overrides if value.startswith(f"{key}=")
                )
                assert Path(json.loads(value)).is_relative_to(home)


@pytest.mark.parametrize(
    "entry",
    [
        "deimv2/l",
        "=backbone.pt",
        "deimv2/l=",
        "ultralytics=backbone.pt",
        "rfdetr/nano=backbone.pt",
        "deimv2/unknown=backbone.pt",
        "fasterrcnn/unknown=backbone.pt",
    ],
)
def test_backbone_options_reject_invalid_or_unsupported_selections(entry: str) -> None:
    with pytest.raises(ValueError, match="backbone"):
        parse_backbone_options([entry])


def test_backbone_options_reject_urls_without_exposing_credentials() -> None:
    with pytest.raises(ValueError, match="local") as error:
        parse_backbone_options(["deimv2/l=https://download.invalid/weights?token=private-value"])
    assert "private-value" not in str(error.value)
    assert "https://" not in str(error.value)


@pytest.mark.parametrize("kind", ["missing", "empty", "directory"])
def test_backbone_options_require_nonempty_local_files(tmp_path: Path, kind: str) -> None:
    path = tmp_path / "backbone.pt"
    if kind == "empty":
        path.touch()
    elif kind == "directory":
        path.mkdir()
    with pytest.raises(ValueError, match="nonempty local file"):
        parse_backbone_options([f"deimv2/l={path}"])


def test_repeatable_backbone_cli_rejects_duplicate_model_keys(tmp_path: Path) -> None:
    from conftest import pytest_addoption

    path = tmp_path / "backbone.pt"
    path.write_bytes(b"checkpoint")
    parser = pytest.Parser(_ispytest=True)
    pytest_addoption(parser)
    entries = [f"deimv2/l={path}", f"deimv2/l={path}"]
    parsed = parser.parse([value for entry in entries for value in ("--severstal-backbone", entry)])
    assert parsed.severstal_backbone == entries
    with pytest.raises(ValueError, match="Duplicate backbone"):
        parse_backbone_options(parsed.severstal_backbone)


def test_backbone_options_preserve_legacy_constructor_and_local_path_characters(
    tmp_path: Path,
) -> None:
    path = tmp_path / "backbone = large.pt"
    path.write_bytes(b"checkpoint")
    parsed = parse_backbone_options([f"deimv2/l={path}", f"fasterrcnn/dinov3_small={path}"])
    assert parsed == {"deimv2/l": path.resolve(), "fasterrcnn/dinov3_small": path.resolve()}
    previous = SeverstalOptions(tmp_path, tmp_path, "acceptance", ("owned",), "1", 900)
    assert previous.backbone_weights == {}
    assert previous.device == "1"
    assert previous.timeout == 900


def test_backbone_mapping_is_validated_and_frozen_between_variants(tmp_path: Path) -> None:
    first = tmp_path / "first.pt"
    second = tmp_path / "second.pt"
    first.write_bytes(b"first checkpoint")
    second.write_bytes(b"second checkpoint")
    configured = {"deimv2/l": first}
    options = SeverstalOptions(
        tmp_path, tmp_path, "acceptance", ("owned",), backbone_weights=configured
    )
    configured["deimv2/l"] = second
    assert options.backbone_weights["deimv2/l"] == first.resolve()
    with pytest.raises(ValueError, match="supports only"):
        SeverstalOptions(
            tmp_path,
            tmp_path,
            "acceptance",
            ("owned",),
            backbone_weights={"rfdetr/nano": first},
        )


@pytest.mark.parametrize("selection", ["deimv2/l", "fasterrcnn/dinov3_small"])
@pytest.mark.parametrize("variant", ["default", "json", "json_mosaic"])
def test_backbone_override_composes_only_for_matching_selection(
    tmp_path: Path, selection: str, variant: str
) -> None:
    from hydra import compose, initialize_config_module
    from hydra_zen import store

    import clearml_yolo.entrypoints.hydra.configs  # noqa: F401 - config registration

    path = tmp_path / "backbone = local.pt"
    path.write_bytes(b"checkpoint")
    options = SeverstalOptions(
        tmp_path,
        tmp_path,
        "acceptance",
        ("owned",),
        backbone_weights=parse_backbone_options([f"{selection}={path}"]),
    )
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=scenario_overrides(options, tmp_path, selection, variant, "native-smoke"),
        )
    assert Path(config.model.train.backbone_weights) == path.resolve()
    assert config.model.train.pretrained is True
    assert config.transforms.mode == ("native" if variant == "default" else "albumentations")
    for other in MODEL_SELECTIONS:
        if other != selection:
            overrides = scenario_overrides(options, tmp_path, other, variant, "native-smoke")
            assert not any(value.startswith("model.train.backbone_weights=") for value in overrides)


def test_saved_mosaic_recipe_is_standard_albumentations_json(tmp_path: Path) -> None:
    import albumentations as alb

    target = tmp_path / "pipeline.json"
    write_pipeline(target, "json_mosaic", 384)
    restored = alb.load(target, data_format="json")
    assert isinstance(restored, alb.Compose)
    assert isinstance(restored.transforms[0], alb.Mosaic)
    assert restored.transforms[0].p == 1
    assert restored.transforms[0].target_size == (384, 384)


def test_optimizer_evidence_observes_real_parameter_update() -> None:
    import torch

    parameter = torch.nn.Parameter(torch.tensor([2.0]))
    optimizer = torch.optim.SGD([parameter], lr=0.1)
    observation = OptimizerObservation()
    with observation.installed():
        torch.autograd.backward(parameter.square().sum())
        optimizer.step()
    evidence = observation.result()
    assert evidence["steps"] == 1
    assert evidence["parameter_changed"]
    validate_observation(evidence)


def test_optimizer_evidence_rejects_zero_learning_rate() -> None:
    import torch

    parameter = torch.nn.Parameter(torch.tensor([2.0]))
    optimizer = torch.optim.SGD([parameter], lr=0)
    observation = OptimizerObservation()
    with observation.installed():
        torch.autograd.backward(parameter.square().sum())
        optimizer.step()
    assert not observation.result()["parameter_changed"]
    with pytest.raises(AssertionError, match="parameter"):
        validate_observation(observation.result())


@pytest.mark.parametrize("values", [[], [float("nan")], [float("inf")]])
def test_native_loss_evidence_rejects_missing_or_nonfinite_losses(values: list[float]) -> None:
    with pytest.raises(AssertionError, match="loss"):
        loss_values({"Native training": {"loss": {"y": values}}})


def test_native_comparison_rejects_different_initial_weights(tmp_path: Path) -> None:
    prior = tmp_path / "prior"
    prior.mkdir()
    result = {
        "manifest_sha256": "same-manifest",
        "optimizer": {"initial_optimizer_parameters_sha256": "weights-a"},
    }
    (prior / "summary.json").write_text(
        json.dumps({"status": "passed", "selection": "ultralytics", "verification": result})
    )
    assert _verify_initialization(tmp_path / "current", "ultralytics", result) == 1
    result["optimizer"] = {"initial_optimizer_parameters_sha256": "weights-b"}
    with pytest.raises(AssertionError, match="initialization differs"):
        _verify_initialization(tmp_path / "current", "ultralytics", result)


@pytest.mark.parametrize("selection", MODEL_SELECTIONS)
@pytest.mark.parametrize("variant", ["default", "json_mosaic"])
def test_native_scenario_composes(selection: str, variant: str, tmp_path: Path) -> None:
    from hydra import compose, initialize_config_module
    from hydra_zen import store

    import clearml_yolo.entrypoints.hydra.configs  # noqa: F401 - fresh-process config registration

    options = SeverstalOptions(tmp_path, tmp_path, "acceptance", ("owned",))
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="pipeline",
            overrides=scenario_overrides(options, tmp_path, selection, variant, "native-smoke"),
        )
    assert config.splits == ["val", "test"]
    settings = config.ultralytics if selection == "ultralytics" else config.model.train
    assert settings.epochs == 1
    assert settings.batch == 1
    assert settings.seed == 0
    assert settings.amp is False


def test_optimizer_evidence_distinguishes_fused_amp_overflow_from_update() -> None:
    import torch

    parameter = torch.nn.Parameter(torch.tensor([2.0]))
    optimizer = torch.optim.AdamW([parameter], lr=0.1, fused=True)
    scaler = torch.amp.GradScaler("cpu")
    observation = OptimizerObservation()
    with observation.installed():
        torch.autograd.backward(scaler.scale(parameter.square().sum()))
        assert parameter.grad is not None
        parameter.grad.fill_(float("inf"))
        scaler.step(optimizer)
        scaler.update()
        assert parameter.item() == 2.0
        assert observation.result()["steps"] == 0
        assert observation.result()["skipped_steps"] == 1
        optimizer.zero_grad()
        torch.autograd.backward(scaler.scale(parameter.square().sum()))
        scaler.step(optimizer)
        scaler.update()
    assert observation.result()["steps"] == 1
    validate_observation(observation.result())


def test_worker_environment_does_not_expose_credentials_in_failure_repr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLEARML_API_SECRET_KEY", "test-private-token")
    environment = worker_environment(tmp_path)
    assert environment["CLEARML_API_SECRET_KEY"] == "test-private-token"  # noqa: S105 - fake
    assert "test-private-token" not in repr(environment)


def test_publication_lookup_accepts_owned_collision_suffix_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import re

    from clearml import Task

    from severstal_harness import _verify_publication

    captured: dict[str, object] = {}

    def get_tasks(**kwargs: object) -> list[object]:
        captured.update(kwargs)
        return []

    monkeypatch.setattr(Task, "get_tasks", get_tasks)
    with pytest.raises(AssertionError, match="exactly one"):
        _verify_publication(
            tmp_path, {"project": "owned", "task_name": "run.42", "tags": ["owned-tag"]}, {}
        )
    pattern = str(captured["task_name"])
    assert re.fullmatch(pattern, "run.42")
    assert re.fullmatch(pattern, "run.42-wise-meadow")
    assert not re.fullmatch(pattern, "runX42")
    assert not re.fullmatch(pattern, "run.42-other-invocation-extra")
    assert captured["tags"] == ["owned-tag"]
