# Verification: batch cleanup permissions

- Date: 2026-11-02
- Status: source fix verified; native release blocked
- Assessment: [assessment.md](assessment.md)
- Fix: [fix.md](fix.md)
- Independent review: [review.md](review.md)

## Reproduction and behavioral verification

The two added real-subprocess tests failed against unmodified current upstream
when case-pool and training-worker cleanup attempted to enumerate all `/proc`.
After the fix, the focused pool, training worker, native descendant, subreaper and
capability suites passed: 72 tests. Coverage includes sibling preservation, detached
adopted grandchildren, shutdown interruption, uncertain cleanup retry, helper
preservation, inaccessible relevant descendants, PID identity and thread topology.

## Acceptance checks

Canonical verification, final locked paired checks and documentation validation
are recorded below after completion. The initial unlocked environment selected a
newer Ruff release and reported unrelated lint diagnostics; acceptance uses the
repository lockfile and does not change dependencies or their approved sources.

## Documentation

Updated runtime worker cleanup guidance. Portable usage source and references were
inspected at commit `80ec2a037e008fafe401e39e9f1b507005cb9a0d`; no change is needed
because CLI, configuration, output and recovery procedures are unchanged.

## Limitations

The exact remote host/PID permissions from the report cannot be replayed locally.
The regression tests exercise actual process supervision with prohibited unrelated
proc enumeration. No CUDA capacity, model quality or ClearML publication claim is made.

## Native release gate: blocked

The shared environment's required `infra.py room` preflight failed with exit 1:
its Kubernetes API request could not validate the configured TLS certificate
(`x509: certificate signed by unknown authority`). Capacity/reservation admission
and the required single-GPU native release run could not be established. No stand,
certificate, credential, service or pre-existing workload was changed. No new GPU
work was launched. The exact estimator CLI also correctly rejects foreign GPU
compute, so a contaminated capacity measurement is not substituted for this gate.

The source fix can be committed on a dedicated branch after canonical checks,
but this missing native release evidence blocks version tagging and delivery.
No code GitHub Release, distribution asset or package publication is authorized.

## First complete run and consistency rejection

All canonical check commands returned zero. The complete suite reported 4,703
passed, 30 skipped and 81 deselected, including native CPU-DDP and architecture
negative cases. The verifier then rejected its receipt because optional `pi-heif`
1.4.0 was installed during execution. Input timestamp inspection identified only
that decoder's installed files as changed; no task source files changed. The
decoder is retained in the isolated prepared environment, with no project
dependency/lockfile edit. A fresh canonical run now verifies stable inputs.

## Paired source and environment evidence

- CY base: `73bb044`, version 0.44.7, with the task-owned patch.
- Latest queue source: `32bea017b609a258300619cef2d170a14a8aa2a7`, version 0.1.7.
- Normal editable source installation resolved both packages and the existing local
  external dependency sources without `--no-deps`; installed CY/queue versions and
  source imports matched those checkouts. Frozen development sync aligned the
  environment with CY's lockfile; no source revision or lockfile was changed.
- `uv pip check --python .venv/bin/python`: passed.
- Queue `python -m pytest -q` under the prepared CY environment after decoder
  installation: 582 passed, 7 deselected (19 warnings).
- Queue Ruff, strict mypy (70 files), import-linter (two contracts), and installed
  `cy-queue --help`: passed.
- No proposed release version is installed or tagged: native release admission
  remains blocked as recorded above.

## Scope and documentation reconciliation

The owned implementation is limited to the existing process-tree adapter and its
case-pool/training-worker callers, with three test files and runtime documentation.
No architecture import rule, dependency source/revision, CLI, persistent schema or
configuration changed. Scoped mutation targets are unaffected. Extensive unrelated
changes in the original checkout remain intact. The isolated checkout has no local
`[tool.uv.sources]` section to remove around the eventual fix commit.

## Stable final canonical acceptance

`uv run --frozen --no-sync python scripts/verify.py` completed successfully,
including its final unchanged-input check and private application receipt. Ruff,
strict mypy, Vulture and import-linter passed; complete pytest reported 4,703
passed, 30 skipped, 81 deselected and 182 warnings. The skips/deselections do not
establish optional service/GPU outcomes. Native CPU-DDP and architecture negative
cases ran in the ordinary suite. No source changes followed this successful run.

`uv run --frozen --no-sync python scripts/verify.py --docs` passed for the
updated runtime guidance and all bug artifacts. Architecture plan validation passed
before implementation; final module scope, executed checks and independent review
were reconciled for acceptance. The native GPU prerequisite failure remains an
explicit release gap; it is not counted as a passing verification.

## Commit hooks

The native changelog hook refreshed eight generated lines for the already committed
upstream documentation change `73bb044`. The parent reviewed that exact diff and
staged it for the required retry. The exact source/dependency hook passed using
the successful canonical evidence. Package version and lockfile remain unchanged;
no local source-override section exists in this isolated checkout.
