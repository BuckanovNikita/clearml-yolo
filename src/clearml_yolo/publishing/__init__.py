"""Replaceable visual publication boundary, safe to import without FiftyOne."""

from typing import Protocol

from clearml_yolo.publishing.models import (
    FiftyOneConfig,
    PublicationReceipt,
    PublicationRequest,
)


class Publisher(Protocol):
    @property
    def enabled(self) -> bool: ...

    def preflight(self) -> None: ...

    def publish(self, request: PublicationRequest) -> PublicationReceipt | None: ...


class NoOpPublisher:
    enabled = False

    def preflight(self) -> None:
        """Disabled publication requires no filesystem or database access."""

    def publish(self, request: PublicationRequest) -> None:
        del request


def create_publisher(config: FiftyOneConfig | None = None) -> Publisher:
    selected = config if config is not None else FiftyOneConfig()
    if not selected.enabled:
        return NoOpPublisher()
    from clearml_yolo.publishing.fiftyone_adapter import FiftyOnePublisher

    return FiftyOnePublisher(selected)
