import pytest

from backend.providers.base import Message
from tests.fakes.provider import FakeProvider


def test_fake_returns_scripted_responses_in_order():
    fake = FakeProvider(["first", "second"])
    assert fake.complete([Message(role="user", content="hi")]) == "first"
    assert fake.complete([Message(role="user", content="again")]) == "second"


def test_fake_records_calls():
    fake = FakeProvider(["ok"])
    fake.complete([Message(role="user", content="hello")])
    assert fake.calls[0][0].content == "hello"


def test_fake_raises_when_exhausted():
    fake = FakeProvider([])
    with pytest.raises(AssertionError):
        fake.complete([Message(role="user", content="x")])
