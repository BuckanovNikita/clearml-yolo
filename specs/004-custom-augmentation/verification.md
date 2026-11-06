# Augmentation acceptance closeout, 2026-11-04

## Scope and architecture

This documentation-only resumption reconciles `tasks.md`, `architecture.json` and
this dated receipt. It changes no runtime modules, interfaces, dependency contracts,
configuration examples, SDK ownership or checking tools. The existing module record
and executable import contracts remain authoritative. Its planning validator passed
before these edits. Historical [verification](evidence/verification.md),
[39-case results](evidence/native-smoke.json), [review](evidence/review.md) and
[release receipt](evidence/release.md) remain unchanged.

## Complete native acceptance

The original 15-preset, three-variant matrix now has **45/45 passing scenarios**:
39 retained passes from 2026-10-24 and six fresh DEIMv2-L/X passes on the proposed
CY 0.46 source. This is dated aggregate evidence, not a fresh 45-case invocation
against one source revision. FCOS, full-dataset training, mixed precision and
physical multi-GPU execution are outside this feature's original matrix.

The fresh six used the actual default Hugging Face fallback, pretrained weights,
null canonical `model.train.backbone_weights`, one epoch, batch one, seed zero,
FP32 and the native 640-pixel preset resolution. Each completed 160 optimizer
updates, zero skipped updates, changed parameters, finite published losses and
all 80 held-out images. Downloaded checkpoint hash equality and actual inference
reload passed. The native test selection reported six passes and 57 deselections.

| Preset | Variant | Verified checkpoint SHA-256 |
| --- | --- | --- |
| DEIMv2-L | default | `2f35f752c37eafc5c0b74679b6dd67a89a2d9a4b40baaac4093b2d1d41e46f60` |
| DEIMv2-L | JSON | `2c75f24948e08792d37008d49e97054679223a66be2ce328d81cdf3d765fd974` |
| DEIMv2-L | JSON+Mosaic | `3e15ed0d4f88ca8f1538212340197a4e718f7ff27e27500eba5c526e3995ed64` |
| DEIMv2-X | default | `8ee48ab3252fc71edbc8cfcd7f84a57cade64e2d54643eef3014025bcce84138` |
| DEIMv2-X | JSON | `5f2f1ce05cbcd8daba21700a411939814c3d982ba30cf534afae066d168e25af` |
| DEIMv2-X | JSON+Mosaic | `fa2b7d0c49aea04f5086e0d24ea861adfe7071aa966991bf2ebfda0c450458c2` |

The L variants share initialization
`020a40c391e18e0e92829139b4012c987a16a3460b12c0364326a084c8d5be11`;
the X variants share
`a9dbda79717f5b8e24dbf09a3ef7f75373bffbf3e05bcdde5276e8b743468b83`.
Independent archive verification confirmed exactly 45 unique preset/variant pairs
and one initialization identity per preset across all 15 groups. It rehashed all
45 retained native best checkpoints and every recorded downloaded artifact, and
checked actual downloaded CSV populations: 240 ground-truth image/split pairs and
the same 80 held-out prediction image/split pairs in every scenario.

The earlier six explicit-backbone runs, including one successful readback recovery
after download-cache corruption, remain separate evidence. They are unnecessary
for this acceptance because all six default-fallback cases passed directly.

## Frozen subset equivalence

The historical manifest is
`1d0f169f2202684f8d6bbee543a149330645dc9c28c026fdb3e1dfa51c2379f9`;
the current manifest is
`f2f9c94f1f71bed8833f1e15fc7a01b27372d3eaca054c4a34aaceb1d933d3a7`.
Both self-digests and both prepared CSV hashes validate against retained files.
All 12,568 image records match after removing only their relocated `image_path`:
source/pixel hashes, dimensions, components, split and smoke membership are equal.
All 240 selected images were independently rehashed at both source locations with
zero mismatches and the same 160/40/40 population. Full and smoke CSVs match after
path-basename normalization, including all labels and boxes: 25,860 and 491 rows.

The source annotation CSV bytes differ and are not relabeled identical. Historical
SHA-256 `653e98583cdcacc71c74924e40baa6edd24b3710581742c1ddfddc0037c41c4e`
uses separate ImageId/ClassId columns and 7,095 positive records; current SHA-256
`5c69184e1457596ad5a96e40c1c25d20510c0393f6bc9d653280a40aba5dc839`
uses ImageId_ClassId and all 50,272 image/class records, including empty masks.
Normalizing this schema difference yields identical 7,095 nonempty image/class/RLE
triples, canonical SHA-256
`bd27d41eb40ccb7c07c39ad507750ec6850ae2c60452090c031d0336566ffd51`.
This proves the same frozen subset and annotation semantics without assuming
identical raw source files. No repeated 39-case execution or dataset waiver is needed.

## Weight provenance and cleanup

Published asset receipts bind converter `hf-dinov3-to-deim-v1` to native DEIMv2
revision `1d2ca42171570c713e78fc6a766ec5104b7f4724` and these pinned HF inputs:

| Preset | HF revision | Raw source SHA-256 | Derived native SHA-256 |
| --- | --- | --- | --- |
| L | `114c1379950215c8b35dfcd4e90a5c251dde0d32` | `4610ad75edef83e75afdebf162d148dc628045ea6cbb83d67d4708c709c4f91d` | `8e720f25b9871695253f8392b4089aa27b2f48c22e4b769a7899f3ff886a882d` |
| X | `c93d816fc9e567563bc068f01475bec89cc634a6` | `208146e499dace99e4c9376ddb8a26f77d64c31c46c4dc4b86ff8bc63b0235e2` | `0eef1d947c36b7201439f5506c4b1262e7a1a75ed1de565b4a17418f5080575d` |

The independent audit rehashed retained derived native files; original HF source
identities come from retained published provenance, not a new audit download.
Fresh cleanup retained checkpoints, artifacts and receipts before deleting the
owned invocation; its final listing reported zero matching projects and tasks.
Historical cleanup remains established by the original dated evidence. This audit
did not repeat native training, reload inference or remote deletion.

## Review and verification

Independent reviewer `/root/augmentation_acceptance_review` inspected the native
contract, archived results and source changes since v0.39.0 through `8be76e4`.
Shared augmentation, YOLO augmentation, DEIM/RF-DETR transform bridges, pipeline
examples, Severstal converter and helper bytes are unchanged. Later backend work
includes DDP orchestration, configuration/probe extraction and shared Torchvision
ownership; the historical runs are not presented as fresh verification of those
changes. Their acceptance belongs to the current implementation workflow.

The current canonical `scripts/verify.py` run passed Ruff, mypy, Vulture,
import-linter and pytest: 4,790 passed, 30 skipped, 81 deselected. Architecture
negative cases and CPU-DDP are included in that ordinary suite; deselected native
tests are established separately by the real-run receipts above. The independent
review accepted the original native acceptance closure without new runtime changes.
The task-owned documentation diff was reconciled against the three paths named in
this receipt; unrelated implementation and workflow changes are excluded.

Private reproducible audit artifacts are indexed by these immutable identities;
machine paths and restoration locators remain in the private evidence inventory:

| Artifact | SHA-256 |
| --- | --- |
| Archive/dataset verification `result.json` | `2d08b354e1792aee6bf9bbeb39d07598febb09585cebc99e591630ccf4678dda` |
| Downloaded CSV `populations.json` | `e49a6bdb246c981f1fc2ca457a764e3773db1e02beaad4a20aa12f67a08adebd` |
| Reproduction script `reproduce.py` | `baccce6308fa994a75bfdbbfb582971241b86355aa6c12cc11780563d9653fbe` |
| Population script `populations.py` | `0add91c1055e4be082890214237f7a8a74c9e4465452c35b4322c88b90e8f236` |
| Source comparison `code-impact.json` | `f6e79ec87c4a4bb4b680274317d317f8177f4c2400a0e407c246a235edba379e` |
| Independent `review.md` | `612b0d03ab7acc32891db27491fcd62aa14974aa774df7195ebefeb26b8206a9` |

## Documentation and delivery

README, augmentation/backend contracts, quickstart, examples and portable usage
guidance need no change for this evidence-only reconciliation: no public interface,
configuration or invocation changes here. The [prior release receipt](evidence/release.md)
establishes published CY v0.39.0 and companion v0.4.4, including annotated tag and
remote-ref verification. This closeout does not repeat or rewrite that delivery.
Current source delivery remains governed by the parent release workflow.

T014/T015/T020 are complete. The following final checks passed with exit zero:

- Shared `validate_architecture.py`, `--phase plan`, before documentation changes.
- Shared `validate_architecture.py`, `--phase acceptance`, against this feature's
  reconciled `architecture.json` and the explicit repository root.
- `uv run --frozen --no-sync python scripts/verify.py --docs`, including the new
  receipt and all governed Markdown/local links.
- `git diff --check -- specs/004-custom-augmentation`.

The final evidence/ledger edits were rechecked before handoff. Architecture
validation establishes record consistency; native execution and source quality
are established by the separately inspected evidence and review above.
