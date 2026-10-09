"""Mine the hosts' wording: missed source clauses grouped by renderer situation.

Builds on the missed-word census (``missed_words.py``). Every clause of the 21
sources (asides excluded) is assigned the renderer situation it narrates and
normalised into a slot template, so the same phrasing about different players,
teams, counts or pitches groups together:

    "Shemper deals, fastball low and away for ball two"
        -> pitch:B:low_outside   "{pitcher} deals, {pitch_type} low and away for ball {n}"

Situations come from the ledgers' line-level facts: a clause on a pitch's
source line belongs to that pitch (``pitch:<code>:<location>``; the in-play
pitch's line belongs to the outcome), a clause after the last pitch to the
outcome (``outcome:<event>:<trajectory>:<fielder>``), a clause before the
first pitch to the batter introduction, or to the half-inning transition when
the inning changed. Count phrases are ``count``. The four ``pbp_example``
references have no line-level ledger, so their clauses are grouped by the
census's fact type (``ref:<type>``) and count only as supporting episodes.

For each (situation, template) the report gives:

* ``said``: clauses with that template anywhere in the 17 ledgers, matched or
  not, and ``opportunities``: how often the situation occurs there, so
  ``said / opportunities`` is the hosts' rate for that phrasing;
* ``missed``: the clauses the production rendering failed to reproduce, and
  their unmatched words, which ranks the groups;
* the distinct episodes (references included) and source lines.

    python wording_mining.py                     # markdown report to stdout
    python wording_mining.py --min-episodes 2 --top 80
    python wording_mining.py --situation pitch:B --top 30
    python wording_mining.py --json > mining.json
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import re

from missed_words import all_units, census, classify, clause_spans

# --- normalisation -----------------------------------------------------------

NUM_WORDS = (r'oh|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|'
             r'thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty')
ORDINALS = (r'first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth')
PITCH_TYPES = (r'four[- ]seam fastball|two[- ]seam fastball|split[- ]finger(?:ed)? fastball|'
               r'knuckle[- ]curve|curve ?ball|fastball|slider|change[- ]?up|sinker|cutter|splitter|'
               r'curve|heater|knuckleball|knuckler|screwball|slurve|breaking ball|two[- ]seamer|four[- ]seamer')
DIRECTIONS = r'(?:left|right)[- ]center(?: field)?|(?:left|right|center) field|(?:left|right) centerfield|centerfield'
POSITIONS = (r'shortstop|short|second baseman|first baseman|third baseman|second base|first base|third base|'
             r'left fielder|center fielder|right fielder|catcher|pitcher')

COUNT_RX = re.compile(rf'\b(?:oh|zero|one|two|three|[0-3])(?:[- ]and[- ]|[- ])(?:oh|zero|one|two|[0-2])\b', re.I)
SLOT_RULES = [
    (re.compile(rf'\b(?:{PITCH_TYPES})s?\b', re.I), '{pitch_type}'),
    (re.compile(rf'\b(?:{DIRECTIONS})\b', re.I), '{direction}'),
    (re.compile(rf'\b(?:{ORDINALS})\b', re.I), '{ordinal}'),
    (re.compile(r'\b\d+(?:[- ]to[- ]\d+)?\b'), '{n}'),
    (re.compile(rf'\b(?:{NUM_WORDS})(?:[- ](?:to[- ])?(?:{NUM_WORDS}|nothing))?\b', re.I), '{n}'),
]
PLACE_WORDS = re.compile(r'\b(?:michigan|wisconsin|minnesota)\b', re.I)


def _names(data):
    players = data['gameData'].get('players', {}).values()
    full = sorted({p['fullName'] for p in players if p.get('fullName')}, key=len, reverse=True)
    last = sorted({p['fullName'].split()[-1] for p in players if p.get('fullName')}, key=len, reverse=True)
    first = sorted({p['fullName'].split()[0] for p in players if p.get('fullName') and len(p['fullName'].split()) > 1},
                   key=len, reverse=True)
    return full, last, first


def _play_roles(play):
    roles = {}
    if not play:
        return roles
    for role, key in (('batter', 'batter'), ('pitcher', 'pitcher')):
        name = play.get('matchup', {}).get(key, {}).get('fullName')
        if name:
            roles[name] = role
    for runner in play.get('runners', []):
        name = runner.get('details', {}).get('runner', {}).get('fullName')
        if name and name not in roles:
            roles[name] = 'runner'
        for credit in runner.get('credits', []):
            name = credit.get('player', {}).get('fullName')
            if name and name not in roles:
                roles[name] = 'fielder'
    return roles


class Normaliser:
    """Slot-template one game's clauses."""

    def __init__(self, data):
        game = data['gameData']
        self.full, self.last, self.first = _names(data)
        teams = [t for t in game['teams'].values()]
        self.places = []
        for team in teams:
            for key, slot in (('name', '{team}'), ('teamName', '{team_short}'), ('locationName', '{location}')):
                if team.get(key):
                    self.places.append((team[key], slot))
        if game.get('venue'):
            self.places.append((str(game['venue']), '{venue}'))
        broadcast = game.get('broadcast', {})
        for key, slot in (('network_name', '{network_name}'), ('station_call', '{station_call}')):
            if broadcast.get(key):
                self.places.append((broadcast[key], slot))
        self.places.sort(key=lambda p: len(p[0]), reverse=True)

    def __call__(self, clause, play=None):
        text = ' '.join(clause.replace('’', "'").split())
        roles = _play_roles(play)
        for name in self.full:
            slot = '{' + roles.get(name, 'player') + '}'
            text = re.sub(rf'\b{re.escape(name)}\b', slot, text)
        for name in self.last:
            full = next((f for f in roles if f.split()[-1] == name), None)
            slot = '{' + (roles[full] if full else 'player') + '}'
            text = re.sub(rf"\b{re.escape(name)}\b(?!')", slot, text)
            text = re.sub(rf"\b{re.escape(name)}'s\b", slot[:-1] + "_pos}", text)
        for value, slot in self.places:
            text = re.sub(rf'\b(?:the )?{re.escape(value)}\b', slot, text, flags=re.I)
        text = PLACE_WORDS.sub('{state}', text)
        text = COUNT_RX.sub('{count}', text)
        for rx, slot in SLOT_RULES:
            text = rx.sub(slot, text)
        text = re.sub(r"[^\w{}' -]", ' ', text.casefold())
        text = re.sub(r'\{(\w+)\}', lambda m: '{' + m.group(1) + '}', text)
        return ' '.join(text.split())


# --- situations --------------------------------------------------------------

def _pitch_situation(event):
    details = event.get('details', {})
    code = details.get('code', '?')
    if code == 'B':
        return f"pitch:B:{details.get('location') or 'unlocated'}"
    if code == 'C':
        return f"pitch:C:{details.get('location') or 'default'}"
    if code == 'S':
        return 'pitch:S:strike_three' if event.get('count', {}).get('strikes') == 2 else 'pitch:S'
    if code == 'F':
        return 'pitch:F'
    if code == 'A' or not event.get('isPitch', True):
        return f"action:{details.get('eventType', 'other')}"
    return f'pitch:{code}'


def _outcome_situation(play):
    event = play['result'].get('event', 'Incomplete')
    hit = next((e.get('hitData') for e in reversed(play.get('playEvents', [])) if e.get('hitData')), None)
    if not hit:
        return f'outcome:{event}'
    return f"outcome:{event}:{hit.get('trajectory', '?')}:{hit.get('location', '?')}"


def _transition(units, i):
    """Whether unit ``i`` starts a new half-inning (its pre-pitch lines hold the break)."""
    play = units[i].play
    previous = next((u.play for u in reversed(units[:i]) if u.play and u.source == units[i].source), None)
    if previous is None:
        return play['about']['inning'] != 1 or not play['about']['isTopInning']
    return (previous['about']['inning'], previous['about']['isTopInning']) != (
        play['about']['inning'], play['about']['isTopInning'])


def _intro_situation(play):
    runners = any(r['movement'].get('start') for r in play.get('runners', []))
    return 'intro:runners' if runners else 'intro:empty'


def situation_of(unit, line, kind, is_transition):
    if unit.index in ('pregame', 'postgame'):
        return unit.index
    if unit.source.startswith('pbp_example'):
        return f'ref:{kind}'
    play = unit.play
    pitches = [e for e in play.get('playEvents', []) if e.get('sourceLine')]
    if kind == 'count':
        return 'count'
    on_line = [e for e in pitches if e['sourceLine'] == line]
    if on_line:
        event = on_line[-1] if any(e['details'].get('code') == 'X' for e in on_line) else on_line[0]
        if event['details'].get('code') == 'X':
            return _outcome_situation(play)
        return _pitch_situation(event)
    first = min((e['sourceLine'] for e in pitches), default=None)
    last = max((e['sourceLine'] for e in pitches), default=None)
    if first is not None and line < first:
        if is_transition and kind in ('inning_transition', 'score_state', 'pregame_postgame', 'situation'):
            return 'transition'
        return 'transition' if is_transition and kind not in ('batter_intro', 'names', 'batter_game_history', 'matchup') \
            else _intro_situation(play)
    if last is not None and line > last:
        return _outcome_situation(play)
    if first is None:
        return _outcome_situation(play)
    # Between two pitch lines: the call of the preceding pitch continues.
    before = max((e for e in pitches if e['sourceLine'] < line), key=lambda e: e['sourceLine'])
    return _pitch_situation(before)


def opportunities(units):
    """How often each situation occurs in the 17 ledgers."""
    counts = Counter()
    for i, unit in enumerate(units):
        if unit.source.startswith('pbp_example') or unit.play is None:
            continue
        play = unit.play
        counts['transition' if _transition(units, i) else _intro_situation(play)] += 1
        for event in play.get('playEvents', []):
            if event.get('sourceLine') and event['details'].get('code') != 'X':
                counts[_pitch_situation(event)] += 1
        counts[_outcome_situation(play)] += 1
    counts['count'] = sum(n for s, n in counts.items() if s.startswith('pitch:') and s != 'pitch:X')
    return counts


# --- mining ------------------------------------------------------------------

def mine(units):
    misses = census(units)
    missed_at = {(id(m.unit), m.start): m for m in misses}
    normalisers = {}
    groups = defaultdict(lambda: {'said': 0, 'missed': 0, 'missed_words': 0, 'episodes': set(),
                                  'kinds': Counter(), 'examples': []})
    transitions = {}
    for i, unit in enumerate(units):
        if unit.play is not None and not unit.source.startswith('pbp_example'):
            transitions[id(unit)] = _transition(units, i)
    for unit in units:
        if unit.source not in normalisers:
            from pbp_comparison import REPOSITORY_ROOT, PBP_EXAMPLES
            from transcript_game_fixtures import OUTPUT_DIR
            if unit.source.startswith('episode'):
                path = OUTPUT_DIR / f'{unit.source}.json'
            else:
                example = next(e for e in PBP_EXAMPLES if e.target_file[:-4] == unit.source)
                path = REPOSITORY_ROOT / example.fixture_file
            normalisers[unit.source] = Normaliser(json.loads(path.read_text()))
        norm = normalisers[unit.source]
        for start, end in clause_spans(unit.text):
            raw = unit.text[start:end]
            clause = raw.strip()
            if not re.search(r'\w', clause):
                continue
            offset = start + len(raw) - len(raw.lstrip())
            line = unit.first_line + unit.text.count('\n', 0, offset)
            miss = missed_at.get((id(unit), offset))
            kind = miss.kind if miss else classify(clause, unit)[1]
            situation = situation_of(unit, line, kind, transitions.get(id(unit), False))
            template = norm(clause, unit.play)
            if not template or len(template.split()) < 2:
                continue
            group = groups[(situation, template)]
            if not unit.source.startswith('pbp_example'):
                group['said'] += 1
            group['episodes'].add(unit.source)
            group['kinds'][kind] += 1
            if miss and miss.cause == 'wording':
                group['missed'] += 1
                group['missed_words'] += miss.words
                if len(group['examples']) < 6:
                    group['examples'].append((unit.source, line, clause))
    return groups


def report_rows(groups, opp, min_episodes=1, situation=None):
    rows = []
    for (sit, template), g in groups.items():
        if not g['missed']:
            continue
        if situation and not sit.startswith(situation):
            continue
        if len(g['episodes']) < min_episodes:
            continue
        base = opp.get(sit) if not sit.startswith(('ref:', 'pregame', 'postgame')) else None
        rows.append({'situation': sit, 'template': template, 'said': g['said'], 'missed': g['missed'],
                     'missed_words': g['missed_words'], 'episodes': sorted(g['episodes']),
                     'opportunities': base, 'rate': (g['said'] / base) if base else None,
                     'kind': g['kinds'].most_common(1)[0][0],
                     'examples': [{'source': s, 'line': l, 'text': t} for s, l, t in g['examples']]})
    rows.sort(key=lambda r: (-r['missed_words'], r['situation'], r['template']))
    return rows


def situation_totals(groups):
    totals = defaultdict(Counter)
    for (sit, _), g in groups.items():
        family = sit.split(':')[0] if not sit.startswith(('pitch', 'outcome')) else ':'.join(sit.split(':')[:2])
        totals[family]['missed_words'] += g['missed_words']
        totals[family]['clauses'] += g['missed']
        if len(g['episodes']) >= 2 and g['missed']:
            totals[family]['multi_episode_words'] += g['missed_words']
    return totals


def print_markdown(rows, totals, opp, top):
    print('# Hosts\' wording: missed clauses by renderer situation\n')
    print('Generated by `python wording_mining.py`. A template slot stands for a name, team, place,')
    print('count, number, ordinal, pitch type or field direction. `said` counts every clause with')
    print('the template in the 17 ledgers (matched or not); `rate` is `said / opportunities`, the')
    print('hosts\' rate for that phrasing in its situation. Episodes include the four references.\n')
    print('## Missed wording words by situation family\n')
    print('| Situation | Missed words | Clauses | In 2+ episodes |')
    print('|---|---:|---:|---:|')
    for family, c in sorted(totals.items(), key=lambda kv: -kv[1]['missed_words']):
        print(f"| `{family}` | {c['missed_words']} | {c['clauses']} | {c['multi_episode_words']} |")
    print(f'\n## Top {top} templates by missed words\n')
    print('| Situation | Template | Missed words | Said | Rate | Episodes | Example |')
    print('|---|---|---:|---:|---:|---:|---|')
    for r in rows[:top]:
        rate = f"{r['rate']:.1%}" if r['rate'] is not None else ''
        ex = r['examples'][0]
        print(f"| `{r['situation']}` | {r['template']} | {r['missed_words']} | {r['said']} | {rate} | "
              f"{len(r['episodes'])} | {ex['source']}:{ex['line']} |")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--min-episodes', type=int, default=1)
    parser.add_argument('--situation', help='situation prefix, e.g. pitch:B or outcome:Groundout')
    parser.add_argument('--top', type=int, default=60)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    units = all_units()
    groups = mine(units)
    opp = opportunities(units)
    rows = report_rows(groups, opp, args.min_episodes, args.situation)
    if args.json:
        print(json.dumps({'opportunities': dict(opp), 'rows': rows}, indent=1))
        return
    print_markdown(rows, situation_totals(groups), opp, args.top)


if __name__ == '__main__':
    main()
