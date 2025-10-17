"""
Utility to extract representative plays from gameday JSON for snapshot testing.

Instead of storing entire game JSON (too large), we extract a curated set of
diverse plays from each game that represent different event types and scenarios.
"""

import json
from typing import List, Dict, Any


def extract_representative_plays(gameday_data: Dict[str, Any], max_plays: int = 5) -> List[Dict[str, Any]]:
    """
    Extract a diverse set of plays from gameday JSON for snapshot testing.

    Selection strategy:
    1. First play of the game (always include)
    2. First of each unique event type (prioritize variety)
    3. First scoring play (if any)
    4. Up to max_plays total

    Args:
        gameday_data: Full gameday JSON structure
        max_plays: Maximum number of plays to extract

    Returns:
        List of play objects
    """
    all_plays = gameday_data.get('liveData', {}).get('plays', {}).get('allPlays', [])

    if not all_plays:
        return []

    selected_plays = []
    seen_event_types = set()

    # Always include first play
    if all_plays:
        selected_plays.append(all_plays[0])
        seen_event_types.add(all_plays[0]['result']['event'])

    # Add first scoring play
    for play in all_plays[1:]:
        if play['about'].get('isScoringPlay', False):
            selected_plays.append(play)
            seen_event_types.add(play['result']['event'])
            break

    # Add first of each unique event type
    for play in all_plays:
        if len(selected_plays) >= max_plays:
            break

        event_type = play['result']['event']
        if event_type not in seen_event_types:
            selected_plays.append(play)
            seen_event_types.add(event_type)

    # If we still have room, add plays with interesting characteristics
    if len(selected_plays) < max_plays:
        for play in all_plays:
            if len(selected_plays) >= max_plays:
                break

            # Skip if already selected
            if play in selected_plays:
                continue

            # Look for interesting plays
            has_multiple_pitches = len(play.get('playEvents', [])) > 3
            has_runners = len(play.get('runners', [])) > 0
            has_rbis = play['result'].get('rbi', 0) > 0

            if has_multiple_pitches or has_runners or has_rbis:
                selected_plays.append(play)

    return selected_plays[:max_plays]


def create_snapshot_data(gameday_data: Dict[str, Any], max_plays: int = 5) -> Dict[str, Any]:
    """
    Create a compact snapshot by extracting representative plays and minimal metadata.

    Args:
        gameday_data: Full gameday JSON structure
        max_plays: Maximum number of plays to extract

    Returns:
        Compact snapshot dictionary
    """
    plays = extract_representative_plays(gameday_data, max_plays)

    return {
        "gameData": gameday_data.get('gameData', {}),
        "plays": plays,
        "playCount": len(gameday_data.get('liveData', {}).get('plays', {}).get('allPlays', [])),
        "metadata": {
            "note": "This is a curated subset of plays for regression testing",
            "totalPlaysInGame": len(gameday_data.get('liveData', {}).get('plays', {}).get('allPlays', [])),
            "snapshotPlayCount": len(plays)
        }
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python gameday_snapshot_extractor.py <gameday_json_file> [max_plays]")
        sys.exit(1)

    input_file = sys.argv[1]
    max_plays = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    with open(input_file, 'r') as f:
        gameday_data = json.load(f)

    snapshot = create_snapshot_data(gameday_data, max_plays)
    print(json.dumps(snapshot, indent=2))
