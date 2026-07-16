from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


class Provider(ABC):
    @abstractmethod
    def complete(self, messages: list[Message]) -> str:
        """Return the model's text completion for the given messages."""
        raise NotImplementedError
