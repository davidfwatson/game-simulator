"""Utilities for managing deterministic example game logs."""
from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from baseball import BaseballSimulator
from teams import TEAMS


_BASE_TEAMS = {key: copy.deepcopy(value) for key, value in TEAMS.items()}


EXAMPLES_DIR = Path(__file__).parent / "examples"


@dataclass(frozen=True)
class ExampleGame:
    seed: int
    home_team: str = "BAY_BOMBERS"
    away_team: str = "PC_PILOTS"
    verbose_phrasing: bool = True
    use_bracketed_ui: bool = False

    def render(self, commentary_style="narrative") -> str:
        """Render the play-by-play log for this example game."""
        random.seed(self.seed)
        simulator = BaseballSimulator(
            copy.deepcopy(_BASE_TEAMS[self.home_team]),
            copy.deepcopy(_BASE_TEAMS[self.away_team]),
            verbose_phrasing=self.verbose_phrasing,
            use_bracketed_ui=self.use_bracketed_ui,
            commentary_style=commentary_style,
        )

        simulator.play_game()

        if commentary_style == "gameday":
            import json
            return json.dumps(simulator.play_events, indent=2)
        else:
            # Return buffered output for narrative/statcast
            return "\n".join(simulator.output_lines) + "\n"


EXAMPLE_GAMES: List[ExampleGame] = [
    ExampleGame(seed=101),
    ExampleGame(seed=202),
    ExampleGame(seed=303),
    ExampleGame(seed=404),
    ExampleGame(seed=505),
    ExampleGame(seed=606),
    ExampleGame(seed=707),
    ExampleGame(seed=808),
    ExampleGame(seed=909),
    ExampleGame(seed=1001),
]


def iter_example_paths(games: Iterable[ExampleGame] | None = None):
    """Yield the path for each example game file."""
    games = list(EXAMPLE_GAMES if games is None else games)
    for index, _ in enumerate(games, start=1):
        yield EXAMPLES_DIR / f"game_{index:02d}.txt"


__all__ = ["ExampleGame", "EXAMPLE_GAMES", "EXAMPLES_DIR", "iter_example_paths"]


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Render a specific example game.")
    parser.add_argument("game_number", type=int, help="Game number (1-10)")
    parser.add_argument("--commentary", type=str, choices=["narrative", "statcast", "gameday"], default="narrative", help="Commentary style")
    args = parser.parse_args()

    if args.game_number < 1 or args.game_number > len(EXAMPLE_GAMES):
        print(f"Error: game_number must be between 1 and {len(EXAMPLE_GAMES)}", file=sys.stderr)
        sys.exit(1)

    example = EXAMPLE_GAMES[args.game_number - 1]
    output = example.render(commentary_style=args.commentary)
    print(output, end="")
