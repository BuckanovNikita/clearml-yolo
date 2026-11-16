# Ticket98: NVML unavailable-memory review and mutation disposition

## Independent product review

The final inventory extension was reviewed against `fbcfa25`, with tests compared
against `c161f3f`. It changes `GPUState.used` to represent unavailable bytes:
NVML `memory.total - memory.free`, including driver reservations. Admission,
monitoring and capacity envelopes consume that value. Invalid total/free ranges
fail explicitly. Selected CUDA ordinals still resolve through UUIDs; foreign PID
checks remain active and the allocator's zero-reserve path performs no discovery.

No blocking implementation finding was identified. The retained third-attempt
readings report NVML total 32607 MiB and CUDA total 34162343936 bytes; combining
these totals is slightly conservative on this device. This source review does
not establish reserve preservation on other devices or rehabilitate any failed
native case. The reserve breach and later foreign-PID failure remain distinct
invalidating observations requiring fresh successful live evidence.

Reviewed product hashes:

- `gpu_inventory.py`: `b97a7b58b2fd2951a3a77b4a142d8e8554fafa8581b1486c4c07dab8f3900384`
- `gpu_memory.py`: `abb71bc16eb552c2176c73a9a592d6c7091f9839abb8c166da426b33ab3b0502`

## Initial mutation evidence and test correction

The [initial native report](2026-11-16-gpu-states-mutation.json) judged all 73
mutants of `gpu_states`: 61 killed and 12 survived. Five survivors exposed test
gaps rather than defects in the unchanged product implementation:

- 11/70 discarded the UUID-to-PID association. The added successful-query test
  exercises process aggregation, reordered inventories, an unrelated GPU's PID,
  rejection when that foreign GPU becomes selected, and idle-admission rejection.
- 48/49 rejected valid zero-free telemetry; 50 rejected free equal to total. Two
  endpoint cases now exercise the real monitor and reserve boundary, accepting
  exact equality and rejecting one byte beyond available memory.

Only `tests/test_gpu_inventory.py` changed during this follow-up. Product sources
remained frozen. One new test signature was mechanically formatted before the
final checks.

## Final bounded native run

Both runs used the unchanged `scripts.mutation` API, a private `GIT_INDEX_FILE`
initialized from `c161f3f`, and an isolated index export containing the current
inventory source and relevant tests. The entire `gpu_states` function is the only
changed product function against that base. Explicit native target selection
avoids expanding scope through this separate worktree's older HEAD/merge base;
native testmon/import test selection is unchanged.

Before the rerun, the inventory module refreshed testmon dependency records:
29 tests passed in 0.69 seconds. The native run retained the ordinary heavy/live
exclusions, used one child and a 300-second budget, with CUDA hidden, affinity 0,1
and nice19. Statistics, clean baseline and forced-failure checks completed.
The [final machine record](2026-11-16-gpu-states-mutation-final.json) contains
selected test nodes, exact hashes, all statuses and survivor diffs.

| Final result | Count |
| --- | ---: |
| Killed | 66 |
| Survived | 7 |
| Unreached | 0 |
| Unrun | 0 |
| Timed out | 0 |

The five behavior-changing survivors are now killed. Remaining dispositions:

- **19, 28, 39, 67 — diagnostic presentation:** add `XX` around the field name
  passed into numeric-telemetry error construction. Numeric parsing, error class,
  offending value, field identification and fail-closed behavior are preserved.
- **52, 53 — diagnostic presentation:** add a wrapper or change capitalization
  in the inconsistent-memory message; rejection and actionable meaning remain.
- **46 — equivalent on the admitted input domain:** `total_bytes <= 0` becomes
  `total_bytes <= 1`. Integer MiB parsing multiplied by 1048576 cannot produce a
  positive one-byte total, so accepted/rejected inputs are identical.

These dispositions are evidence for this reviewed change, not a survivor allowlist.

## Checks, identities and cleanup

- **Passed:** focused inventory/probe/estimation slice, 224 tests in 3.96 seconds.
- **Passed:** strict mypy for `tests/test_gpu_inventory.py`; Ruff check and format.
- **Passed with advisory dispositions:** final native mutation run, exit 0.
- **Not executed here:** physical GPU admission, capacity, training or publication.
  The coordinator owns the live attempt and final integration gate.

Final test SHA-256:
`aae7f84b60d43d87487cbe673460f9fddea4d6bab153a83f7974a30f7ea04ab4`.
The probe-test input remained
`cc27bd3392bc83989e061dd58d5259141350dcdab76cbc5717825ec9309fedfe`.

Worktree `/mnt/wsl/data/nkt/clearml-yolo` was on local `master` at `e1fe64e`,
equal to local master; remote references were not fetched. Managed-worktree
comparison commits and source hashes identify the reviewed inputs. No shared
index, product file, service or GPU process was changed. All owned verification
processes exited and the private index/export directories were removed. Ignored
runner/log files remain under `.tmp/verification-gap-closure` as reproducibility
evidence; no model assets, shared caches or another agent's files were removed.
