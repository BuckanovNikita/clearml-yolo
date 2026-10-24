# Research and approved decisions

- Inspected installed Ultralytics 8.4.165 and published 8.4.184 wheel: serialized
  transform lists already work, but native augmentation remains independent. The
  newer worker seed behavior does not implement full Compose JSON/conflict ownership.
- Shared project-owned preprocessing is required to retain empty crops, standard
  bbox policies, RGB semantics, final sizing and all-backend mosaic behavior.
- Installed Albumentations 2.0.8 Mosaic passed in-memory JSON roundtrip and class/instance
  identity checks, including empty primary and all-empty donor scenarios.
- Root Hydra model/profile specialization was verified with in-memory composition.
  Nested specialization cannot resolve the outer model selection reliably.
- DEIM has collate mixing/multiscale and affine inside native mosaic; RF-DETR has
  decoder resizing, dataset jitter, batch multiscale and optional GPU augmentation.
- Official Severstal has semantic class masks, not detector boxes. User selected
  8-connected component boxes and all-preset smoke acceptance. Full training is deferred.
- Kaggle credential access is a runtime prerequisite. Initial legacy/API checks failed;
  user completed OAuth and a scoped subprocess token successfully listed official files.
