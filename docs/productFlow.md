# BlueprintAI — Product Flow (Happy Path)

This document describes the "happy path" a user takes through BlueprintAI: from a raw idea to a saved, shareable design document produced with a team of AI agents.

The north-star experience: **a user goes from "I have an idea" to "agents are actively helping me" within the first 60 seconds.**

---

## The Happy Path

### 1. Landing — "What do you want to build?"

The user arrives at a near-empty screen with a single, inviting prompt:

> **What do you want to build?**

A large text input, a Start button, nothing else. No signup wall, no configuration. The user types something like:

> "A mobile app that reminds parents when their kids' library books are due."

They press **Start**.

### 2. The team shows up (< 60 seconds)

The user is taken to the **workspace**: a two-pane layout.

- **Left:** a chat/conversation stream where the agents talk.
- **Right:** a live **Design Document** preview that starts mostly empty and fills in as the conversation progresses.

Within seconds, the **Project Manager agent** introduces itself and the team, restates the idea in its own words to confirm understanding, and asks its first scoping question — one question at a time, so the user is never overwhelmed.

> **PM:** Great — a due-date reminder app for parents. To scope this well: who's the primary user, the parent or the child? And roughly how many books does a family track at once?

For the MVP, the **Project Manager is the only active agent**. The UI is designed so additional specialists (Architect, Implementation Lead, Reviewer) can visibly "join" the room in later milestones without changing the core experience.

### 3. Guided, human-in-the-loop Q&A

The agent leads a natural back-and-forth:

- Asks focused questions to pin down **purpose, users, constraints, and success criteria**.
- After meaningful answers, it **proposes edits to the Design Document**, which appear live in the right pane (new sections, tasks, milestones).
- The user always sees what's being written. Nothing is committed silently — this is the **human in the loop**. The user can push back, correct, or redirect at any point, and the document updates accordingly.

The document grows into a real project proposal:

- **Overview / Problem** — what and why.
- **Users & Requirements** — who it's for, what it must do.
- **Proposed Approach** — high-level shape of the solution.
- **Tasks & Milestones** — an actionable, sequenced plan.
- **Open Questions / Risks** — what still needs deciding.

### 4. Converging on a plan

Once the agent judges the design is well-formed, it summarizes:

> **PM:** Here's where we landed. The doc now has a clear proposal, five milestones, and a task list for the first milestone. Anything you'd change before you save it?

The user reviews the right pane, makes any final tweaks via chat, and is satisfied.

### 5. Save & share

The user presses **Save**. BlueprintAI:

- Finalizes the design document as Markdown.
- Persists it to their session.
- Offers a **shareable, downloadable `.md`** the user can hand to a developer, a teammate, or a contractor — a complete, review-ready blueprint to start building from.

The user leaves with a finished design doc in hand, produced in a single guided sitting.

---

## Where this grows (beyond the MVP)

The happy path above runs entirely on the single **Project Manager** agent. The same flow scales as specialists come online:

- The **Architect** joins to shape the technical approach.
- The **Implementation Lead** breaks the approach into concrete tasks and milestones.
- The **Reviewer** critiques the doc for gaps and risks before save.
- Eventually the PM becomes a **delegator** — the single face to the user that pulls in specialists behind the scenes and merges their contributions back into one coherent document.

The user experience stays the same: type an idea, watch a capable team build the plan with you, save the result.
