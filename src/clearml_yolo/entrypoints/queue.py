"""Submit and manage durable, per-host, owner-executed pipeline jobs."""

import argparse
import json
import signal
import socket
import sys
import time
from collections import Counter
from pathlib import Path
from types import FrameType
from typing import Never, override

from loguru import logger

from clearml_yolo.application.queue import QueueGPUControlPort, QueueService
from clearml_yolo.core.queue import (
    MoveDirection,
    PublicJob,
    QueueView,
    QueueVisibility,
    ResourceRequest,
    resolve_job_reference,
)
from clearml_yolo.entrypoints.queue_presentation import QueuePresentation

_HEARTBEAT_SECONDS = 60


class _QueueParser(argparse.ArgumentParser):
    @override
    def exit(self, status: int = 0, message: str | None = None) -> Never:
        super().exit(status, QueuePresentation().text(message) if message else message)


def _parser() -> argparse.ArgumentParser:
    parser = _QueueParser(prog="cy-queue", description=__doc__)
    parser.add_argument("--root", type=Path, help="Override the configured shared metadata root")
    commands = parser.add_subparsers(dest="action", required=True)
    config = commands.add_parser(
        "config", help="Inspect user queue.toml or CY_QUEUE_CONFIG without starting a queue"
    )
    config.add_argument("--json", action="store_true")
    submit = commands.add_parser("submit", help="Freeze and submit one pipeline or Hydra sweep")
    resources = submit.add_mutually_exclusive_group(required=True)
    resources.add_argument("--gpus", type=int)
    resources.add_argument("--devices", help="Exact ordered CUDA indexes, e.g. 0,2")
    submit.add_argument("--label", help="Readable job name (default configured ClearML task name)")
    submit.add_argument("--json", action="store_true", help="Print machine-readable job records")
    submit.add_argument("overrides", nargs=argparse.REMAINDER)
    worker = commands.add_parser("worker", help="Serve this Unix user's jobs until stopped")
    worker.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
        help="Worker stderr verbosity (default INFO; DEBUG includes every poll)",
    )
    listing = commands.add_parser("list", help="Show public job summaries")
    listing.add_argument("--host", help="Read another host partition")
    listing.add_argument("--json", action="store_true")
    views = listing.add_mutually_exclusive_group()
    views.add_argument("--archived", dest="visibility", action="store_const", const="archived")
    views.add_argument("--all", dest="visibility", action="store_const", const="all")
    listing.set_defaults(visibility="main")
    move = commands.add_parser("move", help="Reorder a pending job with optimistic concurrency")
    move.add_argument("job_id", metavar="JOB", help="Stable reference, e.g. job-17")
    move.add_argument("direction", choices=("up", "down", "top", "bottom", "before", "after"))
    move.add_argument("relative_job_id", nargs="?")
    move.add_argument("--revision", type=int, required=True, help="Revision from list --json")
    move.add_argument("--json", action="store_true")
    for action in ("cancel", "recover"):
        command = commands.add_parser(action, help=f"{action.capitalize()} one owned job")
        command.add_argument("job_id", metavar="JOB", help="Stable reference, e.g. job-17")
        command.add_argument("--json", action="store_true")
    for action in ("archive", "restore"):
        command = commands.add_parser(action, help=f"{action.capitalize()} owned finished jobs")
        command.add_argument("job_ids", metavar="JOB", nargs="+")
        command.add_argument("--json", action="store_true")
    commands.add_parser("tui", help="Open the optional Textual queue interface")
    gpu = commands.add_parser("gpu", help="Inspect and control physical host GPUs")
    operations = gpu.add_subparsers(dest="gpu_action", required=True)
    gpu_list = operations.add_parser("list", help="List physical GPU numbers, holds and jobs")
    gpu_list.add_argument("--json", action="store_true")
    disable = operations.add_parser("disable", help="Hold a physical GPU for this Unix owner")
    disable.add_argument("selector", help="Physical GPU number or displayed short GPU label")
    disable.add_argument("--json", action="store_true")
    enable = operations.add_parser("enable", help="Remove only your hold on a physical GPU")
    enable.add_argument("selector", help="Physical GPU number or displayed short GPU label")
    enable.add_argument("--json", action="store_true")
    for action in ("free", "release"):
        release = operations.add_parser(action, help="Free one GPU's reservation and holds")
        release.add_argument("selector", help="Physical GPU number or displayed short GPU label")
        release.add_argument("--json", action="store_true")
    return parser


def _show(
    view: QueueView,
    *,
    as_json: bool = False,
    presentation: QueuePresentation | None = None,
) -> None:
    presentation = presentation or QueuePresentation()
    if as_json:
        sys.stdout.write(json.dumps(presentation.view(view)) + "\n")
        return
    messages = presentation.refresh_messages(view)
    sys.stdout.write(
        f"{presentation.queue_name} | {presentation.host(view.host_id)} | "
        f"revision {view.revision} | archived {len(view.archived_job_ids)} | "
        f"warnings {len(messages)}\n"
    )
    for position, job in enumerate(view.jobs, 1):
        request = presentation.request(job.request, job.host_id)
        allocation = ",".join(presentation.devices(job.devices, job.host_id)) or "-"
        reason = presentation.text(job.waiting_reason or "", job.host_id)
        state = job.state + (" (archived)" if job.id in view.archived_job_ids else "")
        diagnostic = f"\t{messages[job.id]}" if job.id in messages else ""
        sys.stdout.write(
            f"{position}\t{presentation.job_title(job)}\tuid={job.owner_uid}\t{state}\t"
            f"request={request}\tallocation={allocation}\t{reason}{diagnostic}\n"
        )


def _presentation(host_id: str, *, queue_name: str = "Queue") -> QueuePresentation:
    from clearml_yolo.adapters.runtime.gpu_resources import GPUInventory

    try:
        physical = GPUInventory().physical_uuids()
    except Exception as error:  # noqa: BLE001 - optional display metadata from opaque NVML
        logger.debug(
            "GPU indexes unavailable; using short labels: {}",
            QueuePresentation().text(str(error)),
        )
        physical = ()
    return QueuePresentation(
        {uuid: index for index, uuid in enumerate(physical)},
        host_id=host_id,
        host_name=socket.gethostname(),
        queue_name=queue_name,
    )


def _resource_request(arguments: argparse.Namespace) -> ResourceRequest:
    if arguments.devices is None:
        return ResourceRequest(gpus=arguments.gpus)
    from clearml_yolo.adapters.runtime.gpu_resources import GPUInventory

    try:
        indexes = tuple(int(part.strip()) for part in arguments.devices.split(","))
    except ValueError as error:
        raise ValueError(
            "--devices must contain comma-separated nonnegative CUDA indexes"
        ) from error
    if not indexes or any(index < 0 for index in indexes) or len(set(indexes)) != len(indexes):
        raise ValueError("--devices must contain unique nonnegative CUDA indexes")
    visible = GPUInventory().visible()
    if any(index >= len(visible) for index in indexes):
        raise ValueError("--devices selects a GPU outside the inherited CUDA visibility")
    return ResourceRequest(devices=tuple(visible[index] for index in indexes))


def _direction(value: str) -> MoveDirection:
    # argparse restricts this boundary, and the exhaustive match keeps the port typed.
    match value:
        case "up" | "down" | "top" | "bottom" | "before" | "after":
            return value
        case _:
            raise ValueError("Unknown move direction")


def main() -> None:
    parser = _parser()
    arguments = parser.parse_args()
    if arguments.action == "worker":
        logger.remove()
        logger.add(
            sys.stderr,
            level=arguments.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}",
            backtrace=False,
            diagnose=False,
        )
    try:
        _execute(arguments)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"cy-queue: {error}\n")


class _WorkerLog:
    """Render public owner observations without logging unchanged poll timestamps."""

    def __init__(self, owner_uid: int, presentation: QueuePresentation | None = None) -> None:
        self.owner_uid = owner_uid
        self.presentation = presentation or QueuePresentation()
        self._jobs: dict[str, tuple[object, ...]] = {}
        self._last_heartbeat: float | None = None

    def __call__(self, view: QueueView) -> None:
        jobs = tuple(job for job in view.jobs if job.owner_uid == self.owner_uid)
        initial = self._last_heartbeat is None
        current: dict[str, tuple[object, ...]] = {}
        for job in jobs:
            status = (job.state, job.devices, job.waiting_reason, job.progress, job.error)
            current[job.id] = status
            if self._jobs.get(job.id) == status:
                continue
            # Existing completed history is counted, without replaying every old job.
            if initial and job.state in {"completed", "failed", "cancelled"}:
                continue
            level = "ERROR" if job.state in {"failed", "recovery_required"} else "INFO"
            details = (
                f"{self.presentation.job_title(job)} | state={job.state} | "
                f"request={self.presentation.request(job.request, job.host_id)} | "
                f"allocation={','.join(self.presentation.devices(job.devices, job.host_id)) or '-'}"
            )
            if job.waiting_reason:
                details += f" | waiting={job.waiting_reason}"
            if job.progress is not None:
                details += f" | progress={job.progress}"
            if job.error:
                details += f" | error={job.error}"
            logger.log(
                level,
                "{}",
                self.presentation.text(details, job.host_id)
                .replace("\n", "\\n")
                .replace("\r", "\\r"),
            )
        self._jobs = current
        counts = Counter(job.state for job in jobs)
        summary = " ".join(f"{state}={count}" for state, count in sorted(counts.items()))
        active = any(
            job.state in {"pending", "starting", "running", "cancelling", "recovery_required"}
            for job in jobs
        )
        now = time.monotonic()
        if self._last_heartbeat is None or now - self._last_heartbeat >= _HEARTBEAT_SECONDS:
            logger.info(
                "Worker heartbeat | {} | {}", "active" if active else "idle", summary or "no jobs"
            )
            self._last_heartbeat = now
        logger.debug(
            "Worker poll | host={} uid={} | {}",
            self.presentation.host(view.host_id),
            self.owner_uid,
            summary or "no jobs",
        )


def _worker(service: QueueService, presentation: QueuePresentation | None = None) -> None:
    stopped = False

    def stop(_signum: int, _frame: FrameType | None) -> None:
        nonlocal stopped
        stopped = True

    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        service.worker(
            lambda: stopped,
            observe=_WorkerLog(
                service.identity.owner_uid,
                presentation or _presentation(service.identity.host_id),
            ),
        )
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    logger.info("Queue worker stopped; active jobs remain supervised by their guardians")


def _tui(service: QueueService, presentation: QueuePresentation | None = None) -> None:
    try:
        from clearml_yolo.entrypoints.queue_tui import QueueApp
    except ModuleNotFoundError as error:
        if error.name and error.name.startswith("textual"):
            raise RuntimeError(
                "The clearml-yolo installation is missing textual; "
                "reinstall its default dependencies"
            ) from error
        raise
    QueueApp(service, presentation=presentation or _presentation(service.identity.host_id)).run()


def _execute(arguments: argparse.Namespace) -> None:
    from clearml_yolo.adapters.queue.settings import load_queue_settings

    settings = load_queue_settings(arguments.root)
    if arguments.action == "config":
        values = {
            "name": settings.name,
            "root": str(settings.root),
            "coordination_root": str(settings.coordination_root),
            "config_path": str(settings.config_path),
            "root_source": settings.root_source,
        }
        if arguments.json:
            sys.stdout.write(json.dumps(values) + "\n")
        else:
            presentation = QueuePresentation()
            for key, value in values.items():
                sys.stdout.write(f"{key.replace('_', ' ')}: {presentation.text(value)}\n")
        return

    from clearml_yolo.adapters.queue.coordination import bind_coordination_root
    from clearml_yolo.adapters.queue.gpu_controls import GPUControls
    from clearml_yolo.adapters.queue.identity import current_identity
    from clearml_yolo.adapters.queue.locks import LocalGPULocks

    identity = current_identity()
    bind_coordination_root(identity.host_id, settings.coordination_root)
    if arguments.action == "gpu":
        _gpu_operation(GPUControls(LocalGPULocks(identity, settings.coordination_root)), arguments)
        return

    from clearml_yolo.adapters.queue.inventory import QueueGPUInventory
    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment

    root = initialize_runtime_environment()
    storage = NFSQueueStore(settings.root, identity, local_root=settings.coordination_root)
    processes = QueueProcesses(storage, identity, local_root=settings.coordination_root)
    service = QueueService(
        storage,
        QueueGPUInventory(),
        processes,
        identity,
        controls=GPUControls(processes.pool),
    )
    if arguments.action == "worker":
        logger.info(
            "{}",
            QueuePresentation().text(
                f"Starting queue worker | queue={settings.name} root={storage.root} "
                f"host={socket.gethostname()} "
                f"uid={identity.owner_uid} max_used_memory_gib=2.0"
            ),
        )
    _queue_operation(
        service,
        arguments,
        root,
        presentation=_presentation(identity.host_id, queue_name=settings.name),
    )


def _queue_operation(
    service: QueueService,
    arguments: argparse.Namespace,
    root: Path,
    *,
    presentation: QueuePresentation | None = None,
) -> None:
    presentation = presentation or _presentation(service.identity.host_id)
    match arguments.action:
        case "submit":
            _submit(service, arguments, root, presentation)
        case "list":
            _show(
                service.list(arguments.host, visibility=_visibility(arguments.visibility)),
                as_json=arguments.json,
                presentation=presentation,
            )
        case "move":
            _show(
                service.move(
                    arguments.job_id,
                    _direction(arguments.direction),
                    arguments.revision,
                    relative_job_id=arguments.relative_job_id,
                ),
                as_json=arguments.json,
                presentation=presentation,
            )
        case "cancel":
            job = service.cancel(arguments.job_id)
            _show_job(job, presentation, as_json=arguments.json)
        case "recover":
            job = service.recover(arguments.job_id)
            _show_job(job, presentation, as_json=arguments.json)
        case "archive" | "restore":
            jobs = service.list(visibility="all").jobs
            targets = tuple(
                dict.fromkeys(resolve_job_reference(jobs, ref).id for ref in arguments.job_ids)
            )
            view = (
                service.archive(targets)
                if arguments.action == "archive"
                else service.restore(targets)
            )
            if not arguments.json:
                verb = "Archived" if arguments.action == "archive" else "Restored"
                sys.stdout.write(f"{verb} {len(targets)} job(s)\n")
            _show(view, as_json=arguments.json, presentation=presentation)
        case "worker":
            _worker(service, presentation)
        case "tui":
            _tui(service, presentation)
        case _:
            raise ValueError("Unknown queue operation")


def _submit(
    service: QueueService,
    arguments: argparse.Namespace,
    root: Path,
    presentation: QueuePresentation,
) -> None:
    from clearml_yolo.entrypoints.hydra.queue_config import compose_snapshots

    values = arguments.overrides
    if values and values[0] == "--":
        values = values[1:]
    snapshots = compose_snapshots(values, _resource_request(arguments), project_root=root)
    if arguments.label is not None:
        if not arguments.label.strip():
            raise ValueError("Job label must be nonempty")
        snapshots = tuple(
            snapshot.model_copy(update={"label": arguments.label}) for snapshot in snapshots
        )
    jobs = service.submit(snapshots)
    if arguments.json:
        sys.stdout.write(json.dumps([presentation.job(job) for job in jobs]) + "\n")
    else:
        for job in jobs:
            sys.stdout.write(f"Submitted {presentation.job_title(job)}\n")


def _visibility(value: str) -> QueueVisibility:
    match value:
        case "main" | "archived" | "all":
            return value
        case _:
            raise ValueError("Unknown queue view")


def _show_job(job: PublicJob, presentation: QueuePresentation, *, as_json: bool) -> None:
    if as_json:
        sys.stdout.write(json.dumps(presentation.job(job)) + "\n")
    else:
        sys.stdout.write(f"{presentation.job_title(job)}: {job.state}\n")


def _gpu_operation(controls: QueueGPUControlPort, arguments: argparse.Namespace) -> None:
    match arguments.gpu_action:
        case "list":
            cards = controls.list()
            presentation = QueuePresentation(
                {
                    card.uuid: card.physical_index
                    for card in cards
                    if card.physical_index is not None
                }
            )
            if arguments.json:
                sys.stdout.write(json.dumps([presentation.gpu(card) for card in cards]) + "\n")
            else:
                for card in cards:
                    holds = "; ".join(f"uid={hold.owner_uid}" for hold in card.holds)
                    job = f"owned by user {card.claim.owner_uid}" if card.claim else "-"
                    sys.stdout.write(
                        f"{presentation.device(card.uuid)}\tholds={holds or '-'}\tjob={job}\n"
                    )
        case "disable":
            hold = controls.disable(arguments.selector)
            presentation = _selector_presentation(arguments.selector, hold.uuid)
            if arguments.json:
                sys.stdout.write(json.dumps(presentation.hold(hold)) + "\n")
            else:
                sys.stdout.write(f"GPU {presentation.device(hold.uuid)}: own hold added\n")
        case "enable":
            controls.enable(arguments.selector)
            sys.stdout.write(
                json.dumps({"status": "hold removed"}) + "\n"
                if arguments.json
                else "Own GPU hold removed\n"
            )
        case "free" | "release":
            result = controls.release(arguments.selector)
            presentation = _selector_presentation(arguments.selector, result.uuid)
            if arguments.json:
                sys.stdout.write(json.dumps(presentation.freed(result)) + "\n")
            else:
                sys.stdout.write(
                    f"GPU {presentation.device(result.uuid)}: reservations and holds cleared\n"
                )
        case _:
            raise ValueError("Unknown GPU control operation")


def _selector_presentation(selector: str, uuid: str) -> QueuePresentation:
    # The completed control already resolved identity: never add a second lookup.
    return QueuePresentation({uuid: int(selector)} if selector.isdecimal() else {})


if __name__ == "__main__":
    main()
