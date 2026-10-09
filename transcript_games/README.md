# Full broadcast event ledgers

These reviewed ledgers reconstruct every observed baseball appearance and pitch
in the 17 source episodes under [`transcripts/sleep_baseball/`](../transcripts/sleep_baseball/README.md).
The catalog contains 1,106 appearance records, 3,727 pitches, and 29 nonpitch
actions. Appearance records include interrupted or incomplete at-bats; the total
is not an official plate-appearance statistic.

The matching JSON and text under `examples/transcript_games/` are generated
artifacts. Their narration is an approximate wording baseline, including
pregame and inning transitions, rather than a verbatim recreation of all radio
banter. The original four `pbp_example_N.txt` comparisons and the 78 focused
cases in `transcript_cases/` remain separate regression layers.

## Source facts and boundaries

Keep the cleaned source text unchanged. Each ledger identifies `source_file`,
and each play and pitch points to its source lines. Preserve disagreements
between a recap and the narrated events in `notes`, with the relevant evidence.
Use `gaps` for missing intervals instead of manufacturing the expected inning,
at-bat, or pitch sequence.

`complete` means the broadcast reaches the game's conclusion. Episode 001 ends
during the top of the ninth and omits an earlier half-inning; episode 051 ends
at a rain delay after the top of the sixth. Both have `complete: false` and an
`ending_reason`. They must not acquire a winner or a fabricated resumption.
`postgame_start`, when known, records the source boundary after the final play.
Other completed broadcasts can still contain documented intervals without pitch
detail. A complete broadcast is not evidence for unseen pitches.

## Ledger fields

| Field | Meaning |
|---|---|
| `episode`, `source_file` | Episode number and unchanged source filename. |
| `game` | Known teams, venue, starting lineups, pitchers, optional managers, and optional `season_stats`. Omit unknown handedness. |
| `plays` | Ordered observed appearances, including partial appearances. |
| `inning`, `top` | Inning number and whether the visiting team is batting. |
| `batter`, `pitcher`, `outcome` | Identified participants and observed result; use `Incomplete` when the appearance does not finish. |
| `source_start`, `source_end` | One-based inclusive source range for the appearance. Ranges may share a line that contains consecutive events. |
| `outs`, `score` | Outs after the appearance and the known score as `[away, home]`. |
| `pitches` | Ordered observed pitches and nonpitch actions, each with a one-based `line`. |
| `hit` | Known batted-ball location, trajectory, depth, lane, hardness, and source-supported category or situation facts. |
| `fielders`, `runners` | Fielding sequence and runner movements needed to describe the actual play. |
| `substitution` | A pinch hitter: `{"type": "pinch_hitter", "replaces": "Name"}`, `replaces` only when the hosts say it. |
| `initial_count`, pitch `count` | Known count before an appearance or particular pitch when earlier pitches were not narrated. |
| `notes`, `gaps`, `ending_reason` | Provenance and unresolved ambiguity, not narration overrides. |

Pitch codes are `B` (ball), `C` (called strike), `S` (swinging strike), `F`
(foul), `X` (in play), `P` (pitchout), and `H` (hit by pitch). Use `U` for an
observed pitch whose type of result is unspecified; `isStrike: true` can record
a known strike without claiming it was called or swung at. Use `A` for a
nonpitch action, with a factual `eventType` such as `caught_stealing`,
`stolen_base`, `pickoff`, or `wild_pitch` and the known runner movements.
Do not turn a pickoff attempt into an extra pitch or invent an omitted pitch to
complete the count. Separate events can legitimately refer to the same line.

A runner movement records `name`, `start`, `end`, and optional `out`. Use
`1B`, `2B`, `3B`, or `score` for known destinations. Preserve the order of outs
on double plays and tags. Explicitly record discretionary advances and unusual
safe arrivals; the compiler may derive forced advances from baseball rules.

### Verbal locations and hit categories

A pitch's `location` describes the source's words, not tracking coordinates:

```json
{"code": "B", "type": "Fastball", "line": 78, "location": "outside"}
```

Supported ball locations include `high`, `low`, `inside`, `outside`, `dirt`,
`high_inside`, `high_outside`, `low_inside`, and `low_outside`. Called strikes
can use `outside_corner`, `inside_corner`, `corner`, `middle`, or `low`.
The compiler copies this to `playEvents[N].details.location`. Omit unknown
locations. Existing numeric `zone` data remains supported, but do not invent a
zone or batter handedness from a verbal call.

For an explicitly described bloop single to left, the appearance can contain:

```json
"hit": {
  "location": "LF",
  "trajectory": "fly_ball",
  "categoryOverride": "bloop"
}
```

The compiler copies `hit` into the in-play event's `hitData`. Use only
source-supported categories. A throwing error, ground-rule double, walkoff,
forceout, or unusual double play also needs the corresponding outcome, runner,
and fielder facts. Do not add arbitrary velocity, exit-speed, launch-angle, or
pitch-coordinate values to reach a preferred wording pool.

### Where the ball went, and other facts the hosts state

The hosts say things about a play that the older fixtures could not hold, so no
draw could produce them: "lined into the gap in left center", "all the way in
the corner", "on the warning track", "hard grounder", a starter's record and
ERA, a pinch hitter. `python missed_words.py` measures how many source words
each such fact type accounts for (see [the report](COMPARISON_REPORT.md)).
These facts are recorded where a StatsAPI feed keeps them, or in a clearly
named extension field when a feed implies them only through numbers:

| Ledger | Compiled to | Values |
|---|---|---|
| `hit.hardness` | `hitData.hardness` (StatsAPI) | `soft`, `medium`, `hard` |
| `hit.depth` | `hitData.depth` (extension; a feed implies it by `totalDistance`) | `shallow`, `deep`, `warning_track`, `wall` (the ball reached the wall) |
| `hit.lane` | `hitData.lane` (extension; a feed implies it by `coordinates`) | `left_line`, `left_center`, `middle`, `right_center`, `right_line`, `left_side`, `right_side` |
| `game.season_stats` | `boxscore.teams.<side>.players.ID<n>.seasonStats` (StatsAPI) | `{"Name": {"pitching": {"wins": 7, "losses": 8, "era": "5.21"}}}` |
| play `substitution` | an `Offensive Substitution` action (`eventType: offensive_substitution`, `isSubstitution`, `replacedPlayer`) at the start of the at-bat's `playEvents` (StatsAPI) | `{"type": "pinch_hitter", "replaces": "Name"}` |

The runners who score or take third on a ball in play, and the runs a hit or a
home run drove in, were already recorded (`runners`, `result.rbi`); the
renderer now says them ("Nomo will score. Brown will score.", "And that's an
RBI single for Ali Nunez", "a two-run homer").

A template that asserts where or how hard a ball went ("all the way to the
wall", "hard grounder", "into the gap", "squeaks through the infield") is used
only when the ball's facts support the claim
(`renderers/narrative/batted_ball.py`). Under `strictFacts` an unrecorded
claim is never made; elsewhere a ball with none of the fields keeps the older,
unrestricted pools. A recorded depth or lane also sharpens the direction
("down the left field line", "to deep right center"). The simulator writes
`hardness` from exit velocity and `depth`/`lane` from its field model
(`fieldsim.spot`), so simulated games say the same facts; it has no pinch
hitters or season statistics, and the renderer says nothing about either when
they are absent.

`annotate_transcript_facts.py` records the explicit depth, lane, hardness and
ground-rule doubles from each ball's call, and starters' season records from
the pregame, in the 17 ledgers and straight into the four reference fixtures.
It keeps existing values and skips contradictory words. Pinch hitters were
annotated by hand. Review its output (`--dry-run` prints every fact with the
words it came from) against the source.

`annotate_transcript_locations.py` is an optional authoring helper for explicit
verbal locations. It edits ledgers, preserves existing annotations, and skips
lines containing multiple pitches. Review its changes against the source;
ambiguous lines still need manual interpretation.

## Compile, fit, and compare

Run commands from the repository root:

```bash
python transcript_game_fixtures.py
python fit_transcript_games.py
python fit_transcript_games.py 5 49          # selected episodes
python fit_transcript_games.py --references  # the four pbp_example fixtures
python optional_sentence_rates.py
python missed_words.py                       # unmatched source words by cause
python annotate_transcript_facts.py --dry-run
python full_transcript_comparison.py --check
python full_transcript_comparison.py 49 50 --gaps 5
python full_transcript_comparison.py 49 --json
python pbp_match_report.py --check
```

The compiler writes ordinary Gameday JSON and an initial rendering for every
ledger. The fitter recompiles every ledger, searches choices actually offered
by production rendering, and saves explicit integer `commentaryRng` lists with
the resulting text. It verifies that ordinary `NarrativeRenderer` replay
matches its fitted output. Source prose is never injected into production
narration. The source path, hash, and line references are provenance.

### How draws are fitted

Each reseed point (`init`, `play_start`, each `event`, `play_outcome`) has a
source window, read with host asides removed:

| Point | Window |
|---|---|
| `init` | Everything before the first appearance. |
| `play_start` | From the line after the previous appearance to the line before the first pitch: the inning transition and the introduction. If the introduction shares the first pitch's line, only the words before `...`. |
| `event` | The pitch's line, through the line before the next event. |
| `play_outcome` | From the last pitch's line to the end of the appearance. |

A `choice(options)` call takes the option whose words best match the point's
window: weighted 1-, 2- and 3-gram matches minus 0.6 per unmatched n-gram.

A `random()` gate decides whether an optional sentence is said, or which form
it takes. Gates are fitted per point. The fitter first picks the best of six
whole-game constants, as before, then runs a coordinate descent. A coordinate
is the k-th gate of one stream at one kind of point, such as the first colour
gate at every `play_start` (the at-bat recap). The renderer's draws are
instrumented to report the thresholds they are compared with, so the fitter
tries one digit per outcome interval: 0 and 99 for the outer intervals, the
middle for inner ones, and every 0.05 when the renderer uses the draw as an
integer. One render tries a value at every point of that kind at once. Each
point keeps the value whose rendered words, its segment, score best against
its window, with unmatched n-grams penalised 0.3 rather than 0.6. Choices are
refitted greedily on every render, so they follow the gates. Passes repeat
until one changes no draw and exposes no new gate or threshold (a changed gate
can reveal gates behind it), up to six; the 17 broadcasts settle in two. Saved gate
digits are canonical (0, 99 or an interval's middle), so a re-measured
threshold does not silently flip them. All 17 broadcasts refit in under three
minutes.

The four `pbp_example_N` references have no line-level ledger.
`python fit_transcript_games.py --references` aligns each fixture's current
rendering word by word with its reference to find each point's window (the
source between the last aligned word before the segment and the first after
it), fits every choice and gate as above, and repeats the alignment once from
the new rendering, resuming from the first round's gate values. This replaces their hand-edited draws.

### Optional sentences

Some sentences the hosts say only part of the time. The renderer builds each
one, then asks `NarrativeRenderer._optional(name)`, which takes one draw from
the `optional` stream. Dropping the sentence never shifts a draw in another
stream. Simulated games say each at the hosts' measured rate
(`OPTIONAL_SENTENCE_RATES`; rerun `python optional_sentence_rates.py` to
measure again):

| Sentence | Said by the hosts |
|---|---:|
| The count after a call that already numbers it ("Inside for ball two. Two and oh.") | 16 of 159, 10.1% |
| ", for out number N" added to a one- or two-out strikeout call that does not say which out it was | 132 of 189, 69.8% |
| ", to end the inning" added the same way to a third-out strikeout | 77 of 91, 84.6% |
| The situation sentence after a single, double or triple ("A two-out single for Kosinski.", or after a run-scoring hit "And that's an RBI single for Ali Nunez.") | 147 of 207, 71.0% |
| Naming a runner a ball in play brings home or to third ("Nomo will score.") | 66 of 82, 80.5% |
| The runs a home run drove in ("And that's a two-run homer for Steve McDykel.") | 26 of 33, 78.8% |

The counts come from the 17 ledgers (each recorded pitch or play with its
source lines) plus the four references scanned line by line, asides excluded;
the runner and home-run sentences need each reference play's recorded facts,
so their reference calls come from the word alignment in `missed_words.py`.
Home runs are rare in these broadcasts, so that rate rests on 33 opportunities
rather than the 80 the others need.
They are phrase matches, so they are approximate. The same audit of the 17
ledgers found sentences that stay unconditional because the hosts almost
always say them:
the count after an unnumbered call (98%), the batter introduction (99%), the
inning-break score summary (99%), its "we'll be back" closer (93%), the
next-inning introduction (96%), the score after a scoring play (97%), and the
result's out number on a ball in play (92%).

Both commands overwrite `examples/transcript_games/episode_NNN.json` and `.txt`.
Refitting deliberately selects draws again, so it replaces manual draw edits
made only to those generated files. Keep durable factual changes in the ledger
and review the generated changes before committing them.

`full_transcript_comparison.py` reports whole-broadcast word overlap, source
5-gram recall, content-only exact lines, and mean per-appearance ordered-word
coverage. `--gaps N` shows the N weakest appearances for each selected episode;
`--json` includes their source ranges, target text, and rendered text. Ordered
coverage preserves word order; vocabulary overlap alone does not establish a
match. Annotated host asides are excluded from the source side (see below).
Differences in line layout and unmarked colour still affect these
measurements, so use the local source/rendered comparison to diagnose an actual
gap.

With no episode arguments, `--check` also validates the complete source,
ledger, fixture, and snapshot catalog against `FULL_TRANSCRIPT_MINIMUMS` in
`pbp_comparison.py`. Appearance and pitch counts are exact coverage requirements;
wording has reviewed minimums. `pbp_match_report.py --check` without original
example numbers checks these 17 broadcasts, the four original references, and
all 78 focused cases. Measure current results rather than copying a percentage
from an old report.

## Host asides

Between-innings breaks were cut from the cleaned sources, so they count for
nothing in any metric. Host asides get the same treatment without editing the
source: `transcript_asides/<stem>.json` marks them for all 17 episodes and the
four `pbp_example_N.txt` references. Each file records the repository-relative
`source_file` and its `source_sha256`; a changed source fails validation until
its spans are reviewed again. Each entry is one of:

```json
{"line": 279, "text": "And the crew chief is now calling time, there appears to be a goat in center field.", "category": "story", "note": "goat on the field"}
{"line": 281, "category": "story", "note": "goat carried off"}
{"line": 12, "end_line": 26, "category": "banter", "note": "pregame interview"}
```

`text` must be an exact substring of `line` (add `occurrence` when it repeats).
Without `text`, the entry covers whole lines through `end_line`. Spans may not
overlap or cover blank lines. Categories are `story`, `incident`,
`mound_visit`, `trivia`, `banter`, `promo`, and `crowd`; `note` says briefly
what the aside is, for a future aside engine.

`transcript_asides.metric_source_text()` replaces each span with a hard-break
marker while keeping line numbers, so ledger ranges and component provenance
stay valid. No 5-gram, ordered-match run, exact line or extracted clause may
cross that marker, because the words on either side were never adjacent; a
line split by an aside counts as separate pieces. Every corpus source must have
an annotation file, even an empty one: a missing file is an error rather than a
silent fallback to the unfiltered source. `full_transcript_comparison.py`,
`pbp_comparison.compare_example`, the component inventory in
`sleep_baseball_corpus.py`, and `pbp_tools.py diff` all read sources this way.
The metric definitions are otherwise unchanged.

Mark only what no Gameday-driven engine could narrate. Pitch calls, counts,
outcomes, runners, score and inning, batter intros, at-bat history, season
stats, lineup, defensive and pitching changes, pinch hitters, intentional walks,
the bare mound visit or ejection, weather, umpires, managers, the fishbowl
drawing, break sign-offs and returns, and the postgame recap are not asides.
When a sentence mixes both, mark only the aside clause. Tests reject an
annotation that overlaps the recorded call on a ledger pitch line (the delivery
cue, the result or play sentence after it, and a following count), removes a
batter, fielder or runner named in that play's text, empties an appearance
range, or that
removes a phrase a focused transcript case or phrase case expects the renderer
to produce. `python transcript_asides.py` summarizes the marked spans.
[COMPARISON_REPORT.md](COMPARISON_REPORT.md) gives the before/after numbers.

## Follow up on a wording gap

1. Read the cited source range and ledger first. Correct baseball facts and
   preserve ambiguities before changing a wording choice.
2. Inspect the compiled play with
   `python pbp_tools.py inspect-play examples/transcript_games/episode_049.json --play 0 -v`.
   Search existing pools with `python pbp_tools.py search "foul back"`.
3. Add a reusable template only to a route whose facts support it. Append it to
   preserve existing selected indices. Keep source provenance in
   `transcript_pitch_additions.json` or `transcript_play_additions.json` and
   exercise the actual renderer helper or event route in a regression test.
4. Refit, inspect the resulting JSON/text diff, and run comparison and replay
   checks. Adjust reviewed wording minimums only after measuring the intended
   result; do not reduce factual coverage to make a check pass.

The latest source-mining pass appended 366 templates: 188 pitch/delivery
variants and 178 play/transition variants. The recorded-facts pass added 50
more play rows to `transcript_play_additions.json` (pinch hitters, season
records, runners who score or take third, RBI hits, home-run runs, ground-rule
doubles). The source catalogs can also retain
entries that were already available; their row counts are not necessarily the
number of newly inserted templates.

```bash
python -m unittest test_transcript_games test_transcript_comparison test_transcript_phrase_additions
python pbp_match_report.py --check
```

See [PBP_ALIGNMENT_GUIDE.md](../PBP_ALIGNMENT_GUIDE.md) for draw editing and the
historical example-3 alignment checklist.
