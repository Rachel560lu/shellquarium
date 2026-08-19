from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math

from shellquarium.core.pet import Pet


@dataclass(frozen=True)
class TaskDefinition:
    task_id: str
    label: str
    period: str
    counter: str
    target: int
    shells: int
    xp: int


@dataclass(frozen=True)
class AchievementDefinition:
    achievement_id: str
    label: str
    counter: str
    target: int
    xp: int


DAILY_TASKS = (
    TaskDefinition("daily_feed", "Feed your pet once", "daily", "feed", 1, 2, 20),
    TaskDefinition("daily_play", "Play with your pet once", "daily", "play", 1, 2, 20),
    TaskDefinition("daily_focus", "Complete one focus session", "daily", "focus", 1, 3, 30),
)

WEEKLY_TASKS = (
    TaskDefinition("weekly_care", "Perform 10 care actions", "weekly", "care_actions", 10, 8, 80),
    TaskDefinition("weekly_focus", "Complete 5 focus sessions", "weekly", "focus", 5, 10, 100),
    TaskDefinition("weekly_shell", "Earn 5 shells", "weekly", "shell", 5, 10, 100),
)

ACHIEVEMENTS = (
    AchievementDefinition("first_care", "First Care", "feed", 1, 30),
    AchievementDefinition("tidy_tide", "Tidy Tide", "clean", 10, 50),
    AchievementDefinition("playful_current", "Playful Current", "play", 10, 50),
    AchievementDefinition("focus_drifter", "Focus Drifter", "focus", 1, 50),
    AchievementDefinition("steady_current", "Steady Current", "focus_streak", 4, 100),
    AchievementDefinition("task_keeper", "Task Keeper", "daily_tasks", 7, 100),
    AchievementDefinition("pearl_hoard", "Pearl Hoard", "decorations", 3, 120),
    AchievementDefinition("chest_diver", "Chest Diver", "chest", 3, 150),
)

LEVEL_THRESHOLDS = (0, 100, 250, 450, 700, 1000)


def virtual_level(xp: int) -> int:
    if xp < LEVEL_THRESHOLDS[-1]:
        return max(index + 1 for index, threshold in enumerate(LEVEL_THRESHOLDS) if xp >= threshold)
    extra_levels = (xp - LEVEL_THRESHOLDS[-1]) // 300
    return len(LEVEL_THRESHOLDS) + extra_levels


def record_counter(
    pet: Pet,
    counter: str,
    amount: int = 1,
    *,
    now_date: str | None = None,
    now_week: str | None = None,
) -> None:
    if amount <= 0:
        return
    today = now_date or date.today().isoformat()
    week = now_week or _current_week()
    _ensure_task_state(pet, "daily", today)
    _ensure_task_state(pet, "weekly", week)
    pet.lifetime_counters[counter] = pet.lifetime_counters.get(counter, 0) + amount
    pet.daily_task_state["counters"][counter] = pet.daily_task_state["counters"].get(counter, 0) + amount
    pet.weekly_task_state["counters"][counter] = pet.weekly_task_state["counters"].get(counter, 0) + amount


def update_progress(pet: Pet, *, now_date: str | None = None, now_week: str | None = None) -> list[str]:
    today = now_date or date.today().isoformat()
    week = now_week or _current_week()
    events = update_tasks(pet, now_date=today, now_week=week)
    events.extend(evaluate_achievements(pet))
    return events


def update_tasks(
    pet: Pet,
    *,
    now_date: str | None = None,
    now_week: str | None = None,
) -> list[str]:
    today = now_date or date.today().isoformat()
    week = now_week or _current_week()
    _ensure_task_state(pet, "daily", today)
    _ensure_task_state(pet, "weekly", week)
    events: list[str] = []
    for definition in DAILY_TASKS:
        events.extend(_claim_task_if_ready(pet, definition, pet.daily_task_state))
    for definition in WEEKLY_TASKS:
        events.extend(_claim_task_if_ready(pet, definition, pet.weekly_task_state))
    return events


def evaluate_achievements(pet: Pet) -> list[str]:
    events: list[str] = []
    unlocked = set(pet.unlocked_achievements)
    for definition in ACHIEVEMENTS:
        if definition.achievement_id in unlocked:
            continue
        if _achievement_progress(pet, definition.counter) < definition.target:
            continue
        pet.unlocked_achievements.append(definition.achievement_id)
        pet.owned_badges.append(definition.achievement_id)
        pet.xp += definition.xp
        events.append(f"Achievement unlocked: {definition.label}. +{definition.xp} XP.")
    return events


def task_definitions(period: str) -> tuple[TaskDefinition, ...]:
    return DAILY_TASKS if period == "daily" else WEEKLY_TASKS


def task_state(pet: Pet, period: str, *, now_date: str | None = None, now_week: str | None = None) -> dict:
    key = now_date or date.today().isoformat() if period == "daily" else now_week or _current_week()
    _ensure_task_state(pet, period, key)
    return pet.daily_task_state if period == "daily" else pet.weekly_task_state


def _claim_task_if_ready(pet: Pet, definition: TaskDefinition, state: dict) -> list[str]:
    if definition.task_id in state["claimed"]:
        return []
    progress = state["counters"].get(definition.counter, 0)
    if progress < definition.target:
        return []
    state["claimed"].append(definition.task_id)
    pet.shells += definition.shells
    pet.xp += definition.xp
    if definition.period == "daily":
        pet.lifetime_counters["daily_task"] = pet.lifetime_counters.get("daily_task", 0) + 1
    return [
        f"{definition.period.title()} task complete: {definition.label}. "
        f"+{definition.shells} shells, +{definition.xp} XP."
    ]


def _achievement_progress(pet: Pet, counter: str) -> int:
    if counter == "focus_streak":
        return pet.pomodoro_streak
    if counter == "daily_tasks":
        return pet.lifetime_counters.get("daily_task", 0)
    if counter == "decorations":
        return len(pet.owned_decorations)
    return pet.lifetime_counters.get(counter, 0)


def _ensure_task_state(pet: Pet, period: str, key: str) -> None:
    state = pet.daily_task_state if period == "daily" else pet.weekly_task_state
    key_name = "date" if period == "daily" else "week"
    definitions = task_definitions(period)
    if state.get(key_name) == key:
        state.setdefault("counters", {})
        state.setdefault("claimed", [])
        state.setdefault("tasks", [definition.task_id for definition in definitions])
        return
    state.clear()
    state.update(
        {
            key_name: key,
            "tasks": [definition.task_id for definition in definitions],
            "counters": {},
            "claimed": [],
        }
    )


def _current_week() -> str:
    current = date.today().isocalendar()
    return f"{current.year}-W{current.week:02d}"
