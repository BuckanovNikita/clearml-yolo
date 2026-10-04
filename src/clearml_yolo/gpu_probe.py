"""Disposable CUDA metadata probe used by :mod:`clearml_yolo.gpu_resources`."""

import json
import os
import sys


def _uuid(value: object) -> str:
    uuid = str(value)
    if uuid.startswith("MIG-"):
        raise RuntimeError("MIG devices are unsupported by the GPU queue")
    return uuid if uuid.startswith("GPU-") else f"GPU-{uuid}"


def main() -> None:
    """Print visible physical UUIDs in CUDA logical-device order."""
    inherited = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if any(token.strip().startswith("MIG-") for token in inherited.split(",")):
        raise RuntimeError("MIG devices are unsupported by the GPU queue")

    import torch

    uuids: list[str] = []
    for index in range(torch.cuda.device_count()):
        properties = torch.cuda.get_device_properties(index)
        uuid = getattr(properties, "uuid", None)
        if uuid is None:
            raise RuntimeError("CUDA device properties do not expose stable GPU UUIDs")
        uuids.append(_uuid(uuid))
    sys.stdout.write(json.dumps(uuids))


if __name__ == "__main__":
    main()
