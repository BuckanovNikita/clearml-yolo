"""Explicit physical CUDA/NCCL acceptance; never selected by ordinary pytest."""

import pytest

from ddp_gpu_harness import GPUOptions, run_scenario

pytestmark = pytest.mark.ddp_gpu


@pytest.mark.parametrize("compiled", [False, True], ids=["eager", "compiled"])
def test_physical_native_pipeline(ddp_gpu_options: GPUOptions, compiled: bool) -> None:
    scenario = f"direct-{'compiled' if compiled else 'eager'}"
    root = run_scenario(ddp_gpu_options, scenario, queued=False, compiled=compiled)
    assert (root / "verification.json").is_file()
