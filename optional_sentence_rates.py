"""Measure how often the Sleep Baseball hosts say each optional sentence.

The rates set ``OPTIONAL_SENTENCE_RATES`` in ``renderers/narrative/renderer.py``,
the probability that a simulated game says a sentence the hosts only sometimes
say. Host asides are excluded (``transcript_asides``).

The 17 full broadcasts have reviewed ledgers, so each opportunity comes from a
recorded pitch or play and its source lines. The four PBP references have no
line-level ledger; their opportunities are found line by line (one pitch per
line, delivery before ``...``). Detection is by phrase, so it is approximate.

    python optional_sentence_rates.py
    python optional_sentence_rates.py --json
"""
from collections import Counter
import json
from pathlib import Path
import re

from transcript_asides import metric_source_text
from transcript_game_fixtures import LEDGER_DIR, OUTPUT_DIR, SOURCE_DIR

ROOT = Path(__file__).resolve().parent
NUMBER = r'(?:oh|one|two|three|zero|nothing|[0-3])'
COUNT = re.compile(rf'\b{NUMBER}(?: and |-| to ){NUMBER}\b|\bfull\b|\beven(?:s|ed)?\b', re.I)
NUMBERED_CALL = re.compile(r'\b(?:ball (?:one|two|three)|strike (?:one|two))\b', re.I)
OUT_SAID = re.compile(
    r"out number|\b(?:first|second|third|1st|2nd|3rd) out|\bone out\b|\btwo outs?\b|one away|two away|"
    r"two down|one down|\bend(?:s|ing)? (?:the|this) (?:inning|half|frame|top|bottom)|retire[sd]? the side|"
    r"side is retired|out of the inning|for the out|inning is over|that'?s the inning|three outs", re.I)
HIT_SITUATION = re.compile(
    r"leadoff|lead off|one-out|two-out|no-out|nobody out|one out|two outs?\b|one away|two away|two down|"
    r"starts? (?:things|the inning|off the inning)|keeps? the inning alive|get things going|is aboard|"
    r"aboard with|reaches with|is on with|in business|\bRBI\b|-run (?:single|double|triple)", re.I)
STRIKEOUT_LINE = re.compile(r'strike three|strikes? (?:him )?out|struck out|down on strikes|rings him up|'
                            r'caught looking|punch', re.I)
HIT_LINE = re.compile(r'\b(?:single|double|triple|base hit)\b(?! play)', re.I)
HOME_RUN_RUNS = re.compile(r"\bsolo\b|\b(?:one|two|three|four|[1-4])-run\b|grand slam", re.I)
RUNNER_MOVE = r"[^.]{0,60}?\b(?:scor\w*|com(?:es|ing|e) (?:in|home|around)|home|third|advanc\w*)"
INNING_OVER = re.compile(r"we'll be back|we will be back|be right back|end the inning|third out|"
                         r"out number three|retire the side", re.I)


def result_text(line):
    """The words after the delivery ("The one-oh pitch... <result>")."""
    if '...' in line:
        return line.split('...', 1)[1]
    if re.match(r'(?:and )?the ', line, re.I) and ',' in line:
        return line.split(',', 1)[1]
    return line


def named_runners(play):
    """Last names of the runners a ball in play brings home or to third."""
    if play['result']['event'] == 'Home Run' or not any(
            event.get('details', {}).get('code') == 'X' for event in play['playEvents']):
        return []
    batter = play['matchup']['batter']['id']
    final = {}
    for runner in play['runners']:
        person = runner['details']['runner']
        if person['id'] != batter:
            final[person['id']] = (person['fullName'].split()[-1], runner['movement'])
    names = []
    for name, movement in final.values():
        start, end = movement.get('start') or movement.get('originBase'), movement.get('end')
        if movement.get('isOut') or start not in ('1B', '2B', '3B'):
            continue
        if end in ('score', 'home') or (end == '3B' and start in ('1B', '2B')):
            names.append(name)
    return names


def play_facts(tally, play, text, origin):
    """Opportunities that come from a play's recorded facts and its call."""
    for name in named_runners(play):
        tally.add('runner_scores', bool(re.search(re.escape(name) + RUNNER_MOVE, text, re.I)), origin)
    result = play['result']
    if result['event'] == 'Home Run' and result.get('rbi') and not result.get('isWalkoff'):
        tally.add('home_run_runs', bool(HOME_RUN_RUNS.search(text)), origin)


def ledger_opportunities(tally):
    for path in sorted(LEDGER_DIR.glob('episode_*.json')):
        ledger = json.loads(path.read_text())
        lines = metric_source_text(SOURCE_DIR / ledger['source_file']).splitlines()
        data = json.loads((OUTPUT_DIR / path.name).read_text())
        shared = Counter(event.get('sourceLine') for play in data['liveData']['plays']['allPlays']
                         for event in play['playEvents'])
        for record, play in zip(ledger['plays'], data['liveData']['plays']['allPlays']):
            pitches = [event for event in play['playEvents'] if event['isPitch']]
            for event in pitches:
                line = event.get('sourceLine')
                if not line or shared[line] > 1 or event['details']['code'] in ('X', 'U', 'H'):
                    continue
                if event is pitches[-1] and record['outcome'] in ('Strikeout', 'Walk'):
                    continue
                text = result_text(lines[line - 1])
                if NUMBERED_CALL.search(text) and not re.search(r'strike one', text, re.I):
                    tally.add('count_after_numbered_call', bool(COUNT.search(text)), 'ledger')
            last = max([event['sourceLine'] for event in pitches if event.get('sourceLine')] or [record['source_start']])
            outcome = result_text(' '.join(lines[last - 1:record['source_end']]))
            if record['outcome'] == 'Strikeout':
                gate = 'strikeout_inning_end' if record['outs'] == 3 else 'strikeout_out_number'
                tally.add(gate, bool(OUT_SAID.search(outcome)), 'ledger')
            elif record['outcome'] in ('Single', 'Double', 'Triple'):
                tally.add('hit_situation', bool(HIT_SITUATION.search(outcome)), 'ledger')
            play_facts(tally, play, outcome, 'ledger')


def reference_play_opportunities(tally):
    """Runner and home-run sentences need the fixture's facts: each play's call
    comes from the word alignment of the reference with its rendering."""
    from missed_words import reference_units
    from pbp_comparison import PBP_EXAMPLES
    for example in PBP_EXAMPLES:
        for unit in reference_units(example):
            if unit.play:
                play_facts(tally, unit.play, result_text(unit.text.replace('\n', ' ')), 'reference')


def reference_opportunities(tally):
    for path in sorted(ROOT.glob('pbp_example_*.txt')):
        lines = [line for line in metric_source_text(path).splitlines()
                 if line.strip() and not line.startswith('[TTS')]
        for index, line in enumerate(lines):
            if '...' not in line:
                continue
            text = result_text(line)
            if STRIKEOUT_LINE.search(text):
                following = ' '.join(lines[index + 1:index + 3])
                over = INNING_OVER.search(text) or INNING_OVER.search(following)
                tally.add('strikeout_inning_end' if over else 'strikeout_out_number',
                          bool(OUT_SAID.search(text)), 'reference')
            elif HIT_LINE.search(text):
                tally.add('hit_situation', bool(HIT_SITUATION.search(text)), 'reference')
            elif NUMBERED_CALL.search(text) and not re.search(r'strike one|ball four', text, re.I):
                tally.add('count_after_numbered_call', bool(COUNT.search(text)), 'reference')


class Tally:
    def __init__(self):
        self.counts = Counter()

    def add(self, gate, said, origin):
        self.counts[(gate, origin, 'n')] += 1
        self.counts[(gate, origin, 'said')] += said

    def rows(self):
        gates = sorted({gate for gate, _, _ in self.counts})
        rows = []
        for gate in gates:
            row = {'gate': gate}
            for origin in ('ledger', 'reference'):
                row[origin] = [self.counts[(gate, origin, 'said')], self.counts[(gate, origin, 'n')]]
            said = row['ledger'][0] + row['reference'][0]
            total = row['ledger'][1] + row['reference'][1]
            row.update(said=said, opportunities=total, rate=said / total if total else None)
            rows.append(row)
        return rows


def measure():
    tally = Tally()
    ledger_opportunities(tally)
    reference_opportunities(tally)
    reference_play_opportunities(tally)
    return tally.rows()


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    rows = measure()
    if args.json:
        print(json.dumps(rows, indent=2))
        return
    for row in rows:
        print(f"{row['gate']}: said {row['said']} of {row['opportunities']} ({row['rate']:.1%}); "
              f"broadcasts {row['ledger'][0]}/{row['ledger'][1]}, references {row['reference'][0]}/{row['reference'][1]}")


if __name__ == '__main__':
    main()
