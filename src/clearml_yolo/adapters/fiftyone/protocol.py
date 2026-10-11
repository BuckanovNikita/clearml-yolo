"""Validated, file-based messages for optional publication workers."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from clearml_yolo.core.publication import FiftyOneConfig, PublicationReceipt, PublicationRequest


class WorkerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["preflight", "publish"]
    operation_id: str
    config: FiftyOneConfig
    request: PublicationRequest | None = None


class WorkerResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["preflight", "publish"]
    operation_id: str
    task_id: str | None
    complete: Literal[True]
    receipt: PublicationReceipt | None = None
