from typing import Literal

from pydantic import BaseModel, Field


class IntentOutput(BaseModel):
    intent: Literal["simple_chat", "complex_research"] = "simple_chat"
    response_style: Literal["brief", "detailed"] = "brief"


class PlannedTaskOutput(BaseModel):
    id: str
    description: str
    dependencies: list[str] = Field(default_factory=list)


class TaskPlanOutput(BaseModel):
    tasks: list[PlannedTaskOutput] = Field(default_factory=list)
