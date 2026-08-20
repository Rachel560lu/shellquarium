# Hero Aquarium Layout Design

## Goal

Make the aquarium the visual focus of Shellquarium while keeping the existing pet, companion, and item ASCII art unchanged. The target composition is roughly two-thirds aquarium and one-third compact information panels.

## Direction

Use the approved hybrid direction:

- **Hero aquarium structure:** the tank receives most of the available vertical space.
- **Living habitat content:** the extra tank space is filled with calm environmental depth rather than dense new UI or gameplay.

## Layout

- Keep the header and active-pet banner unchanged.
- Change the main content split to approximately `2fr` for `#pet-panel` and `1fr` for `#info-panels` when the terminal has enough height.
- Compress the three lower panels without removing existing actions, status, task, inventory, or collection information.
- Keep the existing three-column panel order and focus behavior.
- On short terminals, fall back to a compact layout that avoids clipping or making the information panels unusable.

## Aquarium composition

### Existing art contract

- Do not edit pet frame strings, crab frame strings, decoration strings, colors, or glyph shapes.
- The pet and items may move within a larger safe area, but their rendered characters and proportions remain unchanged.

### Dynamic scene depth

- Allow the tank frame to use the available height instead of always rendering only the minimum scene height.
- Keep the pet in the central swim zone and the crab in a lower side zone.
- Keep seaweed, shell, and starfish anchored to the lower habitat shelf.
- Distribute the existing bubble treatment across additional rows so the upper water column has visual interest.
- Use empty water around the focal pet as intentional breathing room; do not fill every row with decoration.
- Keep ambient details deterministic per animation frame so resizing does not create visual noise or alter gameplay state.

## Interaction and state

- Preserve all current keyboard bindings and focus targets.
- Preserve the active-panel highlight and existing panel content.
- Layout changes must not affect pet simulation, shop prices, tasks, achievements, Pomodoro timing, or save data.
- A resize should reflow the scene and panels without resetting the selected target, selected shop item, or current menu.

## Testing and validation

- Add or update TUI tests for a wide/tall terminal and a short terminal.
- Verify the aquarium-to-panel ratio at a representative size such as 120×50.
- Verify the compact fallback at a size such as 120×32.
- Assert that the existing pet, crab, seaweed, shell, and starfish glyph strings still appear in the rendered scene.
- Manually inspect the running TUI at the user's terminal size for clipping, excessive blank space, and readable panel content.

## Acceptance criteria

- At a tall terminal size, the aquarium occupies approximately two-thirds of the usable content height and the information panels approximately one-third.
- The enlarged tank feels inhabited through existing bubbles, movement zones, and the lower habitat shelf without changing any pet or item appearance.
- The lower panels remain readable and actionable.
- Short terminals remain usable through the compact fallback.
- Existing behavior and tests remain intact.
