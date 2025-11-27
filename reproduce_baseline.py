
import os
import json
import subprocess

def run_baseline():
    command = [
        "python3", "baseball.py",
        "--commentary", "gameday",
        "--game-seed", "42",
        "--commentary-seed", "100",
        "--gameday-outfile", "baseline_gameday.json"
    ]
    subprocess.run(command, check=True)

    command_pbp = [
        "python3", "baseball.py",
        "--commentary", "narrative",
        "--game-seed", "42",
        "--commentary-seed", "100",
        "--pbp-outfile", "baseline_pbp.txt"
    ]
    subprocess.run(command_pbp, check=True)

    command_statcast = [
        "python3", "baseball.py",
        "--commentary", "statcast",
        "--game-seed", "42",
        "--commentary-seed", "100",
        "--pbp-outfile", "baseline_statcast.txt"
    ]
    subprocess.run(command_statcast, check=True)

if __name__ == "__main__":
    run_baseline()
    print("Baseline files created: baseline_gameday.json, baseline_pbp.txt, baseline_statcast.txt")
