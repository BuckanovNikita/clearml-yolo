"""Loopback-only static documentation server with injected preview ownership."""

import json
import mimetypes
import socket
import sys
import webbrowser
from collections.abc import Callable
from contextlib import suppress
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import BoundedSemaphore, Lock
from typing import cast, override
from urllib.parse import unquote, urlsplit

from loguru import logger

from clearml_yolo.adapters.documentation.files import MAX_REQUEST_BYTES, asset_bytes
from clearml_yolo.core.documentation import Catalog, PreviewRequest, PreviewResult

type PreviewCallback = Callable[[PreviewRequest], PreviewResult]

CONNECTION_TIMEOUT = 5
MAX_CONNECTIONS = 8
MAX_HEADER_BYTES = 16 * 1024
MAX_TARGET_BYTES = 4096


class DocumentationServer(ThreadingHTTPServer):
    """Bound sockets before handler construction, including clients that never send headers."""

    daemon_threads = True
    block_on_close = False

    def __init__(self, catalog: Catalog, preview: PreviewCallback, port: int) -> None:
        self.catalog_bytes = catalog.model_dump_json().encode("utf-8")
        self.allowed = {"index.html", "app.js", "style.css"} | {
            f"tutorials/{tutorial.file.removesuffix('.md')}.html" for tutorial in catalog.tutorials
        }
        self.preview = preview
        self._connections = BoundedSemaphore(MAX_CONNECTIONS)
        self._socket_lock = Lock()
        self._sockets: set[socket.socket] = set()
        super().__init__(("127.0.0.1", port), _Handler)

    @override
    def get_request(self) -> tuple[socket.socket, tuple[str, int]]:
        connection, address = super().get_request()
        connection.settimeout(CONNECTION_TIMEOUT)
        with self._socket_lock:
            self._sockets.add(connection)
        return connection, address

    @override
    def process_request(
        self, request: socket.socket | tuple[bytes, socket.socket], client_address: tuple[str, int]
    ) -> None:
        if not isinstance(request, socket.socket):
            raise TypeError("Documentation server requires TCP sockets")
        if not self._connections.acquire(blocking=False):
            try:
                request.sendall(
                    b"HTTP/1.0 503 Service Unavailable\r\n"
                    b"Content-Length: 0\r\nConnection: close\r\n\r\n"
                )
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._connections.release()
            raise

    @override
    def process_request_thread(
        self, request: socket.socket | tuple[bytes, socket.socket], client_address: tuple[str, int]
    ) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._connections.release()

    @override
    def shutdown_request(self, request: socket.socket | tuple[bytes, socket.socket]) -> None:
        if not isinstance(request, socket.socket):
            raise TypeError("Documentation server requires TCP sockets")
        try:
            super().shutdown_request(request)
        finally:
            with self._socket_lock:
                self._sockets.discard(request)

    @override
    def server_close(self) -> None:
        super().server_close()
        with self._socket_lock:
            sockets = tuple(self._sockets)
        for connection in sockets:
            with suppress(OSError):
                connection.shutdown(socket.SHUT_RDWR)
            connection.close()


class _Handler(BaseHTTPRequestHandler):
    @property
    def docs_server(self) -> DocumentationServer:
        # The stdlib handler erases its server subtype; make_server owns this pairing.
        return cast(DocumentationServer, self.server)

    @override
    def log_message(self, format: str, *args: object) -> None:
        # User YAML and queries must not enter a request log.
        pass

    @override
    def parse_request(self) -> bool:
        if not super().parse_request():
            return False
        # The standard parser already bounds each line and the number of headers.
        if sum(len(key) + len(value) for key, value in self.headers.items()) > MAX_HEADER_BYTES:
            self._send(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE, b"Headers too large")
            return False
        if len(self.path) > MAX_TARGET_BYTES:
            self._send(HTTPStatus.REQUEST_URI_TOO_LONG, b"Request target too large")
            return False
        return True

    def _local(self) -> bool:
        address = f"127.0.0.1:{self.docs_server.server_port}"
        hosts = self.headers.get_all("Host", [])
        origins = self.headers.get_all("Origin", [])
        return hosts == [address] and origins in ([], [f"http://{address}"])

    def _send(
        self, status: HTTPStatus, data: bytes, content_type: str = "text/plain; charset=utf-8"
    ) -> None:
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
                "base-uri 'none'; form-action 'none'",
            )
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            return
        finally:
            self.close_connection = True

    def _error(self, status: HTTPStatus, message: str) -> None:
        self._send(status, json.dumps({"errors": [message]}).encode(), "application/json")

    def do_GET(self) -> None:
        if not self._local():
            self._send(HTTPStatus.FORBIDDEN, b"Local origin required")
            return
        try:
            path = unquote(urlsplit(self.path).path)
        except ValueError:
            self._error(HTTPStatus.BAD_REQUEST, "Invalid request target")
            return
        if path == "/api/catalog":
            self._send(
                HTTPStatus.OK, self.docs_server.catalog_bytes, "application/json; charset=utf-8"
            )
            return
        name = "index.html" if path == "/" else path.lstrip("/")
        if name not in self.docs_server.allowed:
            self._send(HTTPStatus.NOT_FOUND, b"Not found")
            return
        try:
            data = asset_bytes(name)
        except (OSError, ValueError) as error:
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, str(error).encode())
            return
        mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
        self._send(HTTPStatus.OK, data, f"{mime}; charset=utf-8")

    def _body(self) -> bytes:
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1 or self.headers.get("Transfer-Encoding") is not None:
            raise ValueError("Exactly one Content-Length and no Transfer-Encoding are required")
        if not lengths[0].isascii() or not lengths[0].isdigit():
            raise ValueError("Content-Length must contain decimal digits")
        length = int(lengths[0])
        if not 0 < length <= MAX_REQUEST_BYTES:
            raise ValueError("Preview body must be between 1 byte and 1 MiB")
        if self.headers.get_content_type() != "application/json":
            raise ValueError("Content-Type must be application/json")
        body = self.rfile.read(length)
        if len(body) != length:
            raise ValueError("Preview body ended before Content-Length")
        return body

    def do_POST(self) -> None:
        if not self._local():
            self._send(HTTPStatus.FORBIDDEN, b"Local origin required")
            return
        if self.path != "/api/preview":
            self._send(HTTPStatus.NOT_FOUND, b"Not found")
            return
        try:
            request = PreviewRequest.model_validate_json(self._body())
        except (ValueError, TimeoutError) as error:
            self._error(HTTPStatus.BAD_REQUEST, str(error))
            return
        try:
            result = self.docs_server.preview(request)
        except Exception as error:  # noqa: BLE001 - isolate unexpected failures at the HTTP boundary
            # This request boundary isolates unexpected documentation failures.
            # Do not include submitted YAML or exception payloads in the HTTP response/log.
            logger.error("Documentation preview callback failed: {}", type(error).__name__)
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Preview worker failed")
            return
        self._send(HTTPStatus.OK, result.model_dump_json().encode(), "application/json")


def make_server(catalog: Catalog, preview: PreviewCallback, port: int = 0) -> DocumentationServer:
    return DocumentationServer(catalog, preview, port)


def serve(catalog: Catalog, preview: PreviewCallback, *, port: int, browser: bool) -> None:
    with make_server(catalog, preview, port) as server:
        url = f"http://127.0.0.1:{server.server_port}/"
        sys.stdout.write(url + "\n")
        sys.stdout.flush()
        if browser:
            try:
                opened = webbrowser.open(url)
            except (webbrowser.Error, OSError):
                opened = False
            if not opened:
                sys.stderr.write("Cannot open a browser automatically; open the printed URL.\n")
        try:
            server.serve_forever(poll_interval=0.1)
        except KeyboardInterrupt:
            return
