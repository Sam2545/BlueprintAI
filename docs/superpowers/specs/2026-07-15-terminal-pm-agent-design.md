# Design Spec — Terminal PM Agent (M1a)

**Date:** 2026-07-15
**Milestone:** M1a (single PM agent, terminal-first, no frontend)
**Status:** Approved for implementation planning
**Builds on:** [`docs/sessionModel.md`](../../sessionModel.md) (the session state model)

## Problem

M1 is the MVP: a single Project Manager agent that guides a user from a raw idea to a
saved design document. Before adding a web UI, we build and prove the agent **entirely
in the terminal**, with a real way to test that its output is correct. This slice
delivers a working PM agent, a model-provider abstraction, and a two-layer testing
approach (deterministic structural tests + a real-model evaluation harness).

## Goals

- A single PM agent that runs the guided, one-question-at-a-time Q&A over the session
  state model.
- Runs two ways from one shared loop: an **interactive REPL** and a **scripted replay**.
- **Save/Export** renders the state to a shareable `.md`.
- **Testing A (structural):** deterministic pytest suite, no live model calls.
- **Testing B (evaluation):** a real-model LLM-as-judge harness to experiment with
  evaluating output quality.

## Non-goals (deferred)

No frontend, no FastAPI/SSE, no Postgres/Alembic, no LangGraph. Session state lives in
memory; `save` writes files. The agent interface is shaped so LangGraph and the web
layer (M1b) slot in later without changing agent logic.

## Architecture

`backend/` contains only product source. All mock/fake/test/eval code lives under
`tests/`.

```
backend/
├── models/
│   ├── session_state.py   # Pydantic models from docs/sessionModel.md
│   └── render.py          # render_design_doc(state) -> markdown
├── providers/
│   ├── base.py            # Provider ABC: complete(messages) -> str
│   └── openrouter.py      # OpenRouterProvider (reads OPENROUTER_API_KEY)
├── agents/
│   ├── base.py            # Agent interface + AgentTurn / EditOp types
│   └── pm.py              # ProjectManager agent
├── core/
│   └── loop.py            # one conversation loop; provider injected in
└── cli/
    ├── repl.py            # interactive entry point
    └── replay.py          # scripted-transcript entry point

tests/
├── fakes/
│   └── provider.py        # FakeProvider (canned responses, no keys)
├── evals/
│   ├── transcripts/       # fixture conversations (idea + user answers)
│   ├── judge.py           # LLM-as-judge rubric scorer (Testing B)
│   └── rubric.md          # the eval rubric (experiment here)
├── test_pm_agent.py       # structural tests (Testing A)
├── test_render.py
└── test_loop.py           # injects FakeProvider
```

## Components

### Provider abstraction (`providers/`)

- `base.py`: a minimal ABC — `complete(messages: list[Message]) -> str`. Nothing
  agent-specific leaks in. Swapping providers never touches agent code.
- `openrouter.py`: `OpenRouterProvider` reads `OPENROUTER_API_KEY` from a git-ignored
  `.env` (keys stay server-side). Targets a free model, default
  `meta-llama/llama-3.3-70b-instruct:free`, overridable via env.
- Testing uses `FakeProvider` (in `tests/fakes/`) which returns pre-scripted strings —
  injected into the loop/agent, so no keys or tokens are needed for structural tests or
  deterministic scripted runs.

### PM agent (`agents/`)

- Implements the standard interface: `contribute(state, history) -> AgentTurn`.
- `AgentTurn = { proposed_edits: list[EditOp], next_question: str | None, done: bool }`.
- Each turn, the agent prompts the model to return **JSON**
  (`{"edits": [...], "question": "...", "done": false}`) — JSON-in-prompt, not
  tool-calling, since free open models handle it most reliably and it stays
  provider-agnostic.
- The JSON is parsed and validated into typed `EditOp`s. **This slice defines the
  edit-op set** (deferred from the model slice):
  `set_summary`, `set_stage`, `add_requirement`, `add_constraint`, `add_decision`,
  `answer_question`.
- Malformed JSON → one repair retry, then a clean, tested error.

**Invariants enforced in code, not left to the model:**
1. Exactly **one** question per turn (extra questions dropped/collapsed).
2. Every agent-created item is forced to `status: proposed` (`open` for questions).
   The model can misbehave; the agent still cannot violate the human-in-the-loop
   contract.

### Core loop (`core/loop.py`)

Drives one turn: take user input → `agent.contribute()` → apply edits to state as
`proposed` → print the proposed changes + next question. The provider is injected, so
both CLIs and the tests share this identical loop. This is what makes scripted mode a
true test of the real interaction.

### Entry points (`cli/`)

- `repl.py` — `python -m backend.cli.repl`. Type the idea, converse, watch proposed
  edits appear. Commands:
  `approve <id>` / `approve all`, `reject <id>`, `doc` (print rendered markdown),
  `save [file]` (export state → `.md`), `quit`. Defaults to `OpenRouterProvider`.
- `replay.py` — `python -m backend.cli.replay <transcript.json>`. Feeds a fixed idea +
  user answers through the same loop non-interactively; prints final state + doc.
  Defaults to `OpenRouterProvider` (for producing real transcripts that feed Testing B).
  Tests drive the same loop with an injected `FakeProvider` for deterministic runs.

### Human-in-the-loop (terminal)

Proposed edits are applied as `proposed` and shown each turn. The user promotes them
with `approve <id>` / `approve all` or drops them with `reject <id>`. `save` exports the
current state. This keeps HITL real but lightweight for a terminal MVP.

## Testing A — structural, deterministic (pytest + FakeProvider)

CI-able, no keys, never flaky. Covers:
- One-question-per-turn invariant holds regardless of model output.
- Agent-created items always land as `proposed` / `open`.
- Malformed-JSON handling (repair retry, then clean error).
- IDs are well-formed and server-assigned (not model-invented).
- State stays schema-valid across a scripted conversation.
- `render_design_doc` golden-file output.
- `save` appends an `Artifact` and bumps `version`.

These guarantee the agent **behaves correctly** no matter what the model says.

## Testing B — evaluation harness (real model, LLM-as-judge)

`replay.py` with `OpenRouterProvider` produces a real transcript → `tests/evals/judge.py`
scores it against `tests/evals/rubric.md` using the model as judge, emitting a score +
notes per dimension. Starter rubric (designed to be iterated on):

1. **One question per turn** — also checked structurally, cross-validating the judge.
2. **Question relevance** — does each question advance scoping?
3. **Coverage** — did it probe purpose / users / constraints / success criteria?
4. **Grounding** — are proposed requirements faithful to what the user said (no
   hallucination)?
5. **Convergence** — did it reach a coherent doc without dragging?

Output is a small scored report to eyeball. This is a **spot-check tool**, explicitly
not a pass/fail CI gate. The harness is structured so the rubric, transcripts, and judge
prompt can all be edited to experiment with what makes a good evaluation.

## Key decisions

1. **Provider injected as a dependency**, not imported concretely — this is what lets
   `FakeProvider` live entirely in `tests/` while the CLIs default to the real provider.
2. **JSON-in-prompt for structured output**, not tool-calling — most reliable across
   free open models and provider-agnostic.
3. **HITL invariants enforced in agent code**, never trusted to the model.
4. **Two testing layers, different jobs:** A proves correct *behavior* deterministically;
   B spot-checks output *quality* with a real model. B is a tool, not a gate.
5. **State in memory for M1a**; persistence, SSE, web UI, and LangGraph are M1b+.

## Open defaults (revisit at review)

- HITL depth: `approve`/`reject` commands (could go lighter — auto-approve — or heavier).
- The five-dimension starter rubric for Testing B.
