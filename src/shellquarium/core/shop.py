from __future__ import annotations

from dataclasses import dataclass

from shellquarium.core.pet import LifeStage, Pet


@dataclass(frozen=True)
class ShopItem:
    item_id: str
    name: str
    price: int
    kind: str
    effect: str | None = None

    @property
    def decorative(self) -> bool:
        return self.kind == "decoration"


SHOP_CATALOG: dict[str, ShopItem] = {
    "seaweed_snack": ShopItem("seaweed_snack", "Seaweed Snack", 2, "consumable", "hunger"),
    "bubble_tea": ShopItem("bubble_tea", "Bubble Tea", 3, "consumable", "happiness"),
    "tiny_sponge": ShopItem("tiny_sponge", "Tiny Sponge", 4, "consumable", "poop"),
    "pearl_tonic": ShopItem("pearl_tonic", "Pearl Tonic", 5, "consumable", "health"),
    "seaweed_ribbon": ShopItem("seaweed_ribbon", "Seaweed Ribbon", 3, "decoration"),
    "bubble_stone": ShopItem("bubble_stone", "Bubble Stone", 5, "decoration"),
    "pink_star_clip": ShopItem("pink_star_clip", "Pink Star Clip", 7, "decoration"),
    "moon_shell_lamp": ShopItem("moon_shell_lamp", "Moon Shell Lamp", 9, "decoration"),
}


def buy_item(pet: Pet, item_id: str) -> str:
    item = SHOP_CATALOG.get(item_id)
    if item is None:
        return "That shop item does not exist."
    if item.decorative and item_id in pet.owned_decorations:
        return f"You already own the {item.name}."
    if pet.shells < item.price:
        return f"You need {item.price} shells for the {item.name}."

    pet.shells -= item.price
    if item.decorative:
        pet.owned_decorations.append(item_id)
        pet.collection_unseen = True
        return f"You bought the {item.name}. It was added to your collection."

    pet.inventory[item_id] = pet.inventory.get(item_id, 0) + 1
    return f"You bought a {item.name}."


def use_item(pet: Pet, item_id: str) -> str:
    item = SHOP_CATALOG.get(item_id)
    if item is None:
        return "That inventory item does not exist."
    if item.decorative:
        return f"The {item.name} is a collection decoration, not a consumable."
    if pet.stage == LifeStage.EGG or not pet.is_alive:
        return "Your pet cannot use items right now."
    if pet.inventory.get(item_id, 0) <= 0:
        return f"You do not have a {item.name}."

    if item.effect == "hunger":
        if pet.hunger >= 4:
            return f"{pet.name} is already full."
        pet.hunger = min(4, pet.hunger + 1)
    elif item.effect == "happiness":
        if pet.happiness >= 4:
            return f"{pet.name} is already cheerful."
        pet.happiness = min(4, pet.happiness + 1)
    elif item.effect == "poop":
        if pet.poop <= 0:
            return f"{pet.name}'s space is already clean."
        pet.poop -= 1
    elif item.effect == "health":
        if not pet.is_sick:
            return f"{pet.name} is not sick."
        pet.is_sick = False
        pet.health = min(4, pet.health + 1)

    _decrement_inventory(pet, item_id)
    return f"You used a {item.name}."


def _decrement_inventory(pet: Pet, item_id: str) -> None:
    remaining = pet.inventory[item_id] - 1
    if remaining:
        pet.inventory[item_id] = remaining
    else:
        del pet.inventory[item_id]
