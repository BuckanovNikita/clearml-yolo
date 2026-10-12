"""Stdlib-only pre-import configuration and invocation scratch ownership.

Importing this module is inert. Entry points install the environment explicitly
before loading SDKs; spawned workers inherit its persistent selections.
"""

import json
import os
import shutil
import signal
import socket
import sys
import tempfile
import threading
import uuid
import warnings
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType
from typing import TypedDict
from xml.sax.saxutils import escape

_LOCK = threading.RLock()
_ARENA_ENV = "CY_RUNTIME_ARENA"
_OWNER_FILE = ".cy-owner.json"


@dataclass
class _State:
    root: Path | None = None
    sdk_root: Path | None = None
    active: tuple[int, Path] | None = None
    installed: dict[str, str] = field(default_factory=dict)
    participant_leases: dict[tuple[int, Path], int] = field(default_factory=dict)
    retained: dict[Path, str] = field(default_factory=dict)


_STATE = _State()


@dataclass
class _RuntimeScope:
    environment: dict[str, str]
    root: Path | None
    installed: dict[str, str]
    active: tuple[int, Path] | None
    temporary: str | None
    bytecode: str | None
    changed: set[str] = field(default_factory=set)
    initialized_root: Path | None = None
    arena: Path | None = None
    created: bool = False
    lease: int | None = None
    previous_handler: int | Callable[[int, FrameType | None], object] | None = None


class _Owner(TypedDict):
    version: int
    pid: int
    start: str
    boot: str
    host: str
    token: str


def _identity(pid: int) -> str:
    """Linux start time distinguishes a recycled PID; other hosts fail closed."""
    try:
        # comm may contain spaces and parentheses, so split after its last ')'.
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]
    except (FileNotFoundError, ProcessLookupError):
        return ""
    except (OSError, IndexError):
        return "unknown"


def _boot() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return "unknown"


def _owner(token: str) -> _Owner:
    return {
        "version": 1,
        "pid": os.getpid(),
        "start": _identity(os.getpid()),
        "boot": _boot(),
        "host": socket.gethostname(),
        "token": token,
    }


def _read_owner(source: Path) -> _Owner | None:
    try:
        value: object = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return _parse_owner(value)


def _parse_owner(value: object) -> _Owner | None:
    if not isinstance(value, dict) or set(value) != {
        "version",
        "pid",
        "start",
        "boot",
        "host",
        "token",
    }:
        return None
    if value["version"] != 1 or type(value["pid"]) is not int or value["pid"] < 1:
        return None
    if not all(isinstance(value[key], str) for key in ("start", "boot", "host", "token")):
        return None
    return _Owner(
        version=1,
        pid=value["pid"],
        start=value["start"],
        boot=value["boot"],
        host=value["host"],
        token=value["token"],
    )


def _alive(owner: _Owner) -> bool:
    if owner["host"] != socket.gethostname():
        return True  # Another host's ownership is never ours to recover.
    current_boot = _boot()
    if owner["boot"] != current_boot:
        try:
            uuid.UUID(owner["boot"])
            uuid.UUID(current_boot)
        except ValueError:
            return True  # An unknown/corrupt boot is not liveness evidence.
        return False  # A process from an earlier boot cannot remain alive.
    try:
        os.kill(owner["pid"], 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    current = _identity(owner["pid"])
    unknown_identity = current in {"", "unknown"} or owner["start"] in {"", "unknown"}
    return unknown_identity or current == owner["start"]


def _has_live_participants(arena: Path) -> bool:
    for source in arena.glob(".cy-participant-*.json"):
        owner = _read_owner(source)
        if owner is None or _alive(owner):
            return True
    return False


def _unsafe_marker_blocks(source: Path) -> bool:
    try:
        value: object = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return True
    if not isinstance(value, dict) or set(value) != {"version", "owners", "reason"}:
        return True
    if value["version"] != 1 or not isinstance(value["reason"], str):
        return True
    owners = value["owners"]
    if not isinstance(owners, list) or not owners:
        return True
    return any(_unsafe_owner_alive(candidate) for candidate in owners)


def _unsafe_owner_alive(candidate: object) -> bool:
    owner = _parse_owner(candidate)
    if owner is None or not owner["start"].isdigit():
        return True
    try:
        uuid.UUID(owner["boot"])
    except ValueError:
        return True
    return _alive(owner)


def _has_unproved_cleanup(arena: Path) -> bool:
    # Publication descendants may survive before joining the arena lease.
    # Their supervisor leaves this marker rather than claiming safe deletion.
    for marker in arena.rglob(".cy-unsafe-cleanup.json"):
        if _unsafe_marker_blocks(marker):
            warnings.warn(
                f"Retaining scratch with unproved descendant cleanup: {marker}",
                RuntimeWarning,
                stacklevel=2,
            )
            return True
    return False


def _remove_arena(arena: Path) -> None:
    try:
        shutil.rmtree(arena)
    except FileNotFoundError:
        pass
    except OSError as error:
        warnings.warn(
            f"Cannot clean invocation scratch {arena}: {error}", RuntimeWarning, stacklevel=2
        )


def _recover_abandoned(root: Path) -> None:
    for arena in root.glob("cy-runtime-*"):
        if arena.is_symlink() or not arena.is_dir():
            continue
        if arena in _STATE.retained:
            continue
        owner = _read_owner(arena / _OWNER_FILE)
        if owner is None or arena.name != "cy-runtime-" + owner["token"]:
            continue
        if (
            not _alive(owner)
            and not _has_live_participants(arena)
            and not _has_unproved_cleanup(arena)
        ):
            descriptor = _acquire_lease(arena, create=False)
            if descriptor is not None:
                try:
                    if (
                        not _alive(owner)
                        and not _has_live_participants(arena)
                        and not _has_unproved_cleanup(arena)
                    ):
                        _remove_arena(arena)
                finally:
                    os.close(descriptor)


def _lock_lease(descriptor: int, *, exclusive: bool) -> bool:
    try:
        if sys.platform == "win32":
            import msvcrt

            # Windows has no shared lock here; participant start identities
            # still protect liveness and the exclusive owner lease is retained.
            if not exclusive:
                return True
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            fcntl.flock(descriptor, mode | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


def _acquire_lease(arena: Path, *, create: bool, exclusive: bool = True) -> int | None:
    path = arena / ".cy-lease"
    if path.is_symlink():
        return None
    flags = os.O_RDWR | (os.O_CREAT if create else 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileNotFoundError:
        return None
    try:
        acquired = _lock_lease(descriptor, exclusive=exclusive)
    except BaseException:
        os.close(descriptor)
        raise
    if not acquired:
        os.close(descriptor)
        return None
    return descriptor


def _register_inherited(temporary: Path) -> None:
    inherited = os.environ.get(_ARENA_ENV)
    if not inherited:
        return
    arena = Path(inherited).resolve()
    if arena.parent != temporary or not arena.is_dir():
        return
    owner = _read_owner(arena / _OWNER_FILE)
    if owner is not None and owner["pid"] != os.getpid():
        key = (os.getpid(), arena)
        if key in _STATE.participant_leases:
            return
        descriptor = _acquire_lease(arena, create=False, exclusive=False)
        if descriptor is None:
            raise RuntimeError(f"Cannot join invocation scratch ownership: {arena}")
        participant = _owner(owner["token"])
        try:
            (arena / f".cy-participant-{os.getpid()}.json").write_text(
                json.dumps(participant), encoding="utf-8"
            )
        except OSError:
            os.close(descriptor)
            raise
        _STATE.participant_leases[key] = descriptor


def _capture_queue_root() -> None:
    # Queue coordination is deliberately user-wide, not library configuration.
    if os.environ.get("CY_GPU_QUEUE_ROOT"):
        return
    if os.name == "nt":
        state = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local")
    else:
        state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    os.environ["CY_GPU_QUEUE_ROOT"] = str((state.expanduser() / "clearml-yolo/queue").resolve())


def _project_path(root: Path, name: str, default: Path) -> Path:
    return _validated_project_path(root, name, Path(os.environ.get(name) or default))


def _validated_project_path(root: Path, name: str, value: Path) -> Path:
    selected = value.expanduser()
    if not selected.is_absolute():
        selected = root / selected
    selected = selected.resolve()
    if not selected.is_relative_to(root):
        raise ValueError(f"{name} must resolve inside the physical project root {root}: {selected}")
    return selected


def _directory(root: Path, name: str, default: Path) -> Path:
    selected = _project_path(root, name, default)
    selected.mkdir(parents=True, exist_ok=True)
    os.environ[name] = str(selected)
    return selected


def _directory_list(root: Path, name: str, default: Path) -> None:
    # Distro/desktop launchers routinely install system search lists. Replace
    # those ambient lookup roots; specific SDK configuration selections below
    # remain strict about an explicit path escaping the physical project root.
    os.environ[name] = str(default)
    _directory(root, name, default)


def _project_directory_list(root: Path, name: str, default: Path) -> None:
    # Botocore models are executable configuration inputs, unlike generic XDG
    # desktop search lists. Validate every caller-selected physical directory.
    values = [value for value in os.environ.get(name, "").split(os.pathsep) if value]
    selected = [_validated_project_path(root, name, Path(value)) for value in values] or [
        _validated_project_path(root, name, default)
    ]
    for directory in selected:
        directory.mkdir(parents=True, exist_ok=True)
    os.environ[name] = os.pathsep.join(str(directory) for directory in selected)


def _file(root: Path, name: str, default: Path, content: str = "") -> Path:
    selected = _project_path(root, name, default)
    selected.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Exclusive create preserves project credentials and concurrent writers.
        descriptor = os.open(selected, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if not selected.is_file():
            raise ValueError(
                f"{name} must select a regular configuration file: {selected}"
            ) from None
    else:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
    os.environ[name] = str(selected)
    return selected


def initialize_runtime_environment() -> Path:
    """Freeze CY_HOME and install only project-owned library configuration paths."""
    with _LOCK:
        before = dict(os.environ)
        root_before = _STATE.root
        installed_before = dict(_STATE.installed)
        leases_before = dict(_STATE.participant_leases)
        bytecode_before = sys.pycache_prefix
        try:
            return _initialize_runtime_environment()
        except BaseException:
            # Startup owns these mutations; callers may report/retry a rejected
            # configuration without inheriting a half-installed environment.
            _restore_environment(before)
            _STATE.root = root_before
            _STATE.installed = installed_before
            sys.pycache_prefix = bytecode_before
            for key, descriptor in _STATE.participant_leases.items():
                if key not in leases_before:
                    os.close(descriptor)
            _STATE.participant_leases = leases_before
            raise


def _restore_environment(before: dict[str, str]) -> None:
    for name in set(before) | set(os.environ):
        value = before.get(name)
        if value is None:
            os.environ.pop(name, None)
        elif os.environ.get(name) != value:
            os.environ[name] = value


def _initialize_runtime_environment() -> Path:
    with _LOCK:
        root = Path(os.environ.get("CY_HOME") or _STATE.root or Path.cwd()).expanduser().resolve()
        if _STATE.root is not None:
            _bind_sdk_root(_STATE.root)
        if _STATE.sdk_root is not None and root != _STATE.sdk_root:
            raise ValueError(
                "Cannot change CY_HOME after runtime SDK configuration has been loaded "
                f"for {_STATE.sdk_root}; select the new workspace in a fresh process"
            )
        if _STATE.root is not None and root != _STATE.root:
            if _STATE.active is not None:
                raise ValueError("Cannot change CY_HOME during an active invocation")
            for name, value in _STATE.installed.items():
                if os.environ.get(name) == value:
                    os.environ.pop(name, None)
            _STATE.installed.clear()
        root.mkdir(parents=True, exist_ok=True)
        _capture_queue_root()
        before = dict(os.environ)
        _install_paths(root)
        _STATE.installed.update(
            {
                name: value
                for name, value in os.environ.items()
                if before.get(name) != value and name != "CY_GPU_QUEUE_ROOT"
            }
        )
        _STATE.root = root
        temporary = Path(os.environ["CY_RUNTIME_TEMP_ROOT"])
        _register_inherited(temporary)
        _recover_abandoned(temporary)
        return root


def _bind_sdk_root(root: Path) -> None:
    # These SDK modules retain configuration/cache locations after import.
    # Inspect the module registry only; bootstrap must never import an SDK.
    cached_modules = (
        "clearml.config",
        "matplotlib",
        "fiftyone",
        "eta",
        "ultralytics.utils",
        "torch._inductor.codecache",
        "triton.runtime.cache",
        "huggingface_hub.constants",
    )
    if _STATE.sdk_root is None and any(name in sys.modules for name in cached_modules):
        _STATE.sdk_root = root


def _install_paths(root: Path) -> None:
    config = _directory(root, "XDG_CONFIG_HOME", root / ".config")
    cache = _directory(root, "XDG_CACHE_HOME", root / ".cache")
    _directory_list(root, "XDG_CONFIG_DIRS", config)
    _directory(root, "XDG_DATA_HOME", cache / "data")
    _directory_list(root, "XDG_DATA_DIRS", cache / "data")
    # The original XDG_STATE_HOME is already captured for the shared registry.
    os.environ["XDG_STATE_HOME"] = str(cache / "state")
    _directory(root, "XDG_STATE_HOME", cache / "state")
    _directory(root, "YOLO_CONFIG_DIR", config)
    clearml_dir = _directory(root, "CLEARML_CONFIG_PATH", config / "clearml")
    clearml_file = _file(root, "CLEARML_CONFIG_FILE", clearml_dir / "clearml.conf")
    # Validate aliases even when the modern SDK would ignore them.
    _directory(root, "TRAINS_CONFIG_PATH", clearml_dir)
    _file(root, "TRAINS_CONFIG_FILE", clearml_file)
    for suffix, filename in (
        ("CONFIG", "config"),
        ("APP_CONFIG", "app_config"),
        ("ANNOTATION_CONFIG", "annotation_config"),
        ("EVALUATION_CONFIG", "evaluation_config"),
        ("BRAIN_CONFIG", "brain_config"),
    ):
        _file(root, f"FIFTYONE_{suffix}_PATH", config / "fiftyone" / f"{filename}.json", "{}\n")
    _directory(root, "ETA_CONFIG_DIR", config / "eta")
    for name, folder in {
        "MPLCONFIGDIR": config / "matplotlib",
        "FONTCONFIG_PATH": config / "fontconfig",
        "TORCH_HOME": cache / "torch",
        "TORCH_EXTENSIONS_DIR": cache / "torch/extensions",
        "TORCHINDUCTOR_CACHE_DIR": cache / "torch/inductor",
        "TRITON_CACHE_DIR": cache / "triton",
        "TRITON_DUMP_DIR": cache / "triton/dump",
        "TRITON_OVERRIDE_DIR": config / "triton",
        "CUDA_CACHE_PATH": cache / "cuda",
        "NUMBA_CACHE_DIR": cache / "numba",
        "HF_HOME": cache / "huggingface",
        "HF_HUB_CACHE": cache / "huggingface/hub",
        "HF_ASSETS_CACHE": cache / "huggingface/assets",
        "RF_HOME": cache / "rfdetr",
        "ROBOFLOW_HOME": cache / "roboflow",
        "PYTHONPYCACHEPREFIX": cache / "python",
        "KERAS_HOME": cache / "keras",
    }.items():
        _directory(root, name, folder)
    sys.pycache_prefix = os.environ["PYTHONPYCACHEPREFIX"]
    _file(root, "MATPLOTLIBRC", Path(os.environ["MPLCONFIGDIR"]) / "matplotlibrc")
    font_cache = _validated_project_path(root, "Fontconfig cache", cache / "fontconfig")
    font_cache.mkdir(parents=True, exist_ok=True)
    _file(
        root,
        "FONTCONFIG_FILE",
        config / "fontconfig/fonts.conf",
        '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">'
        "<fontconfig><dir>/usr/share/fonts</dir><dir>/usr/local/share/fonts</dir>"
        f"<cachedir>{escape(str(font_cache))}</cachedir></fontconfig>\n",
    )
    for name, filename in (
        ("NETRC", "netrc"),
        ("AWS_CONFIG_FILE", "aws/config"),
        ("AWS_SHARED_CREDENTIALS_FILE", "aws/credentials"),
        ("BOTO_CONFIG", "boto.cfg"),
    ):
        _file(root, name, config / filename)
    for name in ("AWS_WEB_IDENTITY_TOKEN_FILE", "AWS_CREDENTIAL_FILE"):
        if os.environ.get(name):
            # Credential sources must already exist when used. Validating a
            # configured path must not synthesize an empty identity token.
            os.environ[name] = str(_project_path(root, name, Path(os.environ[name])))
    _project_directory_list(root, "AWS_DATA_PATH", config / "aws/models")
    os.environ["AWS_EC2_METADATA_DISABLED"] = "true"
    # ECS metadata is a separate provider and ignores the EC2 disable switch.
    # Preserve scalar credentials; require project files for credential sources.
    os.environ.pop("AWS_CONTAINER_CREDENTIALS_FULL_URI", None)
    os.environ.pop("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI", None)
    _directory(root, "FIFTYONE_PLUGINS_DIR", config / "fiftyone/plugins")
    _install_data_paths(cache)
    temporary = _project_path(root, "CY_RUNTIME_TEMP_ROOT", root / ".tmp")
    temporary.mkdir(parents=True, exist_ok=True)
    os.environ["CY_RUNTIME_TEMP_ROOT"] = str(temporary)
    os.environ["CY_HOME"] = str(root)


def _install_data_paths(cache: Path) -> None:
    launch_directory = Path.cwd().resolve()
    try:
        loaded: object = json.loads(
            Path(os.environ["FIFTYONE_CONFIG_PATH"]).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        warnings.warn(
            f"Cannot read optional project FiftyOne settings: {error}", RuntimeWarning, stacklevel=2
        )
        loaded = {}
    settings = loaded if isinstance(loaded, dict) else {}
    # SDK storage/data destinations are explicit and can live outside CY_HOME.
    for name, folder in {
        "CLEARML_CACHE_DIR": cache / "clearml",
        "FIFTYONE_DATABASE_DIR": cache / "fiftyone/database",
        "FIFTYONE_DEFAULT_DATASET_DIR": cache / "fiftyone/datasets",
        "FIFTYONE_DATASET_ZOO_DIR": cache / "fiftyone/datasets",
        "FIFTYONE_MODEL_ZOO_DIR": cache / "fiftyone/models",
        "ETA_OUTPUT_DIR": cache / "eta/output",
    }.items():
        configured = settings.get(name.removeprefix("FIFTYONE_").lower())
        default = (
            configured
            if name.startswith("FIFTYONE_") and isinstance(configured, str) and configured
            else str(folder)
        )
        selected = os.environ.get(name, default)
        os.environ[name] = str(_data_directory(selected, launch_directory))
    _install_eta_models(cache / "eta/models", launch_directory)


def _install_eta_models(default: Path, launch_directory: Path) -> None:
    selected = os.environ.get("ETA_MODELS_DIRS")
    inherited = os.environ.get("CY_ETA_MODELS_DIRS")
    if selected is None and inherited is None:
        values = [str(default)]
    elif selected is None or selected.lstrip().startswith("["):
        decoded: object = json.loads(selected if selected is not None else inherited or "")
        if not isinstance(decoded, list) or not all(isinstance(value, str) for value in decoded):
            raise ValueError("ETA model directories must be a JSON array of strings")
        values = decoded
    else:
        separator = "," if "," in selected else os.pathsep
        values = selected.split(separator) if selected else []
    # ETA hardcodes ':' for arrays, which corrupts Windows drive letters and
    # POSIX path names containing colons. Carry absolute values losslessly to
    # the optional worker, which applies ETA's public configuration API.
    os.environ["CY_ETA_MODELS_DIRS"] = json.dumps(
        [str(_data_directory(value, launch_directory)) for value in values]
    )
    os.environ.pop("ETA_MODELS_DIRS", None)


def _data_directory(value: str, launch_directory: Path) -> Path:
    # SDKs resolve relative paths during import; Matplotlib's controlled import
    # directory must never become the base for an explicit durable destination.
    selected = Path(value).expanduser()
    selected = (selected if selected.is_absolute() else launch_directory / selected).resolve()
    selected.mkdir(parents=True, exist_ok=True)
    return selected


def invocation_temporary_root() -> Path | None:
    """Return active or inherited owned scratch without claiming its ownership."""
    selected = os.environ.get(_ARENA_ENV)
    if selected:
        root = Path(os.environ.get("CY_HOME") or Path.cwd()).resolve()
        arena = Path(selected).resolve()
        temporary = Path(os.environ.get("CY_RUNTIME_TEMP_ROOT") or root / ".tmp").resolve()
        if temporary.is_relative_to(root) and arena.parent == temporary and arena.is_dir():
            return arena
    return None


def retain_current_arena(reason: str) -> None:
    """Fail closed in this process when a supervisor cannot persist its marker.

    Supervisors must write an unknown-ownership marker before starting workers;
    this extra guard does not replace durable evidence across parent crashes.
    """
    with _LOCK:
        arena = invocation_temporary_root()
        if arena is not None:
            _STATE.retained[arena] = reason
        warnings.warn(
            f"Unsafe process cleanup requires retained invocation scratch: {arena}",
            RuntimeWarning,
            stacklevel=2,
        )


@contextmanager
def runtime_environment() -> Iterator[Path]:
    """Own scratch through all command cleanup; nested calls reuse the same arena."""
    with _LOCK:
        scope = _RuntimeScope(
            environment=dict(os.environ),
            root=_STATE.root,
            installed=dict(_STATE.installed),
            active=_STATE.active,
            temporary=tempfile.tempdir,
            bytecode=sys.pycache_prefix,
        )
        try:
            scope.initialized_root = initialize_runtime_environment()
            scope.changed = {
                name
                for name in set(scope.environment) | set(os.environ)
                if scope.environment.get(name) != os.environ.get(name)
            }
            if _STATE.active is not None and _STATE.active[0] == os.getpid():
                yield _STATE.active[1]
                return
            token = uuid.uuid4().hex
            arena = Path(os.environ["CY_RUNTIME_TEMP_ROOT"]) / ("cy-runtime-" + token)
            scope.arena = arena
            arena.mkdir(mode=0o700)
            scope.created = True
            (arena / _OWNER_FILE).write_text(json.dumps(_owner(token)), encoding="utf-8")
            scope.lease = _acquire_lease(arena, create=True, exclusive=False)
            if scope.lease is None:
                raise RuntimeError(f"Cannot claim invocation scratch lease: {arena}")
            _install_scope_temporary(scope, arena)
            yield arena
        finally:
            _finish_runtime_scope(scope)


def _install_scope_temporary(scope: _RuntimeScope, arena: Path) -> None:
    names = ("TMPDIR", "TMP", "TEMP", _ARENA_ENV)
    scope.changed.update(names)
    for name in names:
        os.environ[name] = str(arena)
    tempfile.tempdir = str(arena)
    if threading.current_thread() is threading.main_thread():
        previous = signal.getsignal(signal.SIGTERM)
        if previous is not None:
            scope.previous_handler = previous
            signal.signal(signal.SIGTERM, _terminate)
    _STATE.active = (os.getpid(), arena)


def _finish_runtime_scope(scope: _RuntimeScope) -> None:
    if scope.initialized_root is not None:
        _bind_sdk_root(scope.initialized_root)
    _STATE.active = scope.active
    if scope.previous_handler is not None:
        signal.signal(signal.SIGTERM, scope.previous_handler)
    for name in scope.changed:
        value = scope.environment.get(name)
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
    tempfile.tempdir = scope.temporary
    sys.pycache_prefix = scope.bytecode
    _STATE.root = scope.root
    _STATE.installed = scope.installed
    if scope.created and scope.arena is not None:
        if scope.lease is None:
            _remove_arena(scope.arena)  # No worker can have started before yield.
        else:
            try:
                _cleanup_scoped_arena(scope.arena, scope.lease)
            finally:
                os.close(scope.lease)


def _cleanup_scoped_arena(arena: Path, lease: int) -> None:
    if (
        arena in _STATE.retained
        or not _lock_lease(lease, exclusive=True)
        or _has_live_participants(arena)
        or _has_unproved_cleanup(arena)
    ):
        warnings.warn(
            f"Retaining invocation scratch with live worker ownership: {arena}",
            RuntimeWarning,
            stacklevel=2,
        )
    else:
        _remove_arena(arena)


def _terminate(signum: int, _frame: FrameType | None) -> None:
    raise SystemExit(128 + signum)


@contextmanager
def project_configuration_imports() -> Iterator[None]:
    """Load SDKs without Matplotlib's mandatory launch-CWD config precedence.

    This small startup boundary must contain dependency imports only: restore the
    launch directory before composing configuration or resolving user inputs.
    """
    with _LOCK:
        initialized_root = initialize_runtime_environment()
        previous = Path.cwd()
        os.chdir(Path(os.environ["MATPLOTLIBRC"]).parent)
        try:
            yield
        finally:
            _bind_sdk_root(initialized_root)
            os.chdir(previous)
