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

## Play-by-Play Style Guide

The file `pbp_example_1.txt` is a manually-written example of the target announcing style for the `narrative` commentary mode. It is not a direct output from the simulator. It serves as a stylistic reference for the tone, pacing, and descriptive detail that the simulation aims to emulate. This file should not be updated or regenerated, as it is a fixed benchmark for the desired "old-timey radio broadcast" feel.

## Project Structure

* `baseball.py` – core simulation engine and CLI entry point
* `teams.py` – fictional rosters, player attributes, and ambient context (umpires, weather, venues)
* `gameday.py` – type definitions for gameday JSON output format
* `example_games.py` – deterministic example definitions used for snapshot testing and documentation
* `examples/` – checked-in play-by-play logs generated from fixed seeds (narrative, statcast, and gameday formats)
* `test_*.py` – test suites that enforce realism constraints and snapshot parity
* `CLAUDE.md` – guidance for Claude Code AI assistant when working with this codebase

Feel free to modify the team definitions or extend the rules engine. When adding new realism features, remember to regenerate the example logs and expand the regression tests where appropriate so we continue guarding against past issues resurfacing.

## Testing Play-by-Play Generation

This repository uses two distinct snapshot files for different purposes, which should not be confused:

1. `examples/gameday_snapshot.json`: The canonical snapshot of the core simulator structure for structural tests (`test_gameday_snapshot.py`). This file is auto-generated and should not be manually tweaked. Use `python update_gameday_snapshot.py` to regenerate it.
2. `test_fixture_pbp_example_3.json`: A manually constructed/tweaked JSON fixture used specifically for testing NarrativeRenderer similarity against the target text (`pbp_example_3.txt`). It is intentionally modified to hit specific RNG outputs and should NOT be synced with `examples/gameday_snapshot.json`.

If you modify `test_fixture_pbp_example_3.json`, you must also update the generated test output `test_fixture_pbp_example_3.txt`.

### Sleep Baseball phrase coverage

The corpus contains 21 reference games: four `pbp_example_*.txt` alignment
targets and 17 episodes in `transcripts/sleep_baseball/`. Every source is
included in phrase-component coverage and source-linked rendering tests. The
four alignment targets additionally have full-game fixtures.

Run `python pbp_match_report.py` for both reports, or use `--corpus-only` and
`--alignment-only` to select one. The corpus report checks exact ordered pitch,
foul and count clauses against output from renderer methods, lists coverage
per episode and phrase kind, and identifies uncovered source lines. It measures
component capability, with compatible inputs tried where historical context
is unknown; introductions, inning narration and batted-ball outcomes remain
outside its automatic extraction. Use `python sleep_baseball_corpus.py --json`
to inspect every uncovered clause and its inferred inputs.

Full-game metrics exclude TTS delay markers and pregame chatter:
word overlap, coverage of source five-word sequences, and exact content lines
near the corresponding position in the game. Exact lines preserve word order
and repetition after normalizing minor count and punctuation differences.
`test_examples_snapshot.py` enforces a separate floor for each game, alongside
the original metrics that include playback markers.

The October 2026 phrase expansion improved content five-word coverage:

| Target | Before | After |
|--------|-------:|------:|
| Example 1 | 23.2% | 35.9% |
| Example 2 | 27.9% | 37.6% |
| Example 3 | 26.2% | 34.7% |
| Example 4 | 26.2% | 33.5% |

Location-specific called strikes and swinging strikeouts use pitch zone data,
and dirt calls require explicit pitch description evidence. Switch hitters use
the side they bat against the current pitcher. Count phrases such as “falls
behind” and “count evens up” depend on the resulting count, and “another” pitch
requires the same pitch type as the preceding pitch.

`sleep_baseball_phrase_cases.json` records exact source files, lines and
structured inputs for regression cases from every game.
`test_sleep_baseball_corpus.py` verifies provenance, actual renderer output,
the complete source inventory and per-source coverage floors. Adding a phrase
to an unused template pool does not count as support.

When expanding a pool, preserve existing entry order, then realign the fixture
timestamp seeds with `pbp_tools.py`: adding entries changes the pool modulus.
Regenerate the four rendered fixture text files and affected deterministic
examples, run the tests, and ratchet the content coverage floors as coverage
improves. Keep raw transcript prose out of game fixtures; fixtures describe
game events and select reusable renderer phrases.
