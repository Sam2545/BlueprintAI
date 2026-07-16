from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from backend.core.loop import Conversation
from backend.models.render import render_design_doc
from backend.providers.base import Provider


def load_transcript(path: str) -> dict:
    return json.loads(Path(path).read_text())


def run_transcript(transcript: dict, provider: Provider) -> Conversation:
    convo = Conversation(provider)
    convo.send(transcript["idea"])
    for answer in transcript.get("answers", []):
        convo.send(answer)
    convo.save()
    return convo


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m backend.cli.replay <transcript.json>")
        return 1
    from backend.providers.openrouter import OpenRouterProvider

    transcript = load_transcript(argv[0])
    convo = run_transcript(transcript, OpenRouterProvider())
    print(render_design_doc(convo.state))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
