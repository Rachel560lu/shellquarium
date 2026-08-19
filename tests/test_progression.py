import asyncio

from shellquarium.core.pet import LifeStage, Pet
from shellquarium.ui.app import TerminalPetApp


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
    pet.daily_task_state = {
        "date": "2026-08-19",
        "counters": {"feed": 1},
        "claimed": [],
    }
    events = update_tasks(pet, now_date="2026-08-19", now_week="2026-W34")
    first_xp = pet.xp
    first_shells = pet.shells
    update_tasks(pet, now_date="2026-08-19", now_week="2026-W34")

    assert first_xp > 0
    assert first_shells > 0
    assert pet.xp == first_xp
    assert pet.shells == first_shells
    assert events


def test_week_change_resets_weekly_progress_without_losing_xp():
    from shellquarium.core.progression import update_tasks

    pet = Pet(stage=LifeStage.BABY, xp=120)
    pet.weekly_task_state = {
        "week": "2026-W33",
        "counters": {"focus": 4},
        "claimed": [],
    }
    update_tasks(pet, now_date="2026-08-19", now_week="2026-W34")

    assert pet.weekly_task_state["week"] == "2026-W34"
    assert pet.xp == 120


def test_achievement_unlock_grants_xp_and_badge_once():
    from shellquarium.core.progression import evaluate_achievements

    pet = Pet(stage=LifeStage.BABY, lifetime_counters={"feed": 1})
    events = evaluate_achievements(pet)
    evaluate_achievements(pet)

    assert "first_care" in pet.unlocked_achievements
    assert "first_care" in pet.owned_badges
    assert pet.xp == 30
    assert events


def test_virtual_level_is_independent_from_life_stage():
    from shellquarium.core.progression import virtual_level

    pet = Pet(stage=LifeStage.ADULT, xp=450)
    assert virtual_level(pet.xp) == 4


def test_shop_and_progression_state_round_trip():
    payload = Pet(
        stage=LifeStage.BABY,
        inventory={"bubble_tea": 2},
        owned_decorations=["seaweed_ribbon"],
        xp=120,
        unlocked_achievements=["first_care"],
        owned_badges=["first_care"],
        lifetime_counters={"feed": 3},
    ).to_dict()
    restored = Pet.from_dict(payload)

    assert restored.inventory == {"bubble_tea": 2}
    assert restored.owned_decorations == ["seaweed_ribbon"]
    assert restored.xp == 120
    assert restored.unlocked_achievements == ["first_care"]
    assert restored.lifetime_counters == {"feed": 3}


def test_shell_shop_enter_buys_selected_item(monkeypatch):
    async def run() -> None:
        monkeypatch.setattr("shellquarium.ui.app.save_pet", lambda pet: None)
        app = TerminalPetApp()
        app.pet = Pet(name="Pixel", stage=LifeStage.BABY, shells=3)
        app._focus_index = 2
        app._shop_index = 4
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            assert app.pet.shells == 1
            assert app.pet.inventory.get("seaweed_snack") == 1

    asyncio.run(run())


def test_inventory_use_key_applies_selected_consumable(monkeypatch):
    async def run() -> None:
        monkeypatch.setattr("shellquarium.ui.app.save_pet", lambda pet: None)
        app = TerminalPetApp()
        app.pet = Pet(
            name="Pixel",
            stage=LifeStage.BABY,
            hunger=2,
            inventory={"seaweed_snack": 1},
        )
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("i")
            await pilot.press("u")
            assert app.pet.hunger == 3
            assert app.pet.inventory == {}

    asyncio.run(run())


def test_tasks_and_virtual_level_are_visible_in_panels():
    app = TerminalPetApp()
    app.pet = Pet(name="Pixel", stage=LifeStage.BABY, xp=120)
    assert "Level" in "\n".join(app._stats_panel_lines())
    app._info_menu_index = 2
    assert "Daily Tasks" in "\n".join(app._info_panel_lines())


def test_cli_care_action_advances_progression(monkeypatch, tmp_path):
    from shellquarium.__main__ import main
    import shellquarium.core.persistence as persistence

    save_file = tmp_path / "pet.json"
    monkeypatch.setattr(persistence, "SAVE_DIR", tmp_path)
    monkeypatch.setattr(persistence, "SAVE_FILE", save_file)
    main(["hatch", "Pixel"])
    pet = Pet(name="Pixel", stage=LifeStage.BABY, hunger=2)
    persistence.save_pet(pet)

    main(["feed"])
    updated = persistence.load_pet()
    assert updated is not None
    assert updated.lifetime_counters["feed"] == 1
    assert updated.xp >= 30
