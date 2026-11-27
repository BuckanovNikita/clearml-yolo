# ADR-0100 · Carry one ground truth population from source to native training data

CY uses a ground truth CSV to carry image membership, split, class identity and pixel coordinates across detector families. Conversion produces that contract, each experiment resolves its source once, and training builds the native layout from validated records. The prepared dataset can then be shared across runs.

## Conversion and source resolution

`cy-ground-truth` reads the effective dataset YAML connected to its ClearML task. It translates YOLO class indices and normalized boxes into labeled pixel boxes, and emits a membership row for each background image. If the dataset has no test images, `test_fraction` and the seed select validation images by name for the test split. When the installed Ultralytics reader and the historical YAML interpretation disagree about class names, conversion fails before writing the CSV. Successful conversion publishes `gt_csv`. [Conversion workflow](../src/clearml_yolo/application/use_cases/ground_truth.py)

Training and evaluation accept a local CSV, a ClearML Dataset ID or a project/name selector with an optional version. CY downloads a finalized dataset without soft links and requires its ground truth CSV at the root as `dataset.csv`. It records the resolved dataset identity, version and CSV digest and passes that resolution into nested stages. A later invocation with an unversioned selector can resolve a newer version. Local paths carry a warning. [Ground truth sources](../src/clearml_yolo/application/ground_truth.py)

<details>
<summary>Sources and verification</summary>

- Convert a YOLO dataset into ground truth — [YOLO reader and split selection](../src/clearml_yolo/adapters/yolo/ground_truth.py) · [Conversion, YAML compatibility and split tests](../tests/test_ground_truth.py) · [Command guide](../docs/commands/cy-ground-truth.md) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/datasets-and-ground-truth.md#yolo-conversion-with-cy-ground-truth)
- Resolve a ground truth source once per invocation — [ClearML dataset adapter](../src/clearml_yolo/adapters/clearml/datasets.py) · [Source resolution tests](../tests/test_ground_truth_sources.py) · [Source forms](../docs/formats/ground-truth.md) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/datasets-and-ground-truth.md#ground-truth-sources)

</details>

## Image identity and validation

The CSV preserves `image_name`, `image_path` and `instance_label` as text, so numeric-looking identifiers keep their meaning. Relative image paths resolve from the CSV directory. Each object row supplies four pixel corners and a split. An empty label and empty coordinates preserve a background image's membership. During preparation, a name must identify the same image and split throughout. Duplicate background rows and duplicate valid annotations fail. Invalid boxes are dropped and counted individually, including identical invalid rows. Preparation rejects the literal reserved label `background` before opening media. [Ground truth format](../docs/formats/ground-truth.md) · [Duplicate-row cases](../tests/test_dataset_records.py)

The consuming stage chooses a Pandera schema. It checks a table without changing its cells, rewriting identifiers or dropping rows. A failure identifies the stage and includes findings with the original row labels where available. For example, raw predictions retain invalid geometry so scoring can later explain why a row was filtered. Invalid confidence already fails at the raw stage. Prepared, publication and result tables each have constraints appropriate to their consumers. Prediction only needs the ground truth image population and does not validate its class vocabulary. [Dataframe schemas](../src/clearml_yolo/core/validation/schemas.py)

<details>
<summary>Sources and verification</summary>

- Preserve image membership and lexical identity in ground truth — [Detection CSV reader](../src/clearml_yolo/adapters/storage/file_io.py) · [Preparation validation](../src/clearml_yolo/adapters/storage/dataset_records.py) · [Reserved label decision](https://linear.app/sip-ds-team/issue/SIP-218) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/datasets-and-ground-truth.md#csv-interpretation)
- Validate tables at the stage that consumes them — [Validation and non-mutation cases](../tests/test_dataframe_validation.py) · [Decision history](https://github.com/BuckanovNikita/clearml-yolo/commit/493f0399fc10c2f99ac072335115f754176baa14)

</details>

## Native layouts and cache identity

Training needs valid training boxes and populated required splits. An image whose boxes were all dropped can remain as a background image. CY copies the selected images and annotations into NDJSON or flat YOLO for Ultralytics, or COCO for the other detector families. NDJSON preserves basenames. Flat and COCO layouts use numbered filenames. Generated YAML quotes class names so values such as `1e3` remain strings across readers. [Native format writers](../src/clearml_yolo/adapters/storage/dataset_export.py)

Under `dataset_cache_dir`, CY keys the prepared copy by CSV bytes, ordered resolved image references, format and preparation version. A per-key lock and staging directory let concurrent jobs publish a complete entry before another job reuses it. A hit validates the layout and can skip reopening source images. Replacing an image's bytes at the same path therefore leaves the key unchanged. A preparation-version change creates another entry. CY retains completed entries. [Cache implementation](../src/clearml_yolo/adapters/storage/dataset_cache.py) · [Cache identity decision](https://linear.app/sip-ds-team/issue/SIP-219)

<details>
<summary>Sources and verification</summary>

- Prepare native training datasets from validated records — [Record validation and filtering](../src/clearml_yolo/adapters/storage/dataset_records.py) · [Export contract cases](../tests/test_dataset_export.py) · [COCO layout cases](../tests/test_coco_dataset.py) · [Dataset formats](../docs/formats/datasets.md) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/datasets-and-ground-truth.md#training-validation-and-preparation)
- Share prepared datasets under a locked content key — [Reuse and locking tests](../tests/test_dataset_cache.py) · [Archived feature contract](https://github.com/BuckanovNikita/clearml-yolo/blob/4c5a9d595dafb79c65a939cf2d43aeb896d455a8/docs/feature/datasets-and-ground-truth.md#dataset-cache)

</details>
