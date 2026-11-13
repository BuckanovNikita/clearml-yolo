# Validation guide

Prepare the existing locked development environment as described in
[development](../../docs/development.md#external-dependencies). Use disposable repositories
and command stubs for workflow/refusal scenarios; never release the actual repository.

1. Exercise staged/latest-commit static, test and product routes, including renames/deletes.
2. Exercise changed tests, shared helpers, valid/stale failures, absent history and empty
   selection; inspect actual argv and assert no expansion or live/heavy execution.
3. Exercise hygiene fixes, syntax/lock failures, staging safeguards and verify early stop.
4. Collect retained product tests and run architecture checks with a deliberate violating
   temporary product module; restore it immediately.
5. Exercise release dirty/moved/locked/final-pair failure and exact-ref publication in a
   disposable repository. Record gates and verify absence of release commit/tag on failure.
6. After integration, run the canonical complete hook pass with overrides cleared and
   applicable explicit acceptance. Obtain independent review and record outcomes/gaps.

## Consolidation verification

Require release CLI evidence and pairing inputs in disposable repositories. Exercise
required/not-required pairing, final-version failure, no-version and publication recovery
without a real push. Run CPU smoke twice in one owned adopted environment with old-name
collisions present; prove distinct published tasks and teardown with local outputs retained.
Run deterministic property and composed-workflow tests after exploration retirement.
Review active skill pointers and policy consistency within native analysis. Record executed
checks, selection reasons and reusable whole-branch evidence in the dated native ledger.
