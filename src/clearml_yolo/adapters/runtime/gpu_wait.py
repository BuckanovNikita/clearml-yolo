"""Wait for free whole GPUs without allocating or reserving them."""

import time

from loguru import logger

from clearml_yolo.adapters.runtime.gpu_resources import GPUInventory

_POLL_SECONDS = 1.0
_LOG_SECONDS = 30.0


def wait_for_available_gpus(
    count: int, *, inventory: GPUInventory | None = None
) -> tuple[int, ...]:
    """Return enough free CUDA logical indices in inherited visibility order."""
    if isinstance(count, bool) or not isinstance(count, int):
        raise TypeError(f"GPU count must be an integer: {count!r}")
    if count < 0:
        raise ValueError(f"GPU count must be nonnegative: {count}")
    if not count:
        return ()

    source = GPUInventory() if inventory is None else inventory
    visible = source.visible()
    if count > len(visible):
        raise ValueError(
            f"Requested {count} GPUs but only {len(visible)} supported GPUs are visible"
        )

    last_log: float | None = None
    while True:
        physical = {device.uuid: device for device in source.snapshot()}
        missing = [uuid for uuid in visible if uuid not in physical]
        if missing:
            raise RuntimeError(f"GPU visibility was lost for physical GPU UUIDs: {missing}")
        available = tuple(index for index, uuid in enumerate(visible) if not physical[uuid].busy)
        if len(available) >= count:
            return available[:count]
        now = time.monotonic()
        if last_log is None or now - last_log >= _LOG_SECONDS:
            logger.info(
                "Waiting for {} free visible GPUs; {} of {} currently available",
                count,
                len(available),
                len(visible),
            )
            last_log = now
        time.sleep(_POLL_SECONDS)
