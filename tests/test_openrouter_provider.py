import httpx
import pytest

from backend.providers.base import Message
from backend.providers.openrouter import OpenRouterProvider


def test_complete_posts_and_parses_response(monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "hello from model"}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    provider = OpenRouterProvider(api_key="test-key", model="test-model")
    out = provider.complete([Message(role="user", content="hi")])

    assert out == "hello from model"
    assert captured["json"]["model"] == "test-model"
    assert captured["json"]["messages"] == [{"role": "user", "content": "hi"}]
    assert captured["headers"]["Authorization"] == "Bearer test-key"


def test_reads_key_and_model_from_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "env-model")
    provider = OpenRouterProvider()
    assert provider.api_key == "env-key"
    assert provider.model == "env-model"


def test_missing_api_key_raises_actionable_runtime_error(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY not set"):
        OpenRouterProvider()
