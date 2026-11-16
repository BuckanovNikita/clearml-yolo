# Data model

Probe requests carry optional YOLO settings and a resolved TransformConfig alongside
an owner-prepared native ModelConfig. Defaults retain historical standard recipes.
The profile augmentation digest binds native settings plus custom snapshot content;
source-path provenance does not replace content identity.

SearchSettings gains a nonnegative optional free-memory byte reserve, omitted from
ordinary serialized records when zero to preserve historical readers/cache keys.
Capacity remains the existing validated EstimateCase. Selection rejects unusable cases
and chooses a positive backend-valid batch bounded by raw capacity and corpus size.

Acceptance evidence adds raw capacity, chosen batch, measured recipe, memory snapshot,
reserve and two-epoch canonical inputs. Running, failed and completed states remain
separate; incomplete measurements never authorize training.
