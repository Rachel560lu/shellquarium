from __future__ import annotations

from collections import deque
import random
import time

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Resize
from textual.widgets import Button, Footer, Header, Input, Static

from shellquarium.core.persistence import delete_pet, load_pet, save_pet
from shellquarium.core.collection import CHARACTERS, STREAK_CHEST_INTERVAL, roll_streak_chest_drop
from shellquarium.core.pet import Pet
from shellquarium.core.progression import (
    evaluate_achievements,
    record_counter,
    task_definitions,
    task_state,
    update_progress,
    virtual_level,
)
from shellquarium.core.shop import SHOP_CATALOG, buy_item, use_item
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
    "seaweed_ribbon",
    "bubble_stone",
    "pink_star_clip",
    "moon_shell_lamp",
    "seaweed_snack",
    "bubble_tea",
    "tiny_sponge",
    "pearl_tonic",
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
INFO_PANEL_SCROLL_IDS = (
    "shop-panel-scroll",
    "pet-status-scroll",
    "event-panel-scroll",
)
INFO_MENU_ITEMS = (
    "recent",
    "stats",
    "tasks",
    "inventory",
    "collection",
)
INFO_MENU_LABELS = {
    "recent": "Recent Events",
    "stats": "Stats",
    "tasks": "Tasks",
    "inventory": "Inventory",
    "collection": "Collection",
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
        height: 1fr;
    }

    #pet-panel, #new-pet-panel {
        border: round $primary;
        padding: 0 1;
        margin-bottom: 0;
    }

    #pet-panel {
        height: 2fr;
        min-height: 18;
    }

    #pet-sprite {
        width: 1fr;
        height: 100%;
        content-align: center middle;
    }

    #new-pet-panel {
        height: auto;
    }

    #name-input {
        width: 24;
    }

    #info-panels {
        height: 1fr;
        min-height: 8;
        layout: grid;
        grid-size: 3;
        grid-columns: 1fr 1fr 1fr;
        grid-gutter: 1;
    }

    .info-panel {
        border: round $primary;
        padding: 0 1;
        margin-bottom: 0;
        height: 1fr;
        min-height: 3;
        width: 100%;
    }

    .info-panel.active-panel {
        border: round $accent;
    }

    .panel-content {
        width: 1fr;
    }

    Screen.compact-layout #pet-panel {
        height: 18;
        min-height: 14;
    }

    Screen.compact-layout #info-panels {
        height: 1fr;
        min-height: 6;
    }
    """

    BINDINGS = [
        ("left", "focus_left", "Focus Left"),
        ("right", "focus_right", "Focus Right"),
        ("up", "shop_up", "Shop Up"),
        ("down", "shop_down", "Shop Down"),
        ("[", "previous_info_panel", "Prev Panel"),
        ("]", "next_info_panel", "Next Panel"),
        ("pageup", "page_up_info_panel", "Panel Up"),
        ("pagedown", "page_down_info_panel", "Panel Down"),
        ("home", "scroll_home_info_panel", "Panel Top"),
        ("end", "scroll_end_info_panel", "Panel Bottom"),
        ("enter", "primary_action", "Select / Buy / Timer"),
        ("x", "stop_pomodoro", "Stop Timer"),
        ("o", "toggle_collection", "Collection"),
        ("i", "toggle_inventory", "Inventory"),
        ("u", "use_inventory", "Use Item"),
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
        self._inventory_index = 0
        self._shell_panel_mode = "shop"
        self._pomodoro_mode = "idle"
        self._pomodoro_running = False
        self._pomodoro_end_at: float | None = None
        self._pomodoro_seconds_left = self.FOCUS_DURATION_SECONDS
        self._pomodoros_completed = 0
        self._scene_mode = "tank"
        self._pomodoro_bar_symbols: list[str] = []
        self._active_info_panel_index = 1
        self._info_menu_index = 0

    def _pomodoro_encouragement(self, now: float | None = None) -> str:
        now = now or time.time()
        lines = (
            "One small step.",
            "Stay with it.",
            "You can do this.",
            "Deep breath, focus.",
            "Keep going.",
        )
        return lines[int(now // 6) % len(lines)]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="root"):
            yield Static(id="new-pet-panel")
            with Vertical(id="pet-panel"):
                yield Static(id="pet-sprite")
            with Horizontal(id="info-panels"):
                with VerticalScroll(id="shop-panel-scroll", classes="info-panel"):
                    yield Static(id="shop-panel", classes="panel-content")
                with VerticalScroll(id="pet-status-scroll", classes="info-panel"):
                    yield Static(id="pet-status", classes="panel-content")
                with VerticalScroll(id="event-panel-scroll", classes="info-panel"):
                    yield Static(id="event-panel", classes="panel-content")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self._tick_pet)
        self.set_interval(0.45, self._advance_animation)
        self._update_layout_mode()
        self._update_active_info_panel()
        self._refresh_view()
        for panel_id in INFO_PANEL_SCROLL_IDS:
            self.query_one(f"#{panel_id}").can_focus = False
        self.set_focus(None)

    def _update_layout_mode(self) -> None:
        """Use the compact layout only when the terminal cannot fit the hero tank."""
        if self.size.height < 38:
            self.add_class("compact-layout")
        else:
            self.remove_class("compact-layout")

    def on_resize(self, event: Resize) -> None:
        del event
        self._update_layout_mode()
        if self.pet is not None and self.is_mounted:
            self._refresh_pet_panel()

    def _scene_height(self) -> int:
        """Return the available inner tank height, preserving the compact baseline."""
        if "compact-layout" in self.classes:
            return SCENE_HEIGHT
        try:
            sprite_height = int(self.query_one("#pet-sprite", Static).size.height)
        except Exception:
            return SCENE_HEIGHT
        return max(SCENE_HEIGHT, sprite_height - 2)

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
        if self._active_info_panel_index == 2:
            if self._current_info_menu() == "inventory":
                self._cycle_inventory(-1)
                self._refresh_event_panel()
                return
            self._cycle_info_menu(-1)
            self._refresh_event_panel()
            return
        if self.pet is None or self.selected_target != "shell":
            return
        self._shop_index = (self._shop_index - 1) % len(SHOP_ITEMS)
        self._refresh_view()

    def action_shop_down(self) -> None:
        if self._active_info_panel_index == 2:
            if self._current_info_menu() == "inventory":
                self._cycle_inventory(1)
                self._refresh_event_panel()
                return
            self._cycle_info_menu(1)
            self._refresh_event_panel()
            return
        if self.pet is None or self.selected_target != "shell":
            return
        self._shop_index = (self._shop_index + 1) % len(SHOP_ITEMS)
        self._refresh_view()

    def action_previous_info_panel(self) -> None:
        self._active_info_panel_index = (self._active_info_panel_index - 1) % len(INFO_PANEL_SCROLL_IDS)
        self._update_active_info_panel()

    def action_next_info_panel(self) -> None:
        self._active_info_panel_index = (self._active_info_panel_index + 1) % len(INFO_PANEL_SCROLL_IDS)
        self._update_active_info_panel()

    def action_page_up_info_panel(self) -> None:
        self._active_info_panel().scroll_page_up(animate=False)

    def action_page_down_info_panel(self) -> None:
        self._active_info_panel().scroll_page_down(animate=False)

    def action_scroll_home_info_panel(self) -> None:
        self._active_info_panel().scroll_home(animate=False)

    def action_scroll_end_info_panel(self) -> None:
        self._active_info_panel().scroll_end(animate=False)

    def action_toggle_collection(self) -> None:
        if self.pet is None:
            return
        self._shell_panel_mode = "collection"
        self._info_menu_index = INFO_MENU_ITEMS.index("collection")
        self._active_info_panel_index = 2
        self._update_active_info_panel()
        self.pet.collection_unseen = False
        save_pet(self.pet)
        self._refresh_view()

    def action_toggle_inventory(self) -> None:
        if self.pet is None:
            return
        self._info_menu_index = INFO_MENU_ITEMS.index("inventory")
        self._active_info_panel_index = 2
        self._update_active_info_panel()
        self._refresh_event_panel()

    def action_use_inventory(self) -> None:
        if self.pet is None:
            return
        item_ids = self._inventory_item_ids()
        if not item_ids:
            self._record_events(["Your inventory is empty."])
            self._refresh_view()
            return
        item_id = item_ids[self._inventory_index % len(item_ids)]
        message = use_item(self.pet, item_id)
        self._record_events([message])
        if not self._is_blocked_action(message):
            record_counter(self.pet, "shop_use")
            self._record_events(update_progress(self.pet))
        save_pet(self.pet)
        self._refresh_view()

    def action_primary_action(self) -> None:
        if self.pet is None:
            return
        if self.selected_target == "shell":
            item_id = SHOP_ITEMS[self._shop_index]
            message = buy_item(self.pet, item_id)
            self._record_events([message])
            if not self._is_blocked_action(message):
                self._record_events(update_progress(self.pet))
            save_pet(self.pet)
            self._refresh_view()
            return
        if self.selected_target == "crab":
            self.action_toggle_pomodoro()

    def _cycle_inventory(self, step: int) -> None:
        item_count = len(self._inventory_item_ids())
        if item_count:
            self._inventory_index = (self._inventory_index + step) % item_count

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
        if self.pet.pomodoro_streak:
            self.pet.pomodoro_streak = 0
            self._record_events(["Pomodoro stopped. Streak reset."])
        else:
            self._record_events(["Pomodoro crab drifted back to idle."])
        save_pet(self.pet)
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
        # During Pomodoro mode, freeze the pet simulation so it won't decay,
        # get sick, or generate distracting events while the user focuses.
        if self._scene_mode != "pomodoro":
            self._record_events(self.pet.tick())
        self._record_events(self._update_pomodoro(time.time()))
        self._record_events(update_progress(self.pet))
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
        if self.pet is None:
            self._pet_is_moving = False
            return
        dx, dy = random.choice(((0, -1), (0, 1), (-1, 0), (1, 0), (0, 0)))
        current_x, current_y = self._pet_position
        max_x = SCENE_WIDTH - PET_WIDTH
        scene_height = self._scene_height()
        max_y = scene_height - PET_HEIGHT
        min_y = 0
        if self._scene_mode == "pomodoro":
            # Keep the pet away from the timer area, but let it keep swimming.
            min_y = max(0, scene_height - PET_HEIGHT - 2)
        next_x = max(0, min(max_x, current_x + dx))
        next_y = max(min_y, min(max_y, current_y + dy))
        self._pet_is_moving = (next_x, next_y) != self._pet_position
        self._pet_position = (next_x, next_y)

    def _start_pomodoro_mode(self, mode: str) -> None:
        duration = self.FOCUS_DURATION_SECONDS if mode == "focus" else self.BREAK_DURATION_SECONDS
        self._pomodoro_mode = mode
        self._pomodoro_running = True
        self._pomodoro_seconds_left = duration
        self._pomodoro_end_at = time.time() + duration
        self._pomodoro_bar_symbols = []
        if mode == "focus":
            self._scene_mode = "pomodoro"
            # Nudge the pet into the safe swimming band for the timer scene.
            min_y = max(0, self._scene_height() - PET_HEIGHT - 2)
            self._pet_position = (self._pet_position[0], max(self._pet_position[1], min_y))
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
        self._pomodoro_bar_symbols = []

    def _seconds_left(self, now: float | None = None) -> int:
        now = now or time.time()
        if self._pomodoro_mode == "idle":
            return self.FOCUS_DURATION_SECONDS
        if not self._pomodoro_running or self._pomodoro_end_at is None:
            return max(0, self._pomodoro_seconds_left)
        return max(0, int(self._pomodoro_end_at - now + 0.999))

    def _active_info_panel(self) -> VerticalScroll:
        panel_id = INFO_PANEL_SCROLL_IDS[self._active_info_panel_index]
        return self.query_one(f"#{panel_id}", VerticalScroll)

    def _update_active_info_panel(self) -> None:
        if not self.children:
            return
        for index, panel_id in enumerate(INFO_PANEL_SCROLL_IDS):
            panel = self.query_one(f"#{panel_id}", VerticalScroll)
            if index == self._active_info_panel_index:
                panel.add_class("active-panel")
            else:
                panel.remove_class("active-panel")

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
            self.pet.pomodoro_streak += 1
            record_counter(self.pet, "focus")
            record_counter(self.pet, "shell")
            events.extend(self._open_streak_chest_if_ready())
            events.extend(update_progress(self.pet))
            self._pomodoro_mode = "break"
            self._pomodoro_running = True
            self._pomodoro_seconds_left = self.BREAK_DURATION_SECONDS
            self._pomodoro_end_at = now + self.BREAK_DURATION_SECONDS
            events.append("Break time started.")
            return events

        events.append("Break finished. Pomodoro crab is ready again.")
        self._reset_pomodoro()
        return events

    def _open_streak_chest_if_ready(self) -> list[str]:
        if self.pet is None:
            return []
        if self.pet.pomodoro_streak <= 0 or self.pet.pomodoro_streak % STREAK_CHEST_INTERVAL != 0:
            return []

        drop = roll_streak_chest_drop(random)
        self.pet.streak_chests_opened += 1
        record_counter(self.pet, "chest")
        self.pet.collection_unseen = True

        if drop.kind == "shell":
            if drop.shell_rarity == "rare":
                self.pet.collected_shell_rare += drop.amount
                item_text = f"{drop.amount}x Rare Shell"
            else:
                self.pet.collected_shell_common += drop.amount
                item_text = f"{drop.amount}x Common Shell"
        else:
            assert drop.character is not None
            self.pet.character_shards[drop.character] = self.pet.character_shards.get(drop.character, 0) + drop.amount
            required = CHARACTERS.get(drop.character, 0)
            have = self.pet.character_shards[drop.character]
            if required and have >= required and drop.character not in self.pet.unlocked_characters:
                self.pet.unlocked_characters.append(drop.character)
                item_text = f"{drop.amount}x {drop.character} Shard (UNLOCKED!)"
            else:
                suffix = f" ({have}/{required})" if required else ""
                item_text = f"{drop.amount}x {drop.character} Shard{suffix}"

        return [
            f"Streak Chest opened (streak {self.pet.pomodoro_streak}). You found: {item_text}.",
            "Collection updated. Press 'o' in Shell Shop to view.",
        ]

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
        if not self._is_blocked_action(action_result):
            counter_name = {
                "feed": "feed",
                "play": "play",
                "clean": "clean",
                "heal": "heal",
                "discipline_pet": "discipline",
                "toggle_lights": "sleep",
            }[action_name]
            record_counter(self.pet, counter_name)
            record_counter(self.pet, "care_actions")
            self._record_events(update_progress(self.pet))
        save_pet(self.pet)
        self._refresh_view()

    @staticmethod
    def _is_blocked_action(action_result: str) -> bool:
        blocked_markers = (
            "already",
            "cannot",
            "not ready",
            "nothing to clean",
            "not sick",
            "ignores",
            "do not have",
        )
        return any(marker in action_result.lower() for marker in blocked_markers)

    def _trigger_reaction(self, action_name: str, action_result: str) -> None:
        if self._is_blocked_action(action_result):
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
        self._inventory_index = 0
        self._shell_panel_mode = "shop"
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
        self._inventory_index = 0
        self._shell_panel_mode = "shop"
        self._reset_pomodoro()
        self._record_events(["Saved pet deleted."])
        self._refresh_view()

    def _record_events(self, entries: list[str]) -> None:
        for entry in entries:
            if entry:
                self.last_feedback = entry
                self.events.appendleft(entry)

    def _cycle_info_menu(self, step: int) -> None:
        self._info_menu_index = (self._info_menu_index + step) % len(INFO_MENU_ITEMS)

    def _current_info_menu(self) -> str:
        return INFO_MENU_ITEMS[self._info_menu_index]

    def _status_summary_lines(self) -> list[str]:
        if self.pet is None:
            return []
        streak_note = f"   Streak {self.pet.pomodoro_streak}" if self.pet.pomodoro_streak else ""
        return [
            f"Hunger {self.pet.hunger}/4   Happy {self.pet.happiness}/4   Health {self.pet.health}/4",
            f"Weight {self.pet.weight}   Poop {self.pet.poop}   Shells {self.pet.shells}{streak_note}",
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
        streak = self.pet.pomodoro_streak if self.pet is not None else 0
        return [
            "[b]Pomodoro Crab[/b]",
            f"Mode: {POMODORO_MODE_LABELS[self._pomodoro_mode]}",
            f"Time Left: {minutes:02d}:{seconds:02d}",
            f"Completed: {self._pomodoros_completed}",
            f"Streak: {streak}",
            f"State: {state}",
            "",
            "Enter: start / pause / resume",
            "x: stop session",
        ]

    def _action_panel_lines(self) -> list[str]:
        if self.pet is None:
            return [
                "[b]Actions[/b]",
                "",
                "Hatch a pet to unlock care, shop, and pomodoro actions.",
            ]

        if self.selected_target == "crab":
            state_label = "Pause session" if self._pomodoro_running else "Start focus" if self._pomodoro_mode == "idle" else "Resume session"
            return [
                "[b]Actions[/b]",
                "Pomodoro Crab",
                "",
                f"> Enter  {state_label}",
                "  x      Stop session",
                f"  Mode   {POMODORO_MODE_LABELS[self._pomodoro_mode]}",
                f"  Timer  {self._pomodoro_clock_text()}",
            ]

        if self.selected_target == "shell":
            lines = [
                "[b]Actions[/b]",
                "Shell Shop",
                "",
                "Use up/down to browse.",
                "Enter to buy. i for Inventory.",
                "o for Collection.",
                "",
            ]
            for index, item_id in enumerate(SHOP_ITEMS):
                item = SHOP_CATALOG[item_id]
                marker = ">" if index == self._shop_index else " "
                if item.decorative:
                    status = "owned" if item_id in self.pet.owned_decorations else "collection"
                    lines.append(f"{marker} {item.name} - {item.price} shells ({status})")
                else:
                    stock = self.pet.inventory.get(item_id, 0)
                    lines.append(f"{marker} {item.name} - {item.price} shells (x{stock})")
            return lines

        return [
            "[b]Actions[/b]",
            "Pet Care",
            "",
            "> f  Feed",
            "  p  Play",
            "  c  Clean",
            "  h  Heal",
            "  d  Discipline",
            "  s  Sleep",
        ]

    def _status_card_lines(self) -> list[str]:
        if self.pet is None:
            return [
                "[b]Main Menu[/b]",
                "No pet yet",
                "",
                "Recent: Hatch a pet to begin.",
                "Create a jelly, then explore care, shells, and focus mode.",
            ]

        mood = visible_mood(self.pet)
        return [
            f"[b]{self.pet.name}[/b]",
            f"{self.pet.stage.value} / {mood}",
            "",
            f"Recent: {self.last_feedback}",
            performance_line(self.pet),
            "",
            f"Focus: {self._selection_label()}",
            f"Selected: {self._selection_hint()}",
            f"Level: {virtual_level(self.pet.xp)}   XP: {self.pet.xp}",
            f"Shells: {self.pet.shells}   Streak: {self.pet.pomodoro_streak}",
        ]

    def _stats_panel_lines(self) -> list[str]:
        if self.pet is None:
            return ["No pet stats yet."]
        return [
            f"Level       {virtual_level(self.pet.xp)}",
            f"XP          {self.pet.xp}",
            f"Health      {self.pet.health}/4",
            f"Hunger      {self.pet.hunger}/4",
            f"Happiness   {self.pet.happiness}/4",
            f"Discipline  {self.pet.discipline}/4",
            f"Weight      {self.pet.weight}",
            f"Poop        {self.pet.poop}",
            f"Mistakes    {self.pet.care_mistakes}",
            f"Age         {self.pet.age_seconds}s",
        ]

    def _task_panel_lines(self) -> list[str]:
        if self.pet is None:
            return ["No tasks until you hatch a pet."]
        daily_state = task_state(self.pet, "daily")
        weekly_state = task_state(self.pet, "weekly")
        lines = ["[b]Daily Tasks[/b]"]
        for definition in task_definitions("daily"):
            progress = daily_state["counters"].get(definition.counter, 0)
            claimed = "✓" if definition.task_id in daily_state["claimed"] else " "
            lines.append(f"[{claimed}] {definition.label} ({min(progress, definition.target)}/{definition.target})")
        lines.append("")
        lines.append("[b]Weekly Tasks[/b]")
        for definition in task_definitions("weekly"):
            progress = weekly_state["counters"].get(definition.counter, 0)
            claimed = "✓" if definition.task_id in weekly_state["claimed"] else " "
            lines.append(f"[{claimed}] {definition.label} ({min(progress, definition.target)}/{definition.target})")
        return lines

    def _inventory_item_ids(self) -> list[str]:
        if self.pet is None:
            return []
        return [item_id for item_id in SHOP_ITEMS if self.pet.inventory.get(item_id, 0) > 0]

    def _inventory_panel_lines(self) -> list[str]:
        if self.pet is None:
            return ["No inventory until you hatch a pet."]
        item_ids = self._inventory_item_ids()
        lines = ["[b]Inventory[/b]", "Use up/down to select, u to use.", ""]
        if not item_ids:
            lines.append("Empty. Visit Shell Shop to buy supplies.")
            return lines
        for index, item_id in enumerate(item_ids):
            item = SHOP_CATALOG[item_id]
            marker = ">" if index == self._inventory_index % len(item_ids) else " "
            lines.append(f"{marker} {item.name} x{self.pet.inventory[item_id]}")
        return lines

    def _recent_event_lines(self) -> list[str]:
        if not self.events:
            return ["No events yet."]
        return [f"- {event}" for event in list(self.events)[:6]]

    def _info_panel_lines(self) -> list[str]:
        current_menu = self._current_info_menu()
        lines = ["[b]Menu[/b]"]
        for item in INFO_MENU_ITEMS:
            marker = ">" if item == current_menu else " "
            lines.append(f"{marker} {INFO_MENU_LABELS[item]}")
        lines.append("")

        if current_menu == "recent":
            lines.extend(self._recent_event_lines())
        elif current_menu == "stats":
            lines.extend(self._stats_panel_lines())
        elif current_menu == "tasks":
            lines.extend(self._task_panel_lines())
        elif current_menu == "inventory":
            lines.extend(self._inventory_panel_lines())
        else:
            if self.pet is None:
                lines.append("No collection yet.")
            else:
                lines.extend(self._collection_panel_lines())
        return lines

    def _refresh_view(self) -> None:
        if not self.children:
            return
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
        scene_height = self._scene_height()
        max_x = SCENE_WIDTH - PET_WIDTH
        max_y = scene_height - PET_HEIGHT
        self._pet_position = (
            max(0, min(max_x, self._pet_position[0])),
            max(0, min(max_y, self._pet_position[1])),
        )
        clock_progress: float | None = None
        clock_subtitle: str | None = None
        clock_bar_symbols: list[str] | None = None
        clock_bar_width: int | None = None
        mood_override = self._expression_name
        if self._scene_mode == "pomodoro":
            # Render the pet as calm/healthy during Pomodoro to reduce anxiety.
            mood_override = mood_override or "awake"
            duration = self.FOCUS_DURATION_SECONDS if self._pomodoro_mode == "focus" else self.BREAK_DURATION_SECONDS
            duration = max(1, int(duration))
            seconds_left = self._seconds_left(time.time())
            clock_progress = max(0.0, min(1.0, (duration - seconds_left) / duration))
            clock_subtitle = self._pomodoro_encouragement()
            clock_bar_width = min(30, SCENE_WIDTH - 6)
            filled = int(round(clock_progress * clock_bar_width))
            filled = max(0, min(clock_bar_width, filled))
            symbol_pool = ("𓇼", "⋆", ".", "˚", "𓆉", "𓆝", "𓆡")
            while len(self._pomodoro_bar_symbols) < filled:
                self._pomodoro_bar_symbols.append(random.choice(symbol_pool))
            clock_bar_symbols = self._pomodoro_bar_symbols[:filled]
        sprite.update(
            render_scene_with_reaction(
                "tank",
                self.pet,
                self._frame_index,
                self._reaction_name,
                self._frame_index,
                mood_override=mood_override,
                pet_position=self._pet_position,
                is_moving=self._pet_is_moving,
                selected_target=self.selected_target,
                scene_mode=self._scene_mode,
                clock_text=self._pomodoro_clock_text() if self._scene_mode == "pomodoro" else None,
                clock_progress=clock_progress,
                clock_subtitle=clock_subtitle,
                clock_bar_symbols=clock_bar_symbols,
                clock_bar_width=clock_bar_width,
                scene_height=scene_height,
            )
        )

    def _refresh_shop_panel(self) -> None:
        panel = self.query_one("#shop-panel", Static)
        panel.update("\n".join(self._action_panel_lines()))

    def _collection_panel_lines(self) -> list[str]:
        assert self.pet is not None
        lines: list[str] = ["[b]Collection[/b]", "Press 'o' to return to Collection.", ""]
        lines.extend(
            [
                f"Virtual Level: {virtual_level(self.pet.xp)}",
                f"XP: {self.pet.xp}",
                f"Badges: {len(self.pet.owned_badges)}",
                f"Decorations: {len(self.pet.owned_decorations)}",
                "",
                "[b]Achievement Badges[/b]",
            ]
        )
        if not self.pet.owned_badges:
            lines.append("- (none yet)")
        else:
            lines.extend(f"- {badge}" for badge in self.pet.owned_badges)

        lines.extend(["", "[b]Shop Decorations[/b]"])
        if not self.pet.owned_decorations:
            lines.append("- (none yet)")
        else:
            for item_id in self.pet.owned_decorations:
                lines.append(f"- {SHOP_CATALOG[item_id].name}")

        lines.append("[b]Character Shards[/b]")
        if not self.pet.character_shards:
            lines.append("- (none yet)")
        else:
            for name in sorted(self.pet.character_shards):
                have = self.pet.character_shards[name]
                required = CHARACTERS.get(name)
                unlocked = " (unlocked)" if name in self.pet.unlocked_characters else ""
                progress = f"{have}/{required}" if required else f"{have}"
                lines.append(f"- {name}: {progress}{unlocked}")

        lines.extend(["", "[b]Shell Collection[/b]"])
        lines.append(f"- Common: {self.pet.collected_shell_common}")
        lines.append(f"- Rare: {self.pet.collected_shell_rare}")
        lines.append(f"- Streak chests: {self.pet.streak_chests_opened}")
        return lines

    def _refresh_status_panel(self) -> None:
        status = self.query_one("#pet-status", Static)
        status.update("\n".join(self._status_card_lines()))

    def _refresh_event_panel(self) -> None:
        panel = self.query_one("#event-panel", Static)
        panel.update("\n".join(self._info_panel_lines()))
