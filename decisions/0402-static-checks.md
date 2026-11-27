# ADR-0402 · Apply the same whole-tree static checks to each change

Even a local change can break imports, types or dependency declarations elsewhere. The check task runs repository hygiene, lock freshness, Ruff linting and formatting, import contracts, strict mypy, Vulture and deptry in sequence. Hygiene can fix whitespace and fail so the change can be inspected. The separate fix task applies safe Ruff edits and formatting.

These checks cover different contracts. In particular, an allowed import edge says nothing about an SDK call's runtime effect, and absence of a Vulture finding cannot prove a dynamic caller exists. [Static analysis contract](../DOCS.md#static-analysis) · [Check stages](../Taskfile.yml) · [Hygiene implementation](../scripts/hygiene.py) · [Import boundaries](0010-layer-boundaries.md)
