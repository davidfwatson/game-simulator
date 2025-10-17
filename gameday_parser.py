import json

class GamedayParser:
    """
    A utility class to parse and extract information from MLB Gameday JSON files.

    This parser is designed to work with the structure of the 'real_gameday.json'
    file, providing helpful methods to access specific parts of the game data,
    such as play-by-play, player details, and hit data. Its main purpose is to
    facilitate the comparison and improvement of the simulated gameday output
    against real-world examples.
    """
    def __init__(self, filepath):
        """
        Initializes the parser by loading the Gameday JSON data from a file.

        Args:
            filepath (str): The path to the Gameday JSON file.
        """
        with open(filepath, 'r') as f:
            self.data = json.load(f)

    def get_all_plays(self):
        """
        Retrieves all play-by-play entries from the Gameday data.

        Returns:
            list: A list of all plays, where each play is a dictionary.
        """
        return self.data.get('liveData', {}).get('plays', {}).get('allPlays', [])

    def get_play_by_at_bat_index(self, at_bat_index):
        """
        Finds a specific play by its atBatIndex.

        Args:
            at_bat_index (int): The at-bat index to search for.

        Returns:
            dict or None: The play dictionary if found, otherwise None.
        """
        for play in self.get_all_plays():
            if play.get('about', {}).get('atBatIndex') == at_bat_index:
                return play
        return None

    def get_player_details(self, player_id):
        """
        Retrieves the details for a specific player by their ID.

        Args:
            player_id (int): The MLB player ID.

        Returns:
            dict or None: The player's data dictionary if found, otherwise None.
        """
        player_key = f"ID{player_id}"
        return self.data.get('gameData', {}).get('players', {}).get(player_key)

    def get_hit_data(self, play):
        """
        Extracts hit data (launch speed, angle, etc.) from a play.

        Args:
            play (dict): A play object from the Gameday data.

        Returns:
            dict or None: The hitData dictionary if it exists, otherwise None.
        """
        for event in play.get('playEvents', []):
            if 'hitData' in event:
                return event['hitData']
        return None

    def get_matchup_details(self, play):
        """
        Retrieves the matchup details (batter, pitcher, etc.) for a play.

        Args:
            play (dict): A play object from the Gameday data.

        Returns:
            dict or None: The matchup dictionary if it exists, otherwise None.
        """
        return play.get('matchup')

    def search_plays(self, filter_func, max_results=None):
        """
        Searches for plays that match a given set of criteria using a filter function.

        Args:
            filter_func (function): A function that takes a play dictionary and
                                    returns True if it matches the criteria, False otherwise.
            max_results (int, optional): The maximum number of matching plays to return.
                                         If None, all matches are returned.

        Returns:
            list: A list of play dictionaries that match the filter criteria.
        """
        matching_plays = []
        for play in self.get_all_plays():
            if filter_func(play):
                matching_plays.append(play)
                if max_results is not None and len(matching_plays) >= max_results:
                    break
        return matching_plays

if __name__ == '__main__':
    # This is a demonstration of how to use the GamedayParser

    # Create an instance of the parser with the path to your gameday file
    parser = GamedayParser('real_gameday.json')

    # Example 1: Get all plays
    all_plays = parser.get_all_plays()
    print(f"Total plays in the game: {len(all_plays)}\n")

    # Example 2: Get a specific play by at-bat index
    at_bat_index_to_find = 18  # Vladimir Guerrero Jr.'s home run
    specific_play = parser.get_play_by_at_bat_index(at_bat_index_to_find)

    if specific_play:
        print(f"--- Play Details for At-Bat Index {at_bat_index_to_find} ---")
        # Example 3: Get matchup details for the play
        matchup = parser.get_matchup_details(specific_play)
        batter_id = matchup.get('batter', {}).get('id')
        pitcher_id = matchup.get('pitcher', {}).get('id')

        # Example 4: Get player details
        batter_details = parser.get_player_details(batter_id)
        pitcher_details = parser.get_player_details(pitcher_id)

        print(f"Batter: {batter_details.get('fullName', 'N/A')}")
        print(f"Pitcher: {pitcher_details.get('fullName', 'N/A')}")

        # Example 5: Get hit data for the play
        hit_data = parser.get_hit_data(specific_play)
        if hit_data:
            print("Hit Data:")
            print(f"  - Launch Speed: {hit_data.get('launchSpeed')} mph")
            print(f"  - Launch Angle: {hit_data.get('launchAngle')}°")
            print(f"  - Total Distance: {hit_data.get('totalDistance')} ft")

        play_result = specific_play.get('result', {})
        print(f"Result: {play_result.get('event')}")
        print(f"Description: {play_result.get('description')}")
        print("-" * 20)
    else:
        print(f"No play found for at-bat index {at_bat_index_to_find}")

    # Example 6: Search for all home runs in the game
    print("\n--- Searching for all Home Runs ---")
    def is_home_run(play):
        return play.get('result', {}).get('event') == 'Home Run'

    home_runs = parser.search_plays(is_home_run)

    if home_runs:
        for hr in home_runs:
            batter_name = parser.get_player_details(hr['matchup']['batter']['id']).get('fullName', 'N/A')
            description = hr['result']['description']
            print(f"- {batter_name}: {description}")
    else:
        print("No home runs found in this game.")
    print("-" * 20)