# DINOv3 weight publication — 2026-10-31

## Scope and analysis

Task starts from latest remote CY `b23952c433f2addbbdc981fbed1fd8073602cd01`
(version 0.44.4); queue latest main is
`2fbaed25fa7c572757d30cb9b1b343d22e645e3a` (0.1.6). An isolated worktree
preserves every pre-existing workspace edit and local dependency override.
Proposed code patch release is 0.44.5: it repairs the maintained weight snapshot's
DINOv3 omission without changing interfaces, dependencies or loader behavior.

The two amended requirements FR-011/012 map to T017–T023. The existing five
requirements-quality checks are complete; no material ambiguity, uncovered
requirement, constitution conflict or unresolved architecture finding was found.
The initial completed release history remains intact; the dated DINOv3 amendment
explicitly supersedes only the former DINOv3 exclusion. No extension hooks are
registered. The scoped architecture plan validated before runtime edits.

## Regression

The existing real preparation regression was first changed to require one shared
DINOv3 result. It failed because the old filter excluded the checkpoint. The
implementation removes only that exclusion; DEIMv2 large/xlarge and independent
source extraction retain their checks. Focused, canonical, native, documentation,
paired and review results follow when executed.

## Packaging and local native acceptance

The standard maintainer packager produced four independent archives containing
56 weight checkpoints and the pinned DEIM source (57 payloads). Every previous
payload hash and native Hub metadata record is unchanged. The new DINOv3 checkpoint
and config match the official immutable timm snapshot; no checkpoint was modified.

| Archive | Bytes | SHA-256 |
| --- | ---: | --- |
| `weights-001.tar` | 1888911360 | `7d188773e5ef738b5a9f0b76d20c1f2c3ad17933b98eeb3ae7b272c3b9bcc9ad` |
| `weights-002.tar` | 1815398400 | `9df3198c30282914587c157533a56a2caa45d69343423a67eabfd1b37d3980bb` |
| `weights-003.tar` | 1164830720 | `f2271cad2442968514b428166dfdd1a5487a22a3a4b711a1e10842e14023b857` |
| `deim-noncommercial-001.tar` | 61788160 | `5e8f9f88ff681ad49772d39a86fe06d3fa904680d5bd8b064d85f608e553425d` |

Manifest SHA-256: `8fbd564a1137f1d86945000560b527b20875a0bd9a9c1b23cecc5cb31a8bd042`. Every member and all 20 notice files
in each archive were independently re-read and checked for safe paths, regular-file
structure, uniqueness, byte size and digest. The existing per-file licence/source
mapping was extended for DINOv3; AGPL source directions and DEIM non-commercial
notices were retained. Both distinct DINOv3 agreement versions and the exact model
card are included.

The first packaging attempt found absent DEIM native files and failed closed;
no partial output manifest was emitted. A cache-path retry also lacked them. The
unchanged files were then seeded into task-owned caches from the verified prior
release archives; the standard packager succeeded without upstream retrieval.
No dependency, existing source file or shared service was modified for recovery.

Fresh-cache preparation over loopback HTTP restored all 57 assets from four
archive requests, with zero failures and zero upstream requests. All restored
payload/archive hashes matched. The automatic follow-up skipped another transfer;
the task-owned native settings remained unchanged after initial fixture setup.
With every network host denied, genuine timm DINOv3-small pretrained construction
and a CPU forward produced finite output of shape `[1, 384]`.
These checks establish loading and integrity, not model quality, GPU training or
ClearML publication. No live Artifactory test was performed.

Focused preparation, packaging and Hub/bundle tests passed: 99 tests. The
current source pair resolved normally with approved external source revisions;
installed/source origins and versions agreed (CY 0.44.4, queue 0.1.6). Pip
consistency, queue Ruff/format, strict mypy, both import contracts, CLI help and
544 queue tests passed; seven physical-GPU opt-in tests were deselected.
Repository documentation checks passed; final-pin/source and hosted gates follow.

## Independent asset review and proposed pair

A fresh read-only native reviewer returned **ship** for assets publication. It
independently hashed every archive and payload/config member, checked all notice
bytes and safe inventory, compared previous payload records and retained licence
notices, and fetched the exact timm licence/model card and official Hub metadata.
It also compared complete saved/live Meta website agreement text under whitespace
normalization. No blocking finding was reported. Its verdict explicitly excludes
the subsequent source pin/code release and pending hosted-byte verification.

The proposed CY 0.44.5 source snapshot and latest queue 0.1.6 resolved normally
with the approved external sources in a separate environment. Source/installed
versions, editable origins and dependency constraints agree; pip consistency
passed. Queue Ruff/format, strict mypy, import contracts, CLI help and its complete
ordinary suite passed again: 544 passed, seven physical opt-in tests deselected.
The proposed snapshot contains the exact candidate runtime/test bytes and new
manifest, with the expected project/root-lock release version only.

The master-only native code-release hooks require an independent clean master
delivery checkout rather than moving the original workspace's checked-out master.
Only task-owned changes were transferred there from the isolated worktree.
The owned environment was relocated with its console entrypoints corrected; no
original environment or source dependency revision was upgraded. Local dependency
overrides were already absent in this clean checkout and remain absent for
verification, review and commit.

## Documentation acceptance

Repository README, model-assets/current/project contracts, maintainer licence
procedure, packaged operations tutorial and rendered HTML describe the new
catalogue and pin. The actual `cy-download-weights --help` command and documentation
checker passed. The rendered tutorial was regenerated with the maintained script.
The changed adapter/fixture are outside the maintained mutation selection; selected
policy source/tests and dependency versions are unchanged, so no mutation rerun is
claimed. Existing archive/Hub failure injection remains in the focused and canonical
suites.

The portable usage source was updated in an isolated latest-main clone (collection
0.6.7, commit 914f81b0d27fe6b2888adb2a4462bec47f90a145), preparing patch 0.6.8.
Metadata, four-skill discovery, 73-document Markdown lint and packaged/local-link
checks passed. A fresh read-only reviewer independently repeated those checks,
validated the no-impact architecture and exercised reading-only older-installation
and offline-preparation cases. It returned ship conditional on final CY/snapshot
identity reconciliation. No installed skill copy changed and no live OpenCode or
target-model evaluation is claimed.

## Published snapshot and hosted verification

Published [weights-2026-10-31](https://github.com/BuckanovNikita/clearml-yolo/releases/tag/weights-2026-10-31)
as a complete public, Latest weights snapshot under an annotated tag pointing at
the inspected prior source lineage `b23952c433f2addbbdc981fbed1fd8073602cd01`.
No previous snapshot asset was replaced. GitHub reports all six assets uploaded;
every reported byte size and SHA-256 digest matches the locally verified file.
The actually downloaded public manifest and checksum file are byte-identical.

The production manual preparation path then restored all 57 assets into empty
task-owned native caches through exactly four actual public GitHub archive
downloads. Only GitHub and its release CDN hosts were permitted; original model
hosts were denied. Every downloaded archive and restored checkpoint/source matched
the manifest. Zero preparation failures or upstream attempts occurred. Automatic
follow-up reused its completed receipt without another transfer, and task-owned
native settings remained unchanged after fixture setup. Native timm DINOv3-small
loaded from those hosted/restored bytes and produced finite `[1, 384]` CPU output
with every network host denied. The harness initially supplied the verified
candidate manifest explicitly; the final packaged pin is byte-identical to the
actually downloaded public manifest. A separate fresh-process check verifies the
actual packaged pin without a manifest override.

Final source verification started only after server digests and the actually
downloaded manifest were verified; the full hosted roundtrip completed alongside
it. This separates real hosted-byte/native evidence from metadata and ordinary
regression tests. GPU execution, training, model accuracy and live Artifactory
are outside this asset-publication claim.

The separate actual-pin fresh-process check passed with no manifest override:
57 native assets, automatic receipt reuse, a successful manual local-only retry,
unchanged settings and zero post-import network attempts. Its first harness
assertion incorrectly included denied Ultralytics import-time connectivity probes
(`one.one.one.one`, `dns.google`). Inspection traced these to the SDK's module-level
`ONLINE = is_online()` initialization, not asset retrieval. The corrected harness
initializes that SDK while network remains denied, verifies and clears only those
known probes before preparation, and requires zero subsequent attempts. No
application or dependency source was changed for this harness correction.

Native acceptance commands ran in the asset worktree: `uv run --frozen --no-sync
python .tmp/check-archives.py`, `uv run --frozen --no-sync python .tmp/roundtrip.py
local`, `uv run --frozen --no-sync python .tmp/roundtrip.py hosted`, and
`uv run --frozen --no-sync python .tmp/check-final-pin.py`. Paired checks ran from
the latest queue checkout using the isolated current/proposed environments; final
source canonical/docs checks run in the clean master delivery checkout.

The remote annotated weight tag was read back: tag object
`fcb3d93f164bb5a7b440a3e65dd26920316185e1` dereferences to the inspected lineage
commit `b23952c433f2addbbdc981fbed1fd8073602cd01`. GitHub's Latest endpoint
selects `weights-2026-10-31`; runtime selection remains the immutable packaged pin.

## Final canonical acceptance

The final-pin canonical verifier completed successfully and wrote its normal
success receipt after unchanged before/after input checks. Ruff, strict mypy
(454 source files), Vulture and import-linter passed. The full ordinary pytest
suite passed: 4,571 passed, 30 skipped, 81 deselected, 182 warnings in 1,128.01
seconds. The run included architecture forbidden-edge negative tests and real
CPU distributed regression cases. Skipped/physical opt-in cases are not counted
as successful GPU or remote-service evidence. No hook, verifier or receipt was
bypassed, fabricated or weakened.

## Resumed tool-context verification

After the user requested continuation, the exact canonical invocation did not
reuse the previous valid receipt because the tool session's harness context had
changed. The unchanged verifier fingerprints that environment conservatively.
A second complete canonical run is therefore required before committing; the
first successful run above remains actual evidence, not current receipt reuse.
The fresh [source review](review.md) found no code, data, documentation or
architecture finding and explicitly kept this remaining gate open.

For subsequent release commands the task retains only seven non-secret harness
bookkeeping values from the owned running verifier, so commands execute in that
same checked context if the host session changes again. No credentials are saved,
no environment variable is excluded from the verifier, no receipt is restored or
fabricated, and no check is bypassed. The captured context and invocation helper
remain private task artifacts, outside repository source.

The resumed-context canonical run completed normally and produced its own success
receipt: Ruff, strict mypy, Vulture and import-linter passed; pytest again passed
4,571 tests, with 30 skipped, 81 deselected and 182 warnings in 1,047.89 seconds.
Its normal before/after stability comparison passed. The independent source review
requires no source correction. Current-context canonical, native, paired and
documentation checks are all successful before commit.

## Released identities and final delivery acceptance

The normal contributor commit is
`d2761725835dae6fd5d8605308f9ccbe3029e7dc`. Its normal post-commit hook
created CY [v0.44.5](https://github.com/BuckanovNikita/clearml-yolo/tree/v0.44.5),
release commit `d4f566cbd79839be8d6b0767e11cb349ddf4ab8e`. The release commit
changed only CHANGELOG.md and the project/root-lock version tokens. All normal
contributor/generated-version hooks passed, reusing checked inputs through the
maintained verifier's own matching/attestation rules. No hook was bypassed.

The actual committed CY 0.44.5 source and queue 0.1.6 were installed together
through normal resolution. Source/installed versions, editable origins and
requirements match; pip consistency passed. The final runtime, scripts, tests,
manifest, check configuration and release metadata exactly match the already
tested proposed pair. The final actual-version queue suite passed again:
544 passed, seven physical opt-in tests deselected, 19 warnings in 133.69 seconds;
actual command help passed. Approved external source revisions remain unchanged.

The intended master and annotated v0.44.5 tag were pushed atomically and read
back from GitHub. The tag object is
`c98ac69a5a150e5277bac5f1dccb57632931bbe9`, dereferencing to the exact tested
release commit above. No code GitHub Release, project distribution or registry
publication was created.

The companion portable collection was published as
[v0.6.8](https://github.com/BuckanovNikita/custom-opencode-skills/tree/v0.6.8),
commit `83982d2483bdcdd2488a6252f80909d65d7292e0`, with verified main and
annotated-tag refs. Final parent Markdown lint passed for 73 documents, and
explicit-root local-link checks passed for 73 documents. Fresh native reading
evaluation and independent review remain as recorded above; no installed skill
copy was updated. All architecture, behavior, documentation and release tasks
are reconciled with the final owned diff.

Only task-owned fixture servers and test processes were used; fixture servers
closed normally. Original workspace edits, branch position, services and local
dependency overrides are preserved. Verification archives/logs and native-cache
fixtures remain retained as task evidence. The final documentation-only closure
uses normal hooks and does not require another version.
