"""Explicit computation outcomes independent of tracking and persistence effects."""

from typing import Literal

from pydantic import BaseModel, Field, computed_field

StageStatus = Literal["succeeded", "completed_with_warnings", "failed", "skipped"]


class StageOutcome(BaseModel):
    """A stage's actual result; failed artifacts are never advertised as complete."""

    status: StageStatus
    reason: str | None = None
    artifacts: list[str] = Field(default_factory=list)


class PipelineOutcome(BaseModel):
    """Training success survives incomplete downstream work without hiding it."""

    schema_version: int = 1
    training_succeeded: bool = False
    fatal_error: bool = False
    stages: dict[str, StageOutcome] = Field(default_factory=dict)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def status(self) -> Literal["succeeded", "completed_with_warnings", "failed"]:
        if self.fatal_error:
            return "failed"
        failed = any(stage.status == "failed" for stage in self.stages.values())
        if failed and not self.training_succeeded:
            return "failed"
        if failed or any(
            stage.status == "completed_with_warnings" for stage in self.stages.values()
        ):
            return "completed_with_warnings"
        return "succeeded"

    def summary(self) -> str:
        """Render a portable human-readable companion to the JSON record."""
        lines = [f"Pipeline outcome: {self.status}"]
        for name, stage in self.stages.items():
            reason = f" — {stage.reason}" if stage.reason else ""
            lines.append(f"{name}: {stage.status}{reason}")
            lines.extend(f"  Artifact: {path}" for path in stage.artifacts)
        return "\n".join(lines) + "\n"
