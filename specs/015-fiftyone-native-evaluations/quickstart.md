# Validation guide

Run the documented repository checks, then the opt-in FiftyOne persistence suite with
an explicitly isolated database directory. Install the packaged plugin into a task-owned
plugin directory and launch a task-owned App for browser verification. Publish fixtures
with wrong-class/duplicate/empty/filtered labels and real metrics outputs. Compare every
count, confusion cell and report value; click cells and TP/FP/FN selectors. Confirm
`matched_predictions` retains filtered audit labels, `evaluated_predictions` excludes
them, and native patch views never count filtered labels as unmatched false positives. Restart the
reader process, republish, rename/delete a test evaluation and verify other runs survive.
Run real metrics/pipeline acceptance using the project end-to-end and environment skills.
Record checks and limitations in dated evidence, then clean up only task-owned resources.
