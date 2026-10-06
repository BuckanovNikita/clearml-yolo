# README quickstart verification — 2026-10-06

## Scope and workflow

Implemented the user-approved Russian quickstart plan. README now centers one cy
invocation, the YOLO-to-CSV transition, results, a diagram and table-only comparison
with manual Ultralytics/digital-metrics/report-generator orchestration. Other commands
have short descriptions. The requested simplified style is an editorial preference,
not a claim of formal ASD-STE100 compliance.

Spec Kit requirements, plan and tasks were checked before implementation: FR-001
through FR-006 have task coverage, no unresolved clarifications or constitution
conflicts. Extension hooks are empty. Installed workflow files and active feature
state were not changed; only read-only prerequisite path discovery was used.

## Documentation reconciliation

- Updated README.md and docs/development.md setup and release navigation.
- Corrected installation/contributor references in the 001 and 003 quickstarts.
- Moved the working FiftyOne viewing snippet into the 006 quickstart, removing a
  circular reference to the shortened README.
- Reviewed docs/current-contracts.md and the native configuration, input, evaluation,
  publication, filesystem, GPU and release contracts. Their authority and behavior
  are unchanged, so no contract amendments were needed.

## Checks performed

- Parsed 13 changed/new Markdown documents with markdown-it, including final evidence
  and the generated changelog; checked 23 local links
  and fragments, plus inbound README fragments throughout docs/ and specs/.
- Checked syntax of 16 Bash blocks using `bash -n` and the moved Python snippet
  using `ast.parse`.
- Parsed the README TOML source block together with committed project metadata;
  both editable source paths match uv.lock and initialized pinned submodules.
- Generated command/native YAML with `uv run --locked --no-sync cy-init-config`
  into a task-owned temporary directory and filled the mandatory input for validation.
- Ran five CLI scenarios with `uv run --locked --no-sync ... --cfg job --resolve`:
  ground-truth conversion, main GPU example, generated YAML example, both devices on
  CPU, and additional prediction/baseline/output/FiftyOne overrides. All resolved
  without missing mandatory values; CPU device selection and image-size inheritance
  were checked explicitly.
- markdownlint-cli2 0.23.3 reported zero issues across the 12 authored documents
  (the generated changelog retains its generator's formatting). MD013 (line length) and MD060 (table
  column alignment) were disabled for prose/table formatting; all other defaults ran.
- Mermaid parsed and rendered the diagram in a headless Chromium browser; all ten
  nodes rendered. Parent visually inspected the result.
- `git diff --check` passed. The pre-existing pyproject.toml source overrides remain
  unchanged; runtime code, uv.lock and submodule revisions were not changed.

## Independent review

A read-only investigation confirmed installation and migration facts against source.
A separate fresh-context final review returned **ship**, with no actionable findings.
It independently checked the final diff and matched installation, defaults, dataset
conversion, baseline selection, task ownership, outputs and GPU behavior to source.

## Limits

These checks validate documentation and configuration composition. They do not prove
a fresh-machine dependency installation, data availability, training, GPU execution,
FiftyOne publication or ClearML uploads. No application test suite or live pipeline
was required for this documentation-only change. Temporary tools and configuration
outputs are task-owned and will be removed after verification.

## Follow-up: CSV-first onboarding, Russian prose and automatic devices

The user corrected the first revision: onboarding must accept an existing CSV through
`ground_truth`, without requiring YOLO YAML conversion. README and its diagram now
start from CSV/images; the converter is listed only as an optional auxiliary command.
The comparison table still identifies native Ultralytics `data=data.yaml` as the old
interface, not a wrapper prerequisite. Russian prose now uses direct instructions,
familiar terms and fewer formal/redundant phrases.

Further user steering removed hardware/GPU setup and manual-index advice. Wrapper
examples use `-1`; native DDP requests use `[-1,-1]`. The queue section explains FIFO,
atomic admission, delayed ClearML task creation and releasing all but one device after
training. It does not claim that the runtime rejects physical-index syntax.

The requested source-overrides block was removed from README. Installation now uses
`uv sync --frozen` and examples use `uv run --frozen`, retaining the committed lockfile
without requiring a pyproject edit. Related development/001 setup references were
reconciled. The user's pre-existing local source overrides remain untouched.

Follow-up checks:

- In a task-owned temporary layout, committed pyproject.toml (without sources), the
  unchanged lockfile and pinned dependency paths passed `uv sync --frozen --dry-run`.
  This checks install planning; packages were not installed or downloaded by sync.
- Six changed Markdown files parsed; 21 local links/anchors and Bash block syntax
  passed. README assertions verify CSV-first onboarding, no source block and no
  hardware/physical-index examples.
- The main command and DDP variant resolved with `uv run --frozen --no-sync cy ...
  --cfg job --resolve`. Scheduler demand and normalization verified one and two
  automatic device requests respectively; inference remained `-1` in both cases.
- Mermaid parsed and rendered all nine nodes in Chromium, with CSV as the starting
  input. markdownlint reported zero issues with the same formatting exclusions as
  above; `git diff --check` passed.
- Final independent editorial/technical review returned **ship**, with no blocking
  findings. It confirmed natural Russian phrasing, CSV-first onboarding, automatic
  device examples, queue semantics and frozen-lock setup. No live DDP, queue,
  training or ClearML execution is claimed by these documentation checks.

## Follow-up: baseline re-inference and FiftyOne note

Added an explicit README explanation and comparison-table entry for re-running the
old model on the current ground-truth test data, recomputing metrics and retaining
saved weights/frozen thresholds. Replaced FiftyOne on/off guidance with a short
description of image, annotation, prediction and error inspection using the shared
digital-metrics results. The existing viewing-guide link remains.

Checked the prose against tasks/compare.py, comparison/reinfer.py and the maintained
FiftyOne publication/evaluation guidance. Markdown parsing, existing link/anchor
resolution, fence/whitespace checks and `git diff --check` passed. Commands and the
diagram are unchanged, so configuration, rendering and native execution checks were
not repeated. Initial independent review identified two overstatements: inference
can reuse a cache on same-directory retries, and FiftyOne subset reports differ from
full-split reports. README now scopes re-inference to new experiments, documents
same-input/settings reuse with recomputed metrics, and qualifies parity to full splits.
A fresh final independent review returned **ship**, confirming the corrected baseline
inference/cache wording and full-split FiftyOne parity, with no remaining findings.

## Follow-up: assume setup is complete

The user progressively removed clone instructions, ClearML initialization, then all
general setup material. README now begins directly with data input and installed cy
commands. Removed installation/environment prerequisites, setup troubleshooting and
contributor navigation; retained cy-specific parameters/results, migration, DDP/queue
and FiftyOne guidance. Updated development/001 references to avoid the removed README
installation anchor. Early bounded removal reviews passed; a fresh final review of
the combined change returned **ship** with no findings. No runtime behavior or
dependency revisions changed.

The final user addition provides `cy-init-config cy-config`, native training and
prediction snippets for the respective generated group files, main input/tracking
instructions and `cy --config-dir cy-config --config-name cy`.

Validation generated cy-config in a task-owned temporary directory, applied the exact
documented YAML snippets while preserving other settings, filled the CSV/tracking
fields, then composed the exact launch command with `--cfg job --resolve`. Confirmed
model, epochs, independent batches 16/8, inherited image size 640, prediction confidence
0.001 and automatic devices -1. The direct main cy command also resolved. Eight changed
Markdown files and 19 local links/anchors passed, along with Bash/YAML syntax and
`git diff --check`; no inbound links retain the removed installation anchor. No live
training, ClearML or visualization execution was performed. Temporary outputs are
removed after checks.
