# Delivery — 2026-10-20

## Published source

Application `v0.36.0` is published at commit
`42ce196bb4b91d8d4e80fa59397b730bb0d10cd2`. Its annotated tag object is
`745ea0e856698a3b089b0189874939f00b411315`; remote master and the peeled tag
were verified at the release commit after an atomic push. The integrated source
commit is `dfb3a1606f045deb5326a46da94ef18a8618a00f`, preserving both the task
implementation and concurrent upstream `0340e9c` baseline/cleanup history.

The earlier `aaa35d9` candidate and its artifacts were never published. They remain
superseded local evidence. The final source retains the new baseline, dedicated
Ruff/import configuration and relocated fixtures; feature records use epoch `001`.

## Executed acceptance

- Required contributor and release commit hooks passed, including two complete
  routine pytest executions, Ruff, mypy, Vulture and import-linter. Hook output
  does not expose passing pytest counts; none are inferred. Logs are retained as
  `.tmp/cy036/baseline-merge-commit.log` and `integrated-release.log`.
- Parent integration checks passed 395 affected tests. Each minimum environment
  passed 535 affected tests on Python 3.12.13 and 3.13.14; every direct requirement,
  non-root lock record and installed distribution version was preserved. Earlier
  complete minimum suites passed 3,370 tests each, with 30 skips and seven
  deselections; their source snapshot and limitations remain in dependency evidence.
- Fresh independent integration review returned **ship**, with 61 independent
  tests passing and no actionable findings. Architecture acceptance and
  documentation validation passed before the release.
- The final wheel was reinstalled without dependency resolution in four existing
  default/minimum environments across both Python versions. Each passed dependency
  checks, metadata checks and isolated adapter probes. All 186 regular packaged
  files, including 184 Python sources, matched the wheel and tagged source.
  The source archive's payload and project metadata matched the tagged source.
- The wheel has 36 unconditional runtime requirements and no project extras.
  Installed probes verified rejection of extra logical dataset entries before
  materialization, and unchanged valid CSV path, bytes, hash and provenance.
  These probes use a fake SDK; they do not establish new live-service outcomes.

Real ClearML retrieval, paired metrics and CPU/single-GPU pipeline/publication
evidence remain in [native verification](native-verification.md), with their
original source snapshots and scope. The final baseline integration did not repeat
GPU or service execution. No physical multi-GPU, all-backend export, live queued
replay or live OpenCode/DeepSeek result is inferred.

## Build artifacts

The local `dist/` outputs were compared byte-for-byte with the checked release:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `clearml_yolo-0.36.0-py3-none-any.whl` | 427239 | `bbb01a17287de46ed12aac04e83367ab8f82d4400a82bc36b00d8004a06a0dd9` |
| `clearml_yolo-0.36.0.tar.gz` | 343811 | `b137815b4d1a656144e53d784535b9f669f390331437476133d8eb9e0db4464d` |

[Machine-readable artifact evidence](release-artifacts.json) distinguishes final
installed-artifact checks, earlier full minimum runs and native execution.
Only Git commits/tags were published; no package registry, GitHub Release, release
asset upload or deployment was performed.

## Companion guidance and cleanup

The portable usage/evaluation skill is published as collection `v0.2.12`, commit
[`a7bc00f4411bad6759d722a0979b4b0cd20287f7`](https://github.com/BuckanovNikita/custom-opencode-skills/commit/a7bc00f4411bad6759d722a0979b4b0cd20287f7),
after application publication. Remote main and its annotated tag were verified.
Collection discovery, metadata, Markdown, links and architecture checks passed;
prior behavioral evaluations and their live-host limitations remain recorded.
The concurrent published `v0.2.11` baseline links and release history were preserved.
Skill reinstallation is a separate task and was not performed.

Task-owned live resources were cleaned as recorded in native verification.
Artifact probe temporary directories were removed; ignored build/environment/log
evidence is retained. Unrelated working changes and approved external sources are
preserved. The final documentation-only closure changes no executable interfaces,
imports, effects or dependency configuration.
