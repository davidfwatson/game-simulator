import subprocess
import os

def main():
    """
    Generates a new snapshot of the gameday JSON output.
    This is used to update the "golden" file for regression testing.
    """
    snapshot_path = os.path.join('examples', 'gameday_snapshot.json')
    print(f"Generating new gameday snapshot at {snapshot_path}...")

    # We pipe to a file, so we don't have to deal with capturing large stdout.
    with open(snapshot_path, 'w') as f:
        subprocess.run(
            ['python3', 'baseball.py', '--commentary', 'gameday', '--game-seed', '1'],
            stdout=f,
            check=True
        )

    print("Snapshot generated successfully.")

if __name__ == "__main__":
    main()