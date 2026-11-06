# Integrated source review — 2026-11-04

Fresh independent reviewers `hf_conversion_review` and `integrated_source_review`
reviewed the final integrated source after canonical verification. Both returned
SHIP within the source/architecture and recorded native scope, with no blocking
findings. This dated record summarizes their returned review evidence.

The HF review checked exact Q/K/V and standard/gated MLP mappings, complete source
consumption, nonlearned native state, pinned source integrity, authenticated Hub
resolution, cache corruption checks, locked atomic publication, CPU RNG isolation,
explicit override precedence, canonical configuration and provenance. It inspected
the CPU tensor/feature evidence and all six production-fallback native receipts.
The declared parity tolerance is 1e-3; stricter diagnostics remain disclosed.

The integrated review compared all 45 task-owned changed/untracked files with
the frozen pre-review inventory. It covered the shared force/campaign/HF diff,
exact dependency exceptions, inert imports, effect ownership and executable
architecture contracts. The 4,790-test canonical run, documentation checks and
583-test proposed queue pair were inspected. Original dirty trees were excluded
and preserved. This bug's scoped files match the architecture record; the related
force and campaign changes retain their own records and acceptance checks.

The full estimator matrix, final acceptance-record reconciliation, campaign
recovery and physical multi-GPU acceptance remain separate gates. A source review
does not waive missing native evidence or authorize a release claim.

## Isolated current-master review — 2026-11-05

Pending fresh review after parent verification. Earlier SHIP verdicts apply to the
recorded combined source only; they do not accept this new isolated integration.

### Current DINO-only source review outcome

Fresh read-only reviewer `dinov3_final_source_review` returned SHIP for scoped
source and architecture after parent integration and verification, with no
blocking source findings. It inspected complete tracked/untracked source and
tests, exact import exceptions, canonical evidence, CPU conversion/feature
criteria, six native optimizer and provenance receipts, cleanup and proposed
queue pairing. Its nonblocking documentation reconciliation is appended in
[test.md](test.md): the failed ordinary admission remains historical; selected
forced measurements are deferred to final integration following user direction.

This source verdict does not grant final acceptance or release. Final integrated
source/version checks, selected forced winner confirmation, the force catalogue
and final fresh review remain required. No ordinary success, restored original
campaign numerics or physical multi-GPU outcome is claimed.

## WP2a integrated source review — 2026-11-07

Scope: `git diff v0.45.1 v0.46.0 -- src tests`, DINOv3 HF weight preparation
(`adapters/deim/hf_weights.py`, `adapters/deim/assets.py`,
`adapters/assets/execution.py`, `core/assets.py`) and their consumers. Lenses:
DINOv3 HF preparation (primary), forced admission, OOM receipts and scoped campaign
export, each followed by a skeptic pass.

Finding (low, proven by test): `_cached` did not rebuild a derived checkpoint whose
matching receipt pointed at bytes that make weights-only `torch.load` raise
`TypeError`, `KeyError` or `IndexError`; preparation failed loudly until manual
deletion. Recorded and fixed on branch `review/wp2a-20261107` as
[dinov3-cache-reload-errors](../dinov3-cache-reload-errors/assessment.md).

No other defect was found. The lens checked Q/K/V and standard/gated MLP mapping,
complete source consumption, strict load and reload equality, all receipt fields,
locked atomic publication, CPU RNG isolation, preset routing and Meta-first fallback.
Nonblocking notes: a hard kill leaves `.conversion-*` staging directories; batch
profile and probe paths repeat source hashing and conversion checks on every call.

Verdict: one low-severity defect, fixed on the branch; a patch release and the paired
queue check are still required. Limits: CPU-only tests; real-tensor parity relies on
earlier recorded evidence. This lens did not read the constitution or
`docs/project-contracts.md`, which T2a.1 asked reviewers to receive.

### Scope correction and rules lens — 2026-11-07

A follow-up agent with fresh context, part of the same WP2a workflow rather than an
independent reviewer, read `.specify/memory/constitution.md` (300 lines) and
`docs/project-contracts.md` (331 lines) in full and checked the topic above against them.

Documented deviation (constitution Principle I, specific exception types where
possible): the fix in `adapters/deim/hf_weights.py` `_reload` catches `Exception`.
Rationale: the weights-only unpickler raises open-ended types (including
`AssertionError`), so a fixed list would leave stale checkpoints unrepairable. The
error is never discarded: it is re-raised as `ValueError` with the original as cause,
`_cached` reconverts, and a freshly converted checkpoint that still fails stays loud.
Principle II: the new `core/assets.py` `AssetDerivation` is a frozen Pydantic record
with `extra="forbid"` and no effects. Principle IV: evidence stays CPU-only and claims
no GPU result. Leaving `.conversion-*` staging after a hard kill matches
`docs/project-contracts.md:298-299` (no startup scratch recovery or recursive
deletion), so it remains nonblocking. No new finding. The fresh independent review of
the fix commit `d084dd2` is still pending.

Scope narrowed: the diff examined is `git diff v0.45.1 v0.46.0 -- src tests`, but the
review covers only the T2a.1 topic named above. Tooling-only test changes in that diff
were outside every lens: `tests/test_verify.py` (removed), `tests/test_local_release.py`
and `tests/test_tooling_boundaries.py` come from `8a1d5a9` (verify.py replaced by prek
hooks) and were not reviewed. `tests/fixtures/docs-compatibility.json`,
`tests/test_docs_compatibility.py` and `tests/test_native_backend_ddp_harness.py` come
from `c16dbb1`; their diffs (the `--force` help text and `False` default, and a stub that
keeps the AdamW default-accelerator probe off CUDA in the CPU harness) were read and are
consistent with forced admission and the harness intent; nothing more was examined.

### Independent rules lens — 2026-11-07

A separate reviewer with fresh context checked the whole runtime diff
`git diff v0.45.1 v0.46.0 -- src tests` (runtime change `c16dbb1`; the tooling
changes from `8a1d5a9` were counted as outside the runtime scope) against the
constitution and `docs/project-contracts.md`, covering all four T2a.1 topics.

Verdict: **approve**, no rule violation. Checks run on `f8f2c51`, whose `src`,
`.importlinter` and `pyproject.toml` are byte-identical to `v0.46.0`:
`lint-imports` (52 contracts kept, 0 broken), strict mypy on the changed modules and
their tests (56 files, no issues), `ruff check src tests` (clean) and pytest on
`tests/test_architecture.py`, `tests/test_dinov3_hf_weights.py` and
`tests/test_gpu_inventory.py` (294 passed).

It confirmed typed access with explained third-party exceptions, specific exception
boundaries (`resolve_backbone` falls back only on `AssetResolutionError`), opt-in
`--force` with ordinary serialization unchanged for pre-0.46 readers, and test
conventions without GPU or native claims.

Informational notes, not required by the constitution:

- `_cached` in `adapters/deim/hf_weights.py` rebuilds a rejected cache without
  logging why it was rejected.
- `adapters/assets/execution.py` hardcodes the DINOv3 presets `{"l", "x"}` twice,
  copying the keys of `_DINO`/`_HUB_DINO` in `adapters/deim/assets.py`; a shared
  predicate would keep selection and conversion in step.

The lens also covers the force, accelerator-OOM and scoped-campaign topics; their
records point here.
