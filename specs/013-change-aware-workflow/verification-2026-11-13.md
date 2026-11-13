# Workflow verification — 2026-11-13

Implementation base: `05f107c`; first integrated implementation: `ab61cb2`.
Worktree: `/mnt/wsl/data/nkt/clearml-yolo`; branch: `013-change-aware-workflow`.
No real release or external push was authorized or performed. Disposable release
repositories exercised local bare remotes only. CY remote refs were fetched after paired verification; the proposed tip contains
remote master (five commits ahead, zero behind at ab61cb2). Paired verification
fetched the queue remote default branch/tags and confirmed that source is current.

## Scope and measured reductions

Product source, dependency pins, `uv.lock` and installed `.specify/` tooling are unchanged.
Six maintained skill entrypoints shrank from 792 to 289 lines (503 fewer, 63.5%).
The initial implementation removed 4,231 lines and added 1,641 including native artifacts.
Final implementation plus evidence diff: 1,840 lines added, 4,231 removed; net 2,391 fewer lines across 63 paths.

Removed coverage: custom static effect-call scanning; maintainer weight-packager tests
(10 functions), dependency-metadata-only tests (2 functions), physical multi-GPU test
scenarios and their six exclusive harness/worker/observer helpers. Five product runtime
configuration cases moved to `tests/test_distributed_configuration.py`. Import/dynamic
import boundaries, inert initializers, runtime targets, fast mutation selection and
process/lifecycle cleanup remain. Purity is still a review obligation. External multi-user,
two-host NFS and embedded unavailable ClearML UI are no longer mandatory acceptance;
this does not establish those deployment outcomes or remove product capabilities.

## Executed evidence

- **Passed:** native Spec Kit specification checklist and cross-artifact requirement/
  constitution analysis; coverage map is in tasks.md. Historical feature011 intent is
  annotated as superseded; no standalone documentation checker was introduced.
- **Passed:** Task check: tracked hygiene/syntax/required inputs, lock freshness, Ruff,
  formatting, architecture, mypy, Vulture and deptry. YAML duplicate-key rejection was
  independently reproduced as a regression, restored with the existing ruamel loader,
  and checked with duplicate and valid input.
- **Passed:** 16 initial disposable routing/selection scenarios, 14 hygiene invocations,
  and actual Task ordering/refusal probes. Staged/latest-commit/prose/infra/source/rename/
  deletion routes, cached stale/live/heavy IDs, known/missing/corrupt/stale helper history,
  parameterized IDs and empty selections were exercised. Non-product work launches no
  tests; collection is in-process and empty selection launches no pytest subprocess.
  Safe whitespace fixes fail until inspected/staged. Added-file size/LFS eligibility
  matches the original hook; tracked incumbent uv.lock remains eligible for syntax,
  whitespace and lock checks rather than a newly imposed size restriction.
- **Passed:** review-regression probes for failed-test cache creation/reselection/clearing,
  shared helpers in test modules, missing/stale shared history, standalone files and ten
  import forms. Selectors remain current explicit node IDs. Import scans identify
  shared inputs; they never broaden the execution selection.
- **Passed:** 26 disposable release scenarios use actual Git and installed semantic-release,
  plus the actual release-commit-check Task body with expensive stages substituted.
  They exercise dirty/moved/divergent/locked refs, failed/deferred gates, final-pair
  failure (prepared files retained, no release commit/tag), version/no-version outcomes,
  one final pair per invocation, immediate/later publishing, exact annotated objects,
  and unpublished ancestor-version tags after documentation follow-ups.
- **Passed:** 74 focused retained product tests and architecture violation probes;
  offline collection contains 4,658 tests, explicit live collection 93. Collection alone
  establishes no native/GPU/publication outcome.
- **Passed:** explicit paired-check, normal resolution and matching editable metadata:
  CY `0.48.1` at `ab61cb2466947f9e3e54bae5813b4d8acfa3b02d`, cy-queue `0.1.10` at
  `d3627a0da85968429ddeaff4920c05825e6e05e2`. Queue Ruff/format/mypy and both import
  contracts passed; 527 tests passed, 7 opt-in tests deselected. Temporary paired venv
  was deleted. No skipped/deselected hardware test is claimed as executed.
- **Passed:** explicit acceptance property exploration: 4,657 passed, 1 skipped.
- **Passed:** explicit acceptance coverage: 4,657 passed, 1 skipped; 84.32% branch-aware
  coverage exceeds the configured 84.12% floor.
- **Passed:** explicit acceptance live CPU pipeline: 1 passed, 29 optional FiftyOne tests
  skipped, 63 GPU cases deselected. The synthetic pipeline trained, published its Output
  Model/evaluation artifacts, and completed against its owned ClearML environment.
  Namespace `cy-it-e910cf` was deleted and proven absent; its record was removed.
  The stage's final clean/unchanged-tip check accepted `ab61cb2`.
- **Passed:** reviewed fixes at `4ef5d96`: targeted Ruff/format/mypy and the actual-source
  disposable routing/hygiene/release matrices; canonical
  `env -u SKIP -u PREK_SKIP -u CY_VERIFY_SCOPE -u PRE_COMMIT_ALLOW_NO_CONFIG -u UV_PROJECT_ENVIRONMENT uv run --locked prek run --all-files`
  passed with no hook edits. Latest-commit classification was static and did not replay
  earlier product work. The final evidence-only commit receives this canonical pass
  again before completion.
- **Passed:** independent closure review at `4ef5d96`: all six findings fixed, historical
  supersession pointers present, no remaining important findings. No required selected
  check remains failed or deferred. Native skips/deselections are reported above and
  are not represented as fresh hardware/database verification.

## Review and evidence reuse

Independent review reproduced five issues: YAML duplicate keys, failed-test cache
updates, shared helpers inside test modules, pre-acceptance master integration and
omission of an unpublished ancestor version tag. A subsequent review additionally
required the ancestor tag's own project version to match its label. All are fixed and recorded
with targeted disposable regressions; tooling-only tests were not added to tests/.

The full product acceptance and paired run use the clean first implementation commit.
Subsequent review fixes change only tooling and documentation; product sources,
configuration, retained product tests and version pair remain identical. Those product
results are reused; affected workflow scenarios and static/final hooks are rerun.
GPU/native release observations are outside this implementation's selected acceptance,
not waived passes. Publishing and real semantic version creation remain unperformed.

## Commands, limitations and cleanup

The full acceptance command was
`CY_TEST_WORKERS=2 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 env -u SKIP -u PREK_SKIP -u CY_VERIFY_SCOPE -u UV_PROJECT_ENVIRONMENT uv run --locked task --exit-code acceptance`.
Property exploration took 469.22 seconds, coverage 518.64 seconds, live pytest 249.38
seconds. Both unit invocations report one skip; their default output does not identify
its reason. Acceptance is reported as the actual successful Task result with that limit.
The paired-check queue suite took 118.42 seconds. These are dated observations, not budgets.

Final product and pair evidence is reusable because review fixes affect only workflow
scripts and documentation, not source, tests, runtime inputs or dependency versions.
Disposition of review findings is reproduced failure → narrow fix → targeted successful
regression; no tooling-only tests were committed. The remaining diff is self-reviewed
recordkeeping, followed by the final canonical committed-tip pass.

The owned live namespace/port-forwards and paired virtual environment were removed.
Disposable Git repositories, command spies, scratch patches and temporary scenario
scripts are removed after recording this report. Native incremental caches remain for
normal reuse. Pre-existing services, other worktrees and user data were left intact.
