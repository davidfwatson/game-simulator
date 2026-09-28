#!/usr/bin/env python3
"""Edit explicit commentary draws and play data in any PBP fixture.

Use ``--fixture PATH`` to select a file; example 3 is the default.
Draw lists have no length limit and never change timestamps::

    python fixture_utils.py --fixture fixture.json draws --play 0 --point event_0 'pitch=[3,7,12,4]'
    python fixture_utils.py --fixture fixture.json draws --point init 'color=[0,2,1]'
"""
import argparse
import json

FIXTURE = "test_fixture_pbp_example_3.json"


def load(fixture=None):
    with open(fixture or FIXTURE) as f:
        return json.load(f)


def save(data, fixture=None):
    with open(fixture or FIXTURE, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def set_draws(play_idx, point_type, *, fixture=None, **streams):
    """Replace selected stream lists at a point, preserving other streams."""
    from pbp_tools import STREAM_NAMES, get_rng_point

    if not streams:
        raise ValueError('Specify at least one stream of draws')
    if set(streams) - set(STREAM_NAMES):
        raise ValueError(f"Unknown RNG streams: {sorted(set(streams) - set(STREAM_NAMES))}")
    for name, draws in streams.items():
        if not isinstance(draws, list) or any(type(value) is not int or value < 0 for value in draws):
            raise ValueError(f"{name} draws must be a list of nonnegative integers")
    data = load(fixture)
    point = get_rng_point(data, play_idx, point_type)
    metadata = point['owner'].setdefault('commentaryRng', {}).setdefault(point['point'], {})
    metadata.update({name: list(draws) for name, draws in streams.items()})
    save(data, fixture)
    print(f"{point['json_path']}: {metadata}")


def set_zone(play_idx, event_idx, zone, *, fixture=None):
    """Set details.zone on a pitch event."""
    data = load(fixture)
    ev = data["liveData"]["plays"]["allPlays"][play_idx]["playEvents"][event_idx]
    old = ev["details"].get("zone")
    ev["details"]["zone"] = zone
    save(data, fixture)
    print(f"play {play_idx} event_{event_idx}: zone {old} → {zone}")


def set_hit_data(play_idx, event_idx=None, *, fixture=None, **kwargs):
    """Set hitData fields on a pitch event. If event_idx is None, uses the last event."""
    data = load(fixture)
    p = data["liveData"]["plays"]["allPlays"][play_idx]
    if event_idx is None:
        event_idx = len(p["playEvents"]) - 1
    ev = p["playEvents"][event_idx]
    if "hitData" not in ev:
        ev["hitData"] = {}
    for k, v in kwargs.items():
        ev["hitData"][k] = v
    save(data, fixture)
    print(f"play {play_idx} event_{event_idx}: hitData updated: {kwargs}")


def set_bat_side(play_idx, code, *, fixture=None):
    """Set the batter's bat side (L/R/S) for a play."""
    data = load(fixture)
    matchup = data["liveData"]["plays"]["allPlays"][play_idx]["matchup"]
    old = matchup["batSide"]["code"]
    desc = {"L": "Left", "R": "Right", "S": "Switch"}[code]
    matchup["batSide"]["code"] = code
    matchup["batSide"]["description"] = desc
    save(data, fixture)
    print(f"play {play_idx}: batSide {old} → {code}")


def set_pitch_hand(play_idx, code, *, fixture=None):
    """Set the pitcher's hand (L/R) for a play."""
    data = load(fixture)
    matchup = data["liveData"]["plays"]["allPlays"][play_idx]["matchup"]
    old = matchup["pitchHand"]["code"]
    desc = {"L": "Left", "R": "Right"}[code]
    matchup["pitchHand"]["code"] = code
    matchup["pitchHand"]["description"] = desc
    save(data, fixture)
    print(f"play {play_idx}: pitchHand {old} → {code}")


def set_pitch_type(play_idx, event_idx, pitch_type, *, fixture=None):
    """Set the pitch type description on a pitch event."""
    data = load(fixture)
    ev = data["liveData"]["plays"]["allPlays"][play_idx]["playEvents"][event_idx]
    old = ev["details"].get("type", {}).get("description", "")
    if "type" not in ev["details"]:
        ev["details"]["type"] = {}
    ev["details"]["type"]["description"] = pitch_type
    save(data, fixture)
    print(f"play {play_idx} event_{event_idx}: pitch {old} → {pitch_type}")


def set_pitch_code(play_idx, event_idx, code, *, fixture=None):
    """Set the pitch event code (B/S/C/F/X)."""
    data = load(fixture)
    ev = data["liveData"]["plays"]["allPlays"][play_idx]["playEvents"][event_idx]
    old = ev["details"].get("code", "")
    ev["details"]["code"] = code
    save(data, fixture)
    print(f"play {play_idx} event_{event_idx}: code {old} → {code}")


def show_play_data(play_idx, *, fixture=None):
    """Show key data for a play (zones, hitData, matchup)."""
    data = load(fixture)
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', default=FIXTURE, help='Fixture JSON to edit')
    commands = parser.add_subparsers(dest='command', required=True)
    show = commands.add_parser('show', help='Show play data')
    show.add_argument('plays', nargs='+', help='Play indices or ranges such as 21-26')
    draws = commands.add_parser('draws', help='Set explicit commentary draw lists')
    draws.add_argument('--play', type=int, help='Play index; omit for init')
    draws.add_argument('--point', required=True, help='init, play_start, event_N, or play_outcome')
    draws.add_argument('streams', nargs='+', help='stream=[draw,...] (quote for your shell)')
    zone = commands.add_parser('zone')
    zone.add_argument('play', type=int)
    zone.add_argument('event', type=int)
    zone.add_argument('zone', type=int)
    hit = commands.add_parser('hit-data')
    hit.add_argument('play', type=int)
    hit.add_argument('--event', type=int)
    hit.add_argument('fields', nargs='+', help='key=value hit data fields')
    for command in ('bat-side', 'pitch-hand', 'pitch-type', 'pitch-code'):
        action = commands.add_parser(command)
        action.add_argument('play', type=int)
        if command in ('pitch-type', 'pitch-code'):
            action.add_argument('event', type=int)
        action.add_argument('value')
    args = parser.parse_args()

    def key_values(items):
        result = {}
        for item in items:
            if '=' not in item:
                raise ValueError(f"Expected key=value, got {item!r}")
            key, value = item.split('=', 1)
            try:
                result[key] = json.loads(value)
            except json.JSONDecodeError:
                result[key] = value
        return result

    try:
        if args.command == 'draws':
            set_draws(args.play, args.point, fixture=args.fixture, **key_values(args.streams))
        elif args.command == 'show':
            for item in args.plays:
                if '-' in item:
                    start, end = map(int, item.split('-', 1))
                    indices = range(start, end + 1)
                else:
                    indices = [int(item)]
                for index in indices:
                    show_play_data(index, fixture=args.fixture)
        elif args.command == 'zone':
            set_zone(args.play, args.event, args.zone, fixture=args.fixture)
        elif args.command == 'hit-data':
            set_hit_data(args.play, args.event, fixture=args.fixture, **key_values(args.fields))
        elif args.command == 'bat-side':
            set_bat_side(args.play, args.value, fixture=args.fixture)
        elif args.command == 'pitch-hand':
            set_pitch_hand(args.play, args.value, fixture=args.fixture)
        elif args.command == 'pitch-type':
            set_pitch_type(args.play, args.event, args.value, fixture=args.fixture)
        elif args.command == 'pitch-code':
            set_pitch_code(args.play, args.event, args.value, fixture=args.fixture)
    except (ValueError, IndexError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
