from __future__ import annotations

from shellquarium.core.pet import Pet
from shellquarium.ui.sprites import get_pet_frame, pet_mood


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
        # Death is removed; treat legacy "dead" state as sick.
        return "sick"
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
    clock_progress: float | None = None,
    clock_subtitle: str | None = None,
    clock_phase: int = 0,
    clock_bar_symbols: list[str] | None = None,
    clock_bar_width: int | None = None,
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
        clock_progress=clock_progress,
        clock_subtitle=clock_subtitle,
        clock_phase=clock_phase,
        clock_bar_symbols=clock_bar_symbols,
        clock_bar_width=clock_bar_width,
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
    clock_progress: float | None = None,
    clock_subtitle: str | None = None,
    clock_phase: int = 0,
    clock_bar_symbols: list[str] | None = None,
    clock_bar_width: int | None = None,
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
            clock_progress=clock_progress,
            clock_subtitle=clock_subtitle,
            clock_phase=clock_phase,
            clock_bar_symbols=clock_bar_symbols,
            clock_bar_width=clock_bar_width,
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
        clock_progress=clock_progress,
        clock_subtitle=clock_subtitle,
        clock_phase=clock_phase,
        clock_bar_symbols=clock_bar_symbols,
        clock_bar_width=clock_bar_width,
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
    clock_progress: float | None = None,
    clock_subtitle: str | None = None,
    clock_phase: int = 0,
    clock_bar_symbols: list[str] | None = None,
    clock_bar_width: int | None = None,
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
        _draw_clock(
            rows,
            clock_text,
            clock_progress=clock_progress,
            clock_subtitle=clock_subtitle,
            clock_phase=clock_phase,
            clock_bar_symbols=clock_bar_symbols,
            clock_bar_width=clock_bar_width,
        )

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



_BIG_TIMER_FONT: dict[str, tuple[str, ...]] = {
    "0": (" ### ", "#   #", "#   #", "#   #", " ### "),
    "1": ("  #  ", " ##  ", "  #  ", "  #  ", " ### "),
    "2": (" ### ", "#   #", "   # ", "  #  ", "#####"),
    "3": ("#### ", "    #", " ### ", "    #", "#### "),
    "4": ("#   #", "#   #", "#####", "    #", "    #"),
    "5": ("#####", "#    ", "#### ", "    #", "#### "),
    "6": (" ### ", "#    ", "#### ", "#   #", " ### "),
    "7": ("#####", "    #", "   # ", "  #  ", "  #  "),
    "8": (" ### ", "#   #", " ### ", "#   #", " ### "),
    "9": (" ### ", "#   #", " ####", "    #", " ### "),
    ":": ("     ", "  #  ", "     ", "  #  ", "     "),
    " ": ("     ", "     ", "     ", "     ", "     "),
}


def _big_timer_lines(text: str) -> list[str]:
    glyphs = [_BIG_TIMER_FONT.get(ch, _BIG_TIMER_FONT[" "]) for ch in text]
    lines: list[str] = []
    for row in range(5):
        lines.append(" ".join(glyph[row] for glyph in glyphs))
    return lines


def _draw_clock(
    rows: list[list[str]],
    clock_text: str,
    clock_progress: float | None,
    clock_subtitle: str | None,
    clock_phase: int = 0,
    clock_bar_symbols: list[str] | None = None,
    clock_bar_width: int | None = None,
) -> None:
    timer_lines = _big_timer_lines(clock_text)
    timer_width = max((len(line) for line in timer_lines), default=0)
    clock_y = 1
    clock_x = max(0, (SCENE_WIDTH - timer_width) // 2)

    for row_index, clock_line in enumerate(timer_lines):
        target_row = clock_y + row_index
        if target_row >= SCENE_HEIGHT:
            break
        for column, char in enumerate(clock_line):
            target_column = clock_x + column
            if target_column >= SCENE_WIDTH:
                break
            if char != " ":
                rows[target_row][target_column] = f"[bright_white]{char}[/]"

    # Encouragement subtitle (no redundant small clock).
    label_row = clock_y + len(timer_lines)
    if 0 <= label_row < SCENE_HEIGHT:
        subtitle = clock_subtitle or ""
        subtitle = subtitle[: (SCENE_WIDTH - 2)]
        label_x = max(0, (SCENE_WIDTH - len(subtitle)) // 2) if subtitle else 0
        for column, char in enumerate(subtitle):
            target_column = label_x + column
            if target_column >= SCENE_WIDTH:
                break
            rows[label_row][target_column] = f"[grey70]{char}[/]"

    if clock_progress is None:
        return

    progress = max(0.0, min(1.0, float(clock_progress)))
    bar_row = label_row + 2
    if bar_row >= SCENE_HEIGHT:
        return

    # Fixed-width bar: fill part uses user-provided symbols; empty stays "-".
    bar_width = int(clock_bar_width) if clock_bar_width else min(30, SCENE_WIDTH - 6)
    bar_width = max(1, min(bar_width, SCENE_WIDTH - 6))
    filled = int(round(progress * bar_width))
    filled = max(0, min(bar_width, filled))

    filled_symbols: list[str] = []
    if clock_bar_symbols:
        filled_symbols = list(clock_bar_symbols)[:filled]
    if len(filled_symbols) < filled:
        filled_symbols.extend(["⋆"] * (filled - len(filled_symbols)))

    bar_x = max(0, (SCENE_WIDTH - (bar_width + 2)) // 2)
    x = bar_x

    # Brackets: avoid literal `[` / `]` because Rich markup treats them as tag
    # delimiters and escaping is error-prone in this per-cell renderer.
    if 0 <= x < SCENE_WIDTH:
        rows[bar_row][x] = "[grey50]⟦[/]"
    x += 1

    for i in range(bar_width):
        if 0 <= x < SCENE_WIDTH:
            if i < filled:
                rows[bar_row][x] = f"[deepskyblue1]{filled_symbols[i]}[/]"
            else:
                rows[bar_row][x] = "[grey50]-[/]"
        x += 1

    if 0 <= x < SCENE_WIDTH:
        rows[bar_row][x] = "[grey50]⟧[/]"

def visible_mood(pet: Pet) -> str:
    state = performance_state(pet)
    if state in {"hungry", "gloomy", "playful"}:
        return state
    return pet_mood(pet)
