# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a realistic MLB game simulator that generates play-by-play logs indistinguishable from real baseball broadcasts. The engine models pitch-by-pitch sequences, bullpen management, and situational events while respecting modern MLB rules (DH rule, ghost runner in extras).

## Commands

### Running the Simulator

```bash
python baseball.py
```

CLI flags:
- `--terse`: Switch to compact play-by-play phrasing (data feed style)
- `--bracketed-ui`: Use legacy bracketed indicators for base runners instead of prose
- `--commentary {narrative,statcast,gameday}`: Choose output style (narrative=descriptive, statcast=data-driven, gameday=structured JSON)

### Testing

Run all tests:
```bash
pytest -q
```

Run a single test file:
```bash
pytest test_realism.py -q
```

Run a specific test:
```bash
pytest test_realism.py::TestRealism::test_bullpen_variability -q
```

### Updating Example Games

After making behavior changes, regenerate the deterministic example logs:

```bash
python update_examples.py          # Regenerates examples/game_*.txt
python update_statcast_examples.py # Regenerates examples/statcast_game_*.txt
python update_gameday_examples.py  # Regenerates examples/gameday_snapshots/gameday_*.json
```

These scripts are critical for snapshot testing. When you modify the simulation logic, you must regenerate examples and commit them alongside code changes.

## Architecture

### Core Simulation Engine (`baseball.py`)

The `BaseballSimulator` class orchestrates the entire game simulation. Key architectural elements:

1. **State Management**: The simulator maintains game state (inning, outs, bases, scores) and team state (lineups, pitchers, defensive positions)

2. **Commentary Styles**: The engine supports three output modes controlled by `commentary_style`:
   - `narrative`: Verbose, broadcast-style play-by-play (default)
   - `statcast`: Data-driven output with exit velocity, launch angle, and pitch metrics
   - `gameday`: Structured JSON output (stored in `play_events` list)

3. **Event Flow**: Each plate appearance goes through:
   - Pitcher selection and fatigue management
   - At-bat simulation (pitches, counts, outcomes)
   - Runner advancement logic
   - Inning/game transitions

4. **Batted Ball Data**: When `commentary_style='statcast'`, the engine generates realistic exit velocity (EV) and launch angle (LA) for batted balls using `_generate_batted_ball_data()`

### Team Data (`teams.py`)

Defines fictional teams in the `TEAMS` dictionary with:
- Player rosters (position players and pitchers)
- Pitcher roles (Starter, Closer, Reliever)
- Pitch repertoires and velocity ranges
- Player statistics that drive outcome probabilities

Also contains `GAME_CONTEXT` with umpires, weather conditions, pitch locations, and the `PITCH_TYPE_MAP` for abbreviations.

### Output Formats

The simulator produces three distinct output formats:

1. **Narrative** (`.txt` files): Human-readable play-by-play with descriptive prose
2. **Statcast** (`.txt` files): Similar to narrative but includes exit velocity, launch angle, and pitch data
3. **Gameday** (JSON): Structured event data stored in `simulator.gameday_data` dictionary

### Deterministic Examples (`example_games.py`)

The `ExampleGame` dataclass manages seeded game simulations for regression testing:
- Each example has a fixed seed for reproducibility
- `EXAMPLE_GAMES` list defines the catalog of 10 example games (seeds 101, 202, 303, etc.)
- `render()` method generates output in specified commentary style
- Used by snapshot tests (`test_examples_snapshot.py`, `test_gameday_regression.py`, `test_statcast_regression.py`)

### Testing Strategy

The test suite uses multiple approaches:

1. **Snapshot Testing**: Ensures engine changes don't unexpectedly alter output
   - `test_examples_snapshot.py`: Compares rendered games against `examples/game_*.txt`
   - `test_statcast_regression.py`: Validates statcast output against `examples/statcast_game_*.txt`
   - `test_gameday_examples.py`: Compares gameday JSON snapshots against `examples/gameday_snapshots/gameday_*.json` (compact snapshots with 6 representative plays per game to keep file sizes manageable)
   - `test_gameday_regression.py`: Validates gameday JSON event structure (not snapshot-based)

2. **Realism Testing**: Validates statistical properties over many simulated games
   - `test_realism.py`: Checks bullpen diversity, pitch vocabulary, catcher groundout rates, etc.
   - `test_statcast_realism.py`: Validates exit velocity, launch angle, and pitch data distributions
   - `test_analyst_concerns.py`: Tests specific edge cases and reported issues

3. **Regression Testing**: Prevents previously fixed bugs from resurfacing
   - `test_regression_realism.py`: Covers historical issues

## Workflow for Making Changes

1. Make code changes to `baseball.py`, `teams.py`, or other files
2. Run tests to ensure nothing broke: `pytest -q`
3. If behavior intentionally changed, regenerate examples:
   - `python update_examples.py`
   - `python update_statcast_examples.py`
   - `python update_gameday_examples.py`
4. Review the git diff of example files to ensure changes are intentional
5. Commit both code changes and updated example files together

## Key Implementation Details

- **Bullpen Management**: Pitchers are selected based on fatigue (pitch counts), role (Closer vs Reliever), and game situation
- **Modern MLB Rules**: DH in effect, ghost runner on second in extra innings
- **Probabilistic Outcomes**: Player statistics in `teams.py` define weighted probabilities for at-bat outcomes
- **Defensive Positioning**: Fielders are assigned by position (IF/OF/C) for realistic out descriptions
