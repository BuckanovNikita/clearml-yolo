"""Loguru emission using the core credential-safe diagnostic formatting."""

from collections.abc import Mapping

from loguru import logger

from clearml_yolo.core.redaction import (
    context_summary as _context_summary,
)
from clearml_yolo.core.redaction import (
    exception_summary as exception_summary,  # noqa: PLC0414 - typed diagnostic interface
)
from clearml_yolo.core.redaction import (
    redact_text as redact_text,  # noqa: PLC0414 - typed diagnostic interface
)
from clearml_yolo.core.redaction import (
    traceback_locations as _traceback_locations,
)


def log_exception(
    message: str,
    error: BaseException,
    *,
    level: str = "WARNING",
    context: Mapping[str, object] | None = None,
    include_message: bool = True,
) -> None:
    """Log a safe summary and DEBUG frames without attaching raw exception objects.

    Keep the caller's sinks and level policy. Tracebacks contain only frame locations,
    never source lines or locals, even when a sink enables Loguru's diagnosis feature.
    """
    details = exception_summary(error, include_message=include_message)
    operation = redact_text(message)
    if context:
        operation = f"{operation} ({_context_summary(context)})"
    if level != "DEBUG":
        logger.opt(exception=False).log(level, "{}: {}", operation, details)
    logger.opt(exception=False).debug("{}: {}\n{}", operation, details, _traceback_locations(error))


def log(level: str, message: str, *args: object) -> None:
    """Emit a workflow observation while keeping the logging backend outside it."""
    logger.opt(depth=1).log(level, message, *args)
