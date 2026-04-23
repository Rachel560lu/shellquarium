from __future__ import annotations

from collections import deque
import random
import time

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Footer, Header, Input, Static

from shellquarium.core.persistence import delete_pet, load_pet, save_pet
from shellquarium.core.pet import Pet
from shellquarium.ui.themes import (
    DEFAULT_PET_POSITION,
    PET_HEIGHT,
    PET_WIDTH,
    SCENE_HEIGHT,
    SCENE_WIDTH,
    performance_line,
    render_scene_with_reaction,
    visible_mood,
)

FOCUS_TARGETS = ("crab", "pet", "shell")
SHOP_ITEMS = (
    ("Seaweed Ribbon", 3),
    ("Bubble Stone", 5),
    ("Pink Star Clip", 7),
    ("Moon Shell Lamp", 9),
)
FOCUS_LABELS = {
    "crab": "Pomodoro Crab",
    "pet": "Jelly Pet",
    "shell": "Shell Shop",
}
POMODORO_MODE_LABELS = {
    "idle": "Idle",
    "focus": "Focus",
    "break": "Break",
}


class TerminalPetApp(App):
    TITLE = "Terminal Pet"
    FOCUS_DURATION_SECONDS = 25 * 60
    BREAK_DURATION_SECONDS = 5 * 60
    CSS = """
    Screen {
        background: $surface;
    }

    #root {
        padding: 0 1;
    }

    #pet-panel, #shop-panel, #event-panel, #new-pet-panel, #pet-status {
        border: round $primary;
        padding: 0 1;
        margin-bottom: 0;
    }

    #pet-panel {
        height: auto;
    }

    #pet-sprite {
        width: 1fr;
        height: auto;
        content-align: center middle;
    }

    #new-pet-panel {
        height: auto;
    }

    #name-input {
        width: 24;
    }

    #shop-panel {
        height: auto;
    }

    #event-log {
        height: 8;
    }
    """

    BINDINGS = [
        ("left", "focus_left", "Focus Left"),
        ("right", "focus_right", "Focus Right"),
        ("up", "shop_up", "Shop Up"),
        ("down", "shop_down", "Shop Down"),
        ("enter", "toggle_pomodoro", "Start/Pause Timer"),
        ("x", "stop_pomodoro", "Stop Timer"),
        ("q", "quit", "Quit"),
        ("f", "feed", "Feed"),
        ("p", "play", "Play"),
        ("c", "clean", "Clean"),
        ("h", "heal", "Heal"),
        ("d", "discipline", "Discipline"),
        ("s", "sleep", "Sleep"),
        ("r", "reset", "Reset"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.pet = load_pet()
        self.events: deque[str] = deque(maxlen=8)
        self._frame_index = 0
        self.last_feedback = "Ready."
        self._reaction_name: str | None = None
        self._reaction_ticks_remaining = 0
        self._expression_name: str | None = None
        self._expression_ticks_remaining = 0
        self._pet_position = DEFAULT_PET_POSITION
        self._pet_is_moving = False
        self._focus_index = 1
        self._shop_index = 0
        self._pomodoro_mode = "idle"
        self._pomodoro_running = False
        self._pomodoro_end_at: float | None = None
        self._pomodoro_seconds_left = self.FOCUS_DURATION_SECONDS
        self._pomodoros_completed = 0
        self._scene_mode = "tank"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="root"):
            yield Static(id="new-pet-panel")
            with Vertical(id="pet-panel"):
                yield Static(id="pet-sprite")
            yield Static(id="shop-panel")
            yield Static(id="pet-status")
            yield Static(id="event-panel")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self._tick_pet)
        self.set_interval(0.45, self._advance_animation)
        self._refresh_view()

    @property
    def selected_target(self) -> str:
        return FOCUS_TARGETS[self._focus_index]

    def action_focus_left(self) -> None:
        if self.pet is None or self._scene_mode == "pomodoro":
            return
        self._focus_index = (self._focus_index - 1) % len(FOCUS_TARGETS)
        self._refresh_view()

    def action_focus_right(self) -> None:
        if self.pet is None or self._scene_mode == "pomodoro":
            return
        self._focus_index = (self._focus_index + 1) % len(FOCUS_TARGETS)
        self._refresh_view()

    def action_shop_up(self) -> None:
        if self.pet is None or self.selected_target != "shell":
            return
        self._shop_index = (self._shop_index - 1) % len(SHOP_ITEMS)
        self._refresh_view()

    def action_shop_down(self) -> None:
        if self.pet is None or self.selected_target != "shell":
            return
        self._shop_index = (self._shop_index + 1) % len(SHOP_ITEMS)
        self._refresh_view()

    def action_toggle_pomodoro(self) -> None:
        if self.pet is None or self.selected_target != "crab":
            return
        if self._pomodoro_mode == "idle":
            self._start_pomodoro_mode("focus")
        elif self._pomodoro_running:
            self._pause_pomodoro()
        else:
            self._resume_pomodoro()
        self._refresh_view()

    def action_stop_pomodoro(self) -> None:
        if self.pet is None or self.selected_target != "crab":
            return
        if self._pomodoro_mode == "idle":
            return
        self._reset_pomodoro()
        self._record_events(["Pomodoro crab drifted back to idle."])
        self._refresh_view()

    def action_feed(self) -> None:
        self._run_pet_action("feed")

    def action_play(self) -> None:
        self._run_pet_action("play")

    def action_clean(self) -> None:
        self._run_pet_action("clean")

    def action_heal(self) -> None:
        self._run_pet_action("heal")

    def action_discipline(self) -> None:
        self._run_pet_action("discipline_pet")

    def action_sleep(self) -> None:
        self._run_pet_action("toggle_lights")

    def action_reset(self) -> None:
        self._reset_pet()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "hatch":
            self._hatch_pet()

    def _tick_pet(self) -> None:
        if self.pet is None:
            return
        self._record_events(self.pet.tick())
        self._record_events(self._update_pomodoro(time.time()))
        save_pet(self.pet)
        self._refresh_view()

    def _advance_animation(self) -> None:
        self._frame_index += 1
        self._advance_pet_motion()
        if self._reaction_ticks_remaining > 0:
            self._reaction_ticks_remaining -= 1
            if self._reaction_ticks_remaining == 0:
                self._reaction_name = None
        if self._expression_ticks_remaining > 0:
            self._expression_ticks_remaining -= 1
            if self._expression_ticks_remaining == 0:
                self._expression_name = None
        self._refresh_pet_panel()
        self._refresh_status_panel()
        self._refresh_shop_panel()

    def _advance_pet_motion(self) -> None:
        if self.pet is None or not self.pet.is_alive:
            self._pet_is_moving = False
            return
        dx, dy = random.choice(((0, -1), (0, 1), (-1, 0), (1, 0), (0, 0)))
        current_x, current_y = self._pet_position
        max_x = SCENE_WIDTH - PET_WIDTH
        max_y = SCENE_HEIGHT - PET_HEIGHT
        next_x = max(0, min(max_x, current_x + dx))
        next_y = max(0, min(max_y, current_y + dy))
        self._pet_is_moving = (next_x, next_y) != self._pet_position
        self._pet_position = (next_x, next_y)

    def _start_pomodoro_mode(self, mode: str) -> None:
        duration = self.FOCUS_DURATION_SECONDS if mode == "focus" else self.BREAK_DURATION_SECONDS
        self._pomodoro_mode = mode
        self._pomodoro_running = True
        self._pomodoro_seconds_left = duration
        self._pomodoro_end_at = time.time() + duration
        if mode == "focus":
            self._scene_mode = "pomodoro"
            self._record_events(["Pomodoro crab started a focus session."])
        else:
            self._record_events(["Break time started."])

    def _pause_pomodoro(self) -> None:
        self._pomodoro_seconds_left = self._seconds_left(time.time())
        self._pomodoro_running = False
        self._pomodoro_end_at = None
        self._record_events(["Pomodoro paused."])

    def _resume_pomodoro(self) -> None:
        self._pomodoro_running = True
        self._pomodoro_end_at = time.time() + self._pomodoro_seconds_left
        self._record_events(["Pomodoro resumed."])

    def _reset_pomodoro(self) -> None:
        self._pomodoro_mode = "idle"
        self._pomodoro_running = False
        self._pomodoro_end_at = None
        self._pomodoro_seconds_left = self.FOCUS_DURATION_SECONDS
        self._scene_mode = "tank"

    def _seconds_left(self, now: float | None = None) -> int:
        now = now or time.time()
        if self._pomodoro_mode == "idle":
            return self.FOCUS_DURATION_SECONDS
        if not self._pomodoro_running or self._pomodoro_end_at is None:
            return max(0, self._pomodoro_seconds_left)
        return max(0, int(self._pomodoro_end_at - now + 0.999))

    def _update_pomodoro(self, now: float) -> list[str]:
        if self._pomodoro_mode == "idle" or not self._pomodoro_running or self._pomodoro_end_at is None:
            return []
        seconds_left = self._seconds_left(now)
        self._pomodoro_seconds_left = seconds_left
        if seconds_left > 0:
            return []

        events: list[str] = []
        if self._pomodoro_mode == "focus":
            self._pomodoros_completed += 1
            self.pet.shells += 1
            events.append("Focus session complete. Pomodoro crab found a reward shell.")
            self._pomodoro_mode = "break"
            self._pomodoro_running = True
            self._pomodoro_seconds_left = self.BREAK_DURATION_SECONDS
            self._pomodoro_end_at = now + self.BREAK_DURATION_SECONDS
            events.append("Break time started.")
            return events

        events.append("Break finished. Pomodoro crab is ready again.")
        self._reset_pomodoro()
        return events

    def _run_pet_action(self, action_name: str) -> None:
        if self.pet is None:
            self._record_events(["Create a pet first."])
            self._refresh_view()
            return
        action = getattr(self.pet, action_name)
        self._record_events(self.pet.tick())
        action_result = action()
        self._record_events([action_result])
        self._trigger_reaction(action_name, action_result)
        save_pet(self.pet)
        self._refresh_view()

    def _trigger_reaction(self, action_name: str, action_result: str) -> None:
        blocked_markers = (
            "already",
            "cannot",
            "not ready",
            "nothing to clean",
            "not sick",
            "ignores",
        )
        if any(marker in action_result.lower() for marker in blocked_markers):
            self._reaction_name = None
            self._reaction_ticks_remaining = 0
            self._expression_name = None
            self._expression_ticks_remaining = 0
            return

        if action_name == "play":
            self._reaction_name = None
            self._reaction_ticks_remaining = 0
            self._expression_name = "joy"
            self._expression_ticks_remaining = 4
            return

        self._reaction_name = action_name
        self._reaction_ticks_remaining = 2

    def _hatch_pet(self) -> None:
        input_widget = self.query_one("#name-input", Input)
        name = input_widget.value.strip() or "Tama"
        self.pet = Pet(name=name)
        self._pet_position = DEFAULT_PET_POSITION
        self._pet_is_moving = False
        self._focus_index = 1
        self._shop_index = 0
        self._reset_pomodoro()
        save_pet(self.pet)
        input_widget.value = ""
        self._record_events([f"A new egg named {name} is waiting."])
        self._refresh_view()

    def _reset_pet(self) -> None:
        delete_pet()
        self.pet = None
        self._pet_position = DEFAULT_PET_POSITION
        self._pet_is_moving = False
        self._focus_index = 1
        self._shop_index = 0
        self._reset_pomodoro()
        self._record_events(["Saved pet deleted."])
        self._refresh_view()

    def _record_events(self, entries: list[str]) -> None:
        for entry in entries:
            if entry:
                self.last_feedback = entry
                self.events.appendleft(entry)

    def _status_summary_lines(self) -> list[str]:
        if self.pet is None:
            return []
        return [
            f"Hunger {self.pet.hunger}/4   Happy {self.pet.happiness}/4   Health {self.pet.health}/4",
            f"Weight {self.pet.weight}   Poop {self.pet.poop}   Shells {self.pet.shells}",
            f"Discipline {self.pet.discipline}/4   Mistakes {self.pet.care_mistakes}   Age {self.pet.age_seconds}s",
        ]

    def _selection_label(self) -> str:
        return FOCUS_LABELS[self.selected_target]

    def _selection_hint(self) -> str:
        hints = {
            "crab": "Pomodoro crab",
            "pet": f"{self.pet.name if self.pet else 'Jelly'} pet",
            "shell": "Shell shop",
        }
        return hints[self.selected_target]

    def _pomodoro_clock_text(self) -> str:
        seconds_left = self._seconds_left(time.time())
        minutes, seconds = divmod(seconds_left, 60)
        return f"{minutes:02d}:{seconds:02d}"

    def _pomodoro_panel_lines(self) -> list[str]:
        state = "Running" if self._pomodoro_running else "Paused" if self._pomodoro_mode != "idle" else "Ready"
        seconds_left = self._seconds_left(time.time())
        minutes, seconds = divmod(seconds_left, 60)
        return [
            "[b]Pomodoro Crab[/b]",
            f"Mode: {POMODORO_MODE_LABELS[self._pomodoro_mode]}",
            f"Time Left: {minutes:02d}:{seconds:02d}",
            f"Completed: {self._pomodoros_completed}",
            f"State: {state}",
            "",
            "Enter: start / pause / resume",
            "x: stop session",
        ]

    def _refresh_view(self) -> None:
        self._refresh_new_pet_panel()
        self._refresh_pet_panel()
        self._refresh_shop_panel()
        self._refresh_status_panel()
        self._refresh_event_panel()

    def _refresh_new_pet_panel(self) -> None:
        panel = self.query_one("#new-pet-panel", Static)
        if self.pet is None:
            panel.update(
                "[b]No pet yet.[/b]\n\nEnter a name and hatch a new egg below."
            )
            self._ensure_hatch_controls("Hatch")
        elif not self.pet.is_alive:
            panel.update(
                f"[b]{self.pet.name}[/b] has died.\n\nEnter a name to hatch a new pet."
            )
            self._ensure_hatch_controls("Hatch New Pet")
        else:
            panel.remove_children()
            panel.update(f"[b]{self.pet.name}[/b] is currently your active pet.")

    def _ensure_hatch_controls(self, button_label: str) -> None:
        panel = self.query_one("#new-pet-panel", Static)
        name_input = panel.query("#name-input")
        hatch_button = panel.query("#hatch")

        if not name_input:
            panel.mount(Input(placeholder="Pet name", id="name-input"))
        if not hatch_button:
            panel.mount(Button(button_label, id="hatch", variant="success"))
        else:
            panel.query_one("#hatch", Button).label = button_label

    def _refresh_pet_panel(self) -> None:
        sprite = self.query_one("#pet-sprite", Static)
        if self.pet is None:
            sprite.update("( no pet )")
            return
        sprite.update(
            render_scene_with_reaction(
                "tank",
                self.pet,
                self._frame_index,
                self._reaction_name,
                self._frame_index,
                mood_override=self._expression_name,
                pet_position=self._pet_position,
                is_moving=self._pet_is_moving,
                selected_target=self.selected_target,
                scene_mode=self._scene_mode,
                clock_text=self._pomodoro_clock_text() if self._scene_mode == "pomodoro" else None,
            )
        )

    def _refresh_shop_panel(self) -> None:
        panel = self.query_one("#shop-panel", Static)
        if self.pet is None:
            panel.update("Use left and right to inspect the tank once you hatch a pet.")
            return
        if self.selected_target == "crab":
            panel.update("\n".join(self._pomodoro_panel_lines()))
            return
        if self.selected_target != "shell":
            panel.update(f"Focus: [b]{self._selection_label()}[/b]\n{self._selection_hint()}")
            return

        lines = ["[b]Shell Shop[/b]", "Use up and down to browse.", ""]
        for index, (name, price) in enumerate(SHOP_ITEMS):
            marker = ">" if index == self._shop_index else " "
            lines.append(f"{marker} {name} - {price} shells")
        panel.update("\n".join(lines))

    def _refresh_status_panel(self) -> None:
        status = self.query_one("#pet-status", Static)
        if self.pet is None:
            status.update(f"Recent: {self.last_feedback}\nHatch a pet to start playing.")
            return
        mood = visible_mood(self.pet)
        status.update(
            f"{self.pet.name}   {self.pet.stage.value} / {mood}\n"
            f"Selected: {self._selection_hint()}\n"
            f"Recent: {self.last_feedback}\n"
            f"{performance_line(self.pet)}\n"
            + "\n".join(self._status_summary_lines())
        )

    def _refresh_event_panel(self) -> None:
        panel = self.query_one("#event-panel", Static)
        if not self.events:
            panel.update("Recent events will appear here.")
            return
        panel.update("\n".join(f"- {event}" for event in self.events))
