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
