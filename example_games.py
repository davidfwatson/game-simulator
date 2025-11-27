from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from baseball import BaseballSimulator
from teams import TEAMS
from renderers import NarrativeRenderer, StatcastRenderer
import json
import datetime

EXAMPLES_DIR = Path(__file__).parent / "examples"


@dataclass
class ExampleGame:
    game_seed: int
    commentary_seed: int | None = None

    def render(self, commentary_type: str = 'narrative') -> str:
        # 1. Run Simulation
        game = BaseballSimulator(
            TEAMS["BAY_BOMBERS"],
            TEAMS["PC_PILOTS"],
            game_seed=self.game_seed
        )
        game.play_game()

        # 2. Render Output
        if commentary_type == 'gameday':
             class DateTimeEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, datetime.datetime): return obj.isoformat()
                    return super().default(obj)
             return json.dumps(game.gameday_data, indent=2, cls=DateTimeEncoder)

        commentary_seed = self.commentary_seed if self.commentary_seed else self.game_seed
        if commentary_type == 'narrative':
            renderer = NarrativeRenderer(game.gameday_data, seed=commentary_seed)
        elif commentary_type == 'statcast':
            renderer = StatcastRenderer(game.gameday_data, seed=commentary_seed)
        else:
            raise ValueError(f"Unknown commentary type: {commentary_type}")

        return renderer.render()


# Define the 10 example games used for snapshot testing
EXAMPLE_GAMES = [
    ExampleGame(game_seed=1, commentary_seed=1),
    ExampleGame(game_seed=2, commentary_seed=2),
    ExampleGame(game_seed=3, commentary_seed=3),
    ExampleGame(game_seed=4, commentary_seed=4),
    ExampleGame(game_seed=5, commentary_seed=5),
    ExampleGame(game_seed=6, commentary_seed=6),
    ExampleGame(game_seed=7, commentary_seed=7),
    ExampleGame(game_seed=8, commentary_seed=8),
    ExampleGame(game_seed=9, commentary_seed=9),
    ExampleGame(game_seed=10, commentary_seed=10),
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("game_index", type=int, help="Index of the example game (1-10)")
    parser.add_argument("--commentary", type=str, default='narrative', choices=['narrative', 'statcast', 'gameday'], help="Commentary style")
    args = parser.parse_args()

    if 1 <= args.game_index <= len(EXAMPLE_GAMES):
        game = EXAMPLE_GAMES[args.game_index - 1]
        print(game.render(commentary_type=args.commentary), end="")
    else:
        print(f"Invalid game index. Must be between 1 and {len(EXAMPLE_GAMES)}")
