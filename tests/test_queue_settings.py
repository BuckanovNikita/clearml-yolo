"""Explicit shared settings and host binding prevent split queue coordination."""

import json
import os
import stat
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path

import pytest


def _configuration(tmp_path: Path, **values: object) -> Path:
    fields = {
        "name": "Shared experiments",
        "root": str(tmp_path / "metadata"),
        "coordination_root": str(tmp_path / "coordination"),
        **values,
    }
    path = tmp_path / "queue.toml"
    path.write_text(
        "[queue]\n" + "\n".join(f"{key} = {json.dumps(value)}" for key, value in fields.items()),
        encoding="utf-8",
    )
    return path


def test_configuration_is_required_even_with_explicit_metadata_override(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    with pytest.raises(ValueError, match="CY_QUEUE_CONFIG"):
        load_queue_settings(tmp_path / "metadata", environ={})
    assert list(tmp_path.iterdir()) == []


def test_resolving_configuration_never_creates_queue_directories(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    path = _configuration(tmp_path)
    settings = load_queue_settings(environ={"CY_QUEUE_CONFIG": str(path)})
    assert settings.name == "Shared experiments"
    assert settings.root == tmp_path / "metadata"
    assert settings.coordination_root == tmp_path / "coordination"
    assert settings.config_path == path
    assert settings.root_source == "config"
    assert list(tmp_path.iterdir()) == [path]


def test_metadata_override_and_agreeing_legacy_environment_are_explicit(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    path = _configuration(tmp_path)
    root = tmp_path / "another-queue"
    settings = load_queue_settings(
        root, environ={"CY_QUEUE_CONFIG": str(path), "CY_QUEUE_ROOT": str(root)}
    )
    assert settings.root == root
    assert settings.root_source == "--root"
    assert settings.coordination_root == tmp_path / "coordination"


def test_legacy_environment_cannot_silently_select_another_queue(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    path = _configuration(tmp_path)
    with pytest.raises(ValueError, match=r"CY_QUEUE_ROOT.*conflict"):
        load_queue_settings(
            environ={"CY_QUEUE_CONFIG": str(path), "CY_QUEUE_ROOT": str(tmp_path / "old")}
        )


@pytest.mark.parametrize(
    "values",
    [
        {"root": "relative"},
        {"coordination_root": "relative"},
        {"name": "   "},
        {"name": "two\nlines"},
        {"name": 42},
        {"typo": "unrecognized"},
    ],
)
def test_invalid_configuration_fails_before_creating_resources(
    tmp_path: Path, values: dict[str, object]
) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    path = _configuration(tmp_path, **values)
    with pytest.raises(ValueError, match=r"configuration|absolute"):
        load_queue_settings(environ={"CY_QUEUE_CONFIG": str(path)})
    assert list(tmp_path.iterdir()) == [path]


def test_config_and_override_paths_must_be_absolute(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    with pytest.raises(ValueError, match="absolute"):
        load_queue_settings(environ={"CY_QUEUE_CONFIG": "queue.toml"})
    path = _configuration(tmp_path)
    with pytest.raises(ValueError, match="absolute"):
        load_queue_settings(Path("relative"), environ={"CY_QUEUE_CONFIG": str(path)})


@pytest.mark.parametrize("filesystem", ["nfs", "nfs4", "cifs", "fuse.sshfs"])
def test_network_mount_is_allowed_for_metadata_but_refused_for_coordination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, filesystem: str
) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    network = tmp_path / "network"
    original = Path.read_text

    def mountinfo(path: Path, *_args: object, **_kwargs: object) -> str:
        if path == Path("/proc/self/mountinfo"):
            return (
                "1 0 0:1 / / rw - ext4 /dev/root rw\n"
                f"2 1 0:2 / {network} rw - {filesystem} server:/queue rw\n"
            )
        return original(path)

    monkeypatch.setattr(Path, "read_text", mountinfo)
    path = _configuration(tmp_path, root=str(network / "metadata"))
    assert load_queue_settings(environ={"CY_QUEUE_CONFIG": str(path)}).root == network / "metadata"
    _configuration(tmp_path, coordination_root=str(network / "locks"))
    with pytest.raises(ValueError, match="host-local"):
        load_queue_settings(environ={"CY_QUEUE_CONFIG": str(path)})


def test_binding_is_shared_readable_and_rejects_conflicting_location(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.coordination import bind_coordination_root

    bootstrap = tmp_path / "bootstrap"
    selected = tmp_path / "selected"
    previous = os.umask(0o077)
    try:
        bind_coordination_root("test-host", selected, bootstrap_root=bootstrap)
    finally:
        os.umask(previous)
    binding = bootstrap / "test-host" / "coordination-root.json"
    before = binding.read_bytes()
    assert stat.S_IMODE(binding.stat().st_mode) == 0o644
    bind_coordination_root("test-host", selected, bootstrap_root=bootstrap)
    assert binding.read_bytes() == before
    with pytest.raises(RuntimeError, match=r"already bound|maintenance"):
        bind_coordination_root("test-host", tmp_path / "other", bootstrap_root=bootstrap)
    assert binding.read_bytes() == before
    assert not (tmp_path / "other").exists()


@pytest.mark.parametrize("record", ["gpu-card.claim.json", "hold-card.json", "evidence-job.json"])
def test_binding_preserves_existing_coordination_evidence(tmp_path: Path, record: str) -> None:
    from clearml_yolo.adapters.queue.coordination import bind_coordination_root, host_directory

    bootstrap = tmp_path / "bootstrap"
    directory = host_directory("test-host", bootstrap)
    evidence = directory / record
    evidence.write_text("retained evidence", encoding="utf-8")
    with pytest.raises(RuntimeError, match=r"maintenance|evidence"):
        bind_coordination_root("test-host", tmp_path / "other", bootstrap_root=bootstrap)
    assert evidence.read_text() == "retained evidence"
    assert not (directory / "coordination-root.json").exists()
    # Continuing to use the existing location remains safe and does not remove evidence.
    bind_coordination_root("test-host", bootstrap, bootstrap_root=bootstrap)
    assert evidence.read_text() == "retained evidence"


def test_binding_rejects_writable_or_corrupt_committed_records(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.coordination import bind_coordination_root

    bootstrap = tmp_path / "bootstrap"
    selected = tmp_path / "selected"
    bind_coordination_root("test-host", selected, bootstrap_root=bootstrap)
    record = bootstrap / "test-host" / "coordination-root.json"
    record.chmod(0o666)
    with pytest.raises(RuntimeError, match="protected"):
        bind_coordination_root("test-host", selected, bootstrap_root=bootstrap)
    record.chmod(0o644)
    record.write_text("broken", encoding="utf-8")
    with pytest.raises(RuntimeError, match="corrupt"):
        bind_coordination_root("test-host", selected, bootstrap_root=bootstrap)


def test_workers_inherit_configured_storage_coordination_and_reject_conflicts(
    tmp_path: Path,
) -> None:
    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.core.queue import WorkerIdentity

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="test-host", boot_id="boot")
    local = tmp_path / "coordination"
    store = NFSQueueStore(tmp_path / "metadata", identity, local_root=local)
    processes = QueueProcesses(store, identity)
    assert processes.pool.root == local / "test-host"
    assert (local / "test-host" / "nfs-transaction.lock").is_file()
    with pytest.raises(ValueError, match="coordination"):
        QueueProcesses(store, identity, local_root=tmp_path / "other")


def test_guardian_uses_frozen_coordination_without_rereading_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.queue.guardian import _Guardian
    from clearml_yolo.adapters.queue.records import GuardianPayload
    from clearml_yolo.core.queue import WorkerIdentity

    identity = WorkerIdentity(owner_uid=os.geteuid(), host_id="test-host", boot_id="boot")
    local = tmp_path / "coordination"
    payload = GuardianPayload(
        job_id="test-job",
        identity=identity,
        queue_root=str(tmp_path / "metadata"),
        local_root=str(local),
        devices=("GPU-test",),
        marker="test-marker",
        ownership_since=0,
        argv=(sys.executable,),
        snapshot_path=str(tmp_path / "snapshot.json"),
        cwd=str(tmp_path),
        project_root=str(tmp_path),
        start_gate=str(tmp_path / "gate"),
    )
    path = tmp_path / "guardian.json"
    path.write_text(payload.model_dump_json(), encoding="utf-8")
    monkeypatch.setenv("CY_QUEUE_CONFIG", str(tmp_path / "missing-config.toml"))
    guardian = _Guardian(path)
    assert guardian.store.local_root == local
    assert (local / "test-host" / "nfs-transaction.lock").is_file()


def test_binding_preserves_administrator_directory_permissions(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.coordination import bind_coordination_root

    local = tmp_path / "coordination"
    local.mkdir()
    local.chmod(0o2770)
    bind_coordination_root("test-host", local, bootstrap_root=tmp_path / "bootstrap")
    assert stat.S_IMODE(local.stat().st_mode) == 0o2770


def test_concurrent_processes_cannot_bind_different_coordination_roots(tmp_path: Path) -> None:
    bootstrap = tmp_path / "bootstrap"
    script = """
import sys
from pathlib import Path
from clearml_yolo.adapters.queue.coordination import bind_coordination_root
try:
    bind_coordination_root('test-host', Path(sys.argv[1]), bootstrap_root=Path(sys.argv[2]))
except RuntimeError:
    raise SystemExit(3)
"""
    with ExitStack() as stack:
        processes = [
            stack.enter_context(
                subprocess.Popen(  # noqa: S603 - fixed script with isolated fixture arguments
                    [sys.executable, "-c", script, str(tmp_path / name), str(bootstrap)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            )
            for name in ("first", "second")
        ]
        for process in processes:
            stdout, stderr = process.communicate(timeout=20)
            assert not stdout
            assert not stderr
        assert sorted(process.returncode for process in processes) == [0, 3]
    record = json.loads((bootstrap / "test-host" / "coordination-root.json").read_text())
    assert record["root"] in {str(tmp_path / "first"), str(tmp_path / "second")}
