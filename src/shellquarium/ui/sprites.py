from __future__ import annotations

from shellquarium.core.pet import Pet


def pet_mood(pet: Pet) -> str:
    if not pet.is_alive:
        return "dead"
    if pet.is_sick:
        return "sick"
    if not pet.lights_on:
        return "sleeping"
    return "awake"


_SPRITES: dict[str, dict[str, list[list[str]]]] = {
    "idle": {
        "awake": [[" .-. ", "(o^o)", " ~~~ "]],
        "joy": [[" .-. ", "(^U^)", " ~~~ "]],
        "sleeping": [[" .-. ", "(-^-) ", " zzz "]],
        "sick": [[" .-. ", "(x~x)", " ~,~ "]],
        "dead": [[" .-. ", "(x-x)", " RIP "]],
    },
    "moving": {
        "awake": [
            [" .-. ", "(o^o)", "~,~,~"],
            [" .-. ", "(o^o)", ",~,~,"],
        ],
        "joy": [
            [" .-. ", "(^U^)", "~,~,~"],
            [" .-. ", "(^U^)", ",~,~,"],
        ],
        "sleeping": [[" .-. ", "(-^-) ", " zzz "]],
        "sick": [
            [" .-. ", "(x~x)", "~,,~~"],
            [" .-. ", "(x~x)", ",~~,,"],
        ],
        "dead": [[" .-. ", "(x-x)", " RIP "]],
    },
}


def get_pet_frame(
    pet: Pet,
    frame_index: int = 0,
    mood_override: str | None = None,
    is_moving: bool = False,
) -> str:
    mood = mood_override or pet_mood(pet)
    motion = "moving" if is_moving else "idle"
    frames = _SPRITES[motion].get(mood) or _SPRITES["idle"][pet_mood(pet)]
    frame = frames[frame_index % len(frames)]
    return "\n".join(frame)
