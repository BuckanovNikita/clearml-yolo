# Instruction and contract audit

**Date**: 2026-09-30
**Baseline**: `5a11674d44e11a0726333d3c3a9c86e4590dd7fb`
**Scope**: documentation and instructions only; no application, dependency, helper-script,
commit, release or live-infrastructure changes.

The user authorized rewriting current normative guidance to the current implementation,
preserving dated evidence, and documenting existing standalone comparison split overrides.
The [current contract index](../current-contracts.md) routes maintained requirements by topic.
The initial implementation amended the constitution to 6.0.0. The user subsequently
requested restoring all Spec Kit files; that amendment and the Spec Kit customizations
were dropped. Project workflow overrides now live in AGENTS.md (see the scope revision below).

## Findings and initial resolutions

References below identify baseline conflicting guidance and unchanged implementation.
The project documentation uses the corrected behavior, or labels a preserved historical
record explicitly. Spec Kit resolutions in this original matrix now apply through AGENTS.md;
Spec Kit files were restored at the user's request. Configuration composition establishes syntax/resolution, not native execution.

| Finding | Conflicting guidance at baseline | Evidence and correction |
|---|---|---|
| Authority was incomplete | AGENTS pointed only to the original release contracts | [Contract index](../current-contracts.md) maps amendments by topic; code/spec mismatches must be reported explicitly. The original CLI contract already used current groups, so the initial audit's contrary claim was withdrawn. |
| Removed native syntax remained runnable | [Archived migration guide](https://github.com/BuckanovNikita/clearml-yolo/blob/96aa7508d9e16364722d9126f37748ce074d2134/docs/migration-030.md), Native settings; global environment skill command examples | `apps/common.py:24` rejects removed wrapper fields; `native_config.py:175` rejects non-null native cfg. Examples now use top-level groups and ordinary native overrides. |
| Native YAML publication contradicted inventory | [Feature 003 spec](../../specs/003-ultralytics-config-groups/spec.md), replay story; [archived group migration](https://github.com/BuckanovNikita/clearml-yolo/blob/96aa7508d9e16364722d9126f37748ce074d2134/docs/migration-ultralytics-groups.md), local/remote replay | `native_config.py:309`, `tasks/train.py:85`, `tasks/predict.py:165`, `clearml_session.py:551` retain native YAML locally and record canonical configuration; no native YAML artifact. |
| Dataset diagnostics were required as artifacts | [CSV training contract](../../specs/004-ground-truth-training/contracts/cli.md), preparation/publication | `tasks/train.py:64` publishes canonical truth, attaches the consumed dataset and records overrides; NDJSON, preparation records and label archives remain local. |
| Dataset preparation was still run-owned | Feature 004 spec FR-013, plan and research storage sections | `dataset_cache.py:35` resolves a shared CSV-addressed cache outside run outputs. Preparation/conversion files remain in the cache; source images are immutable and owner previews are distinct from dataset artifacts. |
| FiftyOne receipt upload was promised | [Publisher contract](../../specs/006-fiftyone-integration/contracts/publisher.md), owner receipt | `tasks/publication.py:62` writes a local receipt and records the result in run configuration; it does not upload the receipt. |
| Metric artifact counts contradicted consolidation | [Feature 007 spec](../../specs/007-detection-config-cleanup/spec.md), FR-006/SC-003 | `tasks/metrics.py:48` publishes consolidated evaluation workbooks; `tasks/metrics.py:193` publishes exact validation thresholds. Old counts are preserved only in annotated historical records. |
| Native callbacks were described as disabled | Feature 007 native execution requirements; old migration tracking text | `native_runtime.py:96` enables installed callbacks for the owner and `native_runtime.py:118` restores modified process state. Workers do not publish; native training/validation previews are permitted. |
| Standalone comparison was described as test-only | [CLI contract](../../specs/001-release-030/contracts/cli.md), evaluation; constitution Principle III | `tasks/compare.py:595` accepts split; `tasks/pipeline.py:115` fixes test; `tasks/report.py:49` uses the paired manifest split. Documented under the user's explicit decision; no code change. |
| Source-task configuration retrieval was overstated | [Tracking recovery contract](../../specs/010-native-clearml-integration/contracts/tracking-publication.md), Recovery | `tasks/compare.py:132` recovers weights/thresholds and source links; `tasks/compare.py:467` stores sanitized provenance. Current inference settings remain authoritative; source General/Configuration Objects are not automatically imported. |
| Completed work retained pending statuses | Live specs 005, 007, 009 and 010; point-in-time analyses | Status now cites existing verification. Dated analyses remain snapshots, not claims of current pending implementation. Checked task history and observed run evidence remain unchanged. |
| Generic workflows could override host planning restrictions | Local skill Host compatibility and automatic-hook directions | All skills state host-mode/user-scope precedence; mutating artifact generation and hooks wait for implementation authorization. Existing authorization is reused within scope. |
| Templates prescribed commits/deployment and optional verification | [Task template](../../.specify/templates/tasks-template.md), Tests/Strategy/Notes | Commits/deployment require explicit scope. Verification is always proportional; new automated tests depend on affected behavior and risk. |
| Ignore-file edits were automatic scope expansion | [Implement skill](../../.agents/skills/speckit-implement/SKILL.md), Project Setup Verification | Inspect/report first; editing an ignore file requires an affected task or explicit authorized scope. |
| Bug source capture could persist credentials | [Bug assessment](../../.agents/skills/speckit-bug-assess/SKILL.md), source URL and quoted input | Source references and quoted input redact credentials. Canonical extension commands and rendered skills are updated together. |
| Bug slugs/path rules and collisions were inconsistent | Bug assessment/fix/test and extension README | Validate contained paths and symlink ancestors before I/O. Explicit slugs retain identity on collision; only generated slugs may receive a suffix. |
| A changed bug hypothesis abandoned authorized work | [Bug fix](../../.agents/skills/speckit-bug-fix/SKILL.md), Apply remediation | Reassess inline, record deviations and continue within the authorized bug. Ask only for material new scope or missing information. |
| Constitution scratch reports could remain tracked | [Constitution skill](../../.agents/skills/speckit-constitution/SKILL.md), Sync Impact Report | Report temporary impact in the response; preserve dated amendment history and complete the update without temporary scratch text. |

## Coverage and preservation

The baseline inventory contains 170 first-party tracked Markdown paths: 108 feature
files, 20 local skill/reference files, 26 Spec Kit files, 13 documentation files and
three root paths (including the CLAUDE compatibility symlink). The audit examines these
by topic and parses all for local links and Markdown structure. Spec Kit scripts,
workflow definitions and integration metadata were inspected to check instructions
against their callers. The applicable global ClearML environment entrypoint and machine
workflow were checked separately; machine-specific details stay in that global package.

Dated verification and release records are historical evidence. Earlier analysis/research
snapshots and completed task descriptions retain their original facts; annotations route
readers to current behavior. No historical run is reclassified as newly verified.
Unsupported paths and dates in the initial delegated planning report were excluded.

## Follow-up outside this documentation change

`.specify/scripts/bash/setup-plan.sh:35` creates a feature directory and can write a plan
before the caller confirms `spec.md` exists. AGENTS.md now requires a read-only prerequisite check before
calling it; the plan skill itself is restored. A separately authorized helper fix should validate the specification before
writing and test that failure leaves the filesystem unchanged. The helper itself remains
unchanged here.

The registered full SDD workflow has explicit interactive spec/plan gates. These remain
intentional when that workflow is invoked; they are not generic permission requests for
other work already authorized by the user.

Spec Kit customizations were removed at the user's request. Installed workflow files remain
at their original revision; separate project overrides belong in AGENTS.md or project hooks.

## Initial verification record (before requested Spec Kit restoration)

- Configuration examples: eight generated command configurations plus four representative
  current native/split overrides composed and resolved successfully with the locked environment.
  Temporary exports were removed by their context manager. No execution task was started.
- Markdown/link checks passed: 174 files parsed (172 repository paths and two applicable
  global files), 259 local links/anchors checked, and no unclosed fences or missing targets.
- All 19 local skill frontmatters remained valid and unchanged. All eight canonical extension
  command bodies matched their rendered skills after command-placeholder substitution.
- Scope/preservation checks passed for 89 tracked Markdown changes: no application, scripts,
  checks, dependency metadata or submodule changes; dated evidence, completed task descriptions
  and the CLAUDE compatibility symlink were preserved. Two new repository documents are
  the contract index and this evidence record. `git diff --check` passed.
- Parent inspected the combined change set and reran these checks before independent review.
  The first review returned `fix-first`: peer-IP requirements blocked ordinary allowlisted
  URL fetching; Plan Mode needed an explicit exit before mandatory hooks/writes; rewritten
  requirements cited historical evidence for superseded behavior. These were corrected by
  scoping address enforcement to raw/unrecognized-host fetches, adding early read-only exit
  branches to all skills and canonical command sources, and linking later acceptance while
  distinguishing static split-override checks from live current-test evidence. Checks were
  rerun after the corrections. The second fresh review confirmed those closures and found
  an earlier ingestion sentence that fetched URLs before the policy gate; both canonical and
  rendered copies now apply the policy first and retain pasted-text fallback. Checks were
  rerun again. The third fresh read-only review returned `ship` with no findings, confirming
  the ingestion correction and the earlier closures. Its residual limitations are the
  unexercised live URL/native/GPU/DDP/upload/non-test comparison paths listed below.
- Behavior scenarios are instruction reviews, not executions of agents against private URLs
  or live services. Native training, GPU, uploads, physical DDP and standalone non-test
  comparison execution were not exercised by this documentation task.
- Existing external URLs are not newly introduced by this change and were not fetched.
  Internal link validation does not establish availability of an external service.

## User-requested scope revision

After the initial accepted implementation, the user requested dropping all changes to
Spec Kit files and using separate hooks or AGENTS.md for necessary policy. Restored all
29 changed files under `.specify/` and `.agents/skills/speckit-*` to the original HEAD,
including the constitution, extension sources, rendered skills and task template.
Project specs, README, migrations, contract index, end-to-end skill and global environment
example corrections remain. Workflow safeguards and the customization boundary are now
in AGENTS.md; no separate hooks were needed.

The initial verification and review entries above describe the superseded implementation,
not an independent review of this scope revision. Restoration and revised Markdown/link
checks passed: every tracked Spec Kit file is byte-identical to HEAD; 174 Markdown
files parsed and 258 local links/anchors validated. The 60 retained tracked changes
are Markdown only; the index remains unchanged. `git diff --check` passed. Application, dependency and helper-script files
remain unchanged.
