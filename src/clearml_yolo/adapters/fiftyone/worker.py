"""Fresh optional-publication interpreter; owner metadata never enters this process."""

import os
import sys
import time
from pathlib import Path

_PATH_ARGUMENTS = 3


def _run() -> None:
    if len(sys.argv[1:]) != _PATH_ARGUMENTS:
        raise SystemExit("Expected request, result and phase paths")
    gate = os.environ.pop("CY_FIFTYONE_START_GATE", None)
    if gate is not None:
        while not Path(gate).is_file():
            time.sleep(0.01)
    request_path, result_path, phase_path = map(Path, sys.argv[1:])
    phase_path.write_text("bootstrap", encoding="utf-8")
    from clearml_yolo.adapters.runtime.bootstrap import (
        initialize_runtime_environment,
        project_configuration_imports,
    )

    initialize_runtime_environment()
    from clearml_yolo.adapters.fiftyone.compatibility import isolated_constants
    from clearml_yolo.adapters.fiftyone.protocol import WorkerRequest, WorkerResult

    message = WorkerRequest.model_validate_json(request_path.read_text(encoding="utf-8"))
    phase_path.write_text("import", encoding="utf-8")
    with project_configuration_imports(), isolated_constants():
        from clearml_yolo.adapters.fiftyone.publisher import FiftyOnePublisher

        publisher = FiftyOnePublisher(message.config, phase_path=phase_path)
        if message.operation == "preflight":
            publisher.preflight()
            receipt = None
        elif message.request is not None:
            receipt = publisher.publish(message.request)
        else:
            raise ValueError("Publish worker requires a publication request")
    response = WorkerResult(
        operation=message.operation,
        operation_id=message.operation_id,
        task_id=None if message.request is None else message.request.task_id,
        complete=True,
        receipt=receipt,
    )
    pending = result_path.with_suffix(".pending")
    pending.write_text(response.model_dump_json(), encoding="utf-8")
    pending.replace(result_path)
    phase_path.write_text("shutdown", encoding="utf-8")


def main() -> None:
    try:
        _run()
    except Exception as error:  # noqa: BLE001 - process boundary reports optional SDK failures
        from clearml_yolo.core.redaction import exception_summary

        sys.stderr.write(exception_summary(error)[:2048] + "\n")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
