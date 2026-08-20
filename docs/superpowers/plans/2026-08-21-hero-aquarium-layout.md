# Hero Aquarium Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the aquarium occupy roughly two-thirds of the usable TUI height, keep the information panels to one-third, and add deterministic habitat depth without changing any existing pet or item glyphs.

**Architecture:** Keep the existing three-column dashboard and keyboard model. Add an optional scene-height parameter to the theme renderer, derive the available height from the mounted Textual widget, and switch to a compact CSS class for short terminals. The renderer keeps the current 14-row output as its default, while taller scenes anchor the existing companion/decorations to the bottom and distribute deterministic bubbles through the extra water column.

**Tech Stack:** Python 3.10+, Textual, Rich markup, pytest, existing `TerminalPetApp` and `themes.py` renderer.

---

### Task 1: Lock the responsive layout and renderer behavior with failing tests

**Files:**
- Modify: `tests/test_core.py`

- [ ] **Step 1: Add renderer tests for a taller scene**

Add this test beside `test_render_scene_is_bounded_aquarium`:

```python
def test_render_scene_supports_taller_aquarium_without_changing_art():
    pet = Pet(name="Pixel", stage=LifeStage.BABY)
    scene = render_scene("tank", pet, 0, scene_height=24)
    lines = scene.splitlines()

    assert len(lines) == 26  # top border + 24 rows + bottom border
    assert "(o^o)" in scene
    assert "=( )=" in scene
    assert "𓇻" in scene
    assert "œœ" in scene
    assert lines[-1].startswith("[white]+[/]")
```

- [ ] **Step 2: Add Textual layout tests for tall and short terminals**

Add these async tests near the existing TUI tests:

```python
def test_tall_terminal_uses_hero_aquarium_layout():
    async def run() -> None:
        app = TerminalPetApp()
        app.pet = Pet(name="Pixel", stage=LifeStage.BABY)
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            assert "compact-layout" not in app.classes
            assert app._scene_height() >= 20

    asyncio.run(run())


def test_short_terminal_uses_compact_layout():
    async def run() -> None:
        app = TerminalPetApp()
        app.pet = Pet(name="Pixel", stage=LifeStage.BABY)
        async with app.run_test(size=(120, 32)) as pilot:
            await pilot.pause()
            assert "compact-layout" in app.classes
            assert app._scene_height() == SCENE_HEIGHT

    asyncio.run(run())
```

- [ ] **Step 3: Run the focused tests and confirm they fail for the missing scene-height/layout behavior**

Run:

```bash
SHELLQUARIUM_HOME=/tmp/shellquarium-hero-plan \
  /Users/lu/Desktop/🚀\ Past\ projects/shellquarium-remote/.venv/bin/python \
  -m pytest tests/test_core.py::test_render_scene_supports_taller_aquarium_without_changing_art \
  tests/test_core.py::test_tall_terminal_uses_hero_aquarium_layout \
  tests/test_core.py::test_short_terminal_uses_compact_layout -q -p no:cacheprovider
```

Expected: FAIL because `render_scene` does not accept `scene_height` and `TerminalPetApp` has no responsive layout helper yet.

### Task 2: Add dynamic scene height while preserving the existing art contract

**Files:**
- Modify: `src/shellquarium/ui/themes.py`
- Test: `tests/test_core.py`

- [ ] **Step 1: Add a scene-position helper that anchors existing objects to the floor**

Add a helper next to the existing position constants:

```python
def _scene_positions(scene_height: int) -> dict[str, tuple[int, int]]:
    floor = max(SCENE_HEIGHT - 1, scene_height - 1)
    return {
        "crab": (CRAB_POSITION[0], max(0, floor - 3)),
        "seaweed": (SEAWEED_POSITION[0], max(0, floor - 3)),
        "starfish": (STARFISH_POSITION[0], max(0, floor - 2)),
        "shell": (SHELL_POSITION[0], max(0, floor - 2)),
    }
```

Keep `SCENE_HEIGHT == 14` and all existing frame/glyph constants unchanged.

- [ ] **Step 2: Thread an optional `scene_height` through the renderer**

Change `render_scene`, `render_scene_with_reaction`, and `_build_scene_canvas` to accept `scene_height: int = SCENE_HEIGHT`. Clamp it to at least `SCENE_HEIGHT`, allocate the canvas with that height, and pass the computed positions from `_scene_positions(scene_height)` to the crab, seaweed, starfish, and shell drawing loops.

Keep the default call path unchanged so existing tests and CLI output still use the 14-row scene.

- [ ] **Step 3: Distribute deterministic bubbles through the extra rows**

Replace the fixed bubble loop with a helper that starts with the current seven positions and adds positions using a fixed arithmetic pattern for rows between 12 and `scene_height - 2`. Do not use `random`; the same frame index and scene height must produce the same scene.

```python
def _bubble_positions(scene_height: int) -> tuple[tuple[int, int], ...]:
    base = [(30, 1), (39, 2), (24, 3), (34, 5), (42, 7), (28, 10), (37, 11)]
    for row in range(13, max(13, scene_height - 1), 4):
        base.append((8 + (row * 7) % (SCENE_WIDTH - 12), row))
    return tuple(base)
```

- [ ] **Step 4: Run renderer tests**

Run:

```bash
SHELLQUARIUM_HOME=/tmp/shellquarium-hero-plan \
  /Users/lu/Desktop/🚀\ Past\ projects/shellquarium-remote/.venv/bin/python \
  -m pytest tests/test_core.py -k "render_scene or pet_frame or shell_animates" -q -p no:cacheprovider
```

Expected: PASS, including the original 14-row color/glyph assertions and the new 24-row assertion.

### Task 3: Make the Textual dashboard use a 2fr/1fr split with a compact fallback

**Files:**
- Modify: `src/shellquarium/ui/app.py`
- Test: `tests/test_core.py`

- [ ] **Step 1: Replace the fixed pet-panel height with responsive CSS**

Update the CSS declarations as follows:

```css
#pet-panel {
    height: 2fr;
    min-height: 18;
}

#info-panels {
    height: 1fr;
    min-height: 8;
    layout: grid;
    grid-size: 3;
    grid-columns: 1fr 1fr 1fr;
    grid-gutter: 1;
}

Screen.compact-layout #pet-panel {
    height: 18;
    min-height: 14;
}

Screen.compact-layout #info-panels {
    height: 1fr;
    min-height: 6;
}
```

- [ ] **Step 2: Add a height helper and resize-mode updater**

Add these methods to `TerminalPetApp`:

```python
    def _scene_height(self) -> int:
        if not self.children:
            return SCENE_HEIGHT
        height = self.query_one("#pet-sprite", Static).size.height
        if height < SCENE_HEIGHT + 2:
            return SCENE_HEIGHT
        return max(SCENE_HEIGHT, height - 2)

    def _update_layout_mode(self) -> None:
        if not self.children:
            return
        if self.size.height < 38:
            self.add_class("compact-layout")
        else:
            self.remove_class("compact-layout")

    def on_resize(self, event: Resize) -> None:
        self._update_layout_mode()
        self._refresh_pet_panel()
```

Import `Resize` from `textual.events` and call `_update_layout_mode()` in `on_mount()` before `_refresh_view()`.

- [ ] **Step 3: Pass the dynamic height into the aquarium and movement bounds**

In `_refresh_pet_panel`, compute `scene_height = self._scene_height()` and pass `scene_height=scene_height` to `render_scene_with_reaction`. In `_advance_pet_motion`, use `scene_height = self._scene_height()` and set `max_y = scene_height - PET_HEIGHT`. Clamp the existing `_pet_position` before rendering so resizing cannot leave the pet outside the canvas. Keep the existing Pomodoro minimum-y rule, using the dynamic height.

- [ ] **Step 4: Run the focused layout tests**

Run:

```bash
SHELLQUARIUM_HOME=/tmp/shellquarium-hero-plan \
  /Users/lu/Desktop/🚀\ Past\ projects/shellquarium-remote/.venv/bin/python \
  -m pytest tests/test_core.py::test_tall_terminal_uses_hero_aquarium_layout \
  tests/test_core.py::test_short_terminal_uses_compact_layout \
  tests/test_core.py::test_random_walk_changes_position -q -p no:cacheprovider
```

Expected: PASS at both terminal sizes, with movement still bounded and the compact class active only for the short terminal.

### Task 4: Run the full regression suite and inspect the live layout

**Files:**
- Modify: none

- [ ] **Step 1: Run all tests from the isolated worktree**

Run:

```bash
SHELLQUARIUM_HOME=/tmp/shellquarium-hero-full \
  /Users/lu/Desktop/🚀\ Past\ projects/shellquarium-remote/.venv/bin/python \
  -m pytest -q -p no:cacheprovider
```

Expected: all existing tests plus the new layout tests pass.

- [ ] **Step 2: Launch a representative tall TUI**

Run:

```bash
SHELLQUARIUM_HOME=/tmp/shellquarium-hero-live \
  PYTHONPATH=src \
  /Users/lu/Desktop/🚀\ Past\ projects/shellquarium-remote/.venv/bin/python \
  -m shellquarium
```

Confirm the aquarium is the dominant area, the existing pet/crab/items retain their glyphs and colors, the lower panels remain readable, and focus/shop/task interactions still work.

- [ ] **Step 3: Launch a short-size TUI check**

Resize the terminal to approximately 120×32 and confirm the compact layout avoids clipping and keeps the three panels usable.

- [ ] **Step 4: Commit the implementation**

```bash
git add src/shellquarium/ui/app.py src/shellquarium/ui/themes.py tests/test_core.py
git commit -m "feat: give aquarium a hero layout"
```
