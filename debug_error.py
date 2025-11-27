
from baseball import BaseballSimulator
from teams import TEAMS
from renderers import NarrativeRenderer
import copy
import random

# Force an error scenario
def check_error_rendering():
    random.seed(42) # Same as test
    home_team = copy.deepcopy(TEAMS["BAY_BOMBERS"])
    away_team = copy.deepcopy(TEAMS["PC_PILOTS"])

    # Make fielders terrible to ensure errors
    for p in home_team['players'] + away_team['players']:
        if 'fielding_ability' in p:
            p['fielding_ability'] = 0.0 # Guaranteed error if checked?

    home_team['fielding_prowess'] = 0.0
    away_team['fielding_prowess'] = 0.0

    game = BaseballSimulator(home_team, away_team, commentary_style='narrative')
    game.play_game()

    renderer = NarrativeRenderer(game.gameday_data)
    output = renderer.render()

    if "An error by" in output:
        print("Found error text!")
    else:
        print("No error text found.")
        # Print parts of output to see what happened
        # print(output[:2000])

    # Count errors in JSON data
    error_count = 0
    for play in game.gameday_data['liveData']['plays']['allPlays']:
        if play['result']['event'] == 'Field Error':
            error_count += 1
    print(f"Errors in JSON: {error_count}")

check_error_rendering()
