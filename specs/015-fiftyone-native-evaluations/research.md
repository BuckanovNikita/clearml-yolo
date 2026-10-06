# Research decisions

- Use FiftyOne DetectionEvaluation/DetectionResults extension APIs, not COCO rematching.
- Imported config reports method digital_metrics. Importable class paths and explicit
  deserialization are persistence contracts.
- A canonical confusion association claims TP GT first, then one wrong-class prediction
  per unclaimed GT. Original many-to-one evidence remains in dm_matches.
- The builtin panel omits wrong-class FP/FN in headlines and uses broad label-based
  matrix clicks. A project-owned subclass corrects these without patching dependencies.
- NativeModelEvaluationView has no PR slot: package a companion Python report panel.
- Subset APIs do not slice IoUs: override array handling and restore all state; retain
  native GT-or-FP subset membership. Full-split AP is unavailable for restricted subsets.
- Native overwrite cleanup can erase new fields: clean old task evaluations before
  rewriting detections. Recreate all references because publication recreates IDs.
- Plugin cached decorators capture base methods: explicitly override cached entrypoints.
- Upstream APIs inspected in the installed environment and official documentation:
  https://docs.voxel51.com/api/fiftyone.utils.eval.detection.html
  https://docs.voxel51.com/plugins/developing_plugins.html
