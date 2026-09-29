"""The only FiftyOne boundary: persistent samples and exact, run-scoped overlays."""

import hashlib
import json
from collections import defaultdict
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from filelock import FileLock
from PIL import Image

from clearml_yolo.comparison.evaluation_payload import (
    EvaluationBox,
    EvaluationMatch,
    EvaluationPayload,
)
from clearml_yolo.publishing.data import (
    DatasetSnapshot,
    PublicationBox,
    PublicationImage,
    file_hash,
    normalize_box,
    prediction_aliases,
    read_predictions,
    read_snapshot,
)
from clearml_yolo.publishing.models import FiftyOneConfig, PublicationReceipt, PublicationRequest

SCHEMA_VERSION = 1


def _backend() -> Any:
    # FiftyOne's untyped dynamic sample/label API is confined to this adapter.
    import fiftyone as fo

    return fo


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _fields(run_key: str) -> dict[str, str]:
    return {
        field: f"{field}_{run_key}"
        for field in (
            "predictions",
            "matched_ground_truth",
            "matched_predictions",
            "predicted",
            "evaluated",
            "tp",
            "fp",
            "fn",
        )
    }


def _detection(fo: Any, box: PublicationBox | EvaluationBox, width: int, height: int) -> Any:
    return fo.Detection(
        label=box.label,
        bounding_box=normalize_box(box.box, width, height),
        confidence=box.confidence,
        dm_index=box.index,
    )


def _evaluated_detection(
    fo: Any, box: EvaluationBox, matches: list[EvaluationMatch], width: int, height: int
) -> Any:
    detection = _detection(fo, box, width, height)
    detection["dm_status"] = box.status
    detection["dm_gt_indices"] = [match.gt_index for match in matches if match.gt_index is not None]
    detection["dm_pred_indices"] = [
        match.pred_index for match in matches if match.pred_index is not None
    ]
    detection["dm_ious"] = [match.iou for match in matches if match.iou is not None]
    # Retain every association, including a cross-class FP referencing an FN ground truth.
    detection["dm_matches"] = [match.model_dump(mode="json") for match in matches]
    return detection


def _new_sample(fo: Any, name: str, record: PublicationImage) -> Any:
    with Image.open(record.path) as image:
        width, height = image.size
        if image.format == "JPEG" and image.getexif().get(274) in {6, 8}:
            width, height = height, width
    return fo.Sample(
        filepath=str(record.path),
        image_name=name,
        split=record.split,
        metadata=fo.ImageMetadata(width=width, height=height),
        ground_truth=fo.Detections(
            detections=[_detection(fo, box, width, height) for box in record.boxes]
        ),
    )


def _dataset(fo: Any, name: str, snapshot: DatasetSnapshot) -> tuple[Any, bool]:
    identity = {
        "schema_version": SCHEMA_VERSION,
        "ground_truth_sha256": snapshot.sha256,
        "media_identity_sha256": _digest(json.dumps(snapshot.membership, sort_keys=True)),
    }
    if fo.dataset_exists(name):
        dataset = fo.load_dataset(name)
        dataset.reload()
        stored = dataset.info.get("cy_dataset", {})
        if any(stored.get(key) != value for key, value in identity.items()):
            raise ValueError(
                f"FiftyOne dataset {name!r} has incompatible CSV/schema/path identity; "
                "use the original media paths or a different fiftyone.dataset_prefix"
            )
    else:
        dataset = fo.Dataset(name, persistent=True)
        stored = {**identity, "complete": False}
        dataset.info = {"cy_dataset": stored, "cy_runs": {}}
        dataset.save()
    existing = {sample.image_name: sample for sample in dataset.iter_samples()}
    for image_name, sample in existing.items():
        record = snapshot.images.get(image_name)
        if record is None or sample.filepath != str(record.path) or sample.split != record.split:
            raise ValueError(f"FiftyOne sample path identity mismatch for {image_name!r}")
    if len(existing) != len(dataset):
        raise ValueError("FiftyOne dataset contains duplicate image identities")
    reused = bool(stored.get("complete"))
    if reused and len(existing) != len(snapshot.images):
        raise ValueError("Completed FiftyOne dataset has missing samples; use a new dataset_prefix")
    if not reused:
        for image_name, record in snapshot.images.items():
            if image_name not in existing:
                dataset.add_sample(_new_sample(fo, image_name, record), dynamic=True)
        info = deepcopy(dataset.info)
        info["cy_dataset"]["complete"] = True
        dataset.info = info
        dataset.save()
    return dataset, reused


def _load_evaluations(
    request: PublicationRequest, snapshot: DatasetSnapshot
) -> list[EvaluationPayload]:
    payloads: list[EvaluationPayload] = []
    seen: set[str] = set()
    for split, path in request.evaluations.items():
        payload = EvaluationPayload.model_validate_json(path.read_text(encoding="utf-8"))
        if payload.split != split:
            raise ValueError(f"Evaluation payload split {payload.split!r} conflicts with {split!r}")
        for name in payload.image_names:
            if name in seen or name not in snapshot.images or snapshot.images[name].split != split:
                raise ValueError(
                    f"Evaluation image {name!r} conflicts with dataset split membership"
                )
            seen.add(name)
        if any(
            box.image_name not in payload.image_names
            for box in [*payload.ground_truth, *payload.predictions]
        ):
            raise ValueError("Evaluation boxes fall outside their split image membership")
        payloads.append(payload)
    return payloads


class _Overlay:
    """Index exact match associations once, without recomputing matching."""

    def __init__(self, payloads: list[EvaluationPayload]) -> None:
        self.images: set[str] = set()
        self.gt: dict[str, list[tuple[EvaluationBox, list[EvaluationMatch]]]] = defaultdict(list)
        self.pred: dict[str, list[tuple[EvaluationBox, list[EvaluationMatch]]]] = defaultdict(list)
        for payload in payloads:
            self.images.update(payload.image_names)
            gt_matches: dict[int, list[EvaluationMatch]] = defaultdict(list)
            pred_matches: dict[int, list[EvaluationMatch]] = defaultdict(list)
            for match in payload.matches:
                if match.gt_index is not None:
                    gt_matches[match.gt_index].append(match)
                if match.pred_index is not None:
                    pred_matches[match.pred_index].append(match)
            for box in payload.ground_truth:
                self.gt[box.image_name].append((box, gt_matches[box.index]))
            for box in payload.predictions:
                self.pred[box.image_name].append((box, pred_matches[box.index]))


def _write_run(
    fo: Any,
    dataset: Any,
    fields: dict[str, str],
    request: PublicationRequest,
    raw: dict[str, list[PublicationBox]],
    overlay: _Overlay,
) -> None:
    for field in ("tp", "fp", "fn"):
        dataset.add_sample_field(fields[field], fo.IntField)
    dataset.add_sample_field(fields["predicted"], fo.BooleanField)
    for sample in dataset.iter_samples():
        name = sample.image_name
        width, height = sample.metadata.width, sample.metadata.height
        sample[fields["predictions"]] = fo.Detections(
            detections=[_detection(fo, box, width, height) for box in raw.get(name, [])]
        )
        sample[fields["predicted"]] = _prediction_membership(request, sample.split, name in raw)
        sample[fields["evaluated"]] = name in overlay.images
        gt = overlay.gt.get(name, [])
        pred = overlay.pred.get(name, [])
        sample[fields["matched_ground_truth"]] = fo.Detections(
            detections=[
                _evaluated_detection(fo, box, matches, width, height) for box, matches in gt
            ]
        )
        sample[fields["matched_predictions"]] = fo.Detections(
            detections=[
                _evaluated_detection(fo, box, matches, width, height) for box, matches in pred
            ]
        )
        for status, boxes in (("TP", pred), ("FP", pred), ("FN", gt)):
            sample[fields[status.lower()]] = (
                sum(box.status == status for box, _ in boxes) if name in overlay.images else None
            )
        sample.save()


def _prediction_membership(request: PublicationRequest, split: str, has_boxes: bool) -> bool | None:
    if request.predictions is None:
        return False
    if request.prediction_splits is not None:
        return split in request.prediction_splits
    # A standalone CSV has no row for zero detections, so absence cannot prove inference ran.
    return True if has_boxes else None


class FiftyOnePublisher:
    enabled = True

    def __init__(self, config: FiftyOneConfig) -> None:
        self.config = config

    def preflight(self) -> None:
        try:
            _backend().list_datasets()
        except ImportError as error:
            raise RuntimeError(
                "FiftyOne publishing requires the project dependencies; run uv sync, "
                "or set fiftyone.enabled=false"
            ) from error

    def publish(self, request: PublicationRequest) -> PublicationReceipt:
        snapshot = read_snapshot(request.ground_truth)
        raw = read_predictions(
            request.predictions, prediction_aliases(snapshot, request.prediction_image_name)
        )
        payloads = _load_evaluations(request, snapshot)
        source = request.source_ground_truth
        source_hash = (
            file_hash(source)
            if source is not None and source.resolve() != request.ground_truth.resolve()
            else snapshot.sha256
        )
        name = f"{self.config.dataset_prefix}-v{SCHEMA_VERSION}-{snapshot.sha256}"
        run_key = "run_" + _digest(request.task_id)
        fields = _fields(run_key)
        fo = _backend()
        locks = Path(fo.config.database_dir) / "clearml-yolo-locks"
        locks.mkdir(parents=True, exist_ok=True)
        with FileLock(locks / f"{_digest(name)}.lock"):
            dataset, reused = _dataset(fo, name, snapshot)
            run = {
                "task_id": request.task_id,
                "complete": False,
                "fields": fields,
                "source_ground_truth_sha256": source_hash,
                "metadata": request.metadata,
                "evaluations": {
                    item.split: {"thresholds": item.thresholds, "methodology": item.methodology}
                    for item in payloads
                },
            }
            info = deepcopy(dataset.info)
            info.setdefault("cy_runs", {})[run_key] = run
            dataset.info = info
            dataset.save()
            _write_run(fo, dataset, fields, request, raw, _Overlay(payloads))
            dataset.add_dynamic_sample_fields()
            info = deepcopy(dataset.info)
            info["cy_runs"][run_key]["complete"] = True
            dataset.info = info
            dataset.save()
        return PublicationReceipt(
            dataset_name=name,
            task_id=request.task_id,
            run_key=run_key,
            ground_truth_sha256=snapshot.sha256,
            source_ground_truth_sha256=source_hash,
            dataset_reused=reused,
            sample_count=len(snapshot.images),
            fields=fields,
            dataset_complete=True,
            run_complete=True,
            payload_paths=_payload_paths(request),
            published_at=datetime.now(UTC),
        )


def _payload_paths(request: PublicationRequest) -> dict[str, Path]:
    paths = {"ground_truth": request.ground_truth.resolve()}
    if request.source_ground_truth is not None:
        paths["source_ground_truth"] = request.source_ground_truth.resolve()
    if request.predictions is not None:
        paths["predictions"] = request.predictions.resolve()
    paths.update(
        {f"evaluation_{split}": path.resolve() for split, path in request.evaluations.items()}
    )
    return paths
