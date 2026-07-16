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
