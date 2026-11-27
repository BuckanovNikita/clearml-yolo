# ADR-0308 · Install the FiftyOne evaluation panel explicitly

The experiment process and the machine serving the FiftyOne App can be separate installations. The server needs a view of the imported evidence and access to the media.

**Decision.** Use `install_evaluation_plugin()` in the server environment to install `@clearml-yolo/evaluation`. Restart a running App after installation. The panel uses stored label IDs and reports when navigating evaluation views. It displays stored full-split AP and precision–recall data when available.

**Consequences.** Opening a subset can show its fixed-threshold evidence. AP and precision–recall remain unavailable there because those curves were recorded for the full split. The extension requires a compatible FiftyOne environment and explicit overwrite for reinstallation.

[Installer and panel](../src/clearml_yolo/adapters/fiftyone/panel.py) · [Extension manifest](../src/clearml_yolo/adapters/fiftyone/plugin/fiftyone.yml) · [Panel behavior](../tests/test_fiftyone_panel.py) · [Live view scenarios](../tests/integration/fiftyone/test_fiftyone_panel_views.py) · [App instructions](../docs/publication.md) · [Change history](https://github.com/BuckanovNikita/clearml-yolo/commit/60ab70bf90fffab7747f0f53ab2e0e67ac08b764)
