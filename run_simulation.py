import argparse
import json
from datetime import datetime

from baseball import BaseballSimulator
from gameday_converter import GamedayConverter
from teams import TEAMS


def main():
    parser = argparse.ArgumentParser(description="A realistic baseball simulator.")
    parser.add_argument('--terse', action='store_true', help="Use terse, data-driven phrasing for play-by-play.")
    parser.add_argument('--bracketed-ui', action='store_true', help="Use the classic bracketed UI for base runners.")
    parser.add_argument('--output-style', type=str, choices=['narrative', 'statcast', 'gameday'], default='narrative',
                        help="Choose the output style.")
    parser.add_argument('--max-innings', type=int, help="Stop simulation after specified number of innings.")
    parser.add_argument('--outfile', type=str, help="File to write output to (stdout by default).")
    parser.add_argument('--game-seed', type=int, help="Seed for the game's random number generator.")
    parser.add_argument('--commentary-seed', type=int, help="Seed for the commentary's random number generator.")
    args = parser.parse_args()

    # --- 1. Run the simulation to get Gameday JSON ---
    simulator = BaseballSimulator(
        TEAMS["BAY_BOMBERS"],
        TEAMS["PC_PILOTS"],
        max_innings=args.max_innings,
        game_seed=args.game_seed,
        commentary_seed=args.commentary_seed
    )
    gameday_data = simulator.play_game()

    # --- 2. Convert Gameday JSON to the desired output format ---
    output = ""
    if args.output_style == 'gameday':
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime): return obj.isoformat()
                return super().default(obj)

        output = json.dumps(gameday_data, indent=2, cls=DateTimeEncoder)
    else:
        converter = GamedayConverter(
            gameday_data,
            commentary_style=args.output_style,
            verbose_phrasing=not args.terse,
            use_bracketed_ui=args.bracketed_ui,
            commentary_seed=args.commentary_seed
        )
        output = converter.convert()

    # --- 3. Write the output ---
    if args.outfile:
        with open(args.outfile, 'w') as f:
            f.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
