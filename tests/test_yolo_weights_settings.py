"""Native weight settings survive process and working-directory changes."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, override

import pytest
from filelock import FileLock

from clearml_yolo.adapters.yolo import assets


class _Settings(dict[str, Any]):  # noqa: FURB189 - SDK settings is a dict subclass
    """Model the SDK's whole-mapping write through its public update boundary."""

    def __init__(self, file_path: Path) -> None:
        super().__init__(json.loads(file_path.read_text(encoding="utf-8")))
        self.file_path = file_path
        self.updates: list[dict[str, Any]] = []

    @override
    def update(self, *args: Any, **kwargs: Any) -> None:
        values = dict(*args, **kwargs)
        self.updates.append(values)
        super().update(values)
        self.file_path.write_text(json.dumps(self), encoding="utf-8")


@pytest.fixture
def native_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"weights_dir": "weights", "clearml": True, "runs_dir": "runs"}),
        encoding="utf-8",
    )
    utilities = SimpleNamespace(SETTINGS=_Settings(path), WEIGHTS_DIR=Path("stale"))
    monkeypatch.setitem(sys.modules, "ultralytics.utils", utilities)
    monkeypatch.chdir(tmp_path)
    return utilities


def test_relative_directory_preserves_latest_disk_values_and_runtime_overrides(
    native_settings: SimpleNamespace, tmp_path: Path
) -> None:
    settings = native_settings.SETTINGS
    settings["clearml"] = False
    latest = {"weights_dir": "weights", "clearml": True, "runs_dir": "new-runs", "new": 42}
    settings.file_path.write_text(json.dumps(latest), encoding="utf-8")

    directory = assets.configure_weights_directory()

    assert directory == tmp_path / "weights"
    assert json.loads(settings.file_path.read_text()) == latest | {"weights_dir": str(directory)}
    assert settings == {"weights_dir": str(directory), "clearml": False, "runs_dir": "runs"}
    assert settings.updates == [{"weights_dir": str(directory)}]
    assert directory == native_settings.WEIGHTS_DIR


def test_already_absolute_directory_repairs_live_state_without_rewriting(
    native_settings: SimpleNamespace, tmp_path: Path
) -> None:
    settings = native_settings.SETTINGS
    path = settings.file_path
    directory = tmp_path / "absolute-cache"
    path.write_text(json.dumps(dict(settings) | {"weights_dir": str(directory)}), encoding="utf-8")
    before = path.read_bytes(), path.stat().st_mtime_ns

    assert assets.configure_weights_directory() == directory
    assert assets.configure_weights_directory() == directory

    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    assert settings.updates == []
    assert settings["weights_dir"] == str(directory)
    assert directory == native_settings.WEIGHTS_DIR


def test_tilde_is_a_literal_directory_component(
    native_settings: SimpleNamespace, tmp_path: Path
) -> None:
    path = native_settings.SETTINGS.file_path
    values = dict(native_settings.SETTINGS) | {"weights_dir": "~/weights"}
    path.write_text(json.dumps(values), encoding="utf-8")
    assert assets.configure_weights_directory() == tmp_path / "~" / "weights"


@pytest.mark.parametrize("contents", ["{broken", "[]", "{}", '{"weights_dir": 4}'])
def test_invalid_settings_fail_with_recovery_guidance_and_no_live_changes(
    contents: str, native_settings: SimpleNamespace
) -> None:
    settings = native_settings.SETTINGS
    before = dict(settings), native_settings.WEIGHTS_DIR
    settings.file_path.write_text(contents, encoding="utf-8")

    with pytest.raises(assets.WeightCacheConfigurationError) as failure:
        assets.configure_weights_directory()

    assert str(settings.file_path) in str(failure.value)
    assert "cy-download-weights" in str(failure.value)
    assert (dict(settings), native_settings.WEIGHTS_DIR) == before
    assert settings.file_path.read_text(encoding="utf-8") == contents
    assert not settings.updates


@pytest.mark.parametrize("failure", ["suppressed", "unrelated-mismatch", "permission"])
def test_persistence_failure_restores_runtime_and_never_publishes_success(
    failure: str, native_settings: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = native_settings.SETTINGS
    before = dict(settings), native_settings.WEIGHTS_DIR

    def failed_update(values: dict[str, str]) -> None:
        dict.update(settings, values)
        if failure == "permission":
            raise PermissionError("write refused")
        if failure == "unrelated-mismatch":
            settings.file_path.write_text(json.dumps(dict(settings) | {"runs_dir": "lost"}))

    monkeypatch.setattr(settings, "update", failed_update)
    with pytest.raises(assets.WeightCacheConfigurationError):
        assets.configure_weights_directory()
    assert (dict(settings), native_settings.WEIGHTS_DIR) == before


def test_missing_settings_file_is_a_configuration_failure(native_settings: SimpleNamespace) -> None:
    native_settings.SETTINGS.file_path.unlink()
    with pytest.raises(assets.WeightCacheConfigurationError, match="cy-download-weights"):
        assets.configure_weights_directory()


def _subprocess(script: str, cwd: Path, config: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed offline scripts and isolated settings
        [sys.executable, "-c", script],
        cwd=cwd,
        env=os.environ | {"YOLO_CONFIG_DIR": str(config)},
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def test_actual_sdk_loads_selected_and_amp_cache_across_cwd_and_fresh_processes(
    tmp_path: Path,
) -> None:
    caller = tmp_path / "caller"
    worker = tmp_path / "worker"
    caller.mkdir()
    worker.mkdir()
    cache = caller / "weights"
    cache.mkdir()
    for name in ("yolo11n.pt", "yolo26n.pt"):
        (cache / name).write_bytes(b"lookup-only checkpoint fixture")
    setup = f"""
import os
import socket
from pathlib import Path
def forbidden(*args, **kwargs):
    raise AssertionError('offline settings lookup attempted network')
socket.socket.connect = forbidden
from ultralytics import utils
from ultralytics.utils import downloads
from clearml_yolo.adapters.yolo.assets import configure_weights_directory
utils.SETTINGS.update({{'weights_dir': 'weights'}})
utils.WEIGHTS_DIR = Path('stale-before-setup')
assert configure_weights_directory() == Path({str(cache)!r})
os.chdir({str(worker)!r})
downloads.safe_download = forbidden
downloads.get_github_assets = forbidden
for name in ('yolo11n.pt', 'yolo26n.pt'):
    assert Path(downloads.attempt_download_asset(name)) == Path({str(cache)!r}) / name
assert utils.WEIGHTS_DIR / 'yolo26n.pt' == Path({str(cache)!r}) / 'yolo26n.pt'
"""
    configured = _subprocess(setup, caller, tmp_path / "config")
    assert configured.returncode == 0, configured.stdout + configured.stderr
    fresh = f"""
import socket
from pathlib import Path
def forbidden(*args, **kwargs):
    raise AssertionError('fresh offline lookup attempted network')
socket.socket.connect = forbidden
from ultralytics import utils
from ultralytics.utils import downloads
downloads.safe_download = forbidden
downloads.get_github_assets = forbidden
assert utils.WEIGHTS_DIR == Path({str(cache)!r})
for name in ('yolo11n.pt', 'yolo26n.pt'):
    assert Path(downloads.attempt_download_asset(name)) == Path({str(cache)!r}) / name
"""
    reloaded = _subprocess(fresh, worker, tmp_path / "config")
    assert reloaded.returncode == 0, reloaded.stdout + reloaded.stderr
    assert not list(worker.iterdir())


def test_concurrent_processes_read_latest_settings_inside_adjacent_lock(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    initial = {"weights_dir": "weights", "clearml": True, "runs_dir": "old"}
    path.write_text(json.dumps(initial), encoding="utf-8")
    script = f"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from clearml_yolo.adapters.yolo.assets import configure_weights_directory
class Settings(dict):
    def update(self, values):
        super().update(values)
        self.file_path.write_text(json.dumps(self))
settings = Settings({initial!r})
settings.file_path = Path({str(path)!r})
sys.modules['ultralytics.utils'] = SimpleNamespace(SETTINGS=settings, WEIGHTS_DIR=Path('old'))
Path(sys.argv[1]).touch()
assert configure_weights_directory() == Path({str(tmp_path / "weights")!r})
"""
    processes: list[subprocess.Popen[str]] = []
    try:
        with FileLock(str(path.with_name(path.name + ".cy-weights.lock")), timeout=5):
            for index in range(2):
                ready = tmp_path / f"ready-{index}"
                processes.append(
                    subprocess.Popen(  # noqa: S603 - fixed isolated concurrency probe
                        [sys.executable, "-c", script, str(ready)],
                        cwd=tmp_path,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                )
            deadline = time.monotonic() + 10
            while not all((tmp_path / f"ready-{index}").exists() for index in range(2)):
                if time.monotonic() >= deadline:
                    pytest.fail("Settings subprocesses did not reach the held lock")
                time.sleep(0.01)
            latest = initial | {"runs_dir": "new", "added": "preserved"}
            path.write_text(json.dumps(latest), encoding="utf-8")
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            assert process.returncode == 0, stdout + stderr
        assert json.loads(path.read_text()) == latest | {"weights_dir": str(tmp_path / "weights")}
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=5)


def test_import_and_discovery_do_not_configure_settings(tmp_path: Path) -> None:
    script = """
import sys
from types import SimpleNamespace
from clearml_yolo.adapters.yolo import assets
def forbidden(*args, **kwargs):
    raise AssertionError('inspection configured settings')
assets.configure_weights_directory = forbidden
sys.modules['ultralytics.utils'] = SimpleNamespace(SETTINGS={'weights_dir': 'relative'})
def download(file, repo='ultralytics/assets', release='fixture'):
    raise AssertionError('discovery downloaded weights')
sys.modules['ultralytics.utils.downloads'] = SimpleNamespace(
    GITHUB_ASSETS_NAMES={'yolo11n.pt'}, attempt_download_asset=download)
sys.modules['ultralytics.utils.checks'] = SimpleNamespace(
    check_yolov5u_filename=lambda filename, verbose=False: filename)
assert assets.pretrained_asset('yolo11n.pt').native_cache.name == 'relative'
"""
    result = _subprocess(script, tmp_path, tmp_path / "config")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not list(tmp_path.iterdir())
