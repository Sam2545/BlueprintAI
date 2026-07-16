# Design Spec — Session State Model (M1)

**Date:** 2026-07-15
**Milestone:** M1 (single PM agent, MVP) — foundational data model slice
**Status:** Approved for documentation; implementation deferred

## Problem

BlueprintAI needs a well-defined **shared project state** for every session: the
structured object agents read and write as a user designs their project. Without it,
agents would have to re-parse free-text markdown every turn, and human-in-the-loop
approval would have nowhere to live. This spec defines that model.

## Scope

**In scope:** the data model — the shape of the per-session JSON, its entities,
fields, enums, id conventions, and the human-in-the-loop status semantics. Delivered
as documentation (`docs/sessionModel.md`) and this spec.

**Out of scope (deferred, "technical details for later"):**
- The `render_design_doc(state) -> markdown` projection function.
- The agent edit-op / proposed-mutation contract.
- Persistence wiring (SQLAlchemy `jsonb` column, Alembic migration).
- FastAPI endpoints, SSE, and PM-agent integration.
- Pydantic model implementation and its tests.

These are separate M1 slices, planned when we build them.

## Key decisions

1. **Structured JSON is the source of truth (Option A).** The markdown design doc the
   user sees is *rendered from* this state, not stored. The JSON is the brain; the
   markdown is a view.

2. **Persisted as a single JSONB blob**, not normalized tables. The whole state is
   always read and written together; there is no cross-session query need. The blob
   maps 1:1 to a validated model, and avoids a migration on every model change during
   M2–M5.

3. **`currentStage` is content-driven** (`framing → requirements → approach →
   planning → review → done`), tracking the design doc's progression rather than the
   active agent. Agent-driven stages are a parked reach goal; per-item attribution
   (`source` / `proposedBy` / `askedBy`) already captures which agent contributed.

4. **IDs are short, prefixed, and assigned server-side** (`req-1`, `dec-2`), never
   invented by the LLM. Agents propose content; the backend stamps ids.

5. **`status` is the human-in-the-loop.** Agent-created items are always `proposed`
   (questions: `open`); only a human action promotes them to `approved`/`rejected`.
   Nothing becomes "real" silently.

6. **Artifact is narrowed to a saved snapshot.** Not the live doc (which is derived).
   On save/export the rendered markdown is frozen into a versioned `Artifact`; re-saves
   append the next `version`, preserving history. This directly serves the M1 "Save
   produces a shareable `.md`" deliverable.

## The model

Full field-by-field definition, enums, id conventions, and a worked example live in
[`docs/sessionModel.md`](../../sessionModel.md). Summary:

- **`SessionState`** envelope: `schemaVersion`, `sessionId`, `createdAt`,
  `updatedAt`, `project`, and arrays of the entities below.
- **`Project`** (one): `id`, `name`, `summary`, `currentStage`, `status`.
- **`Requirement`**: `id`, `description`, `status`, `source`, `createdAt`.
- **`Constraint`**: `id`, `description`, `status`, `source`.
- **`Decision`**: `id`, `topic`, `choice`, `reason`, `status`, `proposedBy`,
  `approvedBy`.
- **`OpenQuestion`**: `id`, `question`, `askedBy`, `status`, `answer`.
- **`Artifact`**: `id`, `type`, `version`, `status`, `content`.

Enums: Project.currentStage `framing|requirements|approach|planning|review|done`;
Project.status `active|saved|archived`; Requirement/Constraint/Decision.status
`proposed|approved|rejected`; OpenQuestion.status `open|answered|dismissed`;
Artifact.type `design-doc`; Artifact.status `final` (`draft` reserved).

## When implemented (later slices)

The model will land as Pydantic classes in `backend/models/session_state.py`, one
validated schema serialized to a `jsonb` column on the session. Tests will cover
round-trip serialization and the "agent additions default to `proposed`" invariant.
This is noted for continuity only and is not part of this slice.
