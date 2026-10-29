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

    operation: Literal["onnx", "build", "verify"] = Field(
        default="onnx",
        description=(
            "Операция: onnx экспортирует граф, build собирает TensorRT, verify "
            "проверяет качество движка."
        ),
        examples=["onnx"],
        json_schema_extra={
            "shapes": "Literal['onnx', 'build', 'verify']",
            "applicability": "ExportSettings",
            "source": "clearml_yolo.core.export_requests.ExportSettings.operation",
            "classification": "input",
        },
    )
    device: Device = Field(
        default="cpu",
        description="Для onnx только cpu; для build/verify требуется ровно один явный GPU.",
        examples=["cpu"],
        json_schema_extra={
            "shapes": "Device",
            "applicability": "ExportSettings",
            "source": "clearml_yolo.core.export_requests.ExportSettings.device",
            "classification": "input",
        },
    )
    precision: Literal["fp32", "fp16"] = Field(
        default="fp32",
        description=(
            "Точность fp32 или fp16. ONNX экспортируется на CPU только в fp32; "
            "fp16 выбирается при сборке движка."
        ),
        examples=["fp32"],
        json_schema_extra={
            "shapes": "Literal['fp32', 'fp16']",
            "applicability": "ExportSettings",
            "source": "clearml_yolo.core.export_requests.ExportSettings.precision",
            "classification": "input",
        },
    )
    onnx: Path | None = Field(
        default=None,
        description="Путь к графу ONNX; обязателен при operation=build.",
        examples=["model.onnx"],
        json_schema_extra={
            "shapes": "Path | None",
            "applicability": "ExportSettings",
            "source": "clearml_yolo.core.export_requests.ExportSettings.onnx",
            "classification": "input",
        },
    )
    engine: Path | None = Field(
        default=None,
        description="Путь к движку TensorRT; обязателен при operation=verify.",
        examples=["model.engine"],
        json_schema_extra={
            "shapes": "Path | None",
            "applicability": "ExportSettings",
            "source": "clearml_yolo.core.export_requests.ExportSettings.engine",
            "classification": "input",
        },
    )
    metadata: Path | None = Field(
        default=None,
        description="Путь к метаданным экспорта; null использует соседние данные графа или движка.",
        examples=["model.metadata.json"],
        json_schema_extra={
            "shapes": "Path | None",
            "applicability": "ExportSettings",
            "source": "clearml_yolo.core.export_requests.ExportSettings.metadata",
            "classification": "input",
        },
    )
    workspace_gib: Annotated[float, Field(gt=0)] = Field(
        default=4,
        description="Положительный объём рабочего пространства TensorRT в GiB.",
        examples=[4.0],
        json_schema_extra={
            "shapes": "Annotated[float, Field(gt=0)]",
            "applicability": "ExportSettings",
            "source": "clearml_yolo.core.export_requests.ExportSettings.workspace_gib",
            "classification": "input",
        },
    )
    split: Literal["train", "val", "test"] = Field(
        default="test",
        description="Размеченный сплит проверки качества экспорта: train, val или test.",
        examples=["test"],
        json_schema_extra={
            "shapes": "Literal['train', 'val', 'test']",
            "applicability": "ExportSettings",
            "source": "clearml_yolo.core.export_requests.ExportSettings.split",
            "classification": "input",
        },
    )

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
