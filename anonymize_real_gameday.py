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
            },
            'players': None,  # Full dict of player details
            'venue': None,
            'weather': None,
            'umpires': None
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
                        'details': ['event', 'eventType', 'movementReason', 'runner', 'responsiblePitcher', 'isScoringEvent', 'rbi', 'earned', 'teamUnearned', 'playIndex'],
                        'credits': {
                            'player': ['id'],
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

    # Keep track of original count for generating synthetic IDs if needed
    original_player_count = len(our_players)

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

    # Create ID mapping - extend our_players list if we have more real players than fictional ones
    total_real_players = len(real_players)
    if total_real_players > len(our_players):
        # Generate synthetic players to ensure 1-to-1 mapping
        first_names = ['Alex', 'Sam', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Jamie',
                       'Quinn', 'Drew', 'Avery', 'Reese', 'Dakota', 'Skyler', 'Parker']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Davis', 'Miller', 'Wilson',
                      'Moore', 'Taylor', 'Anderson', 'Thomas', 'Jackson', 'White', 'Harris', 'Martin']

        base_id = 700000  # Start synthetic IDs at 700000 to avoid conflicts
        for i in range(total_real_players - original_player_count):
            synthetic_player = {
                'id': base_id + i,
                'legal_name': f"{first_names[i % len(first_names)]} {last_names[i % len(last_names)]}"
            }
            our_players.append(synthetic_player)

    # Now create 1-to-1 mapping
    id_mapping = {}
    name_mapping = {}
    for i, (real_id, real_name) in enumerate(sorted(real_players.items())):
        our_player = our_players[i]  # Direct indexing, no modulo
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
    new_id = mapped['id'] if mapped else real_id
    full_name = mapped['legal_name'] if mapped else player_ref.get('fullName', '')

    return {
        'id': new_id,
        'fullName': full_name,
        'link': f"/api/v1/people/{new_id}"
    }


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
                anon_credit['credit'] = credit['credit']
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
    id_mapping, name_mapping = create_player_mapping(real_data, our_teams)

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
                        'teamName': our_team['teamName']
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
                    # Enforce empty description to match simulator
                    anonymized_play['result']['description'] = ""

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
                    anonymized_play['runners'] = [simplify_runner(r, id_mapping, schema) for r in play['runners']]

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

        # Handle boxscore
        if 'boxscore' in real_data['liveData']:
            bs = real_data['liveData']['boxscore']
            result['liveData']['boxscore'] = {
                'teams': {},
                'officials': [],
                'info': [],
                'pitchingNotes': []
            }

            # Process teams
            if 'teams' in bs:
                for side in ['home', 'away']:
                    if side in bs['teams']:
                        real_bs_team = bs['teams'][side]
                        our_team = our_teams['BAY_BOMBERS'] if side == 'home' else our_teams['PC_PILOTS']

                        anon_bs_team = {
                            'team': {
                                'id': our_team['id'],
                                'name': our_team['name'],
                                'abbreviation': our_team['abbreviation'],
                                'teamName': our_team['teamName']
                            },
                            'teamStats': real_bs_team.get('teamStats', {}),
                            'players': {},
                            'batters': [],
                            'pitchers': [],
                            'bench': [],
                            'bullpen': [],
                            'battingOrder': [],
                            # Clear info/note to avoid leaking names in stats/summaries
                            'info': [],
                            'note': []
                        }

                        # Process players map
                        if 'players' in real_bs_team:
                            for key, player_entry in real_bs_team['players'].items():
                                person = player_entry.get('person', {})
                                if 'id' in person:
                                    real_id = person['id']
                                    mapped = id_mapping.get(real_id)
                                    if mapped:
                                        new_id = mapped['id']
                                        new_key = f"ID{new_id}"

                                        # Clone and update entry
                                        new_entry = player_entry.copy()
                                        new_entry['person'] = {
                                            'id': new_id,
                                            'fullName': mapped['legal_name'],
                                            'link': f"/api/v1/people/{new_id}"
                                        }
                                        new_entry['parentTeamId'] = our_team['id']
                                        new_entry['jerseyNumber'] = str(new_id % 100)

                                        anon_bs_team['players'][new_key] = new_entry

                        # Process ID lists
                        def map_ids(real_ids):
                            new_ids = []
                            for rid in real_ids:
                                mapped = id_mapping.get(rid)
                                if mapped:
                                    new_ids.append(mapped['id'])
                            return new_ids

                        anon_bs_team['batters'] = map_ids(real_bs_team.get('batters', []))
                        anon_bs_team['pitchers'] = map_ids(real_bs_team.get('pitchers', []))
                        anon_bs_team['bench'] = map_ids(real_bs_team.get('bench', []))
                        anon_bs_team['bullpen'] = map_ids(real_bs_team.get('bullpen', []))
                        anon_bs_team['battingOrder'] = map_ids(real_bs_team.get('battingOrder', []))

                        result['liveData']['boxscore']['teams'][side] = anon_bs_team

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
