"""ClearML task lifecycle shared by every app.

A single task is created per invocation and reused by all stages of the pipeline, so
that training scalars, prediction artifacts, per-split metrics and the comparison
reports all land on one experiment.
"""

from __future__ import annotations

import dataclasses
import json
import os
import signal
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import yaml
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, model_validator

ARTIFACT_MANIFEST = "artifact_manifest"
RESOLVED_CONFIGURATION = "resolved_configuration"
OWNER_PID_ENV = "CY_CLEARML_OWNER_PID"
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
    def _validate_tracking_destination(self) -> ClearMLConfig:
        """Require remote artifact storage without changing explicit run identity."""
        if self.output_uri is None or self.output_uri is False or self.output_uri == "":
            raise ValueError("ClearML output_uri is required for remote artifact storage")
        return self


def resolve_task_name(config: ClearMLConfig, stage: str) -> str:
    """Name a stage-specific task, used only when a stage runs standalone."""
    return config.task_name if stage == "pipeline" else f"{config.task_name}/{stage}"


class ArtifactUploadError(RuntimeError):
    """A required artifact or final upload barrier was rejected."""


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
    config_directory: TemporaryDirectory[str] | None = None

    def enter_stage(self, stage: str) -> None:
        self.current_stage = stage
        if stage not in self.stages:
            self.stages.append(stage)

    def manifest(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "task_id": str(self.task.id),
            "stages": list(self.stages),
            "artifacts": [dataclasses.asdict(artifact) for artifact in self.artifacts],
        }

    def config_path(self, suffix: str) -> Path:
        if self.config_directory is None:
            self.config_directory = TemporaryDirectory(prefix="clearml-yolo-config-")
        return Path(self.config_directory.name) / f"{len(self.artifacts):04d}{suffix}"

    def cleanup(self) -> None:
        if self.config_directory is not None:
            self.config_directory.cleanup()


_ACTIVE_INVOCATION: ContextVar[_InvocationState | None] = ContextVar(
    "clearml_yolo_active_invocation", default=None
)


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
    _sync_upload(state.task, ARTIFACT_MANIFEST, state.manifest())
    if state.task.flush(wait_for_uploads=True) is not True:
        raise ArtifactUploadError("ClearML flush did not confirm completion")
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


@contextmanager
def invocation(
    config: ClearMLConfig, stage: str, resolved_config: Any | None = None
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
    state = _InvocationState(task=task, stages=[stage], current_stage=stage)
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
    try:
        if resolved_config is not None:
            sanitized = sanitize_configuration(resolved_config)
            task.connect_configuration(
                configuration=sanitized,
                name="resolved",
                ignore_remote_overrides=True,
            )
            expect_artifacts(task, [RESOLVED_CONFIGURATION])
            upload_artifact(task, RESOLVED_CONFIGURATION, sanitized)
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
        if previous_owner is None:
            os.environ.pop(OWNER_PID_ENV, None)
        else:
            os.environ[OWNER_PID_ENV] = previous_owner
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


def _sanitized_config_file(state: _InvocationState, path: Path) -> Path:
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file does not exist: {path}")
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            content = json.loads(path.read_text(encoding="utf-8"))
        elif suffix in {".yaml", ".yml"}:
            content = yaml.safe_load(path.read_text(encoding="utf-8"))
        else:
            raise ValueError(f"Unsupported configuration file format: {path.suffix or '<none>'}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON configuration file: {path}") from None
    except yaml.YAMLError:
        raise ValueError(f"Invalid YAML configuration file: {path}") from None

    sanitized_path = state.config_path(suffix)
    sanitized = sanitize_configuration(content)
    if suffix == ".json":
        sanitized_path.write_text(
            json.dumps(sanitized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    else:
        sanitized_path.write_text(
            yaml.safe_dump(sanitized, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
    return sanitized_path


def connect_config_file(
    task: Any, name: str, path: Path, *, allow_remote_override: bool = True
) -> Path:
    """Store a file the run is configured by on the task, and return the path to read.

    The sanitized file is attached as both a ClearML configuration object and a downloadable
    artifact, so the run remains reproducible without exposing credentials or depending on
    the machine it ran on.

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
        sanitized_path = _sanitized_config_file(active, path)
    elif allow_remote_override and not task.running_locally():
        # A cloned task can supply its attached source without the original host path.
        sanitized_path = active.config_path(path.suffix or ".yaml")
        sanitized_path.write_text("{}\n", encoding="utf-8")
    else:
        raise FileNotFoundError(f"Configuration file does not exist: {path}")
    if not any(artifact.name == name for artifact in active.artifacts):
        expect_artifacts(task, [name])
    connected = Path(
        task.connect_configuration(
            configuration=sanitized_path,
            name=name,
            ignore_remote_overrides=not allow_remote_override,
        )
    )
    if connected == sanitized_path and not path.is_file():
        raise FileNotFoundError(f"Remote task has no attached configuration for {path}")
    effective = _sanitized_config_file(active, connected)
    task.connect_configuration(
        configuration=effective,
        name=name,
        ignore_remote_overrides=True,
    )
    upload_artifact(task, name, effective)
    logger.info("Connected {} to ClearML as configuration {!r}", path, name)
    # Sanitization is for storage, not model execution: preserve local source values
    # (including externally managed credentials) or use the clone's effective source.
    return path if connected == sanitized_path and path.is_file() else connected
