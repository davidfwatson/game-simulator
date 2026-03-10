#!/usr/bin/env python3
"""Utilities for editing test_fixture_pbp_example_3.json seed timestamps and play data."""
import json
import sys

FIXTURE = "test_fixture_pbp_example_3.json"


def load():
    with open(FIXTURE) as f:
        return json.load(f)


def save(data):
    with open(FIXTURE, "w") as f:
        json.dump(data, f, indent=2)


def pack_seed(play=0, pitch=0, flow=0, color=0):
    """Pack per-stream seeds into an 8-digit fractional second value."""
    return color * 1000000 + flow * 10000 + pitch * 100 + play


def set_event_seed(play_idx, event_idx, play=0, pitch=0, flow=0, color=0):
    """Set the seed on a pitch event's startTime."""
    data = load()
    p = data["liveData"]["plays"]["allPlays"][play_idx]
    ev = p["playEvents"][event_idx]
    # Preserve the base timestamp (seconds part)
    old_ts = ev["startTime"]
    base = old_ts.split(".")[0] if "." in old_ts else old_ts.rstrip("Z").split("+")[0]
    packed = pack_seed(play, pitch, flow, color)
    new_ts = f"{base}.{packed:08d}Z"
    ev["startTime"] = new_ts
    save(data)
    print(f"play {play_idx} event_{event_idx}: {old_ts} → {new_ts}")
    print(f"  seeds: play={play}, pitch={pitch}, flow={flow}, color={color}")


def set_outcome_seed(play_idx, play=0, pitch=0, flow=0, color=0):
    """Set the seed on a play's endTime (play_outcome seed point)."""
    data = load()
    p = data["liveData"]["plays"]["allPlays"][play_idx]
    old_ts = p["about"]["endTime"]
    base = old_ts.split(".")[0] if "." in old_ts else old_ts.rstrip("Z").split("+")[0]
    packed = pack_seed(play, pitch, flow, color)
    new_ts = f"{base}.{packed:08d}"
    p["about"]["endTime"] = new_ts
    save(data)
    print(f"play {play_idx} outcome: {old_ts} → {new_ts}")
    print(f"  seeds: play={play}, pitch={pitch}, flow={flow}, color={color}")


def set_play_start_seed(play_idx, play=0, pitch=0, flow=0, color=0):
    """Set the seed on a play's startTime (play_start seed point)."""
    data = load()
    p = data["liveData"]["plays"]["allPlays"][play_idx]
    old_ts = p["about"]["startTime"]
    # Strip timezone suffix first, then fractional seconds
    stripped = old_ts.replace("+00:00", "").rstrip("Z")
    base = stripped.split(".")[0]
    # play_start uses +00:00 suffix format
    packed = pack_seed(play, pitch, flow, color)
    new_ts = f"{base}.{packed:08d}+00:00"
    p["about"]["startTime"] = new_ts
    save(data)
    print(f"play {play_idx} start: {old_ts} → {new_ts}")
    print(f"  seeds: play={play}, pitch={pitch}, flow={flow}, color={color}")


def set_zone(play_idx, event_idx, zone):
    """Set details.zone on a pitch event."""
    data = load()
    ev = data["liveData"]["plays"]["allPlays"][play_idx]["playEvents"][event_idx]
    old = ev["details"].get("zone")
    ev["details"]["zone"] = zone
    save(data)
    print(f"play {play_idx} event_{event_idx}: zone {old} → {zone}")


def set_hit_data(play_idx, event_idx=None, **kwargs):
    """Set hitData fields on a pitch event. If event_idx is None, uses the last event."""
    data = load()
    p = data["liveData"]["plays"]["allPlays"][play_idx]
    if event_idx is None:
        event_idx = len(p["playEvents"]) - 1
    ev = p["playEvents"][event_idx]
    if "hitData" not in ev:
        ev["hitData"] = {}
    for k, v in kwargs.items():
        ev["hitData"][k] = v
    save(data)
    print(f"play {play_idx} event_{event_idx}: hitData updated: {kwargs}")


def set_bat_side(play_idx, code):
    """Set the batter's bat side (L/R/S) for a play."""
    data = load()
    matchup = data["liveData"]["plays"]["allPlays"][play_idx]["matchup"]
    old = matchup["batSide"]["code"]
    desc = {"L": "Left", "R": "Right", "S": "Switch"}[code]
    matchup["batSide"]["code"] = code
    matchup["batSide"]["description"] = desc
    save(data)
    print(f"play {play_idx}: batSide {old} → {code}")


def set_pitch_hand(play_idx, code):
    """Set the pitcher's hand (L/R) for a play."""
    data = load()
    matchup = data["liveData"]["plays"]["allPlays"][play_idx]["matchup"]
    old = matchup["pitchHand"]["code"]
    desc = {"L": "Left", "R": "Right"}[code]
    matchup["pitchHand"]["code"] = code
    matchup["pitchHand"]["description"] = desc
    save(data)
    print(f"play {play_idx}: pitchHand {old} → {code}")


def set_pitch_type(play_idx, event_idx, pitch_type):
    """Set the pitch type description on a pitch event."""
    data = load()
    ev = data["liveData"]["plays"]["allPlays"][play_idx]["playEvents"][event_idx]
    old = ev["details"].get("type", {}).get("description", "")
    if "type" not in ev["details"]:
        ev["details"]["type"] = {}
    ev["details"]["type"]["description"] = pitch_type
    save(data)
    print(f"play {play_idx} event_{event_idx}: pitch {old} → {pitch_type}")


def set_pitch_code(play_idx, event_idx, code):
    """Set the pitch event code (B/S/C/F/X)."""
    data = load()
    ev = data["liveData"]["plays"]["allPlays"][play_idx]["playEvents"][event_idx]
    old = ev["details"].get("code", "")
    ev["details"]["code"] = code
    save(data)
    print(f"play {play_idx} event_{event_idx}: code {old} → {code}")


def show_play_data(play_idx):
    """Show key data for a play (zones, hitData, matchup)."""
    data = load()
    p = data["liveData"]["plays"]["allPlays"][play_idx]
    matchup = p["matchup"]
    print(f"Play {play_idx}: {matchup['batter']['fullName']} vs {matchup['pitcher']['fullName']}")
    print(f"  batSide={matchup['batSide']['code']} pitchHand={matchup['pitchHand']['code']}")
    print(f"  result={p['result']['event']}")
    for i, ev in enumerate(p["playEvents"]):
        d = ev["details"]
        hd = ev.get("hitData", {})
        ts = ev.get("startTime", "?")
        print(f"  event_{i}: code={d.get('code')} zone={d.get('zone')} pitch={d.get('type',{}).get('description','')} ts={ts}")
        if hd:
            print(f"    hitData: {hd}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  fixture_utils.py show PLAY")
        print("  fixture_utils.py event-seed PLAY EVENT [play=N] [pitch=N] [flow=N] [color=N]")
        print("  fixture_utils.py outcome-seed PLAY [play=N] [pitch=N] [flow=N] [color=N]")
        print("  fixture_utils.py start-seed PLAY [play=N] [pitch=N] [flow=N] [color=N]")
        print("  fixture_utils.py zone PLAY EVENT ZONE")
        print("  fixture_utils.py hit-data PLAY [event=N] key=val ...")
        print("  fixture_utils.py bat-side PLAY CODE")
        print("  fixture_utils.py pitch-hand PLAY CODE")
        sys.exit(0)

    cmd = sys.argv[1]

    def parse_kwargs(args):
        kw = {}
        for a in args:
            if "=" in a:
                k, v = a.split("=", 1)
                try:
                    v = int(v)
                except ValueError:
                    try:
                        v = float(v)
                    except ValueError:
                        pass
                kw[k] = v
        return kw

    if cmd == "show":
        show_play_data(int(sys.argv[2]))
    elif cmd == "event-seed":
        kw = parse_kwargs(sys.argv[4:])
        set_event_seed(int(sys.argv[2]), int(sys.argv[3]), **kw)
    elif cmd == "outcome-seed":
        kw = parse_kwargs(sys.argv[3:])
        set_outcome_seed(int(sys.argv[2]), **kw)
    elif cmd == "start-seed":
        kw = parse_kwargs(sys.argv[3:])
        set_play_start_seed(int(sys.argv[2]), **kw)
    elif cmd == "zone":
        set_zone(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]))
    elif cmd == "hit-data":
        play_idx = int(sys.argv[2])
        kw = parse_kwargs(sys.argv[3:])
        event_idx = kw.pop("event", None)
        if event_idx is not None:
            event_idx = int(event_idx)
        set_hit_data(play_idx, event_idx, **kw)
    elif cmd == "bat-side":
        set_bat_side(int(sys.argv[2]), sys.argv[3])
    elif cmd == "pitch-hand":
        set_pitch_hand(int(sys.argv[2]), sys.argv[3])
    elif cmd == "pitch-type":
        set_pitch_type(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    elif cmd == "pitch-code":
        set_pitch_code(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
