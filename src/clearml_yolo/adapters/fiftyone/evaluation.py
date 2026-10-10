"""Import digital-metrics evidence into FiftyOne's native detection run API.

FiftyOne's dynamic, untyped extension interfaces are confined to this boundary.
Matching and AP are never recomputed by this backend.
"""

from collections.abc import Mapping, Sequence
from typing import Any, Literal, Self, override

import numpy as np
from fiftyone.core.collections import SampleCollection
from fiftyone.utils.eval.base import get_subset_view
from fiftyone.utils.eval.detection import (
    DetectionEvaluation,
    DetectionEvaluationConfig,
    DetectionResults,
)

from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.core.evaluation.payload import (
    EvaluationBox,
    EvaluationMatch,
    EvaluationPayload,
    EvaluationReport,
)

NativeMatch = tuple[str | None, str | None, float | None, float | None, str | None, str | None]
_AP50_IOU = 0.5


def canonical_matches(
    payload: EvaluationPayload,
    gt_ids: Mapping[int, str],
    pred_ids: Mapping[int, str],
) -> list[NativeMatch]:
    """Apply the source confusion matrix's claimed-GT rule, preserving order."""
    claimed = {match.gt_index for match in payload.matches if match.status == "TP"}
    result: list[NativeMatch] = []
    for match in payload.matches:
        if match.status == "FN":
            continue
        gt_index = match.gt_index
        if match.status == "FP" and gt_index is not None:
            if gt_index in claimed:
                gt_index = None
            else:
                claimed.add(gt_index)
        result.append(
            (
                match.gt_label if gt_index is not None else None,
                match.pred_label if match.pred_index is not None else None,
                match.iou if gt_index is not None else None,
                match.confidence,
                gt_ids[gt_index] if gt_index is not None else None,
                pred_ids[match.pred_index] if match.pred_index is not None else None,
            )
        )
    result.extend(
        (
            match.gt_label,
            None,
            None,
            None,
            gt_ids[match.gt_index] if match.gt_index is not None else None,
            None,
        )
        for match in payload.matches
        if match.status == "FN" and match.gt_index not in claimed
    )
    return result


class DigitalMetricsEvaluationConfig(DetectionEvaluationConfig):  # type: ignore[misc,no-any-unimported]
    """Persisted provenance and native fields for an imported evaluation."""

    def __init__(
        self,
        pred_field: str,
        gt_field: str,
        *,
        cy_run_key: str = "",
        cy_split: str = "",
        iou: float | None = None,
        classwise: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(pred_field, gt_field, iou=iou, classwise=classwise, **kwargs)
        self.cy_run_key = cy_run_key
        self.cy_split = cy_split

    @property
    @override
    def method(self) -> str:
        return "digital_metrics"


class DigitalMetricsEvaluation(DetectionEvaluation):  # type: ignore[misc,no-any-unimported]
    """A native run backend whose associations arrive from authoritative evidence."""

    @override
    def evaluate(self, doc: Any, eval_key: str | None = None) -> list[NativeMatch]:
        del doc, eval_key
        raise NotImplementedError("Import an EvaluationPayload with publish_evaluation")


class DigitalMetricsDetectionResults(DetectionResults):  # type: ignore[misc,no-any-unimported]
    """Native matches plus complete source statuses, AP, PR, and provenance."""

    ious: Any

    def __init__(
        self,
        samples: Any,
        config: Any,
        eval_key: str,
        matches: Sequence[NativeMatch],
        *,
        source_payload: Mapping[str, Any],
        ground_truth_ids: Mapping[str, str],
        prediction_ids: Mapping[str, str],
        classes: Sequence[str] | None = None,
        missing: str | None = None,
        custom_metrics: Any = None,
        backend: Any = None,
    ) -> None:
        payload = EvaluationPayload.model_validate(source_payload)
        if classes is None:
            classes = (
                payload.report.classes if payload.report is not None else list(payload.thresholds)
            )
        super().__init__(
            samples,
            config,
            eval_key,
            matches,
            classes=list(classes),
            missing=missing or "background",
            custom_metrics=custom_metrics,
            backend=backend,
        )
        self.source_data = payload.model_dump(mode="json")
        self.ground_truth_ids = dict(ground_truth_ids)
        self.prediction_ids = dict(prediction_ids)
        self._ious_orig: Any = None
        if (
            payload.report is not None
            and self.confusion_matrix(
                classes=payload.report.confusion_matrix.labels,
                include_missing=True,
            ).tolist()
            != payload.report.confusion_matrix.counts
        ):
            raise ValueError("Native associations disagree with the authoritative confusion matrix")

    @property
    def source_payload(self) -> EvaluationPayload:
        return EvaluationPayload.model_validate(self.source_data)

    @property
    def report_payload(self) -> EvaluationReport | None:
        return self.source_payload.report

    @property
    def is_subset(self) -> bool:
        if not self.has_subset:
            return False
        # Removing an empty image can change the AP population despite preserving
        # every fixed-threshold tuple. A full dataset is an allowed scope superset.
        payload = self.source_payload
        return (
            not set(payload.image_names).issubset(self.samples.values("image_name"))
            or not set(self.ground_truth_ids.values()).issubset(
                self._visible_ids(self.config.gt_field, self.ground_truth_ids)
            )
            or not set(self.prediction_ids.values()).issubset(
                self._visible_ids(self.config.pred_field, self.prediction_ids)
            )
        )

    @classmethod
    @override
    def _from_dict(
        cls,
        d: dict[str, Any],
        samples: Any,
        config: Any,
        eval_key: str,
        **kwargs: Any,
    ) -> Self:
        matches = list(
            zip(
                d["ytrue"],
                d["ypred"],
                d["ious"],
                d["confs"],
                d["ytrue_ids"],
                d["ypred_ids"],
                strict=True,
            )
        )
        return cls(
            samples,
            config,
            eval_key,
            matches,
            source_payload=d["source_data"],
            ground_truth_ids=d["ground_truth_ids"],
            prediction_ids=d["prediction_ids"],
            classes=d.get("classes"),
            missing=d.get("missing"),
            custom_metrics=d.get("custom_metrics"),
            **kwargs,
        )

    @override
    def use_subset(self, subset_def: Any) -> Self:
        # Native subset membership is GT-in-subset OR FP-prediction-in-subset.
        # The upstream implementation slices all match arrays except IoUs.
        if self.has_subset:
            self.clear_subset()
        if self.ytrue.size == 0:
            return self._use_empty_subset(subset_def)
        pairs = list(zip(self.ytrue_ids, self.ypred_ids, strict=True))
        original = self.ious
        super().use_subset(subset_def)
        selected = set(zip(self.ytrue_ids, self.ypred_ids, strict=True))
        self._ious_orig = original
        self.ious = original[np.array([pair in selected for pair in pairs], dtype=bool)]
        return self

    def _use_empty_subset(self, subset_def: Any) -> Self:
        # Upstream infers float masks for empty arrays, then fails when combining
        # the GT and FP masks. Keep its view resolution and restore-state contract.
        view = (
            subset_def
            if isinstance(subset_def, SampleCollection)
            else get_subset_view(self.samples, self.config.gt_field, subset_def)
        )
        empty_mask = np.zeros(0, dtype=bool)
        self._samples_orig = self.samples
        for name in ("ytrue", "ypred", "confs", "weights", "ytrue_ids", "ypred_ids", "ious"):
            value = getattr(self, name)
            setattr(self, f"_{name}_orig", value)
            setattr(self, name, value[empty_mask] if value is not None else None)
        self._samples = view
        self._has_subset = True
        return self

    @override
    def clear_subset(self) -> None:
        if self.has_subset:
            self.ious = self._ious_orig
            self._ious_orig = None
        super().clear_subset()

    def _source_matches(self) -> list[EvaluationMatch]:
        matches = self.source_payload.matches
        if not self.has_subset:
            return matches
        gt_ids = set(self.ytrue_ids)
        pred_ids = set(self.ypred_ids)
        return [
            match
            for match in matches
            if (
                self.ground_truth_ids.get(str(match.gt_index)) in gt_ids
                if match.status == "FN"
                else self.prediction_ids.get(str(match.pred_index)) in pred_ids
            )
        ]

    def tp_fp_fn(self) -> tuple[int, int, int]:
        matches = self._source_matches()
        return (
            sum(match.status == "TP" for match in matches),
            sum(match.status == "FP" for match in matches),
            sum(match.status == "FN" for match in matches),
        )

    def _counts(self, classes: Sequence[str] | None) -> dict[str, tuple[int, int, int]]:
        selected = list(classes) if classes is not None else self.classes.tolist()
        matches = self._source_matches()
        return {
            name: (
                sum(match.status == "TP" and match.pred_label == name for match in matches),
                sum(match.status == "FP" and match.pred_label == name for match in matches),
                sum(match.status == "FN" and match.gt_label == name for match in matches),
            )
            for name in selected
        }

    @staticmethod
    def _class_report(tp: int, fp: int, fn: int, beta: float = 1) -> dict[str, float | int]:
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        denominator = max(beta * beta * precision + recall, 1e-6)
        fscore = (1 + beta * beta) * precision * recall / denominator
        return {"precision": precision, "recall": recall, "f1-score": fscore, "support": tp + fn}

    @override
    def report(self, classes: Sequence[str] | None = None) -> dict[str, Any]:
        counts = self._counts(classes)
        result = {name: self._class_report(*values) for name, values in counts.items()}
        tp, fp, fn = (sum(values[i] for values in counts.values()) for i in range(3))
        result["micro avg"] = self._class_report(tp, fp, fn)
        for average in ("macro avg", "weighted avg"):
            weights = {
                name: (float(values["support"]) if average == "weighted avg" else 1.0)
                for name, values in result.items()
                if name in counts
            }
            denominator = sum(weights.values())
            result[average] = {
                metric: sum(
                    float(result[name][metric]) * weight for name, weight in weights.items()
                )
                / denominator
                if denominator
                else 0.0
                for metric in ("precision", "recall", "f1-score")
            }
            result[average]["support"] = tp + fn
        return result

    @override
    def print_report(self, classes: Sequence[str] | None = None, digits: int = 2) -> None:
        import pandas as pd

        # The stock printer derives a new sklearn report from canonical CM rows,
        # which cannot recover the source's separate FP/FN status evidence.
        table = pd.DataFrame.from_dict(self.report(classes), orient="index").round(digits)
        print(table.to_string())  # noqa: T201 - native print_report API

    @override
    def metrics(
        self,
        classes: Sequence[str] | None = None,
        average: str = "micro",
        beta: float = 1.0,
    ) -> dict[str, Any]:
        if average not in {"micro", "macro", "weighted"}:
            raise ValueError("Supported averages are micro, macro and weighted")
        counts = self._counts(classes)
        tp, fp, fn = (sum(values[i] for values in counts.values()) for i in range(3))
        values = self._class_report(tp, fp, fn, beta=beta)
        if average != "micro":
            rows = [self._class_report(*count, beta=beta) for count in counts.values()]
            weights = [float(row["support"]) if average == "weighted" else 1 for row in rows]
            total = sum(weights)
            for metric in ("precision", "recall", "f1-score"):
                values[metric] = (
                    sum(
                        float(row[metric]) * weight
                        for row, weight in zip(rows, weights, strict=True)
                    )
                    / total
                    if total
                    else 0.0
                )
        return {
            "precision": values["precision"],
            "recall": values["recall"],
            "fscore": values["f1-score"],
            "support": values["support"],
            "accuracy": tp / (tp + fp + fn) if tp + fp + fn else 0.0,
            **self._get_custom_metrics(),
        }

    def mAP(self, classes: Sequence[str] | None = None) -> float | None:  # noqa: N802
        report = self.report_payload
        if self.is_subset or report is None:
            return None
        selected = classes if classes is not None else report.classes
        values = [
            report.average_precisions[name].ap50_95
            for name in selected
            if name in report.average_precisions
        ]
        available = [value for value in values if value is not None]
        return sum(available) / len(available) if available else None

    def plot_pr_curves(
        self,
        classes: Sequence[str] | None = None,
        iou_thresh: float | None = None,
        backend: str = "plotly",
        **kwargs: Any,
    ) -> Any:
        report = self.report_payload
        if self.is_subset or report is None:
            raise ValueError("AP50 PR curves are unavailable for this evaluation scope")
        if iou_thresh is not None and iou_thresh != _AP50_IOU:
            raise ValueError("Only authoritative IoU 0.50 PR curves are available")
        curves = [
            curve for curve in report.pr_curves if classes is None or curve.class_name in classes
        ]
        # Source curves have distinct recall grids; resampling would lose evidence.
        if backend == "plotly":
            import plotly.graph_objects as go  # type: ignore[import-untyped]

            figure = go.Figure()
            for curve in curves:
                figure.add_trace(
                    go.Scatter(
                        x=curve.recall,
                        y=curve.precision,
                        mode="lines",
                        name=curve.class_name,
                        customdata=curve.confidence,
                    )
                )
            figure.update_layout(xaxis_title="Recall", yaxis_title="Precision", **kwargs)
            return figure
        if backend == "matplotlib":
            import matplotlib.pyplot as plt

            figure, axes = plt.subplots()
            for curve in curves:
                axes.plot(curve.recall, curve.precision, label=curve.class_name)
            axes.set(xlabel="Recall", ylabel="Precision", **kwargs)
            if curves:
                axes.legend()
            return figure
        raise ValueError(f"Unsupported PR plot backend {backend!r}")

    def _visible_ids(self, field: str, ids: Mapping[str, str]) -> set[str]:
        if not self.has_subset:
            return set(ids.values())
        _, path = self.samples._get_label_field_path(field, "id")  # noqa: SLF001
        return set(self.samples.values(path, unwind=True))

    def label_ids(
        self,
        view_type: Literal["matrix", "field", "class"],
        x: str | None = None,
        y: str | None = None,
        status: str | None = None,
    ) -> tuple[list[str], list[str]]:
        visible_gt = self._visible_ids(self.config.gt_field, self.ground_truth_ids)
        visible_pred = self._visible_ids(self.config.pred_field, self.prediction_ids)
        if view_type == "matrix":
            inds = (self.ypred == x) & (self.ytrue == y)
            return (
                list(dict.fromkeys(value for value in self.ytrue_ids[inds] if value in visible_gt)),
                list(
                    dict.fromkeys(value for value in self.ypred_ids[inds] if value in visible_pred)
                ),
            )
        payload = self.source_payload
        return (
            self._box_ids(payload.ground_truth, self.ground_truth_ids, visible_gt, x, status),
            self._box_ids(payload.predictions, self.prediction_ids, visible_pred, x, status),
        )

    @staticmethod
    def _box_ids(
        boxes: list[EvaluationBox],
        ids: Mapping[str, str],
        visible: set[str],
        label: str | None,
        status: str | None,
    ) -> list[str]:
        return [
            ids[str(box.index)]
            for box in boxes
            if ids.get(str(box.index)) in visible
            and (label is None or box.label == label)
            and (status is None or box.status.lower() == status.lower())
        ]


def _label_ids(view: Any, field: str) -> dict[int, str]:
    result: dict[int, str] = {}
    for sample in view.iter_samples():
        detections = sample[field]
        for detection in detections.detections if detections is not None else []:
            index = int(detection.dm_index)
            if index in result:
                raise ValueError(f"Duplicate source index {index} in evaluation field {field!r}")
            result[index] = detection.id
    return result


def _write_native_fields(
    view: Any,
    payload: EvaluationPayload,
    key: str,
    gt_field: str,
    pred_field: str,
    matches: Sequence[NativeMatch],
) -> None:
    associations: dict[str, tuple[str | None, float | None]] = {}
    for _, _, iou, _, gt_id, pred_id in matches:
        if gt_id is not None:
            associations[gt_id] = (pred_id, iou)
        if pred_id is not None:
            associations[pred_id] = (gt_id, iou)
    gt = {box.index: box for box in payload.ground_truth}
    pred = {box.index: box for box in payload.predictions}
    for sample in view.iter_samples():
        for field, boxes in ((gt_field, gt), (pred_field, pred)):
            for detection in sample[field].detections:
                box = boxes[int(detection.dm_index)]
                association, iou = associations.get(detection.id, (None, None))
                detection[key] = box.status.lower() if box.status != "filtered" else None
                detection[f"{key}_id"] = association or ""
                detection[f"{key}_iou"] = iou
        name = sample.image_name
        sample[f"{key}_tp"] = sum(
            box.status == "TP" and box.image_name == name for box in payload.predictions
        )
        sample[f"{key}_fp"] = sum(
            box.status == "FP" and box.image_name == name for box in payload.predictions
        )
        sample[f"{key}_fn"] = sum(
            box.status == "FN" and box.image_name == name for box in payload.ground_truth
        )
        sample.save()


def publish_evaluation(
    dataset: Any,
    view: Any,
    payload: EvaluationPayload,
    eval_key: str,
    gt_field: str,
    pred_field: str,
    *,
    run_key: str,
) -> DigitalMetricsDetectionResults:
    """Register and persist one already-written split; caller owns old-run cleanup."""
    del dataset  # The view retains its root dataset and exact saved scope.
    with trace_operation("fiftyone.evaluation.labels.scan", context={"split": payload.split}):
        gt_ids = _label_ids(view, gt_field)
        pred_ids = _label_ids(view, pred_field)
    iou = payload.methodology.get("iou_threshold")
    if iou is not None and not isinstance(iou, (int, float)):
        raise ValueError("Evaluation methodology iou_threshold must be numeric")
    config = DigitalMetricsEvaluationConfig(
        pred_field,
        gt_field,
        cy_run_key=run_key,
        cy_split=payload.split,
        iou=float(iou) if iou is not None else None,
        thresholds=payload.thresholds,
        methodology=payload.methodology,
    )
    backend = DigitalMetricsEvaluation(config)
    matches = canonical_matches(payload, gt_ids, pred_ids)
    results = DigitalMetricsDetectionResults(
        view,
        config,
        eval_key,
        matches,
        source_payload=payload.model_dump(mode="json"),
        ground_truth_ids={str(k): v for k, v in gt_ids.items()},
        prediction_ids={str(k): v for k, v in pred_ids.items()},
        backend=backend,
    )
    with trace_operation("fiftyone.evaluation.register", context={"split": payload.split}):
        backend.register_run(view, eval_key, overwrite=False)
        backend.register_samples(view, eval_key, dynamic=True)
    with trace_operation(
        "fiftyone.evaluation.samples.write",
        context={"split": payload.split, "images": len(payload.image_names)},
    ):
        _write_native_fields(view, payload, eval_key, gt_field, pred_field, matches)
    with trace_operation("fiftyone.evaluation.results.save", context={"split": payload.split}):
        backend.save_run_results(view, eval_key, results)
        backend.add_fields_to_sidebar_group(view, eval_key)
    return results
