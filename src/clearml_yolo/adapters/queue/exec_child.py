"""Private exec gate: the guardian records process identity before native execution."""

import json
import os
import sys
from pathlib import Path

from clearml_yolo.adapters.runtime.execution_lifecycle import OWNER_PID_ENV


def main() -> None:
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    descriptor = int(os.environ.pop("CY_QUEUE_EXEC_GATE"))
    try:
        permission = os.read(descriptor, 1)
    finally:
        os.close(descriptor)
    if permission != b"1":
        raise RuntimeError("Guardian did not authorize execution")
    os.environ[OWNER_PID_ENV] = str(os.getpid())
    argv = payload["argv"]
    os.execvpe(argv[0], argv, os.environ)  # noqa: S606 - fixed argv supplied by composition


if __name__ == "__main__":
    main()
