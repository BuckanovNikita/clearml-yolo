# Evaluation plot presentation

Titles: Precision-recall and Confusion matrix. Series: model display name · split.
Confusion selector labels: Counts, Row %, Column %, Overall %. Counts is initially
visible; exactly one heatmap is visible. PR is published only for split test, with
class legends containing AP50 and method, and class/metric hover information.
Empty classes retain explicit legend status using null gaps without numerical points.

Publication excludes comparison_baseline charts. Comparison report tables are not
published; downloadable workbooks and headline values remain. Native training callback
PR images are excluded. Plot captions contain no internal identifiers. Other artifact,
provenance, metric calculation and command contracts remain unchanged.

## Cross-contract integration

Each current-model split has one `Confusion matrix` chart with selectable `Counts`,
`Row %`, `Column %` and `Overall %` views of exact post-threshold counts; Counts is default.
One `Precision-recall` chart combines class traces at IoU 0.50 on test only.
Baseline charts and comparison/degraded-class/methodology tables are excluded from Plots;
baseline dashboards/rows, paired reports and headline single values remain available.
Matrix rows are true labels, columns predicted labels;
normalization preserves counts/order/background and shows zero-denominator observations.
PR uses authoritative geometry-valid AP populations and public matching, with AP50 parity
checks for methods, strategies and ties. No GT has unavailable recall/AP; GT without
predictions has empty PR/AP50 zero. Empty populations have explicit class-legend status
and null-gap traces without numerical points. Class legends retain AP/method; hover retains confidence and cumulative
TP/FP. Readable model/split series omit internal IDs and hashes; checkpoint/split slots
are reused, with model/context fallback and readable stage/ordinal collision suffixes.
Numeric and Unicode class labels remain distinct. See the
[presentation amendment](plots.md).
