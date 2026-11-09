"""Tracking-neutral identity of the model whose checkpoint was evaluated."""

from collections.abc import Mapping
from typing import Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, field_validator

from clearml_yolo.core.presentation import human_text


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
        """Display the model name; exact source identifiers remain in provenance."""
        return human_text(self.model_name)

    @property
    def caption(self) -> str:
        return f"Model: {self.label}\nTraining source: {'recorded' if self.training_task_id else 'unavailable'}"

    @classmethod
    def from_provenance(cls, provenance: Mapping[str, str]) -> Self:
        """Read a checkpoint selection's identity without querying a current task."""
        return cls(
            model_name=provenance["model_name"],
            training_task_id=provenance.get("training_task_id"),
            checkpoint_sha256=provenance.get("checkpoint_sha256"),
            model_id=provenance.get("model_id"),
        )


class IdentityLinks(BaseModel):
    """Exact web addresses of a model's tracked sources, derived when a report renders.

    Links are presentation data: they are never stored as identity, so an unknown
    host only removes the link while the identity remains complete.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_url: str | None = None
    task_url: str | None = None

    @field_validator("model_url", "task_url")
    @classmethod
    def absolute_web_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise ValueError("Identity links must be absolute http or https URLs")
        return value


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
            "Model provenance is unavailable; supply a custom model_label (comparison model references use label)"
        )
    return ModelIdentity(model_name=label, checkpoint_sha256=checkpoint_hash)
