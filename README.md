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

Team definitions may specify `spokenLocation` and `spokenLocationWithState` for
geographic references in dialogue. These are noun phrases without prepositions:
the Bay Area Bombers use `the Bay Area` and `California's Bay Area`, while their
canonical `name` and `locationName` stay unchanged. Without overrides, narration
uses `locationName` (or the location inferred from the team name) and appends
`state` when available. Set both spoken forms for regions that do not fit the
usual city/state wording. The simulator and anonymizer preserve these optional
fields in Gameday team data; older saved games need the fields added or their
data regenerated to use the new regional phrasing.

## Project Structure

* `baseball.py` – core simulation engine and CLI entry point
* `teams.py` – fictional rosters and player attributes
* `commentary.py` – shared wording pools for pitches, plays, transitions, and radio commentary
* `gameday.py` – type definitions for gameday JSON output format
* `example_games.py` – deterministic example definitions used for snapshot testing and documentation
* `examples/` – checked-in play-by-play logs generated from fixed seeds (narrative, statcast, and gameday formats)
* `test_*.py` – test suites that enforce realism constraints and snapshot parity
* `CLAUDE.md` – guidance for Claude Code AI assistant when working with this codebase

Feel free to modify the team definitions or extend the rules engine. When adding new realism features, remember to regenerate the example logs and expand the regression tests where appropriate so we continue guarding against past issues resurfacing.

## Testing Play-by-Play Generation

Snapshots belong to different inputs and must be regenerated through the matching workflow. For example:

1. `examples/gameday_snapshot.json`: The canonical snapshot of the core simulator structure for structural tests (`test_gameday_snapshot.py`). This file is auto-generated and should not be manually tweaked. Use `python update_gameday_snapshot.py` to regenerate it.
2. `test_fixture_pbp_example_3.json`: A manually constructed JSON fixture for NarrativeRenderer comparison against `pbp_example_3.txt`. It stores explicit commentary draws and is independent of the simulator snapshot. The same fixture/reference/snapshot pattern applies to examples 1–4.
3. `examples/transcript_games/episode_NNN.json` and `.txt`: Full broadcast fixtures compiled and fitted from reviewed event ledgers in `transcript_games/`.
4. `examples/transcript_cases/episode_NNN.json` and `.txt`: Focused helper cases compiled from `transcript_cases/`.

If you modify `test_fixture_pbp_example_3.json`, you must also update the generated test output `test_fixture_pbp_example_3.txt`.


## Commentary randomness and alignment

Randomness for wording is separate from game timing and game outcomes.
`gameData.commentarySeed` stores the default rendering seed; `--commentary-seed`
overrides it (including zero). A fixed seed and event sequence reproduce the
same wording even after timestamp corrections. Four independent streams control
plays, pitches, flow, and color commentary. A fifth, `optional`, holds only the
draws that decide whether an optional sentence is said at all (the count after
"for ball two", a strikeout's "for out number two", a hit's situation sentence).
Simulated games say each at the rate the Sleep Baseball hosts do, measured by
`python optional_sentence_rates.py` and recorded in `OPTIONAL_SENTENCE_RATES`.

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

`python fit_transcript_games.py --references` refits the four reference fixtures
automatically (it replaces hand-edited draws; see the transcript-games README).

Register new `pbp_example_N.txt` references in `pbp_comparison.py`, together with
a matching JSON fixture, rendered text snapshot, and reviewed comparison
thresholds. The tests fail if any example is missing or unregistered.
Run `python pbp_match_report.py --check` without example numbers to check the
original four references, all 78 representative cases, and all 17 full broadcast
fixtures. Add `--json` for machine-readable results. Passing example numbers
limits that command to the selected original references. Content-only exact
matching prevents repeated TTS markers from masking wording regressions.


## Full broadcast fixtures

All 17 cleaned episodes in `transcripts/sleep_baseball/` have reviewed event
ledgers in `transcript_games/` and ordinary Gameday JSON/text fixtures in
`examples/transcript_games/`. They cover 1,106 observed appearance records,
3,727 pitches, and 29 nonpitch actions. Episodes 001 and 051 remain incomplete:
the first fades out during the ninth, and the second ends during a rain delay.
Missing innings and unbroadcast pitches are documented rather than filled in.

The full-game wording is an approximate comparison baseline. It reproduces the
recorded baseball events through the production renderer; it does not reproduce
every anecdote or line of announcer banter verbatim. Source ranges, ambiguity
notes, and completion flags distinguish observed facts from gaps. Verbal pitch
locations and source-supported hit categories do not require invented tracking
coordinates, velocities, or launch angles.

The latest corpus pass appended 366 templates: 188 pitch/delivery templates and
178 play/transition templates. Their source references are retained in
`transcript_pitch_additions.json` and `transcript_play_additions.json`.

```bash
python transcript_game_fixtures.py            # Compile reviewed facts; writes JSON and text
python fit_transcript_games.py                 # Recompile and fit ordinary commentaryRng draws
python full_transcript_comparison.py --check   # Compare all 17 broadcasts and per-play wording
python full_transcript_comparison.py 1 51 --gaps 5
python full_transcript_comparison.py --json
python pbp_match_report.py --check              # Check all three comparison catalogs
```

Both compiler and fitter overwrite `examples/transcript_games/`. The fitter is
an offline authoring tool: it selects reachable production phrases, saves their
integer draws, and verifies replay with `NarrativeRenderer`. It does not inject
source prose into generated narration. Review the resulting JSON/text changes
before updating comparison minimums. See [transcript_games/README.md](transcript_games/README.md)
for the ledger schema, focused follow-up loop, and factual checks.

## Representative transcript cases

The 78 reviewed cases in `transcript_cases/` remain a separate, focused layer.
Each cites an exact source line and supplies the context for a particular
renderer helper. Their compiled fixtures in `examples/transcript_cases/` replay
saved draw lists through production methods, require the expected words in
order, and compare exact text snapshots. Catalog checks catch missing episodes,
cases, fixtures, and snapshots.

```bash
python transcript_comparison.py             # Report all 17 episodes / 78 cases
python update_transcript_examples.py --check # Verify saved cases and snapshots
python update_transcript_examples.py         # Recompile reviewed helper cases
```

Use `source_line`, `source_text`, `expected`, `kind`, `pool`, `template`, and
`inputs` in each authoring case. Numeric pitch metrics in older helper cases are
synthetic scenario inputs, not measurements from the broadcasts. New full-game
ledgers preserve the source's verbal facts instead. Add wording only to pools
whose required situation is present, and test the actual helper or event route.

## Automatic phrase coverage

The automatic corpus report scans all 21 source games: the four PBP references
and the 17 episode transcripts. It measures exact ordered pitch, foul and count
clauses against output from production renderer methods. Each episode reports
its eligible and supported clauses by phrase kind, with uncovered source files,
line numbers and inferred inputs. Per-source inventory and pitch-support floors
prevent easy count phrases or omitted episodes from masking regressions.

```bash
python pbp_match_report.py --corpus-only --check
python pbp_match_report.py --corpus-only --uncovered-limit 10
python sleep_baseball_corpus.py --json
python pbp_match_report.py --alignment-only
```

The default report includes this layer alongside the existing PBP, focused-case
and full-broadcast comparisons. `sleep_baseball_phrase_cases.json` supplies
additional source-linked component regression cases from every reference game.
Tests verify exact provenance and actual reachable output, rather than counting
an entry in an unused template pool as support.

Component support describes phrase capability. Unknown location stays unknown;
other missing context is tried across compatible inputs. Case and punctuation
are ignored, while word order, articles, repetition and numeric spelling remain
significant. Introductions, inning narration, batted-ball outcomes and banter are
outside the automatic extractor; full-game comparisons cover a different scope.
Complete pitch calls may omit the pitch name, and numbered ball/strike calls use
the resulting count. Ground-contact phrasing requires explicit dirt or bounce
evidence; a low zone alone is insufficient.
