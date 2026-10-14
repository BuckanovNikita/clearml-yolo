"""Explicit physical CUDA/NCCL acceptance; never selected by ordinary pytest."""

from pathlib import Path

import pytest

from ddp_gpu_harness import GPUOptions, run_scenario

pytestmark = pytest.mark.ddp_gpu


@pytest.mark.parametrize("queued", [False, True], ids=["direct", "queued"])
@pytest.mark.parametrize("compiled", [False, True], ids=["eager", "compiled"])
def test_physical_native_pipeline(
    ddp_gpu_options: GPUOptions, queued: bool, compiled: bool
) -> None:
    scenario = f"{'queued' if queued else 'direct'}-{'compiled' if compiled else 'eager'}"
    root = run_scenario(ddp_gpu_options, scenario, queued=queued, compiled=compiled)
    assert (root / "verification.json").is_file()


@pytest.mark.parametrize("scenario", ["queued-rank-exit", "queued-cancel", "queued-guardian-death"])
def test_physical_queued_failure_cleanup(ddp_gpu_options: GPUOptions, scenario: str) -> None:
    root: Path = run_scenario(ddp_gpu_options, scenario, queued=True, compiled=False)
    assert (root / "cleanup.json").is_file()
