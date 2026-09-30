"""ClearML task lifecycle shared by every app.

A single task is created per invocation and reused by all stages of the pipeline, so
that training scalars, prediction artifacts, per-split metrics and the comparison
reports all land on one experiment.
"""

import copy
import dataclasses
import hashlib
import json
import os
import re
import signal
import threading
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any, Self
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, model_validator
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import YAMLError
from ruamel.yaml.tokens import CommentToken

OWNER_PID_ENV = "CY_CLEARML_OWNER_PID"
OWNER_TASK_ENV = "CY_CLEARML_OWNER_TASK_ID"
REDACTED = "<redacted>"

DEFAULT_PROJECT_NAME = "clearml-yolo"

# Keep the SDK opaque at the adapter boundary so reporting modules need no SDK import.
Task = Any


class ClearMLConfig(BaseModel):
    """Identity of the ClearML experiment this run belongs to."""

    model_config = ConfigDict(extra="forbid")

    project_name: str = DEFAULT_PROJECT_NAME
    task_name: str = "yolo-run"
    task_type: str = "training"
    tags: list[str] = Field(default_factory=list)
    output_uri: str | bool | None = True

    @model_validator(mode="after")
    def _validate_tracking_destination(self) -> Self:
        """Require remote artifact storage without changing explicit run identity."""
        if self.output_uri is None or self.output_uri is False or self.output_uri == "":
            raise ValueError("ClearML output_uri is required for remote artifact storage")
        return self


def resolve_task_name(config: ClearMLConfig, stage: str) -> str:
    """Name a stage-specific task, used only when a stage runs standalone."""
    return config.task_name if stage == "pipeline" else f"{config.task_name}/{stage}"


def task_identity(task: Any) -> tuple[str, str, str]:
    """Read the active SDK identity, including remote overrides and project hierarchy."""
    values = (task.get_project_name(), task.name, task.id)
    if any(not isinstance(value, str) or not value for value in values):
        raise ValueError("Active ClearML task requires a project name, task name and ID")
    return values


class ArtifactUploadError(RuntimeError):
    """A required artifact or final upload barrier was rejected."""


@dataclass(frozen=True)
class ResolvedConfigFile:
    """Detached file values and credential provenance required for safe publication."""

    values: Any
    secrets: frozenset[str] = field(repr=False)


@dataclass
class _ArtifactRecord:
    stage: str
    name: str
    local_path: str | None
    required: bool = True
    uploaded: bool = False


@dataclass
class _InvocationState:
    task: Any
    stages: list[str]
    current_stage: str
    artifacts: list[_ArtifactRecord] = field(default_factory=list)
    table_by_digest: dict[str, str] = field(default_factory=dict)
    table_remote_by_key: dict[tuple[str, str], str] = field(default_factory=dict)
    table_remote_names: set[str] = field(default_factory=set)
    model_barriers: list[Callable[[], None]] = field(default_factory=list)
    run_configuration: dict[str, Any] = field(default_factory=dict)
    config_directory: TemporaryDirectory[str] | None = None
    config_resolver: Callable[[Any], Any] | None = None
    config_file_count: int = 0
    execution_config_paths: list[Path] = field(default_factory=list)

    def enter_stage(self, stage: str) -> None:
        self.current_stage = stage
        if stage not in self.stages:
            self.stages.append(stage)

    def config_path(self, suffix: str) -> Path:
        if self.config_directory is None:
            self.config_directory = TemporaryDirectory(prefix="clearml-yolo-config-")
        path = Path(self.config_directory.name) / f"{self.config_file_count:04d}{suffix}"
        self.config_file_count += 1
        return path

    def execution_config_path(self, source: Path) -> Path:
        # Dataset consumers interpret relative image paths against the YAML parent.
        # Keep the owned execution copy beside its source rather than moving that base.
        with NamedTemporaryFile(
            prefix=f".{source.stem}-resolved-",
            suffix=source.suffix,
            dir=source.parent,
            delete=False,
        ) as stream:
            path = Path(stream.name)
        self.execution_config_paths.append(path)
        return path

    def cleanup(self) -> None:
        for path in self.execution_config_paths:
            path.unlink(missing_ok=True)
        if self.config_directory is not None:
            self.config_directory.cleanup()


_ACTIVE_INVOCATION: ContextVar[_InvocationState | None] = ContextVar(
    "clearml_yolo_active_invocation", default=None
)


def active_task() -> Any | None:
    """Return the invocation-owned task in the current execution context."""
    active = _ACTIVE_INVOCATION.get()
    return active.task if active is not None else None


class _SignalExit(SystemExit):
    def __init__(self, signum: int) -> None:
        self.signum = signum
        super().__init__(128 + signum)


def _is_worker() -> bool:
    owner_pid = os.environ.get(OWNER_PID_ENV)
    if owner_pid and owner_pid != str(os.getpid()):
        return True
    local_rank = os.environ.get("LOCAL_RANK")
    return local_rank is not None and local_rank != "-1"


def _sensitive_key(key: object) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return normalized in {"auth", "authentication", "sig", "signature"} or any(
        marker in normalized
        for marker in (
            "access_key",
            "secret",
            "password",
            "passwd",
            "token",
            "credential",
            "api_key",
            "apikey",
            "accesskey",
            "authorization",
            "private_key",
            "privatekey",
            "bearer",
            "cookie",
            "session_key",
        )
    )


def _sanitize_url(value: str) -> str:
    parts = urlsplit(value)
    if not parts.scheme or not parts.netloc:
        return value
    hostname = parts.hostname or ""
    port = f":{parts.port}" if parts.port is not None else ""
    netloc = f"{REDACTED}@{hostname}{port}" if parts.username is not None else parts.netloc
    query = urlencode(
        [
            (key, REDACTED if _sensitive_key(key) else item)
            for key, item in parse_qsl(parts.query, keep_blank_values=True)
        ],
        doseq=True,
    )
    return urlunsplit((parts.scheme, netloc, parts.path, query, parts.fragment))


def sanitize_configuration(value: Any) -> Any:
    """Return a serializable configuration with credentials removed recursively."""
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        value = dataclasses.asdict(value)
    if isinstance(value, Mapping):
        return {
            str(key): REDACTED if _sensitive_key(key) else sanitize_configuration(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [sanitize_configuration(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, str):
        return _sanitize_url(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)


def _failure_name(error: BaseException) -> str:
    if isinstance(error, _SignalExit):
        try:
            return signal.Signals(error.signum).name
        except ValueError:
            return f"signal-{error.signum}"
    return type(error).__name__


def _mark_failed(task: Any, error: BaseException) -> None:
    reason = _failure_name(error)
    # Arbitrary exception text can contain URLs, headers, or credentials in formats
    # that cannot be exhaustively redacted. Keep full diagnostics in local output.
    message = f"{reason}: invocation failed; see local diagnostics for details"
    task.mark_failed(
        ignore_errors=False,
        force=True,
        status_reason=reason,
        status_message=message,
    )


def _sync_upload(task: Any, name: str, artifact_object: Any) -> None:
    accepted = task.upload_artifact(
        name=name,
        artifact_object=artifact_object,
        wait_on_upload=True,
    )
    if accepted is not True:
        raise ArtifactUploadError(f"ClearML rejected required artifact {name!r}")


def _active_state(task: Any, operation: str) -> _InvocationState:
    active = _ACTIVE_INVOCATION.get()
    if active is None or task is None or task is not active.task:
        raise RuntimeError(f"{operation} requires the active invocation-owned task")
    return active


def _finalize(state: _InvocationState) -> None:
    missing = [
        artifact.name for artifact in state.artifacts if artifact.required and not artifact.uploaded
    ]
    if missing:
        raise ArtifactUploadError(f"Required artifacts were not uploaded: {', '.join(missing)}")
    if state.model_barriers:
        from clearml import OutputModel

        OutputModel.wait_for_uploads()
    if state.task.flush(wait_for_uploads=True) is not True:
        raise ArtifactUploadError("ClearML flush did not confirm completion")
    if state.model_barriers:
        state.task.reload()
        for verify in state.model_barriers:
            verify()
    # close() waits for repository detection and shuts down the status monitor.
    # Marking completed first makes that monitor interpret our own success as an
    # external abort while background configuration uploads are still running.
    task_id = str(state.task.id)
    state.task.close()
    from clearml import Task

    closed_task: Any = Task.get_task(task_id=task_id)
    closed_task.mark_completed(ignore_errors=False, force=True)


def _exit_on_signal(signum: int, _frame: Any) -> None:
    raise _SignalExit(signum)


def _restore_environment(name: str, previous: str | None) -> None:
    if previous is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous


def _replay_initial_configuration(task: Any, resolved_config: Any) -> None:
    if not isinstance(resolved_config, Mapping):
        raise TypeError("Resolved run configuration must be a mapping")
    replay_configuration(task, dict(resolved_config))


@contextmanager
def invocation(
    config: ClearMLConfig,
    stage: str,
    resolved_config: Any | None = None,
    *,
    config_resolver: Callable[[Any], Any] | None = None,
) -> Iterator[Any]:
    """Own the sole ClearML task and its terminal status for one CLI invocation."""
    if _is_worker():
        yield None
        return

    active = _ACTIVE_INVOCATION.get()
    if active is not None:
        previous_stage = active.current_stage
        active.enter_stage(stage)
        try:
            yield active.task
        finally:
            active.current_stage = previous_stage
        return

    owns_signal = threading.current_thread() is threading.main_thread()
    previous_sigterm: Any = signal.getsignal(signal.SIGTERM) if owns_signal else None

    from clearml import Task

    task: Any = Task.init(
        project_name=config.project_name,
        task_name=resolve_task_name(config, stage),
        task_type=config.task_type,
        tags=config.tags or None,
        output_uri=config.output_uri,
        reuse_last_task_id=False,
        auto_connect_arg_parser=False,
        # Native console output may include unredacted URLs/arguments. Keep it local;
        # the wrapper publishes sanitized configuration and explicit metrics instead.
        auto_connect_streams=False,
        # Repository auto-detection uploads arbitrary checkout diffs outside our
        # sanitized provenance contract. Disable it along with framework captures.
        auto_connect_frameworks=dict.fromkeys(
            (
                "detect_repository",
                "hydra",
                "scikit",
                "joblib",
                "matplotlib",
                "tensorflow",
                "tensorboard",
                "tfdefines",
                "pytorch",
                "megengine",
                "xgboost",
                "catboost",
                "fastai",
                "lightgbm",
                "gradio",
            ),
            False,
        ),
    )
    state = _InvocationState(
        task=task, stages=[stage], current_stage=stage, config_resolver=config_resolver
    )
    token = _ACTIVE_INVOCATION.set(state)
    previous_owner = os.environ.get(OWNER_PID_ENV)
    os.environ[OWNER_PID_ENV] = str(os.getpid())
    if owns_signal:
        signal.signal(signal.SIGTERM, _exit_on_signal)

    logger.info(
        "ClearML task {} created: project={!r} name={!r}",
        task.id,
        config.project_name,
        resolve_task_name(config, stage),
    )
    previous_task_id = os.environ.get(OWNER_TASK_ENV)
    os.environ[OWNER_TASK_ENV] = str(task.id)
    try:
        if resolved_config is not None:
            _replay_initial_configuration(task, resolved_config)
        yield task
        _finalize(state)
    except BaseException as error:
        try:
            _mark_failed(task, error)
        finally:
            task.close()
        raise
    finally:
        if owns_signal:
            signal.signal(signal.SIGTERM, previous_sigterm)
        _restore_environment(OWNER_PID_ENV, previous_owner)
        _restore_environment(OWNER_TASK_ENV, previous_task_id)
        _ACTIVE_INVOCATION.reset(token)
        state.cleanup()


def init_task(config: ClearMLConfig, stage: str) -> Any:
    """Return the invocation-owned task, or no task inside a distributed worker."""
    del config
    if _is_worker():
        return None
    active = _ACTIVE_INVOCATION.get()
    if active is None:
        raise RuntimeError("ClearML task access requires an invocation() owner")
    active.enter_stage(stage)
    logger.info(
        "Reusing active ClearML task {} ({}) for stage {}",
        active.task.id,
        active.task.name,
        stage,
    )
    return active.task


def upload_artifact(task: Any, name: str, artifact_object: Any) -> None:
    """Synchronously upload one required artifact and record it in the owner manifest."""
    if _is_worker():
        return
    active = _active_state(task, "Artifact upload")
    record = next((artifact for artifact in active.artifacts if artifact.name == name), None)
    if record is not None and record.uploaded:
        raise ValueError(f"Required artifact {name!r} was already registered")
    local_path = str(artifact_object.resolve()) if isinstance(artifact_object, Path) else None
    if record is None:
        record = _ArtifactRecord(
            stage=active.current_stage,
            name=name,
            local_path=local_path,
        )
        active.artifacts.append(record)
    else:
        record.local_path = local_path
    if isinstance(artifact_object, Path) and not artifact_object.exists():
        raise FileNotFoundError(f"Required artifact path does not exist: {artifact_object}")
    _sync_upload(task, name, artifact_object)
    record.uploaded = True
    logger.debug("Uploaded required artifact {}", name)


def expect_artifacts(task: Any, names: list[str]) -> None:
    """Declare the artifacts a stage must upload before its invocation may complete."""
    if _is_worker():
        return
    active = _active_state(task, "Artifact expectation registration")
    for name in names:
        if not name:
            raise ValueError("Expected artifact names must be non-empty")
        if any(artifact.name == name for artifact in active.artifacts):
            raise ValueError(f"Required artifact {name!r} was already registered")
        active.artifacts.append(
            _ArtifactRecord(stage=active.current_stage, name=name, local_path=None)
        )


def publish_table(task: Any, name: str, path: Path) -> None:
    """Publish CSV bytes once while satisfying every internal alias for those bytes."""
    if _is_worker():
        return
    active = _active_state(task, "Table publication")
    if not name:
        raise ValueError("Published table name must be non-empty")
    if not path.is_file():
        raise FileNotFoundError(f"Required table does not exist: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    existing_name = active.table_by_digest.get(digest)
    existing_key_name = active.table_remote_by_key.get((name, digest))
    record = next((item for item in active.artifacts if item.name == name), None)
    if record is None:
        record = _ArtifactRecord(
            stage=active.current_stage,
            name=name,
            local_path=str(path.resolve()),
        )
        active.artifacts.append(record)
    elif record.uploaded and existing_key_name is None:
        # The expectation is for the canonical logical name. A deterministic remote
        # suffix preserves both distinct tables without registering the expectation twice.
        pass
    else:
        record.local_path = str(path.resolve())
    if existing_name is not None:
        record.uploaded = True
        active.table_remote_by_key[(name, digest)] = existing_name
        return
    remote_name = name
    if remote_name in active.table_remote_names:
        remote_name = f"{name}_{digest[:12]}"
        if remote_name in active.table_remote_names:
            remote_name = f"{name}_{digest}"
    _sync_upload(task, remote_name, path)
    active.table_by_digest[digest] = remote_name
    active.table_remote_by_key[(name, digest)] = remote_name
    active.table_remote_names.add(remote_name)
    record.uploaded = True
    logger.debug("Published canonical table {} as {}", name, remote_name)


def register_model_barrier(task: Any, verifier: Callable[[], None]) -> None:
    """Require native model upload and a fresh verification before task completion."""
    if _is_worker():
        return
    active = _active_state(task, "Model barrier registration")
    if not callable(verifier):
        raise TypeError("Model barrier verifier must be callable")
    active.model_barriers.append(verifier)


def _meaningful(value: Any) -> Any:
    if isinstance(value, Mapping):
        mapping_result = {
            str(key): cleaned
            for key, item in value.items()
            if (cleaned := _meaningful(item)) is not _EMPTY
        }
        return mapping_result or _EMPTY
    if isinstance(value, (list, tuple, set, frozenset)):
        list_result = [cleaned for item in value if (cleaned := _meaningful(item)) is not _EMPTY]
        return list_result or _EMPTY
    if isinstance(value, str) and not value.strip():
        return _EMPTY
    return value


def _merge_configuration(target: dict[str, Any], update: Mapping[str, Any]) -> None:
    for key, value in update.items():
        if isinstance(value, Mapping) and isinstance(target.get(key), dict):
            _merge_configuration(target[key], value)
        else:
            target[key] = value


_EMPTY = object()


def record_run_configuration(task: Any, values: dict[str, Any]) -> dict[str, Any]:
    """Merge sanitized meaningful values into the invocation's canonical run object."""
    if _is_worker():
        return values
    active = _active_state(task, "Run configuration recording")
    cleaned = _meaningful(sanitize_configuration(values))
    if cleaned is _EMPTY:
        return dict(active.run_configuration)
    if not isinstance(cleaned, Mapping):
        raise TypeError("Run configuration must be a mapping")
    _merge_configuration(active.run_configuration, cleaned)
    task.connect_configuration(
        configuration=active.run_configuration,
        name="run",
        ignore_remote_overrides=True,
    )
    return dict(active.run_configuration)


def replay_configuration(task: Any, values: dict[str, Any]) -> dict[str, Any]:
    """Resolve a clone's canonical run object and freeze it for this invocation."""
    if _is_worker():
        return values
    active = _active_state(task, "Run configuration replay")
    cleaned = _meaningful(sanitize_configuration(values))
    if cleaned is _EMPTY or not isinstance(cleaned, Mapping):
        raise ValueError("Canonical run configuration must not be empty")
    connected = task.connect_configuration(
        configuration=dict(cleaned),
        name="run",
        ignore_remote_overrides=False,
    )
    if not isinstance(connected, Mapping):
        raise TypeError("ClearML run configuration override must be a mapping")
    effective = _meaningful(sanitize_configuration(connected))
    if effective is _EMPTY or not isinstance(effective, Mapping):
        raise ValueError("Effective ClearML run configuration must not be empty")
    active.run_configuration = dict(effective)
    task.connect_configuration(
        configuration=active.run_configuration,
        name="run",
        ignore_remote_overrides=True,
    )
    # Redaction is a storage boundary, not a mutation of executable inputs.
    return dict(values if task.running_locally() else connected)


def _configuration_secrets(value: Any, *, sensitive: bool = False) -> set[str]:
    if isinstance(value, Mapping):
        return {
            secret
            for key, item in value.items()
            for secret in _configuration_secrets(item, sensitive=sensitive or _sensitive_key(key))
        }
    if isinstance(value, (list, tuple)):
        return {
            secret for item in value for secret in _configuration_secrets(item, sensitive=sensitive)
        }
    if sensitive and isinstance(value, (bool, int, float)):
        return {str(value)}
    if isinstance(value, str):
        if sensitive:
            return {value} if value and value != REDACTED else set()
        parts = urlsplit(value)
        if parts.scheme and parts.netloc:
            candidates = {parts.username, parts.password}
            candidates.update(item for key, item in parse_qsl(parts.query) if _sensitive_key(key))
            return {item for item in candidates if item and item != REDACTED}
    return set()


def configuration_secrets(value: Any) -> set[str]:
    """Collect credential values for file publication without changing dictionary storage."""
    return _configuration_secrets(value)


def _sanitize_yaml_comment(value: str, secrets: set[str]) -> str:
    lines = []
    for line in value.splitlines(keepends=True):
        # Disabled settings are comments too: keep native settings, but remove
        # credential assignments rather than uploading their inactive values.
        assignments = re.findall(r"\b([A-Za-z_][\w-]*)\s*[:=]\s*\S+", line)
        if any(_sensitive_key(key) for key in assignments):
            newline = "\n" if line.endswith("\n") else ""
            lines.append(f"# {REDACTED}{newline}")
        else:
            lines.append(
                re.sub(r"[A-Za-z][\w+.-]*://[^\s<>]+", lambda m: _sanitize_url(m[0]), line)
            )
    sanitized = "".join(lines)
    for secret in sorted(secrets, key=len, reverse=True):
        sanitized = sanitized.replace(secret, REDACTED)
    return sanitized


def _sanitize_yaml_comments(value: Any, secrets: set[str]) -> None:
    # ruamel stores comment tokens in lists grouped by position (before a key,
    # beside a value, or at document end), including nested lists for sequences.
    if isinstance(value, CommentToken):
        value.value = _sanitize_yaml_comment(value.value, secrets)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _sanitize_yaml_comments(item, secrets)


def _sanitize_config_scalar(value: Any, secrets: set[str]) -> Any:
    sanitized = sanitize_configuration(value)
    if isinstance(sanitized, str):
        for secret in sorted(secrets, key=len, reverse=True):
            sanitized = sanitized.replace(secret, REDACTED)
    elif isinstance(sanitized, (bool, int, float)) and str(sanitized) in secrets:
        return REDACTED
    return sanitized


def _sanitize_yaml_configuration(value: Any, secrets: set[str]) -> Any:
    if isinstance(value, (CommentedMap, CommentedSeq)):
        _sanitize_yaml_comments(value.ca.comment, secrets)
        _sanitize_yaml_comments(value.ca.end, secrets)
        for comments in value.ca.items.values():
            _sanitize_yaml_comments(comments, secrets)
    if isinstance(value, Mapping):
        if not isinstance(value, CommentedMap):
            value = dict(value)
        for key, item in value.items():
            value[key] = (
                REDACTED if _sensitive_key(key) else _sanitize_yaml_configuration(item, secrets)
            )
        return value
    if isinstance(value, list):
        for index, item in enumerate(value):
            value[index] = _sanitize_yaml_configuration(item, secrets)
        return value
    return _sanitize_config_scalar(value, secrets)


def _plain_config_document(value: Any) -> Any:
    """Detach round-trip containers and scalar wrappers from the resolver input."""
    if isinstance(value, Mapping):
        return {
            _plain_config_document(key): _plain_config_document(item) for key, item in value.items()
        }
    if isinstance(value, list):
        return [_plain_config_document(item) for item in value]
    if isinstance(value, str):
        return str(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return float(value)
    return value


def _requires_config_resolver(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_requires_config_resolver(item) for item in value.values())
    if isinstance(value, list):
        return any(_requires_config_resolver(item) for item in value)
    return isinstance(value, str) and (
        value == "???" or re.search(r"(?<!\\)(?:\\\\)*\$\{", value) is not None
    )


def _update_yaml_values(original: Any, resolved: Any) -> Any:
    """Replace active values while retaining round-trip comment positions and order."""
    if isinstance(original, CommentedMap) and isinstance(resolved, Mapping):
        for key in list(original):
            if key not in resolved:
                del original[key]
        for key, value in resolved.items():
            original[key] = _update_yaml_values(original.get(key), value)
        return original
    if isinstance(original, CommentedSeq) and isinstance(resolved, list):
        for index, value in enumerate(resolved):
            if index < len(original):
                original[index] = _update_yaml_values(original[index], value)
            else:
                original.append(_update_yaml_values(None, value))
        del original[len(resolved) :]
        return original
    if isinstance(resolved, Mapping):
        return CommentedMap(
            {key: _update_yaml_values(None, item) for key, item in resolved.items()}
        )
    if isinstance(resolved, list):
        return CommentedSeq([_update_yaml_values(None, item) for item in resolved])
    return resolved


def _write_config_document(path: Path, content: Any, yaml: YAML) -> None:
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        with path.open("w", encoding="utf-8") as stream:
            yaml.dump(content, stream)


def _load_config_document(path: Path, yaml: YAML) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file does not exist: {path}")
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        if suffix in {".yaml", ".yml"}:
            return yaml.load(path.read_text(encoding="utf-8"))
        raise ValueError(f"Unsupported configuration file format: {path.suffix or '<none>'}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON configuration file: {path}") from None
    except YAMLError:
        raise ValueError(f"Invalid YAML configuration file: {path}") from None


def _prepared_config_file(state: _InvocationState, path: Path) -> tuple[Path, Path]:
    """Resolve once, then produce separate executable and sanitized storage inputs."""
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    content = _load_config_document(path, yaml)
    suffix = path.suffix.lower()
    plain = _plain_config_document(content)
    provenance_secrets: frozenset[str] = frozenset()
    if state.config_resolver is None:
        if _requires_config_resolver(plain):
            raise ValueError(
                "Configuration contains unresolved values; use an execution command or "
                "provide invocation(config_resolver=...)"
            )
        resolved = plain
    else:
        try:
            resolved = state.config_resolver(plain)
            if isinstance(resolved, ResolvedConfigFile):
                provenance_secrets = resolved.secrets
                resolved = resolved.values
        except Exception:  # noqa: BLE001 - opaque resolver errors can contain credentials
            raise ValueError("Configuration values could not be resolved") from None

    try:
        effective = _update_yaml_values(content, resolved) if suffix != ".json" else resolved
        execution_path = path
        if resolved != plain:
            execution_path = state.execution_config_path(path)
            _write_config_document(execution_path, effective, yaml)
        sanitized_path = state.config_path(suffix)
        sanitized = _sanitize_yaml_configuration(
            copy.deepcopy(effective), _configuration_secrets(resolved) | provenance_secrets
        )
        _write_config_document(sanitized_path, sanitized, yaml)
    except Exception:  # noqa: BLE001 - parser/serializer details can contain credentials
        raise ValueError("Configuration file could not be prepared") from None
    return execution_path, sanitized_path


def connect_config_file(
    task: Any, name: str, path: Path, *, allow_remote_override: bool = True
) -> Path:
    """Attach a sanitized consumed configuration object and return the path to read.

    The return value is the path that must be read from here on, and it is not always the
    one passed in. A task cloned and run on an agent is handed ClearML's own copy of the
    file — that is what makes the clone reproduce this run rather than whatever now sits at
    that path — so ignoring the return value would quietly reintroduce the machine
    dependency this removes. A distributed worker returns the path unchanged because only
    the invocation owner may write tracking state.

    Values that are not primitives do not survive ClearML hyperparameters reliably. A source
    file is kept as configuration so an agent clone can reproduce it without flattening its
    contents into parameter values.
    """
    if _is_worker():
        return path
    active = _active_state(task, "Configuration recording")
    if path.is_file():
        execution_path, sanitized_path = _prepared_config_file(active, path)
    elif allow_remote_override and not task.running_locally():
        # A cloned task can supply its attached source without the original host path.
        sanitized_path = active.config_path(path.suffix or ".yaml")
        sanitized_path.write_text("{}\n", encoding="utf-8")
        execution_path = path
    else:
        raise FileNotFoundError(f"Configuration file does not exist: {path}")
    connected = Path(
        task.connect_configuration(
            configuration=sanitized_path,
            name=name,
            ignore_remote_overrides=not allow_remote_override,
        )
    )
    if connected == sanitized_path and not path.is_file():
        raise FileNotFoundError(f"Remote task has no attached configuration for {path}")
    if connected != sanitized_path:
        execution_path, sanitized_path = _prepared_config_file(active, connected)
    task.connect_configuration(
        configuration=sanitized_path,
        name=name,
        ignore_remote_overrides=True,
    )
    logger.info("Connected {} to ClearML as configuration {!r}", path, name)
    # Sanitization is for storage, not model execution: preserve local source values
    # (including externally managed credentials) or use the clone's effective source.
    return execution_path
