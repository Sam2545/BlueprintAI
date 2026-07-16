from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from backend.agents.base import Agent, apply_edits, register_question
from backend.agents.pm import ProjectManager
from backend.models.render import render_design_doc
from backend.models.session_state import (
    Artifact, ArtifactStatus, ArtifactType, ItemStatus, ProjectStatus,
    SessionState, now_iso,
)
from backend.providers.base import Message, Provider


@dataclass
class TurnResult:
    changes: list[str]
    question: Optional[str]
    question_id: Optional[str]
    done: bool


class Conversation:
    def __init__(self, provider: Provider, agent: Optional[Agent] = None,
                 session_id: str = "sess-1"):
        self.state = SessionState.new(session_id)
        self.agent = agent or ProjectManager(provider)
        self.history: list[Message] = []

    def send(self, user_input: str) -> TurnResult:
        self.history.append(Message(role="user", content=user_input))
        turn = self.agent.contribute(self.state, self.history)
        changes = apply_edits(self.state, turn.proposed_edits, source=self.agent.name)
        qid = None
        if turn.next_question:
            qid = register_question(self.state, turn.next_question, self.agent.name)
            self.history.append(Message(role="assistant", content=turn.next_question))
        return TurnResult(changes=changes, question=turn.next_question,
                          question_id=qid, done=turn.done)

    def _find(self, item_id: str):
        for coll in (self.state.requirements, self.state.constraints, self.state.decisions):
            for item in coll:
                if item.id == item_id:
                    return item
        return None

    def approve(self, item_id: str) -> bool:
        item = self._find(item_id)
        if item is None:
            return False
        item.status = ItemStatus.approved
        if hasattr(item, "approvedBy"):
            item.approvedBy = "user"
        self.state.updatedAt = now_iso()
        return True

    def reject(self, item_id: str) -> bool:
        item = self._find(item_id)
        if item is None:
            return False
        item.status = ItemStatus.rejected
        self.state.updatedAt = now_iso()
        return True

    def save(self) -> Artifact:
        content = render_design_doc(self.state)
        version = max((a.version for a in self.state.artifacts), default=0) + 1
        art = Artifact(
            id=f"art-{len(self.state.artifacts) + 1}",
            type=ArtifactType.design_doc,
            version=version,
            status=ArtifactStatus.final,
            content=content,
        )
        self.state.artifacts.append(art)
        self.state.project.status = ProjectStatus.saved
        self.state.updatedAt = now_iso()
        return art
