"""Task request and response schemas."""

import uuid

from pydantic import BaseModel, ConfigDict, computed_field, field_validator

from api.schemas.base import LifecycleResponse


class TaskStepActionCreate(BaseModel):
    instruction: str


class TaskStepActionResponse(BaseModel):
    id: uuid.UUID
    order_index: int
    instruction: str

    model_config = ConfigDict(from_attributes=True)


class TaskStepCreate(BaseModel):
    step: str
    completion: str
    notes: str | None = None
    irreversible: bool = False
    actions: list[TaskStepActionCreate] = []


class TaskStepUpdate(BaseModel):
    step: str | None = None
    completion: str | None = None
    notes: str | None = None
    irreversible: bool | None = None


class TaskStepImageResponse(BaseModel):
    id: uuid.UUID
    order_index: int
    storage_path: str
    caption: str | None

    model_config = ConfigDict(from_attributes=True)


class TaskStepResponse(BaseModel):
    id: uuid.UUID
    order_index: int
    step: str
    completion: str
    notes: str | None
    irreversible: bool
    actions: list[TaskStepActionResponse]
    images: list[TaskStepImageResponse]

    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    title: str
    outcome: str
    domain: str
    software_name: str | None = None
    software_version: str | None = None
    media_url: str | None = None
    facts: list[str] = []
    concepts: list[str] = []
    tags: list[str] = []


class TaskUpdate(BaseModel):
    title: str | None = None
    outcome: str | None = None
    domain: str | None = None
    software_name: str | None = None
    software_version: str | None = None
    media_url: str | None = None
    facts: list[str] | None = None
    concepts: list[str] | None = None
    tags: list[str] | None = None


class ReturnRequest(BaseModel):
    note: str | None = None
    severity: str | None = None  # "info" | "warning" | "critical"


class ReviseRequest(BaseModel):
    note: str | None = None


class TaskVersionSummary(BaseModel):
    id: uuid.UUID
    version: int
    status: str

    model_config = ConfigDict(from_attributes=True)


class TaskResponse(LifecycleResponse):
    title: str
    outcome: str
    domain: str
    software_name: str | None
    software_version: str | None
    media_url: str | None
    facts: list[str]
    concepts: list[str]
    tags: list[str]
    steps: list[TaskStepResponse]

    @field_validator("facts", "concepts", mode="before")
    @classmethod
    def _coerce_none_to_empty(cls, v: list[str] | None) -> list[str]:
        return v if v is not None else []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def irreversible(self) -> bool:
        """Derived from steps: True if any step has irreversible=True (§9.5)."""
        return any(s.irreversible for s in self.steps)


class TaskDiffResponse(BaseModel):
    current: TaskResponse
    previous: TaskResponse

    model_config = ConfigDict(from_attributes=True)
