"""Submit and manage durable, per-host, owner-executed pipeline jobs."""

import argparse
import os
import signal
import sys
from pathlib import Path
from types import FrameType

from clearml_yolo.application.queue import QueueService
from clearml_yolo.core.queue import MoveDirection, QueueView, ResourceRequest


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
    try:
        _execute(arguments)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"cy-queue: {error}\n")


def _worker(service: QueueService) -> None:
    stopped = False

    def stop(_signum: int, _frame: FrameType | None) -> None:
        nonlocal stopped
        stopped = True

    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        service.worker(lambda: stopped)
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def _tui(service: QueueService) -> None:
    try:
        from clearml_yolo.entrypoints.queue_tui import QueueApp
    except ModuleNotFoundError as error:
        if error.name and error.name.startswith("textual"):
            raise RuntimeError("Install clearml-yolo[queue-ui] to use cy-queue tui") from error
        raise
    QueueApp(service).run()


def _execute(arguments: argparse.Namespace) -> None:
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
    service = QueueService(
        storage,
        QueueGPUInventory(max_used_memory_gib=threshold),
        QueueProcesses(storage, identity),
        identity,
    )
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


if __name__ == "__main__":
    main()
