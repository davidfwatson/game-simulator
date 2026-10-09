# Cleaning a Sleep Baseball ASR transcript

Input: `epNNN.lines.txt` (made by `segments_to_lines.py`), one ASR segment per line: `IIII [MMM:SS.s] text`.
The ASR (Apple SpeechAnalyzer) splits utterances mid-sentence and mishears names
and baseball terms. Output: a cleaned, readable play-by-play transcript that we
will mine for announcer turns of phrase.

## Output format

- Plain UTF-8 text, one utterance per line. No timestamps, no segment ids.
- Merge ASR fragments into whole sentences/utterances. A pitch lead-in and its
  result go on ONE line joined with "... ", e.g.
  `And the pitch... Curveball misses low. One and oh.`
  `The one-one pitch... Fouled back and out of play. One and two.`
  A plate-appearance intro (batter stepping in + matchup) is its own line.
- Counts are spoken as words, the way Wally says them: "oh and one", "two and two",
  "The oh-two pitch", "And the one-oh...", "full count". The ASR writes these as
  "O2", "01", "1 and 0", "Oh, and to", "VO2", "DO1" — fix them.
- Spell out ordinals and small numbers in the call the way the existing examples
  do: "first out of the inning", "will bat eighth", "top of the fourth",
  "first baseman" (not "1st", "4th", "8"). Keep digits for scores in running
  totals only if that reads naturally ("a 2-nothing lead" is fine), and for
  stats like ERA "4.82" and temperatures.
- A blank line between half-innings (i.e. where a between-innings break was).
- Pregame (station ID, welcome, weather, lineups one player per line, Instagram
  fishbowl winner, listener shout-outs) and postgame recap stay, in order.

## Fix ASR errors — conservatively

- Player/team/place names: use the episode's own lineup readings as the
  authority, and the existing hand-cleaned examples in the repo
  (`pbp_example_1.txt` … `pbp_example_4.txt` in the repo root) for
  spellings of recurring players, parks, umpires, and places (e.g. Loons not
  "Looms", Slauson not "Slosson", "will bat eighth" not "well, bat A",
  "Batting third" not "Betting third", "Fastball" not "Festival"/"Basketball",
  "misses low" not "Mrs. Lowe", "Grounder to short" not "Grounder is short",
  "Quint Cities").
- Obvious mishearings of baseball phrases: fix to the evident phrase.
- Do NOT invent, embellish, or "improve" the prose. Wally's own odd wording is the
  point — keep his exact phrasing, filler ("And", "So,"), and repetitions. Only
  change what the ASR got wrong. If a fragment is unrecoverable, make the most
  conservative guess from context, or drop a lone garbage token.

## Remove (the "commercials")

- Opening jingle/sting garbage before the station ID (e.g. "W.", "uh.",
  "Sleep, baseball, ooh."). Start at the first real announcer line
  ("You're drifting off with WSLP AM, Big Rapids." or "The Northwoods Baseball
  Radio Network presents Sleep Baseball.").
- Everything inside a between-innings break: after the sign-off line ("... after
  these words on WSLP ...", "Back in a minute with more baseball ...") up to the
  return line ("Wally McCarthy and producer Phil, back with you ...", "Top of the
  fourth here in ..."). Keep the sign-off line and the return line themselves.
  Breaks contain the show's own promos ("Stay up to date with all the shenanigans
  of the Sleep Baseball universe at sleepbaseball.com ...", gift shop, Wally's
  World newsletter, fan club), in-character commercial spots read by other voices
  (e.g. "Hey kids, this is Link Retterson ... Ted's Fishing World"; "This is Billy
  the Bombers mascot ... gift shop"), Patreon/membership pitches, and any real
  third-party / dynamically inserted ads. All of it goes.
- Any real third-party ad anywhere else, and any end-of-episode music-bed garbage.

## Keep

- Wally's in-broadcast sponsor mentions woven into the call (e.g. "the first
  inning tonight is sponsored by Glacier's End, makers of Baraboo Bomber hot
  sauce ..."; "courtesy of the fine folks at the Pine Star Lodge"). Those are
  announcer turns of phrase, not ad breaks. When in doubt whether something is a
  break spot or part of the call: if Wally/Phil say it in the flow of the game
  broadcast, keep it; if a different voice reads a standalone spot during a break,
  remove it.
- Mound visits, crowd/weather color, stories, stat notes, pitching changes,
  producer Phil banter, rain delays, postgame recap/line score.
  Keep host asides in the text. Mark them afterwards in `transcript_asides/`
  instead (see `transcript_games/README.md`), so the metrics can exclude them
  without changing the cleaned transcript.
