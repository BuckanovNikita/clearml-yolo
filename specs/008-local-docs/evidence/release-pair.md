# Proposed CY 0.43.0 and queue 0.1.4 pair

Date: 2026-10-29. This supersedes the proposed-version gap in the
[preliminary pair](paired.md) for feature 008; final committed metadata still needs
refresh before delivery.

Both SSH remotes were fetched. Latest CY `origin/master` is
`f8eb8a3c198806c08c0a41161aa4e8034dec0273`, after the existing `v0.42.0` weight
preparation release. Latest queue `origin/main` is
`4205b9ba58f70cd69ffd9d8380ef0dd5556a3937`, source version 0.1.3. The isolated
CY source was based on that latest released feature 007 plus the integrated 008
diff, preserving published 007 runtime/tests. A new snapshot was required because
the old 007-only pair did not include local documentation.

The candidate is CY **0.43.0** with queue **0.1.4**. Queue's original
`clearml-yolo>=0.38,<0.43` rejects 0.43.0; its proposed `>=0.38,<0.44` was
verified before applying the real two-line queue version/bound change. Queue's
package-fix workflow requires the patch bump. Its runtime and tests are unchanged;
compatibility assessment, architecture and outcomes are recorded in that repository's
`docs/bugs/cy-043-compatibility/` task artifacts.

Approved external source snapshots remained clean and unchanged at digital-metrics
`6e801be1564dce458294eb23592cc1aa0939c4d9` and report-generator
`d10aa395d08f738e92e04e076cee93b3a993bf8f`.

## Executed checks

A private Python 3.12.13 environment used a frozen requirements export of the
integrated CY lockfile. Snapshot normalization changed only CY's project/root lock
version and queue's version/bound. Normal source installation used `uv pip install`
with the frozen export and editable CY/queue/approved external sources, copy mode,
and no `--no-deps`. Shared environments and workers were preserved.

| Check | Result |
| --- | --- |
| Normal dependency resolution | 285 packages installed successfully |
| `uv pip check` | All installed packages compatible |
| Isolated source/installed metadata probe | All four versions, normalized direct requirements, module origins and editable URLs match captured sources |
| Queue ordinary `python -m pytest -q` | 518 passed, 7 opt-in physical tests deselected; 19 upstream deprecation warnings |
| Queue `ruff check .` and `ruff format --check .` | Passed |
| Queue strict `mypy .` | Passed, 69 source files |
| Queue `lint-imports` | Both contracts kept; 67 files and 205 dependencies |
| Installed `cy-queue --help` outside sources | Passed |
| Train/pipeline composition while all CY documentation imports raise | Both snapshots compose and validate; documentation never loads |

The deny-documentation probe initially used a temporary project outside inherited
`CY_HOME`, which correctly failed existing filesystem confinement. Its fixture was
corrected to set `CY_HOME` to the temporary project, then the same probe passed.
No product code changed. The ordinary suite and all other checks passed initially.

The exact commands, logs, package origins and source inventories are retained in
private task evidence `cy008-release-pair-nk8xx0ix`: `results.json`,
`source-manifests.json`, `tested-manifests.json`, `normalization.json`, `identity.json`
and `proposed-*.log`. Each result records command arguments, directory, exit status,
duration and log hash. The snapshot manifest hashes after normalization are:

| Package | SHA-256 of sorted path/hash mapping |
| --- | --- |
| clearml-yolo | `fac1c8f348c9743ee87542f4d0c01fa2197f930a42235a6bfef1f54eea52141e` |
| cy-queue | `ae19dcf2619141849b5957ba847019324e33f2d87ce635d8a3955ccdd4e46090` |
| digital-metrics | `88f5b0d13224e04104e0d63bcb65c8aa23ae2e7084c507fd4293159b0b009272` |
| report-generator | `f9b58fddd7a33dea362c72fdc1ddda92baaf78bcca8522340a0107584498fdd0` |

Before/after inventories detected only concurrent changes to feature 008's prose
specification, task ledger and delivery evidence. No CY runtime/test/configuration,
queue source or approved external dependency drift occurred during checks.

This is proposed-version integration acceptance. Final committed-source comparison,
reinstallation and metadata refresh remain required before pushing. Independent
review and CY canonical/native acceptance remain separately recorded in their own
feature evidence. These queue checks do not establish physical GPU/NCCL,
multiuser/NFS, remote publication or operational environment upgrades.


## Final committed-pair refresh

Date: 2026-10-29. The final refresh passed before delivery, using only the retained
private paired environment. The canonical CY verification environment and the
original proposed-source snapshots were not modified.

- CY release commit: `dbde23565a9938cfb7556819ab6a5beee24d5423`, version 0.43.0;
  feature parent: `60091649dd71087e5dac2a9a712098eaa5be5de6`.
- Annotated Git tag `v0.43.0`: object
  `877480264094557b82ae1166b1ebbbecbbd27011`, peeling to that release commit.
- Queue commit: `114b97272ab5bb406a90c146ea62d8fdd19d75b1`, version 0.1.4,
  requiring `clearml-yolo>=0.38,<0.44`.

Both repositories were clean at capture. Each copied file was verified against
its committed Git blob identity. Both actual `pyproject.toml` files and CY's
`uv.lock` match the tested proposal byte-for-byte. Every runtime, test, script,
browser-test and checking-configuration file also matches; only changelog and task
acceptance prose differ. Both approved external source trees are unchanged.

The committed sources were installed normally from a fresh frozen export into the
retained private environment, without `--no-deps`. Resolution accepted 285 packages;
only the four editable origins were refreshed. Dependency consistency and exact
source/installed versions, normalized requirements, module origins and editable
URLs passed again for all four distributions.

The complete queue suite again passed: **518 passed, 7 deselected, 19 upstream
warnings**, in 120.44 seconds. Ruff, formatting, strict mypy (69 files), both
import contracts, installed help and deny-documentation pipeline/train composition
all passed. The installed `cy-docs --check` passed with 467 fields, 156 configurations
and 8 tutorials. An isolated catalog probe explicitly asserted installed CY version
and catalog version both equal **0.43.0**.

Final committed snapshot manifest hashes:

| Package | SHA-256 of sorted path/hash mapping |
| --- | --- |
| clearml-yolo | `6045f9c9eecbbbffd0c331c1e7615ecc59d8abc29aeeef55438bd6d4a9aebe8d` |
| cy-queue | `b6e7975e6c5606ff4c4151e8c56722deef8e17ffe6558fbb23036d34a6449f71` |

The external manifest hashes remain those recorded above. Post-check source
inventories found **no drift in any of the four source repositories**. This
appendix is the subsequent evidence-only change. Markdown/local-link validation
passed for both appended records.

Private evidence retains `committed-source-manifests.json`,
`committed-proposal-comparison.json`, `committed-source-drift.json`,
`committed-identities.json`, `committed-evidence-hashes.json`, exact commands in
`results.json` and `committed-*.log`. Recorded command log hashes were independently
recomputed and matched. Fresh integrated reviews are recorded separately; final
committed pairing is now accepted. Remote push status remains the delivery owner's
responsibility, and the stated physical-execution limitations still apply.
