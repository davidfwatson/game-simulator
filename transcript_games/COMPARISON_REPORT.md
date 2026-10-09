# Full-transcript comparison baseline

All 17 broadcasts have structured fixtures, covering 1,106 observed appearance
segments, 3,727 delivered pitches, and 29 nonpitch actions. Episodes 001 and 051
end before the game is completed; their fixtures preserve those partial endings.

These are approximate wording comparisons, not verbatim broadcast recreation.
Source banter, anecdotes, and line layout differ from the rendering. Ordered word
coverage is the mean fraction of source words matched in order within each
appearance; 5-gram recall measures shared five-word sequences over the entire
broadcast. TTS markers are excluded from both. Exact lines require identical
normalized content, not just shared vocabulary.

| Episode | Appearances | Pitches | 5-gram recall | Ordered words per appearance | Exact content lines |
|---|---:|---:|---:|---:|---:|
| [001](../examples/transcript_games/episode_001.txt) | 73 | 254 | 13.4% | 48.1% | 0.5% |
| [005](../examples/transcript_games/episode_005.txt) | 73 | 270 | 23.4% | 66.5% | 5.1% |
| [011](../examples/transcript_games/episode_011.txt) | 50 | 198 | 18.6% | 65.3% | 3.5% |
| [013](../examples/transcript_games/episode_013.txt) | 70 | 295 | 21.9% | 69.5% | 5.2% |
| [020](../examples/transcript_games/episode_020.txt) | 67 | 223 | 24.5% | 71.9% | 7.8% |
| [029](../examples/transcript_games/episode_029.txt) | 68 | 217 | 24.7% | 68.0% | 10.2% |
| [035](../examples/transcript_games/episode_035.txt) | 63 | 207 | 26.4% | 69.0% | 3.9% |
| [037](../examples/transcript_games/episode_037.txt) | 64 | 220 | 28.0% | 75.7% | 8.8% |
| [039](../examples/transcript_games/episode_039.txt) | 68 | 224 | 30.5% | 74.3% | 11.3% |
| [041](../examples/transcript_games/episode_041.txt) | 62 | 199 | 31.0% | 73.2% | 9.2% |
| [045](../examples/transcript_games/episode_045.txt) | 72 | 237 | 28.2% | 69.2% | 8.2% |
| [046](../examples/transcript_games/episode_046.txt) | 76 | 254 | 34.7% | 74.3% | 9.8% |
| [049](../examples/transcript_games/episode_049.txt) | 63 | 214 | 32.6% | 76.3% | 11.8% |
| [050](../examples/transcript_games/episode_050.txt) | 66 | 170 | 31.4% | 71.1% | 11.4% |
| [051](../examples/transcript_games/episode_051.txt) | 47 | 152 | 26.1% | 69.5% | 14.9% |
| [052](../examples/transcript_games/episode_052.txt) | 62 | 200 | 28.2% | 70.1% | 12.6% |
| [053](../examples/transcript_games/episode_053.txt) | 62 | 193 | 31.2% | 72.2% | 16.4% |

All reviewed minimums pass. The original four full-game minimums were retained,
and the 78 focused source-phrase cases also pass. The new mining pass added 366
distinct reusable templates (188 pitch/delivery and 178 play/transition phrases).

Run `python full_transcript_comparison.py --check` for current measurements, or
`python full_transcript_comparison.py 1 --gaps 5` to inspect individual gaps.
`python pbp_match_report.py --check` checks those comparison catalogs and the
automatic pitch/foul/count component inventory across all 21 sources.

The tables above reflect the refitted commentary draws after the corpus phrase
expansion. The automatic report supports 4,701 of 6,038 extracted clauses; that
component capability has a different scope from the full-broadcast metrics.
See [the ledger guide](README.md) for authoring, fitting, and replay instructions.
