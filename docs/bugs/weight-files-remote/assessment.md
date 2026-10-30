# Bug assessment: weight Files remote recovery

- Slug: weight-files-remote (generated from the report)
- Created: 2026-10-30
- Source: pasted user report and repository inspection
- Verdict: valid client defects; deployment cause remains unverified
- Severity: high for installations with restricted original model hosts

## Report and evidence

The manual command reported 48 prepared assets and eight failures: DEIMv2 s/m,
RF-DETR nano/small/medium/large and ResNet-50/101. Final attempts targeted Google
Drive/Storage and download.pytorch.org, raising SSLError or ConnectionError.
Private user paths and identities are intentionally omitted. The user confirms
GHR is a Files remote of https://github.com and GH a VCS remote of that host.
No live Artifactory checks are authorized.

The current URL builder already implements that split. JFrog documents ordinary
remote access at repository-root/artifact-path and VCS commit access via
api/vcs/downloadCommit/repository-key/owner/repository/commit?ext=tar.gz:
[Files remote](https://docs.jfrog.com/artifactory/docs/remote-repositories),
[VCS commit](https://docs.jfrog.com/artifactory/reference/downloadvcscommit).
Do not invent a different Files API or rewrite release paths through GH.

## Reproduction and diagnosis

Inspection and local probes confirm three client problems: archive transport errors
are discarded then reduced to ValueError, so the final report only describes upstream
fallback; archive transfers inherit a fixed 300-second total limit; and the same
ResNet URL/checksum stops matching the bundle when the supported Torchvision version
changes from 0.29.1 to 0.28.0. DEIM IDs in the report exactly match the pin.
Neither those probes nor the user's final fallback log identify the deployment's
first archive failure. TLS, permissions, missing installed manifest, timeout and
cache publication failures remain distinguishable diagnostic outcomes, not proven
remote causes. Tests will reproduce these paths locally without live endpoints.

## Remediation and architecture

Preserve GHR Files-root and GH VCS-root URL contracts. Add verified fixtures for the
actual split, including project release assets and source fallback. Preserve safe,
actionable archive failures through the final bulk report;
report missing or nonmatching pins instead of silently bypassing them. Never expose
raw transport exception text, URL credentials, signed queries or auth tokens.

Allow ResNet reuse across library versions only when the original URL, filename,
checksum-derived identity and backend/preset remain equivalent. Keep DEIM source
revision and other content identity checks strict. Increase the archive-only total
streaming budget to 1800 seconds, configurable by a positive finite
CY_WEIGHTS_DOWNLOAD_TIMEOUT value; keep existing ordinary downloads at 300 seconds.
Use an independent finite archive lock wait based on the configured streaming budget. Preserve
checksums, atomic cache publication and attempt receipts. Ordinary selected-model
resolution keeps its current upstream fallback policy; bulk preparation is release-only.

[Architecture record](architecture.json) maps changed modules to existing inward
import/negative contracts. No dependency, model payload bytes or manifest schema change is required. The user
subsequently requested a new visible weights release with artifacts; publish the
verified tar payloads under weights-2026-10-30, update the manifest release tag and
checksums, and make this the discoverable latest weights release.

## Ownership and sequence

1. Parent records assessment/architecture and validates plan.
2. Bounded implementation agent owns assets/http.py, assets/bundles.py,
   assets/preparation.py, assets/resolver.py, assets/hub.py,
   entrypoints/download_weights.py and focused asset tests.
   Reproduce regressions before changing runtime code; no further delegation.
3. Parent updates repository guidance, generated operations tutorial and task evidence.
   A bounded companion agent updates portable usage sources and checks the paired
   CY/queue release in isolation after runtime integration.
4. Parent runs focused tests, canonical checks and documentation checks.
5. Fresh independent review covers final integrated diff and architecture evidence.
6. Record acceptance, follow ordinary patch release hooks and verify actual paired
   release metadata before authorized pushes. Publish the new weights release explicitly authorized by the user and verify it.

## Documentation and verification

Update README, docs/model-assets.md, current contract navigation, operations tutorial,
and portable clearml-yolo usage/evaluation guidance. Source artifacts live in docs/bugs
because project policy protects installed .specify tooling and completed history.
Use canonical scripts/verify.py and --docs, focused archive/Artifactory fixtures,
paired latest CY/queue installation/integration, and fresh review. No GPU, training,
ClearML publication, or live Artifactory check is needed. Public weight release publication and a hosted
restoration check are explicitly authorized by the later user correction.

## Risks and limits

Streaming budgets and inactivity timeouts must remain explicit; cache integrity and authentication scoping must
remain unchanged. Version-independent matching must not admit a changed checkpoint
or source revision. The final user environment cannot be declared fixed solely from
fixture results; report the verified client behavior and remaining live limitation.

## User corrections during assessment

The user emphasized that bulk downloading was changed yesterday to this repository's
release artifacts. Therefore bulk preparation must not fall back to restricted
Google Drive/Storage, PyTorch or HF hosts after a release failure. It may reuse
validated native caches; otherwise it must use the pinned project release and return
a release-specific failure. Standalone selected-model resolution remains unchanged.
The user also reports not seeing an appropriate release remotely and explicitly
requests a new correct release containing weights. Verify remote state, publish
weights-2026-10-30 with the verified original archives, new pin/manifest/checksums,
clear title/notes and normal latest visibility, then verify download availability.

The existing resolver and Hub adapter gain a backward-compatible `local_only=False`
keyword. Bulk calls use true both before seeding and after restoration, preventing
network fallback without duplicating native cache validation/provenance logic.

## Review amendment: precise timeout semantics

The initial assessment used total-timeout language too strongly. Requests checks
elapsed streaming time only after a completed chunk; continuous slow input or header
processing can exceed that budget while avoiding the separate read-inactivity timeout.
The user did not request a strict wall-clock deadline. Preserve the existing streaming
transport and explicitly document the weaker budget semantics, 10-second connection
and 30-second read-inactivity timeouts, and independent finite lock wait. A hard
deadline would require a separately designed transport/cancellation change; this fix
does not claim one. This resolves the review's alternative to enforce or revise the
contract without changing the verified runtime.
