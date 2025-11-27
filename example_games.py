from dataclasses import dataclass
from pathlib import Path
import sys
import json
from datetime import datetime

from baseball import BaseballSimulator
from teams import TEAMS
from renderers import NarrativeRenderer, StatcastRenderer

EXAMPLES_DIR = Path(__file__).parent / "examples"

@dataclass
class ExampleGame:
    seed: int
    commentary_style: str = "narrative"

    def render(self, commentary_style=None) -> str:
        style = commentary_style if commentary_style else self.commentary_style

        # Based on baseball.py main
        game = BaseballSimulator(
            TEAMS["BAY_BOMBERS"],
            TEAMS["PC_PILOTS"],
            game_seed=self.seed
        )
        game.play_game()

        if style == "narrative":
            renderer = NarrativeRenderer(game.gameday_data, seed=self.seed, verbose=True)
            return renderer.render()
        elif style == "statcast":
            renderer = StatcastRenderer(game.gameday_data, seed=self.seed)
            return renderer.render()
        elif style == "gameday":
            class DateTimeEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, datetime): return obj.isoformat()
                    return super().default(obj)
            return json.dumps(game.gameday_data, indent=2, cls=DateTimeEncoder)
        return ""

EXAMPLE_GAMES = [
    ExampleGame(seed=101 * i) for i in range(1, 11)
]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            idx = int(sys.argv[1])
            style = None
            if len(sys.argv) > 3 and sys.argv[2] == '--commentary':
                style = sys.argv[3]

            if 1 <= idx <= len(EXAMPLE_GAMES):
                print(EXAMPLE_GAMES[idx-1].render(commentary_style=style), end="")
        except ValueError:
            pass
