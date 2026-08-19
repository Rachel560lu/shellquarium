# Shellquarium Progression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a purchasable shell shop, daily/weekly tasks, and a non-visual XP/achievement progression system without changing existing pet or item sprites.

**Architecture:** Keep `Pet` as the persisted gameplay state, adding backward-compatible inventory, task, counter, XP, achievement, and decoration fields. Put item definitions and progression rules in focused core modules; the Textual app translates user input into those core operations and renders text-only panels. Existing `sprites.py` and scene item frames remain unchanged.

**Tech Stack:** Python 3.10+, dataclasses, JSON persistence, Textual, pytest.

---

### Task 1: Define shop catalog and purchase/use behavior

**Files:**
- Create: `src/shellquarium/core/shop.py`
- Modify: `src/shellquarium/core/pet.py`
- Test: `tests/test_progression.py`

- [ ] **Step 1: Write failing tests for catalog, purchase, inventory, and use rules**

```python
def test_shop_catalog_contains_consumables_and_decorations():
    from shellquarium.core.shop import SHOP_CATALOG
    assert SHOP_CATALOG["seaweed_snack"].price == 2
    assert SHOP_CATALOG["seaweed_ribbon"].decorative


def test_buy_consumable_spends_shells_and_adds_inventory():
    from shellquarium.core.shop import buy_item
    pet = Pet(stage=LifeStage.BABY, shells=3)
    message = buy_item(pet, "seaweed_snack")
    assert pet.shells == 1
    assert pet.inventory["seaweed_snack"] == 1
    assert "bought" in message.lower()


def test_use_consumable_applies_effect_and_decrements_inventory():
    from shellquarium.core.shop import use_item
    pet = Pet(stage=LifeStage.BABY, hunger=2, inventory={"seaweed_snack": 1})
    message = use_item(pet, "seaweed_snack")
    assert pet.hunger == 3
    assert pet.inventory == {}
    assert "snack" in message.lower()


def test_buy_decoration_is_one_time_and_recorded():
    from shellquarium.core.shop import buy_item
    pet = Pet(stage=LifeStage.BABY, shells=10)
    buy_item(pet, "seaweed_ribbon")
    message = buy_item(pet, "seaweed_ribbon")
    assert pet.owned_decorations == ["seaweed_ribbon"]
    assert pet.shells == 7
    assert "already" in message.lower()
```

- [ ] **Step 2: Run the focused tests and verify they fail because the shop module and state fields are missing**

Run: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_progression.py -k 'shop or buy or use'`

Expected: collection/import failures for `shellquarium.core.shop` or missing `Pet` fields.

- [ ] **Step 3: Implement the minimal shop core**

Define a frozen `ShopItem` dataclass with `item_id`, `name`, `price`, `kind`, and `effect`. Add the eight items: four consumables (`seaweed_snack`, `bubble_tea`, `tiny_sponge`, `pearl_tonic`) and four decorative entries using the existing names. Implement `buy_item(pet, item_id)` and `use_item(pet, item_id)` with caps, insufficient-shell checks, sick-only tonic behavior, and no sprite changes. Add `inventory: dict[str, int]` and `owned_decorations: list[str]` to `Pet`.

- [ ] **Step 4: Add backward-compatible serialization for shop state**

Include `inventory` and `owned_decorations` in `to_dict`; use empty defaults in `from_dict` before constructing a pet. Run the focused tests again and expect PASS.

- [ ] **Step 5: Run the existing core tests**

Run: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_core.py`

Expected: all existing tests PASS.

### Task 2: Add counters, daily/weekly tasks, XP, and achievements

**Files:**
- Create: `src/shellquarium/core/progression.py`
- Modify: `src/shellquarium/core/pet.py`
- Test: `tests/test_progression.py`

- [ ] **Step 1: Write failing tests for counters and deterministic task rollover**

```python
def test_record_counter_updates_daily_and_lifetime_progress():
    from shellquarium.core.progression import record_counter
    pet = Pet(stage=LifeStage.BABY)
    record_counter(pet, "feed", now_date="2026-08-19")
    assert pet.lifetime_counters["feed"] == 1
    assert pet.daily_task_state["date"] == "2026-08-19"
    assert pet.daily_task_state["counters"]["feed"] == 1


def test_daily_task_completion_grants_shells_and_xp_once():
    from shellquarium.core.progression import update_tasks
    pet = Pet(stage=LifeStage.BABY)
    pet.daily_task_state = {"date": "2026-08-19", "counters": {"feed": 1}, "claimed": []}
    events = update_tasks(pet, now_date="2026-08-19", now_week="2026-W34")
    assert pet.xp > 0
    assert pet.shells > 0
    assert events


def test_week_change_resets_weekly_progress_without_losing_xp():
    from shellquarium.core.progression import update_tasks
    pet = Pet(stage=LifeStage.BABY, xp=120)
    pet.weekly_task_state = {"week": "2026-W33", "counters": {"focus": 4}, "claimed": []}
    update_tasks(pet, now_date="2026-08-19", now_week="2026-W34")
    assert pet.weekly_task_state["week"] == "2026-W34"
    assert pet.xp == 120


def test_achievement_unlock_grants_xp_and_badge_once():
    from shellquarium.core.progression import evaluate_achievements
    pet = Pet(stage=LifeStage.BABY, lifetime_counters={"feed": 1})
    events = evaluate_achievements(pet)
    assert "first_care" in pet.unlocked_achievements
    assert "first_care" in pet.owned_badges
    assert pet.xp == 30
    assert events


def test_virtual_level_is_independent_from_life_stage():
    from shellquarium.core.progression import virtual_level
    pet = Pet(stage=LifeStage.ADULT, xp=450)
    assert virtual_level(pet.xp) == 4
```

- [ ] **Step 2: Run the focused tests and verify the intended RED state**

Run: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_progression.py -k 'counter or task or achievement or virtual'`

Expected: failures for missing progression functions and state fields.

- [ ] **Step 3: Implement the progression core**

Create fixed daily and weekly task definitions with stable IDs, shell/XP rewards, and progress requirements. Store `daily_task_state` and `weekly_task_state` with date/week keys, counters, and claimed IDs. Implement `record_counter`, `update_tasks`, `evaluate_achievements`, and `virtual_level`. Auto-claim completed task rewards once and emit readable events. Use achievement IDs based only on actions, task completion, focus, shells, chests, and owned decorations; do not use `LifeStage.ADULT` or any sprite state as a requirement.

- [ ] **Step 4: Add progression fields and serialization defaults**

Add `xp`, `unlocked_achievements`, `owned_badges`, `daily_task_state`, `weekly_task_state`, and `lifetime_counters` to `Pet`. Ensure old JSON files load with empty/default values. Run focused tests and expect PASS.

- [ ] **Step 5: Add tests for all defined achievement and task boundaries**

Cover duplicate claims, insufficient progress, date rollover, week rollover, level thresholds, decoration-count achievement, and old-save migration. Run `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_progression.py` and expect PASS.

### Task 3: Integrate actions, shop, tasks, and achievements into the TUI

**Files:**
- Modify: `src/shellquarium/ui/app.py`
- Test: `tests/test_core.py` and `tests/test_progression.py`

- [ ] **Step 1: Write failing TUI tests for purchase/use and text panels**

```python
def test_shell_shop_enter_buys_selected_item():
    async def run():
        app = TerminalPetApp()
        app.pet = Pet(name="Pixel", stage=LifeStage.BABY, shells=3)
        app._focus_index = 2
        app._shop_index = 0
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            assert app.pet.shells == 1
            assert app.pet.inventory.get("seaweed_snack") == 1
    asyncio.run(run())


def test_tasks_and_level_are_visible_in_info_panel():
    app = TerminalPetApp()
    app.pet = Pet(name="Pixel", stage=LifeStage.BABY, xp=120)
    assert "Level" in "\\n".join(app._stats_panel_lines())
```

- [ ] **Step 2: Run the focused TUI tests and verify RED**

Run: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_core.py -k 'shop_shop or tasks or level'`

Expected: failures because the new bindings and panel content do not exist.

- [ ] **Step 3: Add shop and inventory bindings**

In `TerminalPetApp`, keep the existing focus and sprite code untouched. Add `enter` behavior for the Shell Shop, `i` for Inventory, and `u` for using the selected consumable. Add a text-only inventory menu and selected item index. Display price, stock, owned decoration state, and the latest purchase/use feedback.

- [ ] **Step 4: Connect every relevant action to progression counters**

After successful feed/play/clean/heal/discipline/sleep actions, record the corresponding counter; after focus completion, record `focus`; after a shell reward, record `shell`; after a chest opens, record `chest`. Call task and achievement evaluation, append generated events, save, and refresh. Do not call these systems during Pomodoro's frozen pet simulation except for the explicit focus completion event.

- [ ] **Step 5: Add Tasks, Inventory, and progression text to the existing panels**

Extend the info menu with `tasks`, `inventory`, and `collection`. Show task progress and rewards, inventory counts, `Level`, `XP`, unlocked achievement badges, and owned decorations. Keep existing tank rendering and all Sprite/scene item definitions unchanged.

- [ ] **Step 6: Run the focused TUI tests and then all existing tests**

Run: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_core.py tests/test_progression.py`

Expected: all tests PASS with no changes to existing pet/item rendering assertions.

### Task 4: Documentation and full verification

**Files:**
- Modify: `README.md`
- Test: `tests/test_progression.py`

- [ ] **Step 1: Document controls, shop items, task rules, XP, and achievements**

Add the `i` and `u` keybindings, item catalog, task reset behavior, virtual-level explanation, and the fact that achievement decorations are Collection-only and do not alter existing ASCII art.

- [ ] **Step 2: Run compile and complete test suite**

Run: `python3 -m compileall -q src tests && PYTHONPATH=src .venv/bin/python -m pytest -q`

Expected: compile succeeds and the complete test suite passes.

- [ ] **Step 3: Review the diff for scope and sprite preservation**

Run: `git diff --stat && git diff -- src/shellquarium/ui/sprites.py src/shellquarium/ui/themes.py`

Expected: `sprites.py` and `themes.py` have no changes; all modified lines map to shop, task, achievement, persistence, UI text, or tests.
