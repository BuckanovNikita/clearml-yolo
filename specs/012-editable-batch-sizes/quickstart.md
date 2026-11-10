# Validation guide

Prepare dependencies and hooks using [development procedures](../../docs/development.md). Run focused batch tests, project verify, branch mutation report, clean-tip acceptance and final hooks. Follow live-test and environment skills before native GPU work; retain dated evidence separately.

For a bounded native measurement, select an idle GPU and supported cached model:

```bash
cy-batch-estimate --imgsz 640 --models yolo11n --devices 0 --search-limit 3
cy-batch-estimate --list --models yolo11n
```

Expect fixed 150 classes, a separately confirmed batch no larger than three and an editable YAML entry only after worker cleanup. Use isolated `CY_HOME` for verification. Edit the entry, resolve `batch=null`, and inspect table digest and selected-source provenance. Never treat mocked probes as native training evidence.
