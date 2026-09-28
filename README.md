# Realistic MLB Game Simulator

This repository contains a command line play-by-play simulator that aims to produce logs that feel indistinguishable from a real Major League Baseball broadcast. The engine models pitch-by-pitch sequences, strategic bullpen usage, and situational events (mound visits, defensive alignments, challenges, weather, etc.) to generate rich narration while respecting modern MLB rules.

## Getting Started

### Requirements

* Python 3.9 or newer

Install the pinned Python dependencies with `python -m pip install -r requirements.txt`, then run the simulator:

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
2. `test_fixture_pbp_example_3.json`: A manually constructed/tweaked JSON fixture used specifically for testing NarrativeRenderer similarity against the target text (`pbp_example_3.txt`). It stores explicit commentary draws to select specific wording and should NOT be synced with `examples/gameday_snapshot.json`.

If you modify `test_fixture_pbp_example_3.json`, you must also update the generated test output `test_fixture_pbp_example_3.txt`.


## Commentary randomness and alignment

Randomness for wording is separate from game timing and game outcomes.
`gameData.commentarySeed` stores the default rendering seed; `--commentary-seed`
overrides it (including zero). A fixed seed and event sequence reproduce the
same wording even after timestamp corrections. Four independent streams control
plays, pitches, flow, and color commentary.

Curated fixtures can override any number of draws with `commentaryRng`:

```json
{
  "commentaryRng": {
    "play_outcome": {
      "play": [3, 12, 1],
      "flow": [25]
    }
  }
}
```

Store `init` under `gameData`, `play_start` and `play_outcome` on the play,
and `event` on a pitch/event. Each list entry controls one call: `choice()` uses
an index modulo the pool size, and `random()` uses the last two digits as
hundredths. Missing or exhausted lists continue with the seeded stream; they do
not become a repeating zero. There is no packed timestamp format or direct mode.

Use `python pbp_tools.py inspect-play FIXTURE --play N -v` to inspect draws and
`set-choice FIXTURE --play N --point event_0 --set pitch:3:7` to select wording.
The tooling edits commentary metadata without changing timestamps.
See [PBP_ALIGNMENT_GUIDE.md](PBP_ALIGNMENT_GUIDE.md) for the workflow.

Register new `pbp_example_N.txt` references in `pbp_comparison.py`, together with
a matching JSON fixture, rendered text snapshot, and reviewed comparison
thresholds. The tests fail if any example is missing or unregistered.
Run `python pbp_match_report.py --check` to check all examples, or add `--json`
for machine-readable results. Content-only exact matching prevents repeated
TTS markers from masking wording regressions.


## Transcript-derived comparison cases

The 17 cleaned episodes in `transcripts/sleep_baseball/` now have 78 reviewed
comparison cases in `transcript_cases/`. Each case cites an exact source line
and supplies the baseball context needed to reproduce a particular phrase.
Compiled fixtures in `examples/transcript_cases/` store ordinary commentary
draw lists and corresponding text snapshots. Tests replay those lists through
the production renderer methods and require the source phrase's words in order.
They also fail when a source episode, case, fixture, or snapshot goes missing.
The per-episode case minimums are registered in `pbp_comparison.py`, and
`python pbp_match_report.py --check` also verifies this entire corpus.

These are representative situation comparisons, **not full-game reconstructions
or whole-transcript similarity scores**. The four existing full-game PBP
alignment fixtures keep their original minimums. Numeric pitch metrics in a
case are scenario inputs used to exercise the intended category, not measured
statistics from the broadcast.

```bash
python transcript_comparison.py             # Report all 17 episodes / 78 cases
python update_transcript_examples.py --check # Verify saved fixtures and snapshots
python update_transcript_examples.py         # Recompile after reviewing a change
```

Use `source_line`, `source_text`, `expected`, `kind`, `pool`, `template`, and
`inputs` in each authoring case. Add new wording only to a pool consistent with
its facts: bunt singles require bunt data; intentional walks require an
intentional-walk result; a strikeout reach requires the batter's safe movement
to the stated base, and wild-pitch wording requires the corresponding event. Keep expected
phrases grounded in the transcript and review regenerated snapshots.
