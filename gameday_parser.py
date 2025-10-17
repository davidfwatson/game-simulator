"""
Gameday Parser CLI

A command-line utility to parse and display information from MLB Gameday JSON files.
This tool allows you to extract high-level summaries, specific play details, and
search for plays matching certain criteria from a given Gameday data file.

Usage examples:
  # Get a summary of the game
  python gameday_parser.py real_gameday.json summary

  # Get a specific play by its at-bat index
  python gameday_parser.py real_gameday.json get-play 18

  # Search for all home runs in the game
  python gameday_parser.py real_gameday.json search "Home Run"
"""

import json
import argparse

class GamedayParser:
    """
    A utility class to parse and extract information from MLB Gameday JSON files.
    """
    def __init__(self, filepath):
        """
        Initializes the parser by loading the Gameday JSON data from a file.
        """
        with open(filepath, 'r') as f:
            self.data = json.load(f)

    def get_all_plays(self):
        """
        Retrieves all play-by-play entries from the Gameday data.
        """
        return self.data.get('liveData', {}).get('plays', {}).get('allPlays', [])

    def get_play_by_at_bat_index(self, at_bat_index):
        """
        Finds a specific play by its atBatIndex.
        """
        for play in self.get_all_plays():
            if play.get('about', {}).get('atBatIndex') == at_bat_index:
                return play
        return None

    def get_player_details(self, player_id):
        """
        Retrieves the details for a specific player by their ID.
        """
        player_key = f"ID{player_id}"
        return self.data.get('gameData', {}).get('players', {}).get(player_key)

    def get_hit_data(self, play):
        """
        Extracts hit data (launch speed, angle, etc.) from a play.
        """
        for event in play.get('playEvents', []):
            if 'hitData' in event:
                return event['hitData']
        return None

    def get_matchup_details(self, play):
        """
        Retrieves the matchup details (batter, pitcher, etc.) for a play.
        """
        return play.get('matchup')

    def search_plays(self, filter_func, max_results=None):
        """
        Searches for plays that match a given set of criteria using a filter function.
        """
        matching_plays = []
        for play in self.get_all_plays():
            if filter_func(play):
                matching_plays.append(play)
                if max_results is not None and len(matching_plays) >= max_results:
                    break
        return matching_plays

def main():
    """Main function to handle argument parsing and execution."""
    parser = argparse.ArgumentParser(
        description="A CLI tool to parse MLB Gameday JSON files.",
        epilog=__doc__,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('filepath', help="Path to the Gameday JSON file.")

    subparsers = parser.add_subparsers(dest='command', required=True, help="Available commands")

    # Summary command
    summary_parser = subparsers.add_parser('summary', help="Prints a summary of the game.")

    # Get-play command
    get_play_parser = subparsers.add_parser('get-play', help="Fetches a specific play by its at-bat index.")
    get_play_parser.add_argument('at_bat_index', type=int, help="The at-bat index of the play to retrieve.")

    # Search command
    search_parser = subparsers.add_parser('search', help="Searches for plays based on the event type.")
    search_parser.add_argument('event_type', help="The event type to search for (e.g., 'Home Run', 'Walk').")
    search_parser.add_argument('--max', type=int, help="Maximum number of results to return.")

    args = parser.parse_args()

    parser_instance = GamedayParser(args.filepath)

    if args.command == 'summary':
        all_plays = parser_instance.get_all_plays()
        print(f"Total plays in the game: {len(all_plays)}")

    elif args.command == 'get-play':
        play = parser_instance.get_play_by_at_bat_index(args.at_bat_index)
        if play:
            print(json.dumps(play, indent=2))
        else:
            print(f"No play found for at-bat index {args.at_bat_index}")

    elif args.command == 'search':
        def filter_by_event(play):
            return play.get('result', {}).get('event') == args.event_type

        results = parser_instance.search_plays(filter_by_event, max_results=args.max)

        if results:
            print(f"Found {len(results)} plays with event type '{args.event_type}':")
            for play in results:
                batter_name = parser_instance.get_player_details(play['matchup']['batter']['id']).get('fullName', 'N/A')
                description = play['result']['description']
                print(f"- {batter_name}: {description}")
        else:
            print(f"No plays found with event type '{args.event_type}'")

if __name__ == '__main__':
    main()