# Recipe-bound capacity and acceptance contract

The existing public estimator CLI keeps its default recipe, search and serialization.
Programmatic NativeBatchProbe callers may supply native model settings, YOLO settings
and resolved augmentation. Profiles and child requests must agree. Unresolved or
mutated snapshots fail before launch; custom JSON must execute in the probe.

Synthetic measurement remains conservative: cover the selected native maximum shape
and target amplification, retaining loss/backward, optimizer state, EMA and validation.
Custom DEIM/RF-DETR disable optional native scales/augmentation just as production does.

An optional reserve checks actual free VRAM before launch and while workers run.
Breaches or unavailable telemetry stop owned descendants and fail evidence; they are
not OOM-derived capacity boundaries. Zero reserve preserves ordinary defaults.

The acceptance owner estimates afresh, records raw usable capacity and chooses the
largest backend-valid batch <= min(capacity,160). It checks admission again, trains
exactly two epochs and performs the existing scientific/publication readback checks.
No estimation failure, OOM or interruption selects batch one or retries training.
