"""Default filesystem ownership and explicit destination compatibility."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from loguru import logger

from clearml_yolo.dataset_cache import dataset_cache_root
from clearml_yolo.filesystem import model_weights_path, native_weights_directory, write_path


def _environment() -> dict[str, str]:
    environment = dict(os.environ)
    for name in tuple(environment):
        if name.startswith(("CY_HOME", "XDG_", "YOLO_CONFIG_DIR", "CLEARML_CACHE_DIR",
                            "TRAINS_CACHE_DIR", "MPLCONFIGDIR", "TORCH_HOME", "TORCH_EXTENSIONS",
                            "TORCHINDUCTOR_", "TRITON_CACHE", "CUDA_CACHE", "NUMBA_CACHE",
                            "HF_HOME", "FIFTYONE_", "ETA_")) or name in {"TMPDIR", "TMP", "TEMP"}:
            environment.pop(name)
    environment.pop("PYTHONDONTWRITEBYTECODE", None)
    environment.pop("PYTHONPYCACHEPREFIX", None)
    return environment


def test_dataset_default_uses_cy_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    assert dataset_cache_root(None) == tmp_path / ".cache" / "clearml-yolo" / "datasets"


@pytest.mark.parametrize("value", ["ul://user/project/model", "http://host/model", "s3://bucket/m.pt"])
def test_remote_model_references_keep_their_scheme(value: str) -> None:
    assert model_weights_path(value) == value


def test_explicit_relative_model_destination_stays_relative() -> None:
    assert model_weights_path("./explicit-yolo11n.pt") == Path("./explicit-yolo11n.pt")


def test_bare_models_honor_the_selected_native_weights_directory(tmp_path: Path) -> None:
    checkpoint = tmp_path / "custom.pt"
    checkpoint.write_bytes(b"existing checkpoint")
    with native_weights_directory(tmp_path):
        assert model_weights_path("custom.pt") == checkpoint


@pytest.mark.parametrize("selection", [None, "workspace", "absolute"])
def test_config_entrypoint_initializes_paths_before_dependency_imports(
    tmp_path: Path, selection: str | None
) -> None:
    environment = _environment()
    expected = tmp_path
    if selection:
        expected = tmp_path / "workspace"
        environment["CY_HOME"] = str(expected) if selection == "absolute" else selection
    script = """
import json, os
from pathlib import Path
import clearml_yolo.apps.config_tree
os.chdir(Path.cwd().parent)
print(json.dumps({name: os.environ.get(name) for name in
    ('CY_HOME', 'YOLO_CONFIG_DIR', 'CLEARML_CACHE_DIR', 'MPLCONFIGDIR', 'TORCH_HOME', 'TMPDIR')}))
"""
    result = subprocess.run(  # noqa: S603 - current interpreter and a fixed test script
        [sys.executable, "-c", script], cwd=tmp_path, env=environment,
        check=True, capture_output=True, text=True,
    )
    paths = json.loads(result.stdout)
    assert paths["CY_HOME"] == str(expected)
    assert all(value and Path(value).is_relative_to(expected) for value in paths.values())


def test_explicit_home_destination_warns_once_without_relocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)
    selected = home / "chosen.csv"
    messages: list[str] = []
    handle = logger.add(lambda message: messages.append(str(message)), level="WARNING")
    try:
        assert write_path(selected) == selected
        assert write_path(selected) == selected
    finally:
        logger.remove(handle)
    assert len(messages) == 1
    assert "physically inside user home" in messages[0]


@pytest.mark.parametrize("points_into_home", [False, True])
def test_home_warning_follows_physical_symlink_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, points_into_home: bool
) -> None:
    home = tmp_path / "home"
    outside = tmp_path / "outside"
    home.mkdir()
    outside.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    link = (outside if points_into_home else home) / "link"
    destination = home if points_into_home else outside
    link.symlink_to(destination, target_is_directory=True)
    messages: list[str] = []
    handle = logger.add(lambda message: messages.append(str(message)), level="WARNING")
    try:
        assert write_path(link / "output.csv") == link / "output.csv"
    finally:
        logger.remove(handle)
    assert bool(messages) == points_into_home


def test_explicit_dependency_paths_and_temp_alias_are_preserved(tmp_path: Path) -> None:
    environment = _environment()
    workspace = tmp_path / "workspace"
    selected = tmp_path / "explicit"
    environment.update(CY_HOME=str(workspace), XDG_CACHE_HOME=str(selected), TMP=str(selected),
                       TRAINS_CACHE_DIR=str(selected / "clearml"))
    script = """
import json, os, tempfile
import clearml_yolo.apps.config_tree
from clearml_yolo.dataset_cache import dataset_cache_root
print(json.dumps([str(dataset_cache_root(None)), os.environ['CLEARML_CACHE_DIR'],
                  tempfile.gettempdir()]))
"""
    result = subprocess.run(  # noqa: S603 - current interpreter and a fixed test script
        [sys.executable, "-c", script], cwd=tmp_path, env=environment,
        check=True, capture_output=True, text=True,
    )
    assert json.loads(result.stdout) == [str(selected / "clearml-yolo" / "datasets"),
                                       str(selected / "clearml"), str(selected)]


def test_native_and_publication_startup_writes_stay_in_workspace(tmp_path: Path) -> None:
    script = """
import os, sys
from pathlib import Path
root = Path.cwd().resolve()
def audit(event, args):
    candidates = []
    if event == 'open':
        path, mode, flags = args
        if isinstance(path, (str, bytes)) and (
            (mode and any(flag in mode for flag in 'wax+')) or
            flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        ):
            candidates = [path]
    elif event in ('os.mkdir', 'os.remove', 'os.rmdir'):
        candidates = [args[0]]
    elif event == 'os.rename':
        candidates = list(args[:2])
    for path in candidates:
        if isinstance(path, bytes):
            path = os.fsdecode(path)
        if path != os.devnull and not Path(path).resolve().is_relative_to(root):
            raise RuntimeError('write outside workspace: ' + str(path))
sys.addaudithook(audit)
import clearml_yolo.apps.config_tree
from clearml_yolo.native_runtime import native_runtime
with native_runtime():
    import matplotlib.pyplot
    from clearml.config import get_cache_dir
    assert Path(str(get_cache_dir())).is_relative_to(root)
    from ultralytics import utils
    from ultralytics.data import utils as dataset_utils
    from ultralytics.utils import dist
    assert utils.DATASETS_DIR == dataset_utils.DATASETS_DIR
    assert utils.DATASETS_DIR.is_relative_to(root)
    assert dist.USER_CONFIG_DIR.is_relative_to(root / '.tmp')
    import fiftyone as fo
    assert Path(fo.config.database_dir).is_relative_to(root)
    assert Path(fo.config.default_dataset_dir).is_relative_to(root)
print('startup passed')
"""
    result = subprocess.run(  # noqa: S603 - fixed script with a write audit guard
        [sys.executable, "-c", script], cwd=tmp_path, env=_environment(),
        check=False, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "startup passed" in result.stdout
    assert not list((tmp_path / ".tmp").glob("cy-native-*"))


def test_existing_fiftyone_configuration_remains_a_read_only_input(tmp_path: Path) -> None:
    fake_home = tmp_path / "home"
    configs = fake_home / ".fiftyone"
    configs.mkdir(parents=True)
    selected = tmp_path / "explicit_database"
    source = configs / "config.json"
    source.write_text(json.dumps({"database_dir": str(selected), "database_name": "chosen"}))
    original = source.read_bytes()
    script = """
import json, os, sys
from pathlib import Path
import clearml_yolo.filesystem as policy
policy.Path.home = staticmethod(lambda: Path(sys.argv[1]))
policy.initialize_filesystem()
print(json.dumps([os.environ['FIFTYONE_CONFIG_PATH'], os.environ['FIFTYONE_DATABASE_DIR']]))
"""
    result = subprocess.run(  # noqa: S603 - fixed script and task-owned fixture paths
        [sys.executable, "-c", script, str(fake_home)], cwd=tmp_path, env=_environment(),
        check=True, capture_output=True, text=True,
    )
    assert json.loads(result.stdout) == [str(source), str(selected)]
    assert source.read_bytes() == original


def test_atomic_publication_cleans_partial_output_on_failure(tmp_path: Path) -> None:
    from clearml_yolo.comparison.reinfer import _atomic_text

    output = tmp_path / "predictions.csv"
    output.write_text("existing result\n")
    def fail_serialization() -> None:
        with _atomic_text(output) as stream:
            stream.write("partial result\n")
            raise OSError("disk full")

    with pytest.raises(OSError, match="disk full"):
        fail_serialization()
    assert output.read_text() == "existing result\n"
    assert list(tmp_path.iterdir()) == [output]
