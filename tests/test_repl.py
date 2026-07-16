from backend.cli.repl import parse_command, handle_command
from backend.core.loop import Conversation
from tests.fakes.provider import FakeProvider


def test_parse_command_recognizes_known_commands():
    assert parse_command("approve req-1") == ("approve", "req-1")
    assert parse_command("/approve req-1") == ("approve", "req-1")
    assert parse_command("save out.md") == ("save", "out.md")
    assert parse_command("doc") == ("doc", "")
    assert parse_command("quit") == ("quit", "")


def test_parse_command_treats_prose_as_say():
    assert parse_command("A reminder app for parents") == ("say", "A reminder app for parents")


def test_handle_approve_promotes_item():
    fake = FakeProvider([
        '{"edits": [{"op": "add_requirement", "description": "notify"}], "question": "q?", "done": false}'
    ])
    convo = Conversation(fake)
    convo.send("app")
    out = handle_command(convo, "approve", "req-1")
    assert "req-1" in out
    assert convo.state.requirements[0].status.value == "approved"


def test_handle_doc_returns_markdown():
    convo = Conversation(FakeProvider([]))
    out = handle_command(convo, "doc", "")
    assert "## Overview" in out


def test_handle_save_writes_file(tmp_path):
    convo = Conversation(FakeProvider([]))
    target = tmp_path / "design.md"
    out = handle_command(convo, "save", str(target))
    assert target.exists()
    assert "# " in target.read_text()
    assert str(target) in out
