"""Opt-in FiftyOne UI boundary for imported, authoritative evaluations.

FiftyOne's panel contexts, operators, views and builtin panel API are untyped;
``Any`` stays at this boundary. Import this module only when using the plugin.
"""

from importlib.resources import as_file, files
from pathlib import Path
from typing import Any, Literal

import fiftyone.utils.eval as evaluation
from fiftyone import plugins
from fiftyone.operators import types
from fiftyone.operators.panel import Panel, PanelConfig
from plugins.panels.model_evaluation import EvaluationPanel  # type: ignore[import-untyped]
from plugins.utils.model_evaluation import (  # type: ignore[import-untyped]
    get_subsets_from_custom_code,
)

from clearml_yolo.adapters.fiftyone.evaluation import DigitalMetricsDetectionResults
from clearml_yolo.core.evaluation.payload import EvaluationReport

PLUGIN_NAME = "@clearml-yolo/evaluation"


def install_evaluation_plugin(*, overwrite: bool = False) -> Path:
    """Explicitly install the packaged Python plugin in the configured plugin directory."""
    resource = files("clearml_yolo.adapters.fiftyone.plugin")
    with as_file(resource) as directory:
        installed = plugins.create_plugin(
            PLUGIN_NAME,
            from_files=[str(directory / name) for name in ("__init__.py", "fiftyone.yml")],
            overwrite=overwrite,
        )
    return Path(installed)


def report_data(report: EvaluationReport | None, *, is_subset: bool) -> dict[str, Any]:
    """Return original AP values and PR observations; never calculate missing evidence."""
    if is_subset or report is None:
        reason = (
            "AP and PR are unavailable for subsets; fixed-threshold results remain available."
            if is_subset
            else "This evaluation has no persisted AP/PR report."
        )
        return {"available": False, "reason": reason, "average_precisions": [], "curves": []}
    rows = []
    for label in report.classes:
        precision = report.average_precisions.get(label)
        rows.append(
            {
                "class": label,
                "AP50": precision.ap50 if precision else None,
                "AP75": precision.ap75 if precision else None,
                "AP50-95": precision.ap50_95 if precision else None,
            }
        )
    curves = [
        {
            "type": "scatter",
            "mode": "lines+markers",
            "name": curve.class_name,
            "x": curve.recall,
            "y": curve.precision,
            "customdata": curve.confidence,
            "hovertemplate": (
                "Recall %{x}<br>Precision %{y}<br>Confidence %{customdata}"
                "<extra>%{fullData.name}</extra>"
            ),
        }
        for curve in report.pr_curves
        if curve.gt_count > 0
    ]
    return {"available": True, "reason": "", "average_precisions": rows, "curves": curves}


def select_evaluation_labels(
    view: Any, gt_field: str, pred_field: str, gt_ids: list[str], pred_ids: list[str]
) -> Any:
    """Keep only exact evaluated labels, removing samples without selected labels."""
    return view.select_labels(ids=[*gt_ids, *pred_ids], fields=[gt_field, pred_field])


def _evaluation_key(ctx: Any) -> str | None:
    state = ctx.panel.get_state("view") or {}
    key = ctx.params.get("key", state.get("key"))
    return str(key) if key is not None else None


def _is_project(ctx: Any) -> bool:
    key = _evaluation_key(ctx)
    return bool(key and ctx.dataset.get_evaluation_info(key).config.method == "digital_metrics")


def _scenario_definitions(ctx: Any, scenario: dict[str, Any]) -> dict[str, Any]:
    scenario_type = scenario.get("type")
    subsets = scenario.get("subsets", [])
    if scenario_type == "custom_code":
        definitions, error = get_subsets_from_custom_code(ctx, subsets)
        if error:
            raise ValueError(error)
        return definitions if isinstance(definitions, dict) else {"All": definitions}
    if scenario_type == "view":
        return {name: {"type": "view", "view": name} for name in subsets}
    field = scenario.get("field", "")
    if scenario_type == "sample_field":
        return {name: {"type": "field", "field": field, "value": name} for name in subsets}
    if scenario_type == "label_attribute":
        return {
            name: {"type": "attribute", "field": field.split(".")[-1], "value": name}
            for name in subsets
        }
    raise ValueError(f"Unsupported scenario type: {scenario_type}")


def _navigation_ids(
    results: Any, view_type: Literal["matrix", "field", "class"], options: dict[str, Any]
) -> tuple[list[str], list[str]]:
    if isinstance(results, DigitalMetricsDetectionResults):
        gt_ids, pred_ids = results.label_ids(
            view_type=view_type,
            x=options.get("x"),
            y=options.get("y"),
            status=options.get("field"),
        )
        return list(gt_ids), list(pred_ids)
    gt_ids, pred_ids = [], []
    for true, predicted, gt_id, pred_id in zip(
        results.ytrue, results.ypred, results.ytrue_ids, results.ypred_ids, strict=True
    ):
        if _stock_selected(true, predicted, results.missing, view_type, options):
            if gt_id is not None and options.get("field") != "fp":
                gt_ids.append(str(gt_id))
            if pred_id is not None and options.get("field") != "fn":
                pred_ids.append(str(pred_id))
    return gt_ids, pred_ids


def _stock_selected(
    true: str, predicted: str, missing: str, view_type: str, options: dict[str, Any]
) -> bool:
    if view_type == "matrix":
        return true == options.get("y") and predicted == options.get("x")
    if view_type == "class":
        return true == options.get("x") or predicted == options.get("x")
    checks = {
        "tp": true == predicted and true != missing,
        "fp": true == missing,
        "fn": predicted == missing,
    }
    return checks.get(str(options.get("field")), False) if view_type == "field" else False


class NativeEvaluationPanel(EvaluationPanel):  # type: ignore[misc, no-any-unimported]
    """Native evaluation UI with exact imported totals and label navigation."""

    @property
    def config(self) -> Any:
        return PanelConfig(
            name="native_evaluation", label="Imported Model Evaluation", icon="ssid_chart"
        )

    def get_tp_fp_fn(self, info: Any, results: Any) -> tuple[Any, Any, Any]:
        if info.config.method == "digital_metrics":
            return tuple(results.tp_fp_fn())
        return tuple(super().get_tp_fp_fn(info, results))

    def get_confusion_matrix(self, results: Any) -> Any:
        if not isinstance(results, DigitalMetricsDetectionResults):
            return super().get_confusion_matrix(results)
        matrix, classes, _ = results._confusion_matrix(  # noqa: SLF001
            include_other=False, include_missing=True, tabulate_ids=False
        )
        # Upstream log interpolation divides by zero for an all-zero or unit matrix.
        logarithmic = bool(matrix.size and matrix.max() > 1)
        return {
            "matrix": matrix,
            "classes": classes,
            "primary_colorscale": self.get_confusion_matrix_colorscale(matrix, "oranges"),
            "oranges_logarithmic_colorscale": self.get_confusion_matrix_colorscale(
                matrix, "oranges", logarithmic=logarithmic
            ),
            "secondary_colorscale": self.get_confusion_matrix_colorscale(matrix, "blues"),
            "blues_logarithmic_colorscale": self.get_confusion_matrix_colorscale(
                matrix, "blues", logarithmic=logarithmic
            ),
        }

    def _configure_matrix_display(self, ctx: Any, matrix_key: str) -> None:
        configured = ctx.panel.get_state("native_matrix_configured") or []
        if matrix_key in configured:
            return
        # The native component stores its display options above the Python panel's
        # state. Its default hides zero-diagonal classes, including wrong-class errors
        # and background. The builtin full_merge operation seeds those native options.
        ctx.trigger(
            "patch_panel_state",
            params={
                "panel_id": ctx.panel.id,
                "full_merge": True,
                "state": {
                    matrix_key: {
                        "sortBy": "default",
                        "limit": None,
                        "log": False,
                        "skipZeroCount": False,
                    }
                },
            },
        )
        ctx.panel.set_state("native_matrix_configured", [*configured, matrix_key])

    def load_evaluation(self, ctx: Any) -> None:
        if _is_project(ctx):
            evaluation_id = self.get_evaluation_id(ctx.dataset, _evaluation_key(ctx))
            self._configure_matrix_display(ctx, f"{evaluation_id}_cmc")
        super().load_evaluation(ctx)

    def get_map(self, results: Any) -> float | None:
        # Native mAP means this project's mean AP50-95, not subset recomputation.
        if isinstance(results, DigitalMetricsDetectionResults):
            report = results.report_payload
            if results.is_subset or report is None:
                return None
            values = [
                value.ap50_95
                for value in report.average_precisions.values()
                if value.ap50_95 is not None
            ]
            return sum(values) / len(values) if values else None
        return super().get_map(results)  # type: ignore[no-any-return]

    def get_mar(self, results: Any) -> float | None:
        if isinstance(results, DigitalMetricsDetectionResults):
            return None
        return super().get_mar(results)  # type: ignore[no-any-return]

    def get_evaluation_data_cacheable(self, ctx: Any) -> Any:
        # The builtin decorators capture builtin key functions and share a long-lived
        # store. Imported runs can be repaired under the same ID, so read them fresh.
        if _is_project(ctx):
            return self.get_evaluation_data(ctx)
        return super().get_evaluation_data_cacheable(ctx)

    def get_evaluation_data(self, ctx: Any) -> Any:
        if not _is_project(ctx):
            return super().get_evaluation_data(ctx)
        key = _evaluation_key(ctx)
        info = ctx.dataset.get_evaluation_info(key)
        results = ctx.dataset.load_evaluation_results(key, cache=False)
        metrics = results.metrics()
        per_class = self.get_per_class_metrics(info, results)
        metrics["average_confidence"] = self.get_avg_confidence(self.get_confidences(per_class))
        metrics["tp"], metrics["fp"], metrics["fn"] = results.tp_fp_fn()
        metrics["mAP"], metrics["mAR"] = self.get_map(results), None
        return {
            "metrics": metrics,
            "custom_metrics": self.get_custom_metrics(results),
            "info": info.serialize(),
            "confusion_matrix": self.get_confusion_matrix(results),
            "per_class_metrics": per_class,
            "mask_targets": None,
            "missing": results.missing,
        }

    def get_scenario_data_cacheable(self, ctx: Any, scenario: Any) -> Any:
        if _is_project(ctx):
            return self.get_scenario_data(ctx, scenario)
        return super().get_scenario_data_cacheable(ctx, scenario)

    def get_scenario_data(self, ctx: Any, scenario: Any) -> Any:
        if not _is_project(ctx):
            return super().get_scenario_data(ctx, scenario)
        key = _evaluation_key(ctx)
        results = ctx.dataset.load_evaluation_results(key, cache=False)
        info = ctx.dataset.get_evaluation_info(key)
        definitions = _scenario_definitions(ctx, scenario)
        data = dict(scenario)
        data["subsets_data"] = {
            name: self.get_subset_def_data(info, results, definition, "key" in ctx.params)
            for name, definition in definitions.items()
        }
        if scenario.get("type") == "custom_code":
            data["subsets_code"] = scenario.get("subsets")
            data["subsets"] = list(definitions)
        return data

    def load_scenario(self, ctx: Any) -> None:
        if not _is_project(ctx):
            # The builtin refresh calls .clear_cache on its decorated method.
            # Our override is deliberately uncached; use the stock bound wrapper.
            refresh = ctx.params.pop("refresh_cache", False)
            try:
                if refresh:
                    scenario = self.get_scenario(ctx, str(ctx.params.get("id") or ""))
                    validated, _ = self.validate_scenario_subsets(ctx, scenario)
                    super().get_scenario_data_cacheable.clear_cache(self, ctx, validated)
                super().load_scenario(ctx)
            finally:
                ctx.params["refresh_cache"] = refresh
            return
        scenario_id = str(ctx.params.get("id") or "")
        try:
            self._load_project_scenario(ctx, scenario_id)
        except (KeyError, TypeError, ValueError) as error:
            # This operator boundary reports invalidated views and user-code failures.
            ctx.panel.set_state("scenario_loading", False)
            ctx.panel.set_state(
                "scenario_load_error",
                {
                    "code": "scenario_load_error",
                    "error": str(error),
                    "id": scenario_id,
                },
            )

    def _load_project_scenario(self, ctx: Any, scenario_id: str) -> None:
        scenario = self.get_scenario(ctx, scenario_id)
        if scenario is None:
            raise ValueError("This scenario has been removed.")
        validated, changes = self.validate_scenario_subsets(ctx, scenario)
        if changes and not validated.get("subsets"):
            ctx.panel.set_state("scenario_loading", False)
            ctx.panel.set_state(
                "scenario_load_error",
                {
                    "code": "scenario_load_error",
                    "error": "Scenario subsets are unavailable.",
                    "id": scenario_id,
                },
            )
            return
        ctx.panel.set_state(
            f"scenario_{scenario_id}_changes",
            {
                "scenario": validated,
                "changes": changes,
                "id": scenario_id,
            }
            if changes
            else None,
        )
        data = self.get_scenario_data(ctx, validated)
        for subset_name in data.get("subsets_data", {}):
            self._configure_matrix_display(ctx, f"{subset_name}_matrix_config")
        ctx.panel.set_data(f"scenario_{scenario_id}_{_evaluation_key(ctx)}", data)
        ctx.panel.set_state("scenario_load_error", None)
        ctx.panel.set_state("scenario_loading", False)

    def rename_evaluation(self, ctx: Any) -> None:
        super().rename_evaluation(ctx)
        state = ctx.panel.get_state("view") or {}
        new_name = ctx.params.get("new_name")
        if (
            state.get("key") == ctx.params.get("old_name")
            and new_name in ctx.dataset.list_evaluations()
        ):
            ctx.panel.set_state("view", {**state, "key": new_name, "init": True})
        self.on_load(ctx)

    def delete_evaluation(self, ctx: Any) -> None:
        super().delete_evaluation(ctx)
        state = ctx.panel.get_state("view") or {}
        if (
            state.get("key") == ctx.params.get("eval_key")
            and state.get("key") not in ctx.dataset.list_evaluations()
        ):
            ctx.panel.set_state("view", {"page": "overview", "init": True})
        self.on_load(ctx)

    def load_view(self, ctx: Any) -> None:
        if ctx.params.get("type") == "clear":
            ctx.ops.clear_view()
            return
        options = ctx.params.get("options") or {}
        key = options.get("key", _evaluation_key(ctx))
        info = ctx.dataset.get_evaluation_info(key)
        if info.config.method != "digital_metrics":
            super().load_view(ctx)
            return
        view = ctx.dataset.load_evaluation_view(key)
        subset = options.get("subset_def")
        if subset and subset.get("type") == "custom_code":
            subsets, error = get_subsets_from_custom_code(ctx, subset.get("code"))
            if error:
                ctx.ops.notify(error, variant="error")
                return
            subset = subsets.get(subset.get("subset"))
        if subset is not None:
            view = evaluation.get_subset_view(view, info.config.gt_field, subset)
        view_type = ctx.params.get("type")
        if view_type == "subset":
            ctx.ops.set_view(view)
            return
        state = ctx.panel.get_state("view") or {}
        keys = [key, *([state["compareKey"]] if state.get("compareKey") else [])]
        ids, fields = [], []
        for evaluation_key in keys:
            config = ctx.dataset.get_evaluation_info(evaluation_key).config
            results = ctx.dataset.load_evaluation_results(evaluation_key, cache=False)
            with results.use_subset(view):
                gt_ids, pred_ids = _navigation_ids(results, view_type, options)
            ids.extend([*gt_ids, *pred_ids])
            fields.extend([config.gt_field, config.pred_field])
        selected = view.select_labels(ids=ids, fields=list(dict.fromkeys(fields)))
        ctx.ops.set_view(selected)


class EvaluationReportsPanel(Panel):  # type: ignore[misc, no-any-unimported]
    """Original class AP table and confidence-ordered AP50 precision/recall curves."""

    @property
    def config(self) -> Any:
        return PanelConfig(
            name="evaluation_reports", label="Imported AP / PR Reports", icon="show_chart"
        )

    def on_load(self, ctx: Any) -> None:
        keys = [
            key
            for key in ctx.dataset.list_evaluations()
            if ctx.dataset.get_evaluation_info(key).config.method == "digital_metrics"
        ]
        ctx.panel.set_state("evaluation_keys", keys)
        key = ctx.panel.get_state("evaluation_key")
        if key not in keys:
            ctx.panel.set_state("evaluation_key", keys[0] if keys else None)
        self.load_report(ctx)

    def on_change_view(self, ctx: Any) -> None:
        self.on_load(ctx)

    def load_report(self, ctx: Any) -> None:
        key = ctx.panel.get_state("evaluation_key")
        if key is None:
            data = report_data(None, is_subset=False)
        else:
            results = ctx.dataset.load_evaluation_results(key, cache=False)
            with results.use_subset(ctx.view):
                data = report_data(results.report_payload, is_subset=results.is_subset)
        ctx.panel.set_data("report", data)
        ctx.panel.set_data("pr_curves", data["curves"])
        ctx.panel.set_data("average_precisions", data["average_precisions"])
        ctx.panel.set_state(
            "report_status", {"available": data["available"], "reason": data["reason"]}
        )

    def render(self, ctx: Any) -> Any:
        panel = types.Object()
        keys = ctx.panel.get_state("evaluation_keys") or []
        panel.enum("evaluation_key", keys, label="Evaluation", on_change=self.load_report)
        data = ctx.panel.get_state("report_status") or {}
        if not data.get("available"):
            panel.md(data.get("reason", "No imported evaluation is available."))
        else:
            panel.md(
                "Original producer AP50, AP75 and AP50-95. Null means unavailable. "
                "PR curves use IoU 0.50 and the authoritative confidence-ordered population."
            )
            table = types.TableView()
            for column in ("class", "AP50", "AP75", "AP50-95"):
                table.add_column(column, label=column)
            panel.list("average_precisions", types.Object(), view=table)
            panel.plot(
                "pr_curves",
                layout={
                    "title": "Precision-Recall at IoU 0.50",
                    "xaxis": {"title": "Recall", "range": [0, 1]},
                    "yaxis": {"title": "Precision", "range": [0, 1]},
                },
            )
        return types.Property(panel)
