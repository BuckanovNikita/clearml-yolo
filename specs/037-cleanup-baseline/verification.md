# Integrated maintenance verification — 2026-10-20

Integration began on `master` at `129b94b749d7d4bcaf6e82b9a504a141796c7bdc`,
with the user-authorized configuration split and feature 036 changes uncommitted.
Their original task records retain their own acceptance history. A separate initial
working-tree snapshot preserved all tracked changes and untracked additions before
this task. No dependency source, approved revision or installed workflow tool changed.

## Cleanup decisions

| Candidate | Evidence and disposition | Preserved boundary |
| --- | --- | --- |
| `concrete_device_selector`, `validate_concrete_phases`, `configured_phases`, `wait_process` | Removed after caller/config/test search and inspection of the direct-execution replacement in `31a5bd5edc2fe122791005526ae747e7fe5b0401` | Active GPU demand/probing, process-tree supervision and cancellation remain |
| `LocalGPULocks.transaction_recovery`, `_take_recovery_locks` | Removed after confirming their sole recovery caller was retired by generation-fenced free in `dcbbc4903cec07c67ce50cd9b116ea3f6dab8216` | Current generation-aware leases and active recovery/cancellation remain |
| `REPORT_SECTION`, `_assert_native_audit_artifacts` | Removed after tracing publication replacement in `589dc4a563e8a767a3cf9b675df66820b0a3c83b` and finding no remaining consumer | Current result inventory and observable publication assertions remain |
| SDK/Hydra/Textual/Pydantic hooks and fields; public queue methods | Retained: dynamic or external consumers invalidate a zero-text-reference deletion argument | Existing dynamic targets, callbacks and public-looking interfaces remain |
| CI optimization | No change: no representative CI duration/failure evidence supports a claim | No checks removed or timing improvement claimed |

The two executable fixtures were copied unchanged before their historical originals
are retired. Their SHA-256 values and consumer paths are recorded in the baseline.
No scientific expectation was regenerated. Architecture checks still reject injected
forbidden imports and effects; their scope was not weakened for history removal.

## Executed checks

- `uv run --frozen --no-sync ruff check .`: passed.
- `uv run --frozen --no-sync mypy .`: passed, 349 source files.
- `uv run --frozen --no-sync vulture`: passed.
- `uv run --frozen --no-sync lint-imports`: passed, all 43 contracts kept.
- `uv run --frozen --no-sync pytest tests/test_architecture.py`: 242 passed.
- Full `uv run --frozen --no-sync pytest`: 3263 passed, 30 skipped, seven deselected,
  133 warnings in 1033.77 seconds. Skips/deselections are not passed native outcomes.
- `uv run --frozen --no-sync python scripts/check_docs.py --all`: 509 tracked
  Markdown files, zero issues after repairing the pre-existing missing Setup anchor.
  The baseline and all nine initial task Markdown files also passed explicit checks.
- Architecture plan validation: passed before implementation. All three integrated architecture records passed acceptance validation after the
  fresh integrated review returned ship; see [review](review.md).

## Installed-package checks

Built both wheel and sdist from a frozen task source copy, removing local uv sources
only from that copy. The build retained the then-current package version `0.34.1`;
these are source acceptance checks, not a claim that the new source was released.
Separate isolated environments passed dependency consistency and installed-package
verification. The sdist environment included the existing `queue-ui` extra.

Each distribution passed inert root imports, 184 source-file hash comparisons,
12 console help probes, nine default configurations, 81 selected configurations,
nine shipped callable targets, overwrite protection, evaluation-mode checks and
two queue snapshots. Source-manifest SHA-256:
`8d9208dd09e505d37025d4035f02a4a01e139e0c15df058f4e494b05cea21a94`.
These checks establish installed behavior on Python 3.12.13; they do not add a new
Python 3.13, physical multi-GPU, NFS or deployment certification.

## Live acceptance and companion skills

Feature 036's dedicated live record owns actual CPU/single-GPU publication and the
controller miss/hit/scientific-change checks. Both completed remote reruns passed
without changing runtime source after an initial intermittent native-model
enrichment failure. Preserve that failure and its unknown cause; passing reruns
do not establish a fix. This is tiny random-weight execution/publication evidence,
not a model-accuracy evaluation.

The personal `cleanup-code` skill was independently evaluated, released at
`agent-skills` commit `9cea557d73b428ad014129f2ac5fe47a4cd2642a`, tag `v0.7.0`,
and installed through its recorded source for Codex and the shared Claude skill
directory. Six installed files match released bytes; aggregate SHA-256:
`fb8a042ee0172da76513bcd0fc53128d2259b672d93445b22426a76c5738a101`.
Offline skill-repository checks passed (102 tests), as did schema, links, archive
hashes, shell checks and independent forward review. Fresh automatic host activation
was not tested. No other skill was installed or reconfigured.

The portable usage collection's published v0.2.10 already includes feature 036
guidance. This task prepares only its three current-contract link replacements in
an isolated checkout, preserving concurrent unrelated authoring changes. Companion
delivery follows application cutover.

## Preservation and remaining delivery

The [history map](history-map.json) resolves current contracts by topic and retains
precise old paths for immutable evidence links. Its fingerprints must be refreshed
after all active records are final and before checkpoint H. The subsequent cutover
must prove archived-byte coverage, fixture identity, retained tooling, local pointer
reset and next feature `001`. Final cutover evidence belongs in the single baseline.
No retired file has been deleted at this record update.

## Baseline review reconciliation

Fresh read-only reviewer `baseline_review` identified two P2 omissions: exact calibration
metadata keys/types and confusion-chart default/visibility/scale/hover requirements.
Both were restored and independently rechecked. The reviewer accepted the draft
conditionally on the planned H/inventory/cutover checks. This was a risk-based review,
not an exhaustive new verification of every historical outcome.

Subsequent integrated-review corrections changed documentation only. Every runtime
source in the installed-package manifest still matches the verified snapshot.

## Delivery preflight discovery

The initial commit attempt was interrupted before commit creation when the remote
preflight found five published commits ahead, ending at
`41a4036666b2225a4e3029e1695499cf914a5f59` with v0.35.0. Its completed static
hooks passed; its interrupted pytest hook is not a passing check. The exact local
uv.sources section was restored. The prior completed 3263-test suite still describes
the pre-merge source only. Reconciliation and new acceptance are explicit remaining
tasks; no remote changes or tags will be overwritten.

## Normal published-history integration

The local preservation checkpoint `a7d681503381d70eed645efa267726cc9e2ae21b`
passed every normal pre-commit gate, including the full pytest hook. Published
`41a4036666b2225a4e3029e1695499cf914a5f59` is merged normally without rewriting
commits or tags. Twenty conflicts were resolved against inspected source: each
conflicting runtime/test file's local version equalled feature036 at `2e4b5f2`,
so the newer published version preserves both scientific/cache and publication
work. The resulting runtime delta from the published tip is exactly the five
previously reviewed orphan-removal files. The test delta retains fixture moves,
the equivalent import-contract reader and removed unused assertion helper.

Published early-publication contracts and all twelve feature037 artifacts are
included. Both feature036 native evidence chains remain in the combined record;
early-publication's actual scheduler gate remains not-run and is not covered by
the historical waiver. Post-merge checks and independent review follow below.

The personal skill refinement is released at
`7f635ce123332d5444f294909c6a753dea7d268e`, tag `v0.7.2`. It adds observed lessons
on available upstream reconciliation and exact contract/procedure retention.
Fresh independent review returned ship; 102 offline tests and package checks
passed. All six installed files match released source (aggregate SHA-256
`b29f125071b8969ad646d61751f21dbf949d186cbc2999a2c24a6bf54763fb4e`). Only
cleanup-code was updated; previous bytes and lock metadata were backed up, and
unrelated lock entries and shared Claude link were unchanged. Host activation
and empirical behavior improvement remain untested.

The first merged hook exposed `PLR0904` on the published `TrackingSession` port
(23 methods versus the preview threshold of 20). Upstream did not enable that
preview rule; the local configuration split does. The attempt was interrupted
during pytest, before commit creation; its partial test run is not a pass. A
class-specific, documented `noqa: PLR0904` preserves the published cohesive
invocation lifecycle without changing interfaces or a runtime statement. Ruff
then passed. Import/effect rules and the method-count rule elsewhere remain active.
The retry runs normal hooks without bypass.

## Post-merge parent verification

Normal merge commit `9fc0b50db12437ec669daa4ae543c3e7ca1c761f` has parents
`a7d681503381d70eed645efa267726cc9e2ae21b` and
`41a4036666b2225a4e3029e1695499cf914a5f59`. Its normal commit hook passed Ruff,
mypy, all import contracts, Vulture and the full pytest suite. The successful
hook does not print pytest counts; no count is inferred. The separate integrated
architecture suite passed 246 tests (five warnings) in 3.49 seconds.

Both rebuilt wheel and sdist passed installed checks against the final integrated
source: 184 package-file hashes, 12 console help probes, nine default and 81 selected
configurations, nine shipped callables, overwrite/mode checks and two queue snapshots
per distribution. The source-manifest SHA-256 is
`b26afdab1d9620f627d583be6af7980ea3df9158f815689a919838da616d831f`; structured
results supplement the earlier snapshot in [packaging.json](packaging.json).
Python is 3.12.13, dependencies were reused, and only the sdist environment includes
the queue UI extra. These are installed-source checks, not new target certification.

All 43 extracted import contracts are semantically identical to the published
configuration. Package/dependency/other-tool metadata and the entire lockfile equal
the published version. The lint annotation preserves TrackingSession's complete AST.
The runtime delta otherwise remains the five evidenced orphan-removal files; no
new executed behavior or native boundary was introduced by conflict resolution.
Native evidence remains the two dated chains; no new scheduler, physical multi-GPU,
NFS, export-runtime or unexplained-enrichment-failure resolution is claimed.

Fresh read-only `merged_baseline_review` returned ship for the documentation delta:
new contracts match source; all twelve early-publication artifacts and new map
fingerprints match the published commit; prior exact metadata, visualization and
FiftyOne instructions remain intact; both evidence chains and the missing scheduler
acceptance stay distinct. Final integrated source review and archival cutover follow.

Final independent integrated review returned ship after the duplicate-link helper
correction; see [review](review.md#final-merged-source-review-2026-10-20).
Private native proof is retained at agent-skills commit
`1ab7da0b6448971a0abb44b5ec8380304714cfbc`, tag `v0.7.1`, under
`skills/clearml-yolo-environment/references/cache-cleanup-2026-10-20/`.
The 40-entry checksum manifest hashes to
`31cfb3b908497acd566e4815fa9dba900297b282a56cf0ecfb763989e0aa370c`.
This ordinary private Git archive preserves raw observations independently of
temporary workspaces; no environment skill installation was performed.
