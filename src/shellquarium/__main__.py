from __future__ import annotations

import argparse
import sys

from shellquarium.core.persistence import delete_pet, load_pet, save_pet
from shellquarium.core.pet import Pet
from shellquarium.core.progression import record_counter, update_progress


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shellquarium",
        description="A cozy terminal aquarium pet",
    )
    subparsers = parser.add_subparsers(dest="command")

    hatch = subparsers.add_parser("hatch", help="Create a new pet")
    hatch.add_argument("name", nargs="?", default="Tama")

    subparsers.add_parser("status", help="Show pet status")

    for command in ("feed", "play", "clean", "heal", "discipline", "sleep"):
        subparsers.add_parser(command, help=f"Run {command} action")

    subparsers.add_parser("reset", help="Delete the saved pet")
    return parser


def _cmd_tui() -> None:
    from shellquarium.ui.app import TerminalPetApp

    TerminalPetApp().run()


def require_pet() -> Pet:
    pet = load_pet()
    if pet is None:
        raise SystemExit("No pet found. Run 'python -m shellquarium hatch <name>' first.")
    return pet


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        _cmd_tui()
        return

    if args.command == "hatch":
        pet = Pet(name=args.name)
        save_pet(pet)
        print(f"A new egg named {pet.name} is waiting.")
        return

    if args.command == "reset":
        delete_pet()
        print("Saved pet deleted.")
        return

    pet = require_pet()
    messages = pet.tick()

    if args.command == "status":
        pass
    elif args.command in {"feed", "play", "clean", "heal", "discipline", "sleep"}:
        action_name = {
            "feed": "feed",
            "play": "play",
            "clean": "clean",
            "heal": "heal",
            "discipline": "discipline_pet",
            "sleep": "toggle_lights",
        }[args.command]
        action_result = getattr(pet, action_name)()
        messages.append(action_result)
        if not _is_blocked_action(action_result):
            record_counter(pet, args.command)
            record_counter(pet, "care_actions")
    else:
        raise SystemExit(f"Unknown command: {args.command}")

    messages.extend(update_progress(pet))
    save_pet(pet)

    for message in messages:
        print(message)
    for line in pet.status_lines():
        print(line)


def _is_blocked_action(message: str) -> bool:
    markers = ("already", "cannot", "not ready", "nothing to clean", "not sick", "ignores")
    return any(marker in message.lower() for marker in markers)


if __name__ == "__main__":
    main(sys.argv[1:])
