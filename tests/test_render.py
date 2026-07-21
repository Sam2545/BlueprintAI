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
