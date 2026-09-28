"""Compile reviewed broadcast event ledgers into ordinary Gameday data.

Source text is provenance only. NarrativeRenderer receives baseball facts and
commentary draws; it never reads the reference transcript to generate its output.
Unknown/unbroadcast pitches are not manufactured to fill a count or an inning.
"""
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / 'transcripts' / 'sleep_baseball'
LEDGER_DIR = ROOT / 'transcript_games'
OUTPUT_DIR = ROOT / 'examples' / 'transcript_games'
POSITIONS = {
    'P': ('1', 'Pitcher'), 'C': ('2', 'Catcher'), '1B': ('3', 'First Baseman'),
    '2B': ('4', 'Second Baseman'), '3B': ('5', 'Third Baseman'),
    'SS': ('6', 'Shortstop'), 'LF': ('7', 'Left Fielder'),
    'CF': ('8', 'Center Fielder'), 'RF': ('9', 'Right Fielder'),
    'DH': ('D', 'Designated Hitter'), '': ('', 'Player'),
}
EVENT_TYPES = {
    'Hit': 'hit', 'Single': 'single', 'Double': 'double', 'Triple': 'triple', 'Home Run': 'home_run',
    'Walk': 'walk', 'Intentional Walk': 'intent_walk', 'Strikeout': 'strikeout',
    'Hit By Pitch': 'hit_by_pitch', 'Field Error': 'field_error',
    'Double Play': 'grounded_into_double_play', 'Forceout': 'force_out',
    'Fielders Choice': 'fielders_choice', 'Reached Base': 'reached_base', 'Sac Fly': 'sac_fly',
    'Sacrifice Bunt': 'sac_bunt', 'Incomplete': 'incomplete',
}
HIT_BASES = {'Reached Base': '1B', 'Hit': '1B', 'Single': '1B', 'Double': '2B', 'Triple': '3B', 'Home Run': 'score',
             'Walk': '1B', 'Intentional Walk': '1B', 'Hit By Pitch': '1B',
             'Field Error': '1B', 'Forceout': '1B', 'Fielders Choice': '1B'}


def position(abbreviation):
    code, name = POSITIONS.get(abbreviation, POSITIONS[''])
    return {'code': code, 'name': name, 'abbreviation': abbreviation}


def hand(code):
    return {'code': code, 'description': {'L': 'Left', 'R': 'Right', 'S': 'Switch'}.get(code, 'Unknown')}


def compile_game(ledger, source_bytes):
    source_lines = source_bytes.decode('utf-8').splitlines()
    number = ledger['episode']
    game = ledger['game']
    records = ledger['plays']
    if not records:
        raise ValueError('A full broadcast ledger must contain observed plays')
    players = {}
    names = {}

    def person(name, pos='', bat_side='U'):
        if not name:
            raise ValueError('Player names must be explicit; use an identified unknown when source omits one')
        if name not in names:
            pid = number * 1000 + len(names) + 1
            names[name] = pid
            players[f'ID{pid}'] = {
                'id': pid, 'fullName': name, 'lastName': name.split()[-1],
                'primaryPosition': position(pos), 'batSide': hand(bat_side), 'pitchHand': hand('U'),
            }
        pid = names[name]
        player = players[f'ID{pid}']
        if pos:
            player['primaryPosition'] = position(pos)
        if bat_side != 'U':
            player['batSide'] = hand(bat_side)
        return {'id': pid, 'fullName': name}

    teams, boxes = {}, {}
    for index, side in enumerate(('away', 'home')):
        name = game[side]
        teams[side] = {'id': number * 10 + index, 'name': name,
                       'teamName': name.split()[-1], 'locationName': ' '.join(name.split()[:-1]),
                       'manager': game.get(f'{side}_manager', '')}
        order = []
        for player in game.get(f'{side}_lineup', []):
            order.append(person(player['name'], player.get('position', ''), player.get('bat_side', 'U'))['id'])
        boxes[side] = {'team': teams[side], 'battingOrder': order}
        person(game[f'{side}_pitcher'], 'P')

    plays, bases = [], {}
    current_half, previous_score, previous_outs = None, [0, 0], 0
    totals = {'away': Counter(), 'home': Counter()}
    for index, record in enumerate(records):
        start, end = record['source_start'], record['source_end']
        if not 1 <= start <= end <= len(source_lines):
            raise ValueError(f'Play {index}: invalid source range {start}-{end}')
        if index and start < records[index - 1]['source_start']:
            raise ValueError(f'Play {index}: source ranges are out of order')
        half = (record['inning'], record['top'])
        coverage_gap = (current_half is not None and
                        2 * half[0] + (not half[1]) > 2 * current_half[0] + (not current_half[1]) + 1)
        if half != current_half:
            bases, previous_outs = {}, 0
            current_half = half
        batter = person(record['batter'], bat_side=record.get('bat_side', 'U'))
        pitcher = person(record['pitcher'], 'P')
        if record.get('pitch_hand') in ('L', 'R'):
            players[f'ID{pitcher["id"]}']['pitchHand'] = hand(record['pitch_hand'])
        outcome = record['outcome']
        outs, score = record['outs'], record['score']
        if not previous_outs <= outs <= 3:
            raise ValueError(f'Play {index}: invalid out progression {previous_outs}->{outs}')
        if any(now < before for now, before in zip(score, previous_score)):
            raise ValueError(f'Play {index}: score decreases')
        event_type = EVENT_TYPES.get(outcome, 'field_out')
        events = []
        action_movements = []
        trailing_action_movements = []
        last_pitch_index = max((i for i, pitch in enumerate(record.get('pitches', []))
                                if pitch['code'] != 'A'), default=-1)
        event_outs = previous_outs
        balls, strikes = record.get('initial_count', [0, 0])
        for event_index, pitch in enumerate(record.get('pitches', [])):
            code = pitch['code']
            line = pitch['line']
            if not start <= line <= end:
                raise ValueError(f'Play {index}: pitch source {line} outside play range')
            if 'count' in pitch:
                balls, strikes = pitch['count']
            details = {'code': code, 'description': {
                'B': 'Ball', 'C': 'Called Strike', 'S': 'Swinging Strike',
                'F': 'Foul', 'X': 'In play', 'P': 'Pitchout', 'H': 'Hit By Pitch',
            }.get(code, pitch.get('description', 'Action')),
                'type': {'description': pitch.get('type', 'pitch')},
                'eventType': pitch.get('eventType', 'pitch'), 'zone': pitch.get('zone')}
            if pitch.get('location'):
                details['location'] = pitch['location']
            if code == 'U':
                details['description'] = pitch.get('description', 'Pitch')
                details['isStrike'] = pitch.get('isStrike', False)
            event = {'isPitch': code != 'A', 'index': event_index,
                     'details': details, 'count': {'balls': balls, 'strikes': strikes, 'outs': event_outs},
                     'isBunt': pitch.get('isBunt', False), 'pitchData': {},
                     'sourceLine': line}
            if code == 'A':
                action_type = details['eventType']
                details['description'] = {
                    'stolen_base': 'Stolen base', 'caught_stealing': 'Caught stealing',
                    'pickoff_attempt': 'Pickoff attempt', 'pickoff': 'Pickoff',
                    'wild_pitch': 'Wild pitch', 'passed_ball': 'Passed ball', 'balk': 'Balk',
                }.get(action_type, 'Action')
                details['runners'] = [
                    dict(runner=person(movement['name']), fromBase=movement.get('start'),
                         toBase=movement.get('end'), isOut=movement.get('out', False))
                    for movement in pitch.get('runners', [])
                ]
                if details['runners']:
                    details.update(details['runners'][0])
                for movement in pitch.get('runners', []):
                    target = (trailing_action_movements if event_index > last_pitch_index
                              and outcome != 'Incomplete' else action_movements)
                    target.append(copy.deepcopy(movement))
                    event_outs += bool(movement.get('out'))
                    for base, name in list(bases.items()):
                        if name == movement['name']:
                            del bases[base]
                    if not movement.get('out') and movement.get('end') in ('1B', '2B', '3B'):
                        bases[movement['end']] = movement['name']
            if code == 'X':
                event['hitData'] = copy.deepcopy(record.get('hit', {}))
            if 'commentaryRng' in pitch:
                event['commentaryRng'] = copy.deepcopy(pitch['commentaryRng'])
            events.append(event)
            if code in ('B', 'P'):
                balls += 1
            elif code in ('C', 'S') or (code == 'U' and details.get('isStrike')) or (code == 'F' and (strikes < 2 or event['isBunt'])):
                strikes += 1
                if strikes == 3 and outcome == 'Strikeout':
                    batter_safe = any(movement['name'] == record['batter'] and not movement.get('out')
                                      for movement in record.get('runners', []))
                    if not batter_safe:
                        event_outs += 1

        movements = copy.deepcopy(record.get('runners', []))
        if not any(runner['name'] == record['batter'] for runner in movements) and outcome != 'Incomplete':
            safe_base = HIT_BASES.get(outcome)
            movements.append({'name': record['batter'], 'start': None,
                              'end': safe_base, 'out': safe_base is None})
        # Forced advances are rules-derived facts; discretionary advances must
        # come from the reviewed ledger instead of being invented by a simulator.
        if outcome in ('Walk', 'Intentional Walk', 'Hit By Pitch'):
            for origin, destination in [('3B', 'score'), ('2B', '3B'), ('1B', '2B')]:
                occupied = all(base in bases for base in ('1B', '2B', '3B')[:int(origin[0])])
                if occupied and not any(r['name'] == bases[origin] for r in movements):
                    movements.insert(0, {'name': bases[origin], 'start': origin, 'end': destination})
        if outcome == 'Home Run':
            for origin, name in bases.items():
                if not any(r['name'] == name for r in movements):
                    movements.insert(0, {'name': name, 'start': origin, 'end': 'score'})
        # Include intermediate action movements once, followed by the terminal
        # play's movements. A steal and a later score must remain two movements.
        def movement_key(movement):
            return (movement['name'], movement.get('start'), movement.get('end'), movement.get('out', False))
        terminal_movements = {movement_key(movement) for movement in movements}
        movements = ([movement for movement in action_movements if movement_key(movement) not in terminal_movements]
                     + movements
                     + [movement for movement in trailing_action_movements if movement_key(movement) not in terminal_movements])
        fielders = record.get('fielders', [])
        credits = []
        for i, fielder in enumerate(fielders):
            credit = 'fielding'
            if outs > previous_outs:
                caught = outcome in ('Flyout', 'Pop Out', 'Lineout', 'Sac Fly')
                putout = i == len(fielders) - 1 and (caught or fielder['position'] == '1B')
                credit = 'putout' if putout else 'assist'
            if outcome == 'Field Error' and i == 0:
                credit = 'fielding_error'
            credits.append({'player': person(fielder['name'], fielder['position']),
                            'position': position(fielder['position']), 'credit': credit})
        runners = []
        out_number = previous_outs
        for movement in movements:
            if movement.get('out'):
                out_number += 1
            runners.append({'movement': {
                'start': movement.get('start'), 'originBase': movement.get('start'),
                'end': None if movement.get('out') else movement.get('end'),
                'outBase': movement.get('end') if movement.get('out') else None,
                'isOut': movement.get('out', False),
                'outNumber': out_number if movement.get('out') else None,
            }, 'details': {'runner': person(movement['name']), 'event': outcome,
                           'eventType': event_type, 'isScoringEvent': movement.get('end') == 'score' and not movement.get('out')},
                'credits': copy.deepcopy(credits)})
        for movement in movements:
            for base, occupant in list(bases.items()):
                if occupant == movement['name']:
                    del bases[base]
        final_movements = {movement['name']: movement for movement in movements}
        for movement in final_movements.values():
            if not movement.get('out') and movement.get('end') in ('1B', '2B', '3B'):
                bases[movement['end']] = movement['name']
        matchup = {'batter': batter, 'pitcher': pitcher,
                   'batSide': players[f'ID{batter["id"]}']['batSide'],
                   'pitchHand': hand(record.get('pitch_hand', 'U'))}
        for base, suffix in [('1B', 'First'), ('2B', 'Second'), ('3B', 'Third')]:
            if base in bases:
                matchup[f'postOn{suffix}'] = person(bases[base])
        batting_index = 0 if half[1] else 1
        observed_scorers = sum(movement.get('end') == 'score' and not movement.get('out')
                               for movement in final_movements.values())
        runs = score[batting_index] - previous_score[batting_index]
        # A scoreboard after a missing inning is not evidence that this batter
        # drove in those runs. Only explicitly observed scoring counts here.
        if coverage_gap:
            runs = min(runs, observed_scorers)
        non_batted_scoring = any(event['details']['eventType'] in
                                 ('wild_pitch', 'passed_ball', 'balk', 'stolen_base_home')
                                 for event in events)
        inferred_rbi = runs if (outcome not in ('Incomplete', 'Field Error', 'Double Play', 'Reached Base', 'Strikeout')
                                and not record.get('errors') and not non_batted_scoring) else 0
        rbi = record.get('rbi', inferred_rbi)
        if type(rbi) is not int or not 0 <= rbi <= runs:
            raise ValueError(f'Play {index}: RBI must be between zero and observed runs')
        play = {'about': {'inning': half[0], 'isTopInning': half[1],
                          'halfInning': 'top' if half[1] else 'bottom',
                          'atBatIndex': index, 'isComplete': outcome != 'Incomplete',
                          'coverageGapBefore': coverage_gap,
                          'isScoringPlay': bool(runs)},
                'matchup': matchup, 'result': {'event': outcome, 'eventType': event_type,
                'awayScore': score[0], 'homeScore': score[1], 'rbi': rbi},
                'count': {'balls': balls, 'strikes': strikes, 'outs': outs},
                'playEvents': events, 'runners': runners,
                'source': {'start': start, 'end': end}}
        play['result']['isWalkoff'] = bool(
            ledger.get('complete') and index == len(records) - 1 and not half[1]
            and score[1] > score[0] and previous_score[1] <= previous_score[0]
        )
        if 'commentaryRng' in record:
            play['commentaryRng'] = copy.deepcopy(record['commentaryRng'])
        plays.append(play)
        side = 'away' if half[1] else 'home'
        totals[side]['hits'] += outcome in ('Hit', 'Single', 'Double', 'Triple', 'Home Run')
        totals['home' if half[1] else 'away']['errors'] += record.get('errors', int(outcome == 'Field Error'))
        previous_outs, previous_score = outs, list(score)
    for i, side in enumerate(('away', 'home')):
        totals[side]['runs'] = previous_score[i]
    return {'gameData': {'commentarySeed': number, 'teams': teams, 'players': players,
             'game': {'scheduledInnings': game.get('scheduled_innings', 9)},
             'venue': game.get('venue', 'the ballpark'),
             'broadcast': {'network_name': 'Northwoods Baseball Radio Network',
                           'station_call': 'WSLP', 'complete': ledger.get('complete', False), 'strictFacts': True},
             'source': {'file': ledger['source_file'], 'sha256': hashlib.sha256(source_bytes).hexdigest()}},
            'liveData': {'plays': {'allPlays': plays}, 'boxscore': {'teams': boxes},
                         'linescore': {'teams': totals}}}


def build_all():
    from renderers import NarrativeRenderer

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(LEDGER_DIR.glob('episode_*.json')):
        ledger = json.loads(path.read_text())
        data = compile_game(ledger, (SOURCE_DIR / ledger['source_file']).read_bytes())
        (OUTPUT_DIR / path.name).write_text(json.dumps(data, indent=2) + '\n')
        (OUTPUT_DIR / f'{path.stem}.txt').write_text(NarrativeRenderer(data).render())
        print(f'{path.stem}: {len(data["liveData"]["plays"]["allPlays"])} plays')


if __name__ == '__main__':
    build_all()
