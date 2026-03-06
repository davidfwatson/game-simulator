# PBP Alignment Guide

This guide describes the task loop for aligning the rendered output of
`test_fixture_pbp_example_3.json` with the target text in `pbp_example_3.txt`.

Work is done **inning by inning** (one half-inning at a time). Each session
should pick up where the last one left off.

## Play Index Map

Use this to find which plays belong to each half-inning:

```
python3 -c "
import json
with open('test_fixture_pbp_example_3.json') as f:
    data = json.load(f)
for i, p in enumerate(data['liveData']['plays']['allPlays']):
    half = 'Top' if p['about']['isTopInning'] else 'Bot'
    print(f'Play {i:2d}: {half} {p[\"about\"][\"inning\"]} - {p[\"matchup\"][\"batter\"][\"fullName\"]:25s} -> {p[\"result\"][\"event\"]}')
"
```

## The Tools

All tools live in `pbp_tools.py`. Key commands:

| Command | What it does |
|---------|-------------|
| `inspect-play FILE --play N [-v]` | Shows all seed points and RNG choices for play N. Use `-v` to see the full list of options at each choice point. |
| `set-choice FILE --play N --point POINT --set STREAM:CALL:INDEX` | Updates the JSON timestamp at a seed point so that a specific template is selected. Preserves all other selections at the same seed point. |
| `search "phrase"` | Searches all template pools for a substring match. |
| `list-pool POOL_PATH` | Lists all templates in a pool (e.g., `narrative_templates.Single.default`). |
| `whatif SEED POOL_PATH` | Shows what a given seed would select from a pool. |
| `diff FILE TARGET_FILE` | Shows line-by-line mismatches and similarity stats. |

## How DirectRNG Works

Each timestamp in the JSON encodes a seed in its **fractional seconds**:

    "2025-09-27T23:05:19.0000300" → seed = 300

The seed is consumed as **base-100 digits** (right to left). Each `choice(pool)`
call uses one digit:

    choice(pool) → pool[seed_digit % len(pool)]
    then seed_digit = seed // 100   (advance to next digit)

Four independent RNG streams (`play`, `pitch`, `flow`, `color`) all start from
the same seed but advance independently.

**Reseeds happen at three points per at-bat:**

| Seed point | JSON field | Controls |
|-----------|-----------|----------|
| `play_start` | `about.startTime` | Batter intro template, matchup text |
| `event_N` | `playEvents[N].startTime` | Pitch connector, pitch description, foul text, count format |
| `play_outcome` | `about.endTime` | Outcome template (hit/out description), runner status |

Because each seed point is independent, changing one timestamp only affects
the choices at that specific point.

## Task Loop (Per Half-Inning)

### 1. Identify the target text

Find the half-inning boundaries in `pbp_example_3.txt`. The text flows
continuously — look for inning-transition phrases like "Bottom of the third"
or score summaries.

### 2. For each play in the half-inning

#### a) Inspect the current rendering

```bash
python pbp_tools.py inspect-play test_fixture_pbp_example_3.json --play N -v
```

This shows:
- Every seed point (with timestamp and JSON path)
- Every RNG choice made (which pool, which index, which template was selected)
- The full list of available templates at each choice point (with `-v`)
- The current rendered text for this play

#### b) Compare to target text

Read the corresponding section of `pbp_example_3.txt` and compare line by line.
Identify each mismatch:

- **Wrong template selected**: The target phrase exists in the pool but a different
  index was chosen.
- **Missing template**: The target phrase doesn't exist in any pool.
- **Structural issue**: Different line breaks, missing TTS markers, wrong
  pitcher/batter data in the JSON itself.

#### c) Search for the target phrase

```bash
python pbp_tools.py search "drops in front of"
```

If found: note the pool name and index. If not found: the phrase needs to be
added (see step d).

#### d) Add missing templates

When a target phrase has no matching template:

1. Identify the correct pool. The pool depends on context:
   - Pitch descriptions → `pitch_locations.ball.*` or `pitch_locations.strike.*`
   - Foul descriptions → `pitch_locations.foul`
   - Batter intros → `narrative_strings.batter_intro_*`
   - Hit outcomes → `narrative_templates.{Outcome}.{category}`
   - Pitch connectors → `narrative_strings.pitch_connectors*`
   - Runner status → `narrative_strings.leadoff_single`, `single_one_out`, etc.

2. Add the template to `commentary.py` in the appropriate list. **Add it at
   the end** of the list to minimize disruption.

3. **IMPORTANT**: Adding a template changes the pool size, which can break
   existing seed selections in other plays. After adding, re-run
   `inspect-play` for all plays in already-completed innings that use the
   same pool, and verify they still render correctly. If not, use `set-choice`
   to fix them.

#### e) Set the seed to select the right template

```bash
python pbp_tools.py set-choice test_fixture_pbp_example_3.json \
    --play N --point play_outcome \
    --set play:1:3
```

The `--set` format is `STREAM:CALL_NUMBER:DESIRED_INDEX`:
- `STREAM`: one of `play`, `pitch`, `flow`, `color`
- `CALL_NUMBER`: which call within that stream (0-indexed, as shown by `inspect-play`)
- `DESIRED_INDEX`: the index of the desired template in its pool

You can pass multiple `--set` flags to change multiple selections at the same
seed point:

```bash
python pbp_tools.py set-choice test_fixture_pbp_example_3.json \
    --play N --point event_0 \
    --set flow:0:5 --set pitch:0:4
```

Use `--dry-run` first to preview without writing.

#### f) Fix JSON data issues

Some mismatches aren't template issues — they're wrong data in the fixture JSON:
- Wrong pitcher (e.g., home pitcher listed for away at-bats)
- Wrong hit trajectory or location
- Wrong play result type
- Missing or wrong player names in credits

Edit `test_fixture_pbp_example_3.json` directly for these.

#### g) Verify

Re-run `inspect-play` to confirm the rendered output now matches the target.

### 3. After completing a half-inning

Run the consistency test to make sure the fixture still renders deterministically:

```bash
# Re-render the fixture to update the draft file
python3 -c "
import json
from renderers.narrative.renderer import NarrativeRenderer
with open('test_fixture_pbp_example_3.json') as f:
    data = json.load(f)
renderer = NarrativeRenderer(data)
with open('test_fixture_pbp_example_3.txt', 'w') as f:
    f.write(renderer.render())
"

# Run the tests
pytest test_examples_snapshot.py -k "pbp_example_3" -q
```

Also run the diff to track overall progress:

```bash
python pbp_tools.py diff test_fixture_pbp_example_3.json pbp_example_3.txt
```

## Common Patterns

### Pitch descriptions on one line vs separate lines

The target text often puts multiple pitches on one line:
> "Fastball. Misses just a bit outside. It's one and oh. And the 1-0... Another fastball off the plate, two and oh."

The renderer currently puts each pitch on a separate line. This is a **structural
difference in the renderer** — aligning this requires renderer changes, not just
seed/template changes. Note it and move on; these can be addressed in a later pass.

### TTS SPLIT markers

These are generated from timestamp gaps between events. They're controlled by
the `endTime` field on pitch events and the delay calculation logic. Getting
exact TTS delay values right requires setting event endTime timestamps to create
the right gaps.

### Count format: "one-oh" vs "1-0"

The renderer uses spoken words (`one-oh`) while the target sometimes uses digits
(`1-0`). This is controlled by `get_spoken_count()` in `renderers/narrative/helpers.py`.
Note any count-format mismatches — they may need a renderer change.

## IMPORTANT: Fixture JSON Must Match the Target Game

The fixture JSON (`test_fixture_pbp_example_3.json`) was originally generated
from a simulation with seed 42, **not** reverse-engineered from the target
text. This means the game events (outcomes, pitch sequences, lineups) in the
JSON may not match what happens in the target text. For example:

- The fixture has 75 plays; the target game has a different number of at-bats
- The fixture has 6 walks; the target appears to have ~0
- Outcome distributions don't fully align

**Before working on phrasing alignment**, the fixture JSON must be updated so
that the actual game events (which batter, which pitcher, what outcome, what
pitch sequence) match the target text. This is prerequisite work — no amount
of seed-tweaking will produce "Fly ball into shallow left" if the JSON says
the outcome is a Groundout.

The alignment work has two phases:

### Phase 1: Fix game event data in the JSON

For each at-bat in the target text:
1. Identify the batter, pitcher, outcome, and pitch sequence
2. Ensure the corresponding play in the fixture JSON has the right data
3. Add/remove/reorder plays as needed so the JSON game matches the target game

### Phase 2: Align phrasing via seeds and templates

Once the game events match, use the seed tools to select the right phrasing
(this is what the rest of this guide covers).

## Progress Tracking

After completing each half-inning, update this section. The play ranges below
are from the **current** fixture JSON and will need updating once Phase 1
(fixing game events) is complete.

| Half-Inning | Fixture Plays | Phase 1 (events) | Phase 2 (phrasing) |
|-------------|---------------|-------------------|--------------------|
| Pre-game | — | Not started | Not started |
| Top 1 | 0-3 | Not started | Not started |
| Bot 1 | 4-6 | Not started | Not started |
| Top 2 | 7-9 | Not started | Not started |
| Bot 2 | 10-13 | Not started | Not started |
| Top 3 | 14-16 | Not started | Not started |
| Bot 3 | 17-20 | Not started | Not started |
| Top 4 | 21-23 | Not started | Not started |
| Bot 4 | 24-35 | Not started | Not started |
| Top 5 | 36-40 | Not started | Not started |
| Bot 5 | 41-44 | Not started | Not started |
| Top 6 | 45-47 | Not started | Not started |
| Bot 6 | 48-52 | Not started | Not started |
| Top 7 | 53-56 | Not started | Not started |
| Bot 7 | 57-61 | Not started | Not started |
| Top 8 | 62-67 | Not started | Not started |
| Bot 8 | 68-70 | Not started | Not started |
| Top 9 | 71-74 | Not started | Not started |
| Post-game | — | Not started | Not started |
