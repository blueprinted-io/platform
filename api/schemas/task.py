"""Task request and response schemas."""

import uuid

from pydantic import BaseModel, ConfigDict, computed_field

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


class TaskStepResponse(BaseModel):
    id: uuid.UUID
    order_index: int
    step: str
    completion: str
    notes: str | None
    irreversible: bool
    actions: list[TaskStepActionResponse]

    model_config = ConfigDict(from_attributes=True)


class TaskFactRefCreate(BaseModel):
    fact_record_id: uuid.UUID


class TaskFactRefResponse(BaseModel):
    fact_record_id: uuid.UUID
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class TaskConceptRefCreate(BaseModel):
    concept_record_id: uuid.UUID


class TaskConceptRefResponse(BaseModel):
    concept_record_id: uuid.UUID
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    title: str
    outcome: str
    procedure_name: str
    domain: str | None = None
    software_name: str | None = None
    software_version: str | None = None
    media_url: str | None = None
    tags: list[str] = []


class TaskUpdate(BaseModel):
    title: str | None = None
    outcome: str | None = None
    procedure_name: str | None = None
    domain: str | None = None
    software_name: str | None = None
    software_version: str | None = None
    media_url: str | None = None
    tags: list[str] | None = None


class ReturnRequest(BaseModel):
    note: str | None = None


class TaskResponse(LifecycleResponse):
    title: str
    outcome: str
    procedure_name: str
    domain: str | None
    software_name: str | None
    software_version: str | None
    media_url: str | None
    tags: list[str]
    has_deprecated_fact_ref: bool
    has_deprecated_concept_ref: bool
    steps: list[TaskStepResponse]
    fact_refs: list[TaskFactRefResponse]
    concept_refs: list[TaskConceptRefResponse]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def irreversible(self) -> bool:
        """Derived from steps: True if any step has irreversible=True (§9.5)."""
        return any(s.irreversible for s in self.steps)
