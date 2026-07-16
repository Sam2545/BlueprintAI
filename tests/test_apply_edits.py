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
