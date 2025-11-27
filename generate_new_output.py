
import os
import json
import subprocess

def run_new():
    command = [
        "python3", "baseball.py",
        "--commentary", "gameday",
        "--game-seed", "42",
        "--commentary-seed", "100",
        "--gameday-outfile", "new_gameday.json"
    ]
    subprocess.run(command, check=True)

    command_pbp = [
        "python3", "baseball.py",
        "--commentary", "narrative",
        "--game-seed", "42",
        "--commentary-seed", "100",
        "--pbp-outfile", "new_pbp.txt"
    ]
    subprocess.run(command_pbp, check=True)

    command_statcast = [
        "python3", "baseball.py",
        "--commentary", "statcast",
        "--game-seed", "42",
        "--commentary-seed", "100",
        "--pbp-outfile", "new_statcast.txt"
    ]
    subprocess.run(command_statcast, check=True)

if __name__ == "__main__":
    run_new()
    print("New files created: new_gameday.json, new_pbp.txt, new_statcast.txt")
