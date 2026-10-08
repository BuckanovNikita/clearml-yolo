"""Tracking-neutral identity of the model whose checkpoint was evaluated."""

from collections.abc import Mapping
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator


class ModelIdentity(BaseModel):
    """A display name and known source identifiers, never the reporting task's ID."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_name: str
    training_task_id: str | None = None
    checkpoint_sha256: str | None = None
    model_id: str | None = None

    @field_validator("model_name")
    @classmethod
    def nonempty_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Model display name must be nonempty")
        return value

    @property
    def label(self) -> str:
        """Use the full source training task ID whenever it is known."""
        if self.training_task_id:
            return f"{self.model_name} ({self.training_task_id})"
        return self.model_name

    @property
    def caption(self) -> str:
        return (
            f"Model: {self.model_name}\n"
            f"Training task: {self.training_task_id or 'unavailable'}"
        )

    @classmethod
    def from_provenance(cls, provenance: Mapping[str, str]) -> Self:
        """Read a checkpoint selection's identity without querying a current task."""
        return cls(
            model_name=provenance["model_name"],
            training_task_id=provenance.get("training_task_id"),
            checkpoint_sha256=provenance.get("checkpoint_sha256"),
            model_id=provenance.get("model_id"),
        )








def require_model_identity(
    identity: ModelIdentity | None,
    label: str | None,
    *,
    checkpoint_hash: str | None = None,
) -> ModelIdentity:
    """Use source provenance or require an explicit label for an unknown input."""
    if identity is not None:
        return identity
    if label is None or not label.strip():
        raise ValueError(
            "Model provenance is unavailable; supply a custom model_label "
            "(comparison model references use label)"
        )
    return ModelIdentity(model_name=label, checkpoint_sha256=checkpoint_hash)
