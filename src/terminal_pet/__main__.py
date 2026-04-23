from __future__ import annotations

import argparse
import sys

from terminal_pet.core.persistence import delete_pet, load_pet, save_pet
from terminal_pet.core.pet import Pet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="terminal-pet", description="Minimal CLI terminal pet")
    subparsers = parser.add_subparsers(dest="command")

    hatch = subparsers.add_parser("hatch", help="Create a new pet")
    hatch.add_argument("name", nargs="?", default="Tama")

    subparsers.add_parser("status", help="Show pet status")

    for command in ("feed", "play", "clean", "heal", "discipline", "sleep"):
        subparsers.add_parser(command, help=f"Run {command} action")

    subparsers.add_parser("reset", help="Delete the saved pet")
    return parser


def _cmd_tui() -> None:
    from terminal_pet.ui.app import TerminalPetApp

    TerminalPetApp().run()


def require_pet() -> Pet:
    pet = load_pet()
    if pet is None:
        raise SystemExit("No pet found. Run 'python -m terminal_pet hatch <name>' first.")
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
    elif args.command == "feed":
        messages.append(pet.feed())
    elif args.command == "play":
        messages.append(pet.play())
    elif args.command == "clean":
        messages.append(pet.clean())
    elif args.command == "heal":
        messages.append(pet.heal())
    elif args.command == "discipline":
        messages.append(pet.discipline_pet())
    elif args.command == "sleep":
        messages.append(pet.toggle_lights())
    else:
        raise SystemExit(f"Unknown command: {args.command}")

    save_pet(pet)

    for message in messages:
        print(message)
    for line in pet.status_lines():
        print(line)


if __name__ == "__main__":
    main(sys.argv[1:])
