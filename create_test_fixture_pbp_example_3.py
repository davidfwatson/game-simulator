import json
from baseball import BaseballSimulator
from teams import TEAMS

def main():
    # Use existing teams but we will change their names in the JSON
    team1 = TEAMS["BAY_BOMBERS"]
    team2 = TEAMS["PC_PILOTS"]

    # Run a simulation for 9 innings
    sim = BaseballSimulator(team1, team2, game_seed=42)
    sim.play_game()

    data = sim.gameday_data

    # Enable direct mode
    data['gameData']['directMode'] = True

    # Modify team names to match the desired output
    data['gameData']['teams']['home']['name'] = 'Lake City Loons'
    data['gameData']['teams']['home']['teamName'] = 'Loons'
    data['gameData']['teams']['home']['abbreviation'] = 'LCL'

    data['gameData']['teams']['away']['name'] = 'Baraboo Bombers'
    data['gameData']['teams']['away']['teamName'] = 'Bombers'
    data['gameData']['teams']['away']['abbreviation'] = 'BAR'

    # Modify venue and weather
    data['gameData']['venue'] = 'Goodhue Field'
    data['gameData']['weather'] = '66 degrees at game time. With a breeze blowing in from center field...'

    # We must format datetime objects correctly since python's json.dumps doesn't handle them
    from datetime import datetime
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return super().default(obj)

    with open('test_fixture_pbp_example_3.json', 'w') as f:
        json.dump(data, f, indent=2, cls=DateTimeEncoder)

if __name__ == '__main__':
    main()
