"""Wait for free whole GPUs without allocating or reserving them."""

import time
from collections.abc import Callable

from clearml_yolo.adapters.observability.tracing import trace_operation
from clearml_yolo.adapters.runtime.gpu_queue import (
    AdmissionDiagnostics,
    admission_cards,
)
from clearml_yolo.adapters.runtime.gpu_resources import GPUInventory

_POLL_SECONDS = 1.0


@trace_operation("gpu.wait")
def wait_for_available_gpus(
    count: int,
    *,
    inventory: GPUInventory | None = None,
    on_decision: Callable[[AdmissionDiagnostics], None] | None = None,
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

    while True:
        snapshot = source.snapshot()
        physical = {device.uuid: device for device in snapshot}
        missing = [uuid for uuid in visible if uuid not in physical]
        if missing:
            raise RuntimeError(f"GPU visibility was lost for physical GPU UUIDs: {missing}")
        available = tuple(index for index, uuid in enumerate(visible) if not physical[uuid].busy)
        selected = available[:count] if len(available) >= count else ()
        decision = AdmissionDiagnostics(
            requested_count=count,
            visible_count=len(visible),
            max_used_memory_gib=source.max_used_memory_gib,
            cards=admission_cards(snapshot, visible, visible, {}),
            admitted=tuple(visible[index] for index in selected),
        )
        if on_decision is not None:
            on_decision(decision)
        if len(available) >= count:
            with trace_operation(
                "gpu.selected",
                context={"requested": count, "selected": ",".join(map(str, selected))},
            ):
                return selected
        time.sleep(_POLL_SECONDS)
