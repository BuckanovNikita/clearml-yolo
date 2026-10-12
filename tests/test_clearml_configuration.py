"""Native SDK configuration discovery remains intact after project initialization."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("explicit", [False, True])
def test_clearml_discovers_home_or_explicit_configuration(tmp_path: Path, explicit: bool) -> None:
    home = tmp_path / "home"
    home.mkdir()
    config = tmp_path / "external.conf" if explicit else home / "clearml.conf"
    cache = tmp_path / "selected-cache"
    config.write_text(f'sdk.storage.cache.default_base_dir: "{cache}"\n')
    environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith(("CLEARML_", "TRAINS_", "AWS_", "XDG_"))
    }
    environment.update(HOME=str(home), CY_HOME=str(tmp_path / "project"))
    if explicit:
        environment["CLEARML_CONFIG_FILE"] = str(config)
    script = """
import os
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
before = dict(os.environ)
initialize_runtime_environment()
for key in ('CLEARML_CONFIG_FILE', 'CLEARML_CACHE_DIR', 'XDG_CONFIG_HOME', 'AWS_CONFIG_FILE'):
    assert os.environ.get(key) == before.get(key), key
from clearml.config import get_cache_dir
from clearml.config.cache import SessionCache
assert str(get_cache_dir()) == os.environ['EXPECTED_CACHE']
assert Path(SessionCache.SESSION_CACHE_FOLDER).expanduser() == Path.home()/'.clearml'
from botocore.loaders import create_loader
loader = create_loader()
assert str(Path.home()/'.aws/models') in loader.search_paths
assert loader.load_service_model('s3', 'service-2')['metadata']['serviceId'] == 'S3'
"""
    result = subprocess.run(  # noqa: S603 - isolated SDK discovery, no credentials/network
        [sys.executable, "-c", script], cwd=tmp_path,
        env=environment | {"EXPECTED_CACHE": str(cache)}, capture_output=True,
        text=True, timeout=45, check=False,
    )
    assert result.returncode == 0, result.stderr
