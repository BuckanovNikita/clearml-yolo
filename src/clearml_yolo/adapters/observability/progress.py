"""One progress signal for every loop in this project that can run for minutes.

A tqdm bar rewrites a single terminal line, which is unreadable once ClearML captures the
stage output as a log — the carriage returns become thousands of lines. So the bar is used
only on a real terminal, and everything else gets periodic loguru lines carrying the same
information.
"""

from collections.abc import Callable, Generator, Iterable, Sized
from contextlib import contextmanager
from time import monotonic

from loguru import logger
from tqdm import tqdm

from clearml_yolo.adapters.observability.capture import terminal_isatty, write_progress

LOG_STEP_FRACTION = 0.1
# How often to speak when the length is unknown and a percentage cannot be computed.
UNKNOWN_TOTAL_LOG_STEP = 100
MINIMUM_LOG_SECONDS = 2.0


@contextmanager
def image_progress(
    total: int, description: str = "Inference"
) -> Generator[Callable[[int], None], None, None]:
    """Own one image-count operation while native backends process whole batches."""
    started = monotonic()
    last_report = started
    done = 0
    bar = tqdm(total=total, desc=description, unit="img") if terminal_isatty() else None
    write_progress(progress=f"{description}: 0/{total} images")

    def advance(count: int) -> None:
        nonlocal done, last_report
        if count < 0 or done + count > total:
            raise ValueError("Prediction progress exceeds image membership")
        done += count
        now = monotonic()
        if done == total or now - last_report >= MINIMUM_LOG_SECONDS:
            write_progress(progress=f"{description}: {done}/{total} images")
        if bar is not None:
            bar.update(count)
        elif done != total and now - last_report >= MINIMUM_LOG_SECONDS:
            logger.info("{}: {}/{} img in {:.1f}s", description, done, total, now - started)
            last_report = now
        if bar is not None and now - last_report >= MINIMUM_LOG_SECONDS:
            last_report = now

    try:
        yield advance
        if done != total:
            raise ValueError("Prediction progress did not complete image membership")
        if bar is None:
            logger.info("{}: {} img in {:.1f}s", description, done, monotonic() - started)
    finally:
        if bar is not None:
            bar.close()


def track[Item](
    items: Iterable[Item],
    description: str,
    total: int | None = None,
    unit: str = "it",
) -> Generator[Item, None, None]:
    """Yield every item of ``items``, reporting how far along the loop is as it goes.

    ``total`` is taken from the iterable when it has a length, so most callers pass only a
    description. Generators must supply it themselves or the log falls back to a fixed
    interval with no percentage.
    """
    if total is None and isinstance(items, Sized):
        total = len(items)

    if terminal_isatty():
        with tqdm(items, desc=description, total=total, unit=unit) as progress:
            done = 0
            last_update = monotonic()
            for item in progress:
                yield item
                done += 1
                now = monotonic()
                if now - last_update >= MINIMUM_LOG_SECONDS:
                    write_progress(progress=f"{description}: {done}/{total} {unit}")
                    last_update = now
            write_progress(progress=f"{description}: {done} {unit} complete")
        return

    step = max(1, round(total * LOG_STEP_FRACTION)) if total else UNKNOWN_TOTAL_LOG_STEP
    started = monotonic()
    last_report = started
    done = 0
    for item in items:
        yield item
        done += 1
        now = monotonic()
        if done % step == 0 and done != total and now - last_report >= MINIMUM_LOG_SECONDS:
            last_report = now
            elapsed = now - started
            write_progress(
                progress=f"{description}: {done}/{total if total is not None else '?'} {unit}"
            )
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
    write_progress(progress=f"{description}: {done} {unit} complete")


@contextmanager
def progress_callback(
    description: str,
    total: int,
    unit: str = "it",
) -> Generator[Callable[[str | None], None], None, None]:
    """Bridge before-item observations to the existing completed-work tracker.

    Each class name starts an item; advancing on the next observation reports
    the previous item as complete. None finishes the class loop before pooled
    computation. Successful context exit also finishes a loop without that event.
    Closing the iterator always releases terminal progress on exceptional exit.
    """
    tracked = track(range(total), description, total=total, unit=unit)

    def observe(item: str | None) -> None:
        if item is None:
            next(tracked, None)
        else:
            next(tracked)

    try:
        yield observe
        next(tracked, None)
    finally:
        tracked.close()
