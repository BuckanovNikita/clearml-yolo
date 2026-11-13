# Dated evidence index (history)

Everything indexed here is dated history. Commands, paths, endpoints, task IDs,
and hardware counts in these files are past observations, never current
instructions. Current guidance is the `clearml-yolo-environment` skill and its
Machine workflow reference. Archived files
are preserved byte-for-byte within this project-local package. Keep their relative
layout and checksum manifests intact. Absolute paths in archived observations refer
to their original locations and are not current invocation instructions.

Inventory paths below start at `.agents/skills/clearml-yolo-environment/references/`
within the repository.

| Date | Evidence | What it records | Integrity |
| --- | --- | --- | --- |
| 2026-09-19/20 | `release-030-evidence` | clearml-yolo 0.3.0 release verification; exact copy of the application's former `docs/evidence/` tree; predates the move of the helpers into this skill; includes the RTX 5090 and separately owned VLLM observation (historical, not a current capacity claim) | `release-030-evidence.sha256` verifies all 15 files by relative path |
| 2026-10-02 | `console-logs-2026-10-02-evidence.md` | ClearML console-log delivery verification (not training or DDP acceptance) | none |
| 2026-10-02 | `mongodb-2026-10-02-evidence.md`, `mongodb-2026-10-02-combined-suite.log` | shared MongoDB deployment, real FiftyOne persistence, isolation and cleanup | none |
| 2026-10-20 | `cache-cleanup-2026-10-20/archive.md`, `cache-cleanup-2026-10-20/acceptance.md` | feature 036 native cache acceptance; its Python and shell files are historical reproduction helpers, not wired into the skill, tests or runtime | `cache-cleanup-2026-10-20/SHA256SUMS` |

Verify integrity:

```bash
project_root="$(git rev-parse --show-toplevel)"
skill_dir="$project_root/.agents/skills/clearml-yolo-environment"
(cd "$skill_dir/references" && sha256sum -c release-030-evidence.sha256)
(cd "$skill_dir/references/cache-cleanup-2026-10-20" && sha256sum -c SHA256SUMS)
```

Other local run evidence, such as `queue-finalization-*`, is untracked and
excluded from the package. Preserve it separately before any package replacement or removal.
