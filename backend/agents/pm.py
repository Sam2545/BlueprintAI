from __future__ import annotations

import json
from typing import Optional

from pydantic import TypeAdapter, ValidationError

from backend.agents.base import Agent, AgentTurn, AgentOutputError, EditOp
from backend.models.session_state import SessionState, QuestionStatus
from backend.providers.base import Message, Provider

_EDITS_ADAPTER = TypeAdapter(list[EditOp])

SYSTEM_PROMPT = """You are the Project Manager agent in BlueprintAI. You guide a user \
from a raw software idea to a structured design, asking ONE focused question at a time.

Every turn you MUST respond with a single JSON object and nothing else:
{
  "edits": [ ...zero or more edit operations... ],
  "question": "one focused question for the user, or empty string if done",
  "done": false
}

Valid edit operations (use only these shapes):
- {"op": "set_summary", "summary": "..."}
- {"op": "set_stage", "stage": "framing|requirements|approach|planning|review|done"}
- {"op": "add_requirement", "description": "..."}
- {"op": "add_constraint", "description": "..."}
- {"op": "add_decision", "topic": "...", "choice": "...", "reason": "..."}
- {"op": "answer_question", "id": "q-N", "answer": "..."}

Rules:
- Ask exactly ONE question per turn. Never ask multiple questions.
- Propose edits based only on what the user actually said. Do not invent facts.
- Reference open questions by their id (shown in the state) when recording answers.
- Set "done": true only when the design is well-formed and no question remains.
"""

REPAIR_INSTRUCTION = (
    "Your previous response was not valid JSON in the required format. "
    "Respond again with ONLY the JSON object, no prose, no code fences."
)


def _extract_json(raw: str) -> str:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise AgentOutputError("no JSON object found in model output")
    return raw[start:end + 1]


def _single_question(q) -> Optional[str]:
    if not isinstance(q, str) or not q.strip():
        return None
    q = q.strip()
    idx = q.find("?")
    return q[:idx + 1].strip() if idx != -1 else q


def parse_agent_turn(raw: str) -> AgentTurn:
    try:
        data = json.loads(_extract_json(raw))
        edits = _EDITS_ADAPTER.validate_python(data.get("edits", []))
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise AgentOutputError(str(exc)) from exc
    return AgentTurn(
        proposed_edits=edits,
        next_question=_single_question(data.get("question")),
        done=bool(data.get("done", False)),
    )


def _state_snapshot(state: SessionState) -> str:
    open_qs = [f'{q.id}: {q.question}' for q in state.openQuestions
               if q.status == QuestionStatus.open]
    lines = [
        f"stage: {state.project.currentStage.value}",
        f"summary: {state.project.summary or '(none yet)'}",
        f"requirements: {len(state.requirements)}",
        f"open questions: {open_qs or '(none)'}",
    ]
    return "\n".join(lines)


class ProjectManager(Agent):
    name = "pm"

    def __init__(self, provider: Provider):
        self.provider = provider

    def _build_messages(self, state: SessionState, history: list[Message]) -> list[Message]:
        messages = [
            Message(role="system", content=SYSTEM_PROMPT),
            Message(role="system", content="Current state:\n" + _state_snapshot(state)),
        ]
        messages.extend(history)
        return messages

    def contribute(self, state: SessionState, history: list[Message]) -> AgentTurn:
        messages = self._build_messages(state, history)
        raw = self.provider.complete(messages)
        try:
            return parse_agent_turn(raw)
        except AgentOutputError:
            repair = messages + [Message(role="user", content=REPAIR_INSTRUCTION)]
            raw2 = self.provider.complete(repair)
            return parse_agent_turn(raw2)
