"""Stdlib-only tailer: terminal forwarding never waits for a tracking service."""

import json
import os
import sys
import time
from pathlib import Path


def mirror(directory: Path, owner: int, descriptors: tuple[int, int], controls: Path) -> None:
    initial = json.loads((controls / "initial.json").read_text())
    offsets = {name: initial[name] for name in ("stdout", "stderr")}
    while True:
        stop = controls / "final.json"
        final = json.loads(stop.read_text()) if stop.is_file() else None
        for name, descriptor in zip(offsets, descriptors, strict=True):
            with (directory / f"{name}.log").open("rb") as stream:
                stream.seek(offsets[name])
                limit = final[name] - offsets[name] if final is not None else 65536
                payload = stream.read(min(65536, limit))
            remaining = memoryview(payload)
            while remaining:
                written = os.write(descriptor, remaining)
                remaining = remaining[written:]
            offsets[name] += len(payload)
        if final is not None and all(offsets[name] == final[name] for name in offsets):
            return
        try:
            os.kill(owner, 0)
        except ProcessLookupError:
            return
        time.sleep(0.025)


def main() -> None:
    mirror(
        Path(sys.argv[1]), int(sys.argv[2]), (int(sys.argv[3]), int(sys.argv[4])), Path(sys.argv[5])
    )


if __name__ == "__main__":
    main()
