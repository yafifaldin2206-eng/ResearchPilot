"""API schemas. Pydantic v2."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# Project
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# Research run
class ResearchCreate(BaseModel):
    project_id: uuid.UUID
    target: str = Field(..., description="Company name or annual report URL")


class ResearchOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    workflow_type: str
    target: str
    status: str
    progress: dict
    result: Optional[dict]
    error: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}
