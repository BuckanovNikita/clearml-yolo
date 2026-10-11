"""ClearML's separate session cache must not bypass project filesystem isolation."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_session_cache_never_reads_or_writes_home_configuration(tmp_path: Path) -> None:
    script = """
import os,sys
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
root=initialize_runtime_environment()
home=Path.home()/'.clearml'
forbidden=[]
def audit(event,args):
    if event == 'open' and isinstance(args[0], (str,bytes)):
        path=Path(os.fsdecode(args[0])).resolve()
        if path.is_relative_to(home):
            forbidden.append(str(path))
            raise AssertionError('ClearML attempted ambient session cache access')
sys.addaudithook(audit)
from clearml_yolo.adapters.clearml.configuration import configure_sdk_state
configure_sdk_state()
from clearml.config.cache import SessionCache
assert Path(SessionCache.SESSION_CACHE_FOLDER).is_relative_to(root)
SessionCache.store_dict('cy-isolation-test', {'project':str(root)})
assert SessionCache.load_dict('cy-isolation-test') == {'project':str(root)}
assert (Path(SessionCache.SESSION_CACHE_FOLDER)/'.session.json').is_file()
assert forbidden == [], forbidden
from botocore.loaders import create_loader
loader=create_loader()
assert str(Path.home()/'.aws/models') not in loader.search_paths
assert str(root/'.config/aws/models') in loader.search_paths
assert loader.load_service_model('s3', 'service-2')['metadata']['serviceId'] == 'S3'
"""
    result = subprocess.run(  # noqa: S603 - fixed script, test-owned workspace
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=dict(os.environ, CY_HOME=str(tmp_path)),
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("scenario", ["roots", "session", "models"])
def test_sdk_state_paths_validate_physical_project_containment(
    tmp_path: Path, scenario: str
) -> None:
    script = """
import os,sys
from pathlib import Path
root=Path(os.environ['CY_HOME'])
root.mkdir()
outside=root.parent/'outside'
outside.mkdir()
scenario=sys.argv[1]
if scenario == 'roots':
    for name in ('.config','.cache'):
        (root/name).symlink_to(outside, target_is_directory=True)
    os.environ['XDG_CONFIG_HOME']=str(root/'selected-config')
    os.environ['XDG_CACHE_HOME']=str(root/'selected-cache')
from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
initialize_runtime_environment()
if scenario != 'roots':
    selected=(root/'.cache/clearml/session' if scenario == 'session'
              else root/'.config/aws/models')
    if selected.exists():
        selected.rmdir()
    selected.parent.mkdir(parents=True, exist_ok=True)
    selected.symlink_to(outside, target_is_directory=True)
from clearml_yolo.adapters.clearml.configuration import configure_sdk_state
if scenario == 'roots':
    configure_sdk_state()
    from clearml.config.cache import SessionCache
    from botocore.loaders import Loader
    assert Path(SessionCache.SESSION_CACHE_FOLDER).resolve().is_relative_to(root)
    assert Path(Loader.CUSTOMER_DATA_PATH).resolve().is_relative_to(root)
else:
    try:
        configure_sdk_state()
    except ValueError as error:
        assert 'physical project root' in str(error)
    else:
        raise AssertionError('SDK state escaped physical project root')
assert list(outside.iterdir()) == []
"""
    result = subprocess.run(  # noqa: S603 - fixed script, test-owned directories
        [sys.executable, "-c", script, scenario],
        cwd=tmp_path,
        env=dict(os.environ, CY_HOME=str(tmp_path / "project")),
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
