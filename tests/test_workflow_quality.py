"""Saved Hydra configuration through real local datasets, evaluation and reports."""

import os
from functools import partial
from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest
from hydra import compose, initialize_config_module
from hydra.utils import instantiate
from hydra_zen import store
from omegaconf import DictConfig, OmegaConf
from PIL import Image

import clearml_yolo.entrypoints.hydra.configs  # noqa: F401
from clearml_yolo.adapters.reporting.workbook_identity import read_dashboard, workbook_identities
from clearml_yolo.adapters.storage.dataset_records import validate_ground_truth
from clearml_yolo.adapters.storage.identity import checkpoint_sha256, write_checkpoint_identity
from clearml_yolo.adapters.yolo.reinfer import reinfer_split
from clearml_yolo.application.contracts import (
    ClearMLConfig,
    ComparisonManifest,
    InferenceConfig,
    ModelRef,
)
from clearml_yolo.application.ports import WorkflowDependencies
from clearml_yolo.application.use_cases.compare import MANIFEST_NAME, compare
from clearml_yolo.application.use_cases.report import report
from clearml_yolo.application.use_cases.val import validate
from clearml_yolo.core import artifact_names
from clearml_yolo.core.evaluation.payload import EvaluationPayload
from clearml_yolo.core.identity import ModelIdentity
from workflow_dependencies import (
    workflow_dependencies as workflow_dependencies,  # noqa: PLC0414 - fixture export
)

_LABELS = ["0001", "ёж"]
_THRESHOLD = 0.700000000000003
_PRED_COLUMNS = [
    "image_name",
    "instance_label",
    "bbox_x_tl",
    "bbox_y_tl",
    "bbox_x_br",
    "bbox_y_br",
    "confidence",
]


def _dataset(root: Path) -> Path:
    rows = []
    for split in ("val", "test"):
        for index, label in enumerate(_LABELS):
            path = root / f"{split}-{index:04}-猫.png"
            Image.new("RGB", (40, 40)).save(path)
            rows.append((path.name, str(path), label, 0, 0, 10, 10, split))
    source = root / "truth.csv"
    pd.DataFrame(
        rows,
        columns=[
            "image_name",
            "image_path",
            "instance_label",
            "bbox_x_tl",
            "bbox_y_tl",
            "bbox_x_br",
            "bbox_y_br",
            "split",
        ],
    ).to_csv(source, index=False)
    validated = validate_ground_truth(
        source, required_splits=("val", "test"), require_training=False
    )
    assert set(validated.names.values()) == set(_LABELS)
    assert len(validated.images) == 4
    assert validated.errors == []
    return source


def _checkpoint(root: Path, name: str, content: bytes) -> tuple[Path, ModelIdentity]:
    path = root / f"{name}.pt"
    path.write_bytes(content)
    identity = ModelIdentity(
        model_name=f"{name} 猫 0001",
        training_task_id=f"source-{name}",
        checkpoint_sha256=checkpoint_sha256(path),
    )
    write_checkpoint_identity(path, identity)
    return path, identity


def _predictions(paths: list[str], case: str, *, baseline: bool = False) -> pd.DataFrame:
    rows: list[tuple[object, ...]] = []
    for path in paths:
        name = Path(path).name
        label = _LABELS[int(name.split("-")[1])]
        if name.startswith("val"):
            rows.append((name, label, 0, 0, 10, 10, _THRESHOLD))
        elif baseline:
            rows.append((name, label, 0, 0, 10, 10, 0.9))
        elif case == "mixed":
            rows.extend(
                [
                    (name, label, 0, 0, 10, 10, 0.4),
                    (name, label, 20, 20, 30, 30, 0.99),
                ]
            )
        if case in {"mixed", "invalid"}:
            rows.extend(
                [
                    (name, label, 0, 0, 0, 10, 0.99),
                    (name, label, "invalid", 0, 10, 10, 0.99),
                ]
            )
    return pd.DataFrame(rows, columns=_PRED_COLUMNS)


def _saved_val_config(root: Path, truth: Path, weights: Path) -> DictConfig:
    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(
            config_name="val",
            overrides=[
                f"ground_truth={truth}",
                f"weights={weights}",
                f"output_dir={root / 'validation'}",
                "splits=[test]",
                "model_label=display-only",
                "ultralytics_predict.device=cpu",
                "ultralytics_predict.imgsz=64",
                "ultralytics_predict.batch=1",
            ],
        )
    saved = root / "val.yaml"
    OmegaConf.save(config, saved, resolve=True)
    return cast(DictConfig, OmegaConf.load(saved))


@pytest.mark.parametrize("case", ["mixed", "empty", "invalid"])
def test_saved_validation_config_freezes_val_thresholds_through_csv_payload_and_workbook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    truth = _dataset(tmp_path)
    weights, identity = _checkpoint(tmp_path, "candidate", b"candidate checkpoint")
    config = _saved_val_config(tmp_path, truth, weights)
    calls: list[list[str]] = []

    def predictor(_weights: object, paths: list[str], **_kwargs: Any) -> pd.DataFrame:
        calls.append([Path(path).name for path in paths])
        return _predictions(paths, case)

    monkeypatch.setattr(workflow_dependencies.tracking, "init_task", lambda *_a, **_kw: None)
    monkeypatch.setattr(workflow_dependencies.model, "predict_on_images", predictor)
    # Only the native checkpoint reader and inference effect are replaced.
    monkeypatch.setattr("clearml_yolo.adapters.yolo.inference.trained_imgsz", lambda _: 64)
    original_truth = truth.read_bytes()
    result = validate(
        config.weights,
        config.ground_truth,
        config.output_dir,
        instantiate(config.clearml),
        cast(dict[str, Any], OmegaConf.to_container(config.ultralytics, resolve=True)),
        instantiate(config.evaluation),
        splits=list(config.splits),
        ultralytics_predict=cast(
            dict[str, Any], OmegaConf.to_container(config.ultralytics_predict, resolve=True)
        ),
        model_label=config.model_label,
        deps=workflow_dependencies,
    )
    assert calls == [
        [f"val-{index:04}-猫.png" for index in range(2)],
        [f"test-{index:04}-猫.png" for index in range(2)],
    ]
    assert truth.read_bytes() == original_truth
    assert result.best_confidences == {"test": dict.fromkeys(_LABELS, _THRESHOLD)}
    payload = EvaluationPayload.model_validate_json(result.evaluations["test"].read_text())
    assert payload.model_identity == identity
    assert payload.thresholds == dict.fromkeys(_LABELS, _THRESHOLD)
    assert payload.image_names == [f"test-{index:04}-猫.png" for index in range(2)]
    assert {box.label for box in payload.ground_truth} == set(_LABELS)
    assert {box.status for box in payload.ground_truth} == {"FN"}
    assert sum(match.status == "FP" for match in payload.matches) == (2 if case == "mixed" else 0)
    dashboard = read_dashboard(result.dashboards["test"], index_col=0)
    for label in _LABELS:
        assert cast(pd.Series, dashboard.loc[label, ["tp", "fp", "fn"]]).tolist() == [
            0,
            int(case == "mixed"),
            1,
        ]
        # Presentation workbooks round confidence; the replay CSV/JSON stays exact.
        assert dashboard.loc[label, "confidence"] == 0.7
    assert workbook_identities(result.dashboards["test"]) == {"model": identity}
    threshold_csv = pd.read_csv(
        result.output_dir / f"{artifact_names.BEST_CONFIDENCES_VAL}.csv",
        dtype={"class_name": str},
        float_precision="round_trip",
    )
    assert dict(zip(threshold_csv["class_name"], threshold_csv["confidence"], strict=True)) == (
        dict.fromkeys(_LABELS, _THRESHOLD)
    )
    raw = pd.read_csv(tmp_path / "validation" / "predictions.csv", dtype={"instance_label": str})
    assert set(raw["instance_label"]) == set(_LABELS)
    if case in {"mixed", "invalid"}:
        assert raw["bbox_x_tl"].eq("invalid").sum() == 4


def test_comparison_cache_checkpoint_replacement_and_real_reports_preserve_source_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    workflow_dependencies: WorkflowDependencies,
) -> None:
    truth = _dataset(tmp_path)
    baseline, baseline_identity = _checkpoint(tmp_path, "baseline", b"baseline-v1")
    candidate, candidate_identity = _checkpoint(tmp_path, "candidate", b"candidate-v1")
    calls: list[str] = []

    def predictor(weights: Path, paths: list[str], **_kwargs: Any) -> pd.DataFrame:
        calls.append(weights.name)
        assert [Path(path).name for path in paths] == [
            f"test-{index:04}-猫.png" for index in range(2)
        ]
        return _predictions(paths, "mixed", baseline=weights == baseline)

    monkeypatch.setattr(workflow_dependencies.tracking, "init_task", lambda *_a, **_kw: None)
    monkeypatch.setattr("clearml_yolo.adapters.yolo.inference.trained_imgsz", lambda _: 64)
    monkeypatch.setattr(workflow_dependencies.model, "trained_imgsz", lambda _: 64)
    monkeypatch.setattr(
        workflow_dependencies.model,
        "reinfer_split",
        partial(
            reinfer_split,
            predictor=predictor,
            class_names=lambda _: dict(enumerate(_LABELS)),
        ),
    )
    destination = tmp_path / "comparison"
    baseline_ref = ModelRef(
        source="local", weights=baseline, thresholds=dict.fromkeys(_LABELS, 0.5)
    )
    candidate_ref = ModelRef(
        source="local", weights=candidate, thresholds=dict.fromkeys(_LABELS, 0.5)
    )

    def run() -> None:
        result = compare(
            baseline_ref,
            candidate_ref,
            truth,
            destination,
            ClearMLConfig(),
            InferenceConfig(conf=0.001, iou=0.7, imgsz=64, batch=1, device="cpu"),
            bootstrap_iterations=20,
            deps=workflow_dependencies,
        )
        assert result is not None
        frame = read_dashboard(result.candidate_dashboard, index_col=0)
        for label in _LABELS:
            assert cast(pd.Series, frame.loc[label, ["tp", "fp", "fn"]]).tolist() == [0, 1, 1]

    run()
    first_manifest = ComparisonManifest.model_validate_json(
        (destination / MANIFEST_NAME).read_text()
    )
    baseline_cache = destination / first_manifest.baseline_predictions
    candidate_cache = destination / first_manifest.candidate_predictions
    preserved = (baseline_cache.read_bytes(), candidate_cache.read_bytes())
    run()
    assert calls == ["baseline.pt", "candidate.pt"]
    before = candidate.stat()
    candidate.write_bytes(b"candidate-v2")  # Same size and mtime; content must own cache identity.
    os.utime(candidate, ns=(before.st_atime_ns, before.st_mtime_ns))
    candidate_identity = candidate_identity.model_copy(
        update={"checkpoint_sha256": checkpoint_sha256(candidate)}
    )
    write_checkpoint_identity(candidate, candidate_identity)
    run()
    assert calls == ["baseline.pt", "candidate.pt", "candidate.pt"]
    manifest = ComparisonManifest.model_validate_json((destination / MANIFEST_NAME).read_text())
    assert manifest.baseline_predictions == first_manifest.baseline_predictions
    assert manifest.candidate_predictions != first_manifest.candidate_predictions
    assert (baseline_cache.read_bytes(), candidate_cache.read_bytes()) == preserved
    assert manifest.baseline_identity == baseline_identity
    assert manifest.candidate_identity == candidate_identity
    reports = report(destination, tmp_path / "reports", ClearMLConfig(), deps=workflow_dependencies)
    for output in [reports.dev_reports["test"], reports.business_reports["test"]]:
        assert output.is_file()
        assert workbook_identities(output) == {
            "baseline": baseline_identity,
            "candidate": candidate_identity,
        }
        assert not read_dashboard(output).empty
