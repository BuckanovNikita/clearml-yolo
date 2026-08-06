"""One progress signal for every loop in this project that can run for minutes.

A tqdm bar rewrites a single terminal line, which is unreadable once ClearML captures the
stage output as a log — the carriage returns become thousands of lines. So the bar is used
only on a real terminal, and everything else gets periodic loguru lines carrying the same
information.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Iterator, Sized
from time import monotonic

from loguru import logger
from tqdm import tqdm

LOG_STEP_FRACTION = 0.1
# How often to speak when the length is unknown and a percentage cannot be computed.
UNKNOWN_TOTAL_LOG_STEP = 100


def track[Item](
    items: Iterable[Item],
    description: str,
    total: int | None = None,
    unit: str = "it",
) -> Iterator[Item]:
    """Yield every item of ``items``, reporting how far along the loop is as it goes.

    ``total`` is taken from the iterable when it has a length, so most callers pass only a
    description. Generators must supply it themselves or the log falls back to a fixed
    interval with no percentage.
    """
    if total is None and isinstance(items, Sized):
        total = len(items)

    if sys.stderr.isatty():
        yield from tqdm(items, desc=description, total=total, unit=unit)
        return

    step = max(1, round(total * LOG_STEP_FRACTION)) if total else UNKNOWN_TOTAL_LOG_STEP
    started = monotonic()
    done = 0
    for item in items:
        yield item
        done += 1
        if done % step == 0 and done != total:
            elapsed = monotonic() - started
            share = f" ({done / total:.0%})" if total else ""
            logger.info(
                "{}: {}/{}{} {} in {:.1f}s",
                description,
                done,
                total if total is not None else "?",
                share,
                unit,
                elapsed,
            )
    logger.info("{}: {} {} in {:.1f}s", description, done, unit, monotonic() - started)
