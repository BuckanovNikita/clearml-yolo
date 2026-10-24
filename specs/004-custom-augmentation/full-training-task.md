# Independent task: Full Severstal training matrix

**Status**: Awaiting this feature's release and additional explicit user approval.

Train all 15 registered model choices fully on the official Severstal dataset using
the released custom augmentation implementation. Reuse the frozen source identities,
8-connected component conversion, train/validation/test manifests and recipes from
smoke acceptance. Propose final epoch/compute budgets and run matrix for approval
with the release and smoke evidence. Record initialization, effective transforms,
checkpoints, calibrated evaluation and limitations per run.

Do not launch, enqueue or schedule these runs as part of feature implementation,
release hooks or smoke testing. Release completion alone is not authorization.
