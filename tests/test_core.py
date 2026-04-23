import json
import asyncio

from textual.widgets import Button, Static

from shellquarium.__main__ import main
from shellquarium.core.persistence import SAVE_FILE, load_pet
from shellquarium.core.pet import LifeStage, Pet
from shellquarium.ui.sprites import get_pet_frame
from shellquarium.ui.app import TerminalPetApp
from shellquarium.ui.themes import SCENE_HEIGHT, SCENE_WIDTH, performance_line, render_scene, render_scene_with_reaction


def test_hatch_creates_pet(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("SHELLQUARIUM_HOME", str(tmp_path))
    main(["hatch", "Pixel"])

    pet = load_pet()
    assert pet is not None
    assert pet.name == "Pixel"
    assert pet.stage == LifeStage.EGG
    assert "Pixel" in capsys.readouterr().out


def test_feed_after_hatching(monkeypatch, tmp_path):
    monkeypatch.setenv("SHELLQUARIUM_HOME", str(tmp_path))
    pet = Pet(name="Pixel", stage=LifeStage.BABY)
    SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SAVE_FILE.write_text(json.dumps(pet.to_dict()), encoding="utf-8")

    main(["feed"])
    updated = load_pet()
    assert updated is not None
    assert updated.weight == 11


def test_sleep_toggles_lights(monkeypatch, tmp_path):
    monkeypatch.setenv("SHELLQUARIUM_HOME", str(tmp_path))
    pet = Pet(name="Pixel", stage=LifeStage.BABY)
    SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SAVE_FILE.write_text(json.dumps(pet.to_dict()), encoding="utf-8")

    main(["sleep"])
    updated = load_pet()
    assert updated is not None
    assert not updated.lights_on


def test_tick_can_hatch_egg():
    pet = Pet(name="Pixel")
    events = pet.tick(now=pet.stage_started_at + 61)
    assert pet.stage == LifeStage.BABY
    assert events == ["Your egg hatched."]


def test_tick_can_kill_pet_from_neglect():
    pet = Pet(name="Pixel", stage=LifeStage.BABY, hunger=0, health=1, poop=3)
    events = pet.tick(now=pet.last_tick_at + 1)
    assert pet.stage == LifeStage.DEAD
    assert any("has died" in event for event in events)


def test_crab_finds_shell_when_tank_is_clean():
    pet = Pet(name="Pixel", stage=LifeStage.BABY)
    events = pet.tick(now=pet.last_crab_event_at + 151)
    assert pet.shells == 1
    assert "The crab found a shell." in events


def test_crab_cleans_tank_before_finding_shells():
    pet = Pet(name="Pixel", stage=LifeStage.BABY, poop=2)
    events = pet.tick(now=pet.last_crab_event_at + 151)
    assert pet.poop == 1
    assert pet.shells == 0
    assert "The crab cleaned a corner of the tank." in events


def test_crab_cheers_pet_when_tank_is_clean():
    pet = Pet(name="Pixel", stage=LifeStage.BABY, happiness=2)
    events = pet.tick(now=pet.last_crab_event_at + 151)
    assert pet.happiness == 3
    assert pet.shells == 0
    assert "The crab waved at Pixel." in events


def test_main_without_command_launches_tui(monkeypatch):
    called = False

    def fake_tui() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("shellquarium.__main__._cmd_tui", fake_tui)
    main([])
    assert called


def test_pet_frame_changes_with_sleep_state():
    pet = Pet(name="Pixel", stage=LifeStage.BABY)
    awake = get_pet_frame(pet, 0)
    pet.lights_on = False
    sleeping = get_pet_frame(pet, 0)
    assert awake != sleeping


def test_key_binding_feed_updates_pet():
    async def run() -> None:
        app = TerminalPetApp()
        app.pet = Pet(name="Pixel", stage=LifeStage.BABY, hunger=2)
        async with app.run_test() as pilot:
            await pilot.pause()
            before = app.pet.weight
            await pilot.press("f")
            await pilot.pause()
            assert app.pet.hunger == 4
            assert app.pet.weight == before + 1

    asyncio.run(run())


def test_dead_pet_shows_hatch_new_pet_controls():
    async def run() -> None:
        app = TerminalPetApp()
        app.pet = Pet(name="Pixel", stage=LifeStage.DEAD)
        async with app.run_test() as pilot:
            await pilot.pause()
            button = app.query_one("#hatch", Button)
            panel = app.query_one("#new-pet-panel", Static)
            assert str(button.label) == "Hatch New Pet"
            assert "has died" in panel.renderable

    asyncio.run(run())


def test_render_scene_is_bounded_aquarium():
    pet = Pet(name="Pixel", stage=LifeStage.BABY)
    scene = render_scene("tank", pet, 0)
    assert SCENE_WIDTH == 46
    assert SCENE_HEIGHT == 14
    assert "[white]\\[/]" not in scene
    assert "[green]\\[/]" not in scene
    assert "[green]/[/]" not in scene
    assert "[green]" in scene
    assert "[green4]" in scene
    assert "[deepskyblue1]" in scene
    assert "[orange1]" in scene
    assert "[bright_white]" in scene
    assert "[light_pink1]" in scene


def test_crab_animates_between_scene_frames():
    pet = Pet(name="Pixel", stage=LifeStage.BABY)
    scene_a = render_scene("tank", pet, 0)
    scene_b = render_scene("tank", pet, 2)
    assert scene_a != scene_b


def test_small_pet_frame_is_compact():
    pet = Pet(name="Pixel", stage=LifeStage.BABY)
    frame = get_pet_frame(pet, 0).splitlines()
    assert len(frame) == 3
    assert max(len(line) for line in frame) <= 5


def test_performance_line_reflects_sleeping_state():
    pet = Pet(name="Pixel", stage=LifeStage.BABY)
    pet.lights_on = False
    assert "drifting" in performance_line(pet)


def test_action_feedback_is_visible_in_pet_panel():
    async def run() -> None:
        app = TerminalPetApp()
        app.pet = Pet(name="Pixel", stage=LifeStage.BABY, hunger=4, happiness=4, poop=0)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("f")
            await pilot.pause()
            status = app.query_one("#pet-status", Static)
            assert "Recent:" in status.renderable
            assert "already full" in status.renderable
            assert "Theme:" not in status.renderable
            assert "Room:" not in status.renderable

    asyncio.run(run())


def test_play_key_sets_transient_reaction():
    async def run() -> None:
        app = TerminalPetApp()
        app.pet = Pet(name="Pixel", stage=LifeStage.BABY, hunger=2, happiness=2)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("p")
            await pilot.pause()
            assert app._reaction_name is None
            assert app._expression_name == "joy"
            assert app._expression_ticks_remaining > 0

    asyncio.run(run())


def test_blocked_play_does_not_set_reaction():
    async def run() -> None:
        app = TerminalPetApp()
        app.pet = Pet(name="Pixel", stage=LifeStage.EGG)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("p")
            await pilot.pause()
            assert app._reaction_name is None
            assert app._expression_name is None
            assert "not ready to play" in app.last_feedback.lower()

    asyncio.run(run())


def test_play_uses_expression_change_in_scene():
    pet = Pet(name="Pixel", stage=LifeStage.CHILD)
    normal_scene = render_scene_with_reaction("tank", pet, 0)
    joy_scene = render_scene_with_reaction("tank", pet, 0, mood_override="joy")
    assert normal_scene != joy_scene
    assert "U" in joy_scene


def test_pet_moves_with_frame_index_inside_scene():
    pet = Pet(name="Pixel", stage=LifeStage.CHILD)
    frame_a = render_scene("tank", pet, 0, pet_position=(1, 1), is_moving=False)
    frame_b = render_scene("tank", pet, 0, pet_position=(2, 1), is_moving=False)
    assert frame_a != frame_b


def test_legs_only_animate_while_moving():
    pet = Pet(name="Pixel", stage=LifeStage.CHILD)
    still_a = get_pet_frame(pet, 0, is_moving=False)
    still_b = get_pet_frame(pet, 1, is_moving=False)
    moving_a = get_pet_frame(pet, 0, is_moving=True)
    moving_b = get_pet_frame(pet, 1, is_moving=True)
    assert still_a == still_b
    assert moving_a != moving_b


def test_random_walk_changes_position(monkeypatch):
    app = TerminalPetApp()
    app.pet = Pet(name="Pixel", stage=LifeStage.CHILD)
    app._pet_position = (6, 2)
    monkeypatch.setattr("shellquarium.ui.app.random.choice", lambda choices: (1, 0))
    app._advance_pet_motion()
    assert app._pet_position == (7, 2)
    assert app._pet_is_moving


def test_shell_animates_between_scene_frames():
    pet = Pet(name="Pixel", stage=LifeStage.BABY)
    scene_a = render_scene("tank", pet, 0)
    scene_b = render_scene("tank", pet, 2)
    assert scene_a != scene_b
    assert "[bright_white]_[/]" in scene_a or "[bright_white].[/]" in scene_a
    assert "[bright_white]_[/]" in scene_b or "[bright_white].[/]" in scene_b


def test_arrow_keys_change_focus_status_text():
    async def run() -> None:
        app = TerminalPetApp()
        app.pet = Pet(name="Pixel", stage=LifeStage.BABY)
        async with app.run_test() as pilot:
            await pilot.pause()
            status = app.query_one("#pet-status", Static)
            assert "Selected: Pixel pet" in str(status.renderable)
            await pilot.press("left")
            await pilot.pause()
            status = app.query_one("#pet-status", Static)
            assert "Selected: Pomodoro crab" in str(status.renderable)
            await pilot.press("right")
            await pilot.pause()
            status = app.query_one("#pet-status", Static)
            assert "Selected: Pixel pet" in str(status.renderable)

    asyncio.run(run())


def test_shell_focus_opens_shop_panel_and_moves_selection():
    async def run() -> None:
        app = TerminalPetApp()
        app.pet = Pet(name="Pixel", stage=LifeStage.BABY)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("right")
            await pilot.pause()
            shop = app.query_one("#shop-panel", Static)
            rendered = str(shop.renderable)
            assert "Shell Shop" in rendered
            assert "> Seaweed Ribbon - 3 shells" in rendered
            await pilot.press("down")
            await pilot.pause()
            rendered = str(app.query_one("#shop-panel", Static).renderable)
            assert "> Bubble Stone - 5 shells" in rendered

    asyncio.run(run())


def test_crab_focus_starts_and_pauses_pomodoro():
    app = TerminalPetApp()
    app.pet = Pet(name="Pixel", stage=LifeStage.BABY)
    app._focus_index = 0
    app.FOCUS_DURATION_SECONDS = 10

    app.action_toggle_pomodoro()
    assert app._pomodoro_mode == "focus"
    assert app._pomodoro_running

    app.action_toggle_pomodoro()
    assert app._pomodoro_mode == "focus"
    assert not app._pomodoro_running


def test_focus_completion_rewards_shell_and_starts_break():
    app = TerminalPetApp()
    app.pet = Pet(name="Pixel", stage=LifeStage.BABY)
    app._focus_index = 0
    app.FOCUS_DURATION_SECONDS = 1
    app.BREAK_DURATION_SECONDS = 2

    app.action_toggle_pomodoro()
    events = app._update_pomodoro((app._pomodoro_end_at or 0) + 0.1)

    assert app.pet.shells == 1
    assert app._pomodoros_completed == 1
    assert app._pomodoro_mode == "break"
    assert app._pomodoro_running
    assert any("reward shell" in event for event in events)


def test_pomodoro_scene_hides_crab_and_shell_and_shows_clock():
    pet = Pet(name="Pixel", stage=LifeStage.BABY)
    scene = render_scene_with_reaction("tank", pet, 0, scene_mode="pomodoro", clock_text="25:00")
    assert "25:00" in scene
    assert "v   v" not in scene
    assert "œœ" not in scene
    assert "(_ )" not in scene.replace(')', ' )')


def test_focus_navigation_locks_during_pomodoro():
    app = TerminalPetApp()
    app.pet = Pet(name="Pixel", stage=LifeStage.BABY)
    app._focus_index = 0
    app.action_toggle_pomodoro()
    assert app._scene_mode == "pomodoro"
    app.action_focus_right()
    assert app.selected_target == "crab"
