"""Concise, credential-safe error summaries and location-only debug diagnostics."""

import re
from collections.abc import Mapping
from urllib.parse import unquote

from loguru import logger

_REDACTED = "<redacted>"
_SENSITIVE_KEY = re.compile(
    r"access[-_ ]?key|secret|password|passwd|token|credential|api[-_ ]?key|"
    r"authorization|private[-_ ]?key|bearer|cookie|session[-_ ]?key|"
    r"signature|^sig$|connection[-_ ]?string",
    re.IGNORECASE,
)
_URL = re.compile(
    r"[a-z][a-z0-9+.-]*://(?:[^\r\n]*?@[^\s\"'<>]*|[^\s\"'<>]+)",
    re.IGNORECASE,
)
_ASSIGNMENT = re.compile(
    r"(?P<key>[\"']?[\w.-]*(?:access[-_ ]?key|secret|password|passwd|token|credential|"
    r"api[-_ ]?key|authorization|private[-_ ]?key|cookie|bearer|session[-_ ]?key|signature|"
    r"connection[-_ ]?string)[\w.-]*[\"']?|[\"']?sig[\"']?)\s*[:=]\s*",
    re.IGNORECASE,
)
_AUTH_HEADER = re.compile(
    r"\b(?:authorization|proxy-authorization|cookie|set-cookie)\s*[:=]\s*[^\r\n]+",
    re.IGNORECASE,
)
_BEARER = re.compile(r"\bBearer\s+[^\s,;\"']+", re.IGNORECASE)


def _redact_url(match: re.Match[str]) -> str:
    token = match[0]
    decoded = unquote(token)
    query_keys = re.findall(r"[?&]([^=&]+)=", decoded)
    if "@" in decoded or any(_SENSITIVE_KEY.search(key) for key in query_keys):
        return _REDACTED
    return token


def _quoted_end(text: str, start: int) -> int:
    quote = text[start]
    index = start + 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
        elif text[index] == quote:
            return index + 1
        else:
            index += 1
    return len(text)


def _composite_end(text: str, start: int) -> int:
    closers = {"{": "}", "[": "]", "(": ")"}
    expected: list[str] = []
    index = start
    while index < len(text):
        character = text[index]
        if character in "\"'":
            index = _quoted_end(text, index)
            continue
        if character in closers:
            expected.append(closers[character])
        elif character in "}])":
            if character != expected.pop():
                return len(text)
            if not expected:
                return index + 1
        index += 1
    # Incomplete values have no safe following boundary: suppress the remainder.
    return len(text)


def _assignment_end(text: str, start: int) -> int:
    if start == len(text):
        return start
    if text[start] in "\"'":
        return _quoted_end(text, start)
    if text[start] in "{[(":
        return _composite_end(text, start)
    delimiter = re.search(r"[,;\r\n}\])]+", text[start:])
    return start + delimiter.start() if delimiter is not None else len(text)


def _redact_assignments(text: str) -> str:
    pieces: list[str] = []
    index = 0
    while match := _ASSIGNMENT.search(text, index):
        pieces.append(text[index:match.start()])
        pieces.append(f"{match['key']}={_REDACTED}")
        index = _assignment_end(text, match.end())
    pieces.append(text[index:])
    return "".join(pieces)


def redact_text(text: str) -> str:
    """Remove labeled secrets and whole credential-bearing URL tokens from text.

    Recognize URL tokens without parsing their host/port: malformed addresses are
    particularly common in connection failures and must still lose credentials.
    """
    text = _URL.sub(_redact_url, text)
    text = _AUTH_HEADER.sub(_REDACTED, text)
    text = _redact_assignments(text)
    return _BEARER.sub(f"Bearer {_REDACTED}", text)


def _safe_text(value: object) -> str:
    try:
        return str(value)
    except Exception:  # noqa: BLE001 - diagnostic formatting must preserve the original failure
        return f"<{type(value).__name__} message unavailable>"


def _exception_chain(error: BaseException) -> list[BaseException]:
    chain: list[BaseException] = []
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(current)
        if current.__cause__ is not None:
            current = current.__cause__
        else:
            current = None if current.__suppress_context__ else current.__context__
    return chain


def exception_summary(error: BaseException, *, include_message: bool = True) -> str:
    """Return exception types, useful sanitized messages and visible cause/context chains."""
    parts: list[str] = []
    for item in _exception_chain(error):
        name = type(item).__name__
        message = redact_text(_safe_text(item)).strip() if include_message else ""
        parts.append(f"{name}: {message}" if message else name)
    return " <- ".join(parts)


def _context_summary(context: Mapping[str, object]) -> str:
    values: list[str] = []
    for key, value in context.items():
        # A labeled credential can contain arbitrary opaque payload; do not stringify it.
        text = _REDACTED if _SENSITIVE_KEY.search(key) else redact_text(_safe_text(value))
        values.append(f"{redact_text(key)}={text}")
    return ", ".join(values)


def _traceback_locations(error: BaseException) -> str:
    lines: list[str] = []
    for item in _exception_chain(error):
        lines.append(type(item).__name__)
        traceback = item.__traceback__
        while traceback is not None:
            code = traceback.tb_frame.f_code
            lines.append(
                f"  File {redact_text(code.co_filename)}, line {traceback.tb_lineno}, "
                f"in {redact_text(code.co_name)}"
            )
            traceback = traceback.tb_next
    return "\n".join(lines)


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
