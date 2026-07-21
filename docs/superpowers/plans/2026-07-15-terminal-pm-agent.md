# Terminal PM Agent (M1a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single Project Manager agent that runs a guided, one-question-at-a-time design conversation entirely in the terminal, over the session state model, with deterministic structural tests plus a real-model evaluation harness.

**Architecture:** A model-provider abstraction (`Provider.complete`) keeps LLM calls out of agent code. The PM agent returns a structured `AgentTurn` (typed edit-ops + one question) parsed from model JSON; edits are applied to an in-memory `SessionState` with server-assigned IDs and forced `proposed` status. One shared `Conversation` loop backs two CLIs — an interactive REPL and a scripted replay. Fakes and evals live entirely under `tests/`.

**Tech Stack:** Python 3.11+, Pydantic v2, httpx, python-dotenv, pytest.

## Global Constraints

- **Keys server-side only:** the `OPENROUTER_API_KEY` is read from a git-ignored `.env`; never hard-code or log it.
- **Provider abstraction is mandatory:** agent code calls `Provider.complete(...)` only — never an HTTP client or provider SDK directly.
- **`backend/` is product source only.** All fakes, mocks, tests, and evals live under `tests/`.
- **Provider is injected**, never imported concretely by `core/` or `agents/`. CLIs default to `OpenRouterProvider`; tests inject `FakeProvider`.
- **HITL invariants enforced in code:** every agent-created item is forced to `status="proposed"` (`"open"` for questions); at most one question per turn.
- **Default model:** `meta-llama/llama-3.3-70b-instruct:free`, overridable via `OPENROUTER_MODEL`.
- **IDs are server-assigned**, prefixed (`proj-`, `req-`, `con-`, `dec-`, `q-`, `art-`); never taken from model output.
- Run all commands from the repo root. Run tests with `pytest`.

---

### Task 1: Project scaffold + session state models

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `backend/__init__.py`, `backend/models/__init__.py`
- Create: `backend/models/session_state.py`
- Create: `tests/__init__.py`
- Test: `tests/test_session_state.py`

**Interfaces:**
- Produces: enums `ProjectStage`, `ProjectStatus`, `ItemStatus`, `QuestionStatus`, `ArtifactType`, `ArtifactStatus`; models `Project`, `Requirement`, `Constraint`, `Decision`, `OpenQuestion`, `Artifact`, `SessionState`; helper `now_iso() -> str`; classmethod `SessionState.new(session_id: str) -> SessionState`.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "blueprintai"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.6",
    "httpx>=0.27",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.env
.venv/
venv/
.pytest_cache/
*.egg-info/
```

- [ ] **Step 3: Create `.env.example`**

```dotenv
OPENROUTER_API_KEY=sk-or-your-key-here
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

- [ ] **Step 4: Create empty package files**

Create `backend/__init__.py`, `backend/models/__init__.py`, `tests/__init__.py` each as empty files.

- [ ] **Step 5: Write the failing test**

Create `tests/test_session_state.py`:

```python
from backend.models.session_state import (
    SessionState, Requirement, ItemStatus, ProjectStage, ProjectStatus,
)


def test_new_session_has_project_and_defaults():
    s = SessionState.new("sess-1")
    assert s.sessionId == "sess-1"
    assert s.schemaVersion == 1
    assert s.project.id == "proj-1"
    assert s.project.currentStage == ProjectStage.framing
    assert s.project.status == ProjectStatus.active
    assert s.requirements == []


def test_requirement_defaults_to_proposed():
    r = Requirement(id="req-1", description="do a thing", source="pm")
    assert r.status == ItemStatus.proposed
    assert r.createdAt  # timestamp populated


def test_roundtrip_serialization():
    s = SessionState.new("sess-1")
    s.requirements.append(Requirement(id="req-1", description="x", source="user"))
    dumped = s.model_dump_json()
    restored = SessionState.model_validate_json(dumped)
    assert restored.requirements[0].description == "x"
    assert restored == s
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_session_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.models.session_state'`

- [ ] **Step 7: Implement `backend/models/session_state.py`**

```python
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
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest tests/test_session_state.py -v`
Expected: PASS (3 passed)

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml .gitignore .env.example backend/ tests/
git commit -m "Add project scaffold and session state models"
```

---

### Task 2: Render design doc to markdown

**Files:**
- Create: `backend/models/render.py`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `SessionState`, `ItemStatus`, `QuestionStatus` from Task 1.
- Produces: `render_design_doc(state: SessionState) -> str`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_render.py`:

```python
from backend.models.session_state import (
    SessionState, Requirement, Decision, OpenQuestion, ItemStatus,
)
from backend.models.render import render_design_doc


def _sample_state() -> SessionState:
    s = SessionState.new("sess-1")
    s.project.name = "Library Reminders"
    s.project.summary = "Remind parents when library books are due."
    s.requirements.append(
        Requirement(id="req-1", description="Notify before due date",
                    status=ItemStatus.approved, source="user")
    )
    s.requirements.append(
        Requirement(id="req-2", description="Track multiple children",
                    status=ItemStatus.proposed, source="pm")
    )
    s.decisions.append(
        Decision(id="dec-1", topic="Platform", choice="Mobile-first",
                 reason="Push notifications", status=ItemStatus.approved,
                 proposedBy="pm", approvedBy="user")
    )
    s.openQuestions.append(
        OpenQuestion(id="q-1", question="Barcode scan or manual entry?", askedBy="pm")
    )
    return s


def test_render_includes_sections_and_content():
    md = render_design_doc(_sample_state())
    assert "# Library Reminders" in md
    assert "## Overview" in md
    assert "Remind parents when library books are due." in md
    assert "## Users & Requirements" in md
    assert "Notify before due date" in md
    assert "Track multiple children _(proposed)_" in md
    assert "## Proposed Approach" in md
    assert "**Platform:** Mobile-first" in md
    assert "## Open Questions / Risks" in md
    assert "Barcode scan or manual entry?" in md


def test_render_empty_state_has_placeholders():
    md = render_design_doc(SessionState.new("sess-1"))
    assert "_No summary yet._" in md
    assert "_No requirements yet._" in md


def test_rejected_items_are_excluded():
    s = SessionState.new("sess-1")
    s.requirements.append(
        Requirement(id="req-1", description="secret", status=ItemStatus.rejected, source="pm")
    )
    md = render_design_doc(s)
    assert "secret" not in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_render.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.models.render'`

- [ ] **Step 3: Implement `backend/models/render.py`**

```python
from backend.models.session_state import SessionState, ItemStatus, QuestionStatus


def _mark(status: ItemStatus) -> str:
    return "" if status == ItemStatus.approved else " _(proposed)_"


def render_design_doc(state: SessionState) -> str:
    p = state.project
    lines: list[str] = [f"# {p.name or 'Untitled Project'}", ""]

    lines += ["## Overview", "", p.summary or "_No summary yet._", ""]

    reqs = [r for r in state.requirements if r.status != ItemStatus.rejected]
    lines += ["## Users & Requirements", ""]
    if reqs:
        lines += [f"- {r.description}{_mark(r.status)}" for r in reqs]
    else:
        lines.append("_No requirements yet._")
    lines.append("")

    decisions = [d for d in state.decisions if d.status != ItemStatus.rejected]
    constraints = [c for c in state.constraints if c.status != ItemStatus.rejected]
    lines += ["## Proposed Approach", ""]
    if decisions or constraints:
        for d in decisions:
            lines.append(f"- **{d.topic}:** {d.choice}{_mark(d.status)}")
            if d.reason:
                lines.append(f"  - _Why:_ {d.reason}")
        for c in constraints:
            lines.append(f"- _Constraint:_ {c.description}{_mark(c.status)}")
    else:
        lines.append("_No approach defined yet._")
    lines.append("")

    open_qs = [q for q in state.openQuestions if q.status == QuestionStatus.open]
    lines += ["## Open Questions / Risks", ""]
    if open_qs:
        lines += [f"- {q.question}" for q in open_qs]
    else:
        lines.append("_No open questions._")

    return "\n".join(lines).rstrip() + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_render.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/models/render.py tests/test_render.py
git commit -m "Add design doc markdown renderer"
```

---

### Task 3: Provider abstraction + FakeProvider

**Files:**
- Create: `backend/providers/__init__.py`, `backend/providers/base.py`
- Create: `tests/fakes/__init__.py`, `tests/fakes/provider.py`
- Test: `tests/test_fake_provider.py`

**Interfaces:**
- Produces: `Message(role: str, content: str)` dataclass; `Provider` ABC with `complete(messages: list[Message]) -> str`; `FakeProvider(responses: list[str])` recording `.calls: list[list[Message]]`.

- [ ] **Step 1: Create empty package files**

Create `backend/providers/__init__.py` and `tests/fakes/__init__.py` as empty files.

- [ ] **Step 2: Write the failing test**

Create `tests/test_fake_provider.py`:

```python
import pytest

from backend.providers.base import Message
from tests.fakes.provider import FakeProvider


def test_fake_returns_scripted_responses_in_order():
    fake = FakeProvider(["first", "second"])
    assert fake.complete([Message(role="user", content="hi")]) == "first"
    assert fake.complete([Message(role="user", content="again")]) == "second"


def test_fake_records_calls():
    fake = FakeProvider(["ok"])
    fake.complete([Message(role="user", content="hello")])
    assert fake.calls[0][0].content == "hello"


def test_fake_raises_when_exhausted():
    fake = FakeProvider([])
    with pytest.raises(AssertionError):
        fake.complete([Message(role="user", content="x")])
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_fake_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.providers.base'`

- [ ] **Step 4: Implement `backend/providers/base.py`**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


class Provider(ABC):
    @abstractmethod
    def complete(self, messages: list[Message]) -> str:
        """Return the model's text completion for the given messages."""
        raise NotImplementedError
```

- [ ] **Step 5: Implement `tests/fakes/provider.py`**

```python
from backend.providers.base import Message, Provider


class FakeProvider(Provider):
    """Deterministic provider for tests: returns scripted responses in order."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls: list[list[Message]] = []

    def complete(self, messages: list[Message]) -> str:
        self.calls.append(list(messages))
        if not self._responses:
            raise AssertionError("FakeProvider ran out of scripted responses")
        return self._responses.pop(0)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_fake_provider.py -v`
Expected: PASS (3 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/providers/ tests/fakes/ tests/test_fake_provider.py
git commit -m "Add provider abstraction and FakeProvider"
```

---

### Task 4: OpenRouter provider

**Files:**
- Create: `backend/providers/openrouter.py`
- Test: `tests/test_openrouter_provider.py`

**Interfaces:**
- Consumes: `Message`, `Provider` from Task 3.
- Produces: `OpenRouterProvider(api_key=None, model=None, timeout=60.0)` implementing `complete`. Reads `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` from env when args omitted.

- [ ] **Step 1: Write the failing test**

Create `tests/test_openrouter_provider.py`:

```python
import httpx

from backend.providers.base import Message
from backend.providers.openrouter import OpenRouterProvider


def test_complete_posts_and_parses_response(monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "hello from model"}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    provider = OpenRouterProvider(api_key="test-key", model="test-model")
    out = provider.complete([Message(role="user", content="hi")])

    assert out == "hello from model"
    assert captured["json"]["model"] == "test-model"
    assert captured["json"]["messages"] == [{"role": "user", "content": "hi"}]
    assert captured["headers"]["Authorization"] == "Bearer test-key"


def test_reads_key_and_model_from_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "env-model")
    provider = OpenRouterProvider()
    assert provider.api_key == "env-key"
    assert provider.model == "env-model"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_openrouter_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.providers.openrouter'`

- [ ] **Step 3: Implement `backend/providers/openrouter.py`**

```python
import os

import httpx

from backend.providers.base import Message, Provider

DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"


class OpenRouterProvider(Provider):
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ):
        self.api_key = api_key or os.environ["OPENROUTER_API_KEY"]
        self.model = model or os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
        self.timeout = timeout

    def complete(self, messages: list[Message]) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = httpx.post(
            self.BASE_URL, json=payload, headers=headers, timeout=self.timeout
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_openrouter_provider.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/providers/openrouter.py tests/test_openrouter_provider.py
git commit -m "Add OpenRouter provider"
```

---

### Task 5: Edit ops, apply_edits, agent base

**Files:**
- Create: `backend/agents/__init__.py`, `backend/agents/base.py`
- Test: `tests/test_apply_edits.py`

**Interfaces:**
- Consumes: session models from Task 1; `Message` from Task 3.
- Produces: edit-op models `SetSummaryOp`, `SetStageOp`, `AddRequirementOp`, `AddConstraintOp`, `AddDecisionOp`, `AnswerQuestionOp`; union `EditOp`; `AgentTurn(proposed_edits: list[EditOp], next_question: str | None, done: bool)`; `AgentOutputError`; `apply_edits(state, edits, source) -> list[str]`; `register_question(state, question, asked_by="pm") -> str`; `Agent` ABC with `name: str` and `contribute(state, history) -> AgentTurn`.

- [ ] **Step 1: Create empty package file**

Create `backend/agents/__init__.py` as an empty file.

- [ ] **Step 2: Write the failing test**

Create `tests/test_apply_edits.py`:

```python
from backend.models.session_state import SessionState, ItemStatus, QuestionStatus, ProjectStage
from backend.agents.base import (
    apply_edits, register_question,
    SetSummaryOp, SetStageOp, AddRequirementOp, AddDecisionOp, AnswerQuestionOp,
)


def test_add_requirement_assigns_id_and_forces_proposed():
    s = SessionState.new("sess-1")
    apply_edits(s, [AddRequirementOp(op="add_requirement", description="do X")], source="pm")
    assert len(s.requirements) == 1
    assert s.requirements[0].id == "req-1"
    assert s.requirements[0].status == ItemStatus.proposed
    assert s.requirements[0].source == "pm"


def test_ids_increment_per_type():
    s = SessionState.new("sess-1")
    apply_edits(s, [
        AddRequirementOp(op="add_requirement", description="a"),
        AddRequirementOp(op="add_requirement", description="b"),
    ], source="pm")
    assert [r.id for r in s.requirements] == ["req-1", "req-2"]


def test_set_summary_and_stage():
    s = SessionState.new("sess-1")
    apply_edits(s, [
        SetSummaryOp(op="set_summary", summary="a reminder app"),
        SetStageOp(op="set_stage", stage="requirements"),
    ], source="pm")
    assert s.project.summary == "a reminder app"
    assert s.project.currentStage == ProjectStage.requirements


def test_add_decision_records_proposed_by():
    s = SessionState.new("sess-1")
    apply_edits(s, [
        AddDecisionOp(op="add_decision", topic="Platform", choice="Mobile", reason="push"),
    ], source="pm")
    d = s.decisions[0]
    assert d.id == "dec-1"
    assert d.proposedBy == "pm"
    assert d.approvedBy is None
    assert d.status == ItemStatus.proposed


def test_answer_question_resolves_open_question():
    s = SessionState.new("sess-1")
    qid = register_question(s, "How many kids?", asked_by="pm")
    assert qid == "q-1"
    apply_edits(s, [AnswerQuestionOp(op="answer_question", id="q-1", answer="two")], source="user")
    assert s.openQuestions[0].status == QuestionStatus.answered
    assert s.openQuestions[0].answer == "two"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_apply_edits.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.agents.base'`

- [ ] **Step 4: Implement `backend/agents/base.py`**

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_apply_edits.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/agents/ tests/test_apply_edits.py
git commit -m "Add edit-ops, apply_edits, and agent base interface"
```

---

### Task 6: PM agent (parse, invariants, repair)

**Files:**
- Create: `backend/agents/pm.py`
- Test: `tests/test_pm_agent.py`

**Interfaces:**
- Consumes: `Agent`, `AgentTurn`, `AgentOutputError`, `EditOp` from Task 5; `Provider`, `Message` from Task 3; session models from Task 1.
- Produces: `parse_agent_turn(raw: str) -> AgentTurn` (module-level); `ProjectManager(provider: Provider)` with `name = "pm"` implementing `contribute`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_pm_agent.py`:

```python
import pytest

from backend.models.session_state import SessionState
from backend.agents.base import AgentOutputError, AddRequirementOp
from backend.agents.pm import parse_agent_turn, ProjectManager
from tests.fakes.provider import FakeProvider


def test_parse_extracts_edits_and_question():
    raw = '{"edits": [{"op": "add_requirement", "description": "notify user"}], "question": "Who is the user?", "done": false}'
    turn = parse_agent_turn(raw)
    assert isinstance(turn.proposed_edits[0], AddRequirementOp)
    assert turn.next_question == "Who is the user?"
    assert turn.done is False


def test_parse_strips_markdown_fences_and_prose():
    raw = 'Sure!\n```json\n{"edits": [], "question": "What next?", "done": false}\n```'
    turn = parse_agent_turn(raw)
    assert turn.next_question == "What next?"
    assert turn.proposed_edits == []


def test_parse_collapses_multiple_questions_to_one():
    raw = '{"edits": [], "question": "Who uses it? How often? Where?", "done": false}'
    turn = parse_agent_turn(raw)
    assert turn.next_question == "Who uses it?"


def test_parse_blank_question_becomes_none():
    raw = '{"edits": [], "question": "", "done": true}'
    turn = parse_agent_turn(raw)
    assert turn.next_question is None
    assert turn.done is True


def test_parse_raises_on_garbage():
    with pytest.raises(AgentOutputError):
        parse_agent_turn("this is not json at all")


def test_contribute_repairs_once_then_succeeds():
    fake = FakeProvider([
        "not json",
        '{"edits": [], "question": "Recovered?", "done": false}',
    ])
    pm = ProjectManager(fake)
    turn = pm.contribute(SessionState.new("sess-1"), [])
    assert turn.next_question == "Recovered?"
    assert len(fake.calls) == 2


def test_contribute_raises_if_repair_also_fails():
    fake = FakeProvider(["nope", "still nope"])
    pm = ProjectManager(fake)
    with pytest.raises(AgentOutputError):
        pm.contribute(SessionState.new("sess-1"), [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pm_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.agents.pm'`

- [ ] **Step 3: Implement `backend/agents/pm.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pm_agent.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/agents/pm.py tests/test_pm_agent.py
git commit -m "Add PM agent with JSON parsing, one-question invariant, and repair retry"
```

---

### Task 7: Conversation loop (turns, approve/reject, save)

**Files:**
- Create: `backend/core/__init__.py`, `backend/core/loop.py`
- Test: `tests/test_loop.py`

**Interfaces:**
- Consumes: PM agent from Task 6; `apply_edits`/`register_question` from Task 5; renderer from Task 2; session models from Task 1; `Provider`/`Message` from Task 3.
- Produces: `TurnResult(changes: list[str], question: str | None, question_id: str | None, done: bool)`; `Conversation(provider, agent=None, session_id="sess-1")` with `.state`, `.history`, methods `send(user_input) -> TurnResult`, `approve(item_id) -> bool`, `reject(item_id) -> bool`, `save() -> Artifact`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_loop.py`:

```python
from backend.core.loop import Conversation
from backend.models.session_state import ItemStatus, ProjectStatus
from tests.fakes.provider import FakeProvider


def test_send_applies_edits_and_registers_question():
    fake = FakeProvider([
        '{"edits": [{"op": "set_summary", "summary": "reminder app"}], '
        '"question": "Who is the primary user?", "done": false}'
    ])
    convo = Conversation(fake)
    result = convo.send("A library due-date reminder app")
    assert convo.state.project.summary == "reminder app"
    assert result.question == "Who is the primary user?"
    assert result.question_id == "q-1"
    assert convo.state.openQuestions[0].question == "Who is the primary user?"
    # history holds the user turn and the assistant question
    assert convo.history[0].content == "A library due-date reminder app"
    assert convo.history[-1].content == "Who is the primary user?"


def test_approve_promotes_requirement():
    fake = FakeProvider([
        '{"edits": [{"op": "add_requirement", "description": "notify parent"}], '
        '"question": "How many kids?", "done": false}'
    ])
    convo = Conversation(fake)
    convo.send("reminder app")
    assert convo.state.requirements[0].status == ItemStatus.proposed
    assert convo.approve("req-1") is True
    assert convo.state.requirements[0].status == ItemStatus.approved


def test_approve_unknown_id_returns_false():
    convo = Conversation(FakeProvider([]))
    assert convo.approve("req-99") is False


def test_reject_marks_rejected():
    fake = FakeProvider([
        '{"edits": [{"op": "add_requirement", "description": "spurious"}], '
        '"question": "ok?", "done": false}'
    ])
    convo = Conversation(fake)
    convo.send("app")
    assert convo.reject("req-1") is True
    assert convo.state.requirements[0].status == ItemStatus.rejected


def test_save_appends_artifact_and_bumps_version():
    fake = FakeProvider([
        '{"edits": [{"op": "set_summary", "summary": "an app"}], "question": "q?", "done": false}'
    ])
    convo = Conversation(fake)
    convo.send("app")
    art1 = convo.save()
    assert art1.version == 1
    assert "an app" in art1.content
    assert convo.state.project.status == ProjectStatus.saved
    art2 = convo.save()
    assert art2.version == 2
    assert len(convo.state.artifacts) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_loop.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.core.loop'`

- [ ] **Step 3: Create empty package file**

Create `backend/core/__init__.py` as an empty file.

- [ ] **Step 4: Implement `backend/core/loop.py`**

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_loop.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/core/ tests/test_loop.py
git commit -m "Add conversation loop with turns, approve/reject, and save"
```

---

### Task 8: Replay CLI (scripted transcripts)

**Files:**
- Create: `backend/cli/__init__.py`, `backend/cli/replay.py`
- Create: `tests/evals/__init__.py`, `tests/evals/transcripts/library.json`
- Test: `tests/test_replay.py`

**Interfaces:**
- Consumes: `Conversation` from Task 7; `Provider` from Task 3.
- Produces: `run_transcript(transcript: dict, provider) -> Conversation` (drives `send` for the idea then each answer, calls `save` at end); `load_transcript(path) -> dict`; `main(argv=None)` CLI entry defaulting to `OpenRouterProvider`.

Transcript format: `{"idea": str, "answers": [str, ...]}`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_replay.py`:

```python
from backend.cli.replay import run_transcript
from backend.models.session_state import ProjectStatus
from tests.fakes.provider import FakeProvider


def test_run_transcript_drives_idea_then_answers_and_saves():
    fake = FakeProvider([
        '{"edits": [{"op": "set_summary", "summary": "reminder app"}], "question": "Who uses it?", "done": false}',
        '{"edits": [{"op": "add_requirement", "description": "notify parents"}], "question": "", "done": true}',
    ])
    transcript = {"idea": "a reminder app", "answers": ["parents"]}
    convo = run_transcript(transcript, fake)

    assert convo.state.project.summary == "reminder app"
    assert convo.state.requirements[0].description == "notify parents"
    # idea + one answer = 2 provider calls
    assert len(fake.calls) == 2
    # transcript run saves at the end
    assert convo.state.project.status == ProjectStatus.saved
    assert convo.state.artifacts[-1].version == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_replay.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.cli.replay'`

- [ ] **Step 3: Create package + fixture files**

Create `backend/cli/__init__.py` and `tests/evals/__init__.py` as empty files. Create `tests/evals/transcripts/library.json`:

```json
{
  "idea": "A mobile app that reminds parents when their kids' library books are due.",
  "answers": [
    "The parent is the primary user; a family tracks about five books at once.",
    "Manual entry and barcode scan both, but manual entry is the must-have for v1.",
    "Success means zero late fees for a family over a school term."
  ]
}
```

- [ ] **Step 4: Implement `backend/cli/replay.py`**

```python
from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from backend.core.loop import Conversation
from backend.models.render import render_design_doc
from backend.providers.base import Provider


def load_transcript(path: str) -> dict:
    return json.loads(Path(path).read_text())


def run_transcript(transcript: dict, provider: Provider) -> Conversation:
    convo = Conversation(provider)
    convo.send(transcript["idea"])
    for answer in transcript.get("answers", []):
        convo.send(answer)
    convo.save()
    return convo


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m backend.cli.replay <transcript.json>")
        return 1
    from backend.providers.openrouter import OpenRouterProvider

    transcript = load_transcript(argv[0])
    convo = run_transcript(transcript, OpenRouterProvider())
    print(render_design_doc(convo.state))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_replay.py -v`
Expected: PASS (1 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/cli/__init__.py backend/cli/replay.py tests/evals/__init__.py tests/evals/transcripts/library.json tests/test_replay.py
git commit -m "Add replay CLI and scripted transcript runner"
```

---

### Task 9: Interactive REPL CLI

**Files:**
- Create: `backend/cli/repl.py`
- Test: `tests/test_repl.py`

**Interfaces:**
- Consumes: `Conversation` from Task 7; renderer from Task 2.
- Produces: `parse_command(line: str) -> tuple[str, str]` (returns `(command, argument)`; a leading-slash or bareword among the known commands is a command, otherwise `("say", line)`); `handle_command(convo, command, arg) -> str` returning display text (does not read stdin); `main(argv=None)` running the input loop.

Known commands: `approve`, `reject`, `doc`, `save`, `quit`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_repl.py`:

```python
from backend.cli.repl import parse_command, handle_command
from backend.core.loop import Conversation
from tests.fakes.provider import FakeProvider


def test_parse_command_recognizes_known_commands():
    assert parse_command("approve req-1") == ("approve", "req-1")
    assert parse_command("/approve req-1") == ("approve", "req-1")
    assert parse_command("save out.md") == ("save", "out.md")
    assert parse_command("doc") == ("doc", "")
    assert parse_command("quit") == ("quit", "")


def test_parse_command_treats_prose_as_say():
    assert parse_command("A reminder app for parents") == ("say", "A reminder app for parents")


def test_handle_approve_promotes_item():
    fake = FakeProvider([
        '{"edits": [{"op": "add_requirement", "description": "notify"}], "question": "q?", "done": false}'
    ])
    convo = Conversation(fake)
    convo.send("app")
    out = handle_command(convo, "approve", "req-1")
    assert "req-1" in out
    assert convo.state.requirements[0].status.value == "approved"


def test_handle_doc_returns_markdown():
    convo = Conversation(FakeProvider([]))
    out = handle_command(convo, "doc", "")
    assert "## Overview" in out


def test_handle_save_writes_file(tmp_path):
    convo = Conversation(FakeProvider([]))
    target = tmp_path / "design.md"
    out = handle_command(convo, "save", str(target))
    assert target.exists()
    assert "# " in target.read_text()
    assert str(target) in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_repl.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.cli.repl'`

- [ ] **Step 3: Implement `backend/cli/repl.py`**

```python
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

from backend.core.loop import Conversation
from backend.models.render import render_design_doc

KNOWN_COMMANDS = {"approve", "reject", "doc", "save", "quit"}


def parse_command(line: str) -> tuple[str, str]:
    stripped = line.strip()
    token = stripped[1:] if stripped.startswith("/") else stripped
    head, _, rest = token.partition(" ")
    if head in KNOWN_COMMANDS:
        return head, rest.strip()
    return "say", stripped


def handle_command(convo: Conversation, command: str, arg: str) -> str:
    if command == "approve":
        ok = convo.approve(arg)
        return f"approved {arg}" if ok else f"no such item: {arg}"
    if command == "reject":
        ok = convo.reject(arg)
        return f"rejected {arg}" if ok else f"no such item: {arg}"
    if command == "doc":
        return render_design_doc(convo.state)
    if command == "save":
        art = convo.save()
        target = Path(arg) if arg else Path("design.md")
        target.write_text(art.content)
        return f"saved v{art.version} to {target}"
    return f"unknown command: {command}"


def _say(convo: Conversation, text: str) -> str:
    result = convo.send(text)
    lines = []
    for change in result.changes:
        lines.append(f"  · {change}")
    if result.question:
        lines.append(f"\nPM: {result.question}")
    if result.done:
        lines.append("\nPM: I think the design is well-formed. Type `save` to export.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    from backend.providers.openrouter import OpenRouterProvider

    convo = Conversation(OpenRouterProvider())
    print("BlueprintAI — Project Manager (terminal). Describe what you want to build.")
    print("Commands: approve <id>, reject <id>, doc, save [file], quit\n")
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        command, arg = parse_command(line)
        if command == "quit":
            return 0
        if command == "say":
            if not arg:
                continue
            print(_say(convo, arg))
        else:
            print(handle_command(convo, command, arg))


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_repl.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/cli/repl.py tests/test_repl.py
git commit -m "Add interactive REPL CLI"
```

---

### Task 10: Evaluation harness (LLM-as-judge)

**Files:**
- Create: `tests/evals/rubric.md`
- Create: `tests/evals/judge.py`
- Test: `tests/test_judge.py`

**Interfaces:**
- Consumes: `Conversation` from Task 7; `Provider`/`Message` from Task 3.
- Produces: `transcript_to_text(convo) -> str`; `score_transcript(convo, rubric, provider) -> dict` (returns `{"scores": {dimension: int}, "notes": str}`, parsed from judge JSON); `RUBRIC_PATH` constant; `main(argv=None)` running a real transcript then judging it.

- [ ] **Step 1: Write the failing test**

Create `tests/test_judge.py`:

```python
from backend.core.loop import Conversation
from tests.evals.judge import transcript_to_text, score_transcript
from tests.fakes.provider import FakeProvider


def _convo_with_one_turn() -> Conversation:
    fake = FakeProvider([
        '{"edits": [{"op": "set_summary", "summary": "reminder app"}], '
        '"question": "Who is the primary user?", "done": false}'
    ])
    convo = Conversation(fake)
    convo.send("A library reminder app")
    return convo


def test_transcript_to_text_includes_user_and_pm_turns():
    text = transcript_to_text(_convo_with_one_turn())
    assert "A library reminder app" in text
    assert "Who is the primary user?" in text


def test_score_transcript_parses_judge_json():
    judge = FakeProvider([
        '{"scores": {"one_question_per_turn": 5, "relevance": 4, '
        '"coverage": 3, "grounding": 5, "convergence": 4}, "notes": "solid"}'
    ])
    result = score_transcript(_convo_with_one_turn(), "RUBRIC TEXT", judge)
    assert result["scores"]["relevance"] == 4
    assert result["notes"] == "solid"
    # the judge was given both the rubric and the transcript
    sent = judge.calls[0][-1].content
    assert "RUBRIC TEXT" in sent
    assert "Who is the primary user?" in sent
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_judge.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tests.evals.judge'`

- [ ] **Step 3: Create `tests/evals/rubric.md`**

```markdown
# PM Agent Evaluation Rubric

Score each dimension 1 (poor) to 5 (excellent). Judge the transcript as a whole.

1. **one_question_per_turn** — Did the PM ask exactly one focused question each turn,
   never bundling several?
2. **relevance** — Did each question meaningfully advance scoping of the idea?
3. **coverage** — Across the conversation, did the PM probe purpose, users,
   constraints, and success criteria?
4. **grounding** — Are the proposed requirements/decisions faithful to what the user
   actually said, with no invented facts?
5. **convergence** — Did the conversation move toward a coherent, well-formed design
   without dragging or looping?
```

- [ ] **Step 4: Implement `tests/evals/judge.py`**

```python
from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.core.loop import Conversation
from backend.providers.base import Message, Provider

RUBRIC_PATH = Path(__file__).parent / "rubric.md"

_JUDGE_SYSTEM = (
    "You are an evaluator scoring a Project Manager agent's design conversation. "
    "Apply the rubric and respond with ONLY a JSON object of the form "
    '{"scores": {"<dimension>": <int 1-5>, ...}, "notes": "<short critique>"}.'
)


def transcript_to_text(convo: Conversation) -> str:
    lines = []
    for m in convo.history:
        speaker = "User" if m.role == "user" else "PM"
        lines.append(f"{speaker}: {m.content}")
    return "\n".join(lines)


def score_transcript(convo: Conversation, rubric: str, provider: Provider) -> dict:
    transcript = transcript_to_text(convo)
    prompt = (
        f"RUBRIC:\n{rubric}\n\n"
        f"TRANSCRIPT:\n{transcript}\n\n"
        "Score every rubric dimension now."
    )
    raw = provider.complete([
        Message(role="system", content=_JUDGE_SYSTEM),
        Message(role="user", content=prompt),
    ])
    start, end = raw.find("{"), raw.rfind("}")
    return json.loads(raw[start:end + 1])


def main(argv: list[str] | None = None) -> int:
    from dotenv import load_dotenv

    from backend.cli.replay import load_transcript, run_transcript
    from backend.providers.openrouter import OpenRouterProvider

    load_dotenv()
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m tests.evals.judge <transcript.json>")
        return 1
    provider = OpenRouterProvider()
    convo = run_transcript(load_transcript(argv[0]), provider)
    result = score_transcript(convo, RUBRIC_PATH.read_text(), provider)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_judge.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: PASS (all tasks' tests green)

- [ ] **Step 7: Commit**

```bash
git add tests/evals/rubric.md tests/evals/judge.py tests/test_judge.py
git commit -m "Add LLM-as-judge evaluation harness"
```

---

## Manual verification (after all tasks, requires real key)

These require a real `OPENROUTER_API_KEY` in `.env` and are not part of the automated suite:

1. **Interactive REPL:** `python -m backend.cli.repl` → type an idea → confirm the PM asks one question at a time, proposed edits print, `doc` shows the growing markdown, `save design.md` writes a file.
2. **Scripted replay:** `python -m backend.cli.replay tests/evals/transcripts/library.json` → confirm a coherent design doc prints.
3. **Eval:** `python -m tests.evals.judge tests/evals/transcripts/library.json` → confirm a JSON score report prints across all five rubric dimensions.

---

## Self-Review Notes

- **Spec coverage:** provider abstraction (T3/T4), FakeProvider in tests only (T3), PM agent + JSON-in-prompt + one-question invariant + repair (T6), edit-ops defined here (T5), proposed-status enforcement (T5), shared loop (T7), REPL + replay CLIs (T8/T9), Testing A structural suite (T1–T9), Testing B eval harness under `tests/evals/` (T10), render + save/version (T2/T7), keys server-side via dotenv (T4/T8/T9). No frontend/SSE/Postgres/LangGraph — matches non-goals.
- **Provider injection:** `Conversation`, `run_transcript`, and `score_transcript` all take a provider argument; only `main()` entry points import `OpenRouterProvider`. `FakeProvider` never appears in `backend/`.
- **Type consistency:** `AgentTurn`, `EditOp` op-names, `TurnResult`, and `Conversation` method names are consistent across Tasks 5–10.
