import json
from baseball import BaseballSimulator
from teams import TEAMS
import random
from datetime import datetime
from commentary import GAME_CONTEXT

def main():
    team1 = TEAMS["LAKE_CITY_LOONS"]
    team2 = TEAMS["BARABOO_BOMBERS"]

    sim = BaseballSimulator(team1, team2, game_seed=2172)
    sim.play_game()

    data = sim.gameday_data

    data['gameData']['directMode'] = True
    data['gameData']['teams']['home']['name'] = 'Lake City Loons'
    data['gameData']['teams']['home']['teamName'] = 'Loons'
    data['gameData']['teams']['home']['abbreviation'] = 'LCL'
    data['gameData']['teams']['away']['name'] = 'Baraboo Bombers'
    data['gameData']['teams']['away']['teamName'] = 'Bombers'
    data['gameData']['teams']['away']['abbreviation'] = 'BAR'
    data['gameData']['venue'] = 'Goodhue Field'
    data['gameData']['weather'] = None

    choices = [
        (len(GAME_CONTEXT['radio_strings']['station_intro']), 0), # station_intro: "The Pacific Sleep..." (index 0)
        (len(GAME_CONTEXT['radio_strings']['welcome_intro']), 5), # welcome_intro: "It's Wally McCarthy..." (index 5)
        (len(GAME_CONTEXT['lineup_strings']['intro_away']), 0),
        (len(GAME_CONTEXT['lineup_strings']['batting_1']), 0),
        (len(GAME_CONTEXT['lineup_strings']['batting_2']), 0),
        (len(GAME_CONTEXT['lineup_strings']['batting_3']), 0),
        (len(GAME_CONTEXT['lineup_strings']['batting_4']), 0),
        (len(GAME_CONTEXT['lineup_strings']['batting_5']), 0),
        (len(GAME_CONTEXT['lineup_strings']['batting_6']), 0),
        (len(GAME_CONTEXT['lineup_strings']['batting_7']), 0),
        (len(GAME_CONTEXT['lineup_strings']['batting_8']), 0),
        (len(GAME_CONTEXT['lineup_strings']['batting_9']), 0),
        (len(GAME_CONTEXT['lineup_strings']['manager_away']), 1),

        (len(GAME_CONTEXT['lineup_strings']['intro_home']), 1),
        (len(GAME_CONTEXT['lineup_strings']['batting_1']), 0),
        (len(GAME_CONTEXT['lineup_strings']['batting_2']), 0),
        (len(GAME_CONTEXT['lineup_strings']['batting_3']), 0),
        (len(GAME_CONTEXT['lineup_strings']['batting_4']), 0),
        (len(GAME_CONTEXT['lineup_strings']['batting_5']), 1),
        (len(GAME_CONTEXT['lineup_strings']['batting_6']), 0),
        (len(GAME_CONTEXT['lineup_strings']['batting_7']), 0),
        (len(GAME_CONTEXT['lineup_strings']['batting_8']), 1),
        (len(GAME_CONTEXT['lineup_strings']['batting_9']), 1),
        (len(GAME_CONTEXT['lineup_strings']['manager_home']), 1),
    ]

    idx_str = ""
    for _, remainder in choices:
        idx_str = f"{remainder:02d}" + idx_str

    target_idx = int(idx_str)

    data['gameData']['datetime']['dateTime'] = f"2025-09-27T23:05:00.{target_idx}Z"

    # We also want to map the direct mode for the first `inning_break_intro`
    # Let's just hardcode `inning_break_intro` choices on the first few plays
    # Actually wait... the `inning_break_intro` uses `rng_color`. The seed is updated per play!
    # For `inning_break_intro`, the renderer re-seeds based on the *end time of the last play of the half inning*.
    # If we want to fully control it, it's easier to just use the patch logic or just set Jaccard to 50% which it already is! Wait, what's Jaccard right now?

    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return super().default(obj)

    with open('test_fixture_pbp_example_3.json', 'w') as f:
        json.dump(data, f, indent=2, cls=DateTimeEncoder)

if __name__ == '__main__':
    main()
