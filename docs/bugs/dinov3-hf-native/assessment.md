# Bug assessment: authorized official HF DINOv3 cannot initialize DEIM L/X

- Slug: `dinov3-hf-native` (generated for the delegated bug investigation).
- Created: 2026-11-04.
- Source: user report, "Seems like a bug we download original dinov3 from hugging face which i has access. If need redownload and verify that outr released weights are good".
- Verdict: valid unsupported official-source path; medium severity. No released-weight corruption found.

## Symptom and reproduction

Selected DEIM L/X training and batch estimation request original Meta `.pth` bytes.
Authorized official Facebook HF snapshots contain Transformers safetensors instead.
The current validator rejects the verified native format conversion with
`Asset sha256 checksum mismatch`, since converted file bytes differ from the Meta
prefixes. Authenticated fresh downloads confirm the official pinned HF source hashes;
all four released archives and 61 members pass their published checksums. Released
timm DINOv3 Small bytes match fresh upstream exactly and target Faster R-CNN/FCOS,
not DEIM L/X. Redownloading alone cannot satisfy the different serialization hash.

## Proposed remediation

Retain original native local lookup and its checksums. When unavailable, resolve the
pinned official HF source through the existing Hub adapter and convert it in the
DEIM adapter to a distinct native checkpoint. Verify complete source tensors,
architecture shape/dtype/key sets, strict loading and deterministic generated
buffers; atomically cache and reload the result. Preserve source and conversion
provenance explicitly. Original inputs and explicit overrides remain unchanged.
No release manifest or model assets are republished; no dependency revisions change.

## Architecture

[Architecture record](architecture.json) owns the affected module boundaries.
Core asset declarations gain optional typed derivation provenance without effects.
DEIM asset declarations own pinned source identity; conversion adapter owns CPU
Torch/native-source construction, tensor mapping, atomic storage and locks. The
existing Hub adapter retains authenticated network and source-cache ownership.
Execution orchestration routes selected DEIM L/X requests, preserving caller
configuration. Add exact Torch SDK owner edges to the existing import contract;
retain exhaustive architecture/negative-case checks. Existing original source
validation remains authoritative. No application layer gains concrete dependencies.

## Tasks and sequential dependencies

1. Validate architecture planning; capture current failure and source audit.
2. Add focused original-route, authorized fallback, corruption, mapping, cache,
   concurrency and provenance tests; implement the planned adapters/declarations.
3. Run focused tests, strict static checks, existing import/negative-case checks,
   and real CPU source conversion/strict-load/round-trip/consumed-feature parity.
4. Update model-assets documentation and native bug records. Parent updates the
   inspected portable usage reference describing DEIM L/X access behavior.
5. Parent integrates, runs canonical verification/native estimator acceptance,
   obtains fresh independent review and completes architecture acceptance/release.

## Risks and limits

A transformed checkpoint must never be named or validated as original Meta bytes.
Missing authorization and corruption must remain explicit failures. Raw HF tensors
cannot be passed directly to native DEIM. Conversion must not consume GPU or change
random state used by subsequent training. Native training/estimator acceptance and
parent review remain required; CPU mapping tests do not prove these outcomes.
