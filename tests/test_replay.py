from backend.cli.replay import run_transcript
from backend.models.session_state import ProjectStatus
from tests.fakes.provider import FakeProvider


def test_run_transcript_drives_idea_then_answers_and_saves():
    fake = FakeProvider([
        '{"edits": [{"op": "set_summary", "summary": "reminder app"}], "question": "Who uses it?", "done": false}',
        '{"edits": [{"op": "add_requirement", "description": "notify parents"}], "question": "", "done": true}',
    ])
    transcript = {"idea": "a reminder app", "answers": ["parents"]}
    convo = run_transcript(transcript, fake)

    assert convo.state.project.summary == "reminder app"
    assert convo.state.requirements[0].description == "notify parents"
    # idea + one answer = 2 provider calls
    assert len(fake.calls) == 2
    # transcript run saves at the end
    assert convo.state.project.status == ProjectStatus.saved
    assert convo.state.artifacts[-1].version == 1
