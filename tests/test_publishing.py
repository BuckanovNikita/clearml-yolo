"""A disabled publisher has no runtime dependencies or side effects."""

import subprocess
import sys
from pathlib import Path

import pytest
from hydra import compose, initialize_config_module
from hydra_zen import store


def test_disabled_publisher_does_not_import_fiftyone(tmp_path: Path) -> None:
    code = """
import sys
from pathlib import Path
from clearml_yolo.publishing import create_publisher
from clearml_yolo.publishing.models import FiftyOneConfig, PublicationRequest
publisher = create_publisher(FiftyOneConfig(enabled=False))
publisher.preflight()
request = PublicationRequest(task_id='test', ground_truth=Path('missing.csv'))
assert publisher.publish(request) is None
assert not any(name == 'fiftyone' or name.startswith('fiftyone.') for name in sys.modules)
"""
    result = subprocess.run(  # noqa: S603 - fixed interpreter and test-owned source
        [sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("command", ["pipeline", "predict", "metrics"])
def test_publishing_enabled_by_default_and_can_be_disabled(command: str) -> None:
    import clearml_yolo.configs  # noqa: F401

    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        default = compose(config_name=command)
        disabled = compose(config_name=command, overrides=["fiftyone.enabled=false"])
    assert default.fiftyone.enabled is True
    assert default.fiftyone.dataset_prefix == "clearml-yolo"
    assert disabled.fiftyone.enabled is False


@pytest.mark.parametrize("command", ["train", "val", "compare", "report", "ground_truth"])
def test_other_commands_do_not_enable_publishing(command: str) -> None:
    import clearml_yolo.configs  # noqa: F401

    store.add_to_hydra_store(overwrite_ok=True)
    with initialize_config_module(config_module="hydra_zen.wrapper", version_base="1.3"):
        config = compose(config_name=command)
    assert "fiftyone" not in config
