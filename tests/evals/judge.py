from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.core.loop import Conversation
from backend.providers.base import Message, Provider

RUBRIC_PATH = Path(__file__).parent / "rubric.md"

_JUDGE_SYSTEM = (
    "You are an evaluator scoring a Project Manager agent's design conversation. "
    "Apply the rubric and respond with ONLY a JSON object of the form "
    '{"scores": {"<dimension>": <int 1-5>, ...}, "notes": "<short critique>"}.'
)


def transcript_to_text(convo: Conversation) -> str:
    lines = []
    for m in convo.history:
        speaker = "User" if m.role == "user" else "PM"
        lines.append(f"{speaker}: {m.content}")
    return "\n".join(lines)


def score_transcript(convo: Conversation, rubric: str, provider: Provider) -> dict:
    transcript = transcript_to_text(convo)
    prompt = (
        f"RUBRIC:\n{rubric}\n\n"
        f"TRANSCRIPT:\n{transcript}\n\n"
        "Score every rubric dimension now."
    )
    raw = provider.complete([
        Message(role="system", content=_JUDGE_SYSTEM),
        Message(role="user", content=prompt),
    ])
    start, end = raw.find("{"), raw.rfind("}")
    return json.loads(raw[start:end + 1])


def main(argv: list[str] | None = None) -> int:
    from dotenv import load_dotenv

    from backend.cli.replay import load_transcript, run_transcript
    from backend.providers.openrouter import OpenRouterProvider

    load_dotenv()
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m tests.evals.judge <transcript.json>")
        return 1
    provider = OpenRouterProvider()
    convo = run_transcript(load_transcript(argv[0]), provider)
    result = score_transcript(convo, RUBRIC_PATH.read_text(), provider)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
