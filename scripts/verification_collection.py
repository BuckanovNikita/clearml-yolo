"""Capture only the bounded, marker-filtered in-process pytest collection."""

from collections.abc import Iterator

import pytest


class BoundedCollection:
    def __init__(self) -> None:
        self.nodes: set[str] = set()
        self.all_nodes: set[str] = set()

    @pytest.hookimpl(hookwrapper=True, tryfirst=True)
    def pytest_collection_modifyitems(self, items: list[pytest.Item]) -> Iterator[None]:
        self.all_nodes = {item.nodeid for item in items}
        yield

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.nodes = {item.nodeid for item in session.items}
