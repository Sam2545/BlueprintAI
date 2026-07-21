from backend.models.session_state import (
    SessionState, Requirement, ItemStatus, ProjectStage, ProjectStatus,
)


def test_new_session_has_project_and_defaults():
    s = SessionState.new("sess-1")
    assert s.sessionId == "sess-1"
    assert s.schemaVersion == 1
    assert s.project.id == "proj-1"
    assert s.project.currentStage == ProjectStage.framing
    assert s.project.status == ProjectStatus.active
    assert s.requirements == []


def test_requirement_defaults_to_proposed():
    r = Requirement(id="req-1", description="do a thing", source="pm")
    assert r.status == ItemStatus.proposed
    assert r.createdAt  # timestamp populated


def test_roundtrip_serialization():
    s = SessionState.new("sess-1")
    s.requirements.append(Requirement(id="req-1", description="x", source="user"))
    dumped = s.model_dump_json()
    restored = SessionState.model_validate_json(dumped)
    assert restored.requirements[0].description == "x"
    assert restored == s
