# Realistic MLB Game Simulator

This repository contains a command line play-by-play simulator that aims to produce logs that feel indistinguishable from a real Major League Baseball broadcast. The engine models pitch-by-pitch sequences, strategic bullpen usage, and situational events (mound visits, defensive alignments, challenges, weather, etc.) to generate rich narration while respecting modern MLB rules.

## Getting Started

### Requirements

* Python 3.9 or newer

Install the Python dependencies (only the standard library is required) and run the simulator directly:

```bash
python baseball.py
```

Use the available CLI flags to tailor the narration style:

* `--terse` – switch to the more compact play-by-play phrasing that mirrors data feeds.
* `--bracketed-ui` – render base runner state using legacy bracketed indicators instead of prose.

### Running the Test Suite

The project ships with a growing collection of regression tests that encode previously observed realism issues. Run everything with:

```bash
pytest -q
```

The tests cover items such as bullpen variability, pitch vocabulary diversity, realistic catcher groundout frequencies, and snapshot comparisons against curated example games.

## Deterministic Example Games

The `examples/` directory tracks ten seeded, deterministic game logs. These files are used both for documentation and for regression testing to ensure that engine changes produce intentional differences.

* `example_games.py` defines the `ExampleGame` helper along with the catalog of seeds.
* `test_examples_snapshot.py` renders each game with a fixed seed and asserts that the generated output matches the stored text files.
* `update_examples.py` provides a convenient way to refresh the tracked examples after making a behavior change:

  ```bash
  python update_examples.py
  ```

  The script will re-render every example using the latest simulator behavior so the new output can be reviewed and committed alongside your code changes.

## Project Structure

* `baseball.py` – core simulation engine and CLI entry point.
* `teams.py` – fictional rosters, player attributes, and ambient context (umpires, weather, venues).
* `example_games.py` – deterministic example definitions used for snapshot testing and documentation.
* `examples/` – checked-in play-by-play logs generated from fixed seeds.
* `test_*.py` – pytest suites that enforce realism constraints and snapshot parity.

Feel free to modify the team definitions or extend the rules engine. When adding new realism features, remember to regenerate the example logs and expand the regression tests where appropriate so we continue guarding against past issues resurfacing.
