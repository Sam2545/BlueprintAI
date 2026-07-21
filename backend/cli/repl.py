from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from backend.core.loop import Conversation
from backend.models.render import render_design_doc

KNOWN_COMMANDS = {"approve", "reject", "doc", "save", "quit"}


def parse_command(line: str) -> tuple[str, str]:
    stripped = line.strip()
    token = stripped[1:] if stripped.startswith("/") else stripped
    head, _, rest = token.partition(" ")
    if head in KNOWN_COMMANDS:
        return head, rest.strip()
    return "say", stripped


def handle_command(convo: Conversation, command: str, arg: str) -> str:
    if command == "approve":
        if arg == "all":
            count = convo.approve_all()
            return f"approved {count} item(s)"
        ok = convo.approve(arg)
        return f"approved {arg}" if ok else f"no such item: {arg}"
    if command == "reject":
        if arg == "all":
            count = convo.reject_all()
            return f"rejected {count} item(s)"
        ok = convo.reject(arg)
        return f"rejected {arg}" if ok else f"no such item: {arg}"
    if command == "doc":
        return render_design_doc(convo.state)
    if command == "save":
        art = convo.save()
        target = Path(arg) if arg else Path("design.md")
        target.write_text(art.content)
        return f"saved v{art.version} to {target}"
    return f"unknown command: {command}"


def _say(convo: Conversation, text: str) -> str:
    result = convo.send(text)
    lines = []
    for change in result.changes:
        lines.append(f"  · {change}")
    if result.question:
        lines.append(f"\nPM: {result.question}")
    if result.done:
        lines.append("\nPM: I think the design is well-formed. Type `save` to export.")
    return "\n".join(lines)


def main() -> int:
    load_dotenv()
    from backend.providers.openrouter import OpenRouterProvider

    convo = Conversation(OpenRouterProvider())
    print("BlueprintAI — Project Manager (terminal). Describe what you want to build.")
    print("Commands: approve <id|all>, reject <id|all>, doc, save [file], quit\n")
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        command, arg = parse_command(line)
        if command == "quit":
            return 0
        if command == "say":
            if not arg:
                continue
            print(_say(convo, arg))
        else:
            print(handle_command(convo, command, arg))


if __name__ == "__main__":
    raise SystemExit(main())
