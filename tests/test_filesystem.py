"""Project filesystem paths and preserved external configuration."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from loguru import logger

from clearml_yolo.adapters.storage.dataset_cache import dataset_cache_root
from clearml_yolo.adapters.storage.filesystem import model_weights_path, temporary_root, write_path


def test_dataset_default_uses_cy_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    assert dataset_cache_root(None) == tmp_path / ".cache" / "clearml-yolo" / "datasets"


def test_dataset_default_ignores_general_xdg_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path / "workspace"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "home" / ".cache"))
    expected = tmp_path / "workspace" / ".cache" / "clearml-yolo" / "datasets"
    assert dataset_cache_root(None) == expected
    assert dataset_cache_root(tmp_path / "chosen") == tmp_path / "chosen"


@pytest.mark.parametrize(
    "value",
    [
        "ul://user/project/model",
        "http://host/model",
        "s3://bucket/m.pt",
        "yolo11n.pt",
        "./explicit-yolo11n.pt",
        Path("yolo11n.pt"),
    ],
)
def test_model_references_reach_library_without_routing_or_type_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str | Path
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    assert model_weights_path(value) is value
    assert not (tmp_path / ".cache").exists()


def test_existing_checkpoint_string_is_a_local_path_without_cache_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CY_HOME", str(tmp_path))
    old_download = tmp_path / ".cache/ultralytics/weights/model.pt"
    old_download.parent.mkdir(parents=True)
    old_download.write_bytes(b"legacy download")
    assert model_weights_path("model.pt") == "model.pt"
    selected = tmp_path / "model.pt"
    selected.write_bytes(b"native download")
    assert model_weights_path("model.pt") == Path("model.pt")
    assert model_weights_path(str(selected)) == selected
    assert model_weights_path(str(old_download)) == old_download


@pytest.mark.parametrize("selection", [None, "workspace", "absolute"])
def test_initialization_freezes_project_root_without_library_configuration(
    tmp_path: Path, selection: str | None
) -> None:
    environment = dict(os.environ)
    for name in tuple(environment):
        if name.startswith("CY_"):
            environment.pop(name)
    expected = tmp_path
    if selection:
        expected = tmp_path / "workspace"
        environment["CY_HOME"] = str(expected) if selection == "absolute" else selection
    script = """
import json, os
from pathlib import Path
from clearml_yolo.adapters.storage.filesystem import initialize_filesystem
before = dict(os.environ)
initialize_filesystem()
os.chdir(Path.cwd().parent)
from clearml_yolo.adapters.storage.filesystem import cy_home, runs_root, temporary_root
assert all(os.environ.get(name) == value for name, value in before.items() if name != 'CY_HOME')
assert all(name in before for name in os.environ if not name.startswith('CY_'))
print(json.dumps([str(cy_home()), str(runs_root()), str(temporary_root())]))
"""
    result = subprocess.run(  # noqa: S603 - fixed script with task-owned paths
        [sys.executable, "-B", "-c", script],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [
        str(expected),
        str(expected / "runs"),
        str(expected / ".tmp"),
    ]


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


def test_project_temp_directory_honors_explicit_external_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CY_HOME", str(tmp_path / "workspace"))
    selected = tmp_path / "chosen-temp"
    monkeypatch.setenv("CY_RUNTIME_TEMP_ROOT", str(selected))
    assert temporary_root() == selected
    assert selected.is_dir()


def test_project_temp_files_use_invocation_arena_without_changing_global_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tempfile

    from clearml_yolo.adapters.runtime.bootstrap import runtime_environment

    monkeypatch.setenv("CY_HOME", str(tmp_path))
    monkeypatch.delenv("CY_RUNTIME_TEMP_ROOT", raising=False)
    before = tempfile.tempdir
    with runtime_environment() as arena:
        assert temporary_root() == arena
        descriptor, name = tempfile.mkstemp(dir=temporary_root())
        os.close(descriptor)
        retained = Path(name)
        retained.write_text("project temporary file", encoding="utf-8")
        assert tempfile.tempdir == before
    assert retained.read_text(encoding="utf-8") == "project temporary file"


def test_filesystem_does_not_read_or_rewrite_optional_library_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.storage.filesystem import initialize_filesystem

    selected = tmp_path / "outside" / "private-config.json"
    selected.parent.mkdir()
    selected.write_bytes(b"\xff malformed input belongs to the library")
    original = selected.read_bytes()
    monkeypatch.setenv("CY_HOME", str(tmp_path / "workspace"))
    monkeypatch.setenv("FIFTYONE_CONFIG_PATH", str(selected))
    initialize_filesystem()
    assert os.environ["FIFTYONE_CONFIG_PATH"] == str(selected)
    assert selected.read_bytes() == original
    assert not (tmp_path / "workspace" / ".config").exists()


def test_atomic_publication_cleans_partial_output_on_failure(tmp_path: Path) -> None:
    from clearml_yolo.adapters.yolo.reinfer import _atomic_text

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
