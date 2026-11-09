"""Explicit physical CUDA/NCCL acceptance; never selected by ordinary pytest."""

import pytest

from ddp_gpu_harness import GPUOptions, run_scenario
from native_backend_ddp_harness import SELECTIONS, Fault, run_native_case

pytestmark = pytest.mark.ddp_gpu


@pytest.mark.parametrize("compiled", [False, True], ids=["eager", "compiled"])
def test_physical_native_pipeline(ddp_gpu_options: GPUOptions, compiled: bool) -> None:
    scenario = f"direct-{'compiled' if compiled else 'eager'}"
    root = run_scenario(ddp_gpu_options, scenario, queued=False, compiled=compiled)
    assert (root / "verification.json").is_file()


@pytest.mark.parametrize("selection", SELECTIONS)
def test_physical_native_backend_pipeline(ddp_gpu_options: GPUOptions, selection: str) -> None:
    root = run_native_case(ddp_gpu_options, selection)
    assert (root / "verification.json").is_file()


@pytest.mark.parametrize("selection", SELECTIONS)
@pytest.mark.parametrize("fault", ["crash", "oom", "cancel"])
def test_physical_native_backend_failure_and_recovery(
    ddp_gpu_options: GPUOptions, selection: str, fault: Fault
) -> None:
    root = run_native_case(ddp_gpu_options, selection, fault)
    assert (root / "recovery.json").is_file()
