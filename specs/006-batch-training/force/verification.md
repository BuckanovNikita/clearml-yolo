# Forced batch admission verification — 2026-11-03

The user requested forced GPU estimation and Git-only release after verification.
Work is isolated from the heavily modified original checkout, based on latest CY
`84166d5` (0.44.8) and queue `0139152` (0.1.7). Proposed CY patch is 0.44.9;
queue's current `<0.45` bound includes it. Approved external dependency source and
locked versions are preserved. Machine paths and raw telemetry remain private.

## Implemented behavior and focused evidence

Opt-in `--force` persists in search settings and cache keys, permits nonzero
utilization/unattributed activity at scheduling, preflight and optimizer/monitor
boundaries, and labels forced sources in measured/cached/extrapolated output.
Foreign compute PIDs, unavailable telemetry, hardware checks, memory envelopes,
finite computation, all optimizer paths and fresh confirmation remain enforced.
Existing inward layers, import rules and ownership are unchanged.

The bounded implementation agent reproduced six failing force regressions before
implementation. Its final focused run passed 286 estimator/GPU tests, 199 CLI
compatibility/catalog cases, strict mypy for nine owned modules/tests and Ruff.
The parent reviewed the complete diff, including the exact option fixture update.

## Parent checks

- Normal editable CY/queue resolution with locked constraints and approved external
  source copies succeeded; `uv pip check` passed with matching source/installed
  CY 0.44.8 and queue 0.1.7 metadata.
- Current queue integration: 582 passed, 7 intentionally deselected hardware cases;
  queue Ruff, strict mypy and both import contracts passed.
- CY documentation verifier passed, including the changed option help example.
- Initial canonical attempt passed Ruff/mypy/Vulture but could not start the
  import-linter console script in the isolated environment. The locked dev tools
  were installed into that environment; the canonical rerun is pending.
- Native forced catalogue search has passed actual batch-8 and batch-16 trials
  for its first model, with native updates/validation and memory telemetry. Search,
  fresh winner confirmation and the remaining model matrix are pending. These
  intermediate successes are not usable saved recommendations.

## Acceptance and release

Full native evidence, canonical completion, proposed/actual-version pairing, fresh
independent review, architecture acceptance and Git-only publication are pending.
The portable companion is prepared in its own isolated source checkout with
collection 0.7.2 metadata; its static/discovery/link checks passed. Final package
review/evaluation and publication are pending. No unavailable or running check is
reported as passing, and historical physical DDP limitations remain unchanged.

## Compatibility correction and proposed-version verification

The first full ordinary run completed with 4,709 passes and three frozen-key
compatibility failures. Those failures showed that serializing the new default
false force policy changed historical source keys. The key builder now omits that
implicit false field, preserving ordinary and frozen historical identities while
keeping true force searches distinct. All 240 focused estimator/legacy/GPU tests
passed after correction. The required full canonical rerun is pending.

Earlier GPU searches are preserved as pilot evidence, not relabelled as current
measurements. The final complete matrix runs from an isolated proposed-0.44.9
source fixture with matching project/lock/installed metadata and the exact reviewed
runtime tree. This makes its catalogue version-compatible with the intended
release. The actual Git repository's version remains owned by normal release hooks.
The proposed 0.44.9/queue 0.1.7 suite is running under normal locked resolution.
Only final native results and actual-version pairing can qualify delivery.

The selected mutation-policy modules, tests and dependencies are unchanged; the
force/cache behavior is covered by the failing regressions and focused checks.
The existing contract index still links the maintained batch guide, so its authority
and navigation need no separate change. Original unrelated working-tree edits and
local source overrides remain untouched.

## Headless verification rerun

The corrected-source full run exited 1 during the final reporting test in
`test_identity_flows.py`, without a Python traceback or pytest summary. There were
no kernel/cgroup OOM or PID-limit events. That whole 12-test file passed on its own,
and collecting the complete suite then selecting its final metrics/report test
also passed with native diagnostic output enabled. The failure is not reproduced.

Inspection showed the environment automatically selected TkAgg with a live display,
although these checks render PNG/workbook artifacts. The existing CPU-DDP launcher
already uses `MPLBACKEND=Agg`. A fresh complete canonical run now uses that same
headless backend and hides CUDA for ordinary tests. No dependency, assertion,
selection or application behavior was changed to conceal the failed run. Tk/X11
failure is a hypothesis, not a proven cause. Completion remains pending a full pass.

## Verification input isolation correction

The headless run completed all 4,712 ordinary tests successfully (30 optional skips,
81 standard deselections), but the verifier correctly refused a success receipt
because its input fingerprint changed. The temporary shared-site link used during
initial environment preparation still exposed a second CY 0.41.0 checkout and a
second queue 0.1.3 installation. Editable-dependency inventory therefore included
unrelated, actively used working trees. The exact changing file was not retained
by that failed aggregate fingerprint.

The task-owned transitional link was removed after all declared runtime/dev
packages had been normally installed in the isolated environment. `uv pip check`
passed, and distribution enumeration now shows exactly the intended CY 0.44.8
source and queue 0.1.7 source. A complete headless canonical run is pending with
that corrected inventory. The separate clean proposed-0.44.9 environment never
used the shared-site link; its native matrix and successful proposed pair remain
unchanged. No verifier rule was weakened and no failed receipt was reused.

## Historical integrated verification — 2026-11-04

Preserved work was reconciled onto CY `8be76e4` (0.45.0); original dirty trees,
their index states and local overrides remain preserved. The integrated source
passed the canonical verifier with **4,790 passed, 30 skipped, 81 deselected**,
including architecture negative cases and CPU-DDP. Ruff, strict mypy, Vulture and
import contracts passed with unchanged-input success receipt
`application-106ddd8c9333425a8182c6d398a2d77b`. Documentation validation passed.

The proposed **CY 0.46.0 / cy-queue 0.1.9** pair resolved normally and passed
**583 tests, seven physical cases deselected**, metadata/dependency checks,
Ruff, strict mypy, import contracts and command help. Before/after source
inventories remained identical. These proposed versions supersede earlier candidate
identities in this dated continuation; no historical measurements are relabeled.

Fresh independent reviewer `integrated_source_review` inspected all 45 task-owned
changed/untracked files against the frozen pre-review inventory and returned SHIP
for source/architecture scope. Separate force, campaign and HF changes retain
individual records and native acceptance gates.

Portable skill source was reconciled against collection 0.7.3; static, link,
discovery, routing/example evaluation and fresh independent review passed. Its
force/HF guidance is explicitly unreleased. Publication remains separate.

Force propagation, legacy false-key compatibility, foreign-PID and telemetry
rejection, provenance and list-mode rejection were accepted by that review.
The full 64-model forced native matrix and final delivery remain pending.
The matched search benchmark is forced/background-sensitive; timings and trial
counts do not establish idle-device or statistical speedup. Physical multi-GPU
acceptance remains unavailable on this single-GPU host.

This 0.45.0-based closure checkpoint is retained history. Its proposed 0.46.0
identity was never released, and its acceptance is superseded by the sequential
current-master port below.

## Sequential current-master force port — 2026-11-05

This force-owned source port starts from master `66279a6` (0.45.1) after the
DINOv3 source fix and scoped campaign improvements. The existing feature006
follow-up remains the native ledger. Its five-item requirements checklist is
complete; extension hooks are empty. Read-only prerequisite path resolution
and direct required-artifact inspection avoided the helper's normal
`.specify/feature.json` persistence; installed workflow tooling was not edited.

The reconciled architecture plan passed before runtime edits. The port then
copied the force regression and ran it against the pre-force implementation:
`test_force_settings_are_strict_persisted_and_have_distinct_cache_keys` failed
with `AttributeError: SearchSettings has no attribute force` (one test, exit1).
The five source modules were then ported byte-for-byte from the preserved force
worktree. `git apply --check` passed; the current DINOv3/campaign implementation,
master training-outcome changes, import rules, source versions and dependency pins
were retained. Only the twenty force-owned paths were changed by this port.

Current CPU-only checks used `CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2
MPLBACKEND=Agg uv run --frozen --no-sync` and the prepared environment:

- `python -m pytest -q tests/test_batch_estimation.py
  tests/test_batch_estimate_cli.py tests/test_batch_estimate_list.py
  tests/test_batch_probe.py tests/test_gpu_inventory.py
  tests/test_docs_compatibility.py`: exit0, **424 passed**, 19 upstream
  hydra-zen/Pydantic deprecation warnings. These synthetic GPU/worker tests
  establish force propagation, strict defaults, retained foreign-PID/telemetry
  checks, baseline memory accounting, cache labeling and inert list behavior.
- `python -m pytest -q tests/test_batch_search_strategy.py
  tests/test_batch_resolution.py`: exit0, **38 passed**, including frozen
  historical keys, read-only historical bytes and source resolution provenance.
- `ruff check` on the five source and six Python test files: exit0.
- `mypy` on those eleven source/test files: exit0, no issues.
- `python scripts/check_docs.py` on README, the batch guide, feature plan/spec/tasks
  and the two force evidence Markdown files: exit0, seven documents, zero issues.
- `git diff --check`: exit0.

Task-owned raw outputs are retained outside the repository in the parent's
`cy-sequential-20261105-evidence` directory as `force-baseline.log`,
`force-focused.log`, `force-legacy-regressions.log` and `force-mypy.log`.
No native GPU work, installation, metadata/version change, commit, tag or push
was performed by this bounded port. Focused tests do not establish real native
capacity, uncontended GPU availability or final-source catalogue acceptance.

### Remaining integrated gates

The user declared the small unattributed background activity idle. The planned
explicit force option supplies that override; it does not waive the default idle
rule or identify the activity as graphics-only. Forced results must retain their
background-sensitive label and explicit foreign-compute protection.

Parent acceptance remains pending: complete integrated canonical/architecture
negatives and CPU-DDP; full docs and portable usage reconciliation; normal latest
and proposed CY0.46.0/compatible queue source/installed pairing; all64 final-source
native models with raw optimizer receipts and fresh confirmation, including
selected DEIM L/X HF initialization; fresh integrated independent review;
architecture acceptance; and normal Git-only release/final metadata checks.
The retained nineteen historical cases (thirteen validated, six failed) are not
complete coverage and are not current-source acceptance. Existing physical
multi-GPU limits remain unverified. The original full campaign recovery, numerical
failures and SIGILL investigation are outside this scoped force port.

## Frozen final candidate preparation

Current source is integrated in the requested DINOv3 → scoped campaign → force
order, based on master `66279a6`. A hash-bound copied candidate changes only
the root project and root lock versions to the proposed CY 0.46.0; application
source remains byte-identical. Latest queue `694c12f9` is adapted minimally to
0.1.9 with the verified `<0.47` bound, leaving runtime protocols unchanged.

Normal paired resolution and installation passed. Source/installed versions and
paths match; dependency checking, all 583 queue tests (7 physical opt-ins
deselected), Ruff/format, strict mypy, import contracts, help and 35-document
checks passed. The copied environment is frozen before native measurements.
The earlier CY 0.45.2 candidate pair remains historical; it is not the final
release pair. Actual post-hook metadata and source identity still need rechecking.

All 64 native inputs were normally resolved and validated on the final candidate,
including 44 native YOLO cached files and all 20 non-YOLO selections. The missing
ResNet101 checkpoint was restored through normal pinned resolution. Explicit
model weight/backbone overrides and dependency pin changes were not used.
This is input readiness, not measured capacity or full native acceptance.

Final integrated canonical verification and six proposed-version DINOv3 native
training/publication/readback cases are running. Selected L/X forced optimizer
trials and the complete 64-model forced catalogue remain pending. Force results
will be labeled background-sensitive, preserving foreign-PID/numeric-telemetry
checks, whole-device memory accounting and fresh winner confirmation.

## Final integrated verification checkpoint

The complete final-source canonical command exited 0 with a successful
unchanged-input receipt: Ruff, strict mypy, Vulture, import contracts and
4,844 ordinary tests passed; 30 tests were skipped and 81 opt-ins deselected.
The frozen proposed CY 0.46.0 / queue 0.1.9 pair passed normal resolution,
matching source/installed metadata, all 583 queue tests (7 hardware opt-ins
deselected), static/import/help and documentation checks.

All six DINOv3 default/JSON/mosaic L/X native cases also passed on that
proposed-version final source: 160 optimizer updates each, changed parameters,
80 evaluated images and downloaded/reloaded checkpoints. The remote audit
verified all six pinned derivations, derived hashes and canonical null selectors.
The command exited 0 with verified descendant exit and reservation release.
Raw case trees were retained as `final-native-archive`, and tag-scoped stand
cleanup verified zero remaining owned projects/tasks. These results remain
separate from the still-pending forced selected L/X and full64 estimator gates.

Fresh reviewer `review_integrated_source` found no blocking source or architecture
issues in the complete integrated CY and queue compatibility diffs. This is
source clearance, not final release acceptance. Final native catalogue audits,
architecture acceptance, actual delivered-version metadata and fresh final
review remain required before any commit/tag/push delivery.

## Explicit user cancellation

The user requested termination of the GPU task. Scheduled task 6 exited 130
during selected L/X measurement; the catalogue continuation did not run. The
owned service exited, its cgroup was removed and GPU reservation release was
verified. A task-owned stop marker prevents automatic restart. This is operator
cancellation, not a source regression or successful native acceptance. Existing
source, completed verification evidence and partial raw trial receipts are retained.
Selected/64-model estimator gates and release remain incomplete.

## Ordinary-record compatibility fix — 2026-11-06

Fresh consolidation review found that `FileBatchEstimateStore.save` rewrote every
case with `settings.force: false`. CY 0.45 and earlier readers forbid unknown
fields, so one ordinary run under the force source would make a shared catalogue
unreadable to them. `SearchSettings` now omits the default false policy when it
serializes; forced settings still persist `force: true`. Estimate keys are
unchanged, because the key builder previously removed the same field.

The new regression `test_ordinary_settings_stay_readable_by_pre_force_strict_readers`
failed against the sequential source before the fix: 1 failed. After the fix the
focused batch estimation, CLI, listing, resolution and search-strategy suites passed
201 tests, and scoped Ruff, format and strict mypy passed. Canonical results are
recorded in the
[consolidation verification](../../../docs/plans/unfinished-work-cleanup-20261106/verification.md).
Native gates listed above are unchanged.

## WP2a integrated source review — 2026-11-07

Scope: `git diff v0.45.1 v0.46.0 -- src tests`, forced admission and the persisted
`settings.force` policy, including the ordinary-record omission fix. Lens: forced
admission, followed by a skeptic pass.

Checked: `SearchSettings.force` is a `StrictBool` omitted only when false; ordinary
estimate keys equal v0.45.1 keys and forced keys differ. Force reaches scheduling,
preflight, the serialized worker request and the monitor. It relaxes only the
zero-utilization rule and unattributed activity; unavailable telemetry, preflight
PIDs, foreign PIDs and invalid telemetry still raise. Temporary tests loaded the real
v0.45.1 `core/batch_estimation.py` and showed that ordinary catalogues written now
validate under the v0.45.1 strict reader, v0.45.1 catalogues read as `force=False`,
and v0.45.1 rejects forced catalogues as documented. Training may select a forced
estimate: [plan.md](../plan.md) line 203 and `docs/batch-estimation.md` allow it,
`select_estimate` picks the smallest compatible batch and provenance keeps
`force: true`. Temporary probes (15 tests) and 282 focused tests passed. The temporary
tests were not kept.

Findings: none. Nonblocking: `--list` counts a usable forced estimate as covered
without the forced label; the documentation promises the label for recommendations,
not coverage lists.

Verdict: no change required within the stated scope. Limits: CPU only; native GPU
and real `nvidia-smi` telemetry were not exercised. The review brief named the
constitution and `docs/project-contracts.md`; the lens report does not confirm
reading them. Native forced-estimator acceptance (WP1) remains open.
