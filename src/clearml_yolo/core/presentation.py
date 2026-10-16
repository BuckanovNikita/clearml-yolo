"""Pure human-facing reference formatting; machine identity stays with its owner."""

import re
from collections.abc import Iterable, Mapping

_OPAQUE = re.compile(
    r"(?<![0-9a-f])(?:[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
    r"|[0-9a-f]{64}|[0-9a-f]{40}|[0-9a-f]{32})(?![0-9a-f])",
    re.IGNORECASE,
)
_URL = re.compile(r"(?:https?|clearml)://[^\s<>\"']+")
_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_ANSI_TAIL = re.compile(r"\x1b(?:\[[0-?]*[ -/]*)?$")
_WHITESPACE = re.compile(r"\s")
_POSSIBLE_REFERENCE = re.compile(r"([0-9a-f][0-9a-f-]*)$", re.IGNORECASE)
_MAX_TOKEN = 4096
_CHECKSUM_LENGTH = 64
_REVISION_LENGTH = 40


def _reference(match: re.Match[str], labels: Mapping[str, str]) -> str:
    value = match.group()
    if value in labels:
        return _OPAQUE.sub("[reference]", labels[value])
    if "-" in value:
        return "[reference]"
    if len(value) == _CHECKSUM_LENGTH:
        return "[checksum]"
    if len(value) == _REVISION_LENGTH:
        return "[revision]"
    return "[task]"


def human_text(text: str, labels: Mapping[str, str] | None = None) -> str:
    """Render names or semantic labels without modifying stored IDs or link targets.

    Plain console URLs containing opaque references become link descriptions. Rich
    interfaces retain exact URL targets separately from their readable link labels.
    """
    known = labels or {}

    def link(match: re.Match[str]) -> str:
        value = match.group()
        identities = list(_OPAQUE.finditer(value))
        if not identities:
            return value
        names = [known[item.group()] for item in identities if item.group() in known]
        return " / ".join(names) if names else "[ClearML link]"

    text = _URL.sub(link, _ANSI.sub("", text))
    return _OPAQUE.sub(lambda match: _reference(match, known), text)


class HumanLabelRegistry:
    """Issue stable readable aliases for a growing set without merging source keys."""

    def __init__(self, reserved: Iterable[str] = ()) -> None:
        self._reserved = set(reserved)
        self._labels: dict[str, str] = {}
        self._used: set[str] = set()

    def label(self, source: str) -> str:
        existing = self._labels.get(source)
        if existing is not None:
            return existing
        base = human_text(source)
        display = base
        suffix = 2
        while display in self._used or (display in self._reserved and display != source):
            display = f"{base} ({suffix})"
            suffix += 1
        self._labels[source] = display
        self._used.add(display)
        return display


class HumanSeriesRegistry:
    """Keep title/series destinations distinct and stable throughout one owner scope."""

    def __init__(self) -> None:
        self._titles = HumanLabelRegistry()
        self._series: dict[str, HumanLabelRegistry] = {}

    def resolve(self, title: str, series: str) -> tuple[str, str]:
        labels = self._series.setdefault(title, HumanLabelRegistry())
        return self._titles.label(title), labels.label(series)


def human_labels(labels: Iterable[str]) -> dict[str, str]:
    """Keep distinct fixed labels distinct, reserving existing readable spellings."""
    originals = dict.fromkeys(labels)
    registry = HumanLabelRegistry(label for label in originals if human_text(label) == label)
    return {label: registry.label(label) for label in originals}


class HumanTextStream:
    """Bound unfinished tokens so arbitrary chunk boundaries cannot expose IDs.

    Adapters own byte decoding and delivery acknowledgments. ``pending`` identifies
    text not yet emitted. Explicit publication checkpoints conservatively replace a
    possible reference prefix and discard its continuation until the next separator.
    """

    def __init__(self, labels: Mapping[str, str] | None = None) -> None:
        self._labels = dict(labels or {})
        self.pending = ""
        self._discard = False

    def feed(self, text: str, *, final: bool = False) -> str:
        if self._discard:
            separator = _WHITESPACE.search(text)
            if separator is None:
                return ""
            text = text[separator.start() :]
            self._discard = False
        text = self.pending + text
        self.pending = ""
        if final:
            return human_text(text, self._labels)
        boundaries = list(_WHITESPACE.finditer(text))
        boundary = boundaries[-1].end() if boundaries else 0
        self.pending = text[boundary:]
        result = human_text(text[:boundary], self._labels)
        if len(self.pending) > _MAX_TOKEN:
            # A single unbounded native token must not grow the publisher's memory.
            self.pending = ""
            self._discard = True
            result += "[long reference]"
        return result

    def checkpoint(self) -> str:
        """Flush a publication watermark without treating later chunks as a replay."""
        text = _ANSI_TAIL.sub("", _ANSI.sub("", self.pending))
        self.pending = ""
        candidate = _POSSIBLE_REFERENCE.search(text)
        if candidate is not None:
            self._discard = True
            complete = _OPAQUE.search(candidate.group(1))
            if complete is not None and complete.end() == len(candidate.group(1)):
                return human_text(text, self._labels)
            return human_text(text[: candidate.start(1)], self._labels) + "[reference]"
        return human_text(text, self._labels)
