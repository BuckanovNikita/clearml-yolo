"""Native acceptance observations; importing this module starts no workloads."""

import hashlib
import json
import math
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_pipeline(path: Path, variant: str, resolution: int) -> None:
    """Exercise the supported A.save interchange, including real standard Mosaic."""
    import albumentations as alb

    operations: list[Any] = []
    if variant == "json_mosaic":
        operations.append(
            alb.Mosaic(
                grid_yx=(2, 2),
                target_size=(resolution, resolution),
                cell_shape=(resolution, resolution),
                p=1,
            )
        )
    elif variant != "json":
        raise ValueError(f"Unsupported JSON variant: {variant}")
    operations.extend([alb.HorizontalFlip(p=1), alb.RandomBrightnessContrast(p=1)])
    pipeline = alb.Compose(
        operations,
        bbox_params=alb.BboxParams(format="pascal_voc", label_fields=["class_labels"]),
        seed=0,
    )
    alb.save(pipeline, path, data_format="json")


class OptimizerObservation:
    """Observe real optimizer changes without replacing training or optimizer behavior."""

    def __init__(self) -> None:
        self.steps = 0
        self.skipped_steps = 0
        self.skipping = False
        self.changed = False
        self.initial_sha256: str | None = None
        # Torch optimizer hooks expose opaque argument tuples and heterogeneous param groups.
        self.sample: Any = None
        self.before: Any = None

    def _before(self, optimizer: Any, _args: Any, _kwargs: Any) -> None:
        import torch

        if self.initial_sha256 is None:
            digest = hashlib.sha256()
            for group in optimizer.param_groups:
                for parameter in group["params"]:
                    value = parameter.detach().cpu().contiguous()
                    digest.update(str((tuple(value.shape), value.dtype)).encode())
                    digest.update(value.reshape(-1).view(torch.uint8).numpy().tobytes())
            self.initial_sha256 = digest.hexdigest()
        # Fused optimizers receive GradScaler's overflow flag and skip inside step(),
        # so their hooks run even when no parameter update will occur.
        self.skipping = bool(getattr(optimizer, "found_inf", 0))
        if self.skipping:
            return
        if not self.changed:
            for group in optimizer.param_groups:
                for parameter in group["params"]:
                    gradient = parameter.grad
                    if gradient is not None and torch.count_nonzero(gradient):
                        if not torch.isfinite(gradient).all():
                            raise AssertionError("Observed non-finite native training gradient")
                        self.sample = parameter
                        self.before = parameter.detach().clone()
                        return

    def _after(self, _optimizer: Any, _args: Any, _kwargs: Any) -> None:
        import torch

        if self.skipping:
            self.skipped_steps += 1
            return
        self.steps += 1
        if self.sample is not None:
            if not torch.isfinite(self.sample).all():
                raise AssertionError("Observed non-finite parameter after native optimizer step")
            self.changed = self.changed or not torch.equal(self.sample.detach(), self.before)
            self.sample = self.before = None

    @contextmanager
    def installed(self) -> Iterator[None]:
        from torch.optim.optimizer import (
            register_optimizer_step_post_hook,
            register_optimizer_step_pre_hook,
        )

        pre = register_optimizer_step_pre_hook(self._before)
        post = register_optimizer_step_post_hook(self._after)
        try:
            yield
        finally:
            pre.remove()
            post.remove()

    def result(self) -> dict[str, Any]:
        return {
            "steps": self.steps,
            "skipped_steps": self.skipped_steps,
            "parameter_changed": self.changed,
            "initial_optimizer_parameters_sha256": self.initial_sha256,
        }


def validate_observation(observation: Mapping[str, Any]) -> None:
    assert observation["steps"] > 0, "No native optimizer step was observed"
    assert observation["parameter_changed"], "Native optimizer did not change observed parameters"
    assert observation["initial_optimizer_parameters_sha256"], "Missing initialization identity"


def loss_values(scalars: Mapping[str, Any]) -> list[float]:
    values = [
        float(value)
        for title, series in scalars.items()
        for name, points in series.items()
        if "loss" in f"{title} {name}".lower()
        for value in points.get("y", [])
    ]
    assert values, "No real native loss series was published"
    assert all(math.isfinite(value) for value in values), "Native loss is not finite"
    return values


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, default=str, allow_nan=False) + "\n", encoding="utf-8"
    )
