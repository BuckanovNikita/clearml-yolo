"""Launch task-owned documentation servers and isolated browser contexts."""

import os
import re
import selectors
import signal
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from time import monotonic

import pytest
from playwright.sync_api import Browser, Page, sync_playwright


@dataclass(frozen=True)
class DocsServer:
    process: subprocess.Popen[str]
    url: str


@contextmanager
def start_server() -> Iterator[DocsServer]:
    """Wait for the explicit listening announcement, then own graceful cleanup."""
    command = [
        sys.executable,
        "-m",
        "clearml_yolo.entrypoints.docs",
        "--no-browser",
        "--port",
        "0",
    ]
    process = subprocess.Popen(  # noqa: S603 - fixed local entrypoint, no shell
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    try:
        if process.stdout is None:
            raise AssertionError("Documentation process did not provide stdout")
        output: list[str] = []
        deadline = monotonic() + 90
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while monotonic() < deadline:
                if not selector.select(timeout=max(0, deadline - monotonic())):
                    break
                line = process.stdout.readline()
                output.append(line)
                match = re.search(r"http://127\.0\.0\.1:\d+/?", line)
                if match:
                    yield DocsServer(process, match.group(0).rstrip("/"))
                    return
                if process.poll() is not None:
                    break
        raise AssertionError("Documentation server did not become ready:\n" + "".join(output))
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if process.stdout is not None:
            process.stdout.close()


@pytest.fixture(scope="module")
def docs_server() -> Iterator[DocsServer]:
    with start_server() as server:
        yield server


@pytest.fixture(scope="module")
def browser() -> Iterator[Browser]:
    with (
        sync_playwright() as playwright,
        playwright.chromium.launch(channel=os.environ.get("CY_DOCS_BROWSER_CHANNEL")) as launched,
    ):
        yield launched


@pytest.fixture
def page(browser: Browser, docs_server: DocsServer) -> Iterator[Page]:
    with browser.new_context(
        base_url=docs_server.url,
        viewport={"width": 1440, "height": 1000},
        locale="ru-RU",
        permissions=["clipboard-read", "clipboard-write"],
    ) as context:
        opened = context.new_page()
        opened.set_default_timeout(20000)
        yield opened
