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
| [001](../examples/transcript_games/episode_001.txt) | 73 | 254 | 10.5% | 45.4% | 0.5% |
| [005](../examples/transcript_games/episode_005.txt) | 73 | 270 | 16.1% | 59.7% | 1.0% |
| [011](../examples/transcript_games/episode_011.txt) | 50 | 198 | 17.5% | 62.7% | 3.3% |
| [013](../examples/transcript_games/episode_013.txt) | 70 | 295 | 20.1% | 66.7% | 5.2% |
| [020](../examples/transcript_games/episode_020.txt) | 67 | 223 | 23.1% | 69.3% | 7.1% |
| [029](../examples/transcript_games/episode_029.txt) | 68 | 217 | 22.7% | 65.4% | 10.2% |
| [035](../examples/transcript_games/episode_035.txt) | 63 | 207 | 25.3% | 67.7% | 3.9% |
| [037](../examples/transcript_games/episode_037.txt) | 64 | 220 | 26.2% | 73.4% | 8.6% |
| [039](../examples/transcript_games/episode_039.txt) | 68 | 224 | 27.5% | 71.2% | 10.3% |
| [041](../examples/transcript_games/episode_041.txt) | 62 | 199 | 28.8% | 70.8% | 8.9% |
| [045](../examples/transcript_games/episode_045.txt) | 72 | 237 | 26.6% | 67.6% | 8.0% |
| [046](../examples/transcript_games/episode_046.txt) | 76 | 254 | 33.0% | 72.4% | 8.8% |
| [049](../examples/transcript_games/episode_049.txt) | 63 | 214 | 30.0% | 73.8% | 10.7% |
| [050](../examples/transcript_games/episode_050.txt) | 66 | 170 | 29.8% | 69.5% | 9.6% |
| [051](../examples/transcript_games/episode_051.txt) | 47 | 152 | 23.1% | 66.3% | 13.1% |
| [052](../examples/transcript_games/episode_052.txt) | 62 | 200 | 25.4% | 67.2% | 12.1% |
| [053](../examples/transcript_games/episode_053.txt) | 62 | 193 | 28.4% | 69.4% | 15.3% |

All reviewed minimums pass. The original four full-game minimums were retained,
and the 78 focused source-phrase cases also pass. The new mining pass added 366
distinct reusable templates (188 pitch/delivery and 178 play/transition phrases).

Run `python full_transcript_comparison.py --check` for current measurements, or
`python full_transcript_comparison.py 1 --gaps 5` to inspect individual gaps.
`python pbp_match_report.py --check` checks all three comparison catalogs.

The baseline was validated with 213 tests passing and eight skips for the absent
optional `anonymized_gameday_1.json` fixture. See [the ledger guide](README.md)
for authoring, fitting, and replay instructions.
