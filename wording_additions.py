"""Templates added from the hosts' wording, weighted by how often they say it.

``wording_mining.py`` ranks the hosts' missed phrasings by renderer situation.
This catalog holds the ones added to production pools: each entry names its
pool and template, a pattern that finds the hosts saying that phrasing in the
sources, and the slot that measures how often they had the chance.

Running it writes ``transcript_wording_additions.json``: every template with
its measured count, opportunities, episodes, source lines (provenance) and the
sampling weight that makes simulated games say it at the hosts' rate.

Weights. In a pool of ``N`` original templates (weight 1 each), templates
added with host rates ``s_1 .. s_k`` (``said / opportunities``) get

    w_i = s_i * N / (1 - S),    S = s_1 + ... + s_k  (capped at 0.8)

so each is drawn with probability ``s_i`` and the original templates share
the rest. A phrasing the hosts used five times in 1,106 appearances is drawn
about as rarely in a simulated game. ``commentary.TEMPLATE_WEIGHTS`` holds the
result; ``--weights`` prints it. Fixture draws index a pool directly, so the
fitter still sees every template.

Pattern macros, expanded per game: ``{venue}``, ``{location}`` (either team's
city), ``{state}``, ``{team}`` (full name), ``{short}`` (nickname),
``{player}`` (any player's full or last name), ``{pitch}`` (pitch type),
``{n}`` (number word), ``{ordinal}``, ``{count}``, ``{network}`` and
``{station}``.

    python wording_additions.py              # rebuild the JSON catalog
    python wording_additions.py --weights    # print TEMPLATE_WEIGHTS
    python wording_additions.py --check      # fail if the catalog is stale
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / 'transcript_wording_additions.json'
MAX_SHARE = 0.8

# pool, template, pattern (case-insensitive regex with macros), slot, and
# ``generic=True`` for plain broadcast language admitted from one episode.
# ``slot`` is a key of ``slot_counts()`` or ``pattern:<regex>``, the number of
# times the hosts said any form of the slot. ``draw_size`` overrides the
# number of original templates a draw competes with when the pool is merged
# with others at draw time.
A = dict
RETURNS = 12  # the return sentence is drawn from 6 return templates and ~6 intros that open with one
ADDITIONS = [
    # --- the return from a break -----------------------------------------
    A(pool='radio_strings.inning_break_return', template="And welcome back with us from {venue}.",
      pattern=r"welcome back with us from {venue}\.", slot='break_return', draw_size=RETURNS),
    A(pool='radio_strings.inning_break_return',
      template="And welcome back with us from {venue} here in {location_with_state}.",
      pattern=r"welcome back with us from (?:beautiful )?{venue},? (?:here )?in {location}", slot='break_return',
      draw_size=RETURNS),
    A(pool='radio_strings.inning_break_return',
      template="And welcome back with us here from {venue} in {location_with_state}.",
      pattern=r"welcome back with us here from {venue},? (?:here )?in {location}", slot='break_return',
      draw_size=RETURNS),
    A(pool='radio_strings.inning_break_return', template="And welcome back with us.",
      pattern=r"^\W*and welcome back with us[.,]", slot='break_return', draw_size=RETURNS),
    A(pool='radio_strings.inning_break_return', template="And welcome back to {venue} here in {location_with_state}.",
      pattern=r"welcome back to {venue},? (?:here )?in {location}", slot='break_return', draw_size=RETURNS),
    A(pool='radio_strings.inning_break_return', template="Wally McCarthy and producer Phil back with you.",
      pattern=r"producer phil,? back with you\.", slot='break_return', draw_size=RETURNS),
    A(pool='radio_strings.inning_break_return',
      template="Wally McCarthy and producer Phil reporting from {venue} here in {location}.",
      pattern=r"producer phil,? reporting from {venue}", slot='break_return', draw_size=RETURNS),
    A(pool='radio_strings.inning_break_return',
      template="And welcome back with us here on {station_call} and {network_name}.",
      pattern=r"welcome back with us (?:here )?on {station} and {network}", slot='break_return', draw_size=RETURNS),
    # --- the inning introduction ------------------------------------------
    A(pool='radio_strings.inning_break_intro_top', template="{score_lead} as we begin the top of the {inning_ordinal}.",
      pattern=r"as we begin the top of the {ordinal}", slot='break_top'),
    A(pool='radio_strings.inning_break_intro_top', template="{score_lead} as we enter the top of the {inning_ordinal}.",
      pattern=r"as we enter the top of the {ordinal}", slot='break_top'),
    A(pool='radio_strings.inning_break_intro_top',
      template="{half} of the {inning_ordinal} inning here in {location} at {venue}. {score_lead}.",
      pattern=r"top of the {ordinal} inning,? here (?:in {location},? at {venue}|at {venue},? in {location})[.,] "
              r"(?:the {short} lead the {short}|no score|we are tied|the {short} and the {short} are tied)",
      slot='break_top'),
    A(pool='radio_strings.inning_break_intro_top',
      template="Top of the {inning_ordinal} inning here at {venue}. {score_lead}, and the {batting_team_short} "
               "will bring {due_up_desc} to the plate against {pitcher_name}.",
      pattern=r"top of the {ordinal}\b[^.]*\.[^.]*will bring the {n}, {n},? and {n} hitters to the plate",
      slot='break_top'),
    A(pool='radio_strings.inning_break_intro_bottom', template="{score_lead} as we begin the bottom of the {inning_ordinal}.",
      pattern=r"as we begin the bottom of the {ordinal}", slot='break_bottom'),
    A(pool='radio_strings.inning_break_intro_bottom', template="{score_lead} as we enter the bottom of the {inning_ordinal}.",
      pattern=r"as we enter the bottom of the {ordinal}", slot='break_bottom'),
    A(pool='radio_strings.inning_break_intro_bottom',
      template="Bottom of the {inning_ordinal} inning here at {venue}. {score_lead}, and the {batting_team_short} "
               "will bring {due_up_desc} to the plate against {pitcher_name}.",
      pattern=r"bottom of the {ordinal}\b[^.]*\.[^.]*will bring the {n}, {n},? and {n} hitters to the plate",
      slot='break_bottom'),
    # --- the score at the break -------------------------------------------
    A(pool='radio_strings.inning_summary_remains',
      template="We've played {innings_word} here at {venue}, and it remains {leading_short} {leading_score_val}, "
               "{trailing_short} {score_trail}.",
      pattern=r"we've played {n}(?: and a half)? here at {venue}", slot='break'),
    A(pool='radio_strings.inning_summary_remains',
      template="And with {inning_count_word} in the books, it remains {leading_short} {leading_score_val}, "
               "{trailing_short} {score_trail}.",
      pattern=r"with {n} in the books,? it remains {short}", slot='break_top'),
    A(pool='radio_strings.inning_summary_tied', template="And after {innings_word}, we are tied at {score}.",
      pattern=r"after {n}(?: and a half)?,? we(?: are|'re) (?:still |all )?tied", slot='break'),
    A(pool='radio_strings.inning_outro_scored_first', template="But the {batting_team_short} get on the board.",
      pattern=r"but the {short} get on the board", slot='game'),
    A(pool='radio_strings.inning_summary_remains_stretch',
      template="And as we head into the stretch, it remains {leading_short} {leading_score_val}, {trailing_short} {score_trail}.",
      pattern=r"as we head into the stretch", slot='stretch', draw_size='radio_strings.inning_summary_remains'),
    A(pool='radio_strings.inning_summary_score_stretch',
      template="And as we head into the stretch, it's {leading_short} {leading_score_val}, {trailing_short} {score_trail}.",
      pattern=r"as we head into the stretch", slot='stretch', draw_size='radio_strings.inning_summary_score'),
    A(pool='radio_strings.inning_summary_tied_stretch', template="And as we head into the stretch, we are tied at {score}.",
      pattern=r"as we head into the stretch", slot='stretch', draw_size='radio_strings.inning_summary_tied'),
    A(pool='radio_strings.inning_summary_scoreless_stretch',
      template="And as we head into the stretch, it remains a scoreless contest.",
      pattern=r"as we head into the stretch", slot='stretch', draw_size='radio_strings.inning_summary_scoreless'),
    # --- pregame and postgame ---------------------------------------------
    A(pool='radio_strings.station_intro', template="You're drifting off with {station_call} AM.",
      pattern=r"^you're drifting off with {station} am", slot='game'),
    A(pool='radio_strings.outro',
      template="Producer Phil and I will be back with the postgame show in a moment here on {station_call} and {network_name}.",
      pattern=r"producer phil and i will be back with the post-?game show in a moment,? here on {station} and {network}",
      slot='game'),
    # --- batter introductions ---------------------------------------------
    A(pool='narrative_strings.batter_intro_leadoff', template="And {batter_name} is due up against {pitcher_name}.",
      pattern=r"and {player} is due up against {player}", slot='leadoff'),
    A(pool='narrative_strings.batter_intro_leadoff', template="And {batter_name} steps in against {pitcher_name}.",
      pattern=r"and {player} steps in against {player}", slot='plate_appearance'),
    A(pool='narrative_strings.batter_intro_leadoff',
      template="And {batter_name} will step in at the top of the {team_short_possessive} order.",
      pattern=r"will step in at the top of the {short}'?s? order", slot='leadoff'),
    A(pool='narrative_strings.batter_intro_leadoff',
      template="And that will bring up {batter_name} at the top of the {team_short_possessive} order.",
      pattern=r"that will bring up {player} at the top of the {short}'?s? order", slot='leadoff'),
    A(pool='narrative_strings.batter_intro_leadoff',
      template="And here's {batter_name} at the top of the {team_short_possessive} order.",
      pattern=r"here's {player} at the top of the {short}'?s? order", slot='leadoff'),
    A(pool='narrative_strings.batter_intro_empty', template="{outs_str}, nobody on for {batter_name}.",
      pattern=r"\b(?:one|two) (?:outs?|away|down)[.,]? nobody on for {player}", slot='later_batter'),
    A(pool='narrative_strings.batter_intro_empty', template="{outs_str}, bases empty for {batter_name}.",
      pattern=r"\b(?:one|two) (?:outs?|away|down)[.,]? bases empty for {player}", slot='later_batter'),
    A(pool='narrative_strings.outs_none', template="no outs", pattern=r"\bno outs\b",
      slot=r"pattern:\b(?:nobody out|no outs)\b"),
    A(pool='narrative_strings.outs_one', template="one out", pattern=r"\bone out\b",
      slot=r"pattern:\bone (?:out|away|down)\b"),
    A(pool='narrative_strings.outs_one', template="one down", pattern=r"\bone down\b",
      slot=r"pattern:\bone (?:out|away|down)\b"),
    A(pool='narrative_strings.outs_two', template="two outs", pattern=r"\btwo outs\b",
      slot=r"pattern:\btwo (?:outs|away|down)\b"),
    A(pool='narrative_strings.outs_two', template="two away", pattern=r"\btwo away\b",
      slot=r"pattern:\btwo (?:outs|away|down)\b"),
    # --- which out --------------------------------------------------------
    A(pool='narrative_strings.out_context_one', template="for the first out of the inning",
      pattern=r"for the first out of the inning", slot=r"pattern:for out number one|for the first out"),
    A(pool='narrative_strings.out_context_one', template="for the first out",
      pattern=r"for the first out\b(?! of)", slot=r"pattern:for out number one|for the first out"),
    A(pool='narrative_strings.out_context_one', template="for the first out of the frame",
      pattern=r"for the first out of the frame", slot=r"pattern:for out number one|for the first out"),
    A(pool='narrative_strings.out_context_two', template="for the second out of the inning",
      pattern=r"for the second out of the inning", slot=r"pattern:for out number two|for the second out"),
    A(pool='narrative_strings.out_context_two', template="for the second out",
      pattern=r"for the second out\b(?! of)", slot=r"pattern:for out number two|for the second out"),
    A(pool='narrative_strings.out_context_three', template="for out number three",
      pattern=r"for out number three", slot=r"pattern:to end the inning|for out number three|for the third out"),
    A(pool='narrative_strings.out_context_three', template="for the third out",
      pattern=r"for the third out", slot=r"pattern:to end the inning|for out number three|for the third out"),
    A(pool='narrative_strings.out_context_game', template="to end the ball game",
      pattern=r"to end the ball ?game", slot='game'),
    # --- pitch calls, counts, fouls ---------------------------------------
    A(pool='pitch_locations.ball.dirt', template="And that's a {pitch_type_lower} in the dirt",
      pattern=r"and that's an? {pitch} in the dirt", slot='ball:dirt'),
    A(pool='pitch_locations.ball.low', template="And that {pitch_type_lower} misses low",
      pattern=r"and that {pitch} misses low", slot='ball:low'),
    A(pool='pitch_locations.ball.high', template="And that {pitch_type_lower} misses high",
      pattern=r"and that {pitch} misses high", slot='ball:high'),
    A(pool='pitch_locations.ball.inside', template="brushes him back",
      pattern=r"brushes him back", slot='ball:inside'),
    A(pool='narrative_strings.count_full', template=", full count", pattern=r"\bfull count\.",
      slot=r"pattern:full count|count runs full|count is (?:now )?full|fills the count"),
    A(pool='narrative_strings.count_even', template="count even at {count_str}", pattern=r"count even at {count}",
      slot=r"pattern:\b(?:two and two|two-two)\b"),
    A(pool='narrative_strings.count_plain', template="and it's {count_str}", pattern=r"\band it's {count}\b",
      slot=r"pattern:\b(?:oh|one|two|three)(?: and |-)(?:oh|one|two)\b"),
    A(pool='narrative_strings.foul_another', template="And he fouls another one off",
      pattern=r"and he fouls another one off", slot=r"pattern:fouls another one off|fouled off again"),
    A(pool='narrative_strings.foul_another', template="Fouled off again",
      pattern=r"fouled off again", slot=r"pattern:fouls another one off|fouled off again"),
]

NUM = (r'(?:oh|zero|nothing|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|'
       r'thirteen|fourteen|fifteen|\d+)')
ORD = r'(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth)'
PITCH = (r'(?:fastball|four[- ]seam(?:er| fastball)|two[- ]seam(?:er| fastball)|curve ?ball|curve|slider|'
         r'change[- ]?up|sinker|cutter|splitter|knuckle ?ball|knuckler|knuckle[- ]curve|heater|screwball|slurve|breaking ball)')
COUNT = r'(?:oh|one|two|three)[- ](?:and[- ])?(?:oh|one|two)'


def _alt(values):
    values = sorted({v for v in values if v}, key=len, reverse=True)
    return '(?:' + '|'.join(re.escape(v) for v in values) + ')' if values else '(?!x)x'


class Game:
    """One source with its fixture's names, for macro expansion."""

    def __init__(self, stem, source_path, fixture_path, ledger=True):
        from transcript_asides import metric_source_text
        self.stem, self.ledger = stem, ledger
        self.lines = metric_source_text(source_path).splitlines()
        self.raw = source_path.read_text().splitlines()
        data = json.loads(fixture_path.read_text())
        game = data['gameData']
        teams = list(game['teams'].values())
        players = [p['fullName'] for p in game.get('players', {}).values() if p.get('fullName')]
        broadcast = game.get('broadcast', {})
        network = broadcast.get('network_name') or 'Northwoods Baseball Radio Network'
        self.macros = {
            'venue': _alt([str(game.get('venue', ''))]),
            'location': _alt([t.get('locationName') for t in teams]),
            'state': r'(?:Michigan|Wisconsin|Minnesota|South Dakota|Iowa|Illinois)',
            'team': _alt([t.get('name') for t in teams]),
            'short': _alt([t.get('teamName') for t in teams]),
            'player': _alt(players + [p.split()[-1] for p in players]),
            'pitch': PITCH, 'n': NUM, 'ordinal': ORD, 'count': COUNT,
            'network': r'the ' + re.escape(re.sub(r'^the ', '', network, flags=re.I)),
            'station': _alt([broadcast.get('station_call') or 'WSLP']),
        }

    def regex(self, pattern):
        return re.compile(re.sub(r'\{(\w+)\}', lambda m: self.macros[m.group(1)], pattern), re.I)


def games():
    from pbp_comparison import PBP_EXAMPLES, REPOSITORY_ROOT
    from transcript_game_fixtures import OUTPUT_DIR, SOURCE_DIR
    found = [Game(p.stem, SOURCE_DIR / f'{p.stem}.txt', p)
             for p in sorted(OUTPUT_DIR.glob('episode_*.json'))]
    found += [Game(e.target_file[:-4], REPOSITORY_ROOT / e.target_file, REPOSITORY_ROOT / e.fixture_file, ledger=False)
              for e in PBP_EXAMPLES]
    return found


def slot_counts():
    """How often each slot comes up in the 17 ledgers."""
    from transcript_game_fixtures import LEDGER_DIR
    from optional_sentence_rates import measure
    counts = Counter()
    for path in sorted(LEDGER_DIR.glob('episode_*.json')):
        ledger = json.loads(path.read_text())
        counts['game'] += 1
        previous = None
        outs = 0
        for play in ledger['plays']:
            half = (play['inning'], play['top'])
            new_half = half != previous
            if new_half:
                outs = 0
                if previous is not None:
                    counts['break'] += 1
                    counts['break_top' if play['top'] else 'break_bottom'] += 1
                    if previous[1] and previous[0] == 7:
                        counts['stretch'] += 1
            counts['plate_appearance'] += 1
            counts['leadoff' if new_half else 'later_batter'] += 1
            for pitch in play.get('pitches', []):
                code = pitch.get('code')
                if code == 'B':
                    counts[f"ball:{pitch.get('location') or 'unlocated'}"] += 1
                    counts['ball'] += 1
                elif code == 'C':
                    counts[f"called:{pitch.get('location') or 'default'}"] += 1
                    counts['called'] += 1
                elif code in ('S', 'F'):
                    counts['swinging' if code == 'S' else 'foul'] += 1
                if code in ('B', 'C', 'S', 'F'):
                    counts['pitch'] += 1
            outcome = play.get('outcome', '')
            counts[f'outcome:{outcome}'] += 1
            if outcome == 'Strikeout':
                counts['strikeout'] += 1
            previous = half
    returns = next(row for row in measure() if row['gate'] == 'break_return')
    counts['break_return'] = returns['ledger'][0]
    return counts


def occurrences(entry, all_games):
    """Every source line where the hosts use the entry's phrasing."""
    found = []
    for game in all_games:
        rx = game.regex(entry['pattern'])
        for number, line in enumerate(game.lines, start=1):
            for match in rx.finditer(line):
                found.append({'source': game.stem, 'line': number, 'ledger': game.ledger,
                              'expected': match.group(0).strip(' ,.'), 'source_text': game.raw[number - 1]})
    return found


def build():
    from transcript_comparison import get_pool
    all_games, slots = games(), slot_counts()
    rows = []
    for entry in ADDITIONS:
        found = occurrences(entry, all_games)
        said = sum(1 for f in found if f['ledger'])
        if entry['slot'].startswith('pattern:') and entry['slot'] not in slots:
            slots[entry['slot']] = sum(len(game.regex(entry['slot'][8:]).findall(line))
                                       for game in all_games if game.ledger for line in game.lines)
        episodes = sorted({f['source'] for f in found})
        rows.append({'pool': entry['pool'], 'template': entry['template'], 'pattern': entry['pattern'],
                     'draw_size': entry.get('draw_size'),
                     'slot': entry['slot'], 'said': said, 'opportunities': slots[entry['slot']],
                     'rate': round(said / slots[entry['slot']], 4) if slots[entry['slot']] else 0.0,
                     'episodes': episodes, 'generic': bool(entry.get('generic')),
                     'provenance': [{k: f[k] for k in ('source', 'line', 'expected', 'source_text')}
                                    for f in found[:6]]})
    by_pool = {}
    for row in rows:
        by_pool.setdefault(row['pool'], []).append(row)
    for pool, members in by_pool.items():
        size = members[0].pop('draw_size')
        for row in members[1:]:
            row.pop('draw_size')
        if isinstance(size, str):
            size = len(get_pool(size))
        original = size or len(get_pool(pool)) - len(members)
        share = min(sum(r['rate'] for r in members), MAX_SHARE)
        scale = min(1.0, MAX_SHARE / sum(r['rate'] for r in members)) if sum(r['rate'] for r in members) else 1.0
        for row in members:
            row['original_pool_size'] = original
            row['weight'] = round(max(row['rate'] * scale, 0.0005) * original / (1 - share), 4)
    return rows


def weights(rows):
    out = {}
    for row in rows:
        if row['template'] in out and out[row['template']] != row['weight']:
            out[row['template']] = max(out[row['template']], row['weight'])
        else:
            out[row['template']] = row['weight']
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--weights', action='store_true', help='print TEMPLATE_WEIGHTS')
    parser.add_argument('--check', action='store_true', help='fail if the catalog or weights are stale')
    args = parser.parse_args()
    rows = build()
    if args.check:
        from commentary import TEMPLATE_WEIGHTS
        stale = json.loads(CATALOG.read_text()) != rows
        if stale or TEMPLATE_WEIGHTS != weights(rows):
            raise SystemExit('transcript_wording_additions.json or TEMPLATE_WEIGHTS is stale; rerun this script')
        print(f'{len(rows)} additions, catalog and weights current')
        return
    if args.weights:
        print('TEMPLATE_WEIGHTS = {')
        for template, weight in weights(rows).items():
            print(f'    {json.dumps(template)}: {weight},')
        print('}')
        return
    CATALOG.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n')
    for row in rows:
        flag = '' if len(row['episodes']) >= 2 or row['generic'] else '  <-- ONE EPISODE'
        print(f"{row['said']:4}/{row['opportunities']:<5} {row['rate']:6.1%} w={row['weight']:<7} "
              f"eps={len(row['episodes']):2} {row['pool']}: {row['template']}{flag}")


if __name__ == '__main__':
    main()
