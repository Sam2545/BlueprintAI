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
