"""Opt-in physical DDP acceptance orchestration; imports cause no device/service effects."""

import hashlib
import json
import math
import os
import re
import signal
import subprocess
import sys
import time
import traceback
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4
from xml.etree.ElementTree import Element, SubElement, tostring

_HELPER = Path(__file__).with_name("ddp_gpu_worker.py")
_TERMINAL = {"completed", "failed", "cancelled", "recovery_required"}
_FALLBACK_CLEANUP_TIMEOUT_SECONDS = 15.0
_SECRET_KEY = re.compile(
    r"(?i)(secret(?:[_ -]?key)?|access[_ -]?key(?:[_ -]?id)?|"
    r"api[_ -]?key|token|password|authorization)"
)


def _redact_url(match: re.Match[str]) -> str:
    try:
        url = urlsplit(match.group())
    except ValueError:
        # Malformed endpoints are failure evidence too; never hide the original error.
        return "<redacted-invalid-url>"
    query = [
        (
            key,
            "<redacted>"
            if re.search(r"(?i)(sig|token|key|secret|credential|auth|password)", key)
            else value,
        )
        for key, value in parse_qsl(url.query, keep_blank_values=True)
    ]
    host = url.netloc.rsplit("@", 1)[-1]
    return urlunsplit((url.scheme, host, url.path, urlencode(query), url.fragment))


def physical_indexes(value: str) -> tuple[int, ...]:
    """Selectors mean NVML physical indexes, never inherited CUDA logical indexes."""
    try:
        indexes = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as error:
        raise ValueError(
            "--ddp-devices requires comma-separated physical integer indexes"
        ) from error
    if len(indexes) < 2 or len(set(indexes)) != len(indexes) or min(indexes) < 0:
        raise ValueError("--ddp-devices requires at least two unique nonnegative physical indexes")
    return indexes


def resolve_devices(indexes: tuple[int, ...], inventory: list[dict[str, Any]]) -> tuple[str, ...]:
    cards = {int(card["index"]): str(card["uuid"]) for card in inventory}
    if any(index not in cards for index in indexes):
        raise RuntimeError("Selected physical GPU index does not exist in NVML inventory")
    uuids = tuple(cards[index] for index in indexes)
    if any(not value.startswith("GPU-") for value in uuids) or len(set(uuids)) != len(uuids):
        raise RuntimeError(
            "Physical selection requires distinct whole-GPU UUIDs; MIG is unsupported"
        )
    return uuids


def redact(value: str) -> str:
    value = re.sub(r"https?://[^\s<>\"']+", _redact_url, value)
    value = re.sub(
        r"(?i)(authorization[\"']?\s*[:=]\s*[\"']?(?:bearer|basic)\s+)[^\s\"',}]+",
        r"\1<redacted>",
        value,
    )
    return re.sub(
        r"(?i)((?:secret(?:[_ -]?key)?|access[_ -]?key(?:[_ -]?id)?|"
        r"api[_ -]?key|token|password)[\"']?\s*[:=]\s*)[^\s,}\n]+",
        r"\1<redacted>",
        value,
    )


def redact_data(value: Any) -> Any:
    """Redact structured evidence without damaging JSON strings or delimiters."""
    if isinstance(value, dict):
        return {
            key: "<redacted>" if _SECRET_KEY.fullmatch(str(key)) else redact_data(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_data(item) for item in value)
    return redact(value) if isinstance(value, str) else value


def _redact_file(path: Path) -> None:
    contents = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".json":
        try:
            contents = json.dumps(redact_data(json.loads(contents)), indent=2)
        except json.JSONDecodeError:
            contents = redact(contents)
    elif path.suffix == ".jsonl":
        records = []
        for line in contents.splitlines():
            try:
                records.append(json.dumps(redact_data(json.loads(line))))
            except json.JSONDecodeError:
                records.append(redact(line))
        contents = "\n".join(records) + "\n"
    else:
        contents = redact(contents)
    path.write_text(contents, encoding="utf-8")


@dataclass(frozen=True)
class GPUOptions:
    devices: str
    project: str
    artifacts: Path
    timeout: float = 1200
    cleanup_timeout: float = 150


class Evidence:
    """Retain a failure receipt even when selection or preflight never succeeds."""

    def __init__(self, options: GPUOptions, scenario: str) -> None:
        self.options = options
        self.root = options.artifacts.resolve() / f"{scenario}-{uuid4().hex[:10]}"
        self.root.mkdir(parents=True, exist_ok=False)
        self.data: dict[str, Any] = {
            "scenario": scenario,
            "status": "running",
            "started_at": time.time(),
            "physical_selection": options.devices,
            "clearml_project": options.project,
            "commands": [],
            "limitations": ["Synthetic random initialization establishes execution, not accuracy."],
        }
        self.start = time.monotonic()

    def finish(self, error: BaseException | None) -> None:
        self.data.update(
            status="failed" if error else "passed",
            elapsed_seconds=time.monotonic() - self.start,
            error=redact("".join(traceback.format_exception(error))) if error else None,
        )
        for path in self.root.rglob("*"):
            if path.is_file() and path.suffix in {".log", ".json", ".jsonl", ".yaml"}:
                _redact_file(path)
        self.data = redact_data(self.data)
        (self.root / "summary.json").write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        suite = Element(
            "testsuite", name="physical_ddp", tests="1", failures=str(int(error is not None))
        )
        case = SubElement(
            suite, "testcase", name=self.data["scenario"], time=str(self.data["elapsed_seconds"])
        )
        if error:
            SubElement(case, "failure", message=redact(str(error))).text = self.data["error"]
        (self.root / "junit.xml").write_bytes(
            tostring(suite, encoding="utf-8", xml_declaration=True)
        )

    @contextmanager
    def retained(self) -> Iterator["Evidence"]:
        try:
            yield self
        except BaseException as error:
            self.finish(error)
            raise
        else:
            self.finish(None)

    def command(
        self,
        argv: list[str],
        environment: dict[str, str],
        *,
        timeout: float = 60,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        self.data["commands"].append(argv)
        index = len(self.data["commands"])
        try:
            result = subprocess.run(  # noqa: S603 - explicit local acceptance commands
                argv,
                cwd=self.root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            captured = [
                output.decode(errors="replace") for output in (error.stdout, error.stderr) if output
            ]
            (self.root / f"command-{index}.log").write_text(
                redact("\n".join(captured)), encoding="utf-8"
            )
            self.data.setdefault("command_timeouts", []).append(
                {"command": index, "timeout": timeout}
            )
            raise
        (self.root / f"command-{index}.log").write_text(
            redact(result.stdout + result.stderr), encoding="utf-8"
        )
        if check and result.returncode:
            raise RuntimeError(
                f"Command exited {result.returncode}: {argv}; see command-{index}.log"
            )
        return result

    def helper(self, operation: str, environment: dict[str, str], *, timeout: float = 60) -> None:
        self.command(
            [sys.executable, str(_HELPER), operation, str(self.root)], environment, timeout=timeout
        )


def environment_for(evidence: Evidence, *, instrument: bool = False) -> dict[str, str]:
    environment = dict(os.environ)
    # Stable fresh interpreter paths: the installed editable source and these test helpers.
    repository = Path(__file__).resolve().parents[1]
    paths = [str(repository / "src"), str(Path(__file__).parent)]
    if instrument:
        paths.insert(0, str(evidence.root / "instrumentation"))
        environment["CY_DDP_TRACE"] = str(evidence.root)
    else:
        environment.pop("CY_DDP_TRACE", None)
    paths.append(environment.get("PYTHONPATH", ""))
    environment.update(
        CY_HOME=str(evidence.root),
        PYTHONPATH=os.pathsep.join(paths),
        PYTHONUNBUFFERED="1",
        YOLO_CONFIG_DIR=str(evidence.root / "native-config"),
    )
    return environment


def _queue_command(root: Path, *arguments: str) -> list[str]:
    return [
        sys.executable,
        "-m",
        "clearml_yolo.entrypoints.queue",
        "--root",
        str(root / "queue"),
        *arguments,
    ]


def _wait(check: Callable[[], Any], deadline: float, description: str) -> Any:
    while time.monotonic() < deadline:
        value = check()
        if value:
            return value
        time.sleep(0.2)
    raise TimeoutError(f"Timed out waiting for {description}")


def _stop_owned(process: subprocess.Popen[Any], deadline: float) -> None:
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def _job(evidence: Evidence, environment: dict[str, str], identifier: str) -> dict[str, Any]:
    result = evidence.command(
        _queue_command(evidence.root, "list", "--json"), environment, timeout=30
    )
    view = json.loads(result.stdout)
    job = next(job for job in view["jobs"] if job["id"] == identifier)
    transitions = evidence.data.setdefault("queue_transitions", [])
    if not transitions or transitions[-1]["state"] != job["state"]:
        transitions.append({"observed_at": time.time(), **job})
    return cast(dict[str, Any], job)


def _claim(
    evidence: Evidence, environment: dict[str, str], identifier: str
) -> dict[str, Any] | None:
    (evidence.root / "job-id").write_text(identifier, encoding="utf-8")
    evidence.helper("claim", environment)
    return cast(
        dict[str, Any] | None, json.loads((evidence.root / "claim-readback.json").read_text())
    )


def _assert_allocation(evidence: Evidence, environment: dict[str, str], identifier: str) -> None:
    claim = _claim(evidence, environment, identifier)
    if claim is None or tuple(claim["devices"]) != tuple(evidence.data["uuids"]):
        raise AssertionError(
            "Whole physical allocation was not retained through the pipeline stage"
        )
    evidence.data.setdefault("allocation_readbacks", []).append(claim)


def _prepare_scenario(evidence: Evidence, *, compiled: bool) -> dict[str, str]:
    options = evidence.options
    indexes = physical_indexes(options.devices)
    if not options.project.strip():
        raise ValueError("--ddp-clearml-project is required")
    if (
        not math.isfinite(options.timeout)
        or options.timeout <= 0
        or not math.isfinite(options.cleanup_timeout)
        or options.cleanup_timeout < 120
    ):
        raise ValueError(
            "Execution timeout must be positive; cleanup timeout must be at least 120s"
        )
    base = environment_for(evidence)
    (evidence.root / "request.json").write_text(
        json.dumps(
            {
                "indexes": indexes,
                "project": options.project,
                "compiled": compiled,
                "scenario": evidence.data["scenario"],
                "tag": f"ddp-gpu-{uuid4().hex}",
                "timeout": options.timeout,
            }
        ),
        encoding="utf-8",
    )
    evidence.helper("preflight", base, timeout=90)
    preflight = json.loads((evidence.root / "preflight.json").read_text())
    evidence.data["preflight"] = preflight
    uuids = resolve_devices(indexes, preflight["inventory"])
    evidence.data["uuids"] = uuids
    base["CUDA_VISIBLE_DEVICES"] = ",".join(uuids)
    evidence.helper("cuda", base, timeout=90)
    evidence.helper("prepare", base)
    return base


def _launch_arguments(
    evidence: Evidence, base: dict[str, str], *, queued: bool
) -> tuple[list[str], str | None]:
    overrides = ["--config-dir", str(evidence.root / "config"), "--config-name", "ddp"]
    devices = ",".join(str(i) for i in range(len(evidence.data["uuids"])))
    if not queued:
        overrides += [f"ultralytics.device=[{devices}]", "ultralytics_predict.device=0"]
        return [sys.executable, "-m", "clearml_yolo.entrypoints.pipeline", *overrides], None
    submitted = evidence.command(
        _queue_command(evidence.root, "submit", "--devices", devices, "--", *overrides), base
    )
    identifiers = submitted.stdout.strip().splitlines()
    if len(identifiers) != 1:
        raise AssertionError(f"Expected one queued job, received {identifiers}")
    identifier = identifiers[0]
    evidence.data["job_id"] = identifier
    if _job(evidence, base, identifier)["state"] != "pending":
        raise AssertionError("Submission did not create a pending immutable job")
    return _queue_command(evidence.root, "worker"), identifier


def _cleanup_queue(
    evidence: Evidence, base: dict[str, str], identifier: str, deadline: float
) -> None:
    state = _job(evidence, base, identifier)["state"]
    if state not in _TERMINAL:
        evidence.command(_queue_command(evidence.root, "cancel", identifier), base)
        _wait(
            lambda: _job(evidence, base, identifier)["state"] in _TERMINAL,
            deadline,
            "queue cancellation cleanup",
        )
    if _job(evidence, base, identifier)["state"] == "recovery_required":
        evidence.command(
            _queue_command(evidence.root, "recover", identifier),
            base,
            timeout=max(1, deadline - time.monotonic()),
        )
    if _claim(evidence, base, identifier) is not None:
        raise AssertionError("Owned allocation remains claimed after cleanup")


def _cleanup_scenario(
    evidence: Evidence,
    base: dict[str, str],
    owner: subprocess.Popen[Any] | None,
    identifier: str | None,
) -> None:
    deadline = time.monotonic() + evidence.options.cleanup_timeout
    errors: list[str] = []
    if identifier:
        try:
            _cleanup_queue(evidence, base, identifier, deadline)
        except Exception as error:  # noqa: BLE001 - retain diagnostics and always attempt cleanup
            # Report every queue failure while still running owned-process cleanup.
            errors.append(str(error))
    if owner is not None:
        try:
            _stop_owned(owner, deadline)
        except (OSError, subprocess.TimeoutExpired) as error:
            errors.append(str(error))
    try:
        # Queue recovery may use its entire budget. Fallback still needs TERM/KILL grace.
        evidence.helper("cleanup", base, timeout=_FALLBACK_CLEANUP_TIMEOUT_SECONDS)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        errors.append(str(error))
    evidence.data["cleanup_errors"] = errors
    if errors and sys.exc_info()[0] is None:
        raise AssertionError(f"Physical DDP cleanup failed: {errors}")


def run_scenario(options: GPUOptions, scenario: str, *, queued: bool, compiled: bool) -> Path:
    evidence = Evidence(options, scenario)
    with evidence.retained():
        base = _prepare_scenario(evidence, compiled=compiled)
        environment = environment_for(evidence, instrument=True)
        environment["CUDA_VISIBLE_DEVICES"] = base["CUDA_VISIBLE_DEVICES"]
        evidence.data["environment"] = {
            key: environment[key]
            for key in (
                "CY_HOME",
                "CUDA_VISIBLE_DEVICES",
                "PYTHONPATH",
                "CY_DDP_TRACE",
                "YOLO_CONFIG_DIR",
            )
        }
        owner: subprocess.Popen[Any] | None = None
        identifier: str | None = None
        deadline = time.monotonic() + options.timeout
        try:
            argv, identifier = _launch_arguments(evidence, base, queued=queued)
            evidence.data["commands"].append(argv)
            with (evidence.root / "owner.log").open("w", encoding="utf-8") as log:
                owner = subprocess.Popen(  # noqa: S603 - fresh real production entrypoint
                    argv,
                    cwd=evidence.root,
                    env=environment,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
                if queued and identifier:
                    _run_queued(evidence, base, identifier, scenario, deadline)
                else:
                    owner.wait(timeout=max(0.1, deadline - time.monotonic()))
                    if owner.returncode != 0:
                        raise AssertionError(
                            f"Direct native pipeline exited {owner.returncode}; see owner.log"
                        )
            evidence.helper("verify", base, timeout=max(0.1, min(180, deadline - time.monotonic())))
            evidence.data["verification"] = json.loads(
                (evidence.root / "verification.json").read_text()
            )
        finally:
            _cleanup_scenario(evidence, base, owner, identifier)
    return evidence.root


def _run_queued(
    evidence: Evidence, environment: dict[str, str], identifier: str, scenario: str, deadline: float
) -> None:
    fault = scenario in {"queued-rank-exit", "queued-cancel", "queued-guardian-death"}
    _wait(
        lambda: _job(evidence, environment, identifier)["state"] == "running",
        deadline,
        "queue launch",
    )
    _assert_allocation(evidence, environment, identifier)
    _wait(
        lambda: len(list(evidence.root.glob("rank-*-started.json"))) == len(evidence.data["uuids"]),
        deadline,
        "all physical CUDA ranks",
    )
    if fault:
        _assert_allocation(evidence, environment, identifier)
        if scenario == "queued-cancel":
            evidence.command(_queue_command(evidence.root, "cancel", identifier), environment)
            evidence.command(_queue_command(evidence.root, "cancel", identifier), environment)
        elif scenario == "queued-guardian-death":
            evidence.helper("kill-guardian", environment)
            _wait(
                lambda: _job(evidence, environment, identifier)["state"] == "recovery_required",
                deadline,
                "guardian death quarantine",
            )
            _assert_allocation(evidence, environment, identifier)
            evidence.command(
                _queue_command(evidence.root, "recover", identifier), environment, timeout=120
            )
        else:
            (evidence.root / "release-training").touch()
    else:
        (evidence.root / "release-training").touch()
        prediction_started = evidence.root / "pipeline-predict-started.json"
        _wait(prediction_started.exists, deadline, "post-training prediction/validation")
        _assert_allocation(evidence, environment, identifier)
        (evidence.root / "release-predict").touch()

    def terminal_job() -> dict[str, Any] | None:
        job = _job(evidence, environment, identifier)
        return job if job["state"] in _TERMINAL else None

    final = _wait(
        terminal_job,
        deadline,
        "queue finalization",
    )
    expected = "failed" if scenario == "queued-rank-exit" else "cancelled" if fault else "completed"
    if final["state"] != expected:
        raise AssertionError(
            f"Expected {expected}, observed {final['state']}: {final.get('error')}"
        )
    if _claim(evidence, environment, identifier) is not None:
        raise AssertionError("Terminal queue job retained an owned whole-GPU claim")


def checkpoint_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
