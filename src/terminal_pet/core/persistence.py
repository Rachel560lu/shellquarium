from __future__ import annotations

import json
import os
from pathlib import Path

from terminal_pet.core.pet import Pet


SAVE_DIR = Path(os.getenv("TERMINAL_PET_HOME", Path.home() / ".terminal_pet"))
SAVE_FILE = SAVE_DIR / "pet.json"
SETTINGS_FILE = SAVE_DIR / "settings.json"


def save_pet(pet: Pet) -> Path:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    SAVE_FILE.write_text(json.dumps(pet.to_dict(), indent=2), encoding="utf-8")
    return SAVE_FILE


def load_pet() -> Pet | None:
    if not SAVE_FILE.exists():
        return None
    data = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
    pet = Pet.from_dict(data)
    pet.tick()
    return pet


def delete_pet() -> None:
    if SAVE_FILE.exists():
        SAVE_FILE.unlink()


def load_settings() -> dict[str, str]:
    if not SETTINGS_FILE.exists():
        return {}
    return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))


def save_settings(settings: dict[str, str]) -> Path:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return SETTINGS_FILE
