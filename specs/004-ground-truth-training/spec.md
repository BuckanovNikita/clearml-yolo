# Feature Specification: Ground-Truth-Driven Training

**Feature Branch**: `004-ground-truth-training`

**Created**: 2026-09-29

**Status**: Implemented and verified

**Input**: User description (format name corrected by the user to NDJSON): "Next feature is full training based only on provided ground truth file. Convert from input csv to ultraltics ndjson dataset or flat dataset (support both by default ndjson switch by tool params). Override yolo params related to data if need"

**Current-only amendment (2026-10-02)**: The
[remove-legacy-compatibility feature](../012-remove-legacy-compatibility/spec.md) supersedes
the original direct native-data exception. Standalone `cy-train` now requires `ground_truth`,
and successful training always returns its prepared dataset paths. The original decision remains
below where needed to explain completed history.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Train directly from ground truth (Priority: P1)

As a model developer, I provide one ground-truth CSV referencing my images and run
training without separately preparing labels, a dataset descriptor, or a class list.
The same input drives the full pipeline so training and evaluation agree on the data.

**Why this priority**: Removes duplicate dataset preparation and prevents training on
annotations or splits different from those used to evaluate the resulting model.

**Independent Test**: With accessible images and a valid CSV, run standalone training
and the full pipeline without a pre-existing native dataset. Verify a trained checkpoint
and the pipeline's requested evaluation outputs using only the supplied data.

**Acceptance Scenarios**:

1. **Given** a valid detection CSV with train, val, and test images, **When** `cy` runs
   with `ground_truth` and ordinary execution settings, **Then** dataset preparation,
   training, prediction, and metrics complete; comparison and reports follow the existing
   baseline and skip rules, with no separately supplied native dataset.
2. **Given** a valid CSV with train and val images, **When** `cy-train` runs with
   `ground_truth`, **Then** it prepares the default NDJSON dataset and produces its best
   checkpoint without requiring a test split.
3. **Given** multiple boxes on an image and explicit background images, **When** training
   data is prepared, **Then** each image appears once, all annotated instances survive,
   and background images remain with no fabricated boxes. Invalid boxes follow
   the drop-and-report policy below.
4. **Given** a full pipeline invocation, **When** training finishes, **Then** predictions,
   validation calibration, test evaluation, and any baseline comparison use the same image
   identities, class meanings, and split membership as the supplied CSV.

### User Story 2 - Select either dataset representation (Priority: P1)

As a model developer, I can choose NDJSON or a conventional flat YOLO dataset using a tool
parameter, without changing my ground-truth file or manually converting annotations.

**Why this priority**: Both representations are explicitly required and must support the
same training task.

**Independent Test**: Prepare and train the same representative CSV in both modes;
compare image membership, annotations, class mapping, and split assignments.

**Acceptance Scenarios**:

1. **Given** no format override, **When** either training command runs in CSV mode,
   **Then** the selected format is `ndjson`, using Ultralytics-compatible NDJSON content.
2. **Given** the tool parameter `dataset_format=flat`, **When** either command runs in
   CSV mode, **Then** it generates a native dataset descriptor and per-image YOLO labels
   with flat image and label collections within each split, without class subdirectories.
3. **Given** equivalent input in both modes, **When** generated datasets are inspected,
   **Then** they contain identical images, class mappings, boxes, and splits, within the
   documented coordinate tolerance; neither mode silently falls back to the other.
4. **Given** an unsupported format value, **When** the command starts, **Then** it fails
   before training and lists `ndjson` and `flat` as accepted values.

### User Story 3 - Keep data ownership explicit and inspectable (Priority: P2)

As a model developer, I can reuse training settings knowing the supplied CSV
controls the dataset, and I can inspect what was generated and overridden after a run.

**Why this priority**: Stale dataset settings must not silently change the experiment.

**Independent Test**: Supply a conflicting native dataset setting and inspect the effective
configuration, generated data inventory, and tracking records for both formats.

**Acceptance Scenarios**:

1. **Given** a CSV and a stale `ultralytics.data`, **When** training starts, **Then** the
   generated dataset wins, and the original and effective dataset settings are recorded.
2. **Given** explicitly chosen epochs, device, batch, and augmentation settings,
   **When** CSV dataset preparation runs, **Then** those unrelated settings retain their
   existing precedence and values.
3. **Given** invalid bounding boxes alongside usable training annotations, **When** preparation
   runs, **Then** it drops only invalid boxes, displays the total error-box count before
   training, preserves valid boxes and images, and continues without modifying source files.
4. **Given** successful computation but a required artifact upload or flush failure,
   **When** the invocation ends, **Then** the command and its single tracking task fail,
   and local preparation and training outputs remain available for diagnosis.
5. **Given** repeated or concurrent invocations, **When** datasets are prepared,
   **Then** each run owns its generated files without overwriting another run or the inputs.
6. **Given** inaccessible images or structurally invalid input, **When** preparation runs,
   **Then** the invocation fails before training with the offending row or image and reason.
7. **Given** an image whose boxes are all invalid, **When** preparation removes them,
   **Then** the image remains as a background image in its original split, and the pipeline
   uses the same cleaned annotations for training and evaluation.

### Edge Cases

- Empty CSV, missing required columns, absent labels across the entire CSV, unknown split
  values, or missing required train/val/requested evaluation splits fail before training.
- Multiple rows for one image are expected; inconsistent paths or splits for that image
  fail. One resolved image cannot belong to multiple splits or image identities.
- An image name identifying different source files fails, preserving the existing evaluation
  identity contract. Distinct names sharing a filename stem must not overwrite flat labels.
- Empty labels and all four empty coordinates denote background and do not count as errors.
  Partially empty boxes or attempted annotations without a class label are dropped and
  counted as invalid boxes. Background rows mixed with annotations for one image remain
  a structural input error.
- Non-numeric or non-finite coordinates, non-positive box sizes, and coordinates outside
  image bounds cause the affected box to be dropped and counted, without clipping or
  stopping an otherwise usable run. Boundary-aligned boxes are valid.
- Each dropped annotation row counts once even if it has multiple box errors. Valid boxes
  on the same image remain; an image with no surviving boxes becomes background. If no
  valid training instances remain anywhere, report the error-box total and the unusable
  training-set error before attempting training.
- Missing or unreadable images fail. Relative paths resolve against the CSV's directory;
  spaces and non-ASCII paths and class names remain usable.
- Row reordering does not change class IDs, image membership, or split assignments.
  Exact duplicate valid annotation rows fail explicitly rather than silently changing multiplicity.
  Duplicate invalid box rows are each dropped and counted.
- Classes present only in validation or test retain their names and receive a visible
  training-coverage warning; they are neither discarded nor moved into training.
- Interrupted preparation, insufficient disk space, and native conversion failures leave
  diagnostic output and cannot count as a completed dataset or successful run.
- A requested resume restoring different data or class meanings fails with guidance
  instead of bypassing CSV ownership.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `cy` MUST derive training data from its supplied `ground_truth` CSV whenever
  training is enabled. `cy-train` MUST accept the same CSV input for standalone training.
  Neither CSV flow may require a separate dataset, class list, or label directory.
- **FR-002**: CSV mode MUST accept the established columns `image_name`, `image_path`,
  `instance_label`, `bbox_x_tl`, `bbox_y_tl`, `bbox_x_br`, `bbox_y_br`, and `split`.
  Additional columns MUST NOT become annotations or alter these fields' meanings.
  Class labels are names and box coordinates are absolute pixel corners. `image_name`
  MUST equal the referenced file basename, matching the existing evaluation identity contract.
- **FR-003**: The system MUST resolve absolute paths directly and relative paths against
  the CSV directory, verify readable images, and use their dimensions when converting boxes.
  Training and downstream evaluation MUST use the same resolved image identities.
- **FR-004**: The system MUST validate the complete input before training, enforce the edge
  case rules above, and distinguish recoverable invalid boxes from fatal structural or image
  errors. It MUST drop and count invalid boxes, retain valid boxes and image membership,
  and report actionable row/image-specific reasons. Invalid boxes alone MUST NOT fail an
  otherwise usable run. Source files MUST remain unchanged.
- **FR-005**: The system MUST preserve supplied train/val/test membership without automatic
  splitting or reassignment. Training requires nonempty train and val splits and at least
  one valid annotated training instance after invalid boxes are removed. Test is required
  only by enabled consumers requesting it.
- **FR-006**: The system MUST create a deterministic, contiguous class-ID mapping from all
  nonempty class names in the CSV, preserve exact class meanings in both formats and the
  trained checkpoint, and retain the mapping with the run. Row order MUST NOT affect it.
- **FR-007**: Both commands MUST expose `dataset_format` with values `ndjson` and `flat`,
  defaulting to `ndjson` in CSV mode. Configuration examples and help MUST describe both.
- **FR-008**: NDJSON mode MUST produce the Ultralytics-compatible line-delimited dataset
  representation, including dataset class metadata and per-image split and annotation data.
  Generated dataset files MUST use the `.ndjson` extension; the tool-facing option is `ndjson`.
  Referenced local images MUST work without requiring remote image hosting.
- **FR-009**: Flat mode MUST produce a conventional native detection dataset descriptor,
  image collections, and corresponding per-image normalized YOLO labels for each split.
  Generated names MUST avoid collisions and remain traceable to original image identities.
- **FR-010**: Both formats MUST preserve every valid image and valid annotated instance, including
  background images. Reconstructing pixel corners from generated annotations MUST differ by
  no more than 0.01 pixel per coordinate from the validated input.
- **FR-011**: In CSV mode the generated dataset MUST override `ultralytics.data`, including
  stale explicit values and tracking-side dataset overrides. Data paths, split membership,
  and class metadata MUST come from the validated CSV. Other native controls that would
  filter images, collapse/filter classes, or replace this dataset MUST be overridden to
  preserve the full supplied data, or rejected with actionable guidance if that is unsafe.
  Every changed value MUST be visible in effective configuration and the override record.
- **FR-012**: Dataset preparation MUST preserve unrelated native settings, including device,
  batch, AMP, epochs, compilation, and augmentation, subject to existing stage/output rules.
  Prediction and comparison MUST retain original class meanings and requested CSV membership.
- **FR-013**: Prepared datasets and native conversion byproducts MUST live in the shared,
  CSV-addressed dataset cache outside run outputs. Cache entries MUST be isolated, atomically
  completed, locked while consumed and reusable across runs. Source CSVs, source images and
  existing labels MUST remain unchanged; pipeline `run_dir` and standalone outputs remain
  isolated from the cache.
- **FR-014**: Each run MUST retain locally the selected format, input fingerprint, resolved image
  inventory and split counts, input/retained/dropped annotation counts, invalid-box reasons,
  class mapping, generated dataset reference,
  and effective data overrides. The cleaned canonical ground-truth CSV MUST be the dataset
  performance artifact; generated dataset YAML MUST be a consumed dataset Configuration Object;
  data overrides MUST be stored in canonical run configuration. NDJSON, preparation records,
  labels and native YAML MUST remain local. Raw source dataset images MUST NOT be uploaded as
  artifacts; owner-only native training/validation previews MAY be published.
- **FR-015**: Preparation MUST share the invocation's single ClearML task with training and
  later stages; workers MUST NOT create tasks or upload artifacts. Completion MUST wait for
  required uploads and flushes. Preparation, computation, upload, flush, and interruption
  failures MUST fail the invocation while retaining local outputs.
- **FR-016**: Full-pipeline evaluation MUST calibrate on validation once, freeze thresholds
  for test, and compare baseline and candidate on identical current test images. Existing
  missing-automatic-baseline and invalid-explicit-baseline behavior MUST remain intact.
- **FR-017**: Standalone training MUST require `ground_truth`; `ultralytics.data` MUST be derived
  from CSV preparation and MUST NOT provide an alternate input path. `skip_train=true` MUST avoid
  training-dataset preparation and retain existing evaluation input requirements.
- **FR-018**: Generated command examples MUST make CSV training discoverable and distinguish
  dataset preparation controls from top-level native groups. No additional entrypoint is
  required, and `cy-ground-truth` MUST retain its existing dataset-to-CSV behavior.
- **FR-019**: Before native training, the command MUST display the total number of
  invalid boxes dropped across the supplied CSV, including zero when none are invalid.
  Count each dropped annotation row once, independently of its number of errors; valid
  background rows MUST NOT contribute. Both formats MUST use the same cleaning policy and
  counts. The run MUST retain a cleaned ground-truth representation and use it consistently
  for downstream evaluation, so dropped boxes cannot reappear in metrics or comparison.

### Key Entities *(include if feature involves data)*

- **Ground-truth source**: CSV and accessible referenced images; authoritative annotation,
  class-name, image-identity, and split information.
- **Validated image record**: Original identity, resolved path, dimensions, single split,
  and zero or more labeled boxes.
- **Class mapping**: Stable relationship between original class names and generated class IDs.
- **Prepared dataset**: Selected representation, generated files, image membership, and
  native training reference owned by one run.
- **Preparation record**: Input fingerprint, counts, class mapping, source-to-generated
  identity mapping, and original/effective data settings for inspection and replay.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user completes standalone training and the full supported pipeline from one
  annotation file and its referenced images, with zero manually prepared dataset descriptors,
  label files, or class lists; normal model and tracking settings remain available.
- **SC-002**: For both supported representations, 100% of valid images, valid annotated instances,
  background images, class meanings, and split assignments survive preparation; coordinate
  round trips meet the 0.01-pixel tolerance.
- **SC-003**: Reordering input rows yields identical class mappings and per-split membership,
  with zero images shared across training, validation, and test partitions.
- **SC-004**: In both formats, every invalid box is dropped exactly once and included in
  the displayed pre-training error-box total; valid boxes are retained and usable datasets
  proceed to training. Fatal structural/image errors and datasets with no valid training
  instances fail before training with an actionable reason. Evaluation uses the same
  cleaned annotations and no data loss is unreported.
- **SC-005**: Each format completes a real training run producing a usable checkpoint, and
  the corresponding full pipeline produces requested evaluation artifacts with one tracking
  task. Mocked execution alone does not establish this outcome.
- **SC-006**: In conflicting-configuration acceptance cases, all effective dataset references
  point to the prepared input and every override is recorded, while unrelated settings remain
  unchanged. Successful runs retain all required preparation and evaluation records.

## Assumptions

- "Only the ground truth file" means it is the sole dataset specification; image bytes must
  already be accessible through its paths. Normal execution prerequisites, model selection,
  and ClearML configuration still apply.
- Per the user's correction, invalid boxes are recoverable: drop them and show the total
  error-box count before training. Images whose boxes are all removed remain as background;
  the existing requirement for at least one valid training instance still applies.
- Scope is bounding-box object detection matching the current CSV contract. Segmentation,
  pose, oriented boxes, classification, remote-image retrieval, and automatic split generation
  are excluded from this feature.
- "Flat dataset" means conventional image/label collections per split, with no class-based
  nesting. File copying/linking strategy is a planning decision subject to input preservation
  and native compatibility.
- `dataset_format` is the proposed public tool parameter. Both representations ship together;
  NDJSON is the default rather than a fallback that requires separate installation or setup.
- The original feature retained standalone native-data training; the 2026-10-02 current-only
  amendment supersedes that decision and makes CSV ground truth authoritative for all training.
- Dependencies are the existing native training runtime, ClearML, and the established
  evaluation interfaces. No changes to the pinned `digital-metrics` dependency are authorized.
- Format terminology follows the official
  [Ultralytics detection dataset documentation](https://docs.ultralytics.com/datasets/detect/).
  Compatibility with the repository's locked runtime, including local-image NDJSON handling,
  must be established during planning and verified during implementation.
