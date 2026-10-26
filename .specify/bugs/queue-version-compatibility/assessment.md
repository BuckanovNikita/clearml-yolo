# Bug Assessment: latest CY and queue cannot install together

- **Slug**: queue-version-compatibility (selected from the reported failure)
- **Created**: 2026-10-26
- **Source**: conversation
- **Verdict**: valid
- **Severity**: medium — blocks installation of the current source pair

## Report

The user requested compatible latest versions of CY and its separate queue,
creation of a public queue repository if absent, and a permanent requirement to
check both latest versions on every release.

## Reproduction and root cause

`uv pip install --python .venv/bin/python --dry-run -e . -e ../cy-queue`
fails resolution: queue 0.1.0 requires CY `>=0.38,<0.39`, while CY source is
0.40.0. `uv pip check --python .venv/bin/python` also fails because the existing
editable CY metadata still says 0.39.0. The source release changed without
updating queue metadata or checking the pair. Confidence: high.

## Remediation and architecture

1. Extend the queue's bounded CY requirement only through the inspected 0.40
   minor; publish the packaging correction as queue 0.1.1. Retain the existing
   0.38 floor. Inspect the intervening interfaces and run the complete queue suite.
2. Strengthen installed-package verification to check source and installed
   requirements against both CY source and installed versions, rejecting stale
   editable metadata. Keep CY independent of the queue at runtime.
3. Install both editable sources together with normal dependency resolution,
   preserving approved external source copies and existing local uv overrides.
4. Document public source installation and a mandatory paired release check in
   both repositories, including the proposed release version before publication.
5. Validate docs, queue lint/types/import contracts/tests, dependency consistency,
   CLI entrypoints outside the checkout, and independent review. Commit each
   repository; evaluate CY's native release workflow, create the requested public
   queue remote and push both intended branches. No registry publication or assets.

CY changes are documentation-only, recorded in [architecture.json](architecture.json).
Queue metadata/test ownership and executable contracts are recorded in the queue
repository's `docs/bugs/queue-version-compatibility/architecture.json`. Queue
adapters retain process/GPU effects; core/application remain pure. No runtime
imports or lifecycle protocol changes are planned.

## Scope and dependencies

Queue: `pyproject.toml`, `tests/test_standalone_training.py`, `README.md`,
`AGENTS.md`, `docs/development.md`, `docs/interfaces.md`, and task evidence.
CY: `README.md`, `AGENTS.md`, `docs/queue.md`, `docs/development.md`, and these bug
artifacts. Preserve the pre-existing local `[tool.uv.sources]` section exactly.
The portable usage skill already requires compatible source installs in the same
environment; its CLI/config examples remain valid and need no changes.

Independent read-only compatibility/publication inspection runs alongside parent
reproduction and artifact preparation. Implementation follows plan validation;
fresh independent review follows integrated verification. Do not rewrite feature
003/005 history or change upstream dependencies. No active queue processes were
observed before the planned environment refresh. No GPU/publication claim is made.

## Acceptance

The original resolver reproduction and `uv pip check` must pass; source/installed
versions must agree; queue's complete ordinary suite and configured static checks
must pass; both documentation checks and architecture acceptance must pass. Review
the full task diff before commits and public delivery. Future untested CY minors
remain outside the queue bound; release instructions must require advancing the
pair together when needed. No unresolved design questions.
