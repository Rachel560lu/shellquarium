from __future__ import annotations

from terminal_pet.core.pet import Pet
from terminal_pet.ui.sprites import get_pet_frame, pet_mood


REACTION_GAP = "       "
SCENE_WIDTH = 46
SCENE_HEIGHT = 14
PET_WIDTH = 5
PET_HEIGHT = 3
DEFAULT_PET_POSITION = ((SCENE_WIDTH - PET_WIDTH) // 2, (SCENE_HEIGHT - PET_HEIGHT) // 2)
CRAB_POSITION = (5, SCENE_HEIGHT - 4)
SEAWEED_POSITION = (14, SCENE_HEIGHT - 4)
STARFISH_POSITION = (35, SCENE_HEIGHT - 3)
SHELL_POSITION = (24, SCENE_HEIGHT - 3)
CLOCK_POSITION = (25, 2)
SEAWEED_LINES = (
    " |) ",
    "  (| ",
    " |) ",
    "  |) ",

)
STARFISH_LINES = (
    "",
    " 𓇻  𓇼"
)
SHELL_FRAMES = (
    (
        "œœ",
        "œœ"
    ),
    (
        "(_)",
        "(º)",
    )
)
CRAB_FRAMES = (
    (
        " v   v ",
        "(o_o)",
        "=( )=",
    ),
    (
        "  v v ",
        " (o_o)",
        " =( )=",
    ),
    (
        " v   v ",
        " (o_o)",
        "=( )=",
    ),
)

BASE_REACTIONS: dict[str, tuple[tuple[str, ...], ...]] = {
    "feed": (
        (
            "  [gold1]*[/] [yellow1].[/]  ",
            " [yellow1].[/] [gold1]*[/]   ",
            "   [gold1]*[/]    ",
            "         ",
            "         ",
        ),
    ),
    "clean": (
        (
            "  [cyan1]*[/] [white]*[/]  ",
            "   [white]*[/] [cyan1]*[/] ",
            "    [cyan1]*[/]   ",
            "         ",
            "         ",
        ),
    ),
    "heal": (
        (
            "    [green]+[/]    ",
            "  [green]+ +[/]   ",
            "    [green]+[/]    ",
            "         ",
            "         ",
        ),
    ),
    "discipline_pet": (
        (
            "    [orange1]![/]    ",
            "  [orange1]! ![/]   ",
            "    [orange1]![/]    ",
            "         ",
            "         ",
        ),
    ),
    "toggle_lights": (
        (
            "   [bright_white]z[/] [lightskyblue1]~[/]   ",
            "  [lightskyblue1]~[/] [bright_white]z[/]    ",
            "   [bright_white]z[/]     ",
            "         ",
            "         ",
        ),
    ),
}

def performance_state(pet: Pet) -> str:
    if not pet.is_alive:
        return "dead"
    if pet.is_sick:
        return "sick"
    if not pet.lights_on:
        return "sleeping"
    if pet.hunger <= 1:
        return "hungry"
    if pet.happiness <= 1:
        return "gloomy"
    if pet.happiness >= 4 and pet.hunger >= 3:
        return "playful"
    return "awake"


def performance_line(pet: Pet, theme_name: str = "") -> str:
    state = performance_state(pet)
    lines = {
        "dead": f"{pet.name} has gone still.",
        "sleeping": f"{pet.name} is tucked in and drifting.",
        "sick": f"{pet.name} looks woozy and needs care.",
        "hungry": f"{pet.name} is searching for snacks.",
        "gloomy": f"{pet.name} looks restless and wants attention.",
        "playful": f"{pet.name} is zipping around the tank.",
        "awake": f"{pet.name} is idling in the tank.",
    }
    return lines[state]


def render_scene(
    theme_name: str,
    pet: Pet,
    frame_index: int,
    mood_override: str | None = None,
    pet_position: tuple[int, int] = DEFAULT_PET_POSITION,
    is_moving: bool = False,
    selected_target: str | None = None,
    scene_mode: str = "tank",
    clock_text: str | None = None,
) -> str:
    pet_lines = get_pet_frame(pet, frame_index, mood_override=mood_override, is_moving=is_moving).splitlines()
    canvas = _build_scene_canvas(
        pet_lines,
        pet_position,
        frame_index,
        reaction_lines=None,
        reaction_anchor=(0, 0),
        selected_target=selected_target,
        scene_mode=scene_mode,
        clock_text=clock_text,
    )
    top_border = "[white]+[/][white]-[/]" + "[white]-[/]" * (SCENE_WIDTH - 2) + "[white]-[/][white]+[/]"
    bottom_border = "[white]+[/][white]-[/]" + "[white]-[/]" * (SCENE_WIDTH - 2) + "[white]-[/][white]+[/]"
    return f"{top_border}\n{canvas}\n{bottom_border}"


def render_scene_with_reaction(
    theme_name: str,
    pet: Pet,
    frame_index: int,
    reaction_name: str | None = None,
    reaction_frame: int = 0,
    mood_override: str | None = None,
    pet_position: tuple[int, int] = DEFAULT_PET_POSITION,
    is_moving: bool = False,
    selected_target: str | None = None,
    scene_mode: str = "tank",
    clock_text: str | None = None,
) -> str:
    pet_lines = get_pet_frame(pet, frame_index, mood_override=mood_override, is_moving=is_moving).splitlines()
    reaction_anchor = (pet_position[0] + PET_WIDTH + len(REACTION_GAP) - 4, max(0, pet_position[1] - 1))
    if not reaction_name:
        return render_scene(
            theme_name,
            pet,
            frame_index,
            mood_override=mood_override,
            pet_position=pet_position,
            is_moving=is_moving,
            selected_target=selected_target,
            scene_mode=scene_mode,
            clock_text=clock_text,
        )

    reaction_map = BASE_REACTIONS
    if reaction_name not in reaction_map:
        return render_scene(
            theme_name,
            pet,
            frame_index,
            mood_override=mood_override,
            pet_position=pet_position,
            is_moving=is_moving,
            selected_target=selected_target,
            scene_mode=scene_mode,
            clock_text=clock_text,
        )

    reaction_frames = reaction_map[reaction_name]
    reaction_lines = list(reaction_frames[reaction_frame % len(reaction_frames)])
    canvas = _build_scene_canvas(
        pet_lines,
        pet_position,
        frame_index,
        reaction_lines,
        reaction_anchor,
        selected_target=selected_target,
        scene_mode=scene_mode,
        clock_text=clock_text,
    )
    top_border = "[white]+[/][white]-[/]" + "[white]-[/]" * (SCENE_WIDTH - 2) + "[white]-[/][white]+[/]"
    bottom_border = "[white]+[/][white]-[/]" + "[white]-[/]" * (SCENE_WIDTH - 2) + "[white]-[/][white]+[/]"
    return f"{top_border}\n{canvas}\n{bottom_border}"


def _build_scene_canvas(
    pet_lines: list[str],
    pet_position: tuple[int, int],
    frame_index: int,
    reaction_lines: list[str] | None = None,
    reaction_anchor: tuple[int, int] = (0, 0),
    selected_target: str | None = None,
    scene_mode: str = "tank",
    clock_text: str | None = None,
) -> str:
    pet_x, pet_y = pet_position
    rows = [[" " for _ in range(SCENE_WIDTH)] for _ in range(SCENE_HEIGHT)]

    bubble_positions = ((30, 1), (39, 2), (24, 3), (34, 5), (42, 7), (28, 10), (37, 11))
    for bubble_x, bubble_y in bubble_positions:
        rows[bubble_y][bubble_x] = "[deepskyblue1].[/]"

    for x in range(SCENE_WIDTH):
        if x % 3 == 1:
            rows[SCENE_HEIGHT - 1][x] = "[green]|[/]"
        else:
            rows[SCENE_HEIGHT - 1][x] = "[green]~[/]"

    seaweed_x, seaweed_y = SEAWEED_POSITION
    for row_index, seaweed_line in enumerate(SEAWEED_LINES):
        target_row = seaweed_y + row_index
        if target_row >= SCENE_HEIGHT:
            break
        for column, char in enumerate(seaweed_line):
            target_column = seaweed_x + column
            if target_column >= SCENE_WIDTH:
                break
            if char != " ":
                color = "spring_green3" if selected_target == "seaweed" else "green4"
                rows[target_row][target_column] = f"[{color}]{char}[/]"

    if scene_mode != "pomodoro":
        shell_x, shell_y = SHELL_POSITION
        shell_lines = SHELL_FRAMES[(frame_index // 2) % len(SHELL_FRAMES)]
        for row_index, shell_line in enumerate(shell_lines):
            target_row = shell_y + row_index
            if target_row >= SCENE_HEIGHT:
                break
            for column, char in enumerate(shell_line):
                target_column = shell_x + column
                if target_column >= SCENE_WIDTH:
                    break
                if char != " ":
                    color = "bold bright_white" if selected_target == "shell" else "bright_white"
                    rows[target_row][target_column] = f"[{color}]{char}[/]"

    starfish_x, starfish_y = STARFISH_POSITION
    for row_index, starfish_line in enumerate(STARFISH_LINES):
        target_row = starfish_y + row_index
        if target_row >= SCENE_HEIGHT:
            break
        for column, char in enumerate(starfish_line):
            target_column = starfish_x + column
            if target_column >= SCENE_WIDTH:
                break
            if char != " ":
                rows[target_row][target_column] = f"[light_pink1]{char}[/]"

    if scene_mode != "pomodoro":
        crab_x, crab_y = CRAB_POSITION
        crab_step = (frame_index // 2) % len(CRAB_FRAMES)
        crab_lines = CRAB_FRAMES[crab_step]
        crab_x += crab_step
        for row_index, crab_line in enumerate(crab_lines):
            target_row = crab_y + row_index
            if target_row >= SCENE_HEIGHT:
                break
            for column, char in enumerate(crab_line):
                target_column = crab_x + column
                if target_column >= SCENE_WIDTH:
                    break
                if char != " ":
                    if char == "o":
                        color = "bold bright_white" if selected_target == "crab" else "bright_white"
                    else:
                        color = "bold orange1" if selected_target == "crab" else "orange1"
                    rows[target_row][target_column] = f"[{color}]{char}[/]"

    if scene_mode == "pomodoro" and clock_text:
        _draw_clock(rows, clock_text)

    for row_index, pet_line in enumerate(pet_lines):
        target_row = pet_y + row_index
        if target_row >= SCENE_HEIGHT:
            break
        for column, char in enumerate(pet_line):
            target_column = pet_x + column
            if target_column >= SCENE_WIDTH:
                break
            if char != " ":
                if char in {"o", "^", "x", "-", "U", "~", ",", "z", "R", "I", "P"}:
                    color = "bold bright_cyan" if selected_target == "pet" else "bright_cyan"
                else:
                    color = "bold deepskyblue1" if selected_target == "pet" else "deepskyblue1"
                rows[target_row][target_column] = f"[{color}]{char}[/]"

    if reaction_lines:
        reaction_x, reaction_y = reaction_anchor
        for row_index, reaction_line in enumerate(reaction_lines):
            target_row = reaction_y + row_index
            if target_row >= SCENE_HEIGHT:
                break
            for column, char in enumerate(reaction_line):
                target_column = reaction_x + column
                if target_column >= SCENE_WIDTH:
                    break
                if char != " ":
                    rows[target_row][target_column] = char

    return "\n".join("[white]|[/]" + "".join(row) + "[white]|[/]" for row in rows)



def _draw_clock(rows: list[list[str]], clock_text: str) -> None:
    clock_x, clock_y = CLOCK_POSITION
    clock_lines = (
        " .----. ",
        f"({clock_text.center(6)})",
        " '----' ",
    )
    for row_index, clock_line in enumerate(clock_lines):
        target_row = clock_y + row_index
        if target_row >= SCENE_HEIGHT:
            break
        for column, char in enumerate(clock_line):
            target_column = clock_x + column
            if target_column >= SCENE_WIDTH:
                break
            if char != " ":
                color = "bright_white" if char.isdigit() or char == ":" else "grey70"
                rows[target_row][target_column] = f"[{color}]{char}[/]"

def visible_mood(pet: Pet) -> str:
    state = performance_state(pet)
    if state in {"hungry", "gloomy", "playful"}:
        return state
    return pet_mood(pet)
