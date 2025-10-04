"""Utilities for managing deterministic example game logs."""
from __future__ import annotations

import copy
import io
import random
from contextlib import redirect_stdout
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
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            simulator.play_game()
        return buffer.getvalue()


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
