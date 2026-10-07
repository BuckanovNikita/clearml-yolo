# Data model

ResultContext, PRCurve, ConfusionMatrixPayload and ModelIdentity remain unchanged.
The result bundle owns a display-slot registry keyed by stable model identity and split.
It retains the original provenance IDs privately and assigns readable series labels.
Repeated checkpoint/split evaluations reuse labels; unrelated collisions receive stage
and ordinal suffixes. Rendering receives an optional display label, not another schema.
