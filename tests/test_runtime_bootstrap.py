"""Project runtime paths preserve external configuration and retained scratch."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_EXTERNAL_SELECTORS = (
    "HOME",
    "XDG_CONFIG_HOME",
    "XDG_CONFIG_DIRS",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
    "XDG_DATA_DIRS",
    "XDG_STATE_HOME",
    "YOLO_CONFIG_DIR",
    "CLEARML_CONFIG_FILE",
    "CLEARML_CONFIG_PATH",
    "CLEARML_CACHE_DIR",
    "TRAINS_CONFIG_FILE",
    "TRAINS_CONFIG_PATH",
    "TRAINS_CACHE_DIR",
    "FIFTYONE_CONFIG_PATH",
    "FIFTYONE_APP_CONFIG_PATH",
    "FIFTYONE_ANNOTATION_CONFIG_PATH",
    "FIFTYONE_EVALUATION_CONFIG_PATH",
    "FIFTYONE_BRAIN_CONFIG_PATH",
    "FIFTYONE_PLUGINS_DIR",
    "FIFTYONE_DATABASE_DIR",
    "FIFTYONE_DEFAULT_DATASET_DIR",
    "FIFTYONE_DATASET_ZOO_DIR",
    "FIFTYONE_MODEL_ZOO_DIR",
    "ETA_CONFIG_DIR",
    "ETA_MODELS_DIRS",
    "ETA_OUTPUT_DIR",
    "MPLCONFIGDIR",
    "MATPLOTLIBRC",
    "FONTCONFIG_FILE",
    "FONTCONFIG_PATH",
    "TORCH_HOME",
    "TORCH_EXTENSIONS_DIR",
    "TORCHINDUCTOR_CACHE_DIR",
    "TRITON_CACHE_DIR",
    "TRITON_DUMP_DIR",
    "TRITON_OVERRIDE_DIR",
    "CUDA_CACHE_PATH",
    "NUMBA_CACHE_DIR",
    "HF_HOME",
    "HF_HUB_CACHE",
    "HF_ASSETS_CACHE",
    "RF_HOME",
    "ROBOFLOW_HOME",
    "PYTHONPYCACHEPREFIX",
    "KERAS_HOME",
    "NETRC",
    "AWS_CONFIG_FILE",
    "AWS_SHARED_CREDENTIALS_FILE",
    "BOTO_CONFIG",
    "AWS_DATA_PATH",
    "AWS_WEB_IDENTITY_TOKEN_FILE",
    "AWS_CREDENTIAL_FILE",
    "AWS_EC2_METADATA_DISABLED",
    "AWS_CONTAINER_CREDENTIALS_FULL_URI",
    "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
    "TMPDIR",
    "TMP",
    "TEMP",
)


def _environment(root: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    environment = dict(os.environ)
    for name in tuple(environment):
        if name.startswith("CY_"):
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
assert os.environ['XDG_STATE_HOME'] == str(root / 'user-state')
""",
        tmp_path,
        {"XDG_STATE_HOME": str(tmp_path / "user-state")},
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("explicit", [False, True])
def test_initialization_preserves_every_external_selector(tmp_path: Path, explicit: bool) -> None:
    environment = {"SELECTORS": json.dumps(_EXTERNAL_SELECTORS)}
    if explicit:
        environment.update(
            {name: str(tmp_path.parent / "outside" / name) for name in _EXTERNAL_SELECTORS}
        )
        environment["ETA_MODELS_DIRS"] = '["relative:model", "user-selected"]'
        environment["AWS_EC2_METADATA_DISABLED"] = "false"
    result = _run(
        """
import json, os, sys, tempfile
from clearml_yolo.adapters.runtime.bootstrap import (
    initialize_runtime_environment, runtime_environment,
)
names = json.loads(os.environ['SELECTORS'])
if os.environ.get('ETA_MODELS_DIRS') is None:
    for name in names:
        if name != 'HOME':
            os.environ.pop(name, None)
before = {name: os.environ.get(name) for name in names}
bytecode = sys.pycache_prefix
temporary = tempfile.tempdir
initialize_runtime_environment()
with runtime_environment():
    assert {name: os.environ.get(name) for name in names} == before
    assert tempfile.tempdir == temporary
    assert sys.pycache_prefix == bytecode
assert {name: os.environ.get(name) for name in names} == before
assert tempfile.tempdir == temporary
assert sys.pycache_prefix == bytecode
""",
        tmp_path,
        environment,
    )
    assert result.returncode == 0, result.stderr
    assert not (tmp_path.parent / "outside").exists()
    assert not (tmp_path / ".config").exists()
    assert not (tmp_path / ".cache").exists()


@pytest.mark.parametrize("outcome", ["success", "failure", "interrupt", "terminate"])
def test_invocation_retains_explicit_scratch_for_every_outcome(
    tmp_path: Path, outcome: str
) -> None:
    result = _run(
        """
import os, signal
from clearml_yolo.adapters.runtime.bootstrap import invocation_temporary_root, runtime_environment
previous = signal.getsignal(signal.SIGTERM)
try:
    with runtime_environment() as arena:
        assert invocation_temporary_root() == arena
        (arena / 'project.tmp').write_text('retained')
        with runtime_environment() as nested:
            assert nested == arena
        outcome = os.environ['OUTCOME']
        if outcome == 'failure':
            raise RuntimeError('expected')
        if outcome == 'interrupt':
            raise KeyboardInterrupt()
        if outcome == 'terminate':
            os.kill(os.getpid(), signal.SIGTERM)
except (RuntimeError, KeyboardInterrupt, SystemExit):
    pass
assert (arena / 'project.tmp').read_text() == 'retained'
assert invocation_temporary_root() is None
assert signal.getsignal(signal.SIGTERM) == previous
""",
        tmp_path,
        {"OUTCOME": outcome},
    )
    assert result.returncode == 0, result.stderr


def test_old_arenas_and_foreign_files_are_not_scanned_or_recovered(tmp_path: Path) -> None:
    result = _run(
        """
import json, os, socket
from pathlib import Path
from unittest.mock import patch
from clearml_yolo.adapters.runtime.bootstrap import (
    initialize_runtime_environment, runtime_environment,
)
scratch = Path.cwd() / '.tmp'
scratch.mkdir()
records = [None, 'malformed', {'version': 1, 'pid': os.getpid(), 'host': socket.gethostname(),
    'start': '0', 'boot': 'prior-boot', 'token': 'duplicate'},
    {'version': 1, 'pid': os.getpid(), 'host': 'another-host', 'start': '0',
     'boot': 'prior-boot', 'token': 'duplicate'}]
for index, record in enumerate(records):
    arena = scratch / ('cy-runtime-old-' + str(index))
    arena.mkdir()
    (arena / 'foreign.txt').write_text('keep')
    (arena / '.cy-owner.json').write_text(json.dumps(record))
before = {path: path.read_bytes() for path in scratch.rglob('*') if path.is_file()}
with patch.object(Path, 'glob', side_effect=AssertionError('startup scanned scratch')), \
     patch.object(Path, 'rglob', side_effect=AssertionError('startup recursively scanned scratch')):
    initialize_runtime_environment()
    with runtime_environment() as current:
        (current / 'own.tmp').write_text('keep too')
assert all(path.read_bytes() == content for path, content in before.items())
assert (current / 'own.tmp').read_text() == 'keep too'
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("selected", ["relative-temp", "outside"])
def test_explicit_project_temp_root_accepts_uncontained_paths(
    tmp_path: Path, selected: str
) -> None:
    expected = (
        tmp_path / selected
        if selected == "relative-temp"
        else tmp_path.parent / (tmp_path.name + "-outside")
    )
    result = _run(
        """
import os
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment, invocation_temporary_root
with runtime_environment() as arena:
    assert arena.parent == Path(os.environ['EXPECTED_TEMP'])
    assert invocation_temporary_root() == arena
assert arena.is_dir()
""",
        tmp_path,
        {
            "CY_RUNTIME_TEMP_ROOT": selected if selected == "relative-temp" else str(expected),
            "EXPECTED_TEMP": str(expected),
        },
    )
    assert result.returncode == 0, result.stderr


def test_queue_root_is_shared_and_existing_selection_is_unchanged(tmp_path: Path) -> None:
    result = _run(
        """
import os
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment
first = initialize_runtime_environment()
queue = os.environ['CY_GPU_QUEUE_ROOT']
os.environ['CY_HOME'] = str(first / 'other-workspace')
assert initialize_runtime_environment() != first
assert os.environ['CY_GPU_QUEUE_ROOT'] == queue
assert os.environ['XDG_STATE_HOME'] == str(first / 'user-state')
os.environ['CY_GPU_QUEUE_ROOT'] = 'caller-selected/queue'
initialize_runtime_environment()
assert os.environ['CY_GPU_QUEUE_ROOT'] == 'caller-selected/queue'
""",
        tmp_path,
        {"XDG_STATE_HOME": str(tmp_path / "user-state")},
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("outcome", ["success", "failure", "interrupt", "terminate"])
def test_overlapping_subprocesses_keep_distinct_scratch_and_late_children(
    tmp_path: Path, outcome: str
) -> None:
    result = _run(
        """
import os, signal, subprocess, sys
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment
child_script = '''
import sys
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import invocation_temporary_root, runtime_environment
parent = invocation_temporary_root()
with runtime_environment() as child:
    print(child, flush=True)
    assert sys.stdin.readline().strip() == 'finish'
    assert parent.is_dir()
    (parent / 'late-child.tmp').write_text('late write')
    (child / 'own.tmp').write_text('retained child')
'''
try:
    with runtime_environment() as parent:
        process = subprocess.Popen([sys.executable, '-B', '-c', child_script],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert process.stdout is not None
        child = Path(process.stdout.readline().strip())
        assert child != parent and child.parent == parent.parent
        assert child.is_dir()
        outcome = os.environ['OUTCOME']
        if outcome == 'failure':
            raise RuntimeError('expected')
        if outcome == 'interrupt':
            raise KeyboardInterrupt()
        if outcome == 'terminate':
            os.kill(os.getpid(), signal.SIGTERM)
except (RuntimeError, KeyboardInterrupt, SystemExit):
    pass
assert parent.is_dir() and child.is_dir()
stdout, stderr = process.communicate('finish\\n', timeout=15)
assert process.returncode == 0, stderr
assert (parent / 'late-child.tmp').read_text() == 'late write'
assert (child / 'own.tmp').read_text() == 'retained child'
""",
        tmp_path,
        {"OUTCOME": outcome},
    )
    assert result.returncode == 0, result.stderr


def test_child_can_start_runtime_after_parent_invocation_has_finished(tmp_path: Path) -> None:
    result = _run(
        """
import subprocess, sys
from pathlib import Path
from clearml_yolo.adapters.runtime.bootstrap import runtime_environment
child_script = '''
import sys
print('waiting', flush=True)
assert sys.stdin.readline().strip() == 'start'
from clearml_yolo.adapters.runtime.bootstrap import invocation_temporary_root, runtime_environment
parent = invocation_temporary_root()
assert parent is not None
(parent / 'delayed-child.tmp').write_text('started after parent exit')
with runtime_environment() as child:
    print(child, flush=True)
    (child / 'own.tmp').write_text('retained delayed child')
'''
with runtime_environment() as parent:
    process = subprocess.Popen([sys.executable, '-B', '-c', child_script],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert process.stdout is not None
    assert process.stdout.readline().strip() == 'waiting'
stdout, stderr = process.communicate('start\\n', timeout=15)
assert process.returncode == 0, stderr
child = Path(stdout.strip())
assert child != parent and child.parent == parent.parent
assert (parent / 'delayed-child.tmp').read_text() == 'started after parent exit'
assert (child / 'own.tmp').read_text() == 'retained delayed child'
""",
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
