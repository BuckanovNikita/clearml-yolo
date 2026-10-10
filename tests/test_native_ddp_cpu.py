"""Real CPU distributed YOLO training and invocation-owner telemetry."""

import math
import sys
from pathlib import Path
from typing import Any

import pytest
from torch import distributed

pytestmark = [
    pytest.mark.ddp_cpu,
    pytest.mark.skipif(
        not sys.platform.startswith("linux")
        or not distributed.is_available()
        or not distributed.is_gloo_available(),
        reason="CPU DDP integration requires Linux/WSL and PyTorch Gloo",
    ),
]


def _run(tmp_path: Path, ranks: int, scenario: str) -> dict[str, Any]:
    from ddp_cpu_launcher import run_scenario

    return run_scenario(tmp_path, ranks, scenario)


def _clean(result: dict[str, Any]) -> None:
    assert result["remaining_pids"] == []
    assert result["runtime_directories"] == []
    assert result["relay_threads"] == []
    assert result["callbacks_restored"]
    assert result["environment_restored"], result["changed_environment_keys"]


@pytest.mark.parametrize("ranks", [2, 4], ids=["two-ranks", "four-ranks"])
def test_cpu_ddp_trains_yolo_and_replays_only_rank_zero(tmp_path: Path, ranks: int) -> None:
    result = _run(tmp_path, ranks, "success")
    assert result["error"] is None, result
    assert result["launcher_returncode"] == 0
    workers = result["workers"]
    assert len(workers) == ranks
    assert len({worker["pid"] for worker in workers}) == ranks
    assert {worker["rank"] for worker in workers} == set(range(ranks))
    assert len({worker["initial_parameters_sha256"] for worker in workers}) == 1
    for worker in workers:
        assert worker["completed"], worker
        assert worker["error"] is None
        assert worker["world_size"] == ranks
        assert worker["backend"] == "gloo"
        assert worker["device"] == "cpu"
        assert worker["ddp"]
        assert worker["distributed_sampler"]
        assert 0 < worker["parameter_count"] < 4_000_000
        assert not worker["cuda_initialized"]
        assert worker["worker_tracking_disabled"]
        assert worker["active_task_none"]
        assert worker["validation_calls"] == 2
        assert worker["final_validation_calls"] == 1
        assert len(worker["epochs"]) == 2
    for epoch in range(2):
        observations = [worker["epochs"][epoch] for worker in workers]
        assert all(item["epoch"] == epoch for item in observations)
        assert all(item["parameters_changed"] for item in observations)
        assert all(item["optimizer_steps"] > 0 for item in observations)
        assert all(
            math.isfinite(value) for item in observations for value in item["losses"].values()
        )
        assert len({item["parameters_sha256"] for item in observations}) == 1
        samples = [sample for item in observations for sample in item["samples"]]
        assert len(samples) == len(set(samples)) == 8
        assert set(samples) == {f"train-{index}.png" for index in range(8)}
    assert any(
        worker["epochs"][0]["samples"] != worker["epochs"][1]["samples"] for worker in workers
    )
    assert result["live_telemetry"]
    assert result["inference_images"] == 1
    assert result["effective_args"]["imgsz"] == 64
    assert result["effective_args"]["device"] == "cpu"
    assert len(result["output_models"]) == 1
    assert result["output_models"][0]["pid"] == result["owner_pid"]
    assert result["output_models"][0]["bytes"] > 0
    assert all(event["pid"] == result["owner_pid"] for event in result["publications"])
    assert result["replayed_events"] == result["captured_events"]
    assert result["captured_events"].count("on_pretrain_routine_start") == 1
    assert result["captured_events"].count("on_train_epoch_end") == 2
    assert result["captured_events"].count("on_train_end") == 1
    scalars = result["scalars"]
    assert len({(item["title"], item["series"], item["iteration"]) for item in scalars}) == len(
        scalars
    )
    for observation in workers[0]["epochs"]:
        for name, value in observation["losses"].items():
            assert any(
                scalar["series"] == name
                and scalar["iteration"] == observation["epoch"]
                and scalar["value"] == pytest.approx(value)
                for scalar in scalars
            )
    _clean(result)


@pytest.mark.parametrize("failed_rank", [0, 1], ids=["rank-zero", "nonzero-rank"])
def test_cpu_ddp_worker_failure_stops_peers_without_model_publication(
    tmp_path: Path, failed_rank: int
) -> None:
    result = _run(tmp_path, 2, f"rank{failed_rank}_error")
    assert result["launcher_returncode"] != 0
    assert result["error"] is not None
    assert result["output_models"] == []
    assert result["live_telemetry"]
    assert len(result["workers"]) == 2
    failed = next(worker for worker in result["workers"] if worker["rank"] == failed_rank)
    assert not failed["completed"]
    assert f"Injected rank {failed_rank} failure" in failed["error"]["message"]
    assert "Injected rank" in (tmp_path / f"rank-{failed_rank}.log").read_text()
    _clean(result)


def test_cpu_ddp_owner_callback_failure_blocks_final_publication(tmp_path: Path) -> None:
    result = _run(tmp_path, 2, "owner_error")
    assert "Injected owner callback failure" in result["error"]
    assert result["launcher_returncode"] == 0
    assert all(worker["completed"] for worker in result["workers"])
    assert result["output_models"] == []
    assert result["owner_callback_failed"]
    _clean(result)
