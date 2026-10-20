"""Validated export operations; no model SDK or filesystem access."""

from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from clearml_yolo.core.models import Device


def gpu_device_index(device: Device) -> int:
    """Resolve one admitted visible index, retaining native default-device semantics."""
    if isinstance(device, list):
        if len(device) != 1:
            raise ValueError("Export requires exactly one device")
        device = device[0]
    if type(device) is int and device >= -1:
        return max(0, device)
    if isinstance(device, str):
        value = device.removeprefix("cuda:")
        if value.isdecimal():
            return int(value)
        if value in {"-1", "cuda"}:
            return 0
    raise ValueError("Export requires one explicit GPU device")


class ExportSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["onnx", "build", "verify"] = "onnx"
    device: Device = "cpu"
    precision: Literal["fp32", "fp16"] = "fp32"
    onnx: Path | None = None
    engine: Path | None = None
    metadata: Path | None = None
    workspace_gib: Annotated[float, Field(gt=0)] = 4
    split: Literal["train", "val", "test"] = "test"

    @model_validator(mode="after")
    def one_device(self) -> Self:
        device = self.device
        if self.operation == "onnx":
            if device != "cpu" or self.precision != "fp32":
                raise ValueError(
                    "ONNX export requires device=cpu precision=fp32; "
                    "select GPU/FP16 during engine build"
                )
            return self
        gpu_device_index(device)
        return self

    def validate_input_presence(self, *, has_weights: bool, has_ground_truth: bool) -> None:
        """Reject incomplete operations before task creation or remote resolution."""
        if self.operation == "onnx" and not has_weights:
            raise ValueError("ONNX export requires weights")
        if self.operation == "build" and self.onnx is None:
            raise ValueError("Engine build requires an ONNX graph and its metadata")
        if self.operation == "verify" and (
            self.engine is None or not has_weights or not has_ground_truth
        ):
            raise ValueError("Verification requires engine, weights and labeled ground_truth")


class ExportRequest(ExportSettings):
    weights: Path | None = None
    ground_truth: Path | None = None

    @model_validator(mode="after")
    def operation_inputs(self) -> Self:
        self.validate_input_presence(
            has_weights=self.weights is not None, has_ground_truth=self.ground_truth is not None
        )
        return self


class ExportResult(BaseModel):
    artifacts: dict[str, Path]
    evidence: dict[str, Any]
    passed: bool = True
