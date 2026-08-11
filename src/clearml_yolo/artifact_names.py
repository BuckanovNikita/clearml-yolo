"""Every ClearML artifact name this project writes or reads back.

The names had drifted into three unsynchronised spellings of one stem — the on-disk
workbook ``full_dashboard_test.xlsx``, the artifact ``dashboard_full_test``, and a
user-overridable ``artifact_prefix`` default carrying a fourth copy — and two of them are
read back off *previous* tasks, where a mismatch surfaces only as a silently missing
baseline. Naming them once here is what keeps writer and reader in step.

Every name is prefixed with the stage that produced it. The ClearML artifacts tab has four
fixed sections (input model, output models, data audit, other) and no grouping of its own,
so a stage prefix is the only thing that makes one run's artifacts read as related. Genuine
collapsible sections exist in the plots and scalars tabs, keyed by title — see
:mod:`clearml_yolo.clearml_report`.
"""

from __future__ import annotations

PREDICTIONS = "predict_predictions"

DASHBOARD_FULL_PREFIX = "metrics_dashboard_full"
DASHBOARD_DTRK_PREFIX = "metrics_dashboard_dtrk"
MATCHES_GT_PREFIX = "metrics_matches_gt"
MATCHES_PREDS_PREFIX = "metrics_matches_preds"
METRICS_SUMMARY_PREFIX = "metrics_summary"
METRICS_RAW_PREFIX = "metrics_raw"
BEST_CONFIDENCES_PREFIX = "metrics_best_confidences"

REPORT_DEV_PREFIX = "report_dev"
REPORT_BUSINESS_PREFIX = "report_business"

COMPARISON_WORKBOOK_PREFIX = "compare_workbook"

# Titles of the collapsible sections in the plots and scalars tabs. The comparison stage
# owns three more of its own, declared next to the report that writes them.
METRICS_SECTION = "metrics"
REPORT_SECTION = "report"
PREDICT_SECTION = "predict"

# The one series under PREDICT_SECTION. A stage that scores every split writes its section
# once per split; inference resolves its resolution once for the whole run, so the series
# names what the table is about rather than which split it belongs to.
RESOLUTION_SERIES = "resolution"


def per_split(prefix: str, split: str) -> str:
    """Name the artifact one stage produced for one split.

    Every stage of a pipeline run shares a single ClearML task, so a split suffix is what
    keeps three evaluations of the same model from overwriting each other.
    """
    return f"{prefix}_{split}"
