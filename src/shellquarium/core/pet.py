from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time


class LifeStage(str, Enum):
    EGG = "egg"
    BABY = "baby"
    CHILD = "child"
    TEEN = "teen"
    ADULT = "adult"
    ELDER = "elder"
    DEAD = "dead"


STAGE_DURATIONS = {
    LifeStage.EGG: 60.0,
    LifeStage.BABY: 5 * 60.0,
    LifeStage.CHILD: 10 * 60.0,
    LifeStage.TEEN: 15 * 60.0,
    LifeStage.ADULT: 20 * 60.0,
}

CRAB_EVENT_INTERVAL = 150.0

STAGE_ORDER = [
    LifeStage.EGG,
    LifeStage.BABY,
    LifeStage.CHILD,
    LifeStage.TEEN,
    LifeStage.ADULT,
    LifeStage.ELDER,
]


@dataclass
class Pet:
    name: str = "Tama"
    stage: LifeStage = LifeStage.EGG
    hunger: int = 4
    happiness: int = 4
    health: int = 4
    discipline: int = 2
    weight: int = 10
    poop: int = 0
    shells: int = 0
    pomodoro_streak: int = 0
    streak_chests_opened: int = 0
    character_shards: dict[str, int] = field(default_factory=dict)
    unlocked_characters: list[str] = field(default_factory=list)
    collected_shell_common: int = 0
    collected_shell_rare: int = 0
    collection_unseen: bool = False
    inventory: dict[str, int] = field(default_factory=dict)
    owned_decorations: list[str] = field(default_factory=list)
    xp: int = 0
    unlocked_achievements: list[str] = field(default_factory=list)
    owned_badges: list[str] = field(default_factory=list)
    daily_task_state: dict = field(default_factory=dict)
    weekly_task_state: dict = field(default_factory=dict)
    lifetime_counters: dict[str, int] = field(default_factory=dict)
    is_sick: bool = False
    lights_on: bool = True
    care_mistakes: int = 0
    born_at: float = field(default_factory=time.time)
    stage_started_at: float = field(default_factory=time.time)
    last_tick_at: float = field(default_factory=time.time)
    last_hunger_decay_at: float = field(default_factory=time.time)
    last_happiness_decay_at: float = field(default_factory=time.time)
    last_poop_at: float = field(default_factory=time.time)
    last_crab_event_at: float = field(default_factory=time.time)

    @property
    def is_alive(self) -> bool:
        return self.stage != LifeStage.DEAD

    @property
    def age_seconds(self) -> int:
        return max(0, int(time.time() - self.born_at))

    def tick(self, now: float | None = None) -> list[str]:
        now = now or time.time()
        events: list[str] = []

        if self.stage == LifeStage.DEAD:
            # Legacy runtime compatibility: older versions could persist a dead
            # pet. Death is now removed, so revive into an elder stage.
            self.stage = LifeStage.ELDER
            self.stage_started_at = now
            self.health = max(1, self.health)
            self.last_hunger_decay_at = now
            self.last_happiness_decay_at = now
            self.last_poop_at = now
            self.last_crab_event_at = now
            events.append("Welcome back. Your pet can't die anymore (neglect only breaks streaks).")

        if not self.is_alive:
            self.last_tick_at = now
            return events

        if self.stage == LifeStage.EGG and now - self.stage_started_at >= STAGE_DURATIONS[LifeStage.EGG]:
            self._advance_stage(LifeStage.BABY, now)
            events.append("Your egg hatched.")

        if self.stage != LifeStage.EGG and self.lights_on:
            self._apply_decay(now, events)
            self._apply_poop(now, events)
            self._apply_stage_progression(now, events)

        if self.stage != LifeStage.EGG:
            self._apply_crab_event(now, events)

        self._apply_health_checks(events)
        self.last_tick_at = now
        return events

    def feed(self) -> str:
        if not self._can_act():
            return "Your pet cannot eat right now."
        if self.hunger >= 4:
            self.care_mistakes += 1
            self.weight += 1
            return f"{self.name} is already full."
        self.hunger = min(4, self.hunger + 2)
        self.weight += 1
        return f"You fed {self.name}."

    def play(self) -> str:
        if not self._can_act():
            return "Your pet is not ready to play."
        if not self.lights_on:
            return f"{self.name} is asleep."
        self.happiness = min(4, self.happiness + 1)
        self.weight = max(1, self.weight - 1)
        return f"You played with {self.name}."

    def clean(self) -> str:
        if not self._can_act():
            return "There is nothing to clean."
        if self.poop == 0:
            return f"{self.name}'s space is already clean."
        self.poop = 0
        return f"You cleaned up after {self.name}."

    def heal(self) -> str:
        if not self._can_act():
            return "Medicine will not help right now."
        if not self.is_sick:
            self.care_mistakes += 1
            return f"{self.name} is not sick."
        self.is_sick = False
        self.health = min(4, self.health + 1)
        return f"{self.name} feels better now."

    def discipline_pet(self) -> str:
        if not self._can_act():
            return "Your pet ignores discipline right now."
        self.discipline = min(4, self.discipline + 1)
        return f"{self.name} settles down a little."

    def toggle_lights(self) -> str:
        if not self.is_alive:
            return "The lights do not matter anymore."
        self.lights_on = not self.lights_on
        return "Lights on." if self.lights_on else "Lights off. Your pet is sleeping."

    def status_lines(self) -> list[str]:
        mood = "sick" if self.is_sick else "sleeping" if not self.lights_on else "awake"
        return [
            f"Name: {self.name}",
            f"Stage: {self.stage.value}",
            f"Mood: {mood}",
            f"Hunger: {self.hunger}/4",
            f"Happiness: {self.happiness}/4",
            f"Health: {self.health}/4",
            f"Discipline: {self.discipline}/4",
            f"Weight: {self.weight}",
            f"Poop: {self.poop}",
            f"Shells: {self.shells}",
            f"Care mistakes: {self.care_mistakes}",
            f"Age: {self.age_seconds}s",
        ]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "stage": self.stage.value,
            "hunger": self.hunger,
            "happiness": self.happiness,
            "health": self.health,
            "discipline": self.discipline,
            "weight": self.weight,
            "poop": self.poop,
            "shells": self.shells,
            "pomodoro_streak": self.pomodoro_streak,
            "streak_chests_opened": self.streak_chests_opened,
            "character_shards": self.character_shards,
            "unlocked_characters": self.unlocked_characters,
            "collected_shell_common": self.collected_shell_common,
            "collected_shell_rare": self.collected_shell_rare,
            "collection_unseen": self.collection_unseen,
            "inventory": self.inventory,
            "owned_decorations": self.owned_decorations,
            "xp": self.xp,
            "unlocked_achievements": self.unlocked_achievements,
            "owned_badges": self.owned_badges,
            "daily_task_state": self.daily_task_state,
            "weekly_task_state": self.weekly_task_state,
            "lifetime_counters": self.lifetime_counters,
            "is_sick": self.is_sick,
            "lights_on": self.lights_on,
            "care_mistakes": self.care_mistakes,
            "born_at": self.born_at,
            "stage_started_at": self.stage_started_at,
            "last_tick_at": self.last_tick_at,
            "last_hunger_decay_at": self.last_hunger_decay_at,
            "last_happiness_decay_at": self.last_happiness_decay_at,
            "last_poop_at": self.last_poop_at,
            "last_crab_event_at": self.last_crab_event_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Pet":
        payload = data.copy()
        payload["stage"] = LifeStage(payload["stage"])
        payload.setdefault("pomodoro_streak", 0)
        payload.setdefault("streak_chests_opened", 0)
        payload.setdefault("character_shards", {})
        payload.setdefault("unlocked_characters", [])
        payload.setdefault("collected_shell_common", 0)
        payload.setdefault("collected_shell_rare", 0)
        payload.setdefault("collection_unseen", False)
        payload.setdefault("inventory", {})
        payload.setdefault("owned_decorations", [])
        payload.setdefault("xp", 0)
        payload.setdefault("unlocked_achievements", [])
        payload.setdefault("owned_badges", [])
        payload.setdefault("daily_task_state", {})
        payload.setdefault("weekly_task_state", {})
        payload.setdefault("lifetime_counters", {})
        # Legacy compatibility: if an older save has a dead pet, revive it into
        # an elder stage (death is no longer part of the game loop).
        if payload["stage"] == LifeStage.DEAD:
            payload["stage"] = LifeStage.ELDER
            payload["health"] = max(1, int(payload.get("health", 1) or 1))
            payload["is_sick"] = bool(payload.get("is_sick", False))
        return cls(**payload)

    def _can_act(self) -> bool:
        return self.is_alive and self.stage != LifeStage.EGG

    def _apply_decay(self, now: float, events: list[str]) -> None:
        hunger_steps = int((now - self.last_hunger_decay_at) // 120)
        if hunger_steps > 0:
            self.hunger = max(0, self.hunger - hunger_steps)
            self.last_hunger_decay_at += hunger_steps * 120
            if self.hunger == 0:
                self.care_mistakes += 1
                events.append(f"{self.name} is starving.")

        happiness_steps = int((now - self.last_happiness_decay_at) // 180)
        if happiness_steps > 0:
            self.happiness = max(0, self.happiness - happiness_steps)
            self.last_happiness_decay_at += happiness_steps * 180
            if self.happiness == 0:
                self.care_mistakes += 1
                events.append(f"{self.name} looks unhappy.")

    def _apply_poop(self, now: float, events: list[str]) -> None:
        poop_steps = int((now - self.last_poop_at) // 240)
        if poop_steps > 0:
            self.poop = min(4, self.poop + poop_steps)
            self.last_poop_at += poop_steps * 240
            if poop_steps:
                events.append(f"{self.name} made a mess.")

    def _apply_crab_event(self, now: float, events: list[str]) -> None:
        crab_steps = int((now - self.last_crab_event_at) // CRAB_EVENT_INTERVAL)
        if crab_steps <= 0:
            return

        self.last_crab_event_at += crab_steps * CRAB_EVENT_INTERVAL

        if self.poop > 0:
            self.poop = max(0, self.poop - 1)
            events.append("The crab cleaned a corner of the tank.")
            return

        if self.lights_on and self.happiness < 4:
            self.happiness = min(4, self.happiness + 1)
            events.append(f"The crab waved at {self.name}.")
            return

        self.shells += 1
        events.append("The crab found a shell.")

    def _apply_stage_progression(self, now: float, events: list[str]) -> None:
        if self.stage in (LifeStage.ELDER, LifeStage.DEAD):
            return
        required = STAGE_DURATIONS.get(self.stage)
        if required is None:
            return
        if now - self.stage_started_at < required:
            return
        index = STAGE_ORDER.index(self.stage)
        next_stage = STAGE_ORDER[index + 1]
        self._advance_stage(next_stage, now)
        events.append(f"{self.name} grew into a {next_stage.value}.")

    def _advance_stage(self, stage: LifeStage, now: float) -> None:
        self.stage = stage
        self.stage_started_at = now
        self.last_hunger_decay_at = now
        self.last_happiness_decay_at = now
        self.last_poop_at = now
        self.last_crab_event_at = now

    def _apply_health_checks(self, events: list[str]) -> None:
        # Death is intentionally removed from the game loop. Neglect can still
        # make the pet sick, but it cannot kill the pet.
        if self.stage == LifeStage.DEAD:
            return

        neglected = self.poop >= 3 or self.hunger == 0
        if neglected:
            if not self.is_sick:
                events.append(f"{self.name} is sick.")
            self.is_sick = True
            if self.health > 1:
                self.health -= 1
            if self.pomodoro_streak > 0:
                self.pomodoro_streak = 0
                events.append("Neglect broke your focus streak.")
            return

        if self.is_sick:
            self.health = max(1, self.health)
