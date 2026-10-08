"""Disabled visual publication without filesystem or database access."""

from clearml_yolo.core.publication import PublicationRequest


class NoOpPublisher:
    enabled = False

    def preflight(self) -> None:
        """Disabled publication requires no filesystem or database access."""

    def publish(self, request: PublicationRequest) -> None:
        del request
