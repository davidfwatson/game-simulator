"""Utilities for managing deterministic example game logs."""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from baseball import BaseballSimulator
from gameday_converter import GamedayConverter
from teams import TEAMS


_BASE_TEAMS = {key: copy.deepcopy(value) for key, value in TEAMS.items()}


EXAMPLES_DIR = Path(__file__).parent / "examples"


@dataclass(frozen=True)
class ExampleGame:
    seed: int | None = None
    home_team: str = "BAY_BOMBERS"
    away_team: str = "PC_PILOTS"
    verbose_phrasing: bool = True
    use_bracketed_ui: bool = False
    game_seed: int | None = None
    commentary_seed: int | None = None


    def render(self, commentary_style="narrative") -> str:
        """Render the play-by-play log for this example game."""
        game_seed = self.game_seed if self.game_seed is not None else self.seed
        commentary_seed = self.commentary_seed if self.commentary_seed is not None else self.seed
        simulator = BaseballSimulator(
            copy.deepcopy(_BASE_TEAMS[self.home_team]),
            copy.deepcopy(_BASE_TEAMS[self.away_team]),
            game_seed=game_seed,
            commentary_seed=commentary_seed,
        )

        gameday_data = simulator.play_game()

        if commentary_style == "gameday":
            return json.dumps(gameday_data, indent=2)
        else:
            converter = GamedayConverter(
                gameday_data,
                commentary_style=commentary_style,
                verbose_phrasing=self.verbose_phrasing,
                use_bracketed_ui=self.use_bracketed_ui,
                commentary_seed=commentary_seed
            )
            return converter.convert() + "\n"


EXAMPLE_GAMES: List[ExampleGame] = [
    ExampleGame(game_seed=101, commentary_seed=202),
    ExampleGame(game_seed=202, commentary_seed=303),
    ExampleGame(game_seed=303, commentary_seed=404),
    ExampleGame(game_seed=404, commentary_seed=505),
    ExampleGame(game_seed=505, commentary_seed=606),
    ExampleGame(game_seed=606, commentary_seed=707),
    ExampleGame(game_seed=707, commentary_seed=808),
    ExampleGame(game_seed=808, commentary_seed=909),
    ExampleGame(game_seed=909, commentary_seed=1001),
    ExampleGame(game_seed=1001, commentary_seed=1102),
]


def iter_example_paths(games: Iterable[ExampleGame] | None = None):
    """Yield the path for each example game file."""
    games = list(EXAMPLE_GAMES if games is None else games)
    for index, _ in enumerate(games, start=1):
        yield EXAMPLES_DIR / f"game_{index:02d}.txt"


__all__ = ["ExampleGame", "EXAMPLE_GAMES", "EXAMPLES_DIR", "iter_example_paths"]
