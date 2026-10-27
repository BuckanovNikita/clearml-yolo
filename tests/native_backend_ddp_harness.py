"""Opt-in native backend acceptance; ordinary imports have no GPU/service effects."""

import json
import math
import signal
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from ddp_gpu_harness import (
    Evidence,
    GPUOptions,
    _cleanup_scenario,
    environment_for,
    physical_indexes,
    resolve_devices,
)

SELECTIONS = ("deimv2/s", "rfdetr/nano", "fasterrcnn/resnet50_fpn", "fcos/resnet50_fpn")
Fault = Literal["none", "crash", "oom", "cancel"]
_WORKER = Path(__file__).with_name("native_backend_ddp_worker.py")


def request_document(options: GPUOptions, selection: str, fault: Fault) -> dict[str, Any]:
    if selection not in SELECTIONS or fault not in {"none", "crash", "oom", "cancel"}:
        raise ValueError("Unsupported native acceptance selection or fault")
    indexes = physical_indexes(options.devices)
    if not options.project.strip() or not math.isfinite(options.timeout) or options.timeout <= 0:
        raise ValueError("Native acceptance requires a project and positive finite deadline")
    if not math.isfinite(options.cleanup_timeout) or options.cleanup_timeout < 120:
        raise ValueError("Native acceptance cleanup deadline must be at least 120 seconds")
    count = len(indexes)
    accumulation = 1 if selection.startswith("deimv2/") else 2
    # RF-DETR 1.11.2 repeats smaller datasets until five full optimizer batches
    # per rank are available. Supply those unique images to preserve exact sharding.
    microbatches = accumulation * 5 if selection.startswith("rfdetr/") else 4
    return {
        "selection": selection,
        "fault": fault,
        "indexes": list(indexes),
        "world_size": count,
        "global_batch": count * 2,
        "accumulation": accumulation,
        "train_count": count * 2 * microbatches,
        "val_count": count * 2 + 1,
        "test_count": 3,
        "project": options.project,
        "tag": f"native-ddp-{uuid4().hex}",
        "scenario": f"{selection.replace('/', '-')}-{fault}",
        "compiled": False,
        "timeout": options.timeout,
    }


def pipeline_arguments(root: Path, request: dict[str, Any]) -> list[str]:
    devices = list(range(request["world_size"]))
    return [
        sys.executable,
        "-m",
        "clearml_yolo.entrypoints.pipeline",
        f"model={request['selection']}",
        f"ground_truth={json.dumps(str(root / 'ground_truth.csv'))}",
        f"run_dir={json.dumps(str(root / 'pipeline'))}",
        f"clearml.project_name={json.dumps(request['project'])}",
        f"clearml.task_name={json.dumps(request['scenario'])}",
        f"clearml.tags={json.dumps([request['tag']])}",
        "fiftyone.enabled=false",
        "skip_compare=true",
        "skip_report=true",
        "splits=[val,test]",
        "model.train.epochs=1",
        "model.train.imgsz=128",
        f"model.train.batch={request['global_batch']}",
        f"model.train.grad_accum_steps={request['accumulation']}",
        f"model.train.device={json.dumps(devices)}",
        "model.train.workers=0",
        "model.train.pretrained=false",
        "model.train.amp=false",
        "model.train.use_ema=true",
        "model.predict.device=0",
        "model.predict.imgsz=128",
    ]


def instrument_command(command: Any) -> Any:
    """Change only the private rank executable, retaining production supervision."""
    argv = command.argv
    if len(argv) != 5 or argv[1:3] != (
        "-m",
        "clearml_yolo.adapters.integrations.training_worker",
    ):
        raise ValueError("Acceptance observer received an unexpected worker command")
    return replace(command, argv=(argv[0], str(_WORKER), "rank", argv[3], argv[4]))


def validate_ready(request: dict[str, Any], ranks: list[dict[str, Any]]) -> None:
    world = request["world_size"]
    assert len(ranks) == world, "Missing native rank evidence"
    assert {item["rank"] for item in ranks} == set(range(world)), "Wrong native rank identities"
    for item in ranks:
        rank = item["rank"]
        assert item["selection"] == request["selection"], "Wrong native model selection"
        assert item["world_size"] == world, "Wrong NCCL world"
        assert item["backend"] == "nccl", "Wrong NCCL backend"
        assert item["local_rank"] == rank, "Wrong local rank"
        actual_uuid = item["uuid"].removeprefix("GPU-").lower()
        expected_uuid = request["uuids"][rank].removeprefix("GPU-").lower()
        assert actual_uuid == expected_uuid, "Wrong CUDA device mapping"
        assert item["global_batch"] == request["global_batch"], "Wrong global batch"
        assert item["per_rank_batch"] * world == request["global_batch"], "Wrong rank batch"
        assert item["accumulation"] == request["accumulation"], "Wrong accumulation"


def validate_ranks(request: dict[str, Any], ranks: list[dict[str, Any]]) -> None:
    validate_ready(request, ranks)
    world = request["world_size"]
    microbatches, partial_batch = divmod(request["train_count"], request["global_batch"])
    updates, partial_accumulation = divmod(microbatches, request["accumulation"])
    assert not partial_batch, "Fixture does not contain complete global batches"
    assert not partial_accumulation, "Fixture does not contain complete optimizer batches"
    assert updates > 0, "Fixture contains no optimizer updates"
    for item in ranks:
        rank = item["rank"]
        assert item["optimizer_steps"] == updates, "Wrong actual updates"
        assert item["initial_parameters"] != item["parameters"], "Parameters did not train"
        assert item["finite"], "Nonfinite native state"
        assert item["ema_updates"] > 0, "EMA never updated"
        assert item["checkpoints"] if rank == 0 else not item["checkpoints"], (
            "Checkpoint ownership differs from rank zero"
        )
        assert len(item["expected_train_ids"]) == request["train_count"], "Wrong train population"
        assert len(item["expected_val_ids"]) == request["val_count"], "Wrong validation population"
        assert len(item["train_batches"]) == microbatches, "Missing training microbatches"
        assert all(value == request["global_batch"] // world for value in item["train_batches"]), (
            "Actual training microbatch differs from allocation"
        )
    if request["selection"].startswith("fcos/"):
        labels = [label for item in ranks for label in item["train_labels"]]
        assert set(labels) == {0}, "FCOS class zero was lost or shifted"
    for field in ("initial_parameters", "parameters", "model", "ema", "optimizer"):
        assert all(item[field] for item in ranks), f"Missing {field} evidence"
        assert len({item[field] for item in ranks}) == 1, f"Divergent {field} across ranks"
    for phase, expected_key in (
        ("train", "expected_train_ids"),
        ("validation", "expected_val_ids"),
    ):
        expected = ranks[0][expected_key]
        assert all(item[expected_key] == expected for item in ranks), "Different rank datasets"
        observed = [identity for item in ranks for identity in item[f"{phase}_ids"]]
        assert len(set(expected)) == len(expected), "Duplicate expected image identities"
        assert sorted(observed) == sorted(expected), f"Missing or duplicate {phase} samples"


def validate_publication(
    request: dict[str, Any], events: list[dict[str, Any]], publication: dict[str, Any]
) -> None:
    creations = [event for event in events if event["kind"] == "task-init"]
    assert len(creations) == 1, "Expected one ClearML invocation owner"
    owner = creations[0]
    for event in events:
        if event["kind"].endswith("-attempt"):
            assert event["rank"] == -1, "Worker publication"
            assert event["pid"] == owner["pid"], "Worker publication"
    assert publication["task_ids"] == [owner["task_id"]], "Unexpected ClearML tasks"
    assert publication["status"] == "completed", "Native owner task did not complete"
    assert publication["output_models"] == 1, "Expected one selected Output Model"
    assert publication["download_sha256"] == publication["native_sha256"], (
        "Checkpoint hash mismatch"
    )
    assert publication["download_sha256"], "Missing checkpoint hash"
    assert publication["selection"] == request["selection"], "Wrong downloaded checkpoint family"
    assert publication["reload_images"] == request["test_count"], "Checkpoint reload lost images"
    assert publication["unwrapped"], "Checkpoint retained distributed wrapper prefixes"


def validate_failure(request: dict[str, Any], events: list[dict[str, Any]], exit_code: int) -> None:
    assert exit_code != 0, "Faulted native pipeline unexpectedly succeeded"
    expected = f"fault-{request['fault']}"
    observed = [event for event in events if event["kind"] == expected]
    assert len(observed) == 1, "Requested native fault was not observed"
    event = observed[0]
    if request["fault"] == "oom":
        assert event["confirmed_cuda_oom"] is True, "OOM was not an actual CUDA allocation failure"
    assert event["rank"] == (-1 if request["fault"] == "cancel" else 1), "Wrong fault owner"
    if request["fault"] == "crash":
        assert event["exit_code"] == 73, "Wrong injected crash code"
    if request["fault"] == "cancel":
        assert event["signal"] == "SIGINT", "Wrong cancellation signal"
        owners = [item["pid"] for item in events if item["kind"] == "task-init"]
        assert owners == [event["target_pid"]], "Cancellation missed invocation owner"


def _helper(evidence: Evidence, action: str, environment: dict[str, str], timeout: float) -> None:
    evidence.command(
        [sys.executable, str(_WORKER), action, str(evidence.root)], environment, timeout=timeout
    )


def _wait_ready(evidence: Evidence, owner: subprocess.Popen[Any], deadline: float) -> None:
    world = evidence.data["request"]["world_size"]
    while len(list(evidence.root.glob("native-rank-*-ready.json"))) != world:
        if owner.poll() is not None:
            raise AssertionError("Native owner exited before every rank reached the fault gate")
        if time.monotonic() >= deadline:
            raise TimeoutError("Native ranks did not reach the fault gate before the deadline")
        time.sleep(0.1)


def _run(options: GPUOptions, selection: str, fault: Fault) -> Path:
    request = request_document(options, selection, fault)
    evidence = Evidence(options, request["scenario"])
    with evidence.retained():
        evidence.data["request"] = request
        base = environment_for(evidence)
        (evidence.root / "request.json").write_text(json.dumps(request))
        evidence.helper("preflight", base, timeout=90)
        inventory = json.loads((evidence.root / "preflight.json").read_text())["inventory"]
        request["uuids"] = list(resolve_devices(tuple(request["indexes"]), inventory))
        (evidence.root / "request.json").write_text(json.dumps(request))
        base["CUDA_VISIBLE_DEVICES"] = ",".join(request["uuids"])
        # Idle detection is fresh for every scenario and never stops another workload.
        _helper(evidence, "idle", base, 90)
        evidence.helper("cuda", base, timeout=90)
        _helper(evidence, "prepare", base, 60)
        environment = environment_for(evidence, instrument=True)
        environment["CUDA_VISIBLE_DEVICES"] = base["CUDA_VISIBLE_DEVICES"]
        argv = pipeline_arguments(evidence.root, request)
        evidence.data["commands"].append(argv)
        owner: subprocess.Popen[Any] | None = None
        deadline = time.monotonic() + options.timeout
        try:
            with (evidence.root / "owner.log").open("w") as stream:
                owner = subprocess.Popen(  # noqa: S603 - explicit test-owned public pipeline
                    argv,
                    cwd=evidence.root,
                    env=environment,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                )
                if fault != "none":
                    _wait_ready(evidence, owner, deadline)
                    if fault == "cancel":
                        (evidence.root / "cancel-target.json").write_text(json.dumps(owner.pid))
                        _helper(evidence, "cancel-record", base, 10)
                        owner.send_signal(signal.SIGINT)
                    else:
                        (evidence.root / "release-fault").touch()
                owner.wait(timeout=max(0.1, deadline - time.monotonic()))
                (evidence.root / "exit-code.json").write_text(json.dumps(owner.returncode))
                if fault == "none" and owner.returncode != 0:
                    raise AssertionError(
                        f"Native pipeline failed with {owner.returncode}; see owner.log"
                    )
        finally:
            _cleanup_scenario(evidence, base, owner, None)
        _helper(evidence, "verify", base, max(1, min(180, deadline - time.monotonic())))
        evidence.data["verification"] = json.loads(
            (evidence.root / "verification.json").read_text()
        )
    return evidence.root


def run_native_case(options: GPUOptions, selection: str, fault: Fault = "none") -> Path:
    root = _run(options, selection, fault)
    if fault != "none":
        recovered = _run(options, selection, "none")
        (root / "recovery.json").write_text(json.dumps({"successful_native_trial": str(recovered)}))
    return root
