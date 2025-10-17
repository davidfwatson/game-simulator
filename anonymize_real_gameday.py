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


# Top-level constants (module scope)
IGNORED_EVENT_TYPES = {
    'game_advisory', 'mound_visit', 'batter_timeout', 'manager_challenge',
    'pitching_substitution', 'defensive_switch', 'umpire_review',
    'pickoff_attempt', 'stolen_base', 'caught_stealing', 'wild_pitch',
    'passed_ball', 'defensive_indiff', 'game_delayed', 'game_resumed'
}

# Keep a conservative pitch code list (adjust to match your generator’s behavior)
PITCH_CODE_WHITELIST = {'B', 'C', 'S', 'X', 'F', 'D'}

def is_pitch_like(ev: dict) -> bool:
    d = (ev.get('details') or {})
    if d.get('eventType') in IGNORED_EVENT_TYPES:
        return False
    # Require pitchData present (non-pitch events rarely have it)
    if not ev.get('pitchData'):
        return False
    # If a code exists, clamp to a small set your generator would produce
    code = d.get('code')
    return code in PITCH_CODE_WHITELIST if code else True


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
            }
        },
        'liveData': {
            'plays': {
                'allPlays': {
                    'result': ['type', 'event', 'eventType', 'description', 'rbi', 'awayScore', 'homeScore'],
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
                        'details': None,
                        'credits': {
                            'player': ['id'],
                            'position': ['code', 'name', 'abbreviation'],
                            'credit': None
                        }
                    }
                }
            },
            'linescore': ['currentInning', 'isTopInning', 'inningState', 'outs', 'balls', 'strikes', 'teams', 'innings']
        }
    }


def create_player_mapping(real_data, our_teams):
    """
    Create a mapping from real player IDs to our fictional players.

    Args:
        real_data: Real MLB gameday JSON
        our_teams: Our TEAMS dictionary

    Returns:
        tuple of (id_mapping dict, name_mapping dict)
            id_mapping: real player ID -> our player dict
            name_mapping: real player full name -> our player legal_name
    """
    # Get all our players
    our_players = []
    for team in our_teams.values():
        our_players.extend(team['players'])

    # Shuffle to randomize assignment
    random.shuffle(our_players)

    # Extract all unique player IDs and names from real data
    real_players = {}  # id -> full name

    # From gameData.players
    if 'gameData' in real_data and 'players' in real_data['gameData']:
        for player_key in real_data['gameData']['players']:
            player = real_data['gameData']['players'][player_key]
            real_players[player['id']] = player.get('fullName', '')

    # From plays (in case some players aren't in gameData.players)
    if 'liveData' in real_data and 'plays' in real_data['liveData']:
        for play in real_data['liveData']['plays'].get('allPlays', []):
            matchup = play.get('matchup', {})
            if 'batter' in matchup and matchup['batter']['id'] not in real_players:
                real_players[matchup['batter']['id']] = matchup['batter'].get('fullName', '')
            if 'pitcher' in matchup and matchup['pitcher']['id'] not in real_players:
                real_players[matchup['pitcher']['id']] = matchup['pitcher'].get('fullName', '')

            # From runners
            for runner in play.get('runners', []):
                if 'details' in runner and 'runner' in runner['details']:
                    runner_ref = runner['details']['runner']
                    if runner_ref['id'] not in real_players:
                        real_players[runner_ref['id']] = runner_ref.get('fullName', '')

    # Create ID mapping
    id_mapping = {}
    name_mapping = {}
    for i, (real_id, real_name) in enumerate(sorted(real_players.items())):
        our_player = our_players[i % len(our_players)]
        id_mapping[real_id] = our_player
        if real_name:
            # Add original name (with accents if present)
            name_mapping[real_name] = our_player['legal_name']
            # Also add normalized version (without accents) to handle inconsistencies
            normalized_name = normalize_unicode(real_name)
            if normalized_name != real_name:
                name_mapping[normalized_name] = our_player['legal_name']

            # Add first and last names separately for partial match detection
            parts = real_name.split()
            if len(parts) >= 2:
                name_mapping[parts[0]] = our_player['legal_name'].split()[0]  # First name
                name_mapping[parts[-1]] = our_player['legal_name'].split()[-1]  # Last name
                # Also add normalized versions of first/last names
                normalized_first = normalize_unicode(parts[0])
                normalized_last = normalize_unicode(parts[-1])
                if normalized_first != parts[0]:
                    name_mapping[normalized_first] = our_player['legal_name'].split()[0]
                if normalized_last != parts[-1]:
                    name_mapping[normalized_last] = our_player['legal_name'].split()[-1]

    return id_mapping, name_mapping


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
    return {'id': (mapped['id'] if mapped else real_id)}


def _case_like(src: str, repl: str) -> str:
    if src.isupper(): return repl.upper()
    if src.istitle(): return repl.title()
    if src.islower(): return repl.lower()
    return repl

def _compile_name_pattern(name: str):
    # Boundaries that handle apostrophes; avoid replacing inside other words
    return re.compile(rf"(?<!\w){re.escape(name)}(?!\w)(?:['’]s)?", re.IGNORECASE)

def anonymize_description(text: str, name_mapping: dict) -> str:
    if not text:
        return text
    items = sorted(name_mapping.items(), key=lambda kv: len(kv[0]), reverse=True)
    for real, fake in items:
        pat = _compile_name_pattern(real)
        def sub(m):
            s = m.group(0)
            poss = ''
            if s.lower().endswith(("'s","’s")):
                poss, s = s[-2:], s[:-2]
            return _case_like(s, fake) + poss
        text = pat.sub(sub, text)
    return text


def simplify_runner_movement(mov):
    if not isinstance(mov, dict):
        return mov
    # Keep only coarse info; remove outBase/outNumber/isOut etc.
    return {'start': mov.get('start'), 'end': mov.get('end')}

def simplify_runner(r, id_mapping):
    out = {}
    if 'movement' in r:
        out['movement'] = simplify_runner_movement(r['movement'])
    if 'details' in r:
        d = dict(r['details'])
        if 'runner' in d:
            d['runner'] = anonymize_player_reference(d['runner'], id_mapping)
        if 'responsiblePitcher' in d:
            d['responsiblePitcher'] = anonymize_player_reference(d['responsiblePitcher'], id_mapping)
        # Remove MLB-ish extras you don’t generate
        for k in ['event', 'isScoringEvent', 'rbi', 'earned', 'teamUnearned', 'playIndex']:
            d.pop(k, None)
        out['details'] = d
    # Drop fielding credits entirely
    return out


def anonymize_gameday_data(real_data, our_teams):
    """
    Anonymize real gameday data by replacing players and filtering fields.

    Args:
        real_data: Real MLB gameday JSON
        our_teams: Our TEAMS dictionary

    Returns:
        Anonymized gameday JSON
    """
    # Create player mappings
    id_mapping, name_mapping = create_player_mapping(real_data, our_teams)

    # Get schema
    schema = get_our_schema_fields()

    # Filter top-level structure
    result = {}

    # Handle gameData
    if 'gameData' in real_data and 'gameData' in schema:
        result['gameData'] = {}
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
                        'teamName': our_team['teamName']
                    }

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
                    # Anonymize description text
                    if 'description' in anonymized_play['result']:
                        anonymized_play['result']['description'] = anonymize_description(
                            anonymized_play['result']['description'],
                            name_mapping
                        )

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
                    events = [e for e in play['playEvents'] if is_pitch_like(e)]
                    # Optional: keep only terminal pitch to look even more generated:
                    # events = events[-1:]
                    anonymized_play['playEvents'] = []
                    for event in events:
                        filtered_event = {}
                        if 'index' in event:
                            filtered_event['index'] = event['index']
                        if 'count' in event:
                            filtered_event['count'] = filter_dict(event['count'], ['balls', 'strikes'])
                        if 'details' in event:
                            details = {}
                            for field in ['code', 'description', 'isStrike']:
                                if field in event['details']:
                                    val = event['details'][field]
                                    if field == 'description':
                                        val = anonymize_description(val, name_mapping)
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

                # Handle runners
                if 'runners' in play:
                    anonymized_play['runners'] = [simplify_runner(r, id_mapping) for r in play['runners']]

                # Result taxonomy
                if 'result' in anonymized_play:
                    anonymized_play['result'].pop('eventType', None)  # keep 'event' if you need it; otherwise consider removing too

                # Matchup: ensure only IDs and basic handedness/splits
                if 'matchup' in anonymized_play:
                    m = anonymized_play['matchup']
                    # Make sure postOn* are IDs only; you already anonymize them with anonymize_player_reference
                    for base in ['postOnFirst', 'postOnSecond', 'postOnThird']:
                        if base in m and isinstance(m[base], dict):
                            m[base] = anonymize_player_reference(m[base], id_mapping)
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
    anonymized = anonymize_gameday_data(real_data, TEAMS)

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
