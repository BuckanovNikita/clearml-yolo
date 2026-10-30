# Portable usage companion, 2026-10-30

The canonical corp-skills source was fetched and inspected. An isolated clone starts
at `b4fdd473ef85571fa81f75b47dd0ece8a10e1659` (collection 0.6.6), preserving all
original sibling working-tree changes. Collection patch **0.6.7** is prepared;
it remains uncommitted until fresh review and parent release coordination.

Changed paths are `skills/clearml-yolo/SKILL.md`, `references/usage.md`,
`references/evaluation.md`, collection VERSION/CHANGELOG.md and dated no-impact
architecture/verification records. No installed skill copy is changed.

The guide covers memory-guided search and full-trial evidence, independent cases on
idle selected GPUs, automatic concurrency, positive `--jobs`, `--jobs 1`, cache and
failure isolation, owned cleanup, schema-3 strategy writes, schema-1/2 legacy replay
and keys, fingerprint compatibility and numerical recovery's candidate-order
dependence. Single-GPU measurement and linear multi-GPU extrapolation remain distinct.
The physical multi-GPU verification limitation is explicit. Three new explanation-only
evaluation prompts cover concurrency, numerical evidence and catalogue migration.

Executed checks:

- Collection discovery found all four skills, including clearml-yolo, without installing.
- Pinned Markdown lint passed for 72 collection Markdown documents, with zero issues.
- Skill metadata validation passed; extra checks rejected duplicate YAML keys and
  verified allowed fields, types, lengths, name syntax and folder agreement.
- CY's Markdown/local-link checker passed the entrypoint and both references with
  the skill folder as root, and five changed collection documents with the collection
  root; zero issues in both passes.
- The current shared parser accepted the documented selected-model/device example
  with automatic jobs, `--jobs 1` and `--jobs 2`; `--jobs` appears in help. The
  resolved settings retain five warm-up/ten measured updates and `memory_guided_v1`.
- The documentation-only architecture record passed plan and acceptance validation;
  `git diff --check` passed.

Parser/help and packaging checks do not establish GPU execution or speedup. Fresh
independent review covered all three new explanation-only prompts. No live
OpenCode/target-model evaluation, companion commit, tag, push or installation has
been performed at this checkpoint. Final application/collection identities and review
results will be appended after parent acceptance.

## Independent review outcome

Fresh read-only agent `review_portable_speedup` returned **ship** after inspecting
all changed and added files and explicitly evaluating the three new prompts.
The parent corrected the single finding: ordinary measurement/result failures
leave peers running, but unrecoverable process-supervision failures can stop the
invocation while preserving accepted results. The reviewer checked the correction
and reran Markdown/local-link and whitespace checks. There are no unresolved findings.
The companion's dated verification record retains prompt outcomes and reviewed checks.
No routing or live OpenCode/target-model result is inferred from this native-agent review.
