"""Why do source words go unmatched? A missed-word census by cause.

For every unit of the 21 Sleep Baseball sources (the pregame, each observed
appearance with the transition before it, and the postgame), the source words
(host asides excluded) are aligned in order with the production rendering. The
source words the rendering does not reproduce are grouped by clause, and each
clause is classified by a heuristic into one cause:

``missing_fact``
    The hosts state a game fact the fixture cannot express, so no draw can
    produce it (where the ball landed, a season ERA, a pinch hitter).
``unnarrated_fact``
    The fixture records the fact but the renderer never says it (naming the
    runners who score, "a two-run homer").
``wording``
    The renderer narrates the fact, in different words or with a different
    draw (pitch calls, counts, intros, fielder movement verbs).
``other``
    Nothing above matched: unmarked colour, transcription noise, fragments.

Rendered words the source lacks are counted separately as ``our_additions``.
The census is approximate: clause patterns, not a parse. ``--sample N`` prints
random classified clauses for manual review; ``--json`` writes the totals.

    python missed_words.py                 # all 21 sources, totals by cause/type
    python missed_words.py --sample 40     # review a random sample
    python missed_words.py --type hit_spot --examples 20
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
import json
import random
import re

from transcript_asides import ASIDE_BREAK

TTS = re.compile(r'\[TTS SPLIT[^\]]*\]')
TOKEN = re.compile(rf'\w+|{ASIDE_BREAK}')
# Clause boundaries: sentence and comma punctuation, ellipses, line breaks
# and removed asides.
CLAUSE_BREAK = re.compile(rf'\.\.\.|[.!?;,:\n]|{ASIDE_BREAK}|\s-\s')


@dataclass
class Unit:
    source: str            # e.g. episode_049 or pbp_example_1
    index: object          # play index, 'pregame' or 'postgame'
    text: str              # source text (asides replaced by ASIDE_BREAK)
    rendered: str
    play: dict = None      # compiled Gameday play, when the unit is one
    matched: list = field(default_factory=list)   # per source token
    tokens: list = field(default_factory=list)    # (token, start, end)
    rendered_tokens: list = field(default_factory=list)
    rendered_matched: list = field(default_factory=list)


def tokenize(text):
    clean = TTS.sub(lambda m: ' ' * len(m.group()), text)
    return [(m.group().casefold(), m.start(), m.end()) for m in TOKEN.finditer(clean)]


def align(unit):
    unit.tokens = tokenize(unit.text)
    unit.rendered_tokens = tokenize(unit.rendered)
    source = [t for t, _, _ in unit.tokens]
    output = [t for t, _, _ in unit.rendered_tokens]
    unit.matched = [False] * len(source)
    unit.rendered_matched = [False] * len(output)
    matcher = SequenceMatcher(None, source, output, autojunk=False)
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            if source[block.a + k] != ASIDE_BREAK:
                unit.matched[block.a + k] = True
                unit.rendered_matched[block.b + k] = True
    return unit


# --- units -------------------------------------------------------------------

def ledger_units(episode):
    from full_transcript_comparison import spoken_text  # noqa: F401 (same tokens)
    from renderers import NarrativeRenderer
    from transcript_asides import metric_source_text
    from transcript_game_fixtures import OUTPUT_DIR, SOURCE_DIR

    stem = f'episode_{episode:03d}'
    source = metric_source_text(SOURCE_DIR / f'{stem}.txt')
    data = json.loads((OUTPUT_DIR / f'{stem}.json').read_text())
    renderer = NarrativeRenderer(data)
    rendered = renderer.render()
    remember_teams(stem, data)
    lines, out = source.splitlines(), rendered.splitlines()
    plays = data['liveData']['plays']['allPlays']
    units = []
    first = plays[0]['source']['start']
    first_out = renderer._play_line_map[0][0]
    units.append(Unit(stem, 'pregame', '\n'.join(lines[:first - 1]), '\n'.join(out[:first_out])))
    previous_end = first - 1
    for index, play in enumerate(plays):
        start, end = play['source']['start'], play['source']['end']
        low = min(start, previous_end + 1)
        lo, hi = renderer._play_line_map[index]
        units.append(Unit(stem, index, '\n'.join(lines[low - 1:end]), '\n'.join(out[lo:hi]), play))
        previous_end = max(previous_end, end)
    units.append(Unit(stem, 'postgame', '\n'.join(lines[previous_end:]),
                      '\n'.join(out[renderer._play_line_map[len(plays) - 1][1]:])))
    return [align(unit) for unit in units]


def reference_units(example):
    """A reference has no line-level ledger: align the whole game once and give
    each play the source between its neighbours' last and first aligned words."""
    from pbp_comparison import REPOSITORY_ROOT
    from renderers import NarrativeRenderer
    from transcript_asides import metric_source_text

    stem = example.target_file[:-4]
    source = metric_source_text(REPOSITORY_ROOT / example.target_file)
    data = json.loads((REPOSITORY_ROOT / example.fixture_file).read_text())
    renderer = NarrativeRenderer(data)
    rendered = renderer.render()
    remember_teams(stem, data)
    out = rendered.splitlines()
    plays = data['liveData']['plays']['allPlays']
    pieces = [('pregame', '\n'.join(out[:renderer._play_line_map[0][0]]), None)]
    for index, play in enumerate(plays):
        lo, hi = renderer._play_line_map[index]
        pieces.append((index, '\n'.join(out[lo:hi]), play))
    pieces.append(('postgame', '\n'.join(out[renderer._play_line_map[len(plays) - 1][1]:]), None))
    src_tokens = tokenize(source)
    rendered_all, spans = [], []
    for _, text, _ in pieces:
        toks = [t for t, _, _ in tokenize(text)]
        spans.append((len(rendered_all), len(rendered_all) + len(toks)))
        rendered_all.extend(toks)
    words = [t for t, _, _ in src_tokens]
    matched_at = [None] * (len(rendered_all) + 1)
    matcher = SequenceMatcher(None, words, rendered_all, autojunk=False)
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            matched_at[block.b + k] = block.a + k
    previous, last = [], -1
    for i in range(len(rendered_all) + 1):
        previous.append(last)
        if matched_at[i] is not None:
            last = matched_at[i]
    units, cursor = [], 0
    for (index, text, play), (low, high) in zip(pieces, spans):
        if index == 'postgame':
            end_token = len(src_tokens)
        else:
            # Up to and including this piece's last aligned source word.
            end_token = max(previous[high] + 1, cursor)
        if end_token > cursor:
            begin = src_tokens[cursor][1] if cursor < len(src_tokens) else len(source)
            # Extend to the end of the line holding the last word, so trailing
            # punctuation stays with its clause.
            stop = source.find('\n', src_tokens[end_token - 1][2])
            stop = len(source) if stop < 0 or index == 'postgame' else stop
            piece = source[begin:stop]
            # Consume every token that the extended span covers.
            while end_token < len(src_tokens) and src_tokens[end_token][1] < stop:
                end_token += 1
        else:
            piece = ''
        units.append(align(Unit(stem, index, piece, text, play)))
        cursor = max(cursor, end_token)
    return units


def remember_teams(stem, data):
    game = data['gameData']
    TEAM_NAMES[stem] = [team.get('name', '') for team in game['teams'].values()] + [str(game.get('venue', ''))]


def all_units(sources=None):
    from pbp_comparison import FULL_TRANSCRIPT_MINIMUMS, PBP_EXAMPLES
    units = []
    for episode in FULL_TRANSCRIPT_MINIMUMS:
        if sources is None or f'episode_{episode:03d}' in sources:
            units.extend(ledger_units(episode))
    for example in PBP_EXAMPLES:
        if sources is None or example.target_file[:-4] in sources:
            units.extend(reference_units(example))
    return units


# --- classification ----------------------------------------------------------

def _rx(*words):
    return re.compile(r'\b(?:' + '|'.join(words) + r')\b', re.I)


NUMBER = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)"

# (cause, fact type, pattern, exclude). Order matters: the first match wins,
# so the specific fact patterns come before the generic wording ones. A clause
# matching ``exclude`` skips that rule.
PITCH_CONTEXT = _rx(r'strike', r'called', r'paints?', r'ball (?:one|two|three|four)', r'for a ball', r'misses',
                    r'fastball', r'curve\w*', r'slider', r'change-?up', r'sinker', r'cutter', r'pitch', r'swing\w*', r'taken', r'dirt')
BALL_NOUN_START = re.compile(r'^\W*(?:and\s+)?(?:a\s+|that.s\s+a\s+)?(?:hard\s+|soft\s+|slow\s+|high\s+)?(?:grounder|roller|chopper|bouncer|'
                             r'one-hopper|tapped|tapper|ground ball|liner|line drive|fly ball|pop-?up|popped|bunt\w*|dribbler)\b', re.I)
RULES = [
    # --- facts the fixture cannot express --------------------------------
    ('missing_fact', 'pitch_speed', re.compile(rf'\b{NUMBER}(?:[- ]{NUMBER})? (?:miles an hour|mph)\b|\bmiles an hour\b|\bon the gun\b', re.I), None),
    ('missing_fact', 'season_stats', _rx(r'era', r'earned run average', r'this season', r'on the season', r'on the year',
                                         r'this year', r'innings? of work', r'batting average', r'(?:hitting|batting) \.?\d{3}',
                                         r'home runs? (?:on|this)', r'record of', r'(?:wins|losses) and', r'\d+ era', r'era of',
                                         r'leads? the league', r'league lead', r'\w+ start (?:for|of)', r'career', r'gets the save',
                                         r'notch\w+ (?:another|the|a) save', r'the win', r'the loss', r'losing pitcher', r'winning pitcher'),
                                         _rx(r'this evening', r'tonight(?!.s)')),
    ('missing_fact', 'substitution', _rx(r'pinch[- ]?hit\w*', r'pinch[- ]?run\w*', r'pinch hitter', r'bat for himself',
                                         r'defensive (?:change|replacement)', r'into the game', r'double switch', r'has been tossed',
                                         r'ejected', r'tossed (?:from|out)', r'will (?:now )?play (?:first|second|third|short|left|right|center)'),
                                         None),
    ('missing_fact', 'hit_spot', _rx(r'gap', r'alley', r'down the (?:left|right)[- ]field line', r'down the (?:first|third)[- ]base line',
                                     r'down the line', r'corner', r'warning track', r'on the track', r'the wall', r'wall',
                                     r'shallow', r'deep', r'short of', r'track', r'in the hole', r'up the middle', r'down the middle',
                                     r'over the bag', r'right[- ]cent\w+', r'left[- ]cent\w+', r'straightaway', r'into the seats',
                                     r'yard', r'fence', r'in front of (?:him|the|home)', r'no man.s land', r'between', r'over (?:his|the) head',
                                     r'drops? in', r'falls? in', r'drop in', r'fall in', r'into the stands', r'seats', r'bleachers',
                                     r'(?:left|right) side', r'way up', r'a long'), re.compile(PITCH_CONTEXT.pattern + r'|\bcrowd\b', re.I)),
    ('missing_fact', 'contact_quality', _rx(r'hard', r'harder', r'hammered', r'crushed', r'smoked', r'scorched', r'ripped',
                                            r'rocket', r'stung', r'sharply', r'sharp', r'soft', r'softly', r'weak\w*', r'blooper',
                                            r'bloop\w*', r'dribbler', r'swinging bunt', r'slow roller', r'topped', r'squibbed',
                                            r'jammed', r'broken[- ]bat', r'off the end', r'well[- ]hit', r'mis-?hit',
                                            r'high chopper', r'high bouncer', r'can of corn', r'nubber',
                                            r'smacks?', r'belted', r'blast', r'gave that one a ride'), _rx(r'breeze', r'lazy', r'(?:routine|easy|tough) play')),
    ('missing_fact', 'throw_play', _rx(r'no throw', r'no play', r'no time', r'the throw', r'throw (?:home|to the plate|to third|to second)',
                                       r'cut ?off', r'relay', r'tag(?:s|ged|ging)?', r'slid(?:es|ing)', r'slide', r'rundown', r'beats? the throw', r'in ahead',
                                       r'holds? (?:him|the runner)', r'waved', r'sends? him', r'stop sign', r'not going',
                                       r'checks? him', r'looks? (?:him|the runner) back', r'fires home', r'throws? home',
                                       r'collision', r'play at the plate', r'not in time', r'too late'), _rx(r'tagging along')),
    ('missing_fact', 'fielder_on_hit', re.compile(r"\b(?:past|eludes|beyond|under the glove of|off the glove of|just out of the reach of|"
                                                  r"out of reach of)\s+(?:a\s+)?(?:diving|leaping|lunging|sliding|backhanding|charging|outstretched)?\s*[A-Z][a-z]+"), None),
    # --- recorded facts the renderer does not say -------------------------
    ('unnarrated_fact', 'runner_scores', _rx(r'scores?', r'scoring', r'comes? home', r'crosses the plate', r'com\w+ around',
                                             r'in to score', r'trots? home', r'heads? home', r'home to score', r'race[sd]? home',
                                             r'runs? in', r'(?:one|two|three) runs? (?:in|score)'),
                                             _rx(r'scoreless', r'no score', r'score is', r'scoreboard', r'do not score', r'score that one',
                                                 r'by a score', r'score (?:a|another|two|three|four|\w+ runs?)', r'scoring (?:\w+ )?runs')),
    ('unnarrated_fact', 'pitcher_role', _rx(r'out of the bullpen', r'from the bullpen', r'bullpen', r'coming in to pitch', r'takes? over',
                                            r'replac\w+', r'relie\w+', r'warm\w* up', r'new (?:\w+ )?pitcher', r'brought in',
                                            r'takes? the mound', r'on the mound'), None),
    ('unnarrated_fact', 'lineup_slot', _rx(r'(?:nine|eight|seven|six|five|four|three|two|one|leadoff|cleanup|pitcher.s|\w+th) spot'), None),
    ('unnarrated_fact', 'runner_advance', _rx(r'(?:goes|go|moves?|heads?|on his way|races?|trots?|advances?|advanced) to (?:third|second)',
                                              r'moves? up', r'advanc\w+', r'takes? (?:third|second)', r'holds? (?:at|up)', r'stops? at',
                                              r'first to third', r'heads? for (?:third|second)', r'heading for', r'round\w*', r'stays? (?:at|put)',
                                              r'pull in', r'standing', r'stand-?up', r'into second', r'into third', r'on to (?:second|third)',
                                              r'the runners? (?:hold|move|do not)', r'do not advance', r'hustl\w+'), BALL_NOUN_START),
    ('unnarrated_fact', 'pitcher_game_line', _rx(r'no[- ]hitter', r'perfect game', r'shut ?out', r'retired (?:\w+ )?(?:in a row|straight)',
                                                 r'in a row', r'straight', r'pitch count', r'pitches? (?:tonight|so far|this inning)',
                                                 r'(?:\w+th|first|second|third) strikeout', r'strikeouts? (?:of|this|tonight|so far)',
                                                 r'pair of strikeouts', r'(?:two|three|four|five|six|seven|eight|nine|ten) strikeouts',
                                                 r'hits? allowed', r'allowed', r'given up', r'gone (?:\w+ )?innings',
                                                 r'through (?:\w+ )?innings', r'complete game', r'set down', r'one[- ]hitter',
                                                 r'two[- ]hitter', r'hitless', r'no hits', r'strikes out the side', r'a gem',
                                                 r'struck out (?:\w+ )?batters'), None),
    ('unnarrated_fact', 'run_count', _rx(r'(?:one|two|three|four|grand|\d)[- ]run', r'grand slam', r'rbi', r'runs? batted in',
                                         r'drives? in', r'drove in', r'knocks? in', r'brings? (?:him|them|home|in)', r'singled home',
                                         r'sacrifice fly', r'sac fly', r'insurance', r'solo', r'break the ice', r'adds? (?:a|another|two)'), None),
    ('wording', 'batter_game_history', _rx(r'(?:his )?first time up', r'last time up', r'previous', r'(?:two|three|four|\d) times',
                                                   r'twice', r'(?:is|was|with|now) (?:one|two|three|four|oh|nothing) for', r'\w+-for-\w+', r'oh[- ]for',
                                                   r'been on base', r'last at[- ]bat', r'his (?:first|second|third|fourth) (?:at[- ]bat|trip|time)',
                                                   r'trip to the plate', r'(?:struck|grounded|flied|popped|lined) out (?:in|his|to)',
                                                   r'(?:walked|singled|doubled|tripled|homered) (?:in|his)', r'(?:had|has) a (?:base hit|single|double|triple|walk)',
                                                   r'with a (?:groundout|flyout|strikeout|walk|single|double|base hit|base on balls)',
                                                   r'(?:a|an) (?:groundout|flyout|pop-?out|lineout) (?:and|in)', r'reached (?:on|in)'), None),
    # --- facts the renderer narrates, in other words ----------------------
    ('wording', 'pregame_postgame', _rx(r'starting (?:lineup|nine|9)', r'will bat', r'batting (?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|cleanup)',
                                        r'managed by', r'manager', r'crew chief', r'umpire', r'degrees', r'breeze', r'weather', r'night for',
                                        r'cloud', r'fishbowl', r'winner', r'instagram', r'underway', r'welcome', r'good evening', r'evening, friends',
                                        r'host\w*', r'presents', r'sleep baseball', r'postgame', r'victorious', r'final', r'hometown',
                                        r'local programming', r'stay tuned', r'play ball', r'lineup', r'will play', r'playing (?:first|second|third|short|left|right|center)',
                                        r'(?:shortstop|catcher|first baseman|second baseman|third baseman|left fielder|center fielder|right fielder|designated hitter)',
                                        r'starting pitcher', r'michigan', r'wisconsin', r'from \w+ field', r'field in', r'park'), None),
    ('wording', 'score_state', _rx(r'leads?', r'leading', r'trail\w*', r'tie', r'tied', r'ball ?game', r'nothing', r'lead',
                                   r'ahead', r'behind', r'score', r'scoreless', r'up by', r'down by', r'deficit', r'margin',
                                   r'remains', r'on top', r'in the books'), None),
    ('wording', 'inning_transition', _rx(r'top of the', r'bottom of the', r'middle of the', r'end of', r'last of the',
                                         r'after (?:one|two|three|four|five|six|seven|eight|nine|\w+ innings)', r'half', r'innings?',
                                         r'we.ll be back', r'back with', r'here on', r'radio network', r'northwoods', r'wslp',
                                         r'the side', r'retired in order', r'three up', r'stranded', r'left on', r'leave', r'strand',
                                         r'men left', r'that.ll do it', r'that will do it', r'due up', r'welcome back', r'reporting',
                                         r'coming up', r'in a moment', r'stretch'), _rx(r'from the stretch')),
    ('wording', 'batter_intro', _rx(r'steps? in', r'digs? in', r'step(?:s|ping)? (?:in|up|into)', r'at the plate', r'to the plate',
                                    r'leads? off', r'leading off', r'here.s', r'here comes', r'checks? in', r'check in', r'up next',
                                    r'in the box', r'batter.s box', r'bring\w*', r'batting', r'hitter', r'order', r'cleanup',
                                    r'stands in', r'walks? up', r'he.s up', r'next', r'against', r'represents', r'chance'), None),
    ('wording', 'situation', _rx(r'runners?', r'nobody on', r'bases (?:empty|loaded|clear\w*)', r'on (?:first|second|third)',
                                 r'corners', r'(?:one|two|no|nobody) (?:out|outs|away|down|on)', r'outs?', r'away', r'two down',
                                 r'scoring position', r'aboard', r'at (?:first|second|third)', r'bases', r'trouble', r'jam'), None),
    ('wording', 'matchup', _rx(r'righty', r'lefty', r'right[- ]handed', r'left[- ]handed', r'switch[- ]hitt\w*', r'southpaw',
                               r'bats? (?:left|right)', r'matchup', r'portside'), None),
    ('wording', 'fielder_movement', _rx(r'camped', r'(?:routine|easy|tough) play', r'drift\w*', r'rac\w+', r'running', r'on the run', r'goes back', r'going back',
                                        r'back on it', r'charg\w+', r'rang\w+', r'div\w+', r'leap\w*', r'reach\w*', r'backhand\w*',
                                        r'stretch\w*', r'squeez\w*', r'settles?', r'under it', r'waits?', r'gloves?', r'scoops?', r'scooped',
                                        r'picks? it', r'fields? it', r'gets? to it', r'knocks? it down', r'calls? (?:for )?it', r'calling for it',
                                        r'makes the catch', r'catch', r'caught', r'grabs?', r'hauls?', r'snag\w*', r'sprint\w*', r'jog\w*',
                                        r'moving', r'comes? in', r'coming in', r'over', r'up with it', r'gathers?', r'collects?', r'throws?',
                                        r'fires?', r'tosses?', r'toss', r'flips?', r'retire\w*', r'out at first', r'beats? it out',
                                        r'puts? him out', r'is there', r'has it', r'handles?', r'gobbled', r'smothered', r'unassisted',
                                        r'room', r'has room', r'puts? it'), None),
    ('wording', 'batted_ball', _rx(r'grounder', r'ground(?:s|ed)? (?:ball|out)?', r'roller', r'rolled', r'chopper', r'chopped', r'bouncer',
                                   r'bounc\w+', r'one-hopper', r'tapped', r'liner', r'line drive', r'lined', r'fly ball', r'flied', r'fly', r'flies',
                                   r'pop\w*', r'lifted', r'lofted', r'drive', r'driven', r'hit', r'hits', r'single', r'double',
                                   r'triple', r'homer', r'home run', r'base hit', r'gone', r'outta here', r'out of here',
                                   r'goodbye', r'bunt\w*', r'in the air', r'on the ground', r'through', r'into (?:left|right|center)',
                                   r'to (?:left|right|center|short|first|second|third)', r'error', r'e\d', r'safe', r'reaches', r'swings?',
                                   r'chops?', r'slaps?', r'slapped', r'pokes?', r'punch\w*', r'serves?', r'hooks?', r'slices?', r'pulls?',
                                   r'fair', r'drops?', r'squeaks?', r'(?:left|right|center) field', r'whack'), None),
    ('wording', 'pitch_call', _rx(r'ball (?:one|two|three|four)', r'strike', r'strikes', r'called', r'swing\w*', r'swung', r'miss\w*',
                                  r'whiff\w*', r'foul\w*', r'fouled', r'tipped', r'taken', r'takes', r'outside', r'inside', r'high',
                                  r'low', r'dirt', r'corner', r'away', r'tight', r'fastball', r'curve\w*', r'slider', r'change\w*',
                                  r'sinker', r'cutter', r'splitter', r'knuckle\w*', r'heater', r'breaking', r'off-?speed',
                                  r'pitch', r'pitches', r'deals?', r'delivery', r'stretch', r'windup', r'set', r'kicks?', r'offers?',
                                  r'chases?', r'check\w*', r'paint\w*', r'kisses', r'black', r'zone', r'plate', r'screen', r'stands',
                                  r'out of play', r'back', r'balls?', r'walk\w*', r'ball four', r'first base', r'trot\w*', r'free pass',
                                  r'rung up', r'rings', r'punch\w* out', r'struck', r'strikes? out', r'strikeout', r'k', r'looking',
                                  r'caught', r'pickoff', r'picked off', r'throw over', r'toss over', r'steal\w*', r'stole', r'stolen',
                                  r'the runner goes', r'mound', r'visit', r'shaken? off', r'sign', r'wild pitch', r'passed ball',
                                  r'backstop', r'hit by'), None),
    ('wording', 'count', re.compile(r"\b(?:oh|one|two|three)[- ](?:and[- ])?(?:oh|one|two|three)\b|\bfull count\b|\bfull\b|\bpayoff\b|\bcount\b", re.I), None),
]

SHORT_NOISE = re.compile(r'^\W*(?:and|so|well|now|oh|the|a|he|it|that|this|there|just|here|with|for|of|to|in|on)?\W*$', re.I)


def clause_spans(text):
    spans, start = [], 0
    for m in CLAUSE_BREAK.finditer(text):
        if m.start() > start:
            spans.append((start, m.start()))
        start = m.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def player_names(unit):
    """Last names of everyone in the play (batter, pitcher, runners, fielders)."""
    names = set()
    play = unit.play or {}
    for role in ('batter', 'pitcher'):
        name = play.get('matchup', {}).get(role, {}).get('fullName')
        if name:
            names.add(name.split()[-1].casefold())
    for runner in play.get('runners', []):
        name = runner.get('details', {}).get('runner', {}).get('fullName')
        if name:
            names.add(name.split()[-1].casefold())
        for credit in runner.get('credits', []):
            name = credit.get('player', {}).get('fullName')
            if name:
                names.add(name.split()[-1].casefold())
    return names


def classify(clause, unit):
    framing = unit.index in ('pregame', 'postgame')
    for cause, kind, pattern, exclude in RULES:
        if pattern.search(clause) and not (exclude and exclude.search(clause)):
            if framing and kind not in FRAMING_FACTS:
                # Lineups, venue, weather and sign-offs: the renderer's own
                # pregame and postgame, in other words.
                return 'wording', 'pregame_postgame'
            return cause, kind
    words = re.findall(r'\w+', clause.casefold())
    if words and set(words) & player_names(unit):
        return 'wording', 'names'
    if unit.index in ('pregame', 'postgame'):
        return 'wording', 'pregame_postgame'
    if SCORE_FRAGMENT.search(clause) or (words and set(words) & team_words(unit)):
        return 'wording', 'score_state'
    return 'other', 'unclassified'


FRAMING_FACTS = {'season_stats', 'run_count', 'pitcher_game_line', 'pitch_speed'}
SCORE_FRAGMENT = re.compile(r'^\W*(?:and\s+)?(?:it.s\s+)?(?:\w+\s+)?(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|nothing)\W*$', re.I)
_TEAM_WORDS = {}


def team_words(unit):
    """Team and place names of the unit's game, which only ever appear in
    score, venue and transition talk."""
    key = unit.source
    if key not in _TEAM_WORDS:
        words = set()
        for name in TEAM_NAMES.get(key, ()):
            words.update(w.casefold() for w in re.findall(r'\w+', name))
        _TEAM_WORDS[key] = words
    return _TEAM_WORDS[key]


TEAM_NAMES = {}


@dataclass
class Missed:
    unit: Unit
    clause: str
    words: int              # unmatched words in the clause
    cause: str
    kind: str


def census(units):
    misses = []
    for unit in units:
        token_index = 0
        for start, end in clause_spans(unit.text):
            missed = 0
            while token_index < len(unit.tokens) and unit.tokens[token_index][1] < end:
                token, t_start, _ = unit.tokens[token_index]
                if t_start >= start and token != ASIDE_BREAK and not unit.matched[token_index]:
                    missed += 1
                token_index += 1
            if not missed:
                continue
            clause = unit.text[start:end].strip()
            cause, kind = classify(clause, unit)
            misses.append(Missed(unit, clause, missed, cause, kind))
    return misses


ADDITION_RULES = [
    ('tts_and_layout', re.compile(r'^\W*$')),
    ('inning_context', re.compile(r'\bhere in the (?:top|bottom) of the\b', re.I)),
    ('break_summary', re.compile(r"we'll be back|radio network|wslp|remains|it's .* after|strand|left|do not score|\bin order\b|three up", re.I)),
    ('pitching_change', re.compile(r'Pitching Change|replaces', re.I)),
    ('score_update', re.compile(r'\blead\b|\bleads?\b|\btied?\b|\bnow\b.*\d', re.I)),
]


def additions(units):
    counts = Counter()
    for unit in units:
        token_index = 0
        for start, end in clause_spans(unit.rendered):
            extra = 0
            while token_index < len(unit.rendered_tokens) and unit.rendered_tokens[token_index][1] < end:
                if unit.rendered_tokens[token_index][1] >= start and not unit.rendered_matched[token_index]:
                    extra += 1
                token_index += 1
            if not extra:
                continue
            clause = unit.rendered[start:end]
            label = next((name for name, rx in ADDITION_RULES if rx.search(clause)), 'other_rendered')
            counts[label] += extra
    return counts


def summarize(misses, units):
    total_source = sum(sum(1 for t, _, _ in u.tokens if t != ASIDE_BREAK) for u in units)
    total_missed = sum(m.words for m in misses)
    by_cause, by_kind = Counter(), Counter()
    by_source = defaultdict(Counter)
    for m in misses:
        by_cause[m.cause] += m.words
        by_kind[(m.cause, m.kind)] += m.words
        by_source[m.unit.source][m.cause] += m.words
    return {'source_words': total_source, 'missed_words': total_missed,
            'by_cause': dict(by_cause.most_common()),
            'by_type': {f'{c}:{k}': n for (c, k), n in by_kind.most_common()},
            'by_source': {s: dict(c) for s, c in sorted(by_source.items())},
            'our_additions': dict(additions(units).most_common())}


def print_summary(summary):
    total = summary['missed_words']
    print(f"Source words (asides excluded): {summary['source_words']}; "
          f"unmatched by the rendering: {total} ({total / summary['source_words']:.1%})")
    print('\nBy cause:')
    for cause, n in summary['by_cause'].items():
        print(f'  {cause:16} {n:6}  {n / total:6.1%}')
    print('\nBy fact type:')
    for kind, n in summary['by_type'].items():
        print(f'  {kind:36} {n:6}  {n / total:6.1%}')
    adds = summary['our_additions']
    print(f"\nOur additions (rendered words the source lacks): {sum(adds.values())}")
    for label, n in adds.items():
        print(f'  {label:20} {n:6}')


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('sources', nargs='*', help='e.g. episode_049 pbp_example_1 (default: all 21)')
    parser.add_argument('--sample', type=int, metavar='N', help='print N random classified clauses')
    parser.add_argument('--type', help='only show examples of this fact type (with --examples)')
    parser.add_argument('--examples', type=int, default=0, metavar='N', help='print N clauses per shown type')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    units = all_units(set(args.sources) or None)
    misses = census(units)
    summary = summarize(misses, units)
    if args.json:
        print(json.dumps(summary, indent=2))
        return
    print_summary(summary)
    rng = random.Random(args.seed)
    if args.sample:
        print(f'\nRandom sample of {args.sample} clauses (weighted by missed words):')
        for m in rng.choices(misses, weights=[m.words for m in misses], k=args.sample):
            print(f'  [{m.cause}:{m.kind}] ({m.words}) {m.unit.source}#{m.unit.index}: {m.clause}')
    if args.examples:
        kinds = [args.type] if args.type else sorted({m.kind for m in misses})
        for kind in kinds:
            pool = [m for m in misses if m.kind == kind]
            print(f'\n== {kind} ({sum(m.words for m in pool)} words, {len(pool)} clauses)')
            for m in rng.sample(pool, min(args.examples, len(pool))):
                print(f'  ({m.words}) {m.unit.source}#{m.unit.index}: {m.clause}')


if __name__ == '__main__':
    main()
