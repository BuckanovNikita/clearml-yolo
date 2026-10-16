"""Explicit shared settings and host binding prevent split queue coordination."""

import json
import os
import pwd
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
        load_queue_settings(tmp_path / "metadata", environ={"HOME": str(tmp_path)})
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("xdg", [None, "", "relative", "absolute"])
def test_default_configuration_uses_the_users_config_directory(
    tmp_path: Path, xdg: str | None
) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    environment = {"HOME": str(tmp_path / "home")}
    config_home = tmp_path / "home" / ".config"
    if xdg is not None:
        environment["XDG_CONFIG_HOME"] = str(tmp_path / "custom") if xdg == "absolute" else xdg
    if xdg == "absolute":
        config_home = tmp_path / "custom"
    directory = config_home / "clearml-yolo"
    directory.mkdir(parents=True)
    source = _configuration(tmp_path)
    path = directory / "queue.toml"
    path.write_bytes(source.read_bytes())
    settings = load_queue_settings(environ=environment)
    assert settings.config_path == path
    assert settings.root == tmp_path / "metadata"
    assert not settings.root.exists()
    assert not settings.coordination_root.exists()


def test_explicit_configuration_wins_over_default_and_empty_override_uses_default(
    tmp_path: Path,
) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    source = _configuration(tmp_path)
    config_home = tmp_path / "config"
    default = config_home / "clearml-yolo"
    default.mkdir(parents=True)
    path = _configuration(default, name="User queue")
    environment = {"XDG_CONFIG_HOME": str(config_home), "CY_QUEUE_CONFIG": str(source)}
    assert load_queue_settings(environ=environment).name == "Shared experiments"
    environment["CY_QUEUE_CONFIG"] = ""
    assert load_queue_settings(environ=environment).config_path == path


def test_missing_user_configuration_explains_setup_without_creating_files(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    selected = tmp_path / ".config" / "clearml-yolo" / "queue.toml"
    with pytest.raises(ValueError, match="Queue configuration is missing") as failure:
        load_queue_settings(environ={"HOME": str(tmp_path)})
    message = str(failure.value)
    assert str(selected) in message
    for field in ("[queue]", "name", "root", "coordination_root", "CY_QUEUE_CONFIG"):
        assert field in message
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("missing", ["name", "root", "coordination_root"])
def test_each_user_must_fill_all_required_fields(tmp_path: Path, missing: str) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    config_home = tmp_path / ".config"
    directory = config_home / "clearml-yolo"
    directory.mkdir(parents=True)
    path = _configuration(directory)
    path.write_text(
        "\n".join(
            line for line in path.read_text().splitlines() if not line.startswith(missing + " =")
        )
    )
    with pytest.raises(ValueError, match=r"expected.*name, root and coordination_root"):
        load_queue_settings(environ={"XDG_CONFIG_HOME": str(config_home)})
    assert list(directory.iterdir()) == [path]


def test_two_users_can_select_the_same_queue_from_their_own_files(tmp_path: Path) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    settings = []
    for user in ("alice", "bob"):
        home = tmp_path / user
        directory = home / ".config" / "clearml-yolo"
        directory.mkdir(parents=True)
        _configuration(
            directory, root=str(tmp_path / "shared"), coordination_root=str(tmp_path / "locks")
        )
        settings.append(load_queue_settings(environ={"HOME": str(home)}))
    assert settings[0].config_path != settings[1].config_path
    assert settings[0].root == settings[1].root == tmp_path / "shared"
    assert settings[0].coordination_root == settings[1].coordination_root == tmp_path / "locks"
    assert not settings[0].root.exists()
    assert not settings[0].coordination_root.exists()


@pytest.mark.parametrize("home", [None, ""])
def test_missing_home_environment_uses_account_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, home: str | None
) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    account = pwd.struct_passwd(("test-user", "x", os.getuid(), os.getgid(), "", str(tmp_path), ""))
    monkeypatch.setattr(pwd, "getpwuid", lambda _uid: account)
    monkeypatch.setenv("HOME", "")
    directory = tmp_path / ".config" / "clearml-yolo"
    directory.mkdir(parents=True)
    path = _configuration(directory)
    environment = {} if home is None else {"HOME": home}
    assert load_queue_settings(environ=environment).config_path == path


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
    with pytest.raises(ValueError, match=r"host-local|NFS coordination"):
        load_queue_settings(environ={"CY_QUEUE_CONFIG": str(path)})


def _mountinfo(monkeypatch: pytest.MonkeyPatch, content: str) -> None:
    original = Path.read_text

    def read(path: Path, *args: object, **kwargs: object) -> str:
        if path == Path("/proc/self/mountinfo"):
            return content
        return original(path)

    monkeypatch.setattr(Path, "read_text", read)


@pytest.mark.parametrize("filesystem", ["nfs", "nfs4"])
@pytest.mark.parametrize("locking", ["flock", "all"])
def test_nfs_coordination_accepts_effective_hard_host_local_flock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, filesystem: str, locking: str
) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    _mountinfo(
        monkeypatch, f"1 0 0:1 / / rw - {filesystem} server:/queue rw,hard,local_lock={locking}\n"
    )
    path = _configuration(tmp_path)
    settings = load_queue_settings(environ={"CY_QUEUE_CONFIG": str(path)})
    assert settings.coordination_root == tmp_path / "coordination"
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize(
    "options",
    [
        "rw",
        "rw,hard",
        "rw,hard,local_lock=none",
        "rw,hard,local_lock=posix",
        "rw,local_lock=flock",
        "rw,soft,local_lock=all",
        "rw,softerr,local_lock=flock",
        "rw,hard,soft,local_lock=all",
        "rw,hard,softerr,local_lock=all",
        "rw,hard,nosharecache,local_lock=flock",
        "rw,hard,local_lock=all,local_lock=none",
    ],
)
def test_nfs_coordination_rejects_unsafe_effective_options(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, options: str
) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    # Options before the separator cannot override the effective superblock options.
    _mountinfo(
        monkeypatch, f"1 0 0:1 / / rw,hard,local_lock=flock - nfs4 server:/queue {options}\n"
    )
    path = _configuration(tmp_path)
    with pytest.raises(ValueError, match=r"NFS coordination.*hard.*local_lock"):
        load_queue_settings(environ={"CY_QUEUE_CONFIG": str(path)})
    assert list(tmp_path.iterdir()) == [path]


def test_coordination_validation_uses_longest_decoded_mountpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    mount = tmp_path / "shared queue"
    encoded = str(mount).replace(" ", r"\040")
    _mountinfo(
        monkeypatch,
        "1 0 0:1 / / rw - ext4 /dev/root rw\n"
        f"2 1 0:2 / {encoded} rw - nfs4 server:/queue rw,hard,local_lock=flock\n"
        f"3 2 0:3 / {encoded}/unsafe rw - nfs4 server:/unsafe rw,hard,local_lock=none\n",
    )
    path = _configuration(tmp_path, coordination_root=str(mount / "safe"))
    assert (
        load_queue_settings(environ={"CY_QUEUE_CONFIG": str(path)}).coordination_root
        == mount / "safe"
    )
    _configuration(tmp_path, coordination_root=str(mount / "unsafe" / "locks"))
    with pytest.raises(ValueError, match="NFS coordination"):
        load_queue_settings(environ={"CY_QUEUE_CONFIG": str(path)})


@pytest.mark.parametrize(
    "record", ["malformed", "1 0 0:1 / / rw - nfs4", "1 0 0:1 / / rw - nfs4 server:/queue"]
)
def test_incomplete_mount_records_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, record: str
) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    _mountinfo(monkeypatch, record)
    path = _configuration(tmp_path)
    with pytest.raises(RuntimeError, match="Cannot determine"):
        load_queue_settings(environ={"CY_QUEUE_CONFIG": str(path)})
    assert list(tmp_path.iterdir()) == [path]


def test_cli_requires_filled_default_settings_but_help_needs_no_configuration(
    tmp_path: Path,
) -> None:
    environment = dict(os.environ, HOME=str(tmp_path), XDG_CONFIG_HOME="", CY_QUEUE_CONFIG="")
    environment.pop("CY_QUEUE_ROOT", None)
    command = [sys.executable, "-c", "from clearml_yolo.entrypoints.queue import main; main()"]

    def run(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603 - fixed CLI and isolated user configuration
            [*command, *arguments],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )

    assert run("--help").returncode == 0
    missing = run("list")
    assert missing.returncode != 0
    assert "Create and fill [queue]" in missing.stderr
    assert "coordination_root" in missing.stderr
    assert list(tmp_path.iterdir()) == []
    directory = tmp_path / ".config" / "clearml-yolo"
    directory.mkdir(parents=True)
    path = _configuration(directory)
    configured = run("config", "--json")
    assert configured.returncode == 0, configured.stderr
    assert json.loads(configured.stdout)["config_path"] == str(path)
    assert list(directory.iterdir()) == [path]


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
