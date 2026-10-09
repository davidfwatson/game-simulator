# Full-transcript comparison baseline

All 17 broadcasts have structured fixtures, covering 1,106 observed appearance
segments, 3,727 delivered pitches, and 29 nonpitch actions. Episodes 001 and 051
end before the game is completed; their fixtures preserve those partial endings.

These are approximate wording comparisons, not verbatim broadcast recreation.
Line layout still differs from the rendering. Word overlap is the Jaccard
similarity of the two vocabularies. Ordered word coverage is the mean fraction
of source words matched in order within each appearance; 5-gram recall measures
shared five-word sequences over the entire broadcast. TTS markers are excluded
from both. Exact lines require identical normalized content, not just shared
vocabulary.

## The hosts' wording, by frequency

The census below found that 84% of the remaining unmatched source words were
wording: the fixture had the fact and the renderer said it differently. This
pass mined that wording, added it where it recurs, and fixed two fitter limits
that kept the hosts' phrasing out of reach even when a pool already held it.

**Mining.** `python wording_mining.py` assigns every source clause (asides
excluded) to the renderer situation it narrates, from the ledgers' line facts:
a pitch by code and location, a batted ball by outcome, trajectory and fielder,
the batter introduction, the half-inning transition, pregame and postgame. It
normalises each clause into a slot template ("{pitcher} deals, {pitch_type}
low and away") and counts the hosts' uses, episodes and missed words.

**Fitter.** Choices are scored before formatting, and a template slot used to
be dropped, so "The {count_str} pitch..." read as the bigram "the pitch",
which never matches, and the fitter preferred "The one-oh..." to the hosts'
"The one-oh pitch...". A slot is now a gap no n-gram spans. Second, each gate
is searched jointly with the next gate of its stream at the same point: the
at-bat recap's gate never opened while its format draw pointed at the wrong
form, so "Diaz is oh for three this evening" was unreachable.

**Templates.** 54 templates, every one said in at least two episodes, were
appended to the pools of their situation (`WORDING_ADDITIONS` in
`commentary.py`, measured in `transcript_wording_additions.json`):

| Situation | Added | Example |
|---|---:|---|
| Return from the break | 8 | "And welcome back with us from {venue} here in {location_with_state}." |
| Inning introduction | 7 | "{score_lead} as we begin the bottom of the {inning_ordinal}." ("The Tigers lead the Ravens two to one as we begin...") |
| Score at the break, incl. the seventh-inning stretch | 8 | "And as we head into the stretch, it remains {leading_short} {leading_score_val}, {trailing_short} {score_trail}." |
| Batter introduction | 7 | "And {batter_name} is due up against {pitcher_name}.", "...at the top of the {team_short_possessive} order." |
| How many out ("one out", "one down", "two outs", ...) | 5 | new pools whose first entry is the old fixed "one away" |
| Which out ("for the first out of the inning", "to end the ball game", ...) | 8 | new pools whose first entry is the old "for out number one" |
| Pitch calls | 4 | "And that's a {pitch_type_lower} in the dirt", "brushes him back" |
| Counts and fouls | 5 | ", full count", "And he fouls another one off" |
| Pregame and postgame | 2 | "You're drifting off with {station_call} AM." |

Each is weighted by its measured rate (`commentary.TEMPLATE_WEIGHTS`): in a
pool of `N` original templates, phrasings the hosts use at rates `s_i` get
`w_i = s_i * N / (1 - sum(s))`, so a simulated game draws each at the hosts'
rate. Weights run from 0.008 ("and it's two and one", 19 of 4,566 counts) to
48 for phrasings at the 0.8 share cap ("And as we head into the stretch", 13 of
15 stretches; "You're drifting off with WSLP AM", every episode). Fixture draws
index pools directly, so the fitter sees every template.

**Values.** Several sentences were right except for a value the hosts never
use: "the Northwoods Baseball Radio Network" (the article in 361 of 361
mentions), spoken scores and lineup spots ("Tigers two, Ravens nothing", "the
seven, eight, and nine hitters", "And batting ninth", not "Tigers 2", "the 7,
8, and 9 hitters", "Batting 9"), nicknames in the score phrase (the hosts say a
team's full name 136 times and its nickname 977 times in the 17 broadcasts),
and the half inning, which was on the wrong side of every break ("after one
and a half" after the bottom of the first). "In the books" is said only at
full-inning breaks, so it is no longer offered mid-inning. 59 ledger balls the
hosts called "high and tight" or "low and in" were recorded as just high or
low; they are now `high_inside` and `low_inside`, and the annotator reads
"tight" as inside.

**The return line.** The hosts return from a break ("And welcome back with us
from Kittamori Park", "Wally McCarthy and producer Phil back with you") at 163
of 326 breaks, 50.0% (`optional_sentence_rates.py`, 141 of 268 in the ledgers,
22 of 58 in the references). The renderer said it at 15% of breaks in innings
three to eight, before the break's delay marker. It is now the optional
sentence `break_return`, said at 50% of every break after the delay, as its
own sentence or opening the introduction, drawn by form frequency.

**Repetition in simulated games.** `python template_repetition.py` renders 50
simulated games and counts each template that reaches the page; `--check`
fails if an added template averages more uses per game than the hosts' rate
allows (`1.25 * said/17` plus sampling noise), and the test suite runs it on 30
games. Before and after (`--compare`, 50 games, base `origin/main`):

| | Before | After |
|---|---:|---:|
| Uses of the most-repeated template in a game (mean) | 14.6 | 14.1 |
| "A high {pitch}, called {strike_call}" per game | 9.1 | 2.1 |
| "And that high {pitch} is called {strike_call}" per game | 9.4 | 1.4 |
| Top template ("And the {count_str}...") per game | 11.1 | 11.1 |
| Added template with the most uses ("{score_lead} as we begin the bottom of the {inning_ordinal}.") | | 3.9 (hosts 2.8, limit 4.3) |

The two "high ... called" calls were a tell already: a tracked zone 1-3 gave
them a pool of two. A zone-inferred called strike now also offers the plain
calls that claim no spot. The foul-after-foul phrase stays behind a gate, now
0.15: the hosts say one at 46 of 61 fouls after a foul, 2.7 a game, but a
simulated game throws 19 fouls after a foul to their 3.6 (the simulator's foul
rate is a separate problem), so it splits "he fouls another one off", which
was 5.7 a game, into three phrasings near the hosts' count. How many out and
which out are clause values every appearance states; they were one fixed
phrase each and are left out of the count.

All 21 fixtures were refitted (the 78 focused cases recompiled and pass; the
component inventory supports 4,759 of 6,035 clauses, up from 4,701):

| Episode | Word overlap | 5-gram recall | Ordered words per appearance | Exact content lines |
|---|---:|---:|---:|---:|
| [001](../examples/transcript_games/episode_001.txt) | 50.1% → 51.8% | 16.4% → 19.6% | 52.9% → 55.6% | 0.5% → 0.9% |
| [005](../examples/transcript_games/episode_005.txt) | 64.7% → 66.9% | 28.6% → 36.1% | 70.4% → 76.8% | 10.6% → 18.0% |
| [011](../examples/transcript_games/episode_011.txt) | 59.0% → 61.4% | 24.5% → 36.0% | 70.3% → 77.8% | 6.0% → 18.2% |
| [013](../examples/transcript_games/episode_013.txt) | 61.2% → 64.1% | 26.1% → 39.2% | 71.0% → 79.8% | 6.1% → 22.2% |
| [020](../examples/transcript_games/episode_020.txt) | 68.7% → 70.8% | 29.8% → 45.1% | 75.0% → 83.4% | 8.8% → 25.8% |
| [029](../examples/transcript_games/episode_029.txt) | 61.3% → 64.0% | 30.9% → 42.0% | 70.6% → 77.5% | 11.1% → 27.5% |
| [035](../examples/transcript_games/episode_035.txt) | 67.7% → 68.9% | 33.9% → 47.8% | 72.8% → 79.4% | 6.9% → 28.3% |
| [037](../examples/transcript_games/episode_037.txt) | 73.1% → 74.7% | 36.5% → 52.9% | 78.4% → 86.9% | 12.2% → 33.7% |
| [039](../examples/transcript_games/episode_039.txt) | 72.5% → 74.1% | 39.2% → 50.5% | 78.7% → 86.4% | 12.3% → 17.2% |
| [041](../examples/transcript_games/episode_041.txt) | 69.9% → 71.2% | 39.8% → 55.4% | 78.0% → 87.0% | 11.1% → 29.4% |
| [045](../examples/transcript_games/episode_045.txt) | 70.3% → 72.0% | 36.5% → 47.9% | 73.5% → 80.6% | 10.5% → 15.8% |
| [046](../examples/transcript_games/episode_046.txt) | 69.5% → 70.8% | 41.1% → 52.8% | 78.9% → 86.0% | 11.7% → 18.7% |
| [049](../examples/transcript_games/episode_049.txt) | 70.0% → 72.2% | 43.4% → 54.5% | 82.4% → 89.1% | 14.6% → 20.1% |
| [050](../examples/transcript_games/episode_050.txt) | 71.1% → 72.6% | 38.5% → 49.4% | 74.9% → 83.1% | 13.2% → 23.3% |
| [051](../examples/transcript_games/episode_051.txt) | 62.9% → 63.5% | 35.0% → 43.3% | 75.9% → 80.3% | 19.7% → 25.7% |
| [052](../examples/transcript_games/episode_052.txt) | 67.7% → 69.7% | 37.3% → 48.2% | 74.6% → 82.7% | 16.6% → 27.4% |
| [053](../examples/transcript_games/episode_053.txt) | 70.2% → 71.8% | 40.2% → 49.1% | 77.4% → 84.2% | 19.8% → 26.7% |
| **Mean** | 66.5% → 68.3% | 34.0% → 45.3% | 73.9% → 81.0% | 11.3% → 22.3% |

How the gain divides (17-broadcast means, each row adding to the one above;
the first two rows were measured with the old pools):

| Change | Word overlap | 5-gram recall | Ordered words | Exact content lines |
|---|---:|---:|---:|---:|
| Before | 66.5% | 34.0% | 73.9% | 11.3% |
| Slots are gaps in option scoring | 67.1% | 40.0% | 77.5% | 20.5% |
| Gates searched in pairs | 67.2% | 40.7% | 78.8% | 20.5% |
| Templates, values, return rate, ledger locations | 68.3% | 45.3% | 81.0% | 22.3% |

| Reference | Word Jaccard | 5-gram | Exact lines (all) | Exact lines (content) |
|---|---:|---:|---:|---:|
| `pbp_example_1.txt` | 69.3% → 70.4% | 35.6% → 41.5% | 55.0% → 60.0% | 23.0% → 32.5% |
| `pbp_example_2.txt` | 68.4% → 70.9% | 41.6% → 49.1% | 60.1% → 63.5% | 25.5% → 31.8% |
| `pbp_example_3.txt` | 71.0% → 71.7% | 36.8% → 43.4% | 48.7% → 49.5% | 8.9% → 10.4% |
| `pbp_example_4.txt` | 65.8% → 68.3% | 33.8% → 41.0% | 57.0% → 61.5% | 17.2% → 25.9% |

Missed source words fell from 41,199 to 31,798 (32.4% to 25.0%):

| Cause | Before | After |
|---|---:|---:|
| Wording | 34,654 | 25,643 |
| Missing fact | 3,455 | 3,318 |
| Recorded but never said | 2,188 | 2,031 |
| Other | 902 | 806 |

Wording is still 80.6% of what is missed. Its largest types are now pregame
and postgame (5,301), the inning transition (4,512) and score talk (3,691).
Rendered words the source lacks rose from 19,125 to 21,127, mostly longer score
and break sentences. The minimums more than four points below the new
measurements were raised to three points below them, rounded down: the 5-gram
and ordered-word minimums of all 17 episodes and every reference minimum but
`pbp_example_3`'s Jaccard. None was lowered.

Not done here: the remaining fact types (the pitcher's game line, throws and
slides, reliever roles), where a swinging strike was located (ledgers record
no location for swinging strikes, so "swing and a miss on a low curve" is
unreachable), and the simulator's foul rate.

## Facts the hosts state that the fixtures could not hold

Many remaining wording gaps were missing facts: the hosts said something a
fixture had no field for, so no draw could produce it. `python
missed_words.py` measures this. For every unit of the 21 sources (the pregame,
each appearance with the transition before it, the postgame) it aligns the
source words, asides excluded, with the rendering, and sorts each clause that
holds unmatched words into a cause by pattern: a **missing fact** the fixture
cannot express, a recorded fact the renderer **never says**, a **wording**
difference about a fact it does narrate, or **other**. It is a heuristic;
in a review of 60 randomly drawn clauses the cause was right for 57, and the
three misses were wording clauses of one kind filed under another.

Before this pass, 42,537 of the 127,019 source words (33.5%) went unmatched:

| Cause | Missed words | Share |
|---|---:|---:|
| Wording (the fact is narrated in other words) | 34,666 | 81.5% |
| Missing fact | 4,340 | 10.2% |
| Recorded but never said | 2,625 | 6.2% |
| Other (unmarked colour, transcription noise) | 906 | 2.1% |

The game facts by missed words, before and after (same classifier; a type now
recorded keeps its label, so its remainder is wording or an unannotated call):

| Fact type | Example | Before | After |
|---|---|---:|---:|
| Where the ball went (now `hitData.depth`, `lane`) | "into the gap in left center", "on the warning track" | 2,189 | 1,875 |
| Season statistics (now boxscore `seasonStats`) | "enters tonight's contest with a record of 7 and 8 with a 5.21 ERA" | 724 | 318 |
| Runs a hit or homer drove in (now said) | "And that's an RBI single for Ali Nunez", "a two-run homer" | 636 | 404 |
| Pitcher's game line (not yet) | "that's the twelfth strikeout of the night for Nomo" | 566 | 566 |
| Throws and slides (not yet) | "the throw to the plate is not in time" | 505 | 509 |
| Runners who score (now said) | "Nomo will score. Brown will score." | 489 | 368 |
| Reliever role (not yet) | "against Ravens' right-handed reliever Dom Fuller" | 434 | 438 |
| Contact quality (now `hitData.hardness`) | "Hard grounder to short", "a little looper" | 426 | 425 |
| Pinch hitters (now an Offensive Substitution) | "steps in to pinch-hit for Brocktune Shemper in the nine spot" | 412 | 244 |
| Runners who take third (now said) | "Ferguson will advance to third" | 405 | 317 |
| Lineup slot (not yet) | "that will bring up Virgil Hughes in the pitcher's spot" | 95 | 95 |
| Fielder on a hit (not yet) | "that one gets past a diving Nunez" | 84 | 85 |

Missed words fell from 42,537 to 41,207: missing facts from 4,340 to 3,456 and
unsaid recorded facts from 2,625 to 2,188, while wording stayed at 34,661 and
rendered words the source lacks rose only from 19,101 to 19,125. Hardness
barely moved because the clauses that say it ("Hard grounder to short") were
already partly matched by templates that claimed it without a fact; those
claims now need the fact, so the gain shows up as fidelity rather than recall.

What was recorded, and where (see [the ledger guide](README.md#where-the-ball-went-and-other-facts-the-hosts-state)):

* `hitData.hardness` (StatsAPI), `hitData.depth` and `hitData.lane`
  (extensions a real feed implies by distance and coordinates) on 361 ledger
  balls and 81 reference balls, plus two ground-rule doubles, by
  `annotate_transcript_facts.py` from each ball's call. The simulator writes
  all three from its field model and exit velocity.
* Boxscore `seasonStats.pitching` for 26 ledger starters and 7 in the
  references, said after the starter's lineup slot.
* 26 ledger pinch hitters and 4 in the references, as the at-bat's
  `offensive_substitution` action with `replacedPlayer` when the hosts name
  him; the introduction says it, with the lineup slot when recorded.
* Already recorded and now said: runners a ball in play brings home or to
  third (optional, the hosts say 80.5%), the RBI form of the hit situation
  sentence, and a home run's runs (optional, 78.8%).

Templates asserting a wall, warning track, gap, line, corner, depth, hardness
or a grounder's path are now offered only when the ball's facts support them,
so a strict fixture never claims an unrecorded wall or hard contact. A
"Strikeout Looking" or "Called Strikeout" result no longer leaves its third
strike on a dangling comma (`pbp_example_1`, `pbp_example_3`).

All 21 fixtures were refitted:

| Episode | Word overlap | 5-gram recall | Ordered words per appearance | Exact content lines |
|---|---:|---:|---:|---:|
| [001](../examples/transcript_games/episode_001.txt) | 48.7% → 50.1% | 15.9% → 16.4% | 51.8% → 52.9% | 0.5% → 0.5% |
| [005](../examples/transcript_games/episode_005.txt) | 62.6% → 64.7% | 27.9% → 28.6% | 69.7% → 70.4% | 10.6% → 10.6% |
| [011](../examples/transcript_games/episode_011.txt) | 58.4% → 59.0% | 24.1% → 24.5% | 70.3% → 70.3% | 6.0% → 6.0% |
| [013](../examples/transcript_games/episode_013.txt) | 57.9% → 61.2% | 25.4% → 26.1% | 70.4% → 71.0% | 6.1% → 6.1% |
| [020](../examples/transcript_games/episode_020.txt) | 67.3% → 68.7% | 28.3% → 29.8% | 73.9% → 75.0% | 8.3% → 8.8% |
| [029](../examples/transcript_games/episode_029.txt) | 59.7% → 61.3% | 30.4% → 30.9% | 69.9% → 70.6% | 11.1% → 11.1% |
| [035](../examples/transcript_games/episode_035.txt) | 63.7% → 67.3% | 31.5% → 33.7% | 71.3% → 72.6% | 6.1% → 6.6% |
| [037](../examples/transcript_games/episode_037.txt) | 70.1% → 73.1% | 35.0% → 36.5% | 77.6% → 78.4% | 11.9% → 12.2% |
| [039](../examples/transcript_games/episode_039.txt) | 69.1% → 72.5% | 37.7% → 39.2% | 78.3% → 78.7% | 12.1% → 12.3% |
| [041](../examples/transcript_games/episode_041.txt) | 68.1% → 69.9% | 38.8% → 39.8% | 77.2% → 78.0% | 10.8% → 11.1% |
| [045](../examples/transcript_games/episode_045.txt) | 68.0% → 70.3% | 35.4% → 36.5% | 72.9% → 73.5% | 10.3% → 10.5% |
| [046](../examples/transcript_games/episode_046.txt) | 67.3% → 69.5% | 39.2% → 41.1% | 77.6% → 78.9% | 11.1% → 11.7% |
| [049](../examples/transcript_games/episode_049.txt) | 66.2% → 70.0% | 40.1% → 43.4% | 80.5% → 82.4% | 14.4% → 14.6% |
| [050](../examples/transcript_games/episode_050.txt) | 66.8% → 71.1% | 36.0% → 38.5% | 74.0% → 74.9% | 12.9% → 13.2% |
| [051](../examples/transcript_games/episode_051.txt) | 60.6% → 62.9% | 33.7% → 35.0% | 75.1% → 75.9% | 19.7% → 19.7% |
| [052](../examples/transcript_games/episode_052.txt) | 65.0% → 67.7% | 35.3% → 37.3% | 73.6% → 74.6% | 16.6% → 16.6% |
| [053](../examples/transcript_games/episode_053.txt) | 68.1% → 70.2% | 39.0% → 40.2% | 76.8% → 77.4% | 19.5% → 19.8% |
| **Mean** | 64.0% → 66.5% | 32.6% → 34.0% | 73.0% → 73.9% | 11.1% → 11.3% |

| Reference | Word Jaccard | 5-gram | Exact lines (all) | Exact lines (content) |
|---|---:|---:|---:|---:|
| `pbp_example_1.txt` | 68.3% → 69.3% | 35.1% → 35.6% | 55.0% → 55.0% | 23.0% → 23.0% |
| `pbp_example_2.txt` | 65.9% → 68.4% | 40.1% → 41.6% | 59.9% → 60.1% | 25.1% → 25.5% |
| `pbp_example_3.txt` | 69.7% → 71.0% | 36.3% → 36.8% | 48.7% → 48.7% | 8.9% → 8.9% |
| `pbp_example_4.txt` | 65.1% → 65.8% | 32.2% → 33.8% | 57.0% → 57.0% | 17.2% → 17.2% |

Minimums more than four points below the new measurements were raised to three
points below them, rounded down: 5-gram minimums of 15 episodes and
ordered-word minimums of 13, and the references' Jaccard (1, 2, 3), 5-gram (2,
4) and all-line (2) minimums. No minimum was lowered. The test for measured
optional-sentence rates now accepts 30 opportunities for the home-run sentence
(the 21 sources hold only 33 home runs with runs batted in); every other rate
still needs 80.

The largest remaining fact types are the pitcher's game line, throws and
slides, and the reliever role; the much larger wording share is lever 4.

## Gates fitted per point, and optional sentences

The fitter used to try six whole-game constants for every `random()` gate, so
an optional sentence (an at-bat recap, a score-and-inning line, a runner
reminder) was said at every opportunity in a game or at none. Now each gate is
fitted per reseed point against that point's own source window, and four
sentences the hosts often leave out became optional, each behind one draw on
a new `optional` stream. [The ledger guide](README.md#how-draws-are-fitted)
describes the method and the measured rates. Rendered facts did not change;
only which sentences are said, and the wording choices that follow them.

| Episode | Word overlap | 5-gram recall | Ordered words per appearance | Exact content lines |
|---|---:|---:|---:|---:|
| [001](../examples/transcript_games/episode_001.txt) | 46.5% → 48.7% | 14.6% → 15.9% | 49.7% → 51.8% | 0.5% → 0.5% |
| [005](../examples/transcript_games/episode_005.txt) | 59.3% → 62.6% | 24.7% → 27.9% | 66.6% → 69.7% | 5.4% → 10.6% |
| [011](../examples/transcript_games/episode_011.txt) | 55.9% → 58.4% | 22.1% → 24.1% | 69.9% → 70.3% | 4.7% → 6.0% |
| [013](../examples/transcript_games/episode_013.txt) | 57.5% → 57.9% | 23.5% → 25.4% | 69.8% → 70.4% | 5.3% → 6.1% |
| [020](../examples/transcript_games/episode_020.txt) | 65.1% → 67.3% | 26.2% → 28.3% | 72.2% → 73.9% | 8.0% → 8.3% |
| [029](../examples/transcript_games/episode_029.txt) | 58.4% → 59.7% | 27.0% → 30.4% | 68.4% → 69.9% | 10.6% → 11.1% |
| [035](../examples/transcript_games/episode_035.txt) | 61.8% → 63.7% | 27.6% → 31.5% | 69.4% → 71.3% | 3.7% → 6.1% |
| [037](../examples/transcript_games/episode_037.txt) | 64.8% → 70.1% | 30.3% → 35.0% | 75.7% → 77.6% | 9.3% → 11.9% |
| [039](../examples/transcript_games/episode_039.txt) | 64.2% → 69.1% | 31.6% → 37.7% | 74.3% → 78.3% | 11.7% → 12.1% |
| [041](../examples/transcript_games/episode_041.txt) | 65.1% → 68.1% | 33.0% → 38.8% | 74.0% → 77.2% | 9.5% → 10.8% |
| [045](../examples/transcript_games/episode_045.txt) | 65.1% → 68.0% | 29.8% → 35.4% | 69.7% → 72.9% | 8.4% → 10.3% |
| [046](../examples/transcript_games/episode_046.txt) | 65.8% → 67.3% | 35.7% → 39.2% | 74.3% → 77.6% | 10.0% → 11.1% |
| [049](../examples/transcript_games/episode_049.txt) | 64.4% → 66.2% | 33.8% → 40.1% | 76.3% → 80.5% | 12.1% → 14.4% |
| [050](../examples/transcript_games/episode_050.txt) | 65.5% → 66.8% | 32.6% → 36.0% | 71.1% → 74.0% | 11.7% → 12.9% |
| [051](../examples/transcript_games/episode_051.txt) | 59.6% → 60.6% | 29.5% → 33.7% | 69.9% → 75.1% | 16.4% → 19.7% |
| [052](../examples/transcript_games/episode_052.txt) | 61.1% → 65.0% | 29.8% → 35.3% | 70.1% → 73.6% | 13.1% → 16.6% |
| [053](../examples/transcript_games/episode_053.txt) | 65.1% → 68.1% | 32.9% → 39.0% | 72.5% → 76.8% | 16.9% → 19.5% |
| **Mean** | 61.5% → 64.0% | 28.5% → 32.6% | 70.2% → 73.0% | 9.3% → 11.1% |

How the gain divides (17-broadcast means, each row adding to the one above):

| Change | Word overlap | 5-gram recall | Ordered words | Exact content lines |
|---|---:|---:|---:|---:|
| Before (whole-game gate constants) | 61.5% | 28.5% | 70.2% | 9.3% |
| Fitter reads sources with asides removed | 61.3% | 28.5% | 70.3% | 9.3% |
| Gates fitted per point (segment penalty 0.6) | 62.6% | 30.8% | 72.1% | 10.6% |
| Four optional sentences on their own stream | 62.5% | 31.1% | 71.9% | 11.0% |
| Segment penalty 0.3 instead of 0.6 | 63.0% | 31.4% | 72.8% | 11.0% |
| Introduction choices scored against the tight `play_start` window | 64.0% | 32.6% | 73.0% | 11.1% |

The segment penalty was swept from 0.15 to 0.8. Lower values keep more
partly matched sentences, which raises the recall measures (5-grams, ordered
words) and lengthens the rendering. Exact content lines held at 11.0% from 0.3
upward and fell only at 0.15. With the final settings the per-appearance
renderings total 78,793 words against 80,468 source words (asides excluded),
so the renderer still says somewhat less than the hosts.

The four references were refitted the same way, from an alignment of their
hand-tuned rendering with the source. They improve on every measure:

| Reference | Word Jaccard | 5-gram | Exact lines (all) | Exact lines (content) |
|---|---:|---:|---:|---:|
| `pbp_example_1.txt` | 64.8% → 68.3% | 31.8% → 35.1% | 54.0% → 55.0% | 21.2% → 23.0% |
| `pbp_example_2.txt` | 60.5% → 65.9% | 34.4% → 40.1% | 59.5% → 59.9% | 24.3% → 25.1% |
| `pbp_example_3.txt` | 59.2% → 69.7% | 27.1% → 36.3% | 48.3% → 48.7% | 8.1% → 8.9% |
| `pbp_example_4.txt` | 61.3% → 65.1% | 28.4% → 32.2% | 56.4% → 57.0% | 15.8% → 17.2% |

As a cross-check, the 21 fitted fixtures keep 38 of 121 counts after a
numbered call (31%; hosts 10%), 34 of 61 one- and two-out strikeout out numbers
(56%; hosts 70%), 17 of 21 inning-ending strikeout suffixes (81%; hosts 85%)
and 114 of 189 hit situation sentences (60%; hosts 64%). Fitted counts are
kept more often than the hosts say them, probably because count words such as
"two and oh" also occur elsewhere in a pitch's source line. Simulated games
use the measured rates, not the fitted shares.

Minimums more than four points below the new measurements were raised to three
points below them, rounded down: the full-broadcast 5-gram and ordered-word
minimums of all 17 episodes, and the references' Jaccard, 5-gram and
content-line minimums. No minimum was lowered. The 78 focused cases were
recompiled for the new stream and all pass; the component inventory is
unchanged (4,701 of 6,035 clauses).

## Host asides count for nothing

Between-innings breaks (promos and in-character spots) were cut when the
transcripts were cleaned, so they never entered any metric. Host asides are the
in-call equivalent: stories (the goat in center field, the skydiving mascot),
on-field incidents outside the play record (scuffles, a pitcher signed by the
other team mid-game), mound-visit chatter, player trivia, banter with producer
Phil and listener greetings, in-call sponsor reads, and crowd colour. No
Gameday-driven engine can say them, so they are now excluded in the same way.
Each is marked as an exact substring or whole line in
[`transcript_asides/`](../transcript_asides), the source text stays unchanged,
and every metric reads the source with those spans replaced by a hard break (see
[the ledger guide](README.md#host-asides)). Pitch calls, counts, outcomes,
runners, batter intros, at-bat history, season stats, lineup and pitching
changes, bare mound visits, weather, the fishbowl drawing and break sign-offs
are not asides.

The table gives each episode's measurements before and after the exclusion.
Rendered text and fixtures did not change; only the source side of the
comparison did. The aside column counts annotation entries and words.

| Episode | Appearances | Pitches | Asides (entries / words) | Word overlap | 5-gram recall | Ordered words per appearance | Exact content lines |
|---|---:|---:|---:|---:|---:|---:|---:|
| [001](../examples/transcript_games/episode_001.txt) | 73 | 254 | 26 / 485 | 41.5% → 46.5% | 13.4% → 14.6% | 48.1% → 49.7% | 0.5% → 0.5% |
| [005](../examples/transcript_games/episode_005.txt) | 73 | 270 | 6 / 212 | 52.0% → 59.3% | 23.4% → 24.7% | 66.5% → 66.6% | 5.1% → 5.4% |
| [011](../examples/transcript_games/episode_011.txt) | 50 | 198 | 28 / 554 | 43.7% → 55.9% | 18.6% → 22.1% | 65.3% → 69.9% | 3.5% → 4.7% |
| [013](../examples/transcript_games/episode_013.txt) | 70 | 295 | 10 / 285 | 48.7% → 57.5% | 21.9% → 23.5% | 69.5% → 69.8% | 5.2% → 5.3% |
| [020](../examples/transcript_games/episode_020.txt) | 67 | 223 | 4 / 227 | 55.6% → 65.1% | 24.5% → 26.2% | 71.9% → 72.2% | 7.8% → 8.0% |
| [029](../examples/transcript_games/episode_029.txt) | 68 | 217 | 18 / 327 | 49.9% → 58.4% | 24.7% → 27.0% | 68.0% → 68.4% | 10.2% → 10.6% |
| [035](../examples/transcript_games/episode_035.txt) | 63 | 207 | 6 / 160 | 56.4% → 61.8% | 26.4% → 27.6% | 69.0% → 69.4% | 3.9% → 3.7% |
| [037](../examples/transcript_games/episode_037.txt) | 64 | 220 | 6 / 292 | 56.3% → 64.8% | 28.0% → 30.3% | 75.7% → 75.7% | 8.8% → 9.3% |
| [039](../examples/transcript_games/episode_039.txt) | 68 | 224 | 3 / 150 | 59.0% → 64.2% | 30.5% → 31.6% | 74.3% → 74.3% | 11.3% → 11.7% |
| [041](../examples/transcript_games/episode_041.txt) | 62 | 199 | 4 / 236 | 58.3% → 65.1% | 31.0% → 33.0% | 73.2% → 74.0% | 9.2% → 9.5% |
| [045](../examples/transcript_games/episode_045.txt) | 72 | 237 | 9 / 253 | 56.5% → 65.1% | 28.2% → 29.8% | 69.2% → 69.7% | 8.2% → 8.4% |
| [046](../examples/transcript_games/episode_046.txt) | 76 | 254 | 6 / 127 | 62.1% → 65.8% | 34.7% → 35.7% | 74.3% → 74.3% | 9.8% → 10.0% |
| [049](../examples/transcript_games/episode_049.txt) | 63 | 214 | 5 / 133 | 59.6% → 64.4% | 32.6% → 33.8% | 76.3% → 76.3% | 11.8% → 12.1% |
| [050](../examples/transcript_games/episode_050.txt) | 66 | 170 | 5 / 129 | 60.8% → 65.5% | 31.4% → 32.6% | 71.1% → 71.1% | 11.4% → 11.7% |
| [051](../examples/transcript_games/episode_051.txt) | 47 | 152 | 12 / 403 | 51.2% → 59.6% | 26.1% → 29.5% | 69.5% → 69.9% | 14.9% → 16.4% |
| [052](../examples/transcript_games/episode_052.txt) | 62 | 200 | 8 / 213 | 54.2% → 61.1% | 28.2% → 29.8% | 70.1% → 70.1% | 12.6% → 13.1% |
| [053](../examples/transcript_games/episode_053.txt) | 62 | 193 | 9 / 205 | 58.8% → 65.1% | 31.2% → 32.9% | 72.2% → 72.5% | 16.4% → 16.9% |
| **Mean** | | | 165 / 4391 | 54.4% → 61.5% | 26.8% → 28.5% | 69.7% → 70.2% | 8.9% → 9.3% |

A removed aside is a hard boundary: no 5-gram, ordered-match run, exact line or
extracted clause may join the words on either side, because they were never
adjacent in the broadcast. A line split by an aside counts as separate pieces
for exact lines, which is why `pbp_example_4.txt` loses one content match that
only existed when an aside's neighbours were glued together.

Word overlap rises most because aside vocabulary is almost entirely unique to
the source. The other three metrics move less: many asides fall outside the
appearance ranges (pregame, inning breaks), and exact lines need the remaining
line to match. Exact lines can also shift slightly in either direction, as in
episode 035, because removing lines moves proportional line positions.

The four original references improve in the same way, measured after their
reviewed pregame offsets:

| Reference | Asides (entries / words) | Word Jaccard | 5-gram | Exact lines (all) | Exact lines (content) |
|---|---:|---:|---:|---:|---:|
| `pbp_example_1.txt` | 4 / 164 | 59.7% → 64.8% | 30.8% → 31.8% | 54.0% → 54.0% | 21.2% → 21.2% |
| `pbp_example_2.txt` | 7 / 227 | 57.7% → 60.5% | 33.2% → 34.4% | 59.5% → 59.5% | 24.3% → 24.3% |
| `pbp_example_3.txt` | 8 / 172 | 55.6% → 59.2% | 26.4% → 27.1% | 48.2% → 48.3% | 8.1% → 8.1% |
| `pbp_example_4.txt` | 9 / 190 | 56.9% → 61.3% | 27.5% → 28.4% | 56.7% → 56.4% | 16.0% → 15.8% |

Across all 21 sources, 193 entries cover 5,144 words: story 38 entries / 1,690
words, banter 65 / 1,098, incident 27 / 1,022, trivia 41 / 755, promo 11 / 346,
crowd 9 / 176, and mound_visit 2 / 57. The automatic component report now scans
6,035 clauses instead of 6,038 and still supports 4,701. The three clauses that
left were extractor false positives inside episode 001 asides.

After the exclusion, any wording minimum more than four points below its new
measurement was raised to three points below it, rounded down. This covers the
full-broadcast 5-gram and ordered-word minimums and the four references'
Jaccard, 5-gram, and line minimums. No wording minimum was lowered. The only
lowered floor is episode 001's component inventory floor (360 to 355), and only
because those three false positives are no longer eligible.

All reviewed minimums pass, and the 78 focused source-phrase cases also pass.
The earlier mining pass added 366 distinct reusable templates (188
pitch/delivery and 178 play/transition phrases).

Run `python full_transcript_comparison.py --check` for current measurements, or
`python full_transcript_comparison.py 1 --gaps 5` to inspect individual gaps.
`python pbp_match_report.py --check` checks those comparison catalogs and the
automatic pitch/foul/count component inventory across all 21 sources.
`python transcript_asides.py` lists the marked asides per source and category.
See [the ledger guide](README.md) for authoring, fitting, and replay instructions.
