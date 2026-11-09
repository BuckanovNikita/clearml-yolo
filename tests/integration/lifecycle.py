"""Live-run lifecycle on the shared ClearML stand.

The stand tests in ``tests/integration`` request the session fixture ``live_run``
(``tests/integration/conftest.py``), which calls ``prepare`` before the first stand test
and ``finish`` after the last one. The same steps by hand:

    uv run --frozen --no-sync python -m tests.integration.lifecycle check  # read-only preflight
    uv run --frozen --no-sync python -m tests.integration.lifecycle up     # claim a run tag
    eval "$(uv run --frozen --no-sync python -m tests.integration.lifecycle env)"
    uv run --frozen --no-sync python -m tests.integration.lifecycle stop   # exact-tag cleanup

The run acts as project ``clearml-yolo`` of the shared stands through the installed
k8s-infra skill, exactly as ``.agents/skills/clearml-yolo-environment/scripts/agent_env.sh``
does: ``infra.py room`` for capacity, ``clearml.py --project clearml-yolo env`` for the
credentials and CA trust, ``infra.py newtag`` for the run tag. Every object a run creates is
named by the tag, and ``stop`` removes exactly that tag's objects
(``clearml.py cleanup --prefix <tag>``) and proves it with an empty ``ls --prefix <tag>``.

The run tag, in order of precedence:

1. ``INFRA_RUN_TAG`` when exported (the run contract's variable; adopts an existing run);
2. ``tests/integration/.run-tag``, the gitignored file ``up`` writes when it mints a tag and
   ``stop`` deletes once cleanup is proven;
3. nothing: ``up`` mints one; ``stop`` refuses.

``up`` refuses to start while ``.run-tag`` names another run: stop it or adopt it first. An
exported ``INFRA_RUN_TAG`` adopts only the run ``.run-tag`` names; a different exported tag is
refused too, so one worktree never has two active runs.

``check`` is a read-only preflight bounded by ``CY_INFRA_CHECK_TIMEOUT`` seconds (60 by
default). It creates no tag and no stand object. Exit statuses: 0 available, 3 unavailable
(capacity WAIT, unreachable cluster or stand, timeout: live verification is deferred), 1 error
(missing skill, credentials, TLS trust or a refused identity: waiting would not help), 130
interrupted. ``up`` runs the same bounded check before it claims a tag.

The module stays standard-library only and never imports ``tests.env_isolation``. Inside
pytest that plugin replaces HOME and records the original values in ``CY_REAL_ENV``; this
module restores them for the skill lookup and for every child (kubectl and the k8s-infra
helpers need the real HOME, kubeconfig and caches).
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from contextlib import suppress
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from types import FrameType

PROJECT = "clearml-yolo"
TAG_SLUG = "integration"
MODULE = "uv run --frozen --no-sync python -m tests.integration.lifecycle"
TAG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
REAL_ENV_VARIABLE = "CY_REAL_ENV"
CHECK_TIMEOUT_VARIABLE = "CY_INFRA_CHECK_TIMEOUT"
DEFAULT_CHECK_TIMEOUT_SECONDS = 60.0
TASK_VERIFICATION_VARIABLE = "CY_TASK_VERIFICATION"
KEEP_DATA_VARIABLE = "INTEGRATION_KEEP_DATA"
REQUIRED_KEYS = ("CLEARML_API_HOST", "CLEARML_API_ACCESS_KEY", "CLEARML_API_SECRET_KEY")
OBJECT_ROWS = frozenset({"project", "task"})

EXIT_AVAILABLE = 0
EXIT_ERROR = 1
EXIT_UNAVAILABLE = 3
EXIT_INTERRUPTED = 130
ROOM_WAIT = 3

# curl exit statuses that mean the TLS handshake or certificate check failed: the stand
# answered, this machine does not trust it.
TLS_CURL_STATUSES = frozenset({35, 51, 53, 54, 58, 59, 60, 64, 66, 77, 80, 82, 83, 90, 91})
# curl exit statuses of an endpoint that is not there right now: host not resolved,
# connection refused, timeout, empty reply, connection reset.
DOWN_CURL_STATUSES = frozenset({6, 7, 28, 52, 56})
TLS_REMEDY = (
    "This is a certificate-trust problem, not a stand that is down: the stand serves",
    "https://<name>.k8s.docker.internal with a certificate from the k8s-infra CA.",
    "Check that the k8s-infra CA is installed (update-ca-certificates) and that",
    "clearml.py env exports SSL_CERT_FILE.",
)
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


def valid_tag(tag: str) -> bool:
    return bool(TAG_PATTERN.match(tag))


def tagged_project_name(tag: str, name: str = PROJECT) -> str:
    """ClearML project name whose first token is the run tag, so exact-tag cleanup reaches it."""
    return f"{tag} {name}"


def parse_exports(text: str, source: str) -> dict[str, str]:
    """Parse ``export KEY=<shell-quoted value>`` lines, as the helpers print them."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            words = shlex.split(line)
        except ValueError:
            words = []
        key, _, value = words[-1].partition("=") if words else ("", "", "")
        if len(words) != 2 or words[0] != "export" or not NAME_PATTERN.match(key):
            fail(f"{source} printed an unexpected line; refusing to guess its meaning.")
        values[key] = value
    return values


def find_skill_dir() -> Path | None:
    """Return the installed k8s-infra skill: K8S_INFRA_SKILL_DIR, else under the real HOME.

    An explicit ``K8S_INFRA_SKILL_DIR`` that does not hold the skill is an error rather than
    "not installed": somebody meant to point at it.
    """
    explicit = os.environ.get("K8S_INFRA_SKILL_DIR", "")
    if explicit:
        if not (Path(explicit) / "scripts" / "infra.py").is_file():
            fail(f"K8S_INFRA_SKILL_DIR={explicit} has no scripts/infra.py; point it at the k8s-infra skill.")
        return Path(explicit)
    home = Path(child_env().get("HOME", "~")).expanduser()
    for candidate in (home / ".agents" / "skills" / "k8s-infra", home / ".claude" / "skills" / "k8s-infra"):
        if (candidate / "scripts" / "infra.py").is_file():
            return candidate
    return None


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


def call(command: Sequence[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    """Run a child; if this process is interrupted, let the child finish first.

    Like a shell's foreground job, the child is waited for: Ctrl-C already reached it
    through the terminal's process group, SIGTERM is forwarded. A second Ctrl-C kills it.
    """
    try:
        child = subprocess.Popen(  # noqa: S603 - fixed tool commands
            list(command),
            text=True,
            stdout=subprocess.PIPE if capture else None,
            env=child_env(),
        )
    except FileNotFoundError:
        fail(f"{command[0]} is not installed or not on PATH; the live tests need it.")
    with child:
        try:
            stdout, _ = child.communicate()
        except BaseException as interrupt:
            if isinstance(interrupt, SystemExit) and child.poll() is None:
                child.send_signal(signal.SIGTERM)
            try:
                child.wait()
            except KeyboardInterrupt:
                child.kill()
                child.wait()
            raise
    return subprocess.CompletedProcess(list(command), child.returncode, stdout)


def is_temporary(detail: str) -> bool:
    """Whether lower-cased error text reports lost connectivity and no permanent problem."""
    if any(term in detail for term in PERMANENT_TERMS):
        return False
    return any(term in detail for term in TEMPORARY_TERMS)


def classify_failure(result: subprocess.CompletedProcess[str], description: str) -> NoReturn:
    """Separate temporary connectivity loss from permanent errors without echoing secrets."""
    detail = (result.stderr or "").lower()
    if is_temporary(detail):
        raise StandUnavailableError(f"{description}: service connectivity was lost")
    fail(f"{description} failed (exit {result.returncode}); check prerequisites, credentials, TLS and access.")


class Run:
    """One live run: its tag, its stand credentials and the steps on it."""

    def __init__(self, root: Path, *, deadline: float | None = None) -> None:
        """Resolve the skill, the run tag and the stand credentials; create nothing."""
        self.root = root
        self.deadline = deadline
        self.tag_file = root / "tests" / "integration" / ".run-tag"
        self.exported: dict[str, str] = {}
        skill_dir = find_skill_dir()
        if skill_dir is None:
            fail(
                "the k8s-infra skill was not found under ~/.agents/skills or ~/.claude/skills;",
                "install it or export K8S_INFRA_SKILL_DIR=<k8s-infra>/skills/k8s-infra.",
            )
        self.skill_dir = skill_dir
        self.tag = ""
        self._resolve_run_tag()
        self._stand_env()

    # -- environment ------------------------------------------------------

    def _export(self, **values: str) -> None:
        os.environ.update(values)
        self.exported.update(values)

    def _run(self, command: Sequence[str], *, capture: bool) -> subprocess.CompletedProcess[str]:
        if self.deadline is not None:
            return _probe_call(command, self.deadline)
        return call(command, capture=capture)

    def script(self, name: str) -> str:
        return str(self.skill_dir / "scripts" / name)

    def clearml(self, *args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
        """Run the k8s-infra ClearML helper as project clearml-yolo."""
        return self._run([sys.executable, self.script("clearml.py"), "--project", PROJECT, *args], capture=capture)

    def _stand_env(self) -> None:
        """Export the ClearML credentials and CA trust of project clearml-yolo.

        ``mongodb.py env`` is deliberately not exported: the FiftyOne suites never use the
        shared MongoDB stand, they require an explicit isolated ``FIFTYONE_DATABASE_DIR``.
        """
        completed = self.clearml("env", capture=True)
        if completed.returncode != 0:
            if self.deadline is not None:
                classify_failure(completed, "clearml credential lookup")
            fail(
                f"clearml.py --project {PROJECT} env failed (see above);",
                "the project Secret is missing, the cluster is unreachable or its TLS is not trusted.",
            )
        values = parse_exports(completed.stdout, "clearml.py env")
        missing = [key for key in REQUIRED_KEYS if not values.get(key)]
        if missing:
            fail(f"the {PROJECT} ClearML Secret carries no {', '.join(missing)}; redeploy the ClearML stand.")
        self._export(**values)

    # -- run tag ----------------------------------------------------------

    def _read_tag_file(self) -> str:
        try:
            lines = self.tag_file.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            lines = []
        tag = lines[0].strip() if lines else ""
        if not valid_tag(tag):
            fail(f"{self.tag_file} does not hold a run tag;", "remove it if the run it named is gone.")
        return tag

    def _set_tag(self, tag: str) -> None:
        self.tag = tag
        self._export(INTEGRATION_RUN_TAG=tag)

    def _resolve_run_tag(self) -> None:
        tag = os.environ.get("INFRA_RUN_TAG", "")
        if not tag and self.tag_file.is_file():
            tag = self._read_tag_file()
        if tag and not valid_tag(tag):
            fail(f"run tag '{tag}' is not lowercase [a-z0-9-]; mint it with infra.py newtag.")
        preset = os.environ.get("INTEGRATION_RUN_TAG", "")
        if preset and tag and preset != tag:
            fail(
                f"INTEGRATION_RUN_TAG={preset} is set in the shell but the run tag resolves to {tag};",
                "unset it, and export INFRA_RUN_TAG=<tag> to run under an explicit tag.",
            )
        self._set_tag(tag)

    def adopted(self) -> bool:
        """Whether the tag was exported rather than minted by this worktree."""
        return bool(os.environ.get("INFRA_RUN_TAG"))

    def require_tag(self) -> None:
        if not self.tag:
            fail(
                f"no run is active: run {MODULE} up first,",
                "or export INFRA_RUN_TAG=<tag> to act on a run started elsewhere.",
            )

    def refuse_active_run(self) -> None:
        """Refuse to start while the tag file names a run other than an adopted one.

        Only an exported tag equal to the recorded one adopts that run; a minted or a different
        exported tag would start a second run in this worktree.
        """
        if not self.tag_file.is_file():
            return
        try:
            active = self._read_tag_file()
        except LifecycleError as error:
            raise LifecycleError(
                f"{self.tag_file} is in this worktree but does not hold a readable run tag;",
                "remove it if the run it named is gone, then start again.",
            ) from error
        if self.adopted() and active == self.tag:
            return
        fail(
            f"run '{active}' is active in this worktree ({self.tag_file});",
            f"stop it with INFRA_RUN_TAG={active} {MODULE} stop, or export INFRA_RUN_TAG={active} to adopt it.",
        )

    def claim_run_tag(self) -> None:
        """Mint when needed; assign, then record, so a refusal leaves nothing behind."""
        self.refuse_active_run()
        if self.adopted():
            return
        minted = call(
            [sys.executable, self.script("infra.py"), "newtag", "--project", PROJECT, "--slug", TAG_SLUG],
            capture=True,
        )
        tag = (minted.stdout or "").strip()
        if minted.returncode != 0 or not valid_tag(tag):
            fail(f"infra.py newtag --project {PROJECT} --slug {TAG_SLUG} did not mint a tag (see above).")
        self.tag_file.write_text(f"{tag}\n", encoding="utf-8")
        self._set_tag(tag)

    def release_run_tag(self) -> None:
        """Forget the tag, but only when the file names this run."""
        if not self.tag_file.is_file():
            return
        try:
            recorded = self._read_tag_file()
        except LifecycleError:
            recorded = ""
        if recorded in {self.tag, ""}:
            self.tag_file.unlink(missing_ok=True)

    # -- steps ------------------------------------------------------------

    def remove_tagged_objects(self) -> bool:
        """Delete this tag's ClearML objects, then prove that none remain."""
        host = self.exported.get("CLEARML_API_HOST", "?")
        log(f"Removing ClearML objects of run tag '{self.tag}' at {host}")
        removed = self.clearml("cleanup", "--prefix", self.tag).returncode == 0
        listing = self.clearml("ls", "--prefix", self.tag, capture=True)
        rows = [line for line in (listing.stdout or "").splitlines() if line.split()[:1] in (["project"], ["task"])]
        if not removed:
            warn(f"WARNING: clearml.py cleanup --prefix {self.tag} failed.")
        if listing.returncode != 0 or rows:
            warn(f"WARNING: exact-tag cleanup proof failed for '{self.tag}': {len(rows)} object row(s) remain.")
            return False
        if removed:
            log(f"clearml: no objects remain for exact tag '{self.tag}'")
        return removed

    def up(self) -> None:
        """Claim the tag; an adopted tag may own leftovers, so clear them first."""
        self.claim_run_tag()
        log(f"Run tag '{self.tag}' on ClearML at {os.environ['CLEARML_API_HOST']} (project {PROJECT})")
        if self.adopted() and not self.remove_tagged_objects():
            fail(f"leftovers of adopted run '{self.tag}' could not be removed (see above).")

    def stop(self) -> int:
        """Remove this tag's objects; keep the tag file unless cleanup is proven."""
        self.require_tag()
        if not self.remove_tagged_objects():
            warn(f"ERROR: run '{self.tag}' is not fully torn down; the run tag stays for the retry:")
            warn(f"       INFRA_RUN_TAG={self.tag} {MODULE} stop")
            return EXIT_ERROR
        self.release_run_tag()
        log("Done")
        return EXIT_AVAILABLE


# -- stand availability ----------------------------------------------------


def _curl(url: str, deadline: float) -> str | None:
    """None when the endpoint answers; a reason when it is down; else fail.

    Down means no connection or HTTP 5xx/429. A TLS failure or another HTTP error is a
    problem waiting cannot fix.
    """
    result = _probe_call(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "10", url],
        deadline,
    )
    status = result.returncode
    if status in TLS_CURL_STATUSES:
        fail(f"TLS verification of the ClearML stand at {url} failed (curl exit {status}).", *TLS_REMEDY)
    if status in DOWN_CURL_STATUSES:
        return f"the ClearML stand at {url} does not answer (curl exit {status})"
    if status != 0:
        fail(f"curl could not check the ClearML stand at {url} (exit {status}).")
    try:
        code = int(result.stdout.strip() or "0")
    except ValueError:
        fail("curl returned an invalid HTTP status for the ClearML stand")
    if code >= HTTPStatus.INTERNAL_SERVER_ERROR or code == HTTPStatus.TOO_MANY_REQUESTS:
        return f"the ClearML stand at {url} answers HTTP {code}"
    if code >= HTTPStatus.BAD_REQUEST or code == 0:
        fail(f"the ClearML stand at {url} answers HTTP {code}; that is not a stopped stand.")
    return None


def _cluster_available(deadline: float) -> str | None:
    """Separate Kubernetes access errors from temporary connectivity failures."""
    result = _probe_call(["kubectl", "--context", "docker-desktop", "get", "--raw=/readyz"], deadline)
    if result.returncode == 0:
        return None
    detail = (result.stderr or "").lower()
    if any(term in detail for term in PERMANENT_TERMS):
        fail("Kubernetes access, context, credentials or TLS configuration failed; check kubectl access.")
    if is_temporary(detail):
        return "the docker-desktop cluster does not answer"
    fail(f"Kubernetes readiness probe failed unexpectedly (exit {result.returncode}); check kubectl access.")


def probe(root: Path, deadline: float) -> Run | str:
    """Return a ready run, or the reason the stand is temporarily unavailable.

    Everything else - a missing tool, skill or Secret, an untrusted certificate, a failing
    room check, another HTTP error, a refused identity - raises LifecycleError.
    """
    if find_skill_dir() is not None:
        reason = _cluster_available(deadline)
        if reason is not None:
            return reason
    run = Run(root, deadline=deadline)
    room = _probe_call([sys.executable, run.script("infra.py"), "room"], deadline)
    if room.returncode == ROOM_WAIT:
        return "infra.py room answers WAIT: the stands are at capacity"
    if room.returncode != 0:
        fail(f"infra.py room failed (exit {room.returncode}); run it by hand to see why.")
    reason = _curl(f"{os.environ['CLEARML_API_HOST'].rstrip('/')}/debug.ping", deadline)
    if reason is not None:
        return reason
    identity = run.clearml("whoami", capture=True)
    if identity.returncode != 0:
        classify_failure(identity, "clearml identity probe")
    run.deadline = None
    return run


def check_timeout() -> float:
    raw = os.environ.get(CHECK_TIMEOUT_VARIABLE, str(DEFAULT_CHECK_TIMEOUT_SECONDS))
    try:
        timeout = float(raw)
    except ValueError:
        fail(f"{CHECK_TIMEOUT_VARIABLE} must be a positive finite number of seconds")
    if not math.isfinite(timeout) or timeout <= 0:
        fail(f"{CHECK_TIMEOUT_VARIABLE} must be a positive finite number of seconds")
    return timeout


def check_stands(root: Path) -> Run:
    """One read-only preflight with one overall deadline and no polling."""
    result = probe(root, time.monotonic() + check_timeout())
    if isinstance(result, str):
        raise StandUnavailableError(result)
    return result


def prepare(root: Path) -> Run:
    """Check the stand, refuse a foreign active run, then claim the tag.

    A setup failure after the tag is claimed stops the run, so nothing is left behind.
    """
    run = check_stands(root)
    run.refuse_active_run()
    try:
        run.up()
    except BaseException:
        if run.tag:
            try:
                finish(run)
            except LifecycleError as error:
                report(error)
        raise
    return run


def finish(run: Run) -> int:
    """Stop the run unless INTEGRATION_KEEP_DATA=1 keeps it for inspection."""
    if os.environ.get(KEEP_DATA_VARIABLE, "") != "1":
        return run.stop()
    log(f"keeping run '{run.tag}' for inspection ({KEEP_DATA_VARIABLE}=1)")
    log(f"    remove everything with INFRA_RUN_TAG={run.tag} {MODULE} stop")
    return EXIT_AVAILABLE


# -- command line ----------------------------------------------------------


def _terminate(signum: int, _frame: FrameType | None) -> NoReturn:
    """Turn SIGTERM into an exit so an interrupted child is waited for."""
    raise SystemExit(128 + signum)


def _print_env(run: Run) -> None:
    if sys.stdout.isatty():
        fail(
            "env prints the run's credentials; evaluate it instead of reading it:",
            f'eval "$({MODULE} env)"',
        )
    for key, value in run.exported.items():
        sys.stdout.write(f"export {key}={shlex.quote(value)}\n")


def _dispatch(command: str, root: Path) -> int:
    if command == "check":
        check_stands(root)
        log("AVAILABLE: infrastructure preflight passed; no resources created")
        return EXIT_AVAILABLE
    if command == "up":
        run = prepare(root)
        log(f"Run live tests: INFRA_RUN_TAG={run.tag} uv run --frozen --no-sync pytest tests/integration")
        log(f"Tear down:      {MODULE} stop")
        return EXIT_AVAILABLE
    run = Run(root)
    if command == "env":
        _print_env(run)
        return EXIT_AVAILABLE
    return run.stop()


def main(argv: Sequence[str] | None = None, *, on_signal: Callable[..., object] = signal.signal) -> int:
    parser = argparse.ArgumentParser(prog=MODULE, description="Live-run lifecycle on the shared ClearML stand.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help=argparse.SUPPRESS,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="read-only bounded preflight (0 available, 3 unavailable, 1 error)")
    commands.add_parser("env", help="print this run's variables as shell exports")
    commands.add_parser("up", help="check the stand and claim a run tag")
    commands.add_parser("stop", help="remove the run's tagged objects and release its tag")
    args = parser.parse_args(argv)

    if isinstance(sys.stdout, io.TextIOWrapper):
        # Our lines must interleave with the children's in captured output.
        sys.stdout.reconfigure(line_buffering=True)
    on_signal(signal.SIGTERM, _terminate)
    root: Path = args.repo_root.resolve()
    try:
        return _dispatch(args.command, root)
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
