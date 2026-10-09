# Sleep Baseball transcript corpus

Cleaned play-by-play transcripts of the *Northwoods Baseball Sleep Radio* podcast
(Wally McCarthy and producer Phil on WSLP; feed
<https://rss.buzzsprout.com/1915447.rss>), the show the `pbp_example_*.txt`
targets come from. This directory is reference material for mining announcer
turns of phrase, such as pitch calls, count phrasing, batter intros and inning
transitions, to add to the narrative renderer's templates.

All 17 episodes now have reviewed full-broadcast event ledgers in
[`transcript_games/`](../../transcript_games/README.md), with ordinary Gameday
JSON and rendered text in `examples/transcript_games/`. These retain every
observed appearance and pitch, while documenting unbroadcast intervals and
source ambiguities. Episodes 001 and 051 remain incomplete. The renderer uses
recorded baseball facts and integer commentary draws; it does not read these
transcripts to narrate a game or replay their banter verbatim.

A separate set of 78 source-linked cases in `transcript_cases/` checks specific
phrases and situations through production renderer helpers. Both layers are
covered by `python pbp_match_report.py --check`, alongside the original four
PBP references. Use `python full_transcript_comparison.py --gaps 5` for the
full-broadcast wording report, and [PBP_ALIGNMENT_GUIDE.md](../../PBP_ALIGNMENT_GUIDE.md)
for the alignment tools. Preserve these source texts when improving ledgers,
wording pools, or snapshots.

`python pbp_match_report.py --corpus-only --check` also scans pitch, foul and
count clauses across all 21 source games. This automatic component report lists
uncovered source lines and supplements the reviewed full-game and focused-case
comparisons. Additional sourced regression inputs live in
`sleep_baseball_phrase_cases.json`; their output must be reachable through the
production renderer. Component support does not imply a complete historical
game reconstruction or verbatim reproduction of the broadcast.

## Episodes

| File | Aired | Game |
|------|-------|------|
| `episode_001.txt` | 2022-01-07 | Big Rapids Timbers at Cadillac Cars (audio fades out in the top of the 9th) |
| `episode_005.txt` | 2022-07-28 | Tomah Tigers at Cadillac Cars |
| `episode_011.txt` | 2023-01-11 | 47th Annual Old Timers Exhibition (7 innings), Evergreen Field |
| `episode_013.txt` | 2023-04-20 | Opening Day: Tomah Tigers at Big Rapids Timbers |
| `episode_020.txt` | 2023-11-21 | Baraboo Bombers at Cadillac Cars |
| `episode_029.txt` | 2024-08-29 | Barnstorming exhibition: Tomah Tigers at Pumpkin Center River Rats |
| `episode_035.txt` | 2025-02-25 | South Haven Ravens at Tomah Tigers |
| `episode_037.txt` | 2025-04-22 | South Haven Ravens at Big Rapids Timbers (Timber Race) |
| `episode_039.txt` | 2025-06-26 | Manistee Eagles at Baraboo Bombers |
| `episode_041.txt` | 2025-08-28 | Tomah Tigers at Cadillac Cars |
| `episode_045.txt` | 2025-12-15 | Cadillac Cars at Big Rapids Timbers |
| `episode_046.txt` | 2026-01-30 | Manistee Eagles at South Haven Ravens |
| `episode_049.txt` | 2026-04-30 | Big Rapids Timbers at Tomah Tigers |
| `episode_050.txt` | 2026-05-30 | South Haven Ravens at Manistee Eagles |
| `episode_051.txt` | 2026-06-30 | Cadillac Cars at Lake City Loons (suspended by rain after 5½) |
| `episode_052.txt` | 2026-07-22 | Baraboo Bombers at South Haven Ravens (WSLP Hall of Fame) |
| `episode_053.txt` | 2026-08-31 | Lake City Loons at Cadillac Cars (new manager) |

Episodes 044, 047 and 048 are already in the repo as `pbp_example_3.txt`,
`pbp_example_2.txt` and `pbp_example_4.txt`, so they are not repeated here.

Episode 001 jumps from the end of the 7th straight to the bottom of the 8th.
That jump is in the broadcast itself, not a transcription gap. The file ends
where the audio fades to a quiet bed with no speech, partway through the top
of the 9th.

## How these were made

1. Download the enclosure. Buzzsprout's Cloudflare front blocks curl's default
   User-Agent, so send a podcast-app one, for example
   `curl -sL -A "Overcast/3.0 (+http://overcast.fm/; iOS podcast app)" <url>`.
2. Transcribe it with bw-pod's SpeechAnalyzer helper (the same one prime-mover
   runs; see `bw-pod/deploy/transcription.md`):
   `~/Library/Application\ Support/BWPod/transcription-worker ep.mp3 > ep.json`.
   A 2¼-hour episode takes about 80 s.
3. `python segments_to_lines.py ep.json > epNNN.lines.txt` flattens the
   word-timed segments into one timestamped line per ASR segment.
4. Clean the text by hand or with a model, following `CLEANING_SPEC.md`: merge
   fragments, fix names and counts, and cut the between-innings breaks.

The breaks are all in-character: gift-shop and sleepbaseball.com promos, Ted's
Fishing World, Ed Horn's House of Sleep, Salty Sal, Timbuktu AV, Giovanni
Gasparro's PSAs and so on. The show has no real-world ads. Sponsor mentions
that Wally reads during the game call, such as the Glacier's End hot sauce
inning sponsorship, are kept as announcer phrasing.

Recurring names are spelled the way the hand-cleaned `pbp_example_*.txt` files
spell them (Kosinski, Burke Sessions, Shorty Bush, Brink Filbert, Blink
Rudderson, Tiny Howl). Otherwise they follow the spelling used most often
across episodes.

The raw ASR output is not committed, because it still contains the break
spots. It can be regenerated from the steps above.
