"""Regenerate the checked-in statcast example game logs.

Run `python update_statcast_examples.py` from the repository root to rebuild the
statcast example logs in the ``examples`` directory.
"""
import subprocess
from pathlib import Path

from example_games import EXAMPLE_GAMES, EXAMPLES_DIR


def main() -> None:
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for index, game in enumerate(EXAMPLE_GAMES, start=1):
        path = EXAMPLES_DIR / f"statcast_game_{index:02d}.txt"
        with open(path, 'w', encoding="utf-8") as f:
            subprocess.run(
                [
                    "python3",
                    "run_simulation.py",
                    "--game-seed",
                    str(game.game_seed),
                    "--commentary-seed",
                    str(game.commentary_seed),
                    "--output-style",
                    "statcast"
                ],
                stdout=f,
                check=True,
            )
        print(f"Wrote {path.relative_to(Path.cwd())}")


if __name__ == "__main__":
    main()
