from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from backend.models.session_state import (
    SessionState, Requirement, Constraint, Decision, OpenQuestion,
    ProjectStage, ItemStatus, QuestionStatus, now_iso,
)
from backend.providers.base import Message


class AgentOutputError(Exception):
    """Raised when a model response cannot be parsed into an AgentTurn."""


class SetSummaryOp(BaseModel):
    op: Literal["set_summary"]
    summary: str


class SetStageOp(BaseModel):
    op: Literal["set_stage"]
    stage: ProjectStage


class AddRequirementOp(BaseModel):
    op: Literal["add_requirement"]
    description: str


class AddConstraintOp(BaseModel):
    op: Literal["add_constraint"]
    description: str


class AddDecisionOp(BaseModel):
    op: Literal["add_decision"]
    topic: str
    choice: str
    reason: str = ""


class AnswerQuestionOp(BaseModel):
    op: Literal["answer_question"]
    id: str
    answer: str


EditOp = Annotated[
    Union[
        SetSummaryOp, SetStageOp, AddRequirementOp,
        AddConstraintOp, AddDecisionOp, AnswerQuestionOp,
    ],
    Field(discriminator="op"),
]


@dataclass
class AgentTurn:
    proposed_edits: list
    next_question: Optional[str]
    done: bool


def _next_id(prefix: str, items: list) -> str:
    return f"{prefix}-{len(items) + 1}"


def apply_edits(state: SessionState, edits: list, source: str) -> list[str]:
    """Apply edit-ops to state. Agent-created items are always `proposed`/`open`."""
    changes: list[str] = []
    for e in edits:
        if isinstance(e, SetSummaryOp):
            state.project.summary = e.summary
            changes.append("summary updated")
        elif isinstance(e, SetStageOp):
            state.project.currentStage = e.stage
            changes.append(f"stage -> {e.stage.value}")
        elif isinstance(e, AddRequirementOp):
            rid = _next_id("req", state.requirements)
            state.requirements.append(Requirement(
                id=rid, description=e.description,
                status=ItemStatus.proposed, source=source))
            changes.append(f"+ requirement {rid} (proposed)")
        elif isinstance(e, AddConstraintOp):
            cid = _next_id("con", state.constraints)
            state.constraints.append(Constraint(
                id=cid, description=e.description,
                status=ItemStatus.proposed, source=source))
            changes.append(f"+ constraint {cid} (proposed)")
        elif isinstance(e, AddDecisionOp):
            did = _next_id("dec", state.decisions)
            state.decisions.append(Decision(
                id=did, topic=e.topic, choice=e.choice, reason=e.reason,
                status=ItemStatus.proposed, proposedBy=source))
            changes.append(f"+ decision {did} (proposed)")
        elif isinstance(e, AnswerQuestionOp):
            for q in state.openQuestions:
                if q.id == e.id:
                    q.answer = e.answer
                    q.status = QuestionStatus.answered
                    changes.append(f"answered {q.id}")
                    break
    state.updatedAt = now_iso()
    return changes


def register_question(state: SessionState, question: str, asked_by: str = "pm") -> str:
    qid = _next_id("q", state.openQuestions)
    state.openQuestions.append(OpenQuestion(
        id=qid, question=question, askedBy=asked_by, status=QuestionStatus.open))
    state.updatedAt = now_iso()
    return qid


class Agent(ABC):
    name: str = "agent"

    @abstractmethod
    def contribute(self, state: SessionState, history: list[Message]) -> AgentTurn:
        ...
