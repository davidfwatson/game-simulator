#!/usr/bin/env python3
"""
This script regenerates the example Gameday JSON logs.

The `EXAMPLE_GAMES` list in `example_games.py` defines the seeds and
parameters for each example. This script iterates through that list,
simulates the game, and writes the resulting JSON Gameday log to a
corresponding file in the `examples/gameday/` directory.

To run it from the root of the repository:

    python update_gameday_examples.py
"""
import json
from pathlib import Path

from example_games import EXAMPLE_GAMES, ExampleGame

GAMEDAY_EXAMPLES_DIR = Path(__file__).parent / "examples" / "gameday"


def main():
    """Render each example game and write the Gameday JSON to a file."""
    print(f"Updating {len(EXAMPLE_GAMES)} Gameday example logs...")
    for index, game in enumerate(EXAMPLE_GAMES, start=1):
        path = GAMEDAY_EXAMPLES_DIR / f"game_{index:02d}.json"
        print(f"  - {path} (seed={game.seed})")

        # The render method now returns a string, which for gameday is a JSON string.
        gameday_json_str = ExampleGame.render(game, commentary_style="gameday")

        # Parse the JSON string to a Python object to format it nicely.
        gameday_data = json.loads(gameday_json_str)

        with open(path, "w") as f:
            json.dump(gameday_data, f, indent=2)

    print("Done.")


if __name__ == "__main__":
    main()