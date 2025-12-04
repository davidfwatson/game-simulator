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
    team1: dict | None = None
    team2: dict | None = None

    def __post_init__(self):
        if self.team1 is None:
            self.team1 = TEAMS["BAY_BOMBERS"]
        if self.team2 is None:
            self.team2 = TEAMS["PC_PILOTS"]

    def render(self, commentary_type: str = 'narrative') -> str:
        # 1. Run Simulation
        game = BaseballSimulator(
            self.team1,
            self.team2,
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
# We rotate through all possible matchups of the 4 teams
teams = ["BAY_BOMBERS", "PC_PILOTS", "COASTAL_VIPERS", "DESERT_SCORPIONS"]
matchups = []
for t1 in teams:
    for t2 in teams:
        if t1 != t2:
            matchups.append((t1, t2))

EXAMPLE_GAMES = []
for i in range(10):
    t1_key, t2_key = matchups[i]
    EXAMPLE_GAMES.append(
        ExampleGame(
            game_seed=i + 1,
            commentary_seed=i + 1,
            team1=TEAMS[t1_key],
            team2=TEAMS[t2_key]
        )
    )

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
