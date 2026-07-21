from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectStage(str, Enum):
    framing = "framing"
    requirements = "requirements"
    approach = "approach"
    planning = "planning"
    review = "review"
    done = "done"


class ProjectStatus(str, Enum):
    active = "active"
    saved = "saved"
    archived = "archived"


class ItemStatus(str, Enum):
    proposed = "proposed"
    approved = "approved"
    rejected = "rejected"


class QuestionStatus(str, Enum):
    open = "open"
    answered = "answered"
    dismissed = "dismissed"


class ArtifactType(str, Enum):
    design_doc = "design-doc"


class ArtifactStatus(str, Enum):
    draft = "draft"
    final = "final"


class Project(BaseModel):
    id: str
    name: str = ""
    summary: str = ""
    currentStage: ProjectStage = ProjectStage.framing
    status: ProjectStatus = ProjectStatus.active


class Requirement(BaseModel):
    id: str
    description: str
    status: ItemStatus = ItemStatus.proposed
    source: str
    createdAt: str = Field(default_factory=now_iso)


class Constraint(BaseModel):
    id: str
    description: str
    status: ItemStatus = ItemStatus.proposed
    source: str


class Decision(BaseModel):
    id: str
    topic: str
    choice: str
    reason: str = ""
    status: ItemStatus = ItemStatus.proposed
    proposedBy: str
    approvedBy: Optional[str] = None


class OpenQuestion(BaseModel):
    id: str
    question: str
    askedBy: str
    status: QuestionStatus = QuestionStatus.open
    answer: Optional[str] = None


class Artifact(BaseModel):
    id: str
    type: ArtifactType = ArtifactType.design_doc
    version: int
    status: ArtifactStatus = ArtifactStatus.final
    content: str


class SessionState(BaseModel):
    schemaVersion: int = 1
    sessionId: str
    createdAt: str = Field(default_factory=now_iso)
    updatedAt: str = Field(default_factory=now_iso)
    project: Project
    requirements: list[Requirement] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    openQuestions: list[OpenQuestion] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)

    @classmethod
    def new(cls, session_id: str) -> "SessionState":
        return cls(sessionId=session_id, project=Project(id="proj-1"))
