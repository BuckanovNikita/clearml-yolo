# Portable usage companion, 2026-10-30

The canonical corp-skills source was fetched and inspected. An isolated clone starts
at `b4fdd473ef85571fa81f75b47dd0ece8a10e1659` (collection 0.6.6), preserving all
original sibling working-tree changes. Collection patch **0.6.7** is locally
committed at `914f81b0d27fe6b2888adb2a4462bec47f90a145` after fresh review;
its tag/push waits for verified public CY and queue release refs.

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

## Queue threshold follow-up and local commit

The user's queue memory-threshold follow-up adds guidance for cy-queue 0.1.6's
optional `[queue].max_used_memory_gib`. The portable example uses 6.0, retains the
2.0 default and required queue roots, and requires a positive finite numeric value.
It explains the strict used-VRAM boundary, missing-telemetry rejection, effective
configuration diagnostics, owned-worker restart and frozen launch values. Existing
holds, reservations and manual-free behavior remain distinct from memory admission;
the setting neither reserves VRAM nor changes direct CY checks. Retired worker flags
and Hydra overrides remain unsupported. Private machine preferences are outside this
portable source.

An isolated source-CLI example verified the documented custom value, omitted default,
invalid-string rejection and absence of queue-state creation. Existing fixed-threshold
evaluation cases were reconciled, and a fourth new explanation-only prompt covers
configuration, equality at the threshold and unchanged contracts. Fresh read-only
agent `review_queue_memory` returned **ship** for the queue implementation and this
portable follow-up, with no findings. Its explicit-reading response passed the new
prompt, including the distinction between currently loaded config output and already
running worker/guardian settings. It independently passed 88 queue tests, verified
the frozen source inventory, and passed package consistency, changed Markdown/local
links and architecture acceptance.

The seven task-owned collection files were explicitly staged and committed as
`docs(clearml-yolo): document faster batch search and queue thresholds`. Final
collection checks passed: four-skill discovery, all 72 Markdown files, five changed
documents/local links, metadata validation, architecture acceptance and staged
whitespace/diff inspection. The collection working tree is clean. The application
pair is recorded in [paired verification](paired.md); collection publication remains
pending its public-release gate. No collection tag, push or installed-skill replacement
has occurred at this checkpoint.

## Verified publication

After verified CY 0.44.4 and queue 0.1.6 publication, the collection release checks
confirmed a clean main branch, upstream ancestry, matching VERSION/changelog and
absence of the new tag. The atomic push published main at
`914f81b0d27fe6b2888adb2a4462bec47f90a145` and annotated tag `v0.6.7`, object
`a07de3b24b0c0a2395680f2dde7707bbd8dc58b2`, peeling to that same commit.
Remote refs were verified through both the original origin and its canonical moved
repository, `BuckanovNikita/custom-opencode-skills`. The parent independently checked
the remote branch, tag object and peeled commit. No source or evidence changed after
the reviewed commit; no installed-skill replacement, GitHub Release or assets were
created.
