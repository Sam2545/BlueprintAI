# BlueprintAI — Session State Model

This document defines the **shared project state** that BlueprintAI keeps for every
session: the single structured JSON object the agents read and write as a user
designs their project.

It is the **source of truth** for a session. The "Design Document" the user sees in
the right pane of the workspace is not stored — it is *rendered from* this state.
Agents reason over this JSON; the markdown is a view.

Physically, the whole object below is stored as **one `jsonb` column** on the
session. Every update rewrites the blob.

> Scope: this document defines the **data model only** — the shape of the JSON. How
> it is rendered to markdown, how agents propose edits, and how it is wired into the
> API are deliberately out of scope here and defined later.

---

## Top-level shape

Every session holds exactly one `SessionState` object:

```json
{
  "schemaVersion": 1,
  "sessionId": "sess_8f3a",
  "createdAt": "2026-07-15T18:20:04Z",
  "updatedAt": "2026-07-15T18:41:12Z",
  "project": { ... },
  "requirements": [ ... ],
  "constraints": [ ... ],
  "decisions": [ ... ],
  "openQuestions": [ ... ],
  "artifacts": [ ... ]
}
```

| field | type | notes |
|---|---|---|
| `schemaVersion` | int | Version of *this model*. Starts at `1`. Bumped when the model shape changes so old sessions can be migrated. |
| `sessionId` | string | Stable id of the session. |
| `createdAt` | string | ISO-8601 timestamp, set once. |
| `updatedAt` | string | ISO-8601 timestamp, bumped on every change to the state. |
| `project` | object | The single project being planned. See below. |
| `requirements` | array | Zero or more `Requirement`. |
| `constraints` | array | Zero or more `Constraint`. |
| `decisions` | array | Zero or more `Decision`. |
| `openQuestions` | array | Zero or more `OpenQuestion`. |
| `artifacts` | array | Zero or more `Artifact` (saved snapshots). |

---

## Conventions

**IDs are short, prefixed, and assigned server-side** — never invented by the LLM.
Agents propose *content*; the backend stamps the id. This keeps the JSON readable
and prevents colliding ids.

| entity | id prefix | example |
|---|---|---|
| Project | `proj-` | `proj-1` |
| Requirement | `req-` | `req-3` |
| Constraint | `con-` | `con-1` |
| Decision | `dec-` | `dec-2` |
| OpenQuestion | `q-` | `q-4` |
| Artifact | `art-` | `art-1` |

**`status` is the human-in-the-loop.** Anything an agent adds is created as
`proposed` (for questions, `open`). Nothing an agent creates is ever "real"
automatically — a **human action** is what flips an item to `approved` / `rejected`
(or answers/dismisses a question). This is how the user always stays in the loop.

**`source` / `proposedBy` / `askedBy` record attribution** — who surfaced an item:
either `user` or an agent id (in the MVP, always `pm`; later `architect`,
`implementation-lead`, `reviewer`). This gives per-item agent attribution today,
before any stage-level agent tracking exists.

---

## Project

The single software idea being planned. Exactly one per session.

| field | type | values / notes |
|---|---|---|
| `id` | string | `proj-1` |
| `name` | string | Short title the PM assigns. |
| `summary` | string | The idea restated in the agent's words. |
| `currentStage` | enum | `framing` · `requirements` · `approach` · `planning` · `review` · `done` |
| `status` | enum | `active` · `saved` · `archived` |

`currentStage` is **content-driven**: it tracks how far the *design document* has
progressed, not which agent is active. The stages map onto the doc's sections
(framing → the overview, `requirements` → requirements, `approach` → proposed
approach, `planning` → tasks & milestones, `review` → final review, `done` → saved).

> Reach goal (not in this model): an agent-driven view of progress
> (`pm → architect → implementation → reviewer`). Deferred until specialists exist.

---

## Requirement

Something the product must do.

| field | type | values / notes |
|---|---|---|
| `id` | string | `req-1` |
| `description` | string | What the product must do. |
| `status` | enum | `proposed` · `approved` · `rejected` |
| `source` | string | `user` or an agent id (e.g. `pm`). |
| `createdAt` | string | ISO-8601 timestamp. |

---

## Constraint

A limitation or boundary the design must respect.

| field | type | values / notes |
|---|---|---|
| `id` | string | `con-1` |
| `description` | string | The limitation. |
| `status` | enum | `proposed` · `approved` · `rejected` |
| `source` | string | `user` or an agent id. |

---

## Decision

A choice made during planning.

| field | type | values / notes |
|---|---|---|
| `id` | string | `dec-1` |
| `topic` | string | What is being decided. |
| `choice` | string | What was chosen. |
| `reason` | string | Why. |
| `status` | enum | `proposed` · `approved` · `rejected` |
| `proposedBy` | string | `user` or an agent id. |
| `approvedBy` | string \| null | The id of whoever approved it; `null` until approved. |

---

## OpenQuestion

An unresolved piece of information the design still needs.

| field | type | values / notes |
|---|---|---|
| `id` | string | `q-1` |
| `question` | string | The question asked. |
| `askedBy` | string | Agent id (e.g. `pm`). |
| `status` | enum | `open` · `answered` · `dismissed` |
| `answer` | string \| null | The answer once given; `null` while `open`. |

---

## Artifact

A **saved snapshot** of a rendered output. Narrowly scoped: an artifact is created
when the user **saves/exports**, freezing exactly what they approved into a concrete,
versioned, downloadable copy. The live preview is derived and ephemeral; an artifact
is frozen and persisted. Re-saving appends a new artifact with the next `version` —
nothing is overwritten, so save history is preserved.

| field | type | values / notes |
|---|---|---|
| `id` | string | `art-1` |
| `type` | enum | `design-doc` (the only type in the MVP). |
| `version` | int | 1-based; the next save appends `version + 1`. |
| `status` | enum | `final` (a saved snapshot; `draft` reserved for later). |
| `content` | string | The rendered markdown body of the snapshot. |

---

## Worked example

A session mid-conversation for the idea *"a mobile app that reminds parents when
their kids' library books are due."* The PM has framed the project, proposed two
requirements (one already approved by the user), recorded one approved decision, and
has an open question outstanding. Nothing has been saved yet, so `artifacts` is empty.

```json
{
  "schemaVersion": 1,
  "sessionId": "sess_8f3a",
  "createdAt": "2026-07-15T18:20:04Z",
  "updatedAt": "2026-07-15T18:41:12Z",
  "project": {
    "id": "proj-1",
    "name": "Library Due-Date Reminders",
    "summary": "A mobile app that reminds parents when their kids' library books are due, so nothing gets returned late.",
    "currentStage": "requirements",
    "status": "active"
  },
  "requirements": [
    {
      "id": "req-1",
      "description": "Notify a parent before a book's due date via push notification.",
      "status": "approved",
      "source": "user",
      "createdAt": "2026-07-15T18:24:31Z"
    },
    {
      "id": "req-2",
      "description": "Let a parent track books for more than one child in a single account.",
      "status": "proposed",
      "source": "pm",
      "createdAt": "2026-07-15T18:39:50Z"
    }
  ],
  "constraints": [
    {
      "id": "con-1",
      "description": "Must work without integrating any specific library system's API in v1.",
      "status": "proposed",
      "source": "pm"
    }
  ],
  "decisions": [
    {
      "id": "dec-1",
      "topic": "Primary platform",
      "choice": "Mobile-first (iOS and Android), no web app in v1.",
      "reason": "Reminders are most useful as phone push notifications.",
      "status": "approved",
      "proposedBy": "pm",
      "approvedBy": "user"
    }
  ],
  "openQuestions": [
    {
      "id": "q-1",
      "question": "How does a parent enter a book and its due date — manual entry, barcode scan, or both?",
      "askedBy": "pm",
      "status": "open",
      "answer": null
    }
  ],
  "artifacts": []
}
```
