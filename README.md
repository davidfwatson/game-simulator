# Realistic MLB Game Simulator

This repository contains a command line play-by-play simulator that aims to produce logs that feel indistinguishable from a real Major League Baseball broadcast. The engine models pitch-by-pitch sequences, strategic bullpen usage, and situational events (mound visits, defensive alignments, challenges, weather, etc.) to generate rich narration while respecting modern MLB rules.

## Getting Started

### Requirements

* Python 3.9 or newer

Install the Python dependencies (only the standard library is required) and run the simulator directly:

```bash
python baseball.py
```

Use the available CLI flags to tailor the output:

* `--commentary {narrative,statcast,gameday}` – choose output style:
  * `narrative` (default) – descriptive, broadcast-style play-by-play
  * `statcast` – data-driven output with exit velocity, launch angle, and pitch metrics
  * `gameday` – structured JSON output matching MLB StatsAPI format
* `--terse` – switch to compact play-by-play phrasing (data feed style)
* `--bracketed-ui` – render base runner state using legacy bracketed indicators instead of prose

### Running the Test Suite

The project ships with a growing collection of regression tests that encode previously observed realism issues. Run everything with:

```bash
python -m unittest discover -p "test_*.py"
```

Or run a specific test file:

```bash
python -m unittest test_realism.py -v
```

The tests cover items such as bullpen variability, pitch vocabulary diversity, realistic catcher groundout frequencies, and snapshot comparisons against curated example games.

## Deterministic Example Games

The `examples/` directory tracks ten seeded, deterministic game logs in multiple formats. These files are used both for documentation and for regression testing to ensure that engine changes produce intentional differences.

* `example_games.py` defines the `ExampleGame` helper along with the catalog of seeds.
* `test_examples_snapshot.py` renders each game with a fixed seed and asserts that the generated output matches the stored text files.
* After making behavior changes, refresh the tracked examples:

  ```bash
  python update_examples.py          # Regenerates examples/game_*.txt
  python update_statcast_examples.py # Regenerates examples/statcast_game_*.txt
  ```

  The scripts will re-render every example using the latest simulator behavior so the new output can be reviewed and committed alongside your code changes.

**Note:** Gameday JSON examples are tested via `test_gameday_regression.py` using curated single-event examples rather than full game snapshots.

## Project Structure

* `baseball.py` – core simulation engine and CLI entry point
* `teams.py` – fictional rosters, player attributes, and ambient context (umpires, weather, venues)
* `gameday.py` – type definitions for gameday JSON output format
* `example_games.py` – deterministic example definitions used for snapshot testing and documentation
* `examples/` – checked-in play-by-play logs generated from fixed seeds (narrative, statcast, and gameday formats)
* `test_*.py` – test suites that enforce realism constraints and snapshot parity
* `CLAUDE.md` – guidance for Claude Code AI assistant when working with this codebase

Feel free to modify the team definitions or extend the rules engine. When adding new realism features, remember to regenerate the example logs and expand the regression tests where appropriate so we continue guarding against past issues resurfacing.
