from __future__ import annotations

from dataclasses import dataclass


STREAK_CHEST_INTERVAL = 4

# Placeholder roster for the text-only collection system.
# Unlocking has no gameplay effect yet; it only shows in the Collection view.
CHARACTERS: dict[str, int] = {
    "Coral Kid": 8,
    "Deep Diver": 12,
    "Moon Jelly": 10,
}

SHARD_DROP_PROB = 0.40
RARE_SHELL_PROB = 0.15


@dataclass(frozen=True)
class ChestDrop:
    kind: str  # "shard" | "shell"
    character: str | None = None
    shell_rarity: str | None = None  # "common" | "rare"
    amount: int = 1


def roll_streak_chest_drop(rng) -> ChestDrop:
    """Roll a single streak chest drop.

    `rng` is expected to provide `.random()` and `.choice()`.
    """
    if rng.random() < SHARD_DROP_PROB:
        character = rng.choice(tuple(CHARACTERS.keys()))
        return ChestDrop(kind="shard", character=character, amount=1)
    rarity = "rare" if rng.random() < RARE_SHELL_PROB else "common"
    return ChestDrop(kind="shell", shell_rarity=rarity, amount=1)

