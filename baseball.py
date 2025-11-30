import random
import uuid
import json
from datetime import datetime, timezone
from gameday import GamedayData, GameData, LiveData, Linescore, InningLinescore, Play, PlayResult, PlayAbout, PlayCount, PlayEvent, Runner, FielderCredit, PitchData, HitData, PitchDetails, Boxscore, BoxscoreTeam, BoxscorePlayer
from teams import TEAMS
from commentary import GAME_CONTEXT

class BaseballSimulator:
    """
    Simulates a modern MLB game with realistic rules and enhanced realism.
    - DH rule is in effect.
    - Extra innings start with a "ghost runner" on second.
    - Realistic bullpen management with pitcher fatigue.
    - Positional fielding, errors, and scorer's notation for outs.
    - Varied pitch velocities.
    """

    def __init__(self, team1_data, team2_data, max_innings=None, game_seed=None):
        self.team1_data = team1_data
        self.team2_data = team2_data
        self.team1_name = self.team1_data["name"]
        self.team2_name = self.team2_data["name"]
        self.max_innings = max_innings
        self.game_rng = random.Random(game_seed)

        # Setup lineups and pitchers
        self.team1_lineup = [p for p in self.team1_data["players"] if p['position']['abbreviation'] != 'P']
        self.team2_lineup = [p for p in self.team2_data["players"] if p['position']['abbreviation'] != 'P']
        
        self._setup_pitchers(self.team1_data, 'team1')
        self._setup_pitchers(self.team2_data, 'team2')

        # Setup defensive positions
        self._setup_defense('team1', self.team1_data)
        self._setup_defense('team2', self.team2_data)

        # Game state
        self.team1_batter_idx, self.team2_batter_idx = 0, 0
        self.team1_score, self.team2_score = 0, 0
        self.inning, self.top_of_inning = 1, True
        self.outs, self.bases = 0, [None, None, None] # Runners on base by name

        self.gameday_data: GamedayData | None = None
        self._pitch_event_seq = 0
        self._initialize_gameday_data()

        # Game context
        self.umpires = self.game_rng.sample(GAME_CONTEXT["umpires"], 4)
        self.weather = self.game_rng.choice(GAME_CONTEXT["weather_conditions"])
        self.venue = self.team1_data["venue"]

        # Add context to gameday data
        self.gameday_data['gameData']['umpires'] = self.umpires
        self.gameday_data['gameData']['weather'] = self.weather
        self.gameday_data['gameData']['venue'] = self.venue
        self.gameday_data['gameData']['players'] = self._initialize_game_data_players()

    def _initialize_game_data_players(self):
        players = {}
        for team_data in [self.team1_data, self.team2_data]:
            for p in team_data['players']:
                pid = f"ID{p['id']}"

                # Split name for details
                full_name = p['legal_name']
                name_parts = full_name.split(' ')
                first_name = name_parts[0]
                last_name = name_parts[-1] if len(name_parts) > 1 else ""
                middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else ""

                # Mock realistic bio data
                # Use player ID as seed component for consistency across games if desired,
                # but here we use game_rng for game-specific flavor or just stick to static mocks if prefered.
                # To be safe and realistic, let's generate some consistent-ish data based on ID.
                rng = random.Random(p['id'])

                birth_year = rng.randint(1995, 2003)
                birth_month = rng.randint(1, 12)
                birth_day = rng.randint(1, 28)
                birth_date = f"{birth_year}-{birth_month:02d}-{birth_day:02d}"
                current_age = 2025 - birth_year # Assuming current year 2025

                height_feet = rng.randint(5, 6)
                height_inches = rng.randint(0, 11)
                if height_feet == 6: height_inches = rng.randint(0, 8)
                height = f"{height_feet}' {height_inches}\""

                weight = rng.randint(170, 240)

                draft_year = birth_year + 18 + rng.randint(0, 3)
                debut_year = draft_year + rng.randint(2, 5)
                debut_date = f"{debut_year}-04-01"

                player_detail = {
                    "id": p['id'],
                    "fullName": full_name,
                    "link": f"/api/v1/people/{p['id']}",
                    "firstName": first_name,
                    "lastName": last_name,
                    "primaryNumber": str(p['id'] % 100),
                    "birthDate": birth_date,
                    "currentAge": current_age,
                    "birthCity": "Sim City",
                    "birthStateProvince": "CA",
                    "birthCountry": "USA",
                    "height": height,
                    "weight": weight,
                    "active": True,
                    "primaryPosition": p['position'],
                    "useName": p.get('nickname', first_name) or first_name,
                    "useLastName": last_name,
                    "middleName": middle_name,
                    "boxscoreName": last_name,
                    "gender": "M",
                    "isPlayer": True,
                    "isVerified": False,
                    "draftYear": draft_year,
                    "mlbDebutDate": debut_date,
                    "batSide": p.get('batSide', {'code': 'R', 'description': 'Right'}),
                    "pitchHand": p.get('pitchHand', {'code': 'R', 'description': 'Right'}),
                    "strikeZoneTop": 3.5, # Default
                    "strikeZoneBottom": 1.5 # Default
                }
                players[pid] = player_detail
        return players

    def _initialize_gameday_data(self):
        """Sets up the initial structure for Gameday JSON output."""
        self.gameday_data = {
            "gameData": {
                "teams": {
                    "away": {
                        "id": self.team2_data["id"],
                        "name": self.team2_data["name"],
                        "abbreviation": self.team2_data["abbreviation"],
                        "teamName": self.team2_data["teamName"]
                    },
                    "home": {
                        "id": self.team1_data["id"],
                        "name": self.team1_data["name"],
                        "abbreviation": self.team1_data["abbreviation"],
                        "teamName": self.team1_data["teamName"]
                    }
                }
            },
            "liveData": {
                "plays": {"allPlays": []},
                "linescore": {
                    "currentInning": 1, "isTopInning": True, "inningState": "Top",
                    "outs": 0, "balls": 0, "strikes": 0,
                    "teams": {
                        "home": {"runs": 0, "hits": 0, "errors": 0},
                        "away": {"runs": 0, "hits": 0, "errors": 0}
                    },
                    "innings": [{"num": 1, "home": {"runs": 0}, "away": {"runs": 0}}]
                },
                "boxscore": {
                    "teams": {
                        "away": self._initialize_boxscore_team(self.team2_data, self.team2_lineup),
                        "home": self._initialize_boxscore_team(self.team1_data, self.team1_lineup)
                    },
                    "officials": [],
                    "info": [],
                    "pitchingNotes": []
                }
            }
        }

    def _initialize_boxscore_team(self, team_data, lineup):
        players = {}
        batters = []
        pitchers = []
        bench = []
        bullpen = []
        batting_order = []

        lineup_ids = [p['id'] for p in lineup]

        for p in team_data['players']:
            pid = f"ID{p['id']}"
            is_pitcher = p['position']['abbreviation'] == 'P'
            is_starter = p in lineup

            player_entry = {
                "person": {
                    "id": p['id'],
                    "fullName": p['legal_name'],
                    "link": f"/api/v1/people/{p['id']}"
                },
                "jerseyNumber": str(p['id'] % 100),
                "position": p['position'],
                "status": {"code": "A", "description": "Active"},
                "parentTeamId": team_data['id'],
                "battingOrder": str((lineup_ids.index(p['id']) + 1) * 100) if is_starter else None,
                "stats": {
                    "batting": {
                        "gamesPlayed": 1, "flyOuts": 0, "groundOuts": 0, "runs": 0, "doubles": 0, "triples": 0,
                        "homeRuns": 0, "strikeOuts": 0, "baseOnBalls": 0, "intentionalWalks": 0, "hits": 0,
                        "hitByPitch": 0, "atBats": 0, "caughtStealing": 0, "stolenBases": 0,
                        "groundIntoDoublePlay": 0, "groundIntoTriplePlay": 0, "plateAppearances": 0,
                        "totalBases": 0, "rbi": 0, "leftOnBase": 0, "sacBunts": 0, "sacFlies": 0,
                        "catchersInterference": 0, "pickoffs": 0
                    },
                    "pitching": {
                        "gamesPlayed": 1 if is_pitcher else 0, "gamesStarted": 1 if is_pitcher and p['type'] == 'Starter' else 0,
                        "groundOuts": 0, "airOuts": 0, "runs": 0, "doubles": 0, "triples": 0, "homeRuns": 0,
                        "strikeOuts": 0, "baseOnBalls": 0, "intentionalWalks": 0, "hits": 0, "hitByPitch": 0,
                        "atBats": 0, "caughtStealing": 0, "stolenBases": 0, "inningsPitched": "0.0", "wins": 0,
                        "losses": 0, "saves": 0, "saveOpportunities": 0, "holds": 0, "blownSaves": 0,
                        "earnedRuns": 0, "whip": "0.00", "outs": 0, "numberOfPitches": 0, "strikes": 0, "balls": 0
                    },
                    "fielding": {
                         "gamesPlayed": 1, "gamesStarted": 1 if is_starter or (is_pitcher and p['type'] == 'Starter') else 0,
                         "assists": 0, "putOuts": 0, "errors": 0, "chances": 0, "fielding": "0.000",
                         "position": p['position']
                    }
                },
                "seasonStats": {"batting": {}, "pitching": {}, "fielding": {}},
                "gameStatus": {"isCurrentBatter": False, "isCurrentPitcher": False, "isOnBench": not is_starter and not is_pitcher, "isSubstitute": False}
            }

            players[pid] = player_entry

            if is_pitcher:
                pitchers.append(p['id'])
                if p['type'] != 'Starter':
                    bullpen.append(p['id'])
            elif is_starter:
                batters.append(p['id'])
                batting_order.append(p['id'])
            else:
                bench.append(p['id'])

        return {
            "team": {
                "id": team_data['id'],
                "name": team_data['name'],
                "abbreviation": team_data['abbreviation'],
                "teamName": team_data['teamName']
            },
            "teamStats": {
                "batting": {
                    "flyOuts": 0, "groundOuts": 0, "airOuts": 0, "runs": 0, "doubles": 0, "triples": 0,
                    "homeRuns": 0, "strikeOuts": 0, "baseOnBalls": 0, "intentionalWalks": 0, "hits": 0,
                    "hitByPitch": 0, "atBats": 0, "caughtStealing": 0, "stolenBases": 0,
                    "groundIntoDoublePlay": 0, "groundIntoTriplePlay": 0, "plateAppearances": 0,
                    "totalBases": 0, "rbi": 0, "leftOnBase": 0, "sacBunts": 0, "sacFlies": 0,
                    "catchersInterference": 0, "pickoffs": 0, "popOuts": 0, "lineOuts": 0
                },
                "pitching": {
                    "flyOuts": 0, "groundOuts": 0, "airOuts": 0, "runs": 0, "doubles": 0, "triples": 0,
                    "homeRuns": 0, "strikeOuts": 0, "baseOnBalls": 0, "intentionalWalks": 0, "hits": 0,
                    "hitByPitch": 0, "atBats": 0, "caughtStealing": 0, "stolenBases": 0,
                    "numberOfPitches": 0, "inningsPitched": "0.0", "earnedRuns": 0, "battersFaced": 0,
                    "outs": 0, "balls": 0, "strikes": 0, "hitBatsmen": 0, "balks": 0, "wildPitches": 0,
                    "pickoffs": 0, "rbi": 0, "sacBunts": 0, "sacFlies": 0, "popOuts": 0, "lineOuts": 0
                },
                "fielding": {
                    "assists": 0, "putOuts": 0, "errors": 0, "chances": 0,
                    "caughtStealing": 0, "stolenBases": 0, "passedBall": 0, "pickoffs": 0
                }
            },
            "players": players,
            "batters": batters,
            "pitchers": pitchers,
            "bench": bench,
            "bullpen": bullpen,
            "battingOrder": batting_order,
            "info": [{"title": "Team LOB", "fieldList": [{"label": "LOB", "value": "0"}]}],
            "note": []
        }

    def _update_batting_stat(self, team_key, player_id, stat_key, value=1):
        pid_key = f"ID{player_id}"
        stats = self.gameday_data['liveData']['boxscore']['teams'][team_key]['players'][pid_key]['stats']['batting']
        team_stats = self.gameday_data['liveData']['boxscore']['teams'][team_key]['teamStats']['batting']
        if stat_key in stats:
            stats[stat_key] += value
        if stat_key in team_stats:
            team_stats[stat_key] += value

    def _update_pitching_stat(self, team_key, player_id, stat_key, value=1):
        pid_key = f"ID{player_id}"
        stats = self.gameday_data['liveData']['boxscore']['teams'][team_key]['players'][pid_key]['stats']['pitching']
        team_stats = self.gameday_data['liveData']['boxscore']['teams'][team_key]['teamStats']['pitching']
        if stat_key in stats:
            stats[stat_key] += value
            if stat_key == 'outs':
                outs = stats['outs']
                stats['inningsPitched'] = f"{outs // 3}.{outs % 3}"

        if stat_key in team_stats:
            team_stats[stat_key] += value
            if stat_key == 'outs':
                outs = team_stats['outs']
                team_stats['inningsPitched'] = f"{outs // 3}.{outs % 3}"

    def _update_fielding_stat(self, team_key, player_id, stat_key, value=1):
        pid_key = f"ID{player_id}"
        stats = self.gameday_data['liveData']['boxscore']['teams'][team_key]['players'][pid_key]['stats']['fielding']
        team_stats = self.gameday_data['liveData']['boxscore']['teams'][team_key]['teamStats']['fielding']
        if stat_key in stats:
            stats[stat_key] += value
            if stat_key in ['putOuts', 'assists', 'errors']:
                stats['chances'] += value

        if stat_key in team_stats:
            team_stats[stat_key] += value
            if stat_key in ['putOuts', 'assists', 'errors']:
                team_stats['chances'] += value

    @property
    def _batting_team_key(self):
        return 'away' if self.top_of_inning else 'home'

    @property
    def _pitching_team_key(self):
        return 'home' if self.top_of_inning else 'away'

    def _setup_pitchers(self, team_data, team_prefix):
        all_pitchers = [p for p in team_data["players"] if p['position']['abbreviation'] == 'P']
        pitcher_stats = {p['legal_name']: p.copy() for p in all_pitchers}
        bullpen_candidates = [p['legal_name'] for p in all_pitchers if p['type'] != 'Starter']
        closers = [name for name in bullpen_candidates if pitcher_stats[name]['type'] == 'Closer']
        non_closers = [name for name in bullpen_candidates if pitcher_stats[name]['type'] != 'Closer']
        self.game_rng.shuffle(non_closers)
        available_bullpen = non_closers + closers
        current_pitcher_name = next(p['legal_name'] for p in all_pitchers if p['type'] == 'Starter')

        setattr(self, f"{team_prefix}_pitcher_stats", pitcher_stats)
        setattr(self, f"{team_prefix}_available_bullpen", available_bullpen)
        setattr(self, f"{team_prefix}_current_pitcher_name", current_pitcher_name)

        if not hasattr(self, 'pitch_counts'): self.pitch_counts = {}
        self.pitch_counts.update({name: 0 for name in pitcher_stats.keys()})

    def _setup_defense(self, team_prefix, team_data):
        defense = {p['position']['abbreviation']: p for p in team_data['players']}
        setattr(self, f"{team_prefix}_defense", defense)

        infielders = ['1B', '2B', '3B', 'SS']
        outfielders = ['LF', 'CF', 'RF']

        setattr(self, f"{team_prefix}_infielders", [defense[pos] for pos in infielders if pos in defense])
        setattr(self, f"{team_prefix}_outfielders", [defense[pos] for pos in outfielders if pos in defense])
        setattr(self, f"{team_prefix}_catcher", defense.get('C'))

    def _simulate_pitch_trajectory(self, pitcher):
        """Simulates the pitch's path and determines if it's in the strike zone."""
        fatigue_penalty = (max(0, self.pitch_counts[pitcher['legal_name']] - pitcher['stamina']) / 15) * 0.1
        # Add a small penalty to control to increase walks slightly
        return self.game_rng.random() < (pitcher['control'] - fatigue_penalty - 0.012)

    def _simulate_bat_swing(self, batter, is_strike_loc):
        """Determines if the batter swings at the pitch."""
        discipline_factor = max(0.1, batter['plate_discipline'].get('Walk', 0.09) / 0.08)
        swing_at_ball_prob = 0.14 / discipline_factor
        return self.game_rng.random() < (0.85 if is_strike_loc else swing_at_ball_prob)

    def _simulate_batted_ball_physics(self, batter):
        """Calculates the exit velocity and launch angle of a batted ball."""
        batting_profile = batter['batting_profile']
        # Power influences exit velocity, with some randomness
        ev = round(self.game_rng.normalvariate(80 + batting_profile['power'] * 25, 8), 1)
        # Angle influences launch angle, with some randomness
        # Increase SD to 15.0 to get more popups and grounders
        la = round(self.game_rng.normalvariate(batting_profile['angle'] + 4.5, 15.0), 1)
        return {'ev': ev, 'la': la}

    def _simulate_bunt_physics(self):
        """Calculates the exit velocity and launch angle for a bunt."""
        ev = round(self.game_rng.uniform(60, 75), 1)
        la = round(self.game_rng.uniform(-50, -20), 1)
        return {'ev': ev, 'la': la}

    def _determine_outcome_from_trajectory(self, ev, la):
        """Determines the outcome of a batted ball from its physics."""
        # Weak contact leading to outs
        if ev < 80:
            if la > 46: return "Pop Out"
            if la < 12: return "Groundout"
            return "Flyout"

        # Ground balls
        if la < 12:
            if ev > 108: return "Double Play" # Hard grounder at infielder
            if ev > 102: return "Single" # Hard grounder through the hole
            if ev > 92 and self.game_rng.random() < 0.25: return "Single" # Lucky finder
            return "Groundout"

        # Line drives
        if la < 21:
            if ev > 114: return "Home Run" # Screamer
            if ev > 107: return "Double"
            if ev > 95: return "Single"
            # Reduce Lineouts by converting weaker ones to Groundouts
            if ev < 85: return "Groundout"
            return "Lineout"

        # Fly balls
        if la < 46:
            if ev > 104: return "Home Run" # Reduced threshold
            if ev > 103: return "Double" # Gap shot
            if ev > 94 and self.game_rng.random() < 0.3: return "Double"
            if ev > 90 and self.game_rng.random() < 0.2: return "Single" # Bloop
            if ev > 99 and la > 40: return "Triple"
            return "Flyout"

        return "Pop Out" # Very high flyball

    def _classify_out_trajectory(self, la):
        """Classify the trajectory of a batted ball that results in an out."""
        if la is None:
            return "ground_ball"  # default

        if la < -15:
            return "ground_ball"
        elif -15 <= la < 10:
            return "ground_ball"
        elif 10 <= la <= 25:
            return "line_drive"
        elif 25 < la <= 45:
            return "fly_ball"
        else:  # la > 45
            return "popup"

    def _get_specific_out_type(self, base_type, trajectory, batted_ball_data):
        """Map base out type and trajectory to specific MLB event type."""

        if base_type == "Groundout":
            # Ground balls could be lineouts if hit hard with low angle
            if trajectory == "line_drive":
                ev = batted_ball_data.get('ev', 0)
                # Hard-hit line drives that are caught
                if ev > 95:
                    return "Lineout"
            return "Groundout"

        elif base_type == "Flyout":
            if trajectory == "popup":
                return "Pop Out"
            elif trajectory == "line_drive":
                return "Lineout"
            else:  # fly_ball
                return "Flyout"

        return base_type

    def _get_event_type_code(self, event):
        """Convert event name to MLB event type code."""
        event_map = {
            "Lineout": "field_out",
            "Pop Out": "field_out",
            "Flyout": "field_out",
            "Groundout": "field_out",
            "Forceout": "force_out",
            "Double Play": "grounded_into_double_play",
            "Sac Fly": "sac_fly",
            "Sac Bunt": "sac_bunt",
            "Sacrifice Bunt": "sac_bunt",
            "Single": "single",
            "Double": "double",
            "Triple": "triple",
            "Home Run": "home_run",
            "Walk": "walk",
            "Hit By Pitch": "hit_by_pitch",
            "Strikeout": "strikeout",
            "Field Error": "field_error"
        }
        return event_map.get(event, event.lower().replace(" ", "_"))

    def _determine_hit_location(self, hit_type, ev, la):
        if la is None or ev is None: return "CF"
        if hit_type in ["Single", "Double"]:
            if -10 < la < 10: return self.game_rng.choice(["MI", "RS", "LS"])
            elif 10 < la < 25: return self.game_rng.choice(["LF", "CF", "RF"])
            else: return self.game_rng.choice(["SL", "SC", "SR"])
        elif hit_type == "Triple":
            return self.game_rng.choice(["RC", "LC"])
        elif hit_type == "Home Run":
            if abs(la - 28) < 5 and ev > 105: return "DL"
            return self.game_rng.choice(["DLF", "DCF", "DRF"])
        return "CF"

    def _get_trajectory(self, outcome, la):
        if "Groundout" in outcome: return "ground_ball"
        if la is not None:
            if la < 10: return "ground_ball"
            elif 10 <= la <= 25: return "line_drive"
            elif la > 50: return "popup"
        return "fly_ball"

    def _get_men_on_base_split(self, bases):
        """Determine the men on base split category."""
        if not any(bases):
            return "Empty"
        elif all(bases):
            return "Loaded"
        elif bases[1] or bases[2]:  # Runner in scoring position
            return "RISP"
        else:
            return "Men_On"

    def _build_matchup(self, batter, pitcher, pre_play_bases=None):
        """Build the matchup object for gameday JSON."""

        # Batter info
        batter_info = {
            "id": batter['id'],
            "fullName": batter['legal_name'],
            "link": f"/api/v1/people/{batter['id']}"
        }

        # Pitcher info
        pitcher_info = {
            "id": pitcher['id'],
            "fullName": pitcher['legal_name'],
            "link": f"/api/v1/people/{pitcher['id']}"
        }

        # Determine splits
        pitcher_hand = pitcher.get('pitchHand', {}).get('code', 'R')

        # Handle switch hitters
        batter_hand_code = batter.get('batSide', {}).get('code', 'R')
        if batter_hand_code == 'S':
            batter_hand_code = 'L' if pitcher_hand == 'R' else 'R'

        batter_bat_side = {
            'code': batter_hand_code,
            'description': 'Left' if batter_hand_code == 'L' else 'Right'
        }

        batter_split = f"vs_{'RHP' if pitcher_hand == 'R' else 'LHP'}"
        pitcher_split = f"vs_{'RHB' if batter_hand_code == 'R' else 'LHB'}"

        # Determine men on base situation (use pre-play bases if provided)
        bases_to_check = pre_play_bases if pre_play_bases is not None else self.bases
        men_on = self._get_men_on_base_split(bases_to_check)

        matchup = {
            "batter": batter_info,
            "batSide": batter_bat_side,
            "pitcher": pitcher_info,
            "pitchHand": pitcher.get('pitchHand', {'code': 'R', 'description': 'Right'}),
            "splits": {
                "batter": batter_split,
                "pitcher": pitcher_split,
                "menOnBase": men_on
            }
        }

        return matchup

    def _build_runner_entry(self, runner_name, origin_base, end_base, is_out, out_number,
                       event, event_type, movement_reason, play_index, is_scoring,
                       is_rbi, responsible_pitcher=None, credits=None):
        """Build a complete runner entry for gameday JSON."""

        # Find the runner's player object
        # This is a bit tricky since the runner could be a pinch runner or pitcher
        runner_player = None

        # Check both lineups first
        for p in self.team1_lineup + self.team2_lineup:
            if p['legal_name'] == runner_name:
                runner_player = p
                break

        # If not in a lineup, check the full player lists (for pitchers, etc.)
        if not runner_player:
            for p in self.team1_data['players'] + self.team2_data['players']:
                 if p['legal_name'] == runner_name:
                    runner_player = p
                    break

        if not runner_player:
            return None  # Skip if player not found, though this should be rare

        runner_entry = {
            "movement": {
                "originBase": origin_base,
                "start": origin_base,
                "end": end_base if not is_out else None,
                "outBase": end_base if is_out else None,
                "isOut": is_out,
                "outNumber": out_number if is_out else None
            },
            "details": {
                "event": event,
                "eventType": event_type,
                "movementReason": movement_reason,
                "runner": {
                    "id": runner_player['id'],
                    "fullName": runner_player['legal_name'],
                    "link": f"/api/v1/people/{runner_player['id']}"
                },
                "isScoringEvent": is_scoring,
                "rbi": is_rbi,
                "earned": is_scoring,  # Simplification: assume all runs are earned
                "teamUnearned": False,
                "playIndex": play_index
            },
            "credits": credits if credits else []
        }

        # Add responsible pitcher if runner scored
        if is_scoring and responsible_pitcher:
            runner_entry["details"]["responsiblePitcher"] = {
                "id": responsible_pitcher['id'],
                "link": f"/api/v1/people/{responsible_pitcher['id']}"
            }

        return runner_entry

    def _decide_steal_attempt(self, balls, strikes):
        # This method only *decides* if a steal will happen, it doesn't execute it.
        # This allows the pitch to happen first, and then we resolve the outcome.
        is_home_team_batting = not self.top_of_inning
        batting_lineup = self.team1_lineup if is_home_team_batting else self.team2_lineup

        count_modifier = 1.0
        if (balls == 0 and strikes == 1) or (balls == 0 and strikes == 2) or (balls == 1 and strikes == 2):
            count_modifier = 1.2
        elif (balls == 2 and strikes == 0) or (balls == 3 and strikes == 0) or (balls == 3 and strikes == 1):
            count_modifier = 0.8
        outs_modifier = 1.5 if self.outs == 2 else 1.0

        if self.bases[1] and not self.bases[2]:
            runner_name = self.bases[1]
            runner_data = next((p for p in batting_lineup if p['legal_name'] == runner_name), None)
            if runner_data:
                # Multiplier adjusted to 1.4
                attempt_chance = runner_data['batting_profile']['stealing_tendency'] * 1.4 * count_modifier * outs_modifier
                if self.game_rng.random() < attempt_chance:
                    return 3

        if self.bases[0] and not self.bases[1]:
            runner_name = self.bases[0]
            runner_data = next((p for p in batting_lineup if p['legal_name'] == runner_name), None)
            if runner_data:
                # Multiplier adjusted to 1.4
                attempt_chance = runner_data['batting_profile']['stealing_tendency'] * 1.4 * count_modifier * outs_modifier
                if self.game_rng.random() < attempt_chance:
                    return 2

        return None

    def _resolve_steal_attempt(self, base_to_steal, play_events: list[PlayEvent], balls, strikes):
        is_home_team_batting = not self.top_of_inning
        batting_lineup = self.team1_lineup if is_home_team_batting else self.team2_lineup
        defensive_catcher = self.team2_catcher if is_home_team_batting else self.team1_catcher

        base_from_idx = base_to_steal - 2
        runner_name = self.bases[base_from_idx]
        runner_data = next((p for p in batting_lineup if p['legal_name'] == runner_name), None)

        if not runner_data:
            return False # Should not happen

        success_chance = runner_data['batting_profile']['stealing_success_rate'] - (defensive_catcher['catchers_arm'] * 0.1)
        if self.game_rng.random() < success_chance:
            self.bases[base_to_steal - 1] = runner_name
            self.bases[base_from_idx] = None

            self._update_batting_stat(self._batting_team_key, runner_data['id'], 'stolenBases')
            # Record Stolen Base Event
            event: PlayEvent = {
                 'index': self._pitch_event_seq,
                 'count': {'balls': balls, 'strikes': strikes},
                 'details': {
                     'description': f"Stolen Base {base_to_steal}B",
                     'code': 'X', # In play/action?
                     'isStrike': False,
                     'type': {'code': 'AS', 'description': 'Action'},
                     'eventType': 'stolen_base'
                 }
             }
            play_events.append(event)
            self._pitch_event_seq += 1
            return False # Not caught
        else:
            self.outs += 1
            self.bases[base_from_idx] = None

            self._update_batting_stat(self._batting_team_key, runner_data['id'], 'caughtStealing')
            # Record Caught Stealing Event
            event: PlayEvent = {
                 'index': self._pitch_event_seq,
                 'count': {'balls': balls, 'strikes': strikes},
                 'details': {
                     'description': f"Caught Stealing {base_to_steal}B",
                     'code': 'X',
                     'isStrike': False,
                     'type': {'code': 'AS', 'description': 'Action'},
                     'eventType': 'caught_stealing'
                 }
             }
            play_events.append(event)
            self._pitch_event_seq += 1
            return True # Caught stealing

    def _simulate_at_bat(self, batter, pitcher):
        self._update_batting_stat(self._batting_team_key, batter['id'], 'plateAppearances')
        balls, strikes = 0, 0
        play_events: list[PlayEvent] = []
        
        # Boost HBP rate to match MLB averages
        if self.game_rng.random() < (batter['plate_discipline'].get('HBP', 0) * 2.5):
            self._update_batting_stat(self._batting_team_key, batter['id'], 'hitByPitch')
            self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'hitByPitch')
            return "Hit By Pitch", None, play_events

        bunt_propensity = batter['batting_profile'].get('bunt_propensity', 0.0)
        bunt_situation = self.outs < 2 and any(self.bases) and not self.bases[2]
        is_bunting = bunt_situation and self.game_rng.random() < bunt_propensity

        while balls < 4 and strikes < 3:
            pitch_outcome_text = ""
            steal_attempt_base = self._decide_steal_attempt(balls, strikes)
            
            self.pitch_counts[pitcher['legal_name']] += 1
            pitch_selection = self.game_rng.choices(list(pitcher['pitch_arsenal'].keys()), weights=[v['prob'] for v in pitcher['pitch_arsenal'].values()], k=1)[0]
            pitch_details_team = pitcher['pitch_arsenal'][pitch_selection]
            pitch_velo = round(self.game_rng.uniform(*pitch_details_team['velo_range']), 1)
            pitch_spin = self.game_rng.randint(*pitch_details_team.get('spin_range', (2000, 2500))) if self.game_rng.random() > 0.08 else None
            
            is_strike_loc = self._simulate_pitch_trajectory(pitcher)
            
            pre_pitch_balls, pre_pitch_strikes = balls, strikes
            event_details: PlayEvent['details'] = {}
            is_in_play = False
            hit_result = None

            swing = self._simulate_bat_swing(batter, is_strike_loc) or is_bunting
            # Boost contact rate slightly to reduce strikeouts (adjusted to 0.06)
            contact = self.game_rng.random() < (batter['batting_profile']['contact'] + 0.06) or (is_bunting and is_strike_loc)

            play_event: PlayEvent = {'index': self._pitch_event_seq, 'count': {'balls': pre_pitch_balls, 'strikes': pre_pitch_strikes}}
            if is_bunting:
                play_event['isBunt'] = True

            if not swing:
                if is_strike_loc:
                    strikes += 1; pitch_outcome_text = "called strike"
                    event_details = {'code': 'C', 'description': 'Called Strike', 'isStrike': True}
                    self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'strikes')
                else:
                    balls += 1; pitch_outcome_text = "ball"
                    event_details = {'code': 'B', 'description': 'Ball', 'isStrike': False}
                    self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'balls')
            else: # Swung or Bunting
                if not contact:
                    strikes += 1; pitch_outcome_text = "swinging strike"
                    event_details = {'code': 'S', 'description': 'Swinging Strike', 'isStrike': True}
                    self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'strikes')
                else: # Contact
                    is_foul = self.game_rng.random() < 0.6
                    if is_foul:
                        if strikes < 2: strikes += 1
                        pitch_outcome_text = "foul"
                        event_details = {'code': 'F', 'description': 'Foul', 'isStrike': True}
                        self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'strikes')
                        if is_bunting:
                            event_details['description'] = 'Foul Bunt'
                            if strikes == 3: # Foul bunt with 2 strikes is a strikeout
                                pitch_outcome_text = "strikeout"
                    else: # In Play
                        is_in_play = True
                        if is_bunting:
                            batted_ball_data = self._simulate_bunt_physics()
                            hit_result = "Sacrifice Bunt"
                        else:
                            batted_ball_data = self._simulate_batted_ball_physics(batter)
                            hit_result = self._determine_outcome_from_trajectory(batted_ball_data['ev'], batted_ball_data['la'])
                        pitch_outcome_text = "in play"
                        event_details = {'code': 'X', 'description': f'In play, {hit_result}', 'isStrike': True}
                        self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'strikes')

            self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'numberOfPitches')
            event_details['type'] = {'code': GAME_CONTEXT['PITCH_TYPE_MAP'].get(pitch_selection, 'UN'), 'description': pitch_selection.capitalize()}
            pitch_data: PitchData = {'startSpeed': pitch_velo}
            if pitch_spin: pitch_data['breaks'] = {'spinRate': pitch_spin}

            play_event['details'] = event_details
            play_event['pitchData'] = pitch_data
            play_events.append(play_event)
            self._pitch_event_seq += 1

            if is_in_play:
                if steal_attempt_base:
                    # On a hit, a steal attempt turns into a "hit and run"
                    pass
                description_context = {
                    'batted_ball_data': batted_ball_data,
                    'pitch_details': {'type': pitch_selection, 'velo': pitch_velo, 'spin': pitch_spin}
                }
                if 'ev' in batted_ball_data:
                    hit_data: HitData = {
                        'launchSpeed': batted_ball_data['ev'], 'launchAngle': batted_ball_data['la'],
                        'trajectory': self._get_trajectory(hit_result, batted_ball_data.get('la'))
                    }
                    if hit_result in ["Single", "Double", "Triple", "Home Run"]:
                        hit_data['location'] = self._determine_hit_location(hit_result, batted_ball_data['ev'], batted_ball_data['la'])
                    play_events[-1]['hitData'] = hit_data
                return hit_result, description_context, play_events

            # If the ball is not in play, now we resolve the steal attempt.
            if steal_attempt_base:
                if pitch_outcome_text == "foul":
                    pass
                else:
                    caught_stealing = self._resolve_steal_attempt(steal_attempt_base, play_events, balls, strikes)
                    if caught_stealing and self.outs >= 3:
                        return "Caught Stealing", None, play_events
                    elif caught_stealing and strikes == 3:
                        # "Strike 'em out, throw 'em out" double play
                        self.outs += 1
                        self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'outs')
                        self._update_batting_stat(self._batting_team_key, batter['id'], 'strikeOuts')
                        self._update_batting_stat(self._batting_team_key, batter['id'], 'atBats')
                        self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'strikeOuts')
                        return "Strikeout Double Play", None, play_events

        if balls == 4:
            self._update_batting_stat(self._batting_team_key, batter['id'], 'baseOnBalls')
            self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'baseOnBalls')
            return "Walk", None, play_events

        self._update_batting_stat(self._batting_team_key, batter['id'], 'strikeOuts')
        self._update_batting_stat(self._batting_team_key, batter['id'], 'atBats')
        self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'strikeOuts')
        return "Strikeout", {}, play_events


    def _advance_runners(self, hit_type, batter, was_error=False, include_batter_advance=False):
        runs, rbis = 0, 0
        advances = []
        batter_name = batter['legal_name']
        batter_gets_rbi = not was_error

        if hit_type in ["Walk", "HBP"]:
            new_bases = self.bases[:]
            if new_bases[0]:
                if new_bases[1]:
                    if new_bases[2]: runs += 1; rbis += 1; advances.append(f"{new_bases[2]} scores")
                    advances.append(f"{new_bases[1]} to 3B"); new_bases[2] = new_bases[1]
                advances.append(f"{new_bases[0]} to 2B"); new_bases[1] = new_bases[0]
            new_bases[0] = batter_name
            self.bases = new_bases
            return {'runs': runs, 'rbis': rbis, 'advances': advances}

        old_bases = self.bases[:]
        new_bases = [None, None, None]
        if hit_type == 'Single':
            if old_bases[2]: runs += 1; rbis += (1 if batter_gets_rbi else 0); advances.append(f"{old_bases[2]} scores")
            if old_bases[1]: new_bases[2] = old_bases[1]; advances.append(f"{old_bases[1]} to 3B")
            if old_bases[0]: new_bases[1] = old_bases[0]; advances.append(f"{old_bases[0]} to 2B")
            new_bases[0] = batter_name
            if include_batter_advance: advances.append(f"{batter_name} to 1B")
        elif hit_type == 'Double':
            if old_bases[2]: runs += 1; rbis += (1 if batter_gets_rbi else 0); advances.append(f"{old_bases[2]} scores")
            if old_bases[1]: runs += 1; rbis += (1 if batter_gets_rbi else 0); advances.append(f"{old_bases[1]} scores")
            if old_bases[0]: new_bases[2] = old_bases[0]; advances.append(f"{old_bases[0]} to 3B")
            new_bases[1] = batter_name
            if include_batter_advance: advances.append(f"{batter_name} to 2B")
        elif hit_type == 'Triple':
            for runner in old_bases:
                if runner: runs += 1; rbis += (1 if batter_gets_rbi else 0); advances.append(f"{runner} scores")
            new_bases[2] = batter_name
            if include_batter_advance: advances.append(f"{batter_name} to 3B")
        elif hit_type == 'Home Run':
            for runner in old_bases:
                if runner: runs += 1; rbis += 1; advances.append(f"{runner} scores")
            runs += 1; rbis += 1; advances.append(f"{batter_name} scores")

        self.bases = new_bases
        return {'runs': runs, 'rbis': rbis, 'advances': advances}

    def _get_bases_str(self):
        runners = []
        if self.bases[2]: runners.append(f"3B: {self.bases[2]}")
        if self.bases[1]: runners.append(f"2B: {self.bases[1]}")
        if self.bases[0]: runners.append(f"1B: {self.bases[0]}")
        return ", ".join(runners) if runners else "Bases empty"

    def _manage_pitching_change(self):
        is_home_team_pitching = self.top_of_inning
        current_pitcher_name = self.team1_current_pitcher_name if is_home_team_pitching else self.team2_current_pitcher_name
        pitcher_stats = self.team1_pitcher_stats if is_home_team_pitching else self.team2_pitcher_stats
        available_bullpen = self.team1_available_bullpen if is_home_team_pitching else self.team2_available_bullpen
        fatigue_factor = max(0, self.pitch_counts[current_pitcher_name] - pitcher_stats[current_pitcher_name]['stamina'])
        if fatigue_factor > 0 and available_bullpen:
            next_pitcher_name = available_bullpen[0]
            if is_home_team_pitching:
                if self.team1_current_pitcher_name != next_pitcher_name:
                    self.team1_current_pitcher_name, self.team1_available_bullpen = next_pitcher_name, available_bullpen[1:]
            else:
                if self.team2_current_pitcher_name != next_pitcher_name:
                    self.team2_current_pitcher_name, self.team2_available_bullpen = next_pitcher_name, available_bullpen[1:]

    def _create_credit(self, player, credit_type):
        return {
            'player': {
                'id': player['id'],
                'fullName': player['legal_name'],
                'link': f"/api/v1/people/{player['id']}"
            },
            'position': player['position'],
            'credit': credit_type
        }

    def _get_double_play_participants(self, fielder, defense):
        """Determine participants and credits for a double play."""
        fielder_pos = fielder['position']['abbreviation']
        ss = defense.get('SS')
        second_base = defense.get('2B')
        first_base = defense.get('1B')

        # Default pivot logic
        pivot = None
        if fielder_pos == 'SS': pivot = second_base
        elif fielder_pos == '2B': pivot = ss
        elif fielder_pos == '3B': pivot = second_base
        elif fielder_pos == '1B': pivot = ss # 3-6-3
        elif fielder_pos == 'P': pivot = ss # 1-6-3
        elif fielder_pos == 'C': pivot = second_base # 2-4-3

        if not pivot: pivot = second_base # Fallback

        # Construct credits
        # Runner Out: Initiator (Assist) -> Pivot (Putout)
        credits_runner = [self._create_credit(fielder, 'assist'), self._create_credit(pivot, 'putout')]

        # Batter Out: Pivot (Assist) -> 1B (Putout)
        # The initiating fielder gets one assist (on the runner), not two.
        credits_batter = [self._create_credit(pivot, 'assist'), self._create_credit(first_base, 'putout')]

        return credits_runner, credits_batter

    def _handle_batted_ball_out(self, out_type, batter, context=None):
        defensive_team_prefix = 'team1' if self.top_of_inning else 'team2'
        defense = getattr(self, f"{defensive_team_prefix}_defense")
        infielders = getattr(self, f"{defensive_team_prefix}_infielders")
        outfielders = getattr(self, f"{defensive_team_prefix}_outfielders")
        pitcher = getattr(self, f"{defensive_team_prefix}_pitcher_stats")[getattr(self, f"{defensive_team_prefix}_current_pitcher_name")]
        catcher = getattr(self, f"{defensive_team_prefix}_catcher")
        first_baseman = defense.get('1B')

        fielder, is_error, credits = None, False, []
        credits_runner, credits_batter = [], []
        batted_ball_data = context.get('batted_ball_data', {}) if context else {}
        
        if out_type in ['Groundout', 'Sacrifice Bunt', 'Lineout', 'Pop Out', 'Forceout', 'Grounded Into DP', 'Double Play']:
            grounder_candidates = [(p, 6) for p in infielders] + [(pitcher, 1)] + ([(catcher, 0.25)] if catcher else [])
            fielder = self.game_rng.choices([c[0] for c in grounder_candidates], weights=[c[1] for c in grounder_candidates], k=1)[0]
            if fielder['position']['abbreviation'] == 'C' and 'ev' in batted_ball_data:
                batted_ball_data['ev'], batted_ball_data['la'] = round(self.game_rng.uniform(50, 70), 1), round(self.game_rng.uniform(-45, -20), 1)
        elif out_type == 'Flyout' or out_type == 'Sac Fly':
            fielder = self.game_rng.choices(outfielders + infielders, weights=[6] * len(outfielders) + [1] * len(infielders), k=1)[0]

        # Boost fielding slightly to reduce error rate to MLB levels
        if fielder and self.game_rng.random() > fielder['fielding_ability'] * (self.team1_data if self.top_of_inning else self.team2_data)['fielding_prowess'] * 1.006:
            is_error = True

        if is_error:
            credits = [self._create_credit(fielder, 'fielding_error')]
            return 0, True, 0, credits, [], [], False, "Field Error", None

        runs, rbis = 0, 0
        if out_type in ['Flyout', 'Pop Out', 'Lineout']:
            fielder_pos = fielder['position']['abbreviation']
            credits.append(self._create_credit(fielder, 'putout'))

            # Sac Fly logic
            if self.outs < 2 and self.bases[2] and fielder_pos in ['LF', 'CF', 'RF'] and self.game_rng.random() > 0.4:
                self.outs += 1
                runs, rbis = 1, 1
                runner_on_third, self.bases[2] = self.bases[2], None
                specific_event = "Sac Fly"
                return runs, False, rbis, credits, [], [], False, specific_event, None
            else:
                self.outs += 1
                specific_event = out_type
                return runs, False, rbis, credits, [], [], False, specific_event, None

        if out_type == 'Groundout' or out_type == 'Grounded Into DP' or out_type == 'Double Play':
            is_dp = False
            if out_type == 'Grounded Into DP' or out_type == 'Double Play':
                is_dp = True
            elif self.outs < 2 and self.bases[0] and self.game_rng.random() < self.team1_data['double_play_rate']:
                is_dp = True

            if is_dp and self.outs < 2 and self.bases[0]:
                runner_out = self.bases[0]
                self.outs += 2
                self.bases[0] = None
                if self.bases[1]: self.bases[2], self.bases[1] = self.bases[1], None

                credits_runner, credits_batter = self._get_double_play_participants(fielder, defense)

                # Combine for the main return, but we will access specifics later
                credits = credits_batter

                return 0, False, 0, credits, credits_batter, credits_runner, True, "Double Play", runner_out

            # Check for force play situation (not a double play)
            is_force_play = False
            force_base = None
            if self.bases[0] and not self.bases[1] and self.game_rng.random() < 0.3:
                is_force_play = True
                force_base = "2B"

            if is_force_play and self.outs < 2:
                self.outs += 1
                self.bases[0] = batter['legal_name']  # Batter reaches
                if force_base == "2B":
                    self.bases[1] = None # Runner forced at second
                ss = getattr(self, f"{defensive_team_prefix}_defense").get('SS')
                credits = [self._create_credit(fielder, 'assist'), self._create_credit(ss, 'putout')]
                return 0, False, 0, credits, [], [], False, "Forceout", None

            self.outs += 1
            if self.outs < 3:
                if self.bases[2]: runs, rbis, self.bases[2] = 1, 1, None
                if self.bases[1]: self.bases[2], self.bases[1] = self.bases[1], None
                if self.bases[0]: self.bases[1], self.bases[0] = self.bases[0], None
            else:
                runs, rbis = 0, 0
            specific_event = "Groundout"

        elif out_type == 'Sacrifice Bunt':
            runners_advanced = False
            self.outs += 1
            if self.outs < 3 and any(self.bases):
                new_bases = self.bases[:]
                if new_bases[1]:
                    new_bases[2], new_bases[1] = new_bases[1], None
                    runners_advanced = True
                if new_bases[0]:
                    new_bases[1], new_bases[0] = new_bases[0], None
                    runners_advanced = True
                self.bases = new_bases

            final_out_type = "Sacrifice Bunt" if runners_advanced else "Bunt Ground Out"
            if final_out_type == "Sacrifice Bunt":
                rbis = 0  # No RBI on a sacrifice
            specific_event = final_out_type

        if fielder['position']['abbreviation'] == '1B' and first_baseman:
            credits = [self._create_credit(first_baseman, 'putout')]
        elif first_baseman:
            credits = [self._create_credit(fielder, 'assist'), self._create_credit(first_baseman, 'putout')]

        return runs, False, rbis, credits, [], [], False, specific_event, None

    def _simulate_half_inning(self):
        self.outs, self.bases = 0, [None, None, None]
        is_home_team_batting = not self.top_of_inning
        batting_team_name, lineup, batter_idx_ref = (self.team1_name, self.team1_lineup, 'team1_batter_idx') if is_home_team_batting else (self.team2_name, self.team2_lineup, 'team2_batter_idx')

        if self.inning >= 10:
            last_batter_idx = (getattr(self, batter_idx_ref) - 1 + 9) % 9
            runner_name = lineup[last_batter_idx]['legal_name']
            self.bases[1] = runner_name
            # Note: Renderer handles "Automatic runner" text

        while self.outs < 3:
            old_outs = self.outs
            self._manage_pitching_change()
            pitcher_name = self.team1_current_pitcher_name if self.top_of_inning else self.team2_current_pitcher_name
            pitcher = (self.team1_pitcher_stats if self.top_of_inning else self.team2_pitcher_stats)[pitcher_name]
            batter = lineup[getattr(self, batter_idx_ref)]

            # Store pre-play base state for matchup
            pre_play_bases = self.bases[:]

            outcome, description, play_events = self._simulate_at_bat(batter, pitcher)

            runs, rbis, was_error = 0, 0, False
            advances, credits = [], []
            runner_list: list[Runner] = []
            is_dp = False
            runner_out_dp = None
            credits_runner_dp = []
            credits_batter_dp = []

            # Store pre-advance base state
            old_bases = self.bases[:]

            if outcome == "Caught Stealing":
                self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'outs')
                pass
            elif outcome in ["Groundout", "Flyout", "Sacrifice Bunt", "Lineout", "Pop Out", "Forceout", "Grounded Into DP", "Bunt Ground Out", "Double Play"]:
                result = self._handle_batted_ball_out(outcome, batter, description)
                new_runs, was_error, new_rbis, credits_from_out, credits_batter_dp, credits_runner_dp, is_dp, specific_event, runner_out_dp = result

                # Update fielding stats
                stats_credits = credits_from_out
                if is_dp:
                    stats_credits = credits_batter_dp + credits_runner_dp

                for credit in stats_credits:
                    if credit['credit'] == 'putout':
                        self._update_fielding_stat(self._pitching_team_key, credit['player']['id'], 'putOuts')
                    elif credit['credit'] == 'assist':
                        self._update_fielding_stat(self._pitching_team_key, credit['player']['id'], 'assists')
                    elif credit['credit'] == 'fielding_error':
                        self._update_fielding_stat(self._pitching_team_key, credit['player']['id'], 'errors')

                # If the catcher grounded out logic changed the batted ball data, update the event
                # The 'X' event is the last one in play_events
                if description and 'batted_ball_data' in description:
                    hit_data = play_events[-1].get('hitData')
                    if hit_data:
                        hit_data['launchSpeed'] = description['batted_ball_data']['ev']
                        hit_data['launchAngle'] = description['batted_ball_data']['la']

                # Determine location from credits
                fielder_pos = None
                for c in stats_credits:
                    if c['credit'] == 'fielding_error':
                        fielder_pos = c['position']['abbreviation']
                        break
                if not fielder_pos:
                    for c in stats_credits:
                         if c['credit'] == 'assist':
                              fielder_pos = c['position']['abbreviation']
                              break
                if not fielder_pos:
                     for c in stats_credits:
                          if c['credit'] == 'putout':
                               fielder_pos = c['position']['abbreviation']
                               break

                if fielder_pos:
                     hit_data = play_events[-1].get('hitData')
                     if hit_data:
                          hit_data['location'] = fielder_pos

                runs += new_runs
                rbis += new_rbis
                if is_dp:
                     credits = [] # We handle DP credits in the runner objects
                else:
                     credits.extend(credits_from_out)

                # Pitching Outs
                outs_on_play = self.outs - old_outs
                self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'outs', outs_on_play)

                if 'Ground' in outcome or 'DP' in outcome or 'Forceout' in outcome or 'Bunt' in outcome or 'Double Play' in outcome:
                     self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'groundOuts', outs_on_play)
                else:
                     self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'airOuts', outs_on_play)

                play_description_text = ""
                if was_error:
                    outcome = "Field Error"
                    adv_info = self._advance_runners("Single", batter, was_error=True, include_batter_advance=True)
                    runs += adv_info['runs']
                    advances.extend(adv_info['advances'])
                    self._update_batting_stat(self._batting_team_key, batter['id'], 'atBats')
                elif is_dp:
                    outcome = "Double Play"
                    self._update_batting_stat(self._batting_team_key, batter['id'], 'atBats')
                    self._update_batting_stat(self._batting_team_key, batter['id'], 'groundIntoDoublePlay')

                    # Generate DP description
                    # "shortstop X to second baseman Y to first baseman Z"
                    # We combine runner and batter credits to trace the path of the ball:
                    # Runner: Initiator -> Pivot
                    # Batter: Pivot -> 1B

                    full_chain = credits_runner_dp + credits_batter_dp
                    participants = []
                    last_player_id = None

                    for c in full_chain:
                        player_id = c['player']['id']
                        # Deduplicate consecutive players (e.g., Pivot involved in both PO and A)
                        if player_id != last_player_id:
                            pos_name = c['position']['name'].lower()
                            player_name = c['player']['fullName']
                            participants.append(f"{pos_name} {player_name}")
                            last_player_id = player_id

                    play_description_text = f"{batter['legal_name']} grounds into a double play, {' to '.join(participants)}."
                    # Add runner out details
                    # "RunnerName out at 2nd. BatterName out at 1st."
                    play_description_text += f" {runner_out_dp} out at 2nd. {batter['legal_name']} out at 1st."

                elif "Sacrifice Bunt" in specific_event:
                    self._update_batting_stat(self._batting_team_key, batter['id'], 'sacBunts')
                    outcome = specific_event
                elif "Sac Fly" in specific_event:
                    self._update_batting_stat(self._batting_team_key, batter['id'], 'sacFlies')
                    outcome = specific_event
                else: # Generic Out
                    outcome = specific_event
                    self._update_batting_stat(self._batting_team_key, batter['id'], 'atBats')
                    if "Ground" in outcome or "Forceout" in outcome:
                        self._update_batting_stat(self._batting_team_key, batter['id'], 'groundOuts')
                    else:
                        self._update_batting_stat(self._batting_team_key, batter['id'], 'flyOuts')

            elif outcome == "Strikeout":
                self.outs += 1
                self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'outs')
            elif outcome == "Strikeout Double Play":
                self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'outs') # CS out is separate?
                pass # Outs handled
            elif outcome in ["Single", "Double", "Triple", "Home Run", "Walk", "HBP"]:
                adv_info = self._advance_runners(outcome, batter)
                runs += adv_info['runs']; rbis += adv_info['rbis']; advances.extend(adv_info['advances'])
                if outcome in ["Single", "Double", "Triple", "Home Run"]:
                    self._update_batting_stat(self._batting_team_key, batter['id'], 'hits')
                    self._update_batting_stat(self._batting_team_key, batter['id'], 'atBats')
                    self._update_batting_stat(self._batting_team_key, batter['id'], 'totalBases', {"Single": 1, "Double": 2, "Triple": 3, "Home Run": 4}[outcome])
                    self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'hits')
                    if outcome == "Double": self._update_batting_stat(self._batting_team_key, batter['id'], 'doubles'); self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'doubles')
                    if outcome == "Triple": self._update_batting_stat(self._batting_team_key, batter['id'], 'triples'); self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'triples')
                    if outcome == "Home Run": self._update_batting_stat(self._batting_team_key, batter['id'], 'homeRuns'); self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'homeRuns')

            if is_home_team_batting: self.team1_score += runs
            else: self.team2_score += runs

            if rbis > 0:
                 self._update_batting_stat(self._batting_team_key, batter['id'], 'rbi', rbis)

            # Pitching Runs
            if runs > 0:
                 self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'runs', runs)
                 # Earned runs? Simplifying to all earned for now
                 if not was_error:
                      self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'earnedRuns', runs)

            play_index = len(play_events) - 1 if play_events else 0
            base_map = {0: "1B", 1: "2B", 2: "3B"}

            # --- Runner tracking logic ---

            if outcome in ["Single", "Double", "Triple", "Home Run"]:
                for base_idx, runner_name in enumerate(old_bases):
                    if runner_name:
                        origin = base_map[base_idx]
                        scored = runner_name not in self.bases
                        end = "score" if scored else base_map[self.bases.index(runner_name)]
                        runner_entry = self._build_runner_entry(
                            runner_name=runner_name, origin_base=origin, end_base=end,
                            is_out=False, out_number=None, event=outcome,
                            event_type=self._get_event_type_code(outcome),
                            movement_reason="r_adv_play", play_index=play_index,
                            is_scoring=scored, is_rbi=scored and not was_error,
                            responsible_pitcher=pitcher if scored else None
                        )
                        if runner_entry: runner_list.append(runner_entry)

                batter_end = {"Single": "1B", "Double": "2B", "Triple": "3B", "Home Run": "score"}[outcome]
                batter_scored = outcome == "Home Run"
                batter_entry = self._build_runner_entry(
                    runner_name=batter['legal_name'], origin_base=None, end_base=batter_end,
                    is_out=False, out_number=None, event=outcome,
                    event_type=self._get_event_type_code(outcome),
                    movement_reason=None, play_index=play_index,
                    is_scoring=batter_scored, is_rbi=batter_scored,
                    responsible_pitcher=pitcher if batter_scored else None
                )
                if batter_entry: runner_list.append(batter_entry)

            elif outcome in ["Walk", "HBP"]:
                for base_idx, runner_name in enumerate(old_bases):
                    if runner_name:
                        origin = base_map[base_idx]
                        scored = runner_name not in self.bases
                        end = "score" if scored else base_map[self.bases.index(runner_name)]
                        was_forced = (base_idx == 0) or (base_idx == 1 and old_bases[0]) or (base_idx == 2 and old_bases[0] and old_bases[1])
                        runner_entry = self._build_runner_entry(
                            runner_name=runner_name, origin_base=origin, end_base=end,
                            is_out=False, out_number=None, event=outcome,
                            event_type=self._get_event_type_code(outcome),
                            movement_reason="r_adv_force" if was_forced else "r_adv_play",
                            play_index=play_index,
                            is_scoring=scored, is_rbi=scored,
                            responsible_pitcher=pitcher if scored else None
                        )
                        if runner_entry: runner_list.append(runner_entry)

                batter_entry = self._build_runner_entry(
                    runner_name=batter['legal_name'], origin_base=None, end_base="1B",
                    is_out=False, out_number=None, event=outcome,
                    event_type=self._get_event_type_code(outcome),
                    movement_reason=None, play_index=play_index,
                    is_scoring=False, is_rbi=False
                )
                if batter_entry: runner_list.append(batter_entry)

            elif outcome in ["Groundout", "Flyout", "Sacrifice Bunt", "Lineout", "Pop Out", "Forceout", "Grounded Into DP", "Bunt Ground Out", "Sac Fly", "Field Error", "Double Play"]:
                if is_dp:
                    # Runner out at second
                    runner_entry = self._build_runner_entry(
                        runner_name=runner_out_dp, origin_base="1B", end_base="2B",
                        is_out=True, out_number=self.outs - 1, event="Grounded Into DP",
                        event_type="grounded_into_double_play",
                        movement_reason="r_force_out", play_index=play_index,
                        is_scoring=False, is_rbi=False,
                        credits=credits_runner_dp
                    )
                    if runner_entry: runner_list.append(runner_entry)

                    # Batter out at first
                    batter_entry = self._build_runner_entry(
                        runner_name=batter['legal_name'], origin_base=None, end_base="1B",
                        is_out=True, out_number=self.outs, event="Grounded Into DP",
                        event_type="grounded_into_double_play",
                        movement_reason=None, play_index=play_index,
                        is_scoring=False, is_rbi=False, credits=credits_batter_dp
                    )
                    if batter_entry: runner_list.append(batter_entry)
                else:
                    # Handle runners who advanced, scored, or were out on a force
                    for base_idx, runner_name in enumerate(old_bases):
                        if runner_name:
                            origin = base_map[base_idx]
                            scored = runner_name not in self.bases and runner_name not in [b for b in self.bases if b]
                            advanced = runner_name in self.bases

                            if scored:
                                runner_entry = self._build_runner_entry(
                                    runner_name=runner_name, origin_base=origin, end_base="score",
                                    is_out=False, out_number=None, event=outcome,
                                    event_type=self._get_event_type_code(outcome),
                                    movement_reason="r_sac_fly" if "Sac Fly" in outcome else "r_adv_play",
                                    play_index=play_index, is_scoring=True, is_rbi=True and not was_error,
                                    responsible_pitcher=pitcher
                                )
                                if runner_entry: runner_list.append(runner_entry)
                            elif advanced:
                                end = base_map[self.bases.index(runner_name)]
                                runner_entry = self._build_runner_entry(
                                    runner_name=runner_name, origin_base=origin, end_base=end,
                                    is_out=False, out_number=None, event=outcome,
                                    event_type=self._get_event_type_code(outcome),
                                    movement_reason="r_adv_play", play_index=play_index,
                                    is_scoring=False, is_rbi=False
                                )
                                if runner_entry: runner_list.append(runner_entry)

                    # Batter's outcome (out or reached on error)
                    batter_reaches = was_error
                    batter_entry = self._build_runner_entry(
                        runner_name=batter['legal_name'], origin_base=None, end_base="1B",
                        is_out=not batter_reaches, out_number=self.outs if not batter_reaches else None,
                        event=outcome, event_type=self._get_event_type_code(outcome),
                        movement_reason=None, play_index=play_index,
                        is_scoring=False, is_rbi=False, credits=credits
                    )
                    if batter_entry: runner_list.append(batter_entry)

            elif outcome == "Strikeout":
                batter_entry = self._build_runner_entry(
                    runner_name=batter['legal_name'], origin_base=None, end_base=None,
                    is_out=True, out_number=self.outs, event=outcome,
                    event_type=self._get_event_type_code(outcome),
                    movement_reason=None, play_index=play_index,
                    is_scoring=False, is_rbi=False, credits=credits
                )
                if batter_entry: runner_list.append(batter_entry)

            elif outcome == "Caught Stealing":
                 # 3rd out caught stealing
                 # Find who was out. _resolve_steal_attempt removed them from base.
                 # Check difference between old_bases and self.bases.
                 for i, (old, new) in enumerate(zip(old_bases, self.bases)):
                     if old and not new:
                         # This runner disappeared.
                         origin = base_map[i]
                         out_base = "2B" if origin == "1B" else "3B" # Assumption
                         # Wait, steal attempt.
                         # If caught stealing 2nd, origin 1B.
                         runner_entry = self._build_runner_entry(
                            runner_name=old, origin_base=origin, end_base=None,
                            is_out=True, out_number=self.outs, event="Caught Stealing",
                            event_type="caught_stealing",
                            movement_reason=None, play_index=play_index,
                            is_scoring=False, is_rbi=False
                        )
                         # We need to manually fix outBase because _build_runner_entry sets end=None if out
                         if runner_entry:
                             runner_entry['movement']['outBase'] = out_base
                             runner_list.append(runner_entry)

            # --- End runner tracking ---

            # Update scoring runners stats
            for runner_entry in runner_list:
                if runner_entry['details']['isScoringEvent']:
                     runner_id = runner_entry['details']['runner']['id']
                     self._update_batting_stat(self._batting_team_key, runner_id, 'runs')

            if runs > 0:
                current_inning_idx = self.inning - 1
                if is_home_team_batting:
                    self.gameday_data['liveData']['linescore']['innings'][current_inning_idx]['home']['runs'] += runs
                else:
                    self.gameday_data['liveData']['linescore']['innings'][current_inning_idx]['away']['runs'] += runs

            at_bat_index = len(self.gameday_data['liveData']['plays']['allPlays'])

            final_description = play_description_text if is_dp and play_description_text else ""

            play_result = PlayResult(type="atBat", event=outcome, eventType=self._get_event_type_code(outcome), description=final_description, rbi=rbis, awayScore=self.team2_score, homeScore=self.team1_score)
            play_about = PlayAbout(atBatIndex=at_bat_index, halfInning="bottom" if is_home_team_batting else "top", isTopInning=not is_home_team_batting, inning=self.inning, isScoringPlay=runs > 0)
            final_count = PlayCount(balls=0, strikes=0, outs=self.outs)
            matchup = self._build_matchup(batter, pitcher, pre_play_bases)
            current_lineup = self.team1_lineup if is_home_team_batting else self.team2_lineup

            if self.bases[0]:
                runner_obj = next((p for p in current_lineup if p['legal_name'] == self.bases[0]), None)
                if runner_obj: matchup['postOnFirst'] = { "id": runner_obj['id'], "fullName": runner_obj['legal_name'], "link": f"/api/v1/people/{runner_obj['id']}" }
            if self.bases[1]:
                runner_obj = next((p for p in current_lineup if p['legal_name'] == self.bases[1]), None)
                if runner_obj: matchup['postOnSecond'] = { "id": runner_obj['id'], "fullName": runner_obj['legal_name'], "link": f"/api/v1/people/{runner_obj['id']}" }
            if self.bases[2]:
                runner_obj = next((p for p in current_lineup if p['legal_name'] == self.bases[2]), None)
                if runner_obj: matchup['postOnThird'] = { "id": runner_obj['id'], "fullName": runner_obj['legal_name'], "link": f"/api/v1/people/{runner_obj['id']}" }

            play_data: Play = {"result": play_result, "about": play_about, "count": final_count, "matchup": matchup, "playEvents": play_events, "runners": runner_list}
            self.gameday_data['liveData']['plays']['allPlays'].append(play_data)

            ls = self.gameday_data['liveData']['linescore']
            ls['outs'] = self.outs
            ls['teams']['home']['runs'] = self.team1_score
            ls['teams']['away']['runs'] = self.team2_score
            if outcome in ["Single", "Double", "Triple", "Home Run"]:
                if is_home_team_batting: ls['teams']['home']['hits'] += 1
                else: ls['teams']['away']['hits'] += 1
            if was_error:
                if is_home_team_batting: ls['teams']['away']['errors'] += 1
                else: ls['teams']['home']['errors'] += 1
            
            setattr(self, batter_idx_ref, (getattr(self, batter_idx_ref) + 1) % 9)
            if self.outs >= 3: break
            if is_home_team_batting and self.team1_score > self.team2_score and self.inning >= 9:
                return

    def play_game(self):
        should_continue = lambda: (self.inning <= 9 or self.team1_score == self.team2_score) if self.max_innings is None else self.inning <= self.max_innings

        while should_continue():
            self.top_of_inning = True
            self._simulate_half_inning()

            if self.inning >= 9 and not self.top_of_inning and self.team1_score > self.team2_score:
                break

            if self.max_innings and self.inning >= self.max_innings:
                break

            self.top_of_inning = False
            self._simulate_half_inning()

            if self.inning >= 9 and not self.top_of_inning and self.team1_score > self.team2_score:
                break

            if self.max_innings and self.inning >= self.max_innings:
                break

            self.inning += 1
            self.gameday_data['liveData']['linescore']['currentInning'] = self.inning
            self.gameday_data['liveData']['linescore']['innings'].append({'num': self.inning, 'home': {'runs': 0}, 'away': {'runs': 0}})


if __name__ == "__main__":
    import argparse
    from renderers import NarrativeRenderer, StatcastRenderer

    parser = argparse.ArgumentParser(description="A realistic baseball simulator.")
    parser.add_argument('--terse', action='store_true', help="Use terse, data-driven phrasing for play-by-play.")
    parser.add_argument('--bracketed-ui', action='store_true', help="Use the classic bracketed UI for base runners.")
    parser.add_argument('--commentary', type=str, choices=['narrative', 'statcast', 'gameday', 'combo'], default='narrative', help="Choose the commentary style.")
    parser.add_argument('--max-innings', type=int, help="Stop simulation after specified number of innings (e.g., 2 for partial game).")
    parser.add_argument('--pbp-outfile', type=str, help="File to write play-by-play output to (stdout by default).")
    parser.add_argument('--gameday-outfile', type=str, help="File to write Gameday JSON output to (stdout by default).")
    parser.add_argument('--game-seed', type=int, help="Seed for the game's random number generator.")
    parser.add_argument('--commentary-seed', type=int, help="Seed for the commentary's random number generator.")
    args = parser.parse_args()

    # 1. Run Simulation
    game = BaseballSimulator(
        TEAMS["BAY_BOMBERS"],
        TEAMS["PC_PILOTS"],
        max_innings=args.max_innings,
        game_seed=args.game_seed
    )
    game.play_game()

    # 2. Output Gameday JSON
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime): return obj.isoformat()
            return super().default(obj)

    gameday_json = json.dumps(game.gameday_data, indent=2, cls=DateTimeEncoder)
    if args.gameday_outfile:
        with open(args.gameday_outfile, 'w') as f:
            f.write(gameday_json)
    elif args.commentary == 'gameday':
        print(gameday_json)

    # 3. Output Commentary (PBP or Statcast)
    output_text = ""
    if args.commentary != 'gameday':
        commentary_seed = args.commentary_seed if args.commentary_seed else args.game_seed # Fallback

        if args.commentary == 'narrative' or args.commentary == 'combo':
            renderer = NarrativeRenderer(game.gameday_data, seed=commentary_seed, verbose=not args.terse)
            output_text = renderer.render()
        elif args.commentary == 'statcast':
            renderer = StatcastRenderer(game.gameday_data, seed=commentary_seed)
            output_text = renderer.render()

        if args.pbp_outfile:
             with open(args.pbp_outfile, 'w') as f:
                f.write(output_text)
        else:
             print(output_text)
