"""Native determinism and rank seeding are applied before YOLO probe allocation."""

import os
import random
from pathlib import Path
from typing import Any, cast

import pytest

from clearml_yolo.adapters.yolo import batch_probe
from test_yolo_probe_precision import _request, restore_native_randomness  # noqa: F401 - shared autouse state isolation


@pytest.mark.parametrize("deterministic", [False, True])
@pytest.mark.parametrize(
    ("world_size", "rank", "local_rank", "expected_seed"), [(1, 0, 0, 7), (2, 0, 0, 8), (2, 1, 1, 9), (2, 1, 0, 9)]
)
def test_probe_initializes_native_determinism_and_rank_seed_before_model_allocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    deterministic: bool,
    world_size: int,
    rank: int,
    local_rank: int,
    expected_seed: int,
) -> None:
    import numpy as np
    import torch
    from ultralytics import models
    from ultralytics.utils.torch_utils import init_seeds

    class AssetReachedError(Exception):
        pass

    observed: dict[str, Any] = {}

    def asset(_architecture: str) -> None:
        observed.update(
            deterministic=torch.are_deterministic_algorithms_enabled(),
            warn_only=torch.is_deterministic_algorithms_warn_only_enabled(),
            cudnn=torch.backends.cudnn.deterministic,
            fill=cast(Any, torch.utils.deterministic).fill_uninitialized_memory,
            workspace=os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
            hash_seed=os.environ.get("PYTHONHASHSEED"),
            seed=torch.initial_seed(),
            python_draw=random.random(),  # noqa: S311 - native training reproducibility, not security
            numpy_draw=np.random.random(),  # noqa: NPY002 - observe the RNG seeded by native training
            torch_draw=torch.rand(()).item(),
        )
        raise AssetReachedError

    # Begin with the opposite policy to prove both enabling and resetting work.
    init_seeds(99, deterministic=not deterministic)  # type: ignore[no-untyped-call]
    monkeypatch.setenv("LOCAL_RANK", str(local_rank))
    monkeypatch.setenv("RANK", str(rank))
    monkeypatch.setattr(torch.cuda, "reset_peak_memory_stats", lambda _device: None)
    monkeypatch.setattr(models, "YOLO", asset)
    request = _request(tmp_path, False)
    request = request.model_copy(
        update={
            "profile": request.profile.model_copy(update={"gpus": request.profile.gpus * world_size}),
            "yolo": {"seed": 7, "deterministic": deterministic},
        }
    )
    with pytest.raises(AssetReachedError):
        batch_probe.probe(request)

    assert observed == {
        "deterministic": deterministic,
        "warn_only": deterministic,
        "cudnn": deterministic,
        "fill": not deterministic,
        "workspace": ":4096:8" if deterministic else None,
        "hash_seed": str(expected_seed) if deterministic else None,
        "seed": expected_seed,
        "python_draw": random.Random(expected_seed).random(),  # noqa: S311 - reproduce the native training stream
        "numpy_draw": np.random.RandomState(expected_seed).random(),
        "torch_draw": torch.rand((), generator=torch.Generator().manual_seed(expected_seed)).item(),
    }
