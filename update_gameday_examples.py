#!/usr/bin/env python3
"""
Update gameday example snapshots.

Generates compact gameday JSON snapshots for each example game by extracting
only representative plays. This keeps file sizes manageable while enabling
proper regression testing.
"""

import json
import subprocess
from pathlib import Path
from example_games import EXAMPLE_GAMES, EXAMPLES_DIR
from gameday_snapshot_extractor import create_snapshot_data


def main():
    """Generate compact gameday snapshots for all example games."""

    # Create gameday_snapshots directory if it doesn't exist
    snapshots_dir = EXAMPLES_DIR / "gameday_snapshots"
    snapshots_dir.mkdir(exist_ok=True)

    print(f"Generating gameday snapshots in {snapshots_dir}...")

    for i, example in enumerate(EXAMPLE_GAMES, start=1):
        print(f"  Processing game {i:02d}...", end=" ")

        # Generate full gameday JSON using run_simulation.py
        result = subprocess.run(
            [
                "python3",
                "run_simulation.py",
                "--game-seed",
                str(example.game_seed),
                "--commentary-seed",
                str(example.commentary_seed),
                "--output-style",
                "gameday"
            ],
            capture_output=True,
            text=True,
            check=True
        )

        # Parse the full gameday output
        gameday_data = json.loads(result.stdout)

        # Extract compact snapshot
        snapshot = create_snapshot_data(gameday_data, max_plays=6)

        # Write snapshot file
        snapshot_file = snapshots_dir / f"gameday_{i:02d}.json"
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot, f, indent=2)

        total_plays = snapshot['metadata']['totalPlaysInGame']
        snapshot_plays = snapshot['metadata']['snapshotPlayCount']
        print(f"✓ ({snapshot_plays}/{total_plays} plays)")

    print(f"\nSuccessfully generated {len(EXAMPLE_GAMES)} gameday snapshots.")
    print(f"Run 'pytest test_gameday_examples.py' to verify.")


if __name__ == "__main__":
    main()
