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
