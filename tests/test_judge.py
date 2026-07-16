import pytest

from backend.core.loop import Conversation
from tests.evals.judge import transcript_to_text, score_transcript
from tests.fakes.provider import FakeProvider


def _convo_with_one_turn() -> Conversation:
    fake = FakeProvider([
        '{"edits": [{"op": "set_summary", "summary": "reminder app"}], '
        '"question": "Who is the primary user?", "done": false}'
    ])
    convo = Conversation(fake)
    convo.send("A library reminder app")
    return convo


def test_transcript_to_text_includes_user_and_pm_turns():
    text = transcript_to_text(_convo_with_one_turn())
    assert "A library reminder app" in text
    assert "Who is the primary user?" in text


def test_score_transcript_parses_judge_json():
    judge = FakeProvider([
        '{"scores": {"one_question_per_turn": 5, "relevance": 4, '
        '"coverage": 3, "grounding": 5, "convergence": 4}, "notes": "solid"}'
    ])
    result = score_transcript(_convo_with_one_turn(), "RUBRIC TEXT", judge)
    assert result["scores"]["relevance"] == 4
    assert result["notes"] == "solid"
    # the judge was given both the rubric and the transcript
    sent = judge.calls[0][-1].content
    assert "RUBRIC TEXT" in sent
    assert "Who is the primary user?" in sent


def test_score_transcript_raises_on_no_json():
    judge = FakeProvider(["no json here"])
    with pytest.raises(ValueError, match="no JSON object"):
        score_transcript(_convo_with_one_turn(), "RUBRIC TEXT", judge)
