"""Submit and manage durable, per-host, owner-executed pipeline jobs."""

import argparse
import json
import os
import signal
import sys
import time
from collections import Counter
from pathlib import Path
from types import FrameType

from loguru import logger

from clearml_yolo.application.queue import QueueService
from clearml_yolo.core.queue import MoveDirection, QueueView, ResourceRequest
from clearml_yolo.core.redaction import redact_text

_HEARTBEAT_SECONDS = 60


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cy-queue", description=__doc__)
    parser.add_argument("--root", type=Path, help="Shared metadata root (default CY_QUEUE_ROOT)")
    commands = parser.add_subparsers(dest="action", required=True)
    submit = commands.add_parser("submit", help="Freeze and submit one pipeline or Hydra sweep")
    resources = submit.add_mutually_exclusive_group(required=True)
    resources.add_argument("--gpus", type=int)
    resources.add_argument("--devices", help="Exact ordered CUDA indexes, e.g. 0,2")
    submit.add_argument("overrides", nargs=argparse.REMAINDER)
    worker = commands.add_parser("worker", help="Serve this Unix user's jobs until stopped")
    worker.add_argument("--max-used-memory-gib", type=float, default=2.0)
    worker.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
        help="Worker stderr verbosity (default INFO; DEBUG includes every poll)",
    )
    listing = commands.add_parser("list", help="Show public job summaries")
    listing.add_argument("--host", help="Read another host partition")
    listing.add_argument("--json", action="store_true")
    move = commands.add_parser("move", help="Reorder a pending job with optimistic concurrency")
    move.add_argument("job_id")
    move.add_argument("direction", choices=("up", "down", "top", "bottom", "before", "after"))
    move.add_argument("relative_job_id", nargs="?")
    move.add_argument("--revision", type=int, required=True, help="Revision from list --json")
    for action in ("cancel", "recover"):
        command = commands.add_parser(action, help=f"{action.capitalize()} one owned job")
        command.add_argument("job_id")
    commands.add_parser("tui", help="Open the optional Textual queue interface")
    gpu = commands.add_parser("gpu", help="Inspect and control physical host GPUs")
    operations = gpu.add_subparsers(dest="gpu_action", required=True)
    gpu_list = operations.add_parser(
        "list", help="List physical identities, holds and claim tokens"
    )
    gpu_list.add_argument("--json", action="store_true")
    disable = operations.add_parser("disable", help="Hold a physical GPU for this Unix owner")
    disable.add_argument("selector", help="Physical NVML index or full GPU UUID")
    disable.add_argument("--reason", required=True)
    enable = operations.add_parser("enable", help="Remove only your hold on a physical GPU")
    enable.add_argument("selector", help="Physical NVML index or full GPU UUID")
    release = operations.add_parser("release", help="Release one owned whole-allocation claim")
    release.add_argument("selector", help="Physical NVML index or full GPU UUID")
    release.add_argument("--claim-token", required=True)
    release.add_argument("--reason", required=True)
    release.add_argument(
        "--force", action="store_true", help="Audit unverified stale cleanup; never kill"
    )
    return parser


def _show(view: QueueView, *, as_json: bool = False) -> None:
    if as_json:
        sys.stdout.write(view.model_dump_json() + "\n")
        return
    sys.stdout.write(f"Host {view.host_id} | revision {view.revision}\n")
    for position, job in enumerate(view.jobs, 1):
        request = ",".join(job.request.devices or ()) or str(job.request.count)
        allocation = ",".join(job.devices) or "-"
        reason = job.waiting_reason or ""
        sys.stdout.write(
            f"{position}\t{job.id}\tuid={job.owner_uid}\t{job.state}\t"
            f"request={request}\tallocation={allocation}\t{reason}\n"
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

    def __init__(self, owner_uid: int) -> None:
        self.owner_uid = owner_uid
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
                f"Job {job.id} | state={job.state} | "
                f"request={','.join(job.request.devices or ()) or job.request.count} | "
                f"allocation={','.join(job.devices) or '-'}"
            )
            if job.waiting_reason:
                details += f" | waiting={job.waiting_reason}"
            if job.progress is not None:
                details += f" | progress={job.progress}"
            if job.error:
                details += f" | error={job.error}"
            logger.log(level, "{}", redact_text(details).replace("\n", "\\n").replace("\r", "\\r"))
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
            "Worker poll | host={} uid={} | {}", view.host_id, self.owner_uid, summary or "no jobs"
        )


def _worker(service: QueueService) -> None:
    stopped = False

    def stop(_signum: int, _frame: FrameType | None) -> None:
        nonlocal stopped
        stopped = True

    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        service.worker(lambda: stopped, observe=_WorkerLog(service.identity.owner_uid))
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    logger.info("Queue worker stopped; active jobs remain supervised by their guardians")


def _tui(service: QueueService) -> None:
    try:
        from clearml_yolo.entrypoints.queue_tui import QueueApp
    except ModuleNotFoundError as error:
        if error.name and error.name.startswith("textual"):
            raise RuntimeError("Install clearml-yolo[queue-ui] to use cy-queue tui") from error
        raise
    QueueApp(service).run()


def _execute(arguments: argparse.Namespace) -> None:
    from clearml_yolo.adapters.queue.gpu_controls import GPUControls
    from clearml_yolo.adapters.queue.identity import current_identity
    from clearml_yolo.adapters.queue.inventory import QueueGPUInventory
    from clearml_yolo.adapters.queue.runtime import QueueProcesses
    from clearml_yolo.adapters.queue.storage import NFSQueueStore
    from clearml_yolo.adapters.runtime.bootstrap import initialize_runtime_environment

    root = initialize_runtime_environment()
    queue_root = arguments.root or Path(os.environ.get("CY_QUEUE_ROOT") or root / ".cy-queue")
    identity = current_identity()
    storage = NFSQueueStore(queue_root, identity)
    threshold = arguments.max_used_memory_gib if arguments.action == "worker" else 2.0
    processes = QueueProcesses(storage, identity)
    service = QueueService(
        storage,
        QueueGPUInventory(max_used_memory_gib=threshold),
        processes,
        identity,
        controls=GPUControls(processes.pool),
    )
    if arguments.action == "worker":
        logger.info(
            "Starting queue worker | root={} host={} uid={} max_used_memory_gib={}",
            storage.root,
            identity.host_id,
            identity.owner_uid,
            threshold,
        )
    if arguments.action == "gpu":
        _gpu_operation(service, arguments)
        return
    _queue_operation(service, arguments, root)


def _queue_operation(service: QueueService, arguments: argparse.Namespace, root: Path) -> None:
    match arguments.action:
        case "submit":
            from clearml_yolo.entrypoints.hydra.queue_config import compose_snapshots

            values = arguments.overrides
            if values and values[0] == "--":
                values = values[1:]
            snapshots = compose_snapshots(values, _resource_request(arguments), project_root=root)
            for job in service.submit(snapshots):
                sys.stdout.write(job.id + "\n")
        case "list":
            _show(service.list(arguments.host), as_json=arguments.json)
        case "move":
            _show(
                service.move(
                    arguments.job_id,
                    _direction(arguments.direction),
                    arguments.revision,
                    relative_job_id=arguments.relative_job_id,
                )
            )
        case "cancel":
            sys.stdout.write(service.cancel(arguments.job_id).model_dump_json() + "\n")
        case "recover":
            sys.stdout.write(service.recover(arguments.job_id).model_dump_json() + "\n")
        case "worker":
            _worker(service)
        case "tui":
            _tui(service)
        case _:
            raise ValueError("Unknown queue operation")


def _gpu_operation(service: QueueService, arguments: argparse.Namespace) -> None:
    match arguments.gpu_action:
        case "list":
            cards = service.gpu_list()
            if arguments.json:
                sys.stdout.write(json.dumps([card.model_dump() for card in cards]) + "\n")
            else:
                for card in cards:
                    holds = "; ".join(f"uid={hold.owner_uid}: {hold.reason}" for hold in card.holds)
                    sys.stdout.write(
                        f"{card.physical_index if card.physical_index is not None else '-'}\t"
                        f"{card.uuid}\tholds={holds or '-'}\t"
                        f"job={card.claim.job_id if card.claim else '-'}\t"
                        f"claim-token={card.claim_token or '-'}\n"
                    )
        case "disable":
            sys.stdout.write(
                service.gpu_disable(arguments.selector, reason=arguments.reason).model_dump_json()
                + "\n"
            )
        case "enable":
            service.gpu_enable(arguments.selector)
            sys.stdout.write("Own GPU hold removed\n")
        case "release":
            audit = service.gpu_release(
                arguments.selector,
                token=arguments.claim_token,
                reason=arguments.reason,
                force=arguments.force,
            )
            sys.stdout.write(audit.model_dump_json() + "\n")
        case _:
            raise ValueError("Unknown GPU control operation")


if __name__ == "__main__":
    main()
