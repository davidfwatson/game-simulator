#!/usr/bin/env python3
"""
Stitch draft_innings_example_1/inning_{1-9}.json into test_fixture_pbp_example_1.json.

Builds the fixture from scratch (no existing fixture needed) for the
Cadillac Cars vs Big Rapids Timbers game (pbp_example_1.txt).
"""

import json
import os
import copy
from datetime import datetime, timedelta

# ── Player ID map ──────────────────────────────────────────────────────
# Away (Cadillac Cars) batters
PLAYER_IDS = {
    "Pinky Slauson":       800001,
    "Gabriel Palomar":     800002,
    "Shiny Patterson":     800003,
    "Philip Nakamura":     800004,
    "Gilligan Parker":     800005,
    "Fritz Ortega":        800006,
    "Giovanni Gasparro":   800007,
    "Flipper Cortez":      800008,
    "Virgil Hughes":       800009,  # as batter
    # Home (Big Rapids Timbers) batters
    "Dutch Moon":          800101,
    "Rio Nunez":           800102,
    "Keith Castor":        800103,
    "Randy Chang":         800104,
    "Brink Filbert":       800105,
    "Jesus Ferguson":      800106,
    "Blink Rudderson":    800107,
    "Henny Oldman":        800108,
    "Javier Von Neumann":  800109,  # as batter
    # Pitchers (on mound, same IDs when pitcher == batter)
    "Virgil Hughes_P":     800009,
    "Javier Von Neumann_P": 800109,
    "Royce Babcock":       800110,
}

# Bat side for each player
BAT_SIDES = {
    800001: ("R", "Right"),   # Slauson
    800002: ("R", "Right"),   # Palomar
    800003: ("S", "Switch"),  # Patterson
    800004: ("R", "Right"),   # Nakamura
    800005: ("L", "Left"),    # Parker
    800006: ("R", "Right"),   # Ortega
    800007: ("R", "Right"),   # Gasparro
    800008: ("S", "Switch"),  # Cortez
    800009: ("R", "Right"),   # Hughes
    800101: ("R", "Right"),   # Moon
    800102: ("S", "Switch"),  # Nunez
    800103: ("R", "Right"),   # Castor
    800104: ("R", "Right"),   # Chang
    800105: ("R", "Right"),   # Filbert
    800106: ("R", "Right"),   # Ferguson
    800107: ("R", "Right"),   # Rudderson
    800108: ("R", "Right"),   # Oldman
    800109: ("R", "Right"),   # Von Neumann
    800110: ("L", "Left"),    # Babcock
}

# Pitch hand for pitchers
PITCH_HANDS = {
    800009: ("R", "Right"),   # Hughes
    800109: ("R", "Right"),   # Von Neumann
    800110: ("L", "Left"),    # Babcock
}

# Pitch type name -> MLB code
PITCH_TYPE_MAP = {
    "Fastball": ("FF", "Fastball"),
    "Slider": ("SL", "Slider"),
    "Curveball": ("CU", "Curveball"),
    "Slow Curve": ("CU", "Curveball"),
    "Changeup": ("CH", "Changeup"),
    "Breaking Ball": ("CU", "Curveball"),
    "Breaking ball": ("CU", "Curveball"),
    "Offspeed": ("CH", "Changeup"),
    "off-speed": ("CH", "Changeup"),
    "Unknown": ("FF", "Fastball"),
    "unknown": ("FF", "Fastball"),
}

# Event name -> eventType
EVENT_TYPE_MAP = {
    "Single": "single",
    "Double": "double",
    "Triple": "triple",
    "Home Run": "home_run",
    "Walk": "walk",
    "Strikeout": "strikeout",
    "Called Strikeout": "strikeout",
    "Groundout": "field_out",
    "Flyout": "field_out",
    "Pop Out": "field_out",
    "Popout": "field_out",
    "Pop out": "field_out",
    "Double Play": "grounded_into_double_play",
    "Grounded into Double Play (6-4-3)": "grounded_into_double_play",
    "Grounded Into Double Play": "grounded_into_double_play",
    "Groundout (Unassisted)": "field_out",
    "Groundout (5-3)": "field_out",
    "Groundout (pitcher to first, 1-3)": "field_out",
    "Groundout (third to first, 5-3)": "field_out",
    "Groundout (unassisted)": "field_out",
    "Flyout to right field (RF)": "field_out",
    "Reached on Error": "field_error",
    "Caught Stealing 2B / Single": "single",
    "Out (1-2-3 inning summary, no pitch detail)": "field_out",
}


def get_pitcher_id(pitcher_name, inning, is_top):
    """Get the pitcher's mound ID based on game context."""
    if is_top:
        # Top of inning: home team pitches
        if pitcher_name == "Javier Von Neumann":
            return 800109
        elif pitcher_name == "Royce Babcock":
            return 800110
    else:
        # Bottom of inning: away team pitches
        if pitcher_name == "Virgil Hughes":
            return 800009
    # fallback
    return PLAYER_IDS.get(pitcher_name, PLAYER_IDS.get(pitcher_name + "_P", 0))


def get_batter_id(batter_name):
    """Get the batter's ID."""
    return PLAYER_IDS.get(batter_name, 0)


def pitch_code_to_details(code, pitch_type_name):
    """Convert a pitch code and type name to playEvent details."""
    pt_code, pt_desc = PITCH_TYPE_MAP.get(pitch_type_name, ("FF", "Fastball"))

    code_map = {
        "B": ("B", "Ball", False),
        "S": ("S", "Swinging Strike", True),
        "C": ("C", "Called Strike", True),
        "F": ("F", "Foul", True),
        "X": ("X", "In play", True),
        "D": ("D", "In play", True),
        "H": ("H", "In play", True),
    }
    p_code, p_desc, is_strike = code_map.get(code, ("B", "Ball", False))

    # For X/D/H codes, adjust description based on event
    if code in ("X", "D", "H"):
        p_desc = "In play, no out"  # Will be overridden per-play

    return {
        "code": p_code,
        "description": p_desc,
        "isStrike": is_strike,
        "type": {
            "code": pt_code,
            "description": pt_desc,
        },
        "zone": 5 if is_strike else 14,
    }


def make_play_events(pitch_sequence, event_name, base_time):
    """Convert pitch sequence to playEvents array."""
    events = []
    balls = 0
    strikes = 0

    for i, pitch in enumerate(pitch_sequence):
        code = pitch.get("code", "B")
        pitch_type = pitch.get("pitchType", "Unknown")
        details = pitch_code_to_details(code, pitch_type)

        # For the last pitch that's in play, update description
        is_last = (i == len(pitch_sequence) - 1)
        if code in ("X", "D", "H") and is_last:
            details["description"] = f"In play, {event_name}"

        # Generate timestamp for this pitch event
        pitch_time = base_time + timedelta(seconds=i * 0.5)
        ts = pitch_time.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"

        pt_code, pt_desc = PITCH_TYPE_MAP.get(pitch_type, ("FF", "Fastball"))

        event = {
            "index": i,
            "isPitch": True,
            "count": {
                "balls": balls,
                "strikes": strikes,
            },
            "details": details,
            "pitchData": {
                "startSpeed": 92.5 if pt_code == "FF" else 85.0 if pt_code in ("SL", "CU") else 83.0,
                "zone": details["zone"],
            },
            "startTime": ts,
        }

        # Add hitData for the final pitch if it's in play
        if code in ("X", "D", "H") and is_last:
            event["hitData"] = None  # Will be set by caller

        events.append(event)

        # Update count
        if code == "B":
            balls += 1
        elif code in ("S", "C"):
            strikes = min(strikes + 1, 2)
        elif code == "F":
            if strikes < 2:
                strikes += 1
        # X/D/H don't change count

    return events, balls, strikes


def base_to_str(base):
    """Convert base names to standard format."""
    mapping = {
        "home": None, "batter": None, "HP": None,
        "1B": "1B", "1st": "1B", "first": "1B",
        "2B": "2B", "2nd": "2B", "second": "2B",
        "3B": "3B", "3rd": "3B", "third": "3B",
    }
    if base is None:
        return None
    return mapping.get(base, base)


def make_runners(runner_movements, event_name, fielders, batter_name):
    """Convert runner movement data to runners array."""
    runners = []
    event_type = EVENT_TYPE_MAP.get(event_name, "field_out")

    for rm in runner_movements:
        runner_name = rm.get("runner", "")
        start = rm.get("start", "home")
        end = rm.get("end", "")
        scored = rm.get("scored", False)

        origin_base = base_to_str(start)
        end_base = base_to_str(end)

        is_out = "out" in end.lower() if isinstance(end, str) else False
        out_base = None

        if is_out:
            # Parse out location
            if "2B" in end or "second" in end:
                out_base = "2B"
            elif "1B" in end or "first" in end:
                out_base = "1B"
            elif "3B" in end or "third" in end:
                out_base = "3B"
            end_base = None

        if scored or end == "home":
            end_base = "score"
            is_out = False

        runner_id = get_batter_id(runner_name)

        # Build credits for outs
        credits = []
        if is_out:
            for f in fielders:
                role = f.get("role", "")
                fname = f.get("name", "")
                fid = get_batter_id(fname)
                if "putout" in role.lower():
                    credits.append({
                        "player": {"id": fid, "link": f"/api/v1/people/{fid}"},
                        "credit": "f_putout",
                    })
                elif "assist" in role.lower():
                    credits.append({
                        "player": {"id": fid, "link": f"/api/v1/people/{fid}"},
                        "credit": "f_assist",
                    })

        runner_entry = {
            "movement": {
                "originBase": origin_base,
                "start": origin_base,
                "end": end_base,
                "outBase": out_base,
                "isOut": is_out,
            },
            "details": {
                "event": event_name,
                "eventType": event_type,
                "movementReason": "r_adv_play" if origin_base else None,
                "runner": {
                    "id": runner_id,
                    "fullName": runner_name,
                    "link": f"/api/v1/people/{runner_id}",
                },
                "isScoringEvent": scored or end_base == "score",
            },
            "credits": credits,
        }
        runners.append(runner_entry)

    # If no runner movements listed but it's an out (no baserunner involvement),
    # we still need the batter's out record
    if not runner_movements:
        event_type = EVENT_TYPE_MAP.get(event_name, "field_out")
        if event_type in ("field_out", "strikeout"):
            # Batter is out
            batter_id = get_batter_id(batter_name)
            credits = []
            for f in fielders:
                role = f.get("role", "")
                fname = f.get("name", "")
                fid = get_batter_id(fname)
                if "putout" in role.lower() or "unassisted" in role.lower():
                    credits.append({
                        "player": {"id": fid, "link": f"/api/v1/people/{fid}"},
                        "credit": "f_putout",
                    })
                elif "assist" in role.lower():
                    credits.append({
                        "player": {"id": fid, "link": f"/api/v1/people/{fid}"},
                        "credit": "f_assist",
                    })
                elif "fielder" in role.lower() and "no play" not in role.lower():
                    credits.append({
                        "player": {"id": fid, "link": f"/api/v1/people/{fid}"},
                        "credit": "f_assist",
                    })

            runners.append({
                "movement": {
                    "originBase": None,
                    "start": None,
                    "end": None,
                    "outBase": "1B",
                    "isOut": True,
                },
                "details": {
                    "event": event_name,
                    "eventType": event_type,
                    "movementReason": None,
                    "runner": {
                        "id": batter_id,
                        "fullName": batter_name,
                        "link": f"/api/v1/people/{batter_id}",
                    },
                    "isScoringEvent": False,
                },
                "credits": credits,
            })
    else:
        # Check if the batter reaching is already covered
        batter_covered = any(
            rm.get("runner", "") == batter_name or
            rm.get("start", "") in ("home", "batter", "HP")
            for rm in runner_movements
        )
        if not batter_covered:
            # Batter made contact but isn't in the runner list - they're out at first
            batter_id = get_batter_id(batter_name)
            credits = []
            for f in fielders:
                role = f.get("role", "")
                fname = f.get("name", "")
                fid = get_batter_id(fname)
                if "putout" in role.lower():
                    credits.append({
                        "player": {"id": fid, "link": f"/api/v1/people/{fid}"},
                        "credit": "f_putout",
                    })
                elif "assist" in role.lower():
                    credits.append({
                        "player": {"id": fid, "link": f"/api/v1/people/{fid}"},
                        "credit": "f_assist",
                    })

    return runners


def get_hit_data(draft_play):
    """Extract hitData from draft play."""
    hd = draft_play.get("hitData")
    if not hd:
        return None
    traj = hd.get("trajectory", "")
    loc = hd.get("location", "")
    if not traj and not loc:
        return None
    return {
        "trajectory": traj.lower().replace(" ", "_") if traj else "ground_ball",
        "location": loc,
    }


def is_scoring_event(event_name):
    """Check if an event type typically scores runs."""
    return False  # Determined by runner movements instead


def count_outs_in_play(draft_play):
    """Count how many outs result from this play."""
    event = draft_play["result"]["event"]
    event_lower = event.lower()

    if "double play" in event_lower:
        return 2
    if "triple play" in event_lower:
        return 3

    # Check runner movements for outs
    outs = 0
    for rm in draft_play.get("runnerMovement", []):
        end = rm.get("end", "")
        if "out" in end.lower():
            outs += 1

    # If it's a standard out event and no runners were put out
    if outs == 0:
        et = EVENT_TYPE_MAP.get(event, "")
        if et in ("field_out", "strikeout"):
            outs = 1

    # Special: caught stealing combined with single
    if "Caught Stealing" in event and "Single" in event:
        outs = 1  # One out from CS, batter reaches

    return outs


def runs_scored_in_play(draft_play):
    """Count runs scored in this play."""
    runs = 0
    for rm in draft_play.get("runnerMovement", []):
        if rm.get("scored", False):
            runs += 1
        elif rm.get("end") == "home":
            runs += 1
    return runs


def determine_post_on_bases(runners_on_base):
    """Given current runners dict {base: player_name}, return postOn fields."""
    result = {}
    for base in ("1B", "2B", "3B"):
        if base in runners_on_base:
            name = runners_on_base[base]
            pid = get_batter_id(name)
            result[f"postOn{base_word(base)}"] = {
                "id": pid,
                "fullName": name,
                "link": f"/api/v1/people/{pid}",
            }
    return result


def base_word(base):
    return {"1B": "First", "2B": "Second", "3B": "Third"}.get(base, base)


def men_on_base_str(runners):
    """Get splits menOnBase string."""
    if not runners:
        return "Empty"
    bases = set(runners.keys())
    if bases == {"1B", "2B", "3B"}:
        return "Loaded"
    if "1B" in bases and "3B" in bases:
        return "RISP"
    if "2B" in bases or "3B" in bases:
        return "RISP"
    if "1B" in bases:
        return "Men_On"
    return "Empty"


def load_draft_innings():
    """Load all draft inning JSON files."""
    all_plays = []
    for i in range(1, 10):
        path = f"draft_innings_example_1/inning_{i}.json"
        if os.path.exists(path):
            with open(path) as f:
                plays = json.load(f)
                all_plays.extend(plays)
    return all_plays


def make_player_entry(pid, full_name, first_name, last_name, primary_pos_code,
                      primary_pos_name, primary_pos_abbrev, bat_side_code,
                      bat_side_desc, pitch_hand_code, pitch_hand_desc):
    """Create a player entry for gameData.players."""
    return {
        "id": pid,
        "fullName": full_name,
        "link": f"/api/v1/people/{pid}",
        "firstName": first_name,
        "lastName": last_name,
        "primaryNumber": str(pid % 100),
        "birthDate": "1998-01-01",
        "currentAge": 28,
        "birthCity": "Sim City",
        "birthStateProvince": "CA",
        "birthCountry": "USA",
        "height": "6' 0\"",
        "weight": 200,
        "active": True,
        "primaryPosition": {
            "code": primary_pos_code,
            "name": primary_pos_name,
            "abbreviation": primary_pos_abbrev,
        },
        "useName": first_name,
        "useLastName": last_name,
        "middleName": "",
        "boxscoreName": last_name,
        "gender": "M",
        "isPlayer": True,
        "isVerified": False,
        "draftYear": 2019,
        "mlbDebutDate": "2022-04-01",
        "batSide": {"code": bat_side_code, "description": bat_side_desc},
        "pitchHand": {"code": pitch_hand_code, "description": pitch_hand_desc},
        "strikeZoneTop": 3.5,
        "strikeZoneBottom": 1.5,
    }


def build_game_data():
    """Build gameData from scratch for Cars vs Timbers."""
    players = {}

    # Away team: Cadillac Cars
    away_players = [
        (800001, "Pinky Slauson", "Pinky", "Slauson", "6", "Shortstop", "SS"),
        (800002, "Gabriel Palomar", "Gabriel", "Palomar", "9", "Outfielder", "RF"),
        (800003, "Shiny Patterson", "Shiny", "Patterson", "5", "Third Baseman", "3B"),
        (800004, "Philip Nakamura", "Philip", "Nakamura", "3", "First Baseman", "1B"),
        (800005, "Gilligan Parker", "Gilligan", "Parker", "7", "Outfielder", "LF"),
        (800006, "Fritz Ortega", "Fritz", "Ortega", "8", "Outfielder", "CF"),
        (800007, "Giovanni Gasparro", "Giovanni", "Gasparro", "2", "Catcher", "C"),
        (800008, "Flipper Cortez", "Flipper", "Cortez", "4", "Second Baseman", "2B"),
        (800009, "Virgil Hughes", "Virgil", "Hughes", "1", "Pitcher", "P"),
    ]

    for pid, full, first, last, pos_code, pos_name, pos_abbrev in away_players:
        bat_code, bat_desc = BAT_SIDES[pid]
        ph_code, ph_desc = PITCH_HANDS.get(pid, ("R", "Right"))
        players[f"ID{pid}"] = make_player_entry(
            pid, full, first, last, pos_code, pos_name, pos_abbrev,
            bat_code, bat_desc, ph_code, ph_desc,
        )

    # Home team: Big Rapids Timbers
    home_players = [
        (800101, "Dutch Moon", "Dutch", "Moon", "8", "Outfielder", "CF"),
        (800102, "Rio Nunez", "Rio", "Nunez", "6", "Shortstop", "SS"),
        (800103, "Keith Castor", "Keith", "Castor", "3", "First Baseman", "1B"),
        (800104, "Randy Chang", "Randy", "Chang", "9", "Outfielder", "RF"),
        (800105, "Brink Filbert", "Brink", "Filbert", "7", "Outfielder", "LF"),
        (800106, "Jesus Ferguson", "Jesus", "Ferguson", "4", "Second Baseman", "2B"),
        (800107, "Blink Rudderson", "Blink", "Rudderson", "5", "Third Baseman", "3B"),
        (800108, "Henny Oldman", "Henny", "Oldman", "2", "Catcher", "C"),
        (800109, "Javier Von Neumann", "Javier", "Von Neumann", "1", "Pitcher", "P"),
        (800110, "Royce Babcock", "Royce", "Babcock", "1", "Pitcher", "P"),
    ]

    for pid, full, first, last, pos_code, pos_name, pos_abbrev in home_players:
        bat_code, bat_desc = BAT_SIDES[pid]
        ph_code, ph_desc = PITCH_HANDS.get(pid, ("R", "Right"))
        players[f"ID{pid}"] = make_player_entry(
            pid, full, first, last, pos_code, pos_name, pos_abbrev,
            bat_code, bat_desc, ph_code, ph_desc,
        )

    game_data = {
        "game": {
            "pk": 800001,
            "type": "R",
            "doubleHeader": "N",
            "id": "2025/09/27/cadmlb-brtmlb-1",
            "gamedayType": "P",
            "tiebreaker": "N",
            "gameNumber": 1,
            "calendarEventID": "14-800001-2025-09-27",
            "season": "2025",
            "seasonDisplay": "2025",
        },
        "datetime": {
            "dateTime": "2025-09-27T23:05:00Z",
            "originalDate": "2025-09-27",
            "officialDate": "2025-09-27",
            "dayNight": "night",
            "time": "7:05",
            "ampm": "PM",
        },
        "status": {
            "abstractGameState": "Final",
            "codedGameState": "F",
            "detailedState": "Final",
            "statusCode": "F",
            "startTimeTBD": False,
            "abstractGameCode": "F",
        },
        "teams": {
            "away": {
                "id": 800,
                "name": "Cadillac Cars",
                "teamName": "Cars",
                "abbreviation": "CAD",
                "link": "/api/v1/teams/800",
            },
            "home": {
                "id": 801,
                "name": "Big Rapids Timbers",
                "teamName": "Timbers",
                "abbreviation": "BRT",
                "link": "/api/v1/teams/801",
            },
        },
        "players": players,
        "venue": "Evergreen Field",
        "weather": "71 degrees at game time. With a gentle breeze blowing in from left field.",
        "directMode": True,
    }

    return game_data


def build_boxscore(all_plays, draft_plays):
    """Build a minimal boxscore structure needed by the renderer."""
    # Away batting order (Cadillac Cars)
    away_batting_order = [800001, 800002, 800003, 800004, 800005, 800006, 800007, 800008, 800009]
    # Home batting order (Big Rapids Timbers)
    home_batting_order = [800101, 800102, 800103, 800104, 800105, 800106, 800107, 800108, 800109]

    def make_box_player(pid):
        """Create a minimal boxscore player entry."""
        # Find player name from PLAYER_IDS
        name = None
        for n, i in PLAYER_IDS.items():
            if i == pid and not n.endswith("_P"):
                name = n
                break
        if not name:
            name = f"Player {pid}"

        return {
            "person": {
                "id": pid,
                "fullName": name,
                "link": f"/api/v1/people/{pid}",
            },
            "position": {
                "code": "1",
                "name": "Pitcher",
                "abbreviation": "P",
            },
            "status": {"code": "A", "description": "Active"},
            "stats": {"batting": {}, "pitching": {}},
            "battingOrder": "100",
        }

    away_players = {}
    for pid in away_batting_order:
        away_players[f"ID{pid}"] = make_box_player(pid)

    home_players = {}
    for pid in home_batting_order:
        home_players[f"ID{pid}"] = make_box_player(pid)
    # Add relief pitcher
    home_players["ID800110"] = make_box_player(800110)

    return {
        "teams": {
            "away": {
                "team": {
                    "id": 800,
                    "name": "Cadillac Cars",
                    "abbreviation": "CAD",
                    "teamName": "Cars",
                },
                "players": away_players,
                "batters": away_batting_order,
                "pitchers": [800009],
                "bench": [],
                "bullpen": [],
                "battingOrder": away_batting_order,
            },
            "home": {
                "team": {
                    "id": 801,
                    "name": "Big Rapids Timbers",
                    "abbreviation": "BRT",
                    "teamName": "Timbers",
                },
                "players": home_players,
                "batters": home_batting_order,
                "pitchers": [800109, 800110],
                "bench": [],
                "bullpen": [],
                "battingOrder": home_batting_order,
            },
        },
        "officials": [],
        "info": [],
        "pitchingNotes": [],
    }


def build_fixture():
    """Build the fixture JSON from scratch."""
    # Build gameData from scratch
    game_data = build_game_data()

    fixture = {
        "gameData": game_data,
        "liveData": {
            "plays": {
                "allPlays": [],
                "currentPlay": None,
                "scoringPlays": [],
            },
            "linescore": {},
            "boxscore": {},
        },
    }

    # Load draft plays
    draft_plays = load_draft_innings()

    # Build allPlays
    all_plays = []
    game_time = datetime(2025, 9, 27, 23, 5, 0)
    at_bat_index = 0
    away_score = 0
    home_score = 0
    current_outs = 0
    runners_on_base = {}  # {base: player_name}

    # Track per-inning runs for linescore
    inning_runs = {}  # (inning, is_top) -> runs

    prev_inning = None
    prev_is_top = None

    for draft_play in draft_plays:
        inning = draft_play["inning"]
        is_top = draft_play.get("isTopInning", True)
        batter_name = draft_play["batter"]["fullName"]
        pitcher_name = draft_play["pitcher"]["fullName"]
        event_name = draft_play["result"]["event"]
        rbi = draft_play["result"].get("rbi", 0)

        # Reset outs and runners on half-inning change
        if (inning, is_top) != (prev_inning, prev_is_top):
            current_outs = 0
            runners_on_base = {}
            prev_inning = inning
            prev_is_top = is_top

        # Get IDs
        batter_id = get_batter_id(batter_name)
        pitcher_id = get_pitcher_id(pitcher_name, inning, is_top)

        # Bat side
        bat_code, bat_desc = BAT_SIDES.get(batter_id, ("R", "Right"))
        # For switch hitters vs lefty pitcher, bat right; vs righty, bat left
        if bat_code == "S":
            p_hand = PITCH_HANDS.get(pitcher_id, ("R", "Right"))
            if p_hand[0] == "L":
                bat_code, bat_desc = "R", "Right"
            else:
                bat_code, bat_desc = "L", "Left"

        # Pitch hand
        p_hand_code, p_hand_desc = PITCH_HANDS.get(pitcher_id, ("R", "Right"))

        # Generate timestamps
        play_start = game_time + timedelta(seconds=at_bat_index * 30)
        play_end = play_start + timedelta(seconds=20)

        start_ts = play_start.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00"
        # End timestamp with seed in fractional seconds (seed=0 initially)
        end_ts = play_end.strftime("%Y-%m-%dT%H:%M:%S") + ".0000300"

        # Build playEvents from pitch sequence
        pitch_seq = draft_play.get("pitchSequence", [])
        play_events, final_balls, final_strikes = make_play_events(
            pitch_seq, event_name, play_start
        )

        # Add hitData to the last pitch event if applicable
        hit_data = get_hit_data(draft_play)
        if hit_data and play_events:
            play_events[-1]["hitData"] = hit_data

        # Determine event type
        event_type = EVENT_TYPE_MAP.get(event_name, "field_out")

        # Count runs scored
        play_runs = runs_scored_in_play(draft_play)
        if play_runs == 0 and rbi > 0:
            play_runs = rbi

        # Count outs
        play_outs = count_outs_in_play(draft_play)

        # Determine scoring
        is_scoring = play_runs > 0

        # Build runners
        runners = make_runners(
            draft_play.get("runnerMovement", []),
            event_name,
            draft_play.get("fielders", []),
            batter_name,
        )

        # Update score
        if is_top:
            away_score += play_runs
        else:
            home_score += play_runs

        # Track inning runs
        key = (inning, is_top)
        inning_runs[key] = inning_runs.get(key, 0) + play_runs

        # Update runners on base after this play
        new_runners = {}
        for rm in draft_play.get("runnerMovement", []):
            runner = rm.get("runner", "")
            end = rm.get("end", "")
            scored = rm.get("scored", False)
            if scored or end == "home":
                # Runner scored, remove from bases
                pass
            elif "out" in end.lower():
                # Runner is out
                pass
            elif end in ("1B", "2B", "3B"):
                new_runners[end] = runner

        # Remove runners who moved or were put out
        moved_runners = set()
        for rm in draft_play.get("runnerMovement", []):
            runner = rm.get("runner", "")
            moved_runners.add(runner)

        # Keep runners who didn't move
        for base, name in runners_on_base.items():
            if name not in moved_runners:
                new_runners[base] = name

        runners_on_base = new_runners

        # Update outs
        current_outs += play_outs

        # Determine postOn bases
        post_on = determine_post_on_bases(runners_on_base)

        # Men on base for splits
        mob = men_on_base_str(runners_on_base)

        # Build the play
        matchup = {
            "batter": {
                "id": batter_id,
                "fullName": batter_name,
                "link": f"/api/v1/people/{batter_id}",
            },
            "batSide": {"code": bat_code, "description": bat_desc},
            "pitcher": {
                "id": pitcher_id,
                "fullName": pitcher_name,
                "link": f"/api/v1/people/{pitcher_id}",
            },
            "pitchHand": {"code": p_hand_code, "description": p_hand_desc},
            "splits": {
                "batter": f"vs_{'L' if p_hand_code == 'L' else 'R'}HP",
                "pitcher": f"vs_{'L' if bat_code == 'L' else 'R'}HB",
                "menOnBase": mob,
            },
        }
        matchup.update(post_on)

        play = {
            "result": {
                "type": "atBat",
                "event": event_name,
                "eventType": event_type,
                "description": "",
                "rbi": rbi if rbi else (play_runs if play_runs > 0 and event_type not in ("field_error",) else 0),
                "awayScore": away_score,
                "homeScore": home_score,
            },
            "about": {
                "atBatIndex": at_bat_index,
                "halfInning": "top" if is_top else "bottom",
                "isTopInning": is_top,
                "inning": inning,
                "isScoringPlay": is_scoring,
                "startTime": start_ts,
                "endTime": end_ts,
            },
            "count": {
                "balls": final_balls,
                "strikes": min(final_strikes, 2),
                "outs": current_outs,
            },
            "matchup": matchup,
            "playEvents": play_events,
            "runners": runners,
        }

        all_plays.append(play)
        at_bat_index += 1

    # Replace allPlays
    fixture["liveData"]["plays"]["allPlays"] = all_plays

    # Build linescore
    linescore_innings = []
    for inn in range(1, 10):
        away_runs = inning_runs.get((inn, True), 0)
        home_runs = inning_runs.get((inn, False), 0)
        linescore_innings.append({
            "num": inn,
            "home": {"runs": home_runs},
            "away": {"runs": away_runs},
        })

    fixture["liveData"]["linescore"] = {
        "currentInning": 9,
        "isTopInning": False,
        "inningState": "Bottom",
        "outs": 3,
        "balls": 0,
        "strikes": 0,
        "teams": {
            "home": {
                "runs": home_score,
                "hits": count_hits(draft_plays, False),
                "errors": count_errors(draft_plays, False),
            },
            "away": {
                "runs": away_score,
                "hits": count_hits(draft_plays, True),
                "errors": count_errors(draft_plays, True),
            },
        },
        "innings": linescore_innings,
    }

    # Build boxscore
    fixture["liveData"]["boxscore"] = build_boxscore(all_plays, draft_plays)

    # Write output
    with open("test_fixture_pbp_example_1.json", "w") as f:
        json.dump(fixture, f, indent=2)

    print(f"Wrote {len(all_plays)} plays to test_fixture_pbp_example_1.json")
    print(f"Final score: Away {away_score}, Home {home_score}")
    print(f"Innings: {len(linescore_innings)}")


def count_hits(plays, is_away):
    """Count hits for a team (away=batting in top, home=batting in bottom)."""
    hit_events = {"single", "double", "triple", "home_run"}
    count = 0
    for p in plays:
        is_top = p.get("isTopInning", True)
        if (is_away and is_top) or (not is_away and not is_top):
            event = p["result"]["event"]
            et = EVENT_TYPE_MAP.get(event, "")
            if et in hit_events:
                count += 1
    return count


def count_errors(plays, is_away):
    """Count errors committed by a team (away=fielding in bottom, home=fielding in top)."""
    count = 0
    for p in plays:
        is_top = p.get("isTopInning", True)
        # Errors are committed by the fielding team
        # Away team fields in bottom half, home team fields in top half
        if (is_away and not is_top) or (not is_away and is_top):
            event = p["result"]["event"]
            if "Error" in event or "error" in event:
                count += 1
    return count


if __name__ == "__main__":
    build_fixture()
