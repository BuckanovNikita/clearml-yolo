"""Data-only contracts shared by local documentation composition and serving."""

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class FieldDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    description: str
    shapes: str
    constraints: str
    applicability: str
    examples: list[JsonValue]
    source: str
    required: bool = False
    generated: bool = False


class FieldDoc(FieldDetails):
    id: str
    path: str
    commands: list[str]
    variants: dict[str, FieldDetails] = Field(default_factory=dict)


class ConfigurationDoc(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    command: str
    model: str = ""
    profile: str = ""
    yaml: str
    values: dict[str, JsonValue]
    expressions: dict[str, JsonValue]


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    command: str = "train"
    documents: dict[str, str] = Field(default_factory=dict, max_length=32)
    overrides: list[str] = Field(default_factory=list, max_length=256)
    sweep: bool = False


class PreviewJob(BaseModel):
    yaml: str
    values: dict[str, JsonValue]
    unresolved: list[str]
    errors: list[str]


class PreviewResult(BaseModel):
    jobs: list[PreviewJob] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    deferred: list[str] = Field(default_factory=list)
    command: str = ""


class TutorialDoc(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    file: str
    commands: list[str]
    groups: list[str]
    scenarios: list[str]
    previews: list[PreviewRequest]


class Catalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str
    commands: dict[str, str]
    models: list[str]
    profiles: list[str]
    fields: list[FieldDoc]
    configurations: list[ConfigurationDoc]
    tutorials: list[TutorialDoc]
