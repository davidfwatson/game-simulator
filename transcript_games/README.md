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
| `game` | Known teams, venue, starting lineups, pitchers, optional managers, and the optional facts below (`season_stats`, `pitcher_roles`, `decisions`, `away_state`/`home_state`, `weather`, `crew_chief`). Omit unknown handedness. |
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

A runner movement records `name`, `start`, `end`, and optional `out`, and the
`throw` and `slide` the hosts state (see below). Use
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
| movement `throw` | runner `details.throw`, or a steal's `details.runners[].throw` (extension; a feed has no throws) | `not_in_time`, `beaten` ("he will beat the throw"), `none` ("no play at second"), and for a runner caught stealing `in_time` |
| movement `slide` | runner `details.slide`, or a steal's `details.runners[].slide` (extension) | `true`, `under_tag`, `ahead_of_tag` |
| `game.pitcher_roles` | `gameData.players.ID<n>.pitcherRole` (extension; a feed has no roles) | `{"Name": "closer"}`; also `starter`, `reliever` |
| `game.season_stats` for a reliever | `seasonStats.pitching` as above | `{"inningsPitched": "12.0", "era": "2.67"}` |
| `game.decisions` | `liveData.decisions` (StatsAPI) | `{"winner": "Name", "loser": "Name", "save": "Name"}` |
| `game.away_state`, `game.home_state` | `gameData.teams.<side>.state` | `"Wisconsin"`: said in "Tomah, Wisconsin" |
| `game.weather` | `gameData.weather` (StatsAPI) | `{"temp": "74", "wind": "In From CF"}`; the wind is `In From` or `Out To` a field (`LF`, `CF`, `RF`, and the extensions `LCF`, `RCF`), or a bare `In` / `Out` |
| `game.crew_chief` | `gameData.umpires[0]` (the list the simulator writes) | `"V.R. Montebianco"` |

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
(`fieldsim.spot`; null when nothing is notable), so simulated games say the
same facts. A real StatsAPI feed has neither extension field, so the renderer
derives them from its `coordinates` and `totalDistance` by the same rules
(`fieldsim.spot_facts`), and the anonymizer keeps those fields for the blind
judge; it has no pinch
hitters or season statistics, and the renderer says nothing about either when
they are absent.

`annotate_transcript_facts.py` records the explicit depth, lane, hardness and
ground-rule doubles from each ball's call, and starters' season records from
the pregame, in the 17 ledgers and straight into the four reference fixtures.
It keeps existing values and skips contradictory words. Pinch hitters were
annotated by hand. Review its output (`--dry-run` prints every fact with the
words it came from) against the source. It also records the throws and slides
below, a new pitcher's hand, role and season line from the words that bring him
in, the decisions from the postgame, and the pregame's states, weather and
crew chief.

### The pitcher's game line, throws and slides, pitchers entering the game

`python missed_words.py` put three more fact types among the unmatched words.
Each is narrated in every kind of game, as an optional sentence built before
its gate (see Optional sentences).

**The pitcher's game line** needs no new field: the renderer counts it from
the plays. "And that's the ninth strikeout of the evening for Butch Flores."
after a strikeout (in a simulated game from a pitcher's third, or his third in
a row), "Hiroki Nomo strikes out the side here in the bottom of the third."
and "And that's 13 in a row set down by Scooter McKeever." at the break (from
seven in a row, `RETIRED_IN_A_ROW_MINIMUM`), and "Zach Valentine pitches a
complete game shutout." or "... throws a no-hitter." after the final line when
the winners used one pitcher for every inning. The hosts never read a pitch
count or a departing starter's line ("six innings, two runs on five hits"), so
the renderer does not either. The decisions ("Ron Nancy gets the save for the
Bombers.") are a feed fact, `liveData.decisions`; the simulator writes them
(the win to the pitcher of record when his team went ahead for good, a starter
needing five innings; a save for protecting a lead of three or fewer for an
inning, or for the last three innings).

**Throws and slides** are recorded on the runner's movement only where the
hosts state them: "The throw to the plate is not in time.", "And he will slide
in safely under the tag.", "No play at second.", and on a steal "Throw to
second is not in time. Patterson steals second." The simulator records the
catcher's throw and the slide on every steal and caught stealing, which now
also name their runner (`details.runners`, as the anonymizer rebuilds them
from a real feed), and a `not_in_time` throw with a slide when its field model
has a runner take an extra base within `RUN_PARAMS['close_play']` seconds of
being thrown out (`fieldsim.advance_on_hit(..., close=...)`).

**A pitcher entering the game** is introduced once, by name, the way the hosts
do it: the inning's or the batter's introduction describes him ("...will step
in against Baraboo closer Buddy Malone", "...up against Ravens' right-handed
reliever Dom Fuller"), and when neither names him a sentence of his own does
("Ravens' closer Masaki Harrington takes the mound."). The old data-feed
banner ("Pitching Change for X: A replaces B.") is gone. His hand is said when
the feed has it and "closer" only for a recorded `pitcherRole`; anyone who
follows the starter is a reliever. A simulated game always brings him in by
name; a fixture can leave him unsaid, as the hosts did for 2 of 34.

### The pregame and the postgame

The pregame now follows the hosts' order: the station's line ("You're drifting
off with WSLP AM, Big Rapids.", from `broadcast.station_city`), "The
Northwoods Baseball Radio Network presents Sleep Baseball.", the opener
("Tonight, from Kittamori Park in Tomah, Wisconsin, it's..."), the host, the
weather ("74 degrees at game time, with a light breeze blowing in from center
field."), the two lineups, the Fishbowl, and the crew chief ("And crew chief
V.R. Montebianco hollers, play ball."). Every lineup slot has the hosts' two
forms ("{position} {player_name} will bat sixth." and "Batting sixth,
{position} {player_name}."). The postgame opens with the final score ("So the
Tigers take this one at home by a score of five to nothing."), then the
pitchers, the line score and the sign-off.

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
| `init` | The pregame up to the visitors' lineup. |
| `lineup_away`, `lineup_home` | Each team's lineup, found by "Let's take a look at the starting nine" and "Those are the..." / "Here are the...". |
| `first_pitch` | From the Fishbowl or the crew chief to the first appearance. When a broadcast's lineups cannot be found (five present the home team by position, not batting order) these four points all see the whole pregame. |
| `postgame` | Everything after the last appearance. It was fitted against the last play's call before. |
| `play_start` | From the line after the previous appearance to the line before the first pitch: the inning transition and the introduction. If the introduction shares the first pitch's line, only the words before `...`. |
| `event` | The pitch's line, through the line before the next event. |
| `play_outcome` | From the last pitch's line to the end of the appearance. |

A `choice(options)` call takes the option whose words best match the point's
window: weighted 1-, 2- and 3-gram matches minus 0.6 per unmatched n-gram.
Options are scored before formatting, so a template slot (`{count_str}`) is a
gap that no n-gram spans. It used to be dropped, which made "The {count_str}
pitch..." read as the bigram "the pitch", a miss in every window, and the
fitter preferred slot-free templates: "The one-oh..." for the hosts' "The
one-oh pitch...".

Where the renderer knows what a template will be filled with it draws through
`NarrativeRenderer._choose(rng, options, context)`, and the fitter scores each
option as it will be said (`fit_transcript_games.filled`): "Those are the
{away_short}." and "Those are the {away_team_name}." tie as templates, as do
"...it's {away_short} {score_away}, ..." and its full-name form, and the fitter
used to keep whichever the seeded draw gave ("Big Rapids Timbers nothing,
Tomah Tigers two" for the hosts' "Tigers two, Timbers nothing"). Production
rendering ignores the context. The lineups, the pregame's close and the
postgame are reseed points of their own (`gameData.commentaryRng.lineup_away`,
`lineup_home`, `first_pitch`, `postgame`), so each is fitted to its own lines.

A `random()` gate decides whether an optional sentence is said, or which form
it takes. Gates are fitted per point. The fitter first picks the best of six
whole-game constants, as before, then runs a coordinate descent. A coordinate
is the k-th gate of one stream at one kind of point, such as the first colour
gate at every `play_start` (the at-bat recap). Each coordinate is searched
jointly with the next gate of its stream at that point, which often picks the
form of the sentence the first one turns on: searched alone, the recap gate
never opened while its format draw pointed at "grounded out in the second", and
the format never mattered while the recap was closed, so "Diaz is oh for three
this evening" was out of reach. The renderer's draws are
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
threshold does not silently flip them. The joint search of gate pairs made
refitting slower: the 17 broadcasts and four references take about 16 minutes
in eight parallel processes (`fit_transcript_games.py 1 5 11 &` and so on).

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
| A return from the break ("And welcome back with us from Kittamori Park.", "Wally McCarthy and producer Phil back with you.") | 163 of 326, 50.0% |
| The strikeout tally ("And that's the ninth strikeout of the evening for Butch Flores."), after a pitcher's third or later strikeout or his third in a row | 13 of 164, 7.9% |
| "Hiroki Nomo strikes out the side here in the bottom of the third." | 5 of 7, 71.4% (0.34 in use: simulated pitchers strike out the side twice as often) |
| "And that's 13 in a row set down by Scooter McKeever.", at the break after a scoreless half with seven or more retired in a row | 2 of 28, 7.1% |
| "Zach Valentine pitches a complete game shutout." | 5 of 9, 55.6% |
| The decisions ("Ron Nancy gets the save for the Bombers.") | 11 of 19 finished broadcasts, 57.9% |
| The sentence that brings in a pitcher no introduction named (a simulated game always says it) | 32 of 34, 94.1% |
| A new pitcher's season ("Fuller has pitched 12 innings of work this season with an ERA of 2.67.") | 2 of 34, 5.9% |
| The throw on a steal ("The throw to second is not in time.") | 3 of 11, 27.3% |
| A recorded throw or slide on a ball in play | said whenever recorded (the simulator records about one in two games) |
| "The Northwoods Baseball Radio Network presents Sleep Baseball." | 18 of 21, 85.7% |
| "And now your host, Wally McCarthy." | 9 of 21, 42.9% |
| "It's Wally McCarthy and producer Phil, back with you from beautiful Kittamori Park..." | 10 of 21, 47.6% |
| "It is a perfect night for a ball game." | 21 of 21 (0.97 in use) |
| "And crew chief V.R. Montebianco hollers, play ball." | 19 of 21, 90.5% |
| "So the Tigers take this one at home by a score of five to nothing." | 15 of 19, 78.9% |

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

### The hosts' wording, by frequency

`python wording_mining.py` groups every source clause (asides excluded) by the
renderer situation it narrates (a pitch by code and location, a batted ball by
outcome, trajectory and fielder, the introduction, the half-inning transition,
pregame, postgame) and normalises it into a slot template, so "Shemper deals,
fastball low and away" and "Nomo deals, curveball low and away" group together.
For each template it reports how often the hosts said it in its situation and
how many words the rendering missed, across how many episodes.

`wording_additions.py` lists the templates added from that report: their pool,
the pattern that finds the hosts saying them, and the slot that counts their
chances. It writes `transcript_wording_additions.json` with each template's
count, rate, episodes and source lines, and the weight
`commentary.TEMPLATE_WEIGHTS` gives it so a simulated game draws it at the
hosts' rate: in a pool of `N` original templates, phrasings with rates `s_i`
get `w_i = s_i * N / (1 - sum(s))` (the sum capped at 0.8). Fixture draws
index pools directly and ignore weights. A phrasing from a single episode goes
in only as plain broadcast language. `python template_repetition.py --games 50`
counts every template's uses per simulated game; `--check` fails if an added
template recurs more than the hosts' `said / 17` per game allows.

Some fixes changed a value rather than a pool, each measured the same way:
"here on the Northwoods Baseball Radio Network" (the article in all 361
mentions), scores and lineup slots spoken ("Tigers two, Ravens nothing", "the
seven, eight, and nine hitters", "And batting ninth"), nicknames in the
score phrase ("Tigers leading two-to-one"), "after three and a half" after the
top of the fourth (the breaks had the half inning on the wrong side), and the
outs ("one away", "one out", "one down") and which out ("for out number one",
"for the first out of the inning") drawn from weighted pools.

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
   For a phrasing the hosts repeat, rank it with `python wording_mining.py`,
   add it to `WORDING_ADDITIONS` in `commentary.py` and its pattern and slot
   to `wording_additions.py`, then run `python wording_additions.py` and
   paste `--weights` into `TEMPLATE_WEIGHTS` so simulated games say it at the
   hosts' rate (`python template_repetition.py --check`).
4. Refit, inspect the resulting JSON/text diff, and run comparison and replay
   checks. Adjust reviewed wording minimums only after measuring the intended
   result; do not reduce factual coverage to make a check pass.

The latest source-mining pass appended 366 templates: 188 pitch/delivery
variants and 178 play/transition variants. The recorded-facts pass added 50
more play rows to `transcript_play_additions.json` (pinch hitters, season
records, runners who score or take third, RBI hits, home-run runs, ground-rule
doubles), and the next 75 (the pitcher's game line, throws and slides, new
pitchers, the lineup forms, the pregame and the postgame). The source catalogs can also retain
entries that were already available; their row counts are not necessarily the
number of newly inserted templates.

```bash
python -m unittest test_transcript_games test_transcript_comparison test_transcript_phrase_additions
python pbp_match_report.py --check
```

See [PBP_ALIGNMENT_GUIDE.md](../PBP_ALIGNMENT_GUIDE.md) for draw editing and the
historical example-3 alignment checklist.
