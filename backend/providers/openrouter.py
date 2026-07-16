import os

import httpx

from backend.providers.base import Message, Provider

DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"


class OpenRouterProvider(Provider):
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ):
        self.api_key = api_key or os.environ["OPENROUTER_API_KEY"]
        self.model = model or os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
        self.timeout = timeout

    def complete(self, messages: list[Message]) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = httpx.post(
            self.BASE_URL, json=payload, headers=headers, timeout=self.timeout
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
