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
import copy
from teams import TEAMS

# Top-level constants (module scope)
IGNORED_EVENT_TYPES = {
    'game_advisory', 'mound_visit', 'batter_timeout', 'manager_challenge',
    'pitching_substitution', 'defensive_switch', 'umpire_review',
    'pickoff_attempt', 'stolen_base', 'caught_stealing', 'wild_pitch',
    'passed_ball', 'defensive_indiff', 'game_delayed', 'game_resumed'
}

# Keep a conservative pitch code list
PITCH_CODE_WHITELIST = {'B', 'C', 'S', 'X', 'F', 'D'}

def is_pitch_like(ev: dict) -> bool:
    d = (ev.get('details') or {})
    if d.get('eventType') in IGNORED_EVENT_TYPES:
        return False
    if not ev.get('pitchData'):
        return False
    code = d.get('code')
    return code in PITCH_CODE_WHITELIST if code else True


def normalize_unicode(text):
    if not text:
        return text
    normalized = unicodedata.normalize('NFD', text)
    return ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')


def get_our_schema_fields():
    return {
        'gameData': {
            'teams': {
                'away': ['id', 'name', 'abbreviation', 'teamName'],
                'home': ['id', 'name', 'abbreviation', 'teamName']
            },
            'players': None,
            'venue': ['name', 'id'],
            'weather': ['condition', 'temp', 'wind'],
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
                        'pitchData': ['startSpeed', 'breaks'],
                        'hitData': ['launchSpeed', 'launchAngle', 'trajectory'],
                        'isBunt': None
                    },
                    'runners': {
                        'movement': None,
                        'details': ['event', 'eventType', 'movementReason', 'runner', 'responsiblePitcher', 'isScoringEvent', 'rbi', 'earned', 'teamUnearned', 'playIndex'],
                        'credits': {
                            'player': ['id'],
                            'credit': None
                        }
                    }
                }
            },
            'linescore': ['currentInning', 'isTopInning', 'inningState', 'outs', 'balls', 'strikes', 'teams', 'innings'],
            'boxscore': {
                'teams': {
                    'away': ['team', 'teamStats', 'players', 'batters', 'pitchers', 'bench', 'bullpen', 'battingOrder', 'info', 'note'],
                    'home': ['team', 'teamStats', 'players', 'batters', 'pitchers', 'bench', 'bullpen', 'battingOrder', 'info', 'note']
                },
                'officials': None,
                'info': None,
                'pitchingNotes': None
            }
        }
    }


def create_player_mapping(real_data, our_teams):
    # Categorize our players
    our_pitchers = []
    our_batters = []
    for team in our_teams.values():
        for p in team['players']:
            if p['position']['abbreviation'] == 'P':
                our_pitchers.append(p)
            else:
                our_batters.append(p)

    random.shuffle(our_pitchers)
    random.shuffle(our_batters)

    # Categorize real players
    real_pitchers = {} # id -> name
    real_batters = {}  # id -> name

    def is_real_pitcher(pid, data):
        if 'gameData' in data and 'players' in data['gameData']:
            p_key = f"ID{pid}"
            if p_key in data['gameData']['players']:
                 pos = data['gameData']['players'][p_key].get('primaryPosition', {}).get('abbreviation')
                 if pos == 'P': return True
                 if pos: return False

        if 'liveData' in data and 'plays' in data['liveData']:
             for play in data['liveData']['plays'].get('allPlays', []):
                 if play.get('matchup', {}).get('pitcher', {}).get('id') == pid:
                     return True
        return False

    all_real_ids = set()
    if 'gameData' in real_data and 'players' in real_data['gameData']:
        for p in real_data['gameData']['players'].values():
            all_real_ids.add(p['id'])

    if 'liveData' in real_data and 'plays' in real_data['liveData']:
        for play in real_data['liveData']['plays'].get('allPlays', []):
            m = play.get('matchup', {})
            if 'batter' in m: all_real_ids.add(m['batter']['id'])
            if 'pitcher' in m: all_real_ids.add(m['pitcher']['id'])
            for r in play.get('runners', []):
                 if 'details' in r and 'runner' in r['details']:
                     all_real_ids.add(r['details']['runner']['id'])

    for pid in all_real_ids:
        name = ""
        if 'gameData' in real_data and 'players' in real_data['gameData']:
             p_entry = real_data['gameData']['players'].get(f"ID{pid}")
             if p_entry: name = p_entry.get('fullName', '')

        if is_real_pitcher(pid, real_data):
            real_pitchers[pid] = name
        else:
            real_batters[pid] = name

    # Map Pitchers
    id_mapping = {}
    name_mapping = {}

    first_names = ['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon', 'Zeta', 'Eta', 'Theta', 'Iota', 'Kappa', 'Lambda', 'Mu', 'Nu', 'Xi', 'Omicron']
    last_names = ['One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen']

    def map_group(real_group, our_group, base_syn_id):
        sorted_real = sorted(real_group.items())

        while len(our_group) < len(sorted_real):
             idx = len(our_group)
             fname = first_names[idx % len(first_names)]
             lname = last_names[idx % len(last_names)] + f"_{idx}"
             syn_player = {
                 'id': base_syn_id + idx,
                 'legal_name': f"{fname} {lname}",
                 'nickname': None,
                 'position': {'code': '1', 'name': 'Pitcher', 'abbreviation': 'P'} if base_syn_id == 800000 else {'code': '10', 'name': 'Utility', 'abbreviation': 'UT'},
                 'batSide': {'code': 'R', 'description': 'Right'},
                 'pitchHand': {'code': 'R', 'description': 'Right'}
             }
             our_group.append(syn_player)

        for i, (rid, rname) in enumerate(sorted_real):
            fake = our_group[i]
            id_mapping[rid] = fake
            if rname:
                name_mapping[rname] = fake['legal_name']
                norm = normalize_unicode(rname)
                if norm != rname: name_mapping[norm] = fake['legal_name']

                parts = rname.split()
                fake_parts = fake['legal_name'].split()
                if len(parts) >= 2 and len(fake_parts) >= 2:
                     name_mapping[parts[0]] = fake_parts[0]
                     name_mapping[parts[-1]] = fake_parts[-1]

    map_group(real_pitchers, our_pitchers, 800000)
    map_group(real_batters, our_batters, 700000)

    return id_mapping, name_mapping


def _generate_player_bio(fake_player):
    pid = fake_player['id']
    full_name = fake_player['legal_name']
    name_parts = full_name.split(' ')
    first_name = name_parts[0]
    last_name = name_parts[-1] if len(name_parts) > 1 else ""
    middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else ""

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
        "primaryPosition": fake_player['position'],
        "useName": fake_player.get('nickname', first_name) or first_name,
        "useLastName": last_name,
        "middleName": middle_name,
        "boxscoreName": last_name,
        "gender": "M",
        "isPlayer": True,
        "isVerified": False,
        "draftYear": draft_year,
        "mlbDebutDate": debut_date,
        "batSide": fake_player.get('batSide', {'code': 'R', 'description': 'Right'}),
        "pitchHand": fake_player.get('pitchHand', {'code': 'R', 'description': 'Right'}),
        "strikeZoneTop": 3.5,
        "strikeZoneBottom": 1.5
    }

def filter_dict(data, allowed_fields):
    if isinstance(allowed_fields, list):
        return {k: data[k] for k in allowed_fields if k in data}
    elif isinstance(allowed_fields, dict):
        result = {}
        for key, subfields in allowed_fields.items():
            if key not in data:
                continue
            if subfields is None:
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
    if not mapped:
        return player_ref

    new_ref = {
        'id': mapped['id'],
        'fullName': mapped['legal_name'],
        'link': f"/api/v1/people/{mapped['id']}"
    }
    return new_ref


def _case_like(src: str, repl: str) -> str:
    if src.isupper(): return repl.upper()
    if src.istitle(): return repl.title()
    if src.islower(): return repl.lower()
    return repl

def _compile_name_pattern(name: str):
    return re.compile(rf"(?<!\w){re.escape(name)}(?!\w)(?:['’]s)?", re.IGNORECASE)

def anonymize_description(text: str, name_mapping: dict) -> str:
    if not text:
        return text
    items = sorted(name_mapping.items(), key=lambda kv: len(kv[0]), reverse=True)
    for real, fake in items:
        if len(real) < 3: continue

        pat = _compile_name_pattern(real)
        def sub(m):
            s = m.group(0)
            poss = ''
            if s.lower().endswith(("'s","’s")):
                poss, s = s[-2:], s[:-2]
            return _case_like(s, fake) + poss
        text = pat.sub(sub, text)
    return text

def anonymize_text_container(item, name_mapping):
    if isinstance(item, str):
        return anonymize_description(item, name_mapping)
    elif isinstance(item, dict):
        new_item = copy.deepcopy(item)
        if 'label' in new_item:
            new_item['label'] = anonymize_description(new_item['label'], name_mapping)
        if 'value' in new_item:
            new_item['value'] = anonymize_description(new_item['value'], name_mapping)
        if 'fieldList' in new_item:
             for field in new_item['fieldList']:
                 if 'value' in field:
                     field['value'] = anonymize_description(field['value'], name_mapping)
                 if 'label' in field:
                     field['label'] = anonymize_description(field['label'], name_mapping)
        return new_item
    return item

def simplify_runner(r, id_mapping, schema):
    out = {}
    if 'movement' in r:
        out['movement'] = r['movement']

    if 'details' in r:
        allowed_detail_fields = schema['liveData']['plays']['allPlays']['runners']['details']
        d = {}
        for field in allowed_detail_fields:
            if field in r['details']:
                value = r['details'][field]
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
                anon_credit['credit'] = credit['credit']
            out['credits'].append(anon_credit)

    return out


def anonymize_gameday_data(real_data, teams_template):
    # Patch TEAMS to avoid collision (Nate Pearson / Nate Diaz)
    our_teams = copy.deepcopy(teams_template)
    for t in our_teams.values():
        for p in t['players']:
            if 'Nate' in p['legal_name']:
                 p['legal_name'] = p['legal_name'].replace('Nate', 'Nathaniel')

    id_mapping, name_mapping = create_player_mapping(real_data, our_teams)
    schema = get_our_schema_fields()
    result = {}

    if 'gameData' in real_data and 'gameData' in schema:
        result['gameData'] = {}
        if 'teams' in real_data['gameData']:
            result['gameData']['teams'] = {}
            for side in ['home', 'away']:
                if side in real_data['gameData']['teams']:
                    our_team = our_teams['BAY_BOMBERS'] if side == 'home' else our_teams['PC_PILOTS']
                    result['gameData']['teams'][side] = {
                        'id': our_team['id'],
                        'name': our_team['name'],
                        'abbreviation': our_team['abbreviation'],
                        'teamName': our_team['teamName']
                    }

        result['gameData']['players'] = {}
        for fake_player in id_mapping.values():
            bio = _generate_player_bio(fake_player)
            result['gameData']['players'][f"ID{fake_player['id']}"] = bio

        # Context
        result['gameData']['venue'] = {
             "id": 999,
             "name": "Sim City Stadium",
             "link": "/api/v1/venues/999"
        }
        if 'weather' in real_data['gameData']:
             result['gameData']['weather'] = real_data['gameData']['weather']

        # Umpires - empty or generic
        result['gameData']['umpires'] = []

    if 'liveData' in real_data and 'liveData' in schema:
        result['liveData'] = {}

        if 'boxscore' in real_data['liveData']:
            bs = real_data['liveData']['boxscore']
            anon_bs = {}

            if 'teams' in bs:
                anon_bs['teams'] = {}
                for side in ['home', 'away']:
                    if side in bs['teams']:
                        real_bs_team = bs['teams'][side]
                        our_team = our_teams['BAY_BOMBERS'] if side == 'home' else our_teams['PC_PILOTS']

                        anon_team_entry = {}
                        anon_team_entry['team'] = {
                            'id': our_team['id'],
                            'name': our_team['name'],
                            'abbreviation': our_team['abbreviation'],
                            'teamName': our_team['teamName']
                        }

                        if 'teamStats' in real_bs_team:
                            anon_team_entry['teamStats'] = real_bs_team['teamStats']

                        anon_team_entry['players'] = {}
                        if 'players' in real_bs_team:
                            for pid_key, p_data in real_bs_team['players'].items():
                                try:
                                    real_id = int(pid_key[2:])
                                except ValueError:
                                    continue

                                mapped = id_mapping.get(real_id)
                                if mapped:
                                    fake_id_key = f"ID{mapped['id']}"
                                    new_p_data = copy.deepcopy(p_data)
                                    if 'person' in new_p_data:
                                        new_p_data['person'] = {
                                            "id": mapped['id'],
                                            "fullName": mapped['legal_name'],
                                            "link": f"/api/v1/people/{mapped['id']}"
                                        }
                                    new_p_data['parentTeamId'] = our_team['id']
                                    anon_team_entry['players'][fake_id_key] = new_p_data

                        for list_key in ['batters', 'pitchers', 'bench', 'bullpen', 'battingOrder']:
                            if list_key in real_bs_team:
                                new_list = []
                                for real_id in real_bs_team[list_key]:
                                    mapped = id_mapping.get(real_id)
                                    if mapped:
                                        new_list.append(mapped['id'])
                                anon_team_entry[list_key] = new_list

                        if 'info' in real_bs_team:
                            anon_team_entry['info'] = [anonymize_text_container(item, name_mapping) for item in real_bs_team['info']]

                        if 'note' in real_bs_team:
                             anon_team_entry['note'] = [anonymize_text_container(item, name_mapping) for item in real_bs_team['note']]

                        anon_bs['teams'][side] = anon_team_entry

            anon_bs['officials'] = []
            if 'info' in bs:
                 anon_bs['info'] = [anonymize_text_container(item, name_mapping) for item in bs['info']]

            if 'pitchingNotes' in bs:
                 anon_bs['pitchingNotes'] = [anonymize_text_container(item, name_mapping) for item in bs['pitchingNotes']]

            result['liveData']['boxscore'] = anon_bs

        if 'plays' in real_data['liveData']:
            result['liveData']['plays'] = {'allPlays': []}

            for play in real_data['liveData']['plays'].get('allPlays', []):
                anonymized_play = {}
                if 'result' in play:
                    anonymized_play['result'] = filter_dict(play['result'], schema['liveData']['plays']['allPlays']['result'])
                    anonymized_play['result'].pop('eventType', None)

                if 'about' in play:
                    anonymized_play['about'] = filter_dict(play['about'], schema['liveData']['plays']['allPlays']['about'])

                if 'count' in play:
                    anonymized_play['count'] = filter_dict(play['count'], schema['liveData']['plays']['allPlays']['count'])

                if 'matchup' in play:
                    matchup = play['matchup']
                    anonymized_play['matchup'] = {}
                    for field in ['batter', 'pitcher']:
                        if field in matchup:
                            anonymized_play['matchup'][field] = anonymize_player_reference(matchup[field], id_mapping)
                    if 'batSide' in matchup: anonymized_play['matchup']['batSide'] = matchup['batSide']
                    if 'pitchHand' in matchup: anonymized_play['matchup']['pitchHand'] = matchup['pitchHand']
                    for base in ['postOnFirst', 'postOnSecond', 'postOnThird']:
                        if base in matchup:
                            anonymized_play['matchup'][base] = anonymize_player_reference(matchup[base], id_mapping)

                    # Clear hot cold zones
                    anonymized_play['matchup']['batterHotColdZones'] = []
                    anonymized_play['matchup']['pitcherHotColdZones'] = []

                    if 'splits' in matchup:
                        anonymized_play['matchup']['splits'] = {}
                        for k, v in matchup['splits'].items():
                            if isinstance(v, str):
                                anonymized_play['matchup']['splits'][k] = anonymize_description(v, name_mapping)
                            else:
                                anonymized_play['matchup']['splits'][k] = v

                if 'playEvents' in play:
                    events = [e for e in play['playEvents'] if is_pitch_like(e)]
                    anonymized_play['playEvents'] = []
                    for event in events:
                        filtered_event = {}
                        if 'index' in event: filtered_event['index'] = event['index']
                        if 'count' in event: filtered_event['count'] = filter_dict(event['count'], ['balls', 'strikes'])

                        if 'details' in event:
                            details = {}
                            for field in ['code', 'description', 'isStrike']:
                                if field in event['details']:
                                    val = event['details'][field]
                                    if field == 'description':
                                        val = anonymize_description(val, name_mapping)
                                    details[field] = val
                            if 'type' in event['details']:
                                details['type'] = event['details']['type']
                            filtered_event['details'] = details

                        if 'pitchData' in event:
                            pd = {}
                            if 'startSpeed' in event['pitchData']:
                                pd['startSpeed'] = event['pitchData']['startSpeed']
                            if 'breaks' in event['pitchData'] and 'spinRate' in event['pitchData']['breaks']:
                                pd['breaks'] = {'spinRate': event['pitchData']['breaks']['spinRate']}
                            filtered_event['pitchData'] = pd

                        if 'hitData' in event:
                            hd = {}
                            for fld in ['launchSpeed', 'launchAngle', 'trajectory']:
                                if fld in event['hitData']:
                                    hd[fld] = event['hitData'][fld]
                            filtered_event['hitData'] = hd

                        if 'isBunt' in event:
                            filtered_event['isBunt'] = event['isBunt']

                        anonymized_play['playEvents'].append(filtered_event)

                if 'runners' in play:
                    anonymized_play['runners'] = [simplify_runner(r, id_mapping, schema) for r in play['runners']]

                result['liveData']['plays']['allPlays'].append(anonymized_play)

        if 'linescore' in real_data['liveData']:
            ls = real_data['liveData']['linescore']
            result['liveData']['linescore'] = {}
            for field in schema['liveData']['linescore']:
                 if field in ls:
                      result['liveData']['linescore'][field] = ls[field]

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

    random.seed(args.seed)

    print(f"Loading {args.input_file}...")
    with open(args.input_file, 'r') as f:
        real_data = json.load(f)

    print("Anonymizing players and filtering fields...")
    anonymized = anonymize_gameday_data(real_data, TEAMS)

    print(f"Writing to {args.output}...")
    with open(args.output, 'w') as f:
        json.dump(anonymized, f, indent=2)

    real_plays = len(real_data.get('liveData', {}).get('plays', {}).get('allPlays', []))
    anon_plays = len(anonymized.get('liveData', {}).get('plays', {}).get('allPlays', []))

    print(f"\n✓ Anonymization complete!")
    print(f"  Plays: {anon_plays}/{real_plays}")
    print(f"  Output: {args.output}")

    lifecycle_smoke_test(anonymized)


if __name__ == '__main__':
    main()
