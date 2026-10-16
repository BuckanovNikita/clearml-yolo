# Readable queue documentation verification — 2026-10-16

## Reviewed scope

Documentation was reconciled against the implementation on `feat/readable-shared-queue`,
based on application 0.32.0, before its new release. Inspected settings parsing and
host binding, storage/archive records, application visibility, CLI arguments, TUI
bindings, readable formatting, trace task naming and workbook metadata. The README,
technical reference, queue/filesystem/diagnostics/reporting contracts, architecture
guidance and current-contract index now describe the same interfaces. Historical
specifications and verification evidence were preserved.

The canonical portable skill companion changes are
[`SKILL.md`](https://github.com/BuckanovNikita/corp-skills/blob/main/skills/clearml-yolo/SKILL.md),
[`usage.md`](https://github.com/BuckanovNikita/corp-skills/blob/main/skills/clearml-yolo/references/usage.md)
and [`evaluation.md`](https://github.com/BuckanovNikita/corp-skills/blob/main/skills/clearml-yolo/references/evaluation.md).
They were edited in their source repository, based on collection 0.2.6. No installed
copy was replaced. The added scenarios cover two-user configuration, archive/restore,
conflicting roots and readable reports with retained exact provenance.

## Executed checks

- Baseline: the former `CY_QUEUE_ROOT`-only listing recipe failed with the new required
  `CY_QUEUE_CONFIG` explanation, establishing that the old usage instructions were stale.
- Actual command help verified `config`, `submit --label/--json`, `list --archived/--all`,
  and multi-target `archive`. Source inspection checked TUI bindings and remaining options.
- An isolated temporary TOML fixture exercised `config --json`, an explicit `--root`
  override, agreeing legacy `CY_QUEUE_ROOT` and a conflicting legacy value. Valid
  settings returned the expected paths; conflicting settings failed. Read-only commands
  created neither metadata nor coordination directories. Temporary files were removed.
- `uv run --frozen --no-sync python scripts/check_docs.py --all docs/readable-output.md`
  checked 476 Markdown files with zero issues before this evidence file was added.
- The installed skill-creator package validator passed. A duplicate-rejecting YAML
  loader checked frontmatter types, name/folder agreement and four package-local links.
- `DISABLE_TELEMETRY=1 npx --yes skills@1.7.1 add . --list` discovered the portable skill
  without installing it. Collection-wide markdownlint-cli2 0.23.3 checked 37 files
  with zero issues. `git diff --check` passed in both repositories.
- The final application documentation check including this evidence file checked
  477 Markdown files with zero issues. The companion's added evidence and no-impact
  architecture record passed plan validation; collection Markdown validation then
  checked 38 files with zero issues. Collection 0.2.7 metadata is prepared but uncommitted.

## Independent review and limits

Fresh independent usage review accepted the corrected package and application
guidance. Nine reasoned scenarios and actual read-only help/configuration checks
passed. The reviewer identified and verified correction of an overbroad raw-log
claim: original invocation captures retain exact bytes; the queue's combined log
can receive the readable mirror. The companion evidence records these results.

These checks establish documentation syntax, packaged references and observed command
interfaces. They do not establish training, physical GPU concurrency, ClearML publication,
multi-user/NFS execution, automatic skill routing or OpenCode/DeepSeek behavior.
Runtime review remains a separate feature gate. Companion release follows application publication;
this record does not claim either release has occurred.
