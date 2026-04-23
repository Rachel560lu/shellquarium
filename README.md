# Termiquarium

A cozy terminal pet aquarium with a jelly pet, a crab companion, a shell shop, and a built-in Pomodoro mode.

## What It Does

This project gives you a small Tamagotchi-inspired pet that lives in a terminal aquarium.
The current version supports:

- a Textual TUI that opens by default
- an animated ASCII jelly pet inside a glass tank
- an animated crab companion that can find shells, clean the tank, and cheer your pet
- shell collection that persists in save data
- focus navigation between the crab, the pet, and the shell shop with left and right arrow keys
- a shell shop panel with a browsable text-only item list
- a Pomodoro Crab timer panel with focus / break states
- a Pomodoro scene that swaps the tank view to jelly + clock while a session is active
- hatching a new pet
- checking pet status
- feeding, playing, cleaning, healing, disciplining, and sleeping
- mood performance text and animation that reacts to pet state
- time-based decay for hunger and happiness
- poop, sickness, stage progression, crab companion events, shell rewards, and death
- local save/load so your pet persists between commands

## Requirements

- Python 3.10+

## Setup

From the project root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e .
```

If you do not want to install the package, you can still run it with:

```bash
PYTHONPATH=src python -m terminal_pet --help
```

## How To Use

Launch the TUI:

```bash
python -m terminal_pet
```

Inside the TUI you can:

- hatch a pet if no save exists
- hatch a new pet directly after death without doing a reset first
- see the jelly pet rendered as animated ASCII art in the tank
- move focus with left and right between the crab, pet, and shell shop
- browse shell shop items with up and down when the shell is selected
- start, pause, resume, or stop the Pomodoro timer from the crab panel
- watch the tank switch into a jelly + clock focus scene during Pomodoro mode
- use hotkeys: `left`, `right`, `up`, `down`, `enter`, `x`, `f`, `p`, `c`, `h`, `d`, `s`, `r`, `q`
- let the pet update every second while the app is open
- quit with `q`

### Pomodoro Crab

When the crab is selected:

- `enter` starts a focus session if idle
- `enter` pauses a running session
- `enter` resumes a paused session
- `x` stops the current session and returns the tank to normal

When a focus session completes:

- the crab awards `+1` shell
- the timer automatically switches to a break session

## CLI Commands

Create a new pet:

```bash
python -m terminal_pet hatch Pixel
```

Show the current pet status:

```bash
python -m terminal_pet status
```

Run actions:

```bash
python -m terminal_pet feed
python -m terminal_pet play
python -m terminal_pet clean
python -m terminal_pet heal
python -m terminal_pet discipline
python -m terminal_pet sleep
```

Delete the current save and start over:

```bash
python -m terminal_pet reset
```

If you installed the package with `pip install -e .`, you can also use the script entry point:

```bash
terminal-pet
terminal-pet hatch Pixel
terminal-pet status
```

## Commands

| Command | What it does |
| --- | --- |
| `hatch [name]` | Creates a new pet egg. |
| `status` | Prints the current pet state. |
| `feed` | Restores hunger if the pet can eat. |
| `play` | Increases happiness and lowers weight. |
| `clean` | Removes poop if there is a mess. |
| `heal` | Cures sickness if the pet is sick. |
| `discipline` | Increases discipline. |
| `sleep` | Toggles lights on or off. |
| `reset` | Deletes the saved pet. |

## Save Data

By default, save data is written to:

```text
~/.terminal_pet/pet.json
```

You can override the save location by setting `TERMINAL_PET_HOME`.

Example:

```bash
TERMINAL_PET_HOME=/tmp/termiquarium python -m terminal_pet hatch Pixel
```

## Development

Useful checks from the project root:

```bash
python3 -m compileall -q src tests
```

If you install `pytest`, you can also run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
```

## Current Scope

This is still a small TUI + CLI aquarium. It does not include:

- buying shell shop items yet
- configurable Pomodoro lengths in the UI yet
- multiple save slots
- social or AI-agent integrations
