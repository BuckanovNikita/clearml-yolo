"""FiftyOne configuration and constants remain governed by the installed library."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("explicit", [False, True])
def test_fiftyone_uses_native_config_and_constants(tmp_path: Path, explicit: bool) -> None:
    home = tmp_path / "home"
    config = tmp_path / "external.json" if explicit else home / ".fiftyone/config.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text('{"default_dataset_dir": "native-data-selection"}')
    environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith(("FIFTYONE_", "ETA_", "CY_ETA_"))
    }
    environment.update(
        HOME=str(home), CY_HOME=str(tmp_path / "project"), FIFTYONE_DISABLE_SERVICES="1"
    )
    if explicit:
        environment["FIFTYONE_CONFIG_PATH"] = str(config)
    script = """
import os, sys
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
before = dict(os.environ)
initialize_runtime_environment()
assert os.environ.get('FIFTYONE_CONFIG_PATH') == before.get('FIFTYONE_CONFIG_PATH')
assert os.environ.get('FIFTYONE_DATABASE_DIR') == before.get('FIFTYONE_DATABASE_DIR')
import fiftyone as fo
from fiftyone import constants as c
assert Path(fo.config.default_dataset_dir) == Path.cwd()/'native-data-selection'
assert c.FIFTYONE_CONFIG_DIR == str(Path.home()/'.fiftyone')
assert Path(c.DEFAULT_DB_DIR).is_relative_to(Path.home()/'.fiftyone')
assert not any(type(f).__name__ == '_ConstantsFinder' for f in sys.meta_path)
"""
    result = subprocess.run(  # noqa: S603 - test-owned HOME, native services disabled
        [sys.executable, "-c", script], cwd=tmp_path, env=environment,
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stderr
