"""Subprocess driver for GPU queue integration tests."""

import argparse
import json
import sys
from pathlib import Path

from clearml_yolo.gpu_queue import GPUQueue
from clearml_yolo.gpu_resources import GPUDevice


class MetadataInventory:
    """Read the test-owned inventory snapshot on every queue operation."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def snapshot(self) -> tuple[GPUDevice, ...]:
        values = json.loads(self._path.read_text(encoding="utf-8"))
        return tuple(GPUDevice(uuid=item["uuid"], busy=item["busy"]) for item in values)


def _emit(**values: object) -> None:
    sys.stdout.write(f"{json.dumps(values)}\n")
    sys.stdout.flush()


def _serve_supervisor(args: argparse.Namespace, queue: GPUQueue) -> None:
    ticket = queue.register(args.count, tuple(args.visible))
    _emit(event="registered", ticket_id=ticket.id)
    try:
        for raw_command in sys.stdin:
            command = raw_command.strip()
            if command == "acquire":
                _emit(event=command, devices=ticket.try_acquire())
            elif command == "position":
                _emit(event=command, position=ticket.position())
            elif command == "devices":
                _emit(event=command, devices=ticket.devices)
            elif command == "close":
                ticket.close()
                _emit(event=command)
            elif command == "exit":
                return
            else:
                raise ValueError(f"Unknown command: {command}")
    finally:
        ticket.close()


def _serve_worker(args: argparse.Namespace, queue: GPUQueue) -> None:
    with queue.claim_worker(args.ticket_id) as claim:
        _emit(event="claimed", devices=claim.devices)
        for raw_command in sys.stdin:
            command = raw_command.strip()
            if command == "devices":
                _emit(event=command, devices=claim.devices)
            elif command == "shrink":
                try:
                    _emit(event=command, devices=claim.shrink())
                except RuntimeError as error:
                    _emit(event=command, error=type(error).__name__, message=str(error))
            elif command == "exit":
                return
            else:
                raise ValueError(f"Unknown command: {command}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("supervisor", "worker"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--count", type=int, default=0)
    parser.add_argument("--visible", nargs="*", default=[])
    parser.add_argument("--ticket-id")
    parser.add_argument("--untrusted-label")
    args = parser.parse_args(argv)
    queue = GPUQueue(root=args.root, inventory=MetadataInventory(args.inventory))
    if args.mode == "supervisor":
        _serve_supervisor(args, queue)
        return
    if args.ticket_id is None:
        parser.error("worker mode requires --ticket-id")
    try:
        _serve_worker(args, queue)
    except (RuntimeError, ValueError) as error:
        _emit(event="error", error=type(error).__name__, message=str(error))
        raise


if __name__ == "__main__":
    main()
