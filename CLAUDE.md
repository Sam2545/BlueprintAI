# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

BlueprintAI is an interactive multi-agent workspace for turning software ideas into reviewed, actionable project plans. A user enters a single idea ("What do you want to build?"), a team of AI agents guides them through a human-in-the-loop design conversation, and the result is a saved, shareable Markdown design document (proposal + tasks + milestones).

See `docs/productFlow.md` for the intended user experience (the happy path). This CLAUDE.md is the build guide and milestone plan.

## Core Design Principles

- **Start with one agent, grow to a delegator.** The MVP runs entirely on a single Project Manager agent. Specialists (Architect, Implementation Lead, Reviewer) are added one at a time, each independently testable, until the PM becomes a delegating orchestrator. Do not build the full multi-agent graph up front.
- **One agent interface.** Every agent implements the same small interface (e.g. `contribute(doc, history) -> proposed_edits + next_question`) so the LangGraph graph can grow without rewrites.
- **Model-provider abstraction.** Never call an LLM provider SDK directly from agent code. All model calls go through a provider abstraction. Default provider is **OpenRouter** (free/cheap open-source models — Llama, Qwen, DeepSeek); **Groq** is a drop-in alternative. Swapping providers must not touch agent logic.
- **Keys live server-side only.** The Next.js frontend never sees model API keys. It talks only to the FastAPI backend, which owns the keys and makes all model calls.
- **Human in the loop.** Agents propose edits to the design doc; the user always sees changes in the live preview before they're final. Nothing is written silently.
- **One question at a time.** Agents ask a single focused question per turn — never overwhelm the user.

## Architecture

Monorepo with two apps plus an agent core:

```
BlueprintAI/
├── frontend/            Next.js + TypeScript + Tailwind CSS + shadcn/ui
├── backend/             FastAPI + Pydantic + SQLAlchemy + Alembic
│   ├── agents/          custom agent classes + LangGraph orchestration graph
│   └── providers/       model-provider abstraction (OpenRouter default, Groq alt)
├── docker-compose.yml   frontend + backend + postgres
└── docs/productFlow.md  the happy-path user experience
```

**Data flow:** Frontend renders a two-pane workspace (chat stream on the left, live design-document preview on the right). It calls the backend, which runs the active agent(s) via LangGraph and **streams tokens/events back over Server-Sent Events (SSE)**. Sessions, messages, and the evolving design doc are persisted to Postgres. WebSockets may replace SSE later if bidirectional needs arise.

**Data model (MVP, keep small):**
- `Session` — the idea, status.
- `Message` — role, agent, content.
- `DesignDoc` — markdown body, version.

## Milestones

Build in this order. Each milestone should be independently runnable and tested before moving on.

- **M0 — Scaffold.** Monorepo skeleton, Docker Compose (frontend + backend + postgres), FastAPI health endpoint, Next.js landing page, Alembic wired up. `docker compose up` brings the stack online.
- **M1 — Single PM agent, end to end (the MVP).** Landing "What do you want to build?" → workspace with chat + live doc preview → Project Manager agent (via provider abstraction + LangGraph single-node graph) runs the full guided Q&A → design doc builds live via SSE → **Save/Export** produces a shareable `.md`. This delivers the entire happy path in `docs/productFlow.md`.
- **M2 — Add the Architect.** Second agent behind the same interface; introduce a real LangGraph handoff (PM → Architect). Independently tested.
- **M3 — Add the Implementation Lead.** Turns the approach into concrete tasks and milestones in the doc.
- **M4 — Add the Reviewer.** Critiques the doc for gaps/risks before save.
- **M5 — Delegator.** PM becomes the user-facing orchestrator that routes to specialists via LangGraph and merges their contributions into one coherent document.

## Commands

> The repository is currently at initial scaffolding. Fill these in as each tool lands (M0), then keep them accurate.

- **Whole stack:** `docker compose up` — _to be added in M0._
- **Backend (FastAPI):** run server, run migrations (`alembic upgrade head`), tests (`pytest`, single test `pytest path::test_name`) — _to be added in M0/M1._
- **Frontend (Next.js):** dev server, unit tests (Vitest), e2e (Playwright) — _to be added in M0/M1._

## Testing

- **Backend:** pytest. Agent logic must be testable without live model calls — mock the provider abstraction so agent behavior is deterministic in tests.
- **Frontend:** Vitest for units, Playwright for the end-to-end happy path (landing → guided conversation → save).
