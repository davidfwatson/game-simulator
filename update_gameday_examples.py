"""Regenerate the checked-in Gameday example game logs.

Run `python update_gameday_examples.py` from the repository root to rebuild the
Gameday example logs in the ``examples`` directory.
"""
from __future__ import annotations

import json
from pathlib import Path

from example_games import EXAMPLE_GAMES, EXAMPLES_DIR


def main() -> None:
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for index, game in enumerate(EXAMPLE_GAMES, start=1):
        output = game.render(commentary_style="gameday")

        # The output is a JSON string, so we parse it to re-format it nicely.
        # This ensures consistent formatting in the snapshot files.
        try:
            parsed_json = json.loads(output)
            formatted_output = json.dumps(parsed_json, indent=2)
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON for game {index}")
            formatted_output = output

        path = EXAMPLES_DIR / f"gameday_game_{index:02d}.json"
        path.write_text(formatted_output, encoding="utf-8")
        print(f"Wrote {path.relative_to(Path.cwd())}")


if __name__ == "__main__":
    main()