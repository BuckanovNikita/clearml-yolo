"""The project's own test environment for the live tests.

A **test environment** is one Kubernetes namespace ``cy-it-<6 hex>`` on context
``docker-desktop`` that this project creates, uses and deletes: a ``ResourceQuota`` and a
``LimitRange`` first, then MongoDB (also the FiftyOne database) and, when ClearML is needed,
Redis, Elasticsearch and the ClearML API and file servers, every volume ``emptyDir``. The
manifests are in ``tests/integration/environment``. Host access is by ``kubectl
port-forward`` to loopback ports that kubectl chooses (plain HTTP inside the tunnel); no
ingress, certificate, host name, shared stand or k8s-infra helper is used.

The stand tests request the session fixtures of ``tests/integration/conftest.py``, which
select the environment lazily through ``Session``. The same steps by hand:

    uv run --locked python -m tests.integration.lifecycle check   # read-only preflight
    uv run --locked python -m tests.integration.lifecycle up      # create an environment
    exports="$(uv run --locked python -m tests.integration.lifecycle env)" && eval "$exports"
    uv run --locked python -m tests.integration.lifecycle stop    # delete it, prove it gone

Environment selection (one rule for ``up`` and session setup). The worktree's record
``tests/integration/.run-tag`` names at most one environment: its first line is the
identifier, then ``forward <component> <port> <pid> <start-time>`` lines for the detached
port-forwards of a manual ``up``; it never holds a credential.

- No record, a retired-format record (first line not an identifier, such as a run tag of the
  retired shared-stand lifecycle) or a stale record (namespace gone): the record is cleared
  without any delete call and a new environment is created.
- A live recorded environment (namespace present with the project label): a pytest session
  whose shell exports ``INTEGRATION_RUN_TAG`` equal to it adopts it and never creates or
  deletes anything; ``up`` and every other session refuse with exit 1.
- A recorded namespace without the project label: refused, record kept.

Whoever creates an environment deletes it: a session deletes the one it created (unless
``INTEGRATION_KEEP_DATA=1``); one created by ``up`` is deleted by ``stop``. Every delete passes
the deletion guard: the name must match ``^cy-it-[0-9a-f]{6}$`` and the live namespace must
carry ``app.kubernetes.io/part-of=clearml-yolo-tests``. The platform sweeper may delete any
environment 48 hours after its creation or after a Docker Desktop or PC restart; a vanished
namespace only makes the record stale.

Exit statuses: 0 success, 3 unavailable (cluster not answering, not ready within the start-up
budget: live verification is deferred), 1 error or refusal, 130 interrupted. ``check`` is
bounded by ``CY_INFRA_CHECK_TIMEOUT`` (60 s), start-up by ``CY_TEST_ENV_START_TIMEOUT``
(300 s) and teardown by ``CY_TEST_ENV_STOP_TIMEOUT`` (180 s).

The module stays standard-library only and never imports ``tests.env_isolation``. Inside
pytest that plugin replaces HOME and records the original values in ``CY_REAL_ENV``; this
module restores them for every child, because kubectl needs the real kubeconfig.
"""

import argparse
import base64
import io
import json
import math
import os
import re
import secrets
import shlex
import signal
import string
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterable, Sequence
from contextlib import redirect_stdout, suppress
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType
from typing import Any, Literal, NoReturn

PROJECT = "clearml-yolo"
CONTEXT = "docker-desktop"
MODULE = "uv run --locked python -m tests.integration.lifecycle"
IDENTIFIER_PREFIX = "cy-it-"
IDENTIFIER_PATTERN = re.compile(r"^cy-it-[0-9a-f]{6}$")
PART_OF_LABEL = "app.kubernetes.io/part-of"
PART_OF_VALUE = "clearml-yolo-tests"
SECRET_NAME = "cy-it-credentials"  # noqa: S105 - the Secret's name, not a value
MANIFEST_DIR = Path(__file__).resolve().parent / "environment"
RECORD_PATH = Path("tests") / "integration" / ".run-tag"
NAMESPACE_PLACEHOLDER = "__NAMESPACE__"

REAL_ENV_VARIABLE = "CY_REAL_ENV"
CHECK_TIMEOUT_VARIABLE = "CY_INFRA_CHECK_TIMEOUT"
START_TIMEOUT_VARIABLE = "CY_TEST_ENV_START_TIMEOUT"
STOP_TIMEOUT_VARIABLE = "CY_TEST_ENV_STOP_TIMEOUT"
DEFAULT_CHECK_TIMEOUT_SECONDS = 60.0
DEFAULT_START_TIMEOUT_SECONDS = 300.0
DEFAULT_STOP_TIMEOUT_SECONDS = 180.0
TASK_VERIFICATION_VARIABLE = "CY_TASK_VERIFICATION"
KEEP_DATA_VARIABLE = "INTEGRATION_KEEP_DATA"
RUN_TAG_VARIABLE = "INTEGRATION_RUN_TAG"
SWEEPER_NOTE = "the platform sweeper deletes it 48 hours after its creation or after a restart"

KUBECTL_TIMEOUT_SECONDS = 60.0
FORWARD_START_SECONDS = 30.0
FORWARD_STOP_SECONDS = 5.0
POLL_SECONDS = 2.0
NAMESPACE_ATTEMPTS = 5
# The user's own host ClearML listens on 8008; a forward never takes that port.
HOST_CLEARML_PORT = 8008
FORWARD_LINE = re.compile(r"Forwarding from 127\.0\.0\.1:(\d+) ->")

EXIT_AVAILABLE = 0
EXIT_ERROR = 1
EXIT_UNAVAILABLE = 3
EXIT_INTERRUPTED = 130

# Manifest groups and the deployments each one starts.
GROUPS: dict[str, tuple[str, ...]] = {
    "database": ("mongo",),
    "clearml": ("redis", "elastic", "apiserver", "fileserver"),
}
# Service ports reached through a port-forward.
FORWARD_PORTS = {"apiserver": 8008, "fileserver": 8081, "mongo": 27017}
type Selection = Literal["clearml", "fiftyone", "all"]
# selection: (manifest groups, forwarded components)
SELECTIONS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "clearml": (("database", "clearml"), ("apiserver", "fileserver")),
    "fiftyone": (("database",), ("mongo",)),
    "all": (("database", "clearml"), ("apiserver", "fileserver", "mongo")),
}

PERMANENT_TERMS = ("unauthorized", "forbidden", "certificate", "x509", "invalid credential", "401", "403")
# Refusals are matched by their specific texts: kubectl prefixes every failure, permanent
# configuration errors included (a missing exec credential plugin), with "Unable to connect to
# the server", so that prefix alone proves nothing. "was refused" covers kubectl's stopped API
# server ("The connection to the server <host:port> was refused"); "actively refused" and "no
# connection could be made" cover the Windows socket error.
TEMPORARY_TERMS = (
    "connection refused",
    "was refused",
    "actively refused",
    "no connection could be made",
    "connection reset",
    "remote end closed",
    "timed out",
    "timeout",
    "deadline exceeded",
    "no such host",
    "name or service not known",
    "unreachable",
    "eof",
    "serviceunavailable",
    "unable to handle the request",
    "502",
    "503",
    "504",
)
# Container states that keep a component from becoming ready; reported on budget expiry.
WAITING_REASONS = ("ImagePullBackOff", "ErrImagePull", "CrashLoopBackOff", "CreateContainerConfigError")


class LifecycleError(Exception):
    """A refusal or failure, reported as ``ERROR:`` plus indented detail lines."""

    def __init__(self, *lines: str) -> None:
        """Keep every line; the first is the headline."""
        super().__init__(lines[0])
        self.lines = lines


class StandUnavailableError(LifecycleError):
    """Temporary infrastructure unavailability; live verification is deferred."""


def fail(*lines: str) -> NoReturn:
    raise LifecycleError(*lines)


def log(message: str) -> None:
    sys.stdout.write(f"==> {message}\n")


def warn(message: str) -> None:
    sys.stderr.write(f"{message}\n")


def report(error: LifecycleError) -> None:
    first, *rest = error.lines
    warn(f"ERROR: {first}")
    for line in rest:
        warn(f"       {line}")


def child_env() -> dict[str, str]:
    """Return the environment with what ``tests.env_isolation`` replaced restored.

    ``CY_REAL_ENV`` maps each replaced name to its original value, or to null when it was
    unset; outside pytest it is absent and nothing changes.
    """
    environ = dict(os.environ)
    try:
        recorded: object = json.loads(environ.get(REAL_ENV_VARIABLE, "{}"))
    except json.JSONDecodeError:
        recorded = {}
    if not isinstance(recorded, dict):
        return environ
    for name, value in recorded.items():
        if value is None:
            environ.pop(str(name), None)
        else:
            environ[str(name)] = str(value)
    return environ


def is_identifier(name: str) -> bool:
    return bool(IDENTIFIER_PATTERN.match(name))


def tagged_project_name(tag: str, name: str = PROJECT) -> str:
    """ClearML project name whose first token is the environment identifier."""
    return f"{tag} {name}"


def positive_seconds(variable: str, default: float) -> float:
    raw = os.environ.get(variable, str(default))
    try:
        seconds = float(raw)
    except ValueError:
        fail(f"{variable} must be a positive finite number of seconds")
    if not math.isfinite(seconds) or seconds <= 0:
        fail(f"{variable} must be a positive finite number of seconds")
    return seconds


def is_temporary(detail: str) -> bool:
    """Whether lower-cased error text reports lost connectivity and no permanent problem."""
    if any(term in detail for term in PERMANENT_TERMS):
        return False
    return any(term in detail for term in TEMPORARY_TERMS)


def first_line(text: str | None) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    return lines[0] if lines else "no error text"


def classify_failure(result: subprocess.CompletedProcess[str], description: str, *, quote: bool = True) -> NoReturn:
    """Separate temporary connectivity loss from permanent errors.

    ``quote=False`` withholds kubectl's error text, for calls whose input or output holds
    credentials.
    """
    detail = (result.stderr or "").lower()
    if is_temporary(detail):
        raise StandUnavailableError(f"{description}: the {CONTEXT} cluster does not answer")
    if quote:
        fail(f"{description} failed (exit {result.returncode}):", first_line(result.stderr))
    fail(f"{description} failed (exit {result.returncode}); check kubectl access to {CONTEXT}.")


def kubectl(
    *args: str, stdin: str | None = None, timeout: float = KUBECTL_TIMEOUT_SECONDS
) -> subprocess.CompletedProcess[str]:
    """Run one bounded kubectl call on the docker-desktop context; input goes through stdin."""
    command = ["kubectl", "--context", CONTEXT, *args]
    try:
        return subprocess.run(  # noqa: S603 - fixed kubectl argument vectors
            command, input=stdin, capture_output=True, text=True, timeout=timeout, env=child_env(), check=False
        )
    except FileNotFoundError:
        fail("kubectl is not installed or not on PATH; the live tests need it.")
    except subprocess.TimeoutExpired as error:
        raise StandUnavailableError(f"kubectl {args[0]} did not finish within {timeout:g} s") from error


# -- preflight ---------------------------------------------------------------------


def _probe_call(command: Sequence[str], deadline: float) -> subprocess.CompletedProcess[str]:
    """Bound a read-only probe and kill only its own process group on timeout."""
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise StandUnavailableError("infrastructure preflight deadline expired")
    try:
        with subprocess.Popen(  # noqa: S603 - fixed read-only tool commands
            list(command),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=child_env(),
            start_new_session=True,
        ) as child:
            try:
                stdout, stderr = child.communicate(timeout=remaining)
            except (subprocess.TimeoutExpired, KeyboardInterrupt, SystemExit) as error:
                with suppress(ProcessLookupError):
                    os.killpg(child.pid, signal.SIGKILL)
                child.communicate()
                if isinstance(error, subprocess.TimeoutExpired):
                    raise StandUnavailableError(
                        f"infrastructure preflight timed out during {Path(command[0]).name}"
                    ) from error
                raise
    except FileNotFoundError:
        fail(f"{command[0]} is not installed or not on PATH; the live tests need it.")
    return subprocess.CompletedProcess(list(command), child.returncode, stdout, stderr)


def _require_context(deadline: float) -> None:
    result = _probe_call(["kubectl", "config", "get-contexts", CONTEXT, "-o", "name"], deadline)
    if result.returncode != 0 or result.stdout.strip() != CONTEXT:
        fail(f"kubectl has no context '{CONTEXT}'; enable Kubernetes in Docker Desktop or restore the context.")


def _require_cluster(deadline: float) -> None:
    result = _probe_call(["kubectl", "--context", CONTEXT, "get", "--raw=/readyz"], deadline)
    if result.returncode == 0:
        return
    detail = (result.stderr or "").lower()
    if any(term in detail for term in PERMANENT_TERMS):
        fail("Kubernetes access, credentials or TLS configuration failed; check kubectl access.")
    if is_temporary(detail):
        raise StandUnavailableError(f"the {CONTEXT} cluster does not answer")
    fail(f"Kubernetes readiness probe failed unexpectedly (exit {result.returncode}); check kubectl access.")


def _require_permission(deadline: float) -> None:
    result = _probe_call(["kubectl", "--context", CONTEXT, "auth", "can-i", "create", "namespaces"], deadline)
    answer = result.stdout.strip()
    if answer == "yes":
        return
    if answer == "no":
        fail(f"this kubeconfig may not create namespaces on {CONTEXT}; the test environment needs that permission.")
    if is_temporary((result.stderr or "").lower()):
        raise StandUnavailableError(f"the {CONTEXT} cluster does not answer")
    fail(f"kubectl auth can-i create namespaces failed (exit {result.returncode}); check kubectl access.")


def pinned_images() -> list[str]:
    images: set[str] = set()
    for manifest in sorted(MANIFEST_DIR.glob("*.yaml")):
        images.update(re.findall(r"^\s*image:\s*(\S+)\s*$", manifest.read_text(encoding="utf-8"), re.MULTILINE))
    return sorted(images)


def _report_unlisted_images(deadline: float) -> None:
    """Informational: the node lists only some cached images, so absence is not proof."""
    result = _probe_call(
        ["kubectl", "--context", CONTEXT, "get", "nodes", "-o", "jsonpath={.items[*].status.images[*].names[*]}"],
        deadline,
    )
    if result.returncode != 0:
        return
    listed = set(result.stdout.split())
    missing = [image for image in pinned_images() if image not in listed]
    if missing:
        log(
            "note: the node does not list these pinned images (its list is capped, so they may still be "
            f"cached; otherwise the first start pulls them): {', '.join(missing)}"
        )


def preflight() -> None:
    """One read-only preflight with one overall deadline; creates nothing."""
    deadline = time.monotonic() + positive_seconds(CHECK_TIMEOUT_VARIABLE, DEFAULT_CHECK_TIMEOUT_SECONDS)
    _require_context(deadline)
    _require_cluster(deadline)
    _require_permission(deadline)
    _report_unlisted_images(deadline)


# -- port-forwards -----------------------------------------------------------------


def process_start(pid: int) -> str | None:
    """Return the kernel start time of a running process, or None when it is gone."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except OSError:
        return None
    fields = stat.rsplit(")", 1)[-1].split()
    # fields[0] is the state (field 3 of the stat line); fields[19] is starttime (field 22).
    if len(fields) < 20 or fields[0] in {"Z", "X"}:
        return None
    return fields[19]


def forward_log(identifier: str, component: str) -> Path:
    return Path(tempfile.gettempdir()) / f"{identifier}-forward-{component}.log"


@dataclass
class Forward:
    """One loopback port-forward to a component's Service."""

    component: str
    port: int
    pid: int
    start: str
    process: "subprocess.Popen[bytes] | None" = None

    def running(self) -> bool:
        if self.process is not None:
            return self.process.poll() is None
        return process_start(self.pid) == self.start

    def stop(self) -> None:
        """Stop the forward: a child directly, a recorded one only when PID and start time match."""
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=FORWARD_STOP_SECONDS)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            return
        if process_start(self.pid) != self.start:
            return
        with suppress(ProcessLookupError):
            os.kill(self.pid, signal.SIGTERM)
        deadline = time.monotonic() + FORWARD_STOP_SECONDS
        while process_start(self.pid) == self.start and time.monotonic() < deadline:
            time.sleep(0.1)
        if process_start(self.pid) == self.start:
            with suppress(ProcessLookupError):
                os.kill(self.pid, signal.SIGKILL)

    def line(self) -> str:
        return f"forward {self.component} {self.port} {self.pid} {self.start}"


def _await_forward_port(process: "subprocess.Popen[bytes]", log_path: Path, component: str) -> int:
    deadline = time.monotonic() + FORWARD_START_SECONDS
    while True:
        text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        found = FORWARD_LINE.search(text)
        if found:
            return int(found.group(1))
        if process.poll() is not None:
            raise StandUnavailableError(f"the port-forward to {component} exited: {first_line(text)}")
        if time.monotonic() >= deadline:
            process.kill()
            process.wait()
            raise StandUnavailableError(
                f"the port-forward to {component} chose no port within {FORWARD_START_SECONDS:g} s"
            )
        time.sleep(0.2)


def _forward_prefix(identifier: str) -> list[str]:
    return ["kubectl", "--context", CONTEXT, "--namespace", identifier, "port-forward"]


def unrecorded_forwards(identifier: str) -> list[Forward]:
    """Find the current user's port-forward processes of one environment by their command line.

    A session's port-forwards are its children and are not recorded; when the session is
    killed (SIGKILL, a closed terminal) they outlive it. Their command line starts with the
    exact vector ``start_forward`` uses, which names the environment's namespace, so no
    other process matches.
    """
    prefix = _forward_prefix(identifier)
    found: list[Forward] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            words = [word.decode(errors="replace") for word in (entry / "cmdline").read_bytes().split(b"\0") if word]
        except OSError:
            continue
        if len(words) < len(prefix) + 2 or words[: len(prefix)] != prefix:
            continue
        start = process_start(int(entry.name))
        if start is not None:
            found.append(Forward(words[-2].removeprefix("svc/"), 0, int(entry.name), start))
    return found


def start_forward(identifier: str, component: str) -> Forward:
    """Forward a loopback port chosen by kubectl to the component's Service.

    The child runs in its own session with stdin closed and its output in a file outside the
    repository, so it neither receives the terminal's Ctrl-C nor stalls on a full pipe.
    """
    log_path = forward_log(identifier, component)
    command = [
        *_forward_prefix(identifier),
        "--address",
        "127.0.0.1",
        f"svc/{component}",
        f":{FORWARD_PORTS[component]}",
    ]
    for _attempt in range(2):
        with log_path.open("wb") as output:
            process = subprocess.Popen(  # noqa: S603 - fixed kubectl argument vector
                command,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                env=child_env(),
                start_new_session=True,
            )
        port = _await_forward_port(process, log_path, component)
        start = process_start(process.pid)
        if port != HOST_CLEARML_PORT and start is not None:
            return Forward(component, port, process.pid, start, process)
        process.kill()
        process.wait()
    raise StandUnavailableError(f"the port-forward to {component} could not be started")


# -- record and namespace state ------------------------------------------------------


def _parse_forward(line: str) -> Forward | None:
    words = line.split()
    if len(words) != 5 or words[0] != "forward" or words[1] not in FORWARD_PORTS:
        return None
    if not (words[2].isdigit() and words[3].isdigit()):
        return None
    return Forward(words[1], int(words[2]), int(words[3]), words[4])


@dataclass
class Record:
    """The worktree's note of its environment: identifier and detached port-forwards."""

    path: Path

    def read(self) -> tuple[str, list[Forward]] | None:
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return None
        except (OSError, UnicodeDecodeError):
            lines = []
        identifier = lines[0].strip() if lines else ""
        forwards = [forward for forward in map(_parse_forward, lines[1:]) if forward is not None]
        return identifier, forwards

    def write(self, identifier: str, forwards: Iterable[Forward] = ()) -> None:
        lines = [identifier, *(forward.line() for forward in forwards)]
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def clear(self, identifier: str | None = None) -> None:
        """Remove the record; with an identifier, only when the record names it."""
        if identifier is not None:
            recorded = self.read()
            if recorded is None or recorded[0] != identifier:
                return
        self.path.unlink(missing_ok=True)


type NamespaceState = Literal["absent", "foreign", "live"]


def namespace_state(identifier: str, *, timeout: float = KUBECTL_TIMEOUT_SECONDS) -> NamespaceState:
    """Absent only on an explicit NotFound; a connectivity error never counts as absent."""
    result = kubectl("get", "namespace", identifier, "-o", "json", timeout=timeout)
    if result.returncode == 0:
        try:
            labels = json.loads(result.stdout).get("metadata", {}).get("labels", {}) or {}
        except json.JSONDecodeError:
            fail(f"kubectl returned unreadable JSON for namespace {identifier}")
        return "live" if labels.get(PART_OF_LABEL) == PART_OF_VALUE else "foreign"
    if "(notfound)" in (result.stderr or "").lower():
        return "absent"
    classify_failure(result, f"reading namespace {identifier}")


# -- teardown (deletion guard) -------------------------------------------------------


def _await_absence(identifier: str) -> bool:
    deadline = time.monotonic() + positive_seconds(STOP_TIMEOUT_VARIABLE, DEFAULT_STOP_TIMEOUT_SECONDS)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        if namespace_state(identifier, timeout=min(KUBECTL_TIMEOUT_SECONDS, remaining)) == "absent":
            return True
        time.sleep(min(POLL_SECONDS, max(0.0, deadline - time.monotonic())))


def _unlisted(identifier: str, forwards: Sequence[Forward]) -> list[Forward]:
    known = {forward.pid for forward in forwards}
    return [forward for forward in unrecorded_forwards(identifier) if forward.pid not in known]


def stop_unlisted_forwards(identifier: str, forwards: Sequence[Forward] = ()) -> None:
    """Stop the environment's port-forwards that ``forwards`` does not list (a killed session's)."""
    for forward in _unlisted(identifier, forwards):
        log(f"stopping port-forward {forward.pid} to {forward.component} of {identifier} left by an ended session")
        forward.stop()


def remove(root: Path, identifier: str, forwards: Sequence[Forward] = (), *, dry_run: bool = False) -> int:
    """Delete one environment behind the deletion guard and prove it gone.

    The guard: the name must be an environment identifier and the live namespace must carry
    the project label; otherwise nothing is signalled or deleted and the record is kept.
    """
    if not is_identifier(identifier):
        fail(f"'{identifier}' is not an environment identifier (cy-it-<6 hex>); nothing was stopped or deleted.")
    record = Record(root / RECORD_PATH)
    state = namespace_state(identifier)
    if state == "foreign":
        fail(
            f"namespace {identifier} exists without the label {PART_OF_LABEL}={PART_OF_VALUE};",
            "it is not this project's environment: nothing was deleted and the record is kept.",
        )
    if dry_run:
        action = "is already gone" if state == "absent" else "would be deleted"
        count = len(forwards) + len(_unlisted(identifier, forwards))
        log(f"dry run: {count} port-forward(s) would be stopped; namespace {identifier} {action}")
        return EXIT_AVAILABLE
    for forward in forwards:
        forward.stop()
    stop_unlisted_forwards(identifier, forwards)
    for component in FORWARD_PORTS:
        forward_log(identifier, component).unlink(missing_ok=True)
    if state == "absent":
        log(f"namespace {identifier} is already gone")
        record.clear(identifier)
        return EXIT_AVAILABLE
    log(f"deleting namespace {identifier}")
    deleted = kubectl("delete", "namespace", identifier, "--wait=false")
    if deleted.returncode != 0 and "(notfound)" not in (deleted.stderr or "").lower():
        warn(f"ERROR: kubectl delete namespace {identifier} failed: {first_line(deleted.stderr)}")
    if not _await_absence(identifier):
        warn(f"ERROR: namespace {identifier} is not proven gone; the record stays for the retry:")
        warn(f"       {MODULE} stop --env {identifier}")
        return EXIT_ERROR
    log(f"namespace {identifier} deleted and proven absent")
    record.clear(identifier)
    return EXIT_AVAILABLE


def stop(root: Path, target: str | None, *, dry_run: bool = False) -> int:
    """Stop the named or recorded environment; a retired-format record is only cleared."""
    record = Record(root / RECORD_PATH)
    recorded = record.read()
    if target is not None:
        if not is_identifier(target):
            fail(f"--env '{target}' is not an environment identifier (cy-it-<6 hex>); nothing was stopped or deleted.")
    elif recorded is None:
        fail(
            "no environment is recorded in this worktree; nothing to stop.",
            f"start one with {MODULE} up, or name one with --env cy-it-<id>.",
        )
    elif not is_identifier(recorded[0]):
        if dry_run:
            log(f"dry run: {record.path} holds a retired record ('{recorded[0]}'); it would be cleared")
            return EXIT_AVAILABLE
        record.clear()
        log(f"cleared a retired record ('{recorded[0]}' is not an environment identifier); nothing was deleted")
        return EXIT_AVAILABLE
    else:
        target = recorded[0]
    forwards = recorded[1] if recorded is not None and recorded[0] == target else []
    return remove(root, target, forwards, dry_run=dry_run)


# -- environment ---------------------------------------------------------------------


def _render(name: str, identifier: str) -> str:
    return (MANIFEST_DIR / name).read_text(encoding="utf-8").replace(NAMESPACE_PLACEHOLDER, identifier)


def _secret_manifest(identifier: str, credentials: dict[str, str]) -> str:
    return json.dumps(
        {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": SECRET_NAME,
                "namespace": identifier,
                "labels": {PART_OF_LABEL: PART_OF_VALUE, "clearml-yolo/environment": identifier},
            },
            "type": "Opaque",
            "stringData": credentials,
        }
    )


def generate_credentials() -> dict[str, str]:
    """The API server's system pair and token secret and the built-in ``tests`` user's pair."""
    alphabet = string.ascii_uppercase + string.digits

    def key() -> str:
        return "".join(secrets.choice(alphabet) for _ in range(24))

    return {
        "apiserver_key": key(),
        "apiserver_secret": secrets.token_urlsafe(36),
        "token_secret": secrets.token_urlsafe(36),
        "test_key": key(),
        "test_secret": secrets.token_urlsafe(36),
    }


def read_credentials(identifier: str) -> dict[str, str]:
    """Read the SDK pair from the environment's Secret; never echo kubectl's output."""
    result = kubectl("get", "secret", SECRET_NAME, "--namespace", identifier, "-o", "json")
    if result.returncode != 0:
        classify_failure(result, f"reading the credentials of {identifier}", quote=False)
    try:
        data = json.loads(result.stdout).get("data", {})
        return {name: base64.b64decode(data[name]).decode() for name in ("test_key", "test_secret")}
    except (json.JSONDecodeError, KeyError, ValueError):
        fail(f"the Secret {SECRET_NAME} of {identifier} does not hold the test key pair")


def _deployment_problem(deployment: dict[str, Any]) -> str | None:
    """A rejection by the quota or the limit range shows as a ReplicaFailure condition."""
    for condition in deployment.get("status", {}).get("conditions", []):
        if condition.get("type") == "ReplicaFailure" and condition.get("status") == "True":
            return str(condition.get("message", "rejected"))
    return None


def _pod_reasons(pods: Iterable[dict[str, Any]]) -> dict[str, str]:
    """Why each component's pod is not ready: a blocking container state, else its phase."""
    reasons: dict[str, str] = {}
    for pod in pods:
        status = pod.get("status", {})
        statuses = [*status.get("initContainerStatuses", []), *status.get("containerStatuses", [])]
        waiting = [entry.get("state", {}).get("waiting", {}).get("reason", "") for entry in statuses]
        blocking = [reason for reason in waiting if reason in WAITING_REASONS]
        app = str(pod.get("metadata", {}).get("labels", {}).get("app", "?"))
        reasons[app] = blocking[0] if blocking else str(status.get("phase", "unknown"))
    return reasons


@dataclass
class Environment:
    """One test environment: its namespace, credentials and port-forwards."""

    root: Path
    identifier: str
    created: bool
    detached: bool = False
    groups: set[str] = field(default_factory=set)
    forwards: dict[str, Forward] = field(default_factory=dict)
    credentials: dict[str, str] = field(default_factory=dict)

    @property
    def tag(self) -> str:
        """The identifier as the run tag of ClearML project names and ``clearml.tags``."""
        return self.identifier

    @property
    def record(self) -> Record:
        return Record(self.root / RECORD_PATH)

    @property
    def exported(self) -> dict[str, str]:
        """The variables the tests and manual tools use; printed only by ``env``."""
        values = {RUN_TAG_VARIABLE: self.identifier}
        if "apiserver" in self.forwards and "fileserver" in self.forwards:
            api = f"http://127.0.0.1:{self.forwards['apiserver'].port}"
            values |= {
                "CLEARML_API_HOST": api,
                "CLEARML_WEB_HOST": api,
                "CLEARML_FILES_HOST": f"http://127.0.0.1:{self.forwards['fileserver'].port}",
                "CLEARML_API_ACCESS_KEY": self.credentials["test_key"],
                "CLEARML_API_SECRET_KEY": self.credentials["test_secret"],
            }
        if "mongo" in self.forwards:
            values["FIFTYONE_DATABASE_URI"] = f"mongodb://127.0.0.1:{self.forwards['mongo'].port}/"
            values["FIFTYONE_DATABASE_DIR"] = os.environ.get("FIFTYONE_DATABASE_DIR") or str(
                Path.home() / ".cache" / "clearml-yolo" / "fiftyone"
            )
        return values

    def endpoints(self) -> str:
        values = self.exported
        names = ("CLEARML_API_HOST", "CLEARML_FILES_HOST", "FIFTYONE_DATABASE_URI")
        return ", ".join(f"{name}={values[name]}" for name in names if name in values)

    # -- creation ----------------------------------------------------------

    def _apply(self, text: str, description: str, *, quote: bool = True) -> None:
        result = kubectl("apply", "-f", "-", stdin=text)
        if result.returncode != 0:
            classify_failure(result, f"applying {description} in {self.identifier}", quote=quote)

    def _components(self, *, timeout: float) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
        result = kubectl("get", "deployments,pods", "--namespace", self.identifier, "-o", "json", timeout=timeout)
        if result.returncode != 0:
            classify_failure(result, f"reading the components of {self.identifier}")
        items: list[dict[str, Any]] = json.loads(result.stdout).get("items", [])
        deployments = {item["metadata"]["name"]: item for item in items if item.get("kind") == "Deployment"}
        return deployments, [item for item in items if item.get("kind") == "Pod"]

    def _wait(self, names: Sequence[str]) -> None:
        """Wait until every deployment has a ready pod, within the start-up budget."""
        budget = positive_seconds(START_TIMEOUT_VARIABLE, DEFAULT_START_TIMEOUT_SECONDS)
        deadline = time.monotonic() + budget
        pending = list(names)
        pods: list[dict[str, Any]] = []
        while names:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            deployments, pods = self._components(timeout=min(KUBECTL_TIMEOUT_SECONDS, remaining))
            for name in names:
                problem = _deployment_problem(deployments.get(name, {}))
                if problem is not None:
                    fail(f"component {name} of {self.identifier} was rejected:", problem)
            pending = [name for name in names if not deployments.get(name, {}).get("status", {}).get("readyReplicas")]
            if not pending:
                return
            time.sleep(min(POLL_SECONDS, max(0.0, deadline - time.monotonic())))
        if pending:
            reasons = _pod_reasons(pods)
            details = ", ".join(f"{name}: {reasons.get(name, 'no pod')}" for name in pending)
            raise StandUnavailableError(f"{self.identifier} was not ready within {budget:g} s ({details})")

    def _create_namespace(self) -> None:
        for _attempt in range(NAMESPACE_ATTEMPTS):
            self.identifier = IDENTIFIER_PREFIX + secrets.token_hex(3)
            result = kubectl("create", "-f", "-", stdin=_render("namespace.yaml", self.identifier))
            if result.returncode == 0:
                return
            if "alreadyexists" not in (result.stderr or "").lower().replace(" ", ""):
                classify_failure(result, "creating the environment namespace")
        fail(f"no free environment identifier after {NAMESPACE_ATTEMPTS} attempts")

    def create(self, selection: Selection) -> None:
        """Namespace, quota and limit range, credentials, then the selected components.

        Any failure or interrupt after the namespace exists deletes it before propagating.
        """
        self._create_namespace()
        try:
            # Recording is part of setup: even a failed record write must clean up
            # the namespace whose successful creation we have already observed.
            self.record.write(self.identifier)
            log(f"created namespace {self.identifier}")
            self._apply(_render("guard.yaml", self.identifier), "the quota and limit range")
            self.credentials = generate_credentials()
            self._apply(_secret_manifest(self.identifier, self.credentials), "the credentials Secret", quote=False)
            self.provide(selection)
        except BaseException:
            self.discard()
            raise

    def provide(self, selection: Selection) -> None:
        """Start what the selection needs and is not running yet, then forward its ports."""
        groups, components = SELECTIONS[selection]
        missing = [group for group in groups if group not in self.groups]
        for group in missing:
            self._apply(_render(f"{group}.yaml", self.identifier), f"the {group} components")
        started = time.monotonic()
        self._wait([name for group in missing for name in GROUPS[group]])
        self.groups.update(missing)
        if missing:
            log(f"{self.identifier}: {', '.join(missing)} components ready in {time.monotonic() - started:.0f} s")
        for component in components:
            if component not in self.forwards:
                self.forwards[component] = start_forward(self.identifier, component)
        if self.detached:
            self.record.write(self.identifier, self.forwards.values())

    def discard(self) -> None:
        """Setup-failure cleanup: guarded delete of the namespace this process created."""
        recovery = f"retry: {MODULE} stop --env {self.identifier}"
        try:
            status = remove(self.root, self.identifier, list(self.forwards.values()))
        except (LifecycleError, OSError) as error:
            details = error.lines if isinstance(error, LifecycleError) else (type(error).__name__,)
            raise LifecycleError(
                f"setup cleanup of {self.identifier} is incomplete; the environment is not proven deleted",
                *details,
                recovery,
            ) from error
        if status != EXIT_AVAILABLE:
            fail(
                f"setup cleanup of {self.identifier} is incomplete; the environment is not proven deleted",
                recovery,
            )

    # -- adoption ------------------------------------------------------------

    def require(self, selection: Selection) -> None:
        """An adopted environment must already run what the session needs."""
        for component in SELECTIONS[selection][1]:
            forward = self.forwards.get(component)
            if forward is None or not forward.running():
                fail(
                    f"the adopted environment {self.identifier} has no running port-forward to {component};",
                    f"nothing was created or deleted. Restart it: {MODULE} stop, then {MODULE} up.",
                )
        if "apiserver" in self.forwards and not self.credentials:
            self.credentials = read_credentials(self.identifier)


# -- selection -------------------------------------------------------------------------


def _inspect(root: Path) -> tuple[str, str, list[Forward]]:
    """Classify the record: none, retired, stale, live or foreign."""
    recorded = Record(root / RECORD_PATH).read()
    if recorded is None:
        return "none", "", []
    identifier, forwards = recorded
    if not is_identifier(identifier):
        return "retired", identifier, forwards
    state = namespace_state(identifier)
    return ("stale" if state == "absent" else state), identifier, forwards


def _clear_unusable(root: Path, kind: str, identifier: str, forwards: Sequence[Forward]) -> None:
    """Clear a retired or stale record without any delete call."""
    if kind == "retired":
        log(f"cleared a retired record ('{identifier}' is not an environment identifier); nothing was deleted")
    elif kind == "stale":
        for forward in forwards:
            forward.stop()
        stop_unlisted_forwards(identifier, forwards)
        log(f"recorded environment {identifier} no longer exists; record cleared, nothing was deleted")
    else:
        return
    Record(root / RECORD_PATH).clear()


def _refuse_foreign(root: Path, identifier: str) -> NoReturn:
    fail(
        f"{root / RECORD_PATH} names namespace {identifier}, which exists without the label",
        f"{PART_OF_LABEL}={PART_OF_VALUE}: it is not this project's environment. Nothing was created or",
        "deleted and the record is kept; inspect the namespace by hand.",
    )


def _refuse_live(root: Path, identifier: str, reason: str) -> NoReturn:
    fail(
        f"environment {identifier} is active in this worktree ({root / RECORD_PATH}); {reason}",
        f'use it: exports="$({MODULE} env)" && eval "$exports"; or delete it: {MODULE} stop',
    )


def up(root: Path, selection: Selection) -> Environment:
    """Preflight, select (never adopt), create with detached port-forwards and record them."""
    preflight()
    kind, identifier, forwards = _inspect(root)
    if kind == "foreign":
        _refuse_foreign(root, identifier)
    if kind == "live":
        _refuse_live(root, identifier, "up never starts a second one.")
    _clear_unusable(root, kind, identifier, forwards)
    environment = Environment(root, "", created=True, detached=True)
    environment.create(selection)
    return environment


def adopt_or_create(root: Path, selection: Selection) -> Environment:
    """Session setup: adopt the live recorded environment only when the shell exports its identifier."""
    preflight()
    exported = os.environ.get(RUN_TAG_VARIABLE, "")
    kind, identifier, forwards = _inspect(root)
    if kind == "foreign":
        _refuse_foreign(root, identifier)
    if kind == "live":
        if exported != identifier:
            state = "unset" if not exported else f"'{exported}'"
            _refuse_live(root, identifier, f"this session does not adopt it ({RUN_TAG_VARIABLE} is {state}).")
        environment = Environment(root, identifier, created=False)
        environment.forwards = {forward.component: forward for forward in forwards}
        environment.require(selection)
        log(f"adopted environment {identifier} ({RUN_TAG_VARIABLE} equals the record); this session deletes nothing")
        return environment
    _clear_unusable(root, kind, identifier, forwards)
    if exported:
        log(f"{RUN_TAG_VARIABLE}={exported} names no live recorded environment; this session creates its own")
    environment = Environment(root, "", created=True)
    environment.create(selection)
    return environment


def recorded_environment(root: Path) -> Environment:
    """The live recorded environment with running forwards, for ``env``."""
    kind, identifier, forwards = _inspect(root)
    if kind != "live":
        fail("no live recorded environment in this worktree; start one with:", f"{MODULE} up")
    if not forwards:
        fail(
            f"environment {identifier} has no recorded port-forwards: a pytest session owns it;",
            f"env serves environments started by {MODULE} up.",
        )
    environment = Environment(root, identifier, created=False)
    environment.forwards = {forward.component: forward for forward in forwards}
    for forward in forwards:
        if not forward.running():
            fail(
                f"the port-forward to {forward.component} of {identifier} is not running;",
                f"restart the environment: {MODULE} stop, then {MODULE} up.",
            )
    if "apiserver" in environment.forwards:
        environment.credentials = read_credentials(identifier)
    return environment


class Session:
    """The pytest session's environment, selected lazily when a test first needs it."""

    def __init__(self, root: Path) -> None:
        """Select nothing yet."""
        self.root = root
        self.environment: Environment | None = None

    def ensure(self, selection: Selection) -> Environment:
        """Adopt or create on first use; later uses start (or, when adopted, require) more."""
        if self.environment is None:
            self.environment = adopt_or_create(self.root, selection)
        elif self.environment.created:
            try:
                self.environment.provide(selection)
            except BaseException:
                self.environment.discard()
                self.environment = None
                raise
        else:
            self.environment.require(selection)
        os.environ.update(self.environment.exported)
        return self.environment

    def finish(self) -> int:
        """Delete the environment this session created, unless kept; never an adopted one."""
        environment = self.environment
        if environment is None:
            return EXIT_AVAILABLE
        if not environment.created:
            log(f"leaving adopted environment {environment.identifier}; remove it with {MODULE} stop")
            log(f"    {SWEEPER_NOTE}")
            return EXIT_AVAILABLE
        if os.environ.get(KEEP_DATA_VARIABLE, "") == "1":
            for forward in environment.forwards.values():
                forward.stop()
            log(f"keeping environment {environment.identifier} for inspection ({KEEP_DATA_VARIABLE}=1)")
            log(f"    remove it with {MODULE} stop; {SWEEPER_NOTE}")
            return EXIT_AVAILABLE
        return remove(self.root, environment.identifier, list(environment.forwards.values()))


# -- command line ----------------------------------------------------------------------


def _terminate(signum: int, _frame: FrameType | None) -> NoReturn:
    """Turn SIGTERM into an exit so cleanup handlers run."""
    raise SystemExit(128 + signum)


def _print_env(root: Path) -> None:
    if sys.stdout.isatty():
        fail(
            "env prints the environment's credentials; evaluate it instead of reading it:",
            f'exports="$({MODULE} env)" && eval "$exports"',
        )
    for key, value in recorded_environment(root).exported.items():
        sys.stdout.write(f"export {key}={shlex.quote(value)}\n")


def _dispatch(args: argparse.Namespace, root: Path) -> int:
    if args.command == "check":
        preflight()
        log("AVAILABLE: infrastructure preflight passed; no resources created")
        return EXIT_AVAILABLE
    if args.command == "up":
        with redirect_stdout(sys.stderr if args.identifier_only else sys.stdout):
            environment = up(root, args.components)
            log(f"environment {environment.identifier} is ready: {environment.endpoints()}")
            log(f'Use it:    exports="$({MODULE} env)" && eval "$exports"  (pytest in that shell adopts it)')
            log(f"Tear down: {MODULE} stop --env {environment.identifier}")
            log(f"Note:      {SWEEPER_NOTE}")
        if args.identifier_only:
            sys.stdout.write(f"{environment.identifier}\n")
        return EXIT_AVAILABLE
    if args.command == "env":
        _print_env(root)
        return EXIT_AVAILABLE
    try:
        return stop(root, args.env, dry_run=args.dry_run)
    except StandUnavailableError as error:
        report(LifecycleError(f"{error}; nothing was proven deleted and the record is kept"))
        return EXIT_ERROR


def main(argv: Sequence[str] | None = None, *, on_signal: Callable[..., object] = signal.signal) -> int:
    parser = argparse.ArgumentParser(prog=MODULE, description="The project's own Kubernetes test environment.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help=argparse.SUPPRESS,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="read-only bounded preflight (0 available, 3 unavailable, 1 error)")
    commands.add_parser("env", help="print the recorded environment's variables as shell exports")
    starting = commands.add_parser("up", help="create an environment with detached port-forwards")
    starting.add_argument("--components", choices=sorted(SELECTIONS), default="all")
    starting.add_argument(
        "--identifier-only",
        action="store_true",
        help="print only the created identifier to stdout; progress goes to stderr",
    )
    stopping = commands.add_parser("stop", help="delete the recorded (or named) environment and prove it gone")
    stopping.add_argument("--env", default=None, help="environment identifier cy-it-<6 hex>")
    stopping.add_argument("--dry-run", action="store_true", help="apply the guard and report; change nothing")
    args = parser.parse_args(argv)

    if isinstance(sys.stdout, io.TextIOWrapper):
        # Our lines must interleave with the children's in captured output.
        sys.stdout.reconfigure(line_buffering=True)
    on_signal(signal.SIGTERM, _terminate)
    root: Path = args.repo_root.resolve()
    try:
        return _dispatch(args, root)
    except StandUnavailableError as error:
        warn(f"UNAVAILABLE: {error}; live verification is deferred")
        return EXIT_UNAVAILABLE
    except LifecycleError as error:
        report(error)
        return EXIT_ERROR
    except OSError as error:
        warn(f"ERROR: lifecycle operation could not access a required tool or file ({type(error).__name__})")
        return EXIT_ERROR
    except KeyboardInterrupt:
        warn("interrupted")
        return EXIT_INTERRUPTED


if __name__ == "__main__":
    sys.exit(main())
