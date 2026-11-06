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
