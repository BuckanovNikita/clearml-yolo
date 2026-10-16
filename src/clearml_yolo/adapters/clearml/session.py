"""ClearML task lifecycle shared by every app.

A single task is created per invocation and reused by all stages of the pipeline, so
that training scalars, prediction artifacts, per-split metrics and the comparison
reports all land on one experiment.
"""

import copy
import hashlib
import json
import os
import re
import shutil
import signal
import sys
import threading
from collections.abc import Callable, Iterator, Mapping
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, cast
from urllib.parse import parse_qsl, urlsplit

from loguru import logger
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import YAMLError
from ruamel.yaml.tokens import CommentToken

from clearml_yolo.adapters.clearml.console import ConsolePublicationError, ConsolePublisher
from clearml_yolo.adapters.clearml.deadline import (
    TaskFinalizationError,
    detach_sdk_exit_callback,
    sdk_deadline,
)
from clearml_yolo.adapters.clearml.script import publish_script
from clearml_yolo.adapters.observability.capture import (
    OutputCapture,
    active_capture,
    capture_output,
    write_progress,
)
from clearml_yolo.adapters.observability.diagnostics import (
    exception_summary,
    log_exception,
    log_exception_safely,
)
from clearml_yolo.adapters.observability.tracing import trace_operation, trace_task
from clearml_yolo.adapters.storage.filesystem import temporary_root
from clearml_yolo.application.contracts import (
    ClearMLConfig as ClearMLConfig,  # noqa: PLC0414 - typed adapter interface
)
from clearml_yolo.core.redaction import (
    sanitize_configuration as sanitize_configuration,  # noqa: PLC0414 - typed adapter re-export
)
from clearml_yolo.core.redaction import (
    sanitize_url as _sanitize_url,
)
from clearml_yolo.core.redaction import (
    sensitive_key as _sensitive_key,
)

OWNER_PID_ENV = "CY_CLEARML_OWNER_PID"
OWNER_TASK_ENV = "CY_CLEARML_OWNER_TASK_ID"
REDACTED = "<redacted>"

DEFAULT_PROJECT_NAME = "clearml-yolo"
# Task.close drains the reporter again after our required publication flush. Each
# drain can wait a reporting interval; budget both, model/readback work and the
# console barrier without changing SDK timing or allowing unbounded shutdown.
FINALIZATION_TIMEOUT_SECONDS = 600.0

# Keep the SDK opaque at the adapter boundary so reporting modules need no SDK import.
Task = Any


def resolve_task_name(config: ClearMLConfig, stage: str) -> str:
    """Name a stage-specific task, used only when a stage runs standalone."""
    return config.task_name if stage == "pipeline" else f"{config.task_name}/{stage}"


def task_identity(task: Any) -> tuple[str, str, str]:
    """Snapshot routing identity once; display renaming never relocates files."""
    active = _ACTIVE_INVOCATION.get()
    if active is not None and task is active.task and active.routing_identity is not None:
        return active.routing_identity
    values = (task.get_project_name(), task.name, task.id)
    if any(not isinstance(value, str) or not value for value in values):
        raise ValueError("Active ClearML task requires a project name, task name and ID")
    if active is not None and task is active.task:
        active.routing_identity = values
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
    config_directory: Path | None = None
    config_resolver: Callable[[Any], Any] | None = None
    config_file_count: int = 0
    execution_config_paths: list[Path] = field(default_factory=list)
    finalizers: list[Callable[[], None]] = field(default_factory=list)
    resources: dict[str, object] = field(default_factory=dict)
    routing_identity: tuple[str, str, str] | None = None
    console_publisher: ConsolePublisher | None = None

    def enter_stage(self, stage: str) -> None:
        self.current_stage = stage
        if stage not in self.stages:
            self.stages.append(stage)

    def config_path(self, suffix: str) -> Path:
        if self.config_directory is None:
            self.config_directory = Path(
                mkdtemp(prefix="clearml-yolo-config-", dir=temporary_root())
            )
        path = self.config_directory / f"{self.config_file_count:04d}{suffix}"
        self.config_file_count += 1
        return path

    def execution_config_path(self, source: Path) -> Path:
        path = self.config_path(source.suffix)
        self.execution_config_paths.append(path)
        return path

    def cleanup(self) -> None:
        for path in self.execution_config_paths:
            path.unlink(missing_ok=True)
        if self.config_directory is not None:
            shutil.rmtree(self.config_directory)


_ACTIVE_INVOCATION: ContextVar[_InvocationState | None] = ContextVar(
    "clearml_yolo_active_invocation", default=None
)


@dataclass
class _IncompleteOwner:
    pid: int | None = None
    task: Any = None
    close_attempted: bool = False


# ClearML retains its SDK main task after incomplete shutdown, even when its exit
# callback is detached. Keep a separate inert guard, including after partial init.
# A fork inherits uncertain SDK state; only a fresh interpreter resets this guard.
_INCOMPLETE_OWNER = _IncompleteOwner()


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
    if owner_pid and os.environ.get(OWNER_TASK_ENV) and owner_pid != str(os.getpid()):
        return True
    local_rank = os.environ.get("LOCAL_RANK")
    if (
        local_rank is not None
        and local_rank != "-1"
        and not (owner_pid and os.environ.get(OWNER_TASK_ENV))
    ):
        raise ValueError(
            "Top-level LOCAL_RANK launches are unsupported; invoke the cy command directly"
        )
    return False


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
    with trace_operation("clearml.task.mark_failed", cleanup=True):
        task.mark_failed(
            ignore_errors=False,
            force=True,
            status_reason=reason,
            status_message=message,
        )


def _sync_upload(task: Any, name: str, artifact_object: Any) -> None:
    with trace_operation("clearml.artifact.upload", context={"artifact": name}):
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
    for finalize in state.finalizers:
        with trace_operation("clearml.publication.finalizer"):
            finalize()
    missing = [
        artifact.name for artifact in state.artifacts if artifact.required and not artifact.uploaded
    ]
    if missing:
        raise ArtifactUploadError(f"Required artifacts were not uploaded: {', '.join(missing)}")
    if state.model_barriers:
        from clearml import OutputModel

        with trace_operation("clearml.model.wait_uploads"):
            OutputModel.wait_for_uploads()
    with trace_operation("clearml.task.flush"):
        if state.task.flush(wait_for_uploads=True) is not True:
            raise ArtifactUploadError("ClearML flush did not confirm completion")
    if state.model_barriers:
        with trace_operation("clearml.task.reload"):
            state.task.reload()
        for verify in state.model_barriers:
            with trace_operation("clearml.model.verify"):
                verify()
    if state.console_publisher is not None:
        state.console_publisher.barrier()
    # close() waits for repository detection and shuts down the status monitor.
    # Marking completed first makes that monitor interpret our own success as an
    # external abort while background configuration uploads are still running.
    with trace_operation("clearml.task.terminal", cleanup=True):
        closed_task = _close_task(state.task)
        with trace_operation("clearml.task.mark_completed", cleanup=True):
            closed_task.mark_completed(ignore_errors=False, force=True)


def _close_task(task: Any) -> Any:
    task_id = str(task.id)
    with trace_operation("clearml.task.close", cleanup=True):
        owner = _INCOMPLETE_OWNER
        owns_task = owner.pid == os.getpid() and owner.task is task
        if owns_task:
            owner.close_attempted = True
        try:
            task.close()
            # This public SDK getter is inert. close() can suppress a shutdown error
            # before releasing its main task, or return without work after interruption.
            main_task_retained = task.is_main_task() is not False
        except BaseException:
            detach_sdk_exit_callback(task)
            raise
        if main_task_retained:
            detach_sdk_exit_callback(task)
            raise TaskFinalizationError("ClearML owner remained active after close")
        if owns_task:
            # Remote readback/status failures cannot revive a confirmed closed SDK owner.
            owner.pid = None
            owner.task = None
            owner.close_attempted = False
    from clearml import Task

    with trace_operation("clearml.task.readback", cleanup=True):
        return Task.get_task(task_id=task_id)


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


def _start_console_publisher(task: Any, capture: OutputCapture) -> ConsolePublisher:
    offline = Path(task.get_offline_mode_folder()) if task.is_offline() else None
    try:
        publisher = ConsolePublisher(str(task.id), capture, offline_folder=offline)
        publisher.start()
    except OSError as error:
        raise ConsolePublicationError(
            "Console publisher could not start; local logs retained"
        ) from error
    return publisher


def _close_for_failure(state: _InvocationState, error: BaseException) -> Any:
    task = state.task
    owner = _INCOMPLETE_OWNER
    if owner.pid == os.getpid() and owner.task is task and owner.close_attempted:
        # SDK shutdown records entry before draining; a retry can return a no-op
        # while its main task remains alive. Keep uncertain closure quarantined.
        detach_sdk_exit_callback(task)
        return task
    if isinstance(error, ConsolePublicationError):
        detach_sdk_exit_callback(task)
        return task
    if state.console_publisher is not None:
        try:
            state.console_publisher.barrier()
        except ConsolePublicationError as publication_error:
            # Task.close and the SDK exit hook can mark completed. Neither may run
            # while required workload delivery remains unacknowledged.
            detach_sdk_exit_callback(task)
            log_exception_safely("Console publication barrier failed", publication_error)
            return task
    return _close_task(task)


def _release_failure_monitor(state: _InvocationState) -> None:
    """Stop only this owner's monitor before publishing its own failed status."""
    _active_state(state.task, "Failure monitor release")
    with trace_operation("clearml.task.failure_monitor.release", cleanup=True):
        # ClearML exposes no public monitor release. Its opaque, owner-bound
        # compatibility field is needed because an active DevWorker interprets
        # our own mark_failed as external abort and can stop/kill the owner tree.
        missing = object()
        monitor = getattr(state.task, "_dev_worker", missing)
        if monitor is missing:
            raise TaskFinalizationError(
                "Installed ClearML SDK cannot release the owner status monitor"
            )
        if monitor is None:
            return
        unregister = getattr(monitor, "unregister", None)
        if not callable(unregister):
            raise TaskFinalizationError(
                "Installed ClearML SDK cannot release the owner status monitor"
            )
        if unregister() is not True:
            raise TaskFinalizationError("ClearML owner status monitor did not confirm release")


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

    if _INCOMPLETE_OWNER.pid is not None:
        raise RuntimeError(
            "Previous ClearML owner did not confirm closure; "
            "start a fresh process before another invocation"
        )

    owns_signal = threading.current_thread() is threading.main_thread()
    previous_sigterm: Any = signal.getsignal(signal.SIGTERM) if owns_signal else None

    from clearml import Task

    with ExitStack() as stack:
        captured = active_capture()
        if captured is None:
            directory = Path(mkdtemp(prefix="cy-console-", dir=temporary_root()))
            captured = stack.enter_context(capture_output(directory))
        with trace_operation("clearml.task.create", context={"stage": stage}):
            _INCOMPLETE_OWNER.pid = os.getpid()
            _INCOMPLETE_OWNER.task = None
            _INCOMPLETE_OWNER.close_attempted = False
            task: Any = Task.init(
                project_name=config.project_name,
                task_name=resolve_task_name(config, stage),
                task_type=config.task_type,
                tags=config.tags or None,
                output_uri=config.output_uri,
                reuse_last_task_id=False,
                auto_connect_arg_parser=False,
                # FD capture owns native/child output; SDK stream patching duplicates it.
                auto_connect_streams=False,
                # Explicit script publication below owns Git identity without raw diffs/argv.
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
            _INCOMPLETE_OWNER.task = task
            state = stack.enter_context(
                _task_owner(task, config, stage, config_resolver, owns_signal, previous_sigterm)
            )
            state.console_publisher = _start_console_publisher(task, captured)
            publish_script(task, stage)
            write_progress(task_url=str(task.get_output_log_web_page()))
        if resolved_config is not None:
            _replay_initial_configuration(task, resolved_config)
        yield task
        with sdk_deadline(FINALIZATION_TIMEOUT_SECONDS):
            _finalize(state)


@contextmanager
def _task_owner(
    task: Any,
    config: ClearMLConfig,
    stage: str,
    config_resolver: Callable[[Any], Any] | None,
    owns_signal: bool,
    previous_sigterm: Any,
) -> Iterator[_InvocationState]:
    """Register terminal handling before task creation diagnostics can interrupt."""
    task_id = str(task.id)
    with trace_task(task_id):
        state = _InvocationState(
            task=task, stages=[stage], current_stage=stage, config_resolver=config_resolver
        )
        token = _ACTIVE_INVOCATION.set(state)
        previous_owner = os.environ.get(OWNER_PID_ENV)
        os.environ[OWNER_PID_ENV] = str(os.getpid())
        if owns_signal:
            signal.signal(signal.SIGTERM, _exit_on_signal)

        previous_task_id = os.environ.get(OWNER_TASK_ENV)
        os.environ[OWNER_TASK_ENV] = str(task.id)
        primary_error: BaseException | None = None
        try:
            logger.info(
                "ClearML task {} created: project={!r} name={!r}",
                task.id,
                config.project_name,
                resolve_task_name(config, stage),
            )
            yield state
        except BaseException as error:
            primary_error = error
            # Include the original safe diagnostic before the publisher's final barrier.
            log_exception_safely("Invocation failed", error, context={"task_id": task_id})
            if isinstance(error, TaskFinalizationError):
                detach_sdk_exit_callback(task)
            try:
                with (
                    sdk_deadline(FINALIZATION_TIMEOUT_SECONDS),
                    trace_operation("clearml.task.failure_cleanup", cleanup=True),
                ):
                    _release_failure_monitor(state)
                    closed_task = _close_for_failure(state, error)
                    _mark_failed(closed_task, error)
            except BaseException as finalization_error:  # noqa: BLE001 - preserve the original failure
                detach_sdk_exit_callback(task)
                log_exception_safely(
                    "ClearML failure finalization failed",
                    finalization_error,
                    context={"task_id": task_id},
                )
            raise
        finally:
            if owns_signal:
                signal.signal(signal.SIGTERM, previous_sigterm)
            _restore_environment(OWNER_PID_ENV, previous_owner)
            _restore_environment(OWNER_TASK_ENV, previous_task_id)
            _ACTIVE_INVOCATION.reset(token)
            try:
                _cleanup_invocation(state, primary_error)
            finally:
                _finish_incomplete_owner_handler(state)
                # SDK close/status and cleanup diagnostics belong in the final EOF.
                _finish_console(state, primary_error or sys.exception())


def _finish_incomplete_owner_handler(state: _InvocationState) -> None:
    """Make only this incomplete owner's cached logging handler inert at exit."""
    owner = _INCOMPLETE_OWNER
    if owner.pid != os.getpid() or owner.task is not state.task:
        return
    # SDK logging has an independent handler even with stream capture disabled.
    # Use cached compatibility fields; get_logger() would create new SDK work.
    sdk_logger = getattr(state.task, "_logger", None)
    handler = getattr(sdk_logger, "_task_handler", None)
    if handler is None:
        return
    try:
        # TaskHandler clears its task/service references before joining. Its
        # monitor can swallow the alarm at join, so use this timer for no later
        # status/publication operation and never infer daemon completion here.
        with sdk_deadline(FINALIZATION_TIMEOUT_SECONDS):
            detach_sdk_exit_callback(state.task)
            with trace_operation("clearml.task.failure_handler.close", cleanup=True):
                handler.close(wait=False)
    except BaseException as error:  # noqa: BLE001 - preserve the original invocation failure
        log_exception_safely("ClearML failure logging handler cleanup failed", error)


def _finish_console(state: _InvocationState, primary_error: BaseException | None) -> None:
    if state.console_publisher is None:
        return
    try:
        with sdk_deadline(FINALIZATION_TIMEOUT_SECONDS):
            state.console_publisher.finish()
    except BaseException as error:
        if isinstance(error, TaskFinalizationError):
            detach_sdk_exit_callback(state.task)
        if primary_error is not None:
            log_exception_safely("Console publication failed", error)
            return
        try:
            # Only the session owner corrects task state after required final delivery fails.
            from clearml import Task

            with sdk_deadline(FINALIZATION_TIMEOUT_SECONDS):
                closed_task: Any = Task.get_task(task_id=str(state.task.id))
                _mark_failed(closed_task, error)
        except BaseException as status_error:  # noqa: BLE001 - required delivery error remains primary
            if isinstance(status_error, TaskFinalizationError):
                detach_sdk_exit_callback(state.task)
            log_exception_safely("ClearML publication failure status update failed", status_error)
        raise


def _cleanup_invocation(state: _InvocationState, primary_error: BaseException | None) -> None:
    if primary_error is not None:
        # A failed close/upload may still have consumers; retain their input files.
        return
    with trace_operation("clearml.temporary.cleanup", cleanup=True):
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


def invocation_resource[T](task: Any, key: str, factory: Callable[[], T]) -> T:
    """Share an adapter-owned resource only within this owner invocation.

    Adapters own unique keys and their factory types; the registry intentionally
    knows no domain/resource types so dependency direction stays explicit.
    """
    active = _active_state(task, "Invocation resource access")
    if key not in active.resources:
        active.resources[key] = factory()
    return cast(T, active.resources[key])


def register_finalizer(task: Any, callback: Callable[[], None]) -> None:
    """Finish required publications before checking artifacts, models and flush."""
    if _is_worker():
        return
    _active_state(task, "Publication finalizer registration").finalizers.append(callback)


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


@trace_operation("clearml.configuration.record")
def record_run_configuration(task: Any, values: dict[str, Any]) -> dict[str, Any]:
    """Merge result provenance while preserving explicit native replay settings."""
    if _is_worker():
        return values
    active = _active_state(task, "Run configuration recording")
    sanitized = sanitize_configuration(values)
    cleaned = _meaningful(sanitized)
    # Export evidence mirrors its published sidecar: an empty plugin inventory or
    # detection list is meaningful and must survive configuration recording.
    preserve_empty = ("ultralytics", "ultralytics_predict", "export_result")
    if any(key in sanitized for key in preserve_empty):
        cleaned = {} if cleaned is _EMPTY else cleaned
        for key in preserve_empty:
            if key in sanitized:
                cleaned[key] = sanitized[key]
    if cleaned is _EMPTY:
        return dict(active.run_configuration)
    if not isinstance(cleaned, Mapping):
        raise TypeError("Run configuration must be a mapping")
    _merge_configuration(active.run_configuration, cleaned)
    with trace_operation("clearml.configuration.connect"):
        task.set_configuration_object(
            name="run",
            config_dict=_plain_config_document(active.run_configuration),
            config_type="dictionary",
        )
    return dict(active.run_configuration)


@trace_operation("clearml.configuration.replay")
def replay_configuration(task: Any, values: dict[str, Any]) -> dict[str, Any]:
    """Resolve a clone's canonical run object and freeze it for this invocation."""
    if _is_worker():
        return values
    active = _active_state(task, "Run configuration replay")
    if not values:
        raise ValueError("Canonical run configuration must not be empty")
    # Canonical replay must not inherit the SDK's ignore-override parameter or
    # expose connected proxy containers to Hydra/application configuration.
    canonical = None
    if not task.running_locally():
        with trace_operation("clearml.configuration.read"):
            canonical = task.get_configuration_object_as_dict("run")
            # The SDK also returns None for a present empty text blob. Only an
            # absent canonical object may fall back to executable CLI defaults.
            if canonical is None and task.get_configuration_object("run") is not None:
                raise ValueError("Effective ClearML run configuration must not be empty")
    effective = values if canonical is None else canonical
    if not isinstance(effective, Mapping):
        raise TypeError("ClearML run configuration override must be a mapping")
    if not effective:
        raise ValueError("Effective ClearML run configuration must not be empty")
    executable = _plain_config_document(effective)
    active.run_configuration = sanitize_configuration(executable)
    with trace_operation("clearml.configuration.connect"):
        task.set_configuration_object(
            name="run",
            config_dict=_plain_config_document(active.run_configuration),
            config_type="dictionary",
        )
    # Redaction is a storage boundary, not a mutation of executable inputs.
    return cast(dict[str, Any], executable)


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
    if isinstance(value, (list, tuple)):
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
    except json.JSONDecodeError as error:
        log_exception(
            "Invalid JSON configuration file",
            error,
            level="DEBUG",
            context={"source": path, "line": error.lineno, "column": error.colno},
            include_message=False,
        )
        raise ValueError(
            f"Invalid JSON configuration file: {path} (line {error.lineno}, column {error.colno})"
        ) from None
    except YAMLError as error:
        log_exception(
            "Invalid YAML configuration file",
            error,
            level="DEBUG",
            context={"source": path},
            include_message=False,
        )
        raise ValueError(
            f"Invalid YAML configuration file: {path}: "
            + exception_summary(error, include_message=False)
        ) from None


@trace_operation("clearml.configuration.prepare")
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
        except Exception as error:  # noqa: BLE001 - opaque resolver errors can contain credentials
            log_exception(
                "Configuration values could not be resolved",
                error,
                level="DEBUG",
                context={"source": path},
                include_message=False,
            )
            raise ValueError(
                "Configuration values could not be resolved: "
                + exception_summary(error, include_message=False)
            ) from None

    try:
        effective = _update_yaml_values(content, resolved) if suffix != ".json" else resolved
        execution_path = path
        if resolved != plain:
            execution_path = state.execution_config_path(path)
            executable = copy.deepcopy(effective)
            _write_config_document(execution_path, executable, yaml)
        sanitized_path = state.config_path(suffix)
        sanitized = _sanitize_yaml_configuration(
            copy.deepcopy(effective), _configuration_secrets(resolved) | provenance_secrets
        )
        _write_config_document(sanitized_path, sanitized, yaml)
    except Exception as error:  # noqa: BLE001 - parser/serializer details can contain credentials
        log_exception(
            "Configuration file could not be prepared",
            error,
            level="DEBUG",
            context={"source": path},
            include_message=False,
        )
        raise ValueError(
            "Configuration file could not be prepared: "
            + exception_summary(error, include_message=False)
        ) from None
    return execution_path, sanitized_path


@trace_operation("clearml.configuration.file")
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
    with trace_operation("clearml.configuration.connect"):
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
    with trace_operation("clearml.configuration.connect"):
        task.connect_configuration(
            configuration=sanitized_path,
            name=name,
            ignore_remote_overrides=True,
        )
    logger.info("Connected {} to ClearML as configuration {!r}", path, name)
    # Sanitization is for storage, not model execution: preserve local source values
    # (including externally managed credentials) or use the clone's effective source.
    return execution_path
