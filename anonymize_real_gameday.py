#!/usr/bin/env python3
"""
Utility to anonymize real MLB gameday data for testing.

This script:
1. Takes real MLB gameday JSON and strips fields not present in our generated data
2. Replaces real player names/IDs with our fictional team players
3. Outputs a sanitized version that matches our schema

Usage:
    python anonymize_real_gameday.py real_gameday.json -o anonymized_gameday.json
"""

import json
import argparse
import random
import re
import unicodedata
from pathlib import Path
from teams import TEAMS
from commentary import GAME_CONTEXT


# Top-level constants (module scope)
IGNORED_EVENT_TYPES = {
    'game_advisory', 'batter_timeout', 'manager_challenge',
    'pitching_substitution', 'umpire_review',
    'pickoff_attempt', 'stolen_base', 'caught_stealing', 'wild_pitch',
    'passed_ball', 'defensive_indiff', 'game_delayed', 'game_resumed'
}

# Keep a conservative pitch code list (adjust to match your generator’s behavior)
PITCH_CODE_WHITELIST = {'B', 'C', 'S', 'X', 'F', 'D'}
# MLB pitch codes our generator never emits, folded onto the ones it does.
# Dropping them instead loses pitches mid-at-bat (a strikeout on a foul tip
# vanished; a run-scoring ball in play 'E' left the at-bat with no result).
# Hit-by-pitch ('H') stays dropped: the generator narrates no HBP pitch either.
PITCH_CODE_MAP = {'T': 'S', 'W': 'S', 'M': 'S', 'Q': 'S', 'O': 'S',
                  'L': 'F', 'R': 'F', 'E': 'X', 'D': 'X', '*B': 'B', 'V': 'B', 'I': 'B', 'P': 'B'}

SUBSTITUTION_TYPES = {'offensive_substitution', 'defensive_substitution', 'defensive_switch'}
POSITION_ACTIONS = SUBSTITUTION_TYPES | {'mound_visit'}

# Baserunning actions our renderer narrates, keyed by MLB eventType prefix.
# Dropping them left real innings visibly broken (an inning ending mid-at-bat
# on an unnarrated caught stealing, runners appearing from nowhere).
SCORER_POSITIONS = {'1': 'P', '2': 'C', '3': '1B', '4': '2B', '5': '3B', '6': 'SS',
                    '7': 'LF', '8': 'CF', '9': 'RF'}

# Extra names stay in one team's vocabulary. Their combinations are reserved
# by position and handedness so the same name never changes roles across games.
OVERFLOW = {
    'home': ['Dale Whitcomb', 'Ray Pellerin', 'Tommy Askew', 'Luis Ocampo', 'Brent Haddix',
             'Curtis Vane', 'Mel Strand', 'Danny Ruehl', 'Hector Lasso', 'Gil Marchetti',
             'Wade Kimbrell', 'Nico Ferrante', 'Jay Tolliver', 'Ozzie Quill', 'Russ Delacroix'],
    'away': ['Earl Brannock', 'Sid Fennimore', 'Rafael Cuenca', 'Lyle Gessner', 'Mickey Dorr',
             'Arturo Velez', 'Hal Pruitt', 'Kip Lindqvist', 'Doug Sarratt', 'Benny Ochoa',
             'Clay Rourke', 'Manny Ybarra', 'Glen Hutchins', 'Theo Brakefield', 'Abe Calloway'],
}
EXTRA_SURNAMES = {
    'home': ['Hollis', 'Bellamy', 'Caldwell', 'Dunlap', 'Ellery', 'Fossett', 'Garrick', 'Huxley',
             'Ivers', 'Jardine', 'Kessler', 'Lennox', 'Merritt', 'Norvell', 'Ormsby', 'Prescott',
             'Ransome', 'Selwyn', 'Trask', 'Ulmer', 'Valence', 'Winslow', 'Yarrow', 'Zeller',
             'Bramwell', 'Cresswell', 'Dewitt', 'Easton', 'Finlay', 'Haverford'],
    'away': ['Ashby', 'Bancroft', 'Carrigan', 'Darrow', 'Eddings', 'Farnham', 'Godwin', 'Harwood',
             'Ingram', 'Jeffers', 'Kendrick', 'Langford', 'Mayhew', 'Nesbitt', 'Oglesby', 'Penrose',
             'Radford', 'Somerfield', 'Thurston', 'Underhill', 'Varden', 'Walden', 'Yates', 'Zane',
             'Beckford', 'Colter', 'Densmore', 'Everton', 'Farrow', 'Holtby'],
}


def player_sides(data):
    """Infer teams for hitters, runners and fielders, including men who never bat."""
    sides = {}
    box_teams = data.get('liveData', {}).get('boxscore', {}).get('teams', {})
    for side in ('home', 'away'):
        for player in box_teams.get(side, {}).get('players', {}).values():
            pid = player.get('person', {}).get('id')
            if pid is not None:
                sides[pid] = side
    for play in data.get('liveData', {}).get('plays', {}).get('allPlays', []):
        batting, fielding = ('away', 'home') if play['about']['isTopInning'] else ('home', 'away')
        for role, side in (('batter', batting), ('pitcher', fielding)):
            person = play.get('matchup', {}).get(role, {})
            if person.get('id') is not None:
                sides[person['id']] = side
        for runner in play.get('runners', []):
            person = runner.get('details', {}).get('runner', {})
            if person.get('id') is not None:
                sides[person['id']] = batting
            for credit in runner.get('credits', []):
                if credit.get('player', {}).get('id') is not None:
                    sides[credit['player']['id']] = fielding
        for event in play.get('playEvents', []):
            kind = event.get('details', {}).get('eventType', '')
            if kind in ('offensive_substitution', 'runner_placed'):
                side = batting
            elif kind in ('defensive_substitution', 'defensive_switch', 'pitching_substitution'):
                side = fielding
            else:
                continue
            for role in ('player', 'replacedPlayer'):
                if event.get(role, {}).get('id') is not None:
                    sides[event[role]['id']] = side
    return sides


def _position_code(position):
    code = (position or {}).get('code', 'U')
    return 'D' if code == '10' else code


def _extra_names(side, code, hand):
    positions = ('1', '2', '3', '4', '5', '6', '7', '8', '9', 'D', 'U', '11', '12')
    hands = ('R', 'L', 'S', 'U')
    bucket = positions.index(code if code in positions else 'U') * len(hands)
    bucket += hands.index(hand if hand in hands else 'U')
    stride = len(positions) * len(hands)
    firsts = list(dict.fromkeys([name.split()[0] for names in OVERFLOW.values() for name in names]
                               + [p['legal_name'].split()[0] for key in ('BAY_BOMBERS', 'PC_PILOTS')
                                  for p in TEAMS[key]['players']]))
    lasts = [name.split()[-1] for name in OVERFLOW[side]] + EXTRA_SURNAMES[side]
    for i in range(bucket, len(firsts) * len(lasts), stride):
        yield f'{firsts[i % len(firsts)]} {lasts[i // len(firsts)]}'


def _check_unique_player_names(names, label):
    owners, surnames = {}, {}
    for pid, name in names.items():
        for value, seen in ((name, owners), (name.split()[-1], surnames)):
            key = normalize_unicode(value).casefold()
            if key in seen and seen[key] != pid:
                raise ValueError(f'{label}: fictional name {value!r} belongs to players {seen[key]} and {pid}')
            seen[key] = pid


def validate_player_names(data, label='game'):
    """Fail before rendering if two players share a name or a reference drifts."""
    players = {}
    for player in data.get('gameData', {}).get('players', {}).values():
        pid, name = player['id'], player['fullName']
        if pid in players and players[pid] != name:
            raise ValueError(f'{label}: player {pid} has names {players[pid]!r} and {name!r}')
        players[pid] = name
    _check_unique_player_names(players, label)

    def check(node):
        if isinstance(node, dict):
            if 'id' in node and ('fullName' in node or len(node) <= 3):
                pid = node['id']
                if pid not in players:
                    raise ValueError(f'{label}: player {pid} is referenced but missing from gameData.players')
                if node.get('fullName', players[pid]) != players[pid]:
                    raise ValueError(f'{label}: player {pid} is named {node["fullName"]!r}, expected {players[pid]!r}')
            for value in node.values():
                check(value)
        elif isinstance(node, list):
            for value in node:
                check(value)

    check(data.get('liveData', {}).get('plays', {}).get('allPlays', []))


def collect_players(data):
    """Include substitutes and references that have no gameData roster entry."""
    players = {p['id']: dict(p) for p in data.get('gameData', {}).get('players', {}).values()}

    def collect(node):
        if isinstance(node, dict):
            if 'id' in node and ('fullName' in node or len(node) <= 3):
                person = players.setdefault(node['id'], {'id': node['id']})
                if node.get('fullName'):
                    person.setdefault('fullName', node['fullName'])
            for value in node.values():
                collect(value)
        elif isinstance(node, list):
            for value in node:
                collect(value)

    plays = data.get('liveData', {}).get('plays', {}).get('allPlays', [])
    collect(plays)
    for play in plays:
        for role, hand in (('batter', 'batSide'), ('pitcher', 'pitchHand')):
            ref = play.get('matchup', {}).get(role)
            if ref and ref['id'] in players and hand in play['matchup']:
                players[ref['id']].setdefault(hand, play['matchup'][hand])
    for team in data.get('liveData', {}).get('boxscore', {}).get('teams', {}).values():
        for box_player in team.get('players', {}).values():
            pid = box_player.get('person', {}).get('id')
            if pid in players and box_player.get('position'):
                position = dict(box_player['position'])
                position['code'] = _position_code(position)
                players[pid]['primaryPosition'] = position
    for play in plays:
        for runner in play.get('runners', []):
            for credit in runner.get('credits', []):
                pid = credit.get('player', {}).get('id')
                if pid in players and credit.get('position'):
                    players[pid].setdefault('primaryPosition', credit['position'])
        for event in play.get('playEvents', []):
            pid = event.get('player', {}).get('id')
            if pid in players and event.get('position'):
                players[pid].setdefault('primaryPosition', event['position'])
    for person in players.values():
        if person.get('primaryPosition'):
            person['primaryPosition'] = {**person['primaryPosition'], 'code': _position_code(person['primaryPosition'])}
    return players


def assign_player_names(data, our_teams, rng):
    """Use a roster name only when its team, position and hand fit the player."""
    players = collect_players(data)
    plays = data.get('liveData', {}).get('plays', {}).get('allPlays', [])
    order = list(dict.fromkeys([p['matchup'][role]['id'] for p in plays
                                for role in ('batter', 'pitcher')] + sorted(players)))
    sides = player_sides(data)
    positions = {pid: {_position_code(p.get('primaryPosition'))} for pid, p in players.items()}
    for play in plays:
        for runner in play.get('runners', []):
            for credit in runner.get('credits', []):
                pid = credit.get('player', {}).get('id')
                if pid in positions and credit.get('position'):
                    positions[pid].add(_position_code(credit['position']))
    names, used, used_surnames = {}, set(), set()
    for side, key in (('home', 'BAY_BOMBERS'), ('away', 'PC_PILOTS')):
        roster = list(our_teams[key]['players'])
        starter = next((p for p in roster if p.get('type') == 'Starter'), None)
        pen = [p for p in roster if p['position']['code'] == '1' and p is not starter]
        rng.shuffle(pen)
        pitcher_order = ([starter] if starter else []) + pen
        pools = {}
        for pid in order:
            if pid not in players or sides.get(pid, 'home') != side:
                continue
            person = players[pid]
            code = _position_code(person.get('primaryPosition'))
            hand_key = 'pitchHand' if code == '1' else 'batSide'
            hand = person.get(hand_key, {}).get('code', 'U')
            candidates = pitcher_order if code == '1' else roster
            match = next((p for p in candidates if p['legal_name'] not in used
                          and p['legal_name'].split()[-1] not in used_surnames
                          and positions[pid] == {p['position']['code']}
                          and p.get(hand_key, {}).get('code', 'R') == hand), None)
            if match:
                name = match['legal_name']
            else:
                pool = pools.setdefault((code, hand), _extra_names(side, code, hand))
                name = next(n for n in pool if n not in used and n.split()[-1] not in used_surnames)
            names[pid] = name
            used.add(name)
            used_surnames.add(name.split()[-1])
    _check_unique_player_names(names, 'player assignment')
    return names

ACTION_TYPES = (('stolen_base', 'stolen_base'), ('pickoff_caught_stealing', 'caught_stealing'),
                ('caught_stealing', 'caught_stealing'), ('pickoff_error', 'pickoff_attempt'),
                ('pickoff', 'pickoff'), ('wild_pitch', 'wild_pitch'), ('passed_ball', 'passed_ball'),
                ('defensive_indiff', 'defensive_indiff'), ('forced_balk', 'balk'), ('balk', 'balk'),
                ('error', 'runner_advance'), ('field_error', 'runner_advance'),
                ('other_advance', 'runner_advance'))


def runner_action_type(event_type):
    return next((ours for prefix, ours in ACTION_TYPES if event_type.startswith(prefix)), None)


def action_movements(runners, index, id_mapping, default_kind=None):
    movements = []
    for runner in runners:
        details, movement = runner.get('details', {}), runner.get('movement', {})
        if details.get('playIndex') != index or not details.get('runner'):
            continue
        start = movement.get('start') or movement.get('originBase')
        end = movement.get('end') or movement.get('outBase')
        if start == end and not movement.get('isOut'):
            continue
        kind = runner_action_type(details.get('eventType', '')) or default_kind
        if not kind:
            continue
        if kind in ('caught_stealing', 'pickoff') and not movement.get('isOut'):
            # The feed can label every runner with the play's out, even the
            # man who scored while a different runner was caught stealing.
            kind = 'runner_advance'
            if (details.get('eventType', '').startswith('pickoff')
                    and any('error' in credit.get('credit', '') for credit in runner.get('credits', []))):
                kind = 'pickoff_attempt'
        elif kind == 'stolen_base' and movement.get('isOut'):
            kind = 'caught_stealing'
        person = anonymize_player_reference(details['runner'], id_mapping)
        pickoff = details.get('eventType', '').startswith('pickoff_caught_stealing')
        # Two rows can describe successive bases on the same advance. Keep
        # distinct steps when a steal is followed by an error on the throw.
        previous = next((m for m in movements if m['runner']['id'] == person['id']
                         and m['eventType'] == kind and m['toBase'] == start), None)
        if previous:
            previous['toBase'] = end
            previous['isOut'] = bool(movement.get('isOut'))
        else:
            movements.append({'runner': person, 'fromBase': start, 'toBase': end,
                              'isOut': bool(movement.get('isOut')), 'eventType': kind,
                              'reason': 'error' if (details.get('eventType') in ('error', 'field_error')
                                                    or any('error' in credit.get('credit', '') for credit in runner.get('credits', []))) else '',
                              **({'pickoff': True} if pickoff else {})})
    return movements


def action_type(ev: dict):
    """Our eventType for a real baserunning action event, or None."""
    if ev.get('isPitch'):
        return None
    d = ev.get('details') or {}
    real = d.get('eventType') or ''
    if not real and (ev.get('type') == 'pickoff' or 'pickoff attempt' in (d.get('description') or '').lower()):
        return 'pickoff_attempt'
    return runner_action_type(real)


def is_pitch_like(ev: dict) -> bool:
    d = (ev.get('details') or {})
    if d.get('eventType') in IGNORED_EVENT_TYPES:
        return False
    # Require pitchData present (non-pitch events rarely have it)
    if not ev.get('pitchData'):
        return False
    # If a code exists, clamp to a small set your generator would produce
    code = d.get('code')
    return (PITCH_CODE_MAP.get(code, code) in PITCH_CODE_WHITELIST) if code else True


def normalize_unicode(text):
    """Remove accents and other diacritical marks from text."""
    if not text:
        return text
    # Decompose unicode characters and filter out combining marks
    normalized = unicodedata.normalize('NFD', text)
    return ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')


def get_our_schema_fields():
    """
    Define the fields present in our generated gameday JSON.
    This is the allowlist of fields to keep from real MLB data.
    """
    return {
        'gameData': {
            'teams': {
                'away': ['id', 'name', 'abbreviation', 'teamName'],
                'home': ['id', 'name', 'abbreviation', 'teamName']
            },
            'players': None,  # Full dict of player details
            'venue': None,
            'weather': None,
            'umpires': None
        },
        'liveData': {
            'plays': {
                'allPlays': {
                    'result': ['type', 'event', 'rbi', 'awayScore', 'homeScore'],
                    'about': ['atBatIndex', 'halfInning', 'isTopInning', 'inning', 'isScoringPlay'],
                    'count': ['balls', 'strikes', 'outs'],
                    'matchup': ['batter', 'batSide', 'pitcher', 'pitchHand', 'batterHotColdZones', 'pitcherHotColdZones', 'splits', 'postOnFirst', 'postOnSecond', 'postOnThird'],
                    'playEvents': {
                        'index': None,
                        'count': ['balls', 'strikes'],
                        'details': ['code', 'description', 'isStrike', 'type', 'eventType'],
                        'pitchData': ['startSpeed', 'breaks', 'zone'],
                        'hitData': ['launchSpeed', 'launchAngle', 'trajectory', 'location', 'hardness',
                                    'totalDistance', 'coordinates'],
                        'isBunt': None
                    },
                    'runners': {
                        'movement': None,
                        'details': ['event', 'eventType', 'movementReason', 'runner', 'responsiblePitcher', 'isScoringEvent', 'rbi', 'earned', 'teamUnearned', 'playIndex'],
                        'credits': {
                            'player': ['id'],
                            'credit': None,
                            'position': ['code', 'name', 'abbreviation']
                        }
                    }
                }
            },
            'linescore': ['currentInning', 'isTopInning', 'inningState', 'outs', 'balls', 'strikes', 'teams', 'innings']
        }
    }


def create_player_mapping(real_data, our_teams, rng=None):
    """Assign unique fictional identities while retaining the real roles and hands."""
    players = collect_players(real_data)
    context = {'gameData': {'players': {f'ID{pid}': p for pid, p in players.items()}},
               'liveData': real_data.get('liveData', {})}
    names = assign_player_names(context, our_teams, rng or random.Random(42))
    _check_unique_player_names(names, 'player mapping')
    canonical = {p['legal_name']: p for team in our_teams.values() for p in team['players']}
    id_mapping, name_mapping = {}, {}
    for i, (real_id, person) in enumerate(sorted(players.items())):
        name = names[real_id]
        replacement = {'id': canonical[name]['id'] if name in canonical else 9000000 + i,
                       'legal_name': name}
        for source, target in (('primaryPosition', 'position'), ('batSide', 'batSide'), ('pitchHand', 'pitchHand')):
            if person.get(source):
                replacement[target] = person[source]
        id_mapping[real_id] = replacement
        real_name = person.get('fullName', '')
        if real_name:
            name_mapping[real_name] = name
            name_mapping[normalize_unicode(real_name)] = name
            parts = real_name.split()
            if len(parts) >= 2:
                for old, new in ((parts[0], name.split()[0]), (parts[-1], name.split()[-1])):
                    name_mapping[old] = new
                    name_mapping[normalize_unicode(old)] = new
    if len({p['id'] for p in id_mapping.values()}) != len(id_mapping):
        raise ValueError('player mapping: fictional player IDs must be unique')
    return id_mapping, name_mapping


def generate_player_detail(player):
    """
    Generate a full player details object for a given fictional player.
    Matches the logic in baseball.py _initialize_game_data_players.
    """
    pid = player['id']
    full_name = player['legal_name']
    name_parts = full_name.split(' ')
    first_name = name_parts[0]
    last_name = name_parts[-1] if len(name_parts) > 1 else ""
    middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else ""

    # Mock realistic bio data deterministically based on ID
    rng = random.Random(pid)

    birth_year = rng.randint(1995, 2003)
    birth_month = rng.randint(1, 12)
    birth_day = rng.randint(1, 28)
    birth_date = f"{birth_year}-{birth_month:02d}-{birth_day:02d}"
    current_age = 2025 - birth_year

    height_feet = rng.randint(5, 6)
    height_inches = rng.randint(0, 11)
    if height_feet == 6: height_inches = rng.randint(0, 8)
    height = f"{height_feet}' {height_inches}\""

    weight = rng.randint(170, 240)

    draft_year = birth_year + 18 + rng.randint(0, 3)
    debut_year = draft_year + rng.randint(2, 5)
    debut_date = f"{debut_year}-04-01"

    # Handle position if missing (synthetic players)
    position = player.get('position', {'code': 'U', 'name': 'Utility', 'abbreviation': 'UT'})

    return {
        "id": pid,
        "fullName": full_name,
        "link": f"/api/v1/people/{pid}",
        "firstName": first_name,
        "lastName": last_name,
        "primaryNumber": str(pid % 100),
        "birthDate": birth_date,
        "currentAge": current_age,
        "birthCity": "Sim City",
        "birthStateProvince": "CA",
        "birthCountry": "USA",
        "height": height,
        "weight": weight,
        "active": True,
        "primaryPosition": position,
        "useName": player.get('nickname', first_name) or first_name,
        "useLastName": last_name,
        "middleName": middle_name,
        "boxscoreName": last_name,
        "gender": "M",
        "isPlayer": True,
        "isVerified": False,
        "draftYear": draft_year,
        "mlbDebutDate": debut_date,
        "batSide": player.get('batSide', {'code': 'R', 'description': 'Right'}),
        "pitchHand": player.get('pitchHand', {'code': 'R', 'description': 'Right'}),
        "strikeZoneTop": 3.5,
        "strikeZoneBottom": 1.5
    }


def filter_dict(data, allowed_fields):
    """
    Recursively filter a dictionary to only include allowed fields.

    Args:
        data: Dict to filter
        allowed_fields: List of field names or dict of nested structure

    Returns:
        Filtered dict
    """
    if isinstance(allowed_fields, list):
        # Simple list of allowed keys
        return {k: data[k] for k in allowed_fields if k in data}
    elif isinstance(allowed_fields, dict):
        # Nested structure
        result = {}
        for key, subfields in allowed_fields.items():
            if key not in data:
                continue

            if subfields is None:
                # Keep as-is
                result[key] = data[key]
            elif isinstance(data[key], dict):
                result[key] = filter_dict(data[key], subfields)
            elif isinstance(data[key], list):
                result[key] = [filter_dict(item, subfields) if isinstance(item, dict) else item
                              for item in data[key]]
            else:
                result[key] = data[key]
        return result
    else:
        return data


def anonymize_player_reference(player_ref, id_mapping):
    if not player_ref or 'id' not in player_ref:
        return player_ref
    real_id = player_ref['id']
    mapped = id_mapping.get(real_id)
    return {'id': mapped['id'], 'fullName': mapped['legal_name']} if mapped else {'id': real_id}


def _case_like(src: str, repl: str) -> str:
    if src.isupper(): return repl.upper()
    if src.istitle(): return repl.title()
    if src.islower(): return repl.lower()
    return repl

def anonymize_description(text: str, name_mapping: dict) -> str:
    if not text or not name_mapping:
        return text
    names = '|'.join(re.escape(name) for name in sorted(name_mapping, key=len, reverse=True))
    pattern = re.compile(rf"(?<!\w)({names})(?!\w)(['’]s)?", re.IGNORECASE)
    mapping = {name.lower(): fake for name, fake in name_mapping.items()}
    # Replace once: a fictional surname can also be another real player's name.
    return pattern.sub(lambda m: _case_like(m[1], mapping[m[1].lower()]) + (m[2] or ''), text)


def simplify_runner(r, id_mapping, schema):
    """Process a runner entry, anonymizing player references and filtering to schema."""
    out = {}

    if 'movement' in r:
        out['movement'] = r['movement']

    if 'details' in r:
        # Filter to allowed fields from schema
        allowed_detail_fields = schema['liveData']['plays']['allPlays']['runners']['details']
        d = {}
        for field in allowed_detail_fields:
            if field in r['details']:
                value = r['details'][field]
                # Anonymize player references
                if field == 'runner':
                    value = anonymize_player_reference(value, id_mapping)
                elif field == 'responsiblePitcher':
                    value = anonymize_player_reference(value, id_mapping)
                d[field] = value
        out['details'] = d

    if 'credits' in r:
        out['credits'] = []
        for credit in r['credits']:
            anon_credit = {}
            if 'player' in credit:
                anon_credit['player'] = anonymize_player_reference(credit['player'], id_mapping)
            if 'credit' in credit:
                anon_credit['credit'] = credit['credit'].removeprefix('f_')
            if 'position' in credit:
                anon_credit['position'] = credit['position']
            out['credits'].append(anon_credit)

    return out


def anonymize_gameday_data(real_data, our_teams, seed=42):
    """
    Anonymize real gameday data by replacing players and filtering fields.

    Args:
        real_data: Real MLB gameday JSON
        our_teams: Our TEAMS dictionary
        seed: Random seed for context generation

    Returns:
        Anonymized gameday JSON
    """
    rng = random.Random(seed)

    # Create player mappings
    id_mapping, name_mapping = create_player_mapping(real_data, our_teams, rng)

    # Get schema
    schema = get_our_schema_fields()

    # Filter top-level structure
    result = {}

    # Handle gameData
    if 'gameData' in real_data and 'gameData' in schema:
        result['gameData'] = {}

        # Teams
        if 'teams' in real_data['gameData']:
            result['gameData']['teams'] = {}
            for side in ['home', 'away']:
                if side in real_data['gameData']['teams']:
                    team = real_data['gameData']['teams'][side]
                    # Use our team data
                    our_team = our_teams['BAY_BOMBERS'] if side == 'home' else our_teams['PC_PILOTS']
                    result['gameData']['teams'][side] = {
                        'id': our_team['id'],
                        'name': our_team['name'],
                        'abbreviation': our_team['abbreviation'],
                        'teamName': our_team['teamName'],
                        'locationName': our_team.get('locationName', ''),
                        'state': our_team.get('state', ''),
                        **{key: our_team[key] for key in ('spokenLocation', 'spokenLocationWithState')
                           if key in our_team},
                    }

        # Context: Venue, Weather, Umpires
        result['gameData']['venue'] = our_teams['BAY_BOMBERS']['venue']
        result['gameData']['weather'] = rng.choice(GAME_CONTEXT["weather_conditions"])
        result['gameData']['umpires'] = rng.sample(GAME_CONTEXT["umpires"], 4)

        # Players
        result['gameData']['players'] = {}
        # Iterate over all mapped players to populate the players dictionary
        # We use id_mapping.values() which contains the fictional player objects
        # To avoid duplicates, we track IDs we've added
        added_ids = set()

        # But wait, id_mapping keys are REAL IDs. Values are FICTIONAL players.
        # We need to make sure we include all players referenced in the game.
        # The id_mapping covers all players found in real_gameday.

        for fictional_player in id_mapping.values():
            if fictional_player['id'] in added_ids:
                continue

            player_detail = generate_player_detail(fictional_player)
            pid_key = f"ID{fictional_player['id']}"
            result['gameData']['players'][pid_key] = player_detail
            added_ids.add(fictional_player['id'])


    # Handle liveData
    if 'liveData' in real_data and 'liveData' in schema:
        result['liveData'] = {}

        # Handle plays
        if 'plays' in real_data['liveData']:
            result['liveData']['plays'] = {'allPlays': []}

            for play in real_data['liveData']['plays'].get('allPlays', []):
                anonymized_play = {}

                # Filter result
                if 'result' in play:
                    anonymized_play['result'] = filter_dict(play['result'], schema['liveData']['plays']['allPlays']['result'])

                # Filter about
                if 'about' in play:
                    anonymized_play['about'] = filter_dict(play['about'], schema['liveData']['plays']['allPlays']['about'])

                # Filter count
                if 'count' in play:
                    anonymized_play['count'] = filter_dict(play['count'], schema['liveData']['plays']['allPlays']['count'])

                # Handle matchup with player anonymization
                if 'matchup' in play:
                    matchup = play['matchup']
                    anonymized_play['matchup'] = {}

                    # Anonymize batter
                    if 'batter' in matchup:
                        anonymized_play['matchup']['batter'] = anonymize_player_reference(matchup['batter'], id_mapping)

                    # Keep batSide
                    if 'batSide' in matchup:
                        anonymized_play['matchup']['batSide'] = matchup['batSide']

                    # Anonymize pitcher
                    if 'pitcher' in matchup:
                        anonymized_play['matchup']['pitcher'] = anonymize_player_reference(matchup['pitcher'], id_mapping)

                    # Keep pitchHand
                    if 'pitchHand' in matchup:
                        anonymized_play['matchup']['pitchHand'] = matchup['pitchHand']

                    # Keep empty arrays and splits
                    anonymized_play['matchup']['batterHotColdZones'] = []
                    anonymized_play['matchup']['pitcherHotColdZones'] = []

                    if 'splits' in matchup:
                        anonymized_play['matchup']['splits'] = matchup['splits']

                    # Handle postOn bases
                    for base in ['postOnFirst', 'postOnSecond', 'postOnThird']:
                        if base in matchup:
                            anonymized_play['matchup'][base] = anonymize_player_reference(matchup[base], id_mapping)

                # Filter playEvents
                if 'playEvents' in play:
                    events = [e for e in play['playEvents'] if action_type(e) or is_pitch_like(e)
                              or e.get('details', {}).get('eventType') in POSITION_ACTIONS]
                    # Optional: keep only terminal pitch to look even more generated:
                    # events = events[-1:]
                    anonymized_play['playEvents'] = []
                    # MLB records the count AFTER each pitch; our generator and
                    # renderer use the count the pitch was thrown in. Shift by one.
                    count_before = {'balls': 0, 'strikes': 0}
                    for event_number, event in enumerate(events):
                        kind = event.get('details', {}).get('eventType')
                        if kind in POSITION_ACTIONS:
                            filtered_event = {
                                'isPitch': False, 'type': 'action', 'index': event.get('index'),
                                'count': dict(count_before),
                                'details': {'eventType': kind, 'code': '', 'isStrike': False,
                                            'description': ''},
                            }
                            for field in ('isSubstitution', 'position', 'battingOrder'):
                                if field in event:
                                    filtered_event[field] = event[field]
                            for field in ('player', 'replacedPlayer'):
                                if field in event:
                                    filtered_event[field] = anonymize_player_reference(event[field], id_mapping)
                            anonymized_play['playEvents'].append(filtered_event)
                            continue
                        ours = action_type(event)
                        if ours:
                            if ours == 'pickoff_attempt':
                                rows = [r for r in play.get('runners', [])
                                        if r.get('details', {}).get('playIndex') == event.get('index')]
                                if rows and all(r.get('details', {}).get('runner', {}).get('id') == matchup.get('batter', {}).get('id')
                                                and r.get('details', {}).get('eventType') == 'strikeout' for r in rows):
                                    # A catcher finishing an uncaught third strike
                                    # can be logged as a pickoff throw to first.
                                    continue
                                following = events[event_number + 1] if event_number + 1 < len(events) else {}
                                base = (event.get('details', {}).get('code') or '') + 'B'
                                same_runner = any(r.get('details', {}).get('playIndex') == following.get('index')
                                                  and (r['movement'].get('start') or r['movement'].get('originBase')) == base
                                                  for r in play.get('runners', []))
                                if (not rows and action_type(following) in ('caught_stealing', 'pickoff')
                                        and not following.get('isPitch') and same_runner):
                                    # The next action supplies the result of this
                                    # throw; it is not a separate safe return.
                                    continue
                            movements = action_movements(play.get('runners', []), event.get('index'), id_mapping, ours)
                            if ours == 'caught_stealing' and any(m.get('pickoff') for m in movements):
                                # A break on a pickoff throw is not a steal on
                                # the preceding pitch, even when it follows it.
                                ours = ('pickoff_caught_stealing' if any(m.get('isOut') for m in movements)
                                        else 'pickoff_attempt')
                            if ours == 'pickoff_attempt' and not movements:
                                base = re.search(r'\b([123])B\b', (event.get('details') or {}).get('description') or '')
                                if base:
                                    movements.append({'fromBase': f'{base.group(1)}B', 'toBase': f'{base.group(1)}B', 'isOut': False})
                            anonymized_play['playEvents'].append({
                                'isPitch': False, 'index': event.get('index'), 'count': dict(count_before),
                                'details': {'eventType': ours, 'description': ours.replace('_', ' ').title(),
                                            'code': '', 'runners': movements}})
                            continue
                        filtered_event = {'isPitch': True}
                        if 'index' in event:
                            filtered_event['index'] = event['index']
                        filtered_event['count'] = dict(count_before)
                        if 'count' in event:
                            count_before = filter_dict(event['count'], ['balls', 'strikes'])
                        if 'details' in event:
                            details = {}
                            for field in ['code', 'description', 'isStrike']:
                                if field in event['details']:
                                    val = event['details'][field]
                                    if field == 'description':
                                        val = anonymize_description(val, name_mapping)
                                    elif field == 'code':
                                        val = PITCH_CODE_MAP.get(val, val)
                                    details[field] = val
                            # Remove MLB taxonomy fields that can leak lifecycle/type details
                            details.pop('eventType', None)
                            if 'type' in event['details']:
                                details['type'] = event['details']['type']
                            filtered_event['details'] = details

                        if 'pitchData' in event:
                            pd = {}
                            if 'startSpeed' in event['pitchData']:
                                pd['startSpeed'] = event['pitchData']['startSpeed']
                            if 'breaks' in event['pitchData'] and 'spinRate' in event['pitchData']['breaks']:
                                pd['breaks'] = {'spinRate': event['pitchData']['breaks']['spinRate']}
                            # The zone is where the pitch was, not who threw it. The
                            # renderer reads it from details, as the simulator writes it.
                            zone = event['pitchData'].get('zone')
                            if (isinstance(zone, int) and not isinstance(zone, bool) and 1 <= zone <= 14
                                    and 'details' in filtered_event):
                                pd['zone'] = zone
                                filtered_event['details']['zone'] = zone
                            filtered_event['pitchData'] = pd

                        if 'hitData' in event:
                            hd = {}
                            # Coordinates, distance and hardness are ball facts, not
                            # identities: the renderer derives depth and lane from
                            # them as the simulator does, so real and simulated
                            # balls are described alike.
                            for fld in ['launchSpeed', 'launchAngle', 'trajectory', 'location',
                                        'hardness', 'totalDistance', 'coordinates']:
                                if fld in event['hitData']:
                                    hd[fld] = event['hitData'][fld]
                            if 'location' in hd:
                                # StatsAPI codes the fielding spot as a scorer's
                                # number; the renderer's directions are keyed by
                                # position ("4" -> "to second").
                                hd['location'] = SCORER_POSITIONS.get(str(hd['location']), hd['location'])
                            filtered_event['hitData'] = hd

                        if 'isBunt' in event:
                            filtered_event['isBunt'] = event['isBunt']

                        anonymized_play['playEvents'].append(filtered_event)

                # A baserunning action can live only on the pitch's movement
                # rows. Insert it once, immediately after that pitch; movements
                # on a ball in play belong to the batted-ball call instead.
                covered = {e.get('index') for e in anonymized_play.get('playEvents', []) if not e.get('isPitch')}
                pitch_at = {e.get('index'): i for i, e in enumerate(anonymized_play.get('playEvents', [])) if e.get('isPitch')}
                for idx in sorted(pitch_at, key=pitch_at.get, reverse=True):
                    event = anonymized_play['playEvents'][pitch_at[idx]]
                    if idx in covered or event.get('details', {}).get('code') == 'X':
                        continue
                    movements = action_movements(play.get('runners', []), idx, id_mapping)
                    if not movements:
                        continue
                    kind = movements[0]['eventType']
                    anonymized_play['playEvents'].insert(pitch_at[idx] + 1, {
                        'isPitch': False, 'index': idx, 'count': dict(event.get('count', {})),
                        'details': {'eventType': kind, 'description': kind.replace('_', ' ').title(),
                                    'code': '', 'runners': movements}})

                # Handle runners
                if 'runners' in play:
                    anonymized_play['runners'] = [simplify_runner(r, id_mapping, schema) for r in play['runners']]

                # Result taxonomy
                if 'result' in anonymized_play:
                    anonymized_play['result'].pop('eventType', None)  # keep 'event' if you need it; otherwise consider removing too

                # Matchup: ensure only IDs and basic handedness/splits
                if 'matchup' in anonymized_play:
                    m = anonymized_play['matchup']
                    # Drop hot/cold zones if present (you set them to [])
                    m.pop('batterHotColdZones', None)
                    m.pop('pitcherHotColdZones', None)

                result['liveData']['plays']['allPlays'].append(anonymized_play)

        # Handle linescore (keep as-is if present)
        if 'linescore' in real_data['liveData']:
            ls = real_data['liveData']['linescore']
            result['liveData']['linescore'] = {}
            for field in schema['liveData']['linescore']:
                if field in ls:
                    result['liveData']['linescore'][field] = ls[field]

    validate_player_names(result, 'anonymized game')
    return result


def lifecycle_smoke_test(data):
    plays = data.get('liveData', {}).get('plays', {}).get('allPlays', [])
    bad = 0
    for p in plays:
        for ev in p.get('playEvents', []):
            et = (ev.get('details') or {}).get('eventType')
            if et in IGNORED_EVENT_TYPES:
                bad += 1
    print(f"Non-pitch/lifecycle events in playEvents: {bad}")


def main():
    parser = argparse.ArgumentParser(
        description='Anonymize real MLB gameday JSON for testing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('input_file', help='Real MLB gameday JSON file')
    parser.add_argument('-o', '--output', default='anonymized_gameday.json',
                       help='Output file (default: anonymized_gameday.json)')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for player assignment (default: 42)')

    args = parser.parse_args()

    # Set random seed for reproducibility
    random.seed(args.seed)

    # Load real data
    print(f"Loading {args.input_file}...")
    with open(args.input_file, 'r') as f:
        real_data = json.load(f)

    # Anonymize
    print("Anonymizing players and filtering fields...")
    anonymized = anonymize_gameday_data(real_data, TEAMS, seed=args.seed)

    # Write output
    print(f"Writing to {args.output}...")
    with open(args.output, 'w') as f:
        json.dump(anonymized, f, indent=2)

    # Print stats
    real_plays = len(real_data.get('liveData', {}).get('plays', {}).get('allPlays', []))
    anon_plays = len(anonymized.get('liveData', {}).get('plays', {}).get('allPlays', []))

    print(f"\n✓ Anonymization complete!")
    print(f"  Plays: {anon_plays}/{real_plays}")
    print(f"  Output: {args.output}")

    # After writing output:
    lifecycle_smoke_test(anonymized)


if __name__ == '__main__':
    main()
