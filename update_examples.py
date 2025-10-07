"""Regenerate the checked-in example game logs.

Run `python update_examples.py` from the repository root to rebuild the
example logs in the ``examples`` directory.
"""
from __future__ import annotations

from pathlib import Path

from example_games import EXAMPLE_GAMES, EXAMPLES_DIR


def main() -> None:
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for index, game in enumerate(EXAMPLE_GAMES, start=1):
        output = game.render()
        path = EXAMPLES_DIR / f"game_{index:02d}.txt"
        path.write_text(output, encoding="utf-8")
        print(f"Wrote {path.relative_to(Path.cwd())}")


if __name__ == "__main__":
    main()
