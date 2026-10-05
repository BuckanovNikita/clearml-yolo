# Review remediation evidence — 2026-10-04

The authorized remediation covers all 14 YOLO findings from the October 3 review, based on
`4c0e627`. Historical bulky reproduction files are intentionally uncommitted; each finding has
self-contained assessment, fix and verification records under `.specify/bugs/<slug>/`.
Dependency pins and external source are unchanged.

| Finding | Implementation | Change | Evidence limits |
|---|---|---|---|
| `clearml-failure-self-abort` | implemented | Close before fresh-handle failure transition; preserve original exception when cleanup fails. | Live upload/flush/SIGTERM regression passed by parent; SDK close failure cannot guarantee terminal remote status. |
| `split-output-traversal` | implemented | Percent-encode logical split components for filenames, native routes and artifacts; retain manifest identities. | Actual metrics/report producers exercised with traversal-shaped split; no full native arbitrary-split pipeline required. |
| `gpu-telemetry-lock-stall` | implemented | Move telemetry outside registry lock and reread live validated state before admission/contraction. | Event-blocked fake telemetry reproduced lock stall; real NVML hang not induced. Probing caller may still wait for driver. |
| `baseline-tags-use-or` | implemented | Use SDK __$all for multiple ordinary required tags. | Live conjunction and whole-name lookup passed. |
| `baseline-regex-anchoring` | implemented | Group pattern within absolute whole-name anchors. | Alternation, partial names and trailing newline covered. |
| `evaluation-options-not-validated` | implemented | Constrain matching/AP modes and finite IoU probability at config and reusable scoring boundaries. | Valid existing modes preserved; upstream dependency unchanged. |
| `comparison-invalid-q` | implemented | Validate finite inclusive [0,1] q at command, BH and verdict boundaries. | Invalid values rejected before significance decisions. |
| `ground-truth-exif-dimensions` | implemented | Use installed Ultralytics exif_size without mutating images. | Real non-square JPEG orientations 6/8 and unchanged bytes checked. |
| `ground-truth-invalid-coordinates` | implemented | Reject nonfinite/out-of-native-tolerance labels with file/line diagnostic; retain edge clipping. | NaN, infinity, negative/out-of-range centers and sizes covered. |
| `fiftyone-config-blocks-cli` | implemented | Warn/fall back on malformed, non-mapping or unreadable optional configuration. | Installed CLI help/export passed with malformed config; enabled publisher keeps optional no-op boundary. |
| `gpu-partial-reservation-state` | implemented | Accept full allocation or one-device contraction only. | Corrupt intermediate state is rejected before reconciliation. |
| `local-rank-owner-ambiguity` | implemented | Reject ownerless rank launch early; require PID and task owner provenance for descendants. | External torchrun rank launch explicitly unsupported. |
| `signed-url-signatures-not-redacted` | implemented | Recognize provider signature keys consistently for snapshots and secret collection. | Synthetic credentials only; executable mapping is unchanged. |
| `empty-settings-break-replay` | implemented | Preserve empty executable replay shapes and native groups; prune optional results separately. | Fake SDK round trip exercises real adapter; separate remote replay was not run. |

## Checks

- Initial imports (`clearml_yolo`, `digital_metrics`, `report_generator`) succeeded.
- Initial session/queue checks: 85 passed.
- Test-first reproduction: 32 expected failures, 95 passes; separate stalled telemetry lock regression failed by timeout.
- Initial fixed focused run: 149 passed.
- `ruff check src tests`: passed.
- `mypy .`: passed (110 source files).
- `lint-imports`: 9 contracts kept, none broken.
- Final generic regression set: 33 passed, including valid significance endpoints and native coordinate tolerance.
- Final affected regression set (`test_ground_truth`, `test_metrics`, `test_gpu_queue`, `test_review_regressions`, `test_comparison_scoring`): 99 passed.
- Local cleanup OSError exception precedence: 2 passed after reproducing masking in a failing test.
- SDK failure-boundary fixture regression: 1 passed; fake task now covers fresh-handle lookup.
- Both legacy and suffixed dashboard confidence plots: 2 passed. The integration adapter accepts either format and fails when neither exists.
- Changed Markdown parsed with markdown-it; whitespace/local-link validation: 49 files, no errors.
- `git diff --check`: passed.
- Implementer full suite was cancelled at parent request after 329 passes; the new fresh-handle failure cleanup exposed a missing test fake and real network retries. The fixture was fixed and its regression passed. Parent reruns complete pinned and combined suites.

Parent acceptance includes live required-upload rejection, flush rejection and SIGTERM: original
exceptions retained, remote tasks failed, cleanup reached. This evidence is maintained by the
parent's final acceptance report. Physical NVML hangs and Windows execution remain unverified.

## Documentation scope

Updated maintained CLI/evaluation, training conversion, optional publisher, SDK tracking,
GPU queue and launch contracts. The current contract index remains authoritative and unchanged.
README commands and dependency pin instructions are unchanged. No installed workflow tooling or
skills were changed. Verification distinguishes fake SDK/telemetry tests from live/native runs.

## Combined dependency compatibility

Candidate digital-metrics writes split-suffixed confidence plots. The YOLO adapter accepts those
outputs directly and still supports legacy pinned unsuffixed plots. Combined tests also use valid
all-null background annotations instead of missing labels with box coordinates. Normal report
acceptance uses a fresh destination and retains default overwrite protection. No dependency source
or committed pin was changed to achieve compatibility.

## Independent review followup: fresh confidence plots

The first dual-format adapter could reuse an older split-suffixed confidence plot when the
legacy producer wrote a fresh unsuffixed plot into a reused destination. Three test-first
regressions reproduced stale reuse or acceptance of missing fresh output across both naming
conventions. Before dashboard generation, the adapter now removes only the four metrics' known
unsuffixed and current-split confidence plot outputs. It then requires fresh output in one of the
two supported formats. Other splits and unrelated destination files remain intact.

The complete metrics, comparison-assembly and session modules passed 136 tests. Ruff and mypy
passed, all nine import contracts remained intact, and both changed Markdown files passed parsing,
whitespace and local-link checks. This correction keeps
committed dependency pins and normal report overwrite protection unchanged.

## Parent acceptance

See [final verification evidence](verification-20261004.md) for pinned/candidate full suites,
real CPU and single-GPU execution, downloaded artifacts, failure-path checks and cleanup.

## PCRE boundary followup

Independent review identified that MongoDB's PCRE permits a terminal newline before `\Z`,
unlike Python's regex engine. A PCRE whole-record oracle reproduced the remaining failure
(one failed, three passed). The expression now adds a portable strict-end negative lookahead,
rejecting terminal-newline names in both engines while preserving deliberate regex patterns.
