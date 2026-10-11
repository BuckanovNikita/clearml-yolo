"""Pre-import isolation and invocation scratch ownership in fresh processes."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _environment(root: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    environment = dict(os.environ)
    for name in tuple(environment):
        if name.startswith(
            (
                "CY_",
                "XDG_",
                "FIFTYONE_",
                "ETA_",
                "CLEARML_CONFIG",
                "TRAINS_CONFIG",
                "FONTCONFIG",
                "MPLCONFIG",
                "MATPLOTLIBRC",
                "TORCH_",
                "TORCHINDUCTOR_",
                "TRITON_",
                "CUDA_CACHE",
                "HF_",
                "NUMBA_",
            )
        ) or name in {
            "NETRC",
            "AWS_CONFIG_FILE",
            "AWS_SHARED_CREDENTIALS_FILE",
            "BOTO_CONFIG",
            "AWS_WEB_IDENTITY_TOKEN_FILE",
            "AWS_CREDENTIAL_FILE",
            "AWS_DATA_PATH",
        }:
            environment.pop(name)
    environment["CY_HOME"] = str(root)
    environment.update(extra or {})
    return environment


def _run(
    script: str, root: Path, extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed test scripts and fixture-owned paths
        [sys.executable, "-B", "-c", script],
        cwd=root,
        env=_environment(root, extra),
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )


def test_bootstrap_is_stdlib_and_freezes_root_without_changing_home(tmp_path: Path) -> None:
    result = _run(
        """
import os, sys
from pathlib import Path
home = os.environ['HOME']
from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
root = initialize_runtime_environment()
os.chdir(root.parent)
assert initialize_runtime_environment() == root
assert os.environ['HOME'] == home
assert not {'clearml', 'fiftyone', 'matplotlib', 'torch', 'loguru', 'pydantic'} & set(sys.modules)
assert os.environ['CY_GPU_QUEUE_ROOT'] == str(root / 'user-state/clearml-yolo/queue')
""",
        tmp_path,
        {"XDG_STATE_HOME": str(tmp_path / "user-state")},
    )
    assert result.returncode == 0, result.stderr


def test_fontconfig_internal_cache_rejects_outward_symlink(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    project = tmp_path / "project"
    (project / ".cache").mkdir(parents=True)
    (project / ".cache/fontconfig").symlink_to(outside, target_is_directory=True)
    result = _run(
        """
import os
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
before = dict(os.environ)
try:
    initialize_runtime_environment()
except ValueError as error:
    assert 'physical project root' in str(error)
else:
    raise AssertionError('Fontconfig cache escaped the project')
assert dict(os.environ) == before
assert not (Path.cwd() / '.config/fontconfig/fonts.conf').exists()
""",
        project,
    )
    assert result.returncode == 0, result.stderr
    assert list(outside.iterdir()) == []


@pytest.mark.skipif(os.name == "nt", reason="Colons in directory names are POSIX syntax")
def test_eta_default_models_preserve_colon_in_project_path(tmp_path: Path) -> None:
    project = tmp_path / "project:with-colon"
    project.mkdir()
    result = _run(
        """
import os
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import project_configuration_imports
from clearml_yolo.adapters.fiftyone.compatibility import isolated_constants
with project_configuration_imports(), isolated_constants():
    import eta
    expected = str(Path(os.environ['CY_HOME']) / '.cache/eta/models')
    assert eta.config.models_dirs == [expected], eta.config.models_dirs
""",
        project,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("selected", ['["models:one", "models,two"]', "relative-one,relative-two"])
def test_eta_model_selection_survives_repeated_bootstrap_and_fresh_child(
    tmp_path: Path, selected: str
) -> None:
    expected_names = ["models:one", "models,two"] if selected.startswith("[") else [
        "relative-one", "relative-two"
    ]
    result = _run(
        """
import json, os, subprocess, sys
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
expected = [str(Path.cwd() / value) for value in json.loads(os.environ['EXPECTED_MODELS'])]
initialize_runtime_environment()
os.chdir(Path.cwd() / '.config')
initialize_runtime_environment()
assert json.loads(os.environ['CY_ETA_MODELS_DIRS']) == expected
assert 'ETA_MODELS_DIRS' not in os.environ
script = '''
import json, os
from clearml_yolo.adapters.runtime.bootstrap import project_configuration_imports
from clearml_yolo.adapters.fiftyone.compatibility import isolated_constants
with project_configuration_imports(), isolated_constants():
    import eta
    assert eta.config.models_dirs == json.loads(os.environ['EXPECTED_ABSOLUTE_MODELS'])
'''
os.environ['EXPECTED_ABSOLUTE_MODELS'] = json.dumps(expected)
child = subprocess.run([sys.executable, '-B', '-c', script], capture_output=True, text=True)
assert child.returncode == 0, child.stderr
""",
        tmp_path,
        {"ETA_MODELS_DIRS": selected, "EXPECTED_MODELS": json.dumps(expected_names)},
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("selected", ['["valid", 1]', "[null]", "[{}]", "[invalid"])
@pytest.mark.parametrize("selector", ["ETA_MODELS_DIRS", "CY_ETA_MODELS_DIRS"])
def test_eta_rejects_malformed_json_model_selection_without_partial_environment(
    tmp_path: Path, selected: str, selector: str
) -> None:
    result = _run(
        """
import os
from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
before = dict(os.environ)
try:
    initialize_runtime_environment()
except ValueError:
    assert dict(os.environ) == before
else:
    raise AssertionError('Malformed model selection was accepted')
""",
        tmp_path,
        {selector: selected},
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("explicit", [False, True])
def test_eta_windows_drive_paths_reach_real_config_without_colon_split(
    tmp_path: Path, explicit: bool
) -> None:
    result = _run(
        r"""
import json, os
from pathlib import PureWindowsPath
from unittest.mock import patch
from clearml_yolo.adapters.runtime import bootstrap
from clearml_yolo.adapters.fiftyone.compatibility import isolated_constants
bootstrap.initialize_runtime_environment()
expected = [r'C:\project\.cache\eta\models']
os.environ.pop('CY_ETA_MODELS_DIRS')
if os.environ['EXPLICIT_MODELS'] == '1':
    expected = [r'C:\datasets\models', r'D:\model cache\second']
    os.environ['ETA_MODELS_DIRS'] = ';'.join(expected)
# Model Windows filesystem normalization only; the environment handoff and
# ETA's actual public setter/parser execute unchanged on this host.
original_directory = bootstrap._data_directory
def directory(value, launch):
    return PureWindowsPath(value) if value in expected else original_directory(value, launch)
with patch.object(bootstrap.os, 'pathsep', ';'), patch.object(
    bootstrap, '_data_directory', side_effect=directory
):
    bootstrap._install_eta_models(PureWindowsPath(expected[0]), PureWindowsPath(r'C:\project'))
    with bootstrap.project_configuration_imports(), isolated_constants():
        import eta
        assert eta.config.models_dirs == expected, eta.config.models_dirs
        assert eta.ETAConfig({'models_dirs': expected}).models_dirs == expected
assert json.loads(os.environ['CY_ETA_MODELS_DIRS']) == expected
""",
        tmp_path,
        {"EXPLICIT_MODELS": "1" if explicit else "0"},
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(os.name == "nt", reason="Colons in directory names are POSIX syntax")
def test_initial_fiftyone_import_observes_lossless_eta_models(tmp_path: Path) -> None:
    selected = [str(tmp_path / "models:one"), str(tmp_path / "models,two")]
    result = _run(
        """
import json, os
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import project_configuration_imports
from clearml_yolo.adapters.fiftyone.compatibility import isolated_constants
expected = json.loads(os.environ['ETA_MODELS_DIRS'])
home = os.environ['HOME']
with project_configuration_imports(), isolated_constants():
    import fiftyone
    import eta
    assert eta.config.models_dirs == expected
    config_root = Path(os.environ['CY_HOME']) / '.config/fiftyone'
    assert fiftyone.constants.FIFTYONE_CONFIG_DIR == str(config_root)
assert os.environ['HOME'] == home
assert not (Path(home) / '.eta').exists()
assert not (Path(home) / '.fiftyone').exists()
""",
        tmp_path,
        {
            "ETA_MODELS_DIRS": json.dumps(selected),
            "FIFTYONE_DISABLE_SERVICES": "1",
            "HOME": str(tmp_path / "user-home"),
        },
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "failure", ["", "raise RuntimeError('failure')", "raise KeyboardInterrupt()"]
)
def test_scoped_temp_restores_and_cleans_library_leaks(tmp_path: Path, failure: str) -> None:
    result = _run(
        f"""
import os, tempfile
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import (
    initialize_runtime_environment, runtime_environment,
)
initialize_runtime_environment()
before = {{name: os.environ.get(name) for name in ('TMPDIR', 'TMP', 'TEMP')}}
before_temp = tempfile.tempdir
try:
    with runtime_environment() as arena:
        assert Path(tempfile.gettempdir()) == arena
        Path(tempfile.mkstemp()[1]).write_text('library leak')
        with runtime_environment() as nested:
            assert nested == arena
        assert arena.exists()
        {failure or "pass"}
except (RuntimeError, KeyboardInterrupt):
    pass
assert not arena.exists()
assert {{name: os.environ.get(name) for name in before}} == before
assert tempfile.tempdir == before_temp
assert (Path(os.environ['CY_HOME']) / '.cache').exists()
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "name",
    [
        "CLEARML_CONFIG_FILE",
        "TRAINS_CONFIG_PATH",
        "FIFTYONE_BRAIN_CONFIG_PATH",
        "MPLCONFIGDIR",
        "NETRC",
        "AWS_CONFIG_FILE",
        "YOLO_CONFIG_DIR",
    ],
)
def test_external_config_and_symlink_escape_fail_closed(tmp_path: Path, name: str) -> None:
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir()
    (tmp_path / "escape").symlink_to(outside, target_is_directory=True)
    result = _run(
        """
from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
initialize_runtime_environment()
""",
        tmp_path,
        {name: str(tmp_path / "escape" / "private")},
    )
    assert result.returncode != 0
    assert name in result.stderr
    assert "project root" in result.stderr


def test_all_config_selectors_have_local_existing_placeholders(tmp_path: Path) -> None:
    result = _run(
        """
import os
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
root = initialize_runtime_environment()
files = ('CLEARML_CONFIG_FILE', 'TRAINS_CONFIG_FILE', 'FIFTYONE_CONFIG_PATH',
         'FIFTYONE_APP_CONFIG_PATH', 'FIFTYONE_ANNOTATION_CONFIG_PATH',
         'FIFTYONE_EVALUATION_CONFIG_PATH', 'FIFTYONE_BRAIN_CONFIG_PATH',
         'NETRC', 'AWS_CONFIG_FILE', 'AWS_SHARED_CREDENTIALS_FILE',
         'BOTO_CONFIG', 'FONTCONFIG_FILE', 'MATPLOTLIBRC')
for name in files:
    assert Path(os.environ[name]).is_file(), name
    assert Path(os.environ[name]).resolve().is_relative_to(root), name
assert os.environ['AWS_EC2_METADATA_DISABLED'] == 'true'
assert os.environ['AWS_ACCESS_KEY_ID'] == 'explicit-key'
""",
        tmp_path,
        {"AWS_ACCESS_KEY_ID": "explicit-key"},
    )
    assert result.returncode == 0, result.stderr


def test_abandoned_owned_scratch_is_recovered_without_sweeping_unknown_files(
    tmp_path: Path,
) -> None:
    result = _run(
        """
import os
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment
with runtime_environment() as arena:
    print(arena, flush=True)
    (arena / 'leak').write_text('abandoned')
    os._exit(0)
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    abandoned = Path(result.stdout.strip())
    assert abandoned.exists()
    unknown = tmp_path / ".tmp" / "cy-runtime-not-owned"
    unknown.mkdir()
    (unknown / "persistent").write_text("keep")
    result = _run(
        """
from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
initialize_runtime_environment()
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert not abandoned.exists()
    assert (unknown / "persistent").read_text() == "keep"


def test_spawned_worker_owns_separate_arena_and_preserves_parent(tmp_path: Path) -> None:
    result = _run(
        """
import os, subprocess, sys
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment
with runtime_environment() as parent:
    script = ('from clearml_yolo.adapters.runtime.bootstrap import runtime_environment;'
              '\\nwith runtime_environment() as child: print(child)')
    result = subprocess.run([sys.executable, '-B', '-c', script],
                            capture_output=True, text=True, check=True)
    child = Path(result.stdout.strip())
    assert child != parent and child.parent == parent.parent
    assert not child.exists() and parent.exists()
assert not parent.exists()
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr


def test_project_import_boundary_avoids_cwd_matplotlibrc_and_home_clearml(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / "clearml.conf").write_text("THIS IS INVALID HOCON { }")
    (tmp_path / "matplotlibrc").write_text("backend: nonexistent-malicious-backend\n")
    result = _run(
        """
import os
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import (
    runtime_environment, project_configuration_imports,
)
before = Path.cwd()
with runtime_environment():
    with project_configuration_imports():
        import matplotlib
        from clearml import config
        assert Path(matplotlib.matplotlib_fname()).resolve().is_relative_to(before / '.config')
        assert config.get_cache_dir()
    assert Path.cwd() == before
""",
        tmp_path,
        {"HOME": str(home)},
    )
    assert result.returncode == 0, result.stderr


def test_explicit_root_reselection_clears_only_previous_owned_defaults(tmp_path: Path) -> None:
    result = _run(
        """
import os
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import (
    initialize_runtime_environment, runtime_environment,
)
first = initialize_runtime_environment()
second = first / 'second'
second.mkdir()
chosen = second / 'my-netrc'
chosen.write_text('')
os.environ['CY_HOME'] = str(second)
os.environ['NETRC'] = str(chosen)
assert initialize_runtime_environment() == second
assert os.environ['NETRC'] == str(chosen)
assert Path(os.environ['FIFTYONE_CONFIG_PATH']).is_relative_to(second)
with runtime_environment():
    os.environ['CY_HOME'] = str(first)
    try:
        initialize_runtime_environment()
    except ValueError as error:
        assert 'active invocation' in str(error)
    else:
        raise AssertionError('allowed changing active root')
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr


def test_sigterm_unwinds_owned_scratch_and_restores_handler(tmp_path: Path) -> None:
    result = _run(
        """
import os, signal
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment
previous = signal.getsignal(signal.SIGTERM)
try:
    with runtime_environment() as arena:
        print(arena, flush=True)
        os.kill(os.getpid(), signal.SIGTERM)
except SystemExit as error:
    assert error.code == 143
assert signal.getsignal(signal.SIGTERM) == previous
assert not arena.exists()
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr


def test_desktop_xdg_search_lists_are_replaced_with_project_paths(tmp_path: Path) -> None:
    result = _run(
        """
import os
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
root = initialize_runtime_environment()
for name in ('XDG_CONFIG_DIRS', 'XDG_DATA_DIRS', 'XDG_DATA_HOME'):
    assert Path(os.environ[name]).is_relative_to(root)
""",
        tmp_path,
        {"XDG_DATA_DIRS": "/usr/local/share:/usr/share", "XDG_CONFIG_DIRS": "/etc/xdg"},
    )
    assert result.returncode == 0, result.stderr


def test_dead_parent_arena_remains_while_registered_worker_is_live(tmp_path: Path) -> None:
    owner_script = """
import os, time
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment
with runtime_environment() as arena:
    print(arena, flush=True)
    deadline = time.monotonic() + 15
    while not (Path(os.environ['CY_HOME']) / 'proceed').exists():
        if time.monotonic() > deadline:
            raise TimeoutError('test controller did not release owner')
        time.sleep(0.01)
    os._exit(0)
"""
    owner = subprocess.Popen(  # noqa: S603 - fixed test script
        [sys.executable, "-B", "-c", owner_script],
        env=_environment(tmp_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    child: subprocess.Popen[str] | None = None
    try:
        assert owner.stdout is not None
        arena = Path(owner.stdout.readline().strip())
        assert arena.is_dir()
        child_script = """
import sys
from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
initialize_runtime_environment()
print('ready', flush=True)
sys.stdin.read()
"""
        child = subprocess.Popen(  # noqa: S603 - fixed test script
            [sys.executable, "-B", "-c", child_script],
            env=_environment(tmp_path, {"CY_RUNTIME_ARENA": str(arena)}),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert child.stdout is not None
        assert child.stdout.readline().strip() == "ready"
        (tmp_path / "proceed").touch()
        assert owner.wait(timeout=10) == 0
        result = _run(
            "from clearml_yolo.adapters.runtime.bootstrap import "
            "initialize_runtime_environment; initialize_runtime_environment()",
            tmp_path,
        )
        assert result.returncode == 0, result.stderr
        assert arena.exists()
        assert child.stdin is not None
        child.stdin.close()
        assert child.wait(timeout=10) == 0
        result = _run(
            "from clearml_yolo.adapters.runtime.bootstrap import "
            "initialize_runtime_environment; initialize_runtime_environment()",
            tmp_path,
        )
        assert result.returncode == 0, result.stderr
        assert not arena.exists()
    finally:
        for process in (owner, child):
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=10)


def test_outer_scope_restores_bootstrap_owned_environment_and_bytecode_state(
    tmp_path: Path,
) -> None:
    result = _run(
        """
import os, sys
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment
names = ('CY_HOME', 'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'CLEARML_CONFIG_FILE',
         'FIFTYONE_CONFIG_PATH', 'CY_RUNTIME_ARENA', 'PYTHONPYCACHEPREFIX')
before = {name: os.environ.get(name) for name in names}
bytecode_before = sys.pycache_prefix
with runtime_environment() as first:
    pass
assert {name: os.environ.get(name) for name in names} == before
assert sys.pycache_prefix == bytecode_before
with runtime_environment() as second:
    assert first != second
    assert second.parent == first.parent
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr


def test_sdk_config_access_never_opens_seeded_home_files(tmp_path: Path) -> None:
    home = tmp_path / "home"
    for relative in (
        "clearml.conf",
        "trains.conf",
        ".netrc",
        ".boto",
        ".aws/config",
        ".aws/credentials",
        ".config/matplotlib/matplotlibrc",
        ".config/fontconfig/fonts.conf",
    ):
        source = home / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("malicious ambient configuration\n")
    result = _run(
        """
import os, sys
from pathlib import Path
home = Path(os.environ['HOME']).resolve()
def audit(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path = Path(os.fsdecode(args[0])).resolve()
        assert not path.is_relative_to(home), ('ambient config opened', str(path))
sys.addaudithook(audit)
from clearml_yolo.adapters.runtime.bootstrap import (
    runtime_environment, project_configuration_imports,
)
with runtime_environment():
    with project_configuration_imports():
        import matplotlib.pyplot
        import requests.utils
        from clearml.config import get_cache_dir
        import botocore.session
        assert requests.utils.get_netrc_auth('https://example.invalid') is None
        assert get_cache_dir()
        credentials = botocore.session.get_session().get_credentials()
        assert credentials is not None
        assert credentials.access_key == 'explicit-project-key'
assert os.environ['HOME'] == str(home)
""",
        tmp_path,
        {
            "HOME": str(home),
            "AWS_ACCESS_KEY_ID": "explicit-project-key",
            "AWS_SECRET_ACCESS_KEY": "explicit-project-secret",
        },
    )
    assert result.returncode == 0, result.stderr


def test_aws_metadata_credential_sources_are_disabled(tmp_path: Path) -> None:
    result = _run(
        """
import os
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment
with runtime_environment():
    assert os.environ['AWS_EC2_METADATA_DISABLED'] == 'true'
    assert 'AWS_CONTAINER_CREDENTIALS_FULL_URI' not in os.environ
    assert 'AWS_CONTAINER_CREDENTIALS_RELATIVE_URI' not in os.environ
    import botocore.session
    assert botocore.session.get_session().get_credentials() is None
""",
        tmp_path,
        {
            "AWS_CONTAINER_CREDENTIALS_FULL_URI": "http://127.0.0.1:1/metadata",
            "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI": "/metadata",
            "AWS_ACCESS_KEY_ID": "",
            "AWS_SECRET_ACCESS_KEY": "",
            "AWS_SESSION_TOKEN": "",
        },
    )
    assert result.returncode == 0, result.stderr


def test_cleanup_failure_retains_scratch_and_reports_reason(tmp_path: Path) -> None:
    result = _run(
        """
import shutil, warnings
from unittest.mock import patch
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment
with warnings.catch_warnings(record=True) as diagnostics:
    warnings.simplefilter('always')
    with patch('clearml_yolo.adapters.runtime.bootstrap.shutil.rmtree',
               side_effect=PermissionError('injected cleanup access failure')):
        with runtime_environment() as arena:
            (arena / 'leak').write_text('retained for recovery')
assert arena.exists()
assert any('Cannot clean invocation scratch' in str(item.message)
           and 'cleanup access failure' in str(item.message) for item in diagnostics)
shutil.rmtree(arena)
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr


def test_inherited_temp_root_follows_project_selected_arena_parent(tmp_path: Path) -> None:
    result = _run(
        """
import os
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment, invocation_temporary_root
with runtime_environment() as arena:
    assert arena.parent == Path(os.environ['CY_RUNTIME_TEMP_ROOT'])
    assert invocation_temporary_root() == arena
    from clearml_yolo.adapters.storage.filesystem import temporary_root
    assert temporary_root() == arena
""",
        tmp_path,
        {"CY_RUNTIME_TEMP_ROOT": str(tmp_path / "scratch")},
    )
    assert result.returncode == 0, result.stderr


def test_previous_boot_disproves_liveness_but_unknown_identity_fails_closed(tmp_path: Path) -> None:
    result = _run(
        """
import uuid
from clearml_yolo.adapters.runtime.bootstrap import _alive, _owner
owner = _owner('test-token')
assert _alive(owner)
owner['boot'] = str(uuid.uuid4())
assert not _alive(owner)
owner['boot'] = 'unknown'
assert _alive(owner)
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("known_owner", [False, True])
def test_unsafe_descendant_cleanup_marker_preserves_scratch_until_owners_are_proved_dead(
    tmp_path: Path,
    known_owner: bool,
) -> None:
    result = _run(
        f"""
import json, warnings
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment, _owner
with warnings.catch_warnings(record=True) as diagnostics:
    warnings.simplefilter('always')
    with runtime_environment() as arena:
        operation = arena / 'fiftyone-retained'
        operation.mkdir()
        owners = [_owner('descendant-token')] if {known_owner!r} else []
        (operation / '.cy-unsafe-cleanup.json').write_text(json.dumps(
            {{'version': 1, 'reason': 'unproved descendant cleanup', 'owners': owners}}
        ))
        (operation / 'library-leak').write_text('do not remove while process may be alive')
assert arena.exists()
assert any('ownership' in str(item.message) or 'unproved' in str(item.message)
           for item in diagnostics)
print(arena)
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    arena = Path(result.stdout.strip())
    assert arena.exists()
    result = _run(
        "from clearml_yolo.adapters.runtime.bootstrap import "
        "initialize_runtime_environment; initialize_runtime_environment()",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert arena.exists() is not known_owner
    if not known_owner:
        assert "unproved" in result.stderr


def test_scope_setup_failure_rolls_back_partial_library_environment(tmp_path: Path) -> None:
    result = _run(
        """
import os, sys, tempfile
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment
before = dict(os.environ)
bytecode_before = sys.pycache_prefix
temporary_before = tempfile.tempdir
try:
    with runtime_environment():
        raise AssertionError('invalid config unexpectedly admitted')
except ValueError as error:
    assert 'MPLCONFIGDIR' in str(error)
assert dict(os.environ) == before
assert sys.pycache_prefix == bytecode_before
assert tempfile.tempdir == temporary_before
""",
        tmp_path,
        {"MPLCONFIGDIR": str(tmp_path.parent / "outside-matplotlib")},
    )
    assert result.returncode == 0, result.stderr


def test_in_memory_unsafe_cleanup_retains_arena_when_marker_updates_fail(tmp_path: Path) -> None:
    result = _run(
        """
import json, warnings
from pathlib import Path
from unittest.mock import patch
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment, retain_current_arena
with warnings.catch_warnings(record=True) as diagnostics:
    warnings.simplefilter('always')
    with runtime_environment() as arena:
        (arena / '.cy-unsafe-cleanup.json').write_text(json.dumps(
            {'version': 1, 'reason': 'pre-spawn unknown ownership', 'owners': []}
        ))
        with patch.object(Path, 'write_text', side_effect=OSError('marker update failed')):
            retain_current_arena('marker update failed')
assert arena.exists()
assert any('Unsafe process cleanup' in str(item.message) for item in diagnostics)
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("from_config", [False, True])
@pytest.mark.parametrize("model_separator", [",", os.pathsep])
def test_relative_durable_paths_keep_launch_destinations_across_sdk_import_boundary(
    tmp_path: Path,
    from_config: bool,
    model_separator: str,
) -> None:
    workspace = tmp_path / "workspace"
    config_file = workspace / ".config/fiftyone/config.json"
    config_file.parent.mkdir(parents=True)
    config_file.write_text(
        json.dumps(
            {
                "database_dir": "json/database",
                "default_dataset_dir": "json/datasets",
                "dataset_zoo_dir": "~/selected-zoo",
                "model_zoo_dir": "json/models",
            }
        )
    )
    extra = {
        "CY_HOME": str(workspace),
        "HOME": str(tmp_path / "home"),
        "FIFTYONE_CONFIG_PATH": str(config_file),
        "CLEARML_CACHE_DIR": "selected/clearml",
        "ETA_OUTPUT_DIR": "selected/eta-output",
        "ETA_MODELS_DIRS": model_separator.join(("selected/eta-models", "~/eta-models")),
    }
    if not from_config:
        extra.update(
            {
                name: f"selected/{name.lower()}"
                for name in (
                    "FIFTYONE_DATABASE_DIR",
                    "FIFTYONE_DEFAULT_DATASET_DIR",
                    "FIFTYONE_DATASET_ZOO_DIR",
                    "FIFTYONE_MODEL_ZOO_DIR",
                )
            }
        )
    result = _run(
        """
import json, os, sys
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import (
    initialize_runtime_environment, project_configuration_imports,
)
from clearml_yolo.adapters.fiftyone.compatibility import isolated_constants
launch = Path.cwd()
data_names = ('CLEARML_CACHE_DIR', 'FIFTYONE_DATABASE_DIR', 'FIFTYONE_DEFAULT_DATASET_DIR',
              'FIFTYONE_DATASET_ZOO_DIR', 'FIFTYONE_MODEL_ZOO_DIR', 'ETA_OUTPUT_DIR')
settings = json.loads(Path(os.environ['FIFTYONE_CONFIG_PATH']).read_text())
expected = {}
for name in data_names:
    value = os.environ.get(name) or settings[name.removeprefix('FIFTYONE_').lower()]
    expected[name] = Path(value).expanduser().resolve()
model_paths = [Path(value).expanduser().resolve()
               for value in os.environ['ETA_MODELS_DIRS'].split(
                   ',' if ',' in os.environ['ETA_MODELS_DIRS'] else os.pathsep)]
root = initialize_runtime_environment()
assert root != launch
with project_configuration_imports(), isolated_constants():
    import eta
    from eta.core.config import EnvConfig
    from clearml.config import get_cache_dir
    for name, destination in expected.items():
        actual = EnvConfig.parse_path({}, 'directory', env_var=name, default=None)
        assert Path(actual) == destination, (name, actual, str(destination))
        assert destination.is_dir()
        assert not destination.is_relative_to(root)
    assert 'ETA_MODELS_DIRS' not in os.environ
    assert [Path(value) for value in EnvConfig.parse_path_array(
        {'models_dirs': json.loads(os.environ['CY_ETA_MODELS_DIRS'])},
        'models_dirs', env_var='ETA_MODELS_DIRS', default=[])] == model_paths
    assert eta.config.output_dir == str(expected['ETA_OUTPUT_DIR'])
    assert [Path(value) for value in eta.config.models_dirs] == model_paths
    assert Path(str(get_cache_dir())) == expected['CLEARML_CACHE_DIR']
assert Path.cwd() == launch
assert 'fiftyone' not in sys.modules
""",
        tmp_path,
        extra,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("scoped", [False, True])
def test_sdk_configuration_binds_project_root_beyond_scoped_environment_restoration(
    tmp_path: Path,
    scoped: bool,
) -> None:
    result = _run(
        f"""
import os
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import (
    initialize_runtime_environment, project_configuration_imports, runtime_environment,
)
def load_configuration(root):
    Path(os.environ['CLEARML_CONFIG_FILE']).write_text('sdk.audit_project = first\\n')
    from clearml.config import config_obj
    import matplotlib
    assert config_obj.get('sdk.audit_project') == 'first'
    assert Path(matplotlib.get_configdir()) == root / '.config/matplotlib'
if {scoped!r}:
    with runtime_environment():
        root = Path(os.environ['CY_HOME'])
        load_configuration(root)
else:
    root = initialize_runtime_environment()
    with project_configuration_imports():
        load_configuration(root)
os.environ['CY_HOME'] = str(root / 'second')
try:
    initialize_runtime_environment()
except ValueError as error:
    assert 'SDK configuration' in str(error)
    assert 'fresh process' in str(error)
else:
    raise AssertionError('reselected a root with cached SDK state')
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr


def test_direct_sdk_import_after_initialization_prevents_root_reselection(tmp_path: Path) -> None:
    result = _run(
        """
import os
from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
first = initialize_runtime_environment()
import matplotlib
assert matplotlib.get_configdir()
os.environ['CY_HOME'] = str(first / 'second')
try:
    initialize_runtime_environment()
except ValueError as error:
    assert 'SDK configuration' in str(error)
else:
    raise AssertionError('direct cached SDK import did not bind root')
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("inside", [False, True])
@pytest.mark.parametrize("selector", ["AWS_WEB_IDENTITY_TOKEN_FILE", "AWS_CREDENTIAL_FILE"])
def test_optional_aws_credential_source_is_project_bound_and_never_created(
    tmp_path: Path,
    inside: bool,
    selector: str,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    token = workspace / "token.jwt" if inside else tmp_path / "outside-token.jwt"
    result = _run(
        f"""
import os
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
try:
    root = initialize_runtime_environment()
except ValueError as error:
    assert not {inside!r}
    assert {selector!r} in str(error)
else:
    assert {inside!r}
    selected = Path(os.environ[{selector!r}])
    assert selected.is_absolute() and selected.is_relative_to(root)
    assert not selected.exists()
""",
        tmp_path,
        {
            "CY_HOME": str(workspace),
            selector: "token.jwt" if inside else str(token),
        },
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("selection", ["default", "project_list", "outside", "symlink"])
def test_aws_model_search_paths_are_project_bound_and_normalized(
    tmp_path: Path, selection: str
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "ambient-models"
    outside.mkdir()
    (workspace / "escaped-models").symlink_to(outside, target_is_directory=True)
    selected = {
        "default": {},
        "project_list": {"AWS_DATA_PATH": os.pathsep.join(["models-one", "models-two"])},
        "outside": {"AWS_DATA_PATH": str(outside)},
        "symlink": {"AWS_DATA_PATH": "escaped-models"},
    }[selection]
    result = _run(
        f"""
import os
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
try:
    root = initialize_runtime_environment()
except ValueError as error:
    assert {selection!r} in ('outside', 'symlink')
    assert 'AWS_DATA_PATH' in str(error)
else:
    assert {selection!r} in ('default', 'project_list')
    actual = [Path(value) for value in os.environ['AWS_DATA_PATH'].split(os.pathsep)]
    expected = [root / '.config/aws/models'] if {selection!r} == 'default' else [
        root / 'models-one', root / 'models-two',
    ]
    assert actual == expected
    assert all(path.is_absolute() and path.is_dir() for path in actual)
    from botocore.loaders import create_loader
    loader = create_loader(os.environ['AWS_DATA_PATH'])
    assert loader.search_paths[:len(expected)] == [str(path) for path in expected]
""",
        tmp_path,
        {"CY_HOME": str(workspace), **selected},
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("failure", ["lease_error", "lease_missing", "owner_write"])
def test_arena_setup_failure_restores_environment_and_removes_only_new_scratch(
    tmp_path: Path,
    failure: str,
) -> None:
    result = _run(
        f"""
import os, sys, tempfile
from pathlib import Path
from unittest.mock import patch
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment
root = Path(os.environ['CY_HOME'])
temporary = root / '.tmp'
temporary.mkdir()
persistent = temporary / 'unowned-persistent'
persistent.write_text('preserve other tasks')
before = dict(os.environ)
bytecode_before = sys.pycache_prefix
temporary_before = tempfile.tempdir
if {failure!r} == 'owner_write':
    fault = patch.object(Path, 'write_text', side_effect=OSError('owner marker failure'))
elif {failure!r} == 'lease_missing':
    fault = patch('clearml_yolo.adapters.runtime.bootstrap._acquire_lease', return_value=None)
else:
    fault = patch('clearml_yolo.adapters.runtime.bootstrap._acquire_lease',
                  side_effect=OSError('lease access failure'))
with fault:
    try:
        with runtime_environment():
            raise AssertionError('invalid ownership unexpectedly admitted')
    except (OSError, RuntimeError):
        pass
assert dict(os.environ) == before
assert sys.pycache_prefix == bytecode_before
assert tempfile.tempdir == temporary_before
assert list(temporary.iterdir()) == [persistent]
assert persistent.read_text() == 'preserve other tasks'
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
