import json
import datetime
import sys

def parse_time(t_str):
    # Python 3.11+ handles 'Z' with fromisoformat, but to be safe across versions (if I was unsure, but I know it's 3.12):
    # Actually 3.12 handles Z fine.
    try:
        return datetime.datetime.fromisoformat(t_str)
    except ValueError:
        # Fallback for older pythons or if format slightly off
        if t_str.endswith('Z'):
            t_str = t_str[:-1] + '+00:00'
        return datetime.datetime.fromisoformat(t_str)

def analyze(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)

    all_plays = data['liveData']['plays']['allPlays']

    pitch_diffs = []
    at_bat_diffs = []
    inning_diffs = []

    prev_play_end = None
    prev_inning = None
    prev_half = None

    print(f"Analyzing {len(all_plays)} plays...")

    for i, play in enumerate(all_plays):
        # At Bat Timing
        about = play['about']
        start_time = parse_time(about['startTime'])
        end_time = parse_time(about['endTime'])

        inning = about['inning']
        half = about['halfInning']

        if prev_play_end:
            diff = (start_time - prev_play_end).total_seconds()

            is_new_inning = (inning != prev_inning) or (half != prev_half)

            if is_new_inning:
                inning_diffs.append(diff)
                # print(f"Inning change: {diff}s")
            else:
                at_bat_diffs.append(diff)
                # print(f"At Bat change: {diff}s")

        # Pitch Timing
        play_events = play.get('playEvents', [])
        prev_pitch_start = None

        # Filter only pitch events
        pitch_events = [e for e in play_events if e.get('isPitch')]

        for p_event in pitch_events:
            p_start = parse_time(p_event['startTime'])

            if prev_pitch_start:
                p_diff = (p_start - prev_pitch_start).total_seconds()
                pitch_diffs.append(p_diff)
                # print(f"  Pitch diff: {p_diff}s")

            prev_pitch_start = p_start

        prev_play_end = end_time
        prev_inning = inning
        prev_half = half

    def stats(name, arr):
        if not arr:
            print(f"{name}: No data")
            return
        avg = sum(arr) / len(arr)
        med = sorted(arr)[len(arr)//2]
        mn = min(arr)
        mx = max(arr)
        print(f"{name}: Count={len(arr)}, Avg={avg:.2f}s, Median={med:.2f}s, Min={mn:.2f}s, Max={mx:.2f}s")

    stats("Pitch-to-Pitch", pitch_diffs)
    stats("Between At-Bats", at_bat_diffs)
    stats("Between Innings", inning_diffs)

if __name__ == "__main__":
    analyze("real_gameday.json")
