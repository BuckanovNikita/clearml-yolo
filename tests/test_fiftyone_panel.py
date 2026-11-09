"""Panel availability; database-backed panel checks live in tests/integration/fiftyone."""

import importlib.util


def test_panel_module_is_available() -> None:
    assert importlib.util.find_spec("clearml_yolo.adapters.fiftyone.panel") is not None
