import random
import uuid
import json
from datetime import datetime, timezone, timedelta
from gameday import GamedayData, GameData, LiveData, Linescore, InningLinescore, Play, PlayResult, PlayAbout, PlayCount, PlayEvent, Runner, FielderCredit, PitchData, HitData, PitchDetails, Boxscore, BoxscoreTeam, BoxscorePlayer
from teams import TEAMS
from commentary import GAME_CONTEXT
import fieldsim
import os as _os

with open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'fieldsim_batted_balls.json')) as _f:
    _REAL_BATTED_BALLS = [tuple(b) for b in json.load(_f)['balls']]

# Plate-discipline model, tuned so pitch outcomes match MLB rates (fouls ~19%
# of pitches, called strikes ~17%) while keeping K%, BB% and pitches per PA.
# Play batted balls on a 2D field (fieldsim) instead of the EV/LA outcome table:
# outcome, fielder, location and coordinates then come from one calculation.
FIELD_SIM = True
POWER_EV_SHIFT = 8.0          # mph of exit velocity per point of power, around the league's 0.54
CONTACT_BOOST = 0.075         # added to each batter's contact rating
CHASE_CONTACT_FACTOR = 0.65   # contact multiplier on pitches outside the zone
COUNT_CONTACT_BOOST = 0.01   # more contact when protecting or ahead in the count
TWO_STRIKE_CHASE_CONTACT_FACTOR = 0.72
FOUL_SHARE_OF_CONTACT = 0.52  # about half of contact goes foul, at every count
TWO_STRIKE_FOUL_BONUS = 0.01
# 136 real 2026 feeds: hitters take on 0-0 and in hitter's counts, then
# protect the plate with two strikes. Chase rates still vary by discipline.
ZONE_SWING_RATES = {
    (0, 0): 0.46, (0, 1): 0.75, (0, 2): 0.88,
    (1, 0): 0.61, (1, 1): 0.78, (1, 2): 0.90,
    (2, 0): 0.51, (2, 1): 0.76, (2, 2): 0.90,
    (3, 0): 0.69, (3, 1): 0.72, (3, 2): 0.90,
}
CHASE_RATES = {
    (0, 0): 0.19, (0, 1): 0.38, (0, 2): 0.43,
    (1, 0): 0.28, (1, 1): 0.39, (1, 2): 0.46,
    (2, 0): 0.30, (2, 1): 0.38, (2, 2): 0.53,
    (3, 0): 0.30, (3, 1): 0.28, (3, 2): 0.53,
}
# Pitchers expand the zone when ahead and come back over it behind 3-0.
COUNT_ZONE_ADJUSTMENTS = {
    (0, 0): -0.01, (0, 1): -0.13, (0, 2): -0.27,
    (1, 0): 0.015, (1, 1): -0.09, (1, 2): -0.21,
    (2, 0): 0.035, (2, 1): -0.01, (2, 2): -0.12,
    (3, 0): 0.10, (3, 1): 0.04, (3, 2): 0.01,
}
ZONE_RATE_OFFSET = 0.085      # subtracted from pitcher control to get zone rate
PICKOFF_THROW_RATE = 0.037    # per pitch with a runner on first; less often to second or third
PICKOFF_OUT_RATE = 0.026     # includes runners caught stealing after the throw over
PICKOFF_ERROR_RATE = 0.017
# The combined count model and benches create more running opportunities.
# 136 real feeds: 1.34/0.25 steal attempts at second/third and 6.22 visits/game.
STEAL_SECOND_FACTOR = 1.4
STEAL_THIRD_FACTOR = 0.55
MOUND_VISIT_RATE = 0.177
AFTER_FREE_PASS_ZONE_BOOST = 0.03  # zone rate added for the batter after a walk/HBP
WILD_PITCH_FACTOR = 3.2        # x the pitcher's wild_pitch_rate, per ball with runners on
LATE_TROUBLE_HOOK_RATE = 0.15  # per PA, innings 6+, close, runner in scoring position
STARTER_STAMINA_BONUS = 14     # pitches added to a starter's stamina
# Pitching changes, fit to 136 real 2026 feeds: 3.4 relievers per team-game,
# starters 4.9 innings on 82 pitches (sd 20: some go eight, some are gone in
# the second), a third of all changes mid-inning, relievers mostly an inning.
STARTER_PITCH_BUDGET = 24      # pitches past his stamina a starter is allowed, on average
STARTER_BUDGET_SD = 9          # the two starters don't work to the same number
SHORT_LEASH_RATE = 0.08        # starts on a pitch limit (an opener, a man back from injury)
SHORT_LEASH_RANGE = (20, 62)
INNING_PITCHES = 10            # pitches a starter needs left to start another inning
BLOWOUT_MARGIN = 5             # runs ahead or behind at which a manager stops spending relievers
FATIGUE_PENALTY_CAP = 0.12     # control lost to fatigue levels off (a team out of arms
                               # used to walk the lineup around twice)
BUNT_RATE_FACTOR = 0.35       # sacrifice attempts, weighted toward the bottom of the order
BUNT_FOR_HIT_FACTOR = 0.046
# Real bunts make contact on 93% of attempts; 43% of that contact is foul.
# A squared bat needs its own contact model rather than full-swing chase rates.
BUNT_CONTACT_RATE = 0.93
BUNT_FOUL_SHARE = 0.43
# In 136 real feeds, fastball-family usage rises from 43-44% on 0-2/1-2
# to 72-77% on 2-0/3-1 and 95% on 3-0. These multiply the arsenal weights.
FASTBALL_COUNT_WEIGHT = {
    (0, 0): 1.2, (0, 1): 0.85, (0, 2): 0.6,
    (1, 0): 1.3, (1, 1): 0.95, (1, 2): 0.6,
    (2, 0): 2.1, (2, 1): 1.2, (2, 2): 0.75,
    (3, 0): 18.0, (3, 1): 2.65, (3, 2): 1.4,
}


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
        # Per-pitcher game state the manager reads: pitches allowed today,
        # batters faced, runs given up, and when he came in.
        self._pitch_budget, self._batters_faced, self._runs_allowed = {}, {}, {}
        self._entered_inning, self._entered_mid_inning = {}, {}
        self._half_pitcher_traffic, self._half_pitcher_homers = {}, {}
        self._stolen_second_this_inning = set()
        self.commentary_seed = (game_seed if game_seed is not None
                                else random.SystemRandom().randrange(2 ** 63))
        # Throw and slide details must not change the game's results.
        self.steal_rng = random.Random(self.commentary_seed + 1)

        # Setup lineups and pitchers
        self.team1_lineup = [p.copy() for p in self.team1_data["players"] if p['position']['abbreviation'] != 'P']
        self.team2_lineup = [p.copy() for p in self.team2_data["players"] if p['position']['abbreviation'] != 'P']
        self.team1_bench = [p.copy() for p in self.team1_data.get('bench', [])]
        self.team2_bench = [p.copy() for p in self.team2_data.get('bench', [])]
        self._pending_defensive_switches = {'team1': [], 'team2': []}
        # Visits change the broadcast's texture without changing pitch outcomes.
        self.texture_rng = random.Random((game_seed or 0) + 293837)
        
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
        self._runner_pitchers = {}

        # Time state
        # September 27th 2025, 7:05 PM EDT -> 23:05 UTC
        self.current_time = datetime(2025, 9, 27, 23, 5, 0, tzinfo=timezone.utc)
        self.game_start_time = self.current_time

        # Separate RNG for timing to prevent cascading changes to game outcome
        # when timing logic is adjusted.
        # Use a deterministic seed derived from game_seed if available.
        seed_val = game_seed if game_seed is not None else 0
        self.time_rng = random.Random(seed_val + 99999)

        self.gameday_data: GamedayData | None = None
        self._pitch_event_seq = 0
        self._between_pitch_runners = []
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
            for p in team_data['players'] + team_data.get('bench', []):
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
                    # Extension field (a feed has no role): "closer" is said of
                    # a pitcher only when this records it.
                    **({"pitcherRole": {'Starter': 'starter', 'Closer': 'closer'}.get(p.get('type'), 'reliever')}
                       if p['position']['abbreviation'] == 'P' else {}),
                    "strikeZoneTop": 3.5, # Default
                    "strikeZoneBottom": 1.5 # Default
                }
                players[pid] = player_detail
        return players

    def _initialize_gameday_data(self):
        """Sets up the initial structure for Gameday JSON output."""
        self.gameday_data = {
            "gameData": {
                "commentarySeed": self.commentary_seed,
                "datetime": {
                    "dateTime": self.game_start_time.isoformat(),
                    "originalDate": "2025-09-27",
                    "officialDate": "2025-09-27",
                    "dayNight": "night",
                    "time": "7:05",
                    "ampm": "PM"
                },
                "teams": {
                    "away": {
                        "id": self.team2_data["id"],
                        "name": self.team2_data["name"],
                        "abbreviation": self.team2_data["abbreviation"],
                        "teamName": self.team2_data["teamName"],
                        "locationName": self.team2_data.get("locationName", ""),
                        "state": self.team2_data.get("state", ""),
                        **{key: self.team2_data[key] for key in ("spokenLocation", "spokenLocationWithState")
                           if key in self.team2_data},
                    },
                    "home": {
                        "id": self.team1_data["id"],
                        "name": self.team1_data["name"],
                        "abbreviation": self.team1_data["abbreviation"],
                        "teamName": self.team1_data["teamName"],
                        "locationName": self.team1_data.get("locationName", ""),
                        "state": self.team1_data.get("state", ""),
                        **{key: self.team1_data[key] for key in ("spokenLocation", "spokenLocationWithState")
                           if key in self.team1_data},
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

        for p in team_data['players'] + team_data.get('bench', []):
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
                        "gamesPlayed": int(is_starter), "flyOuts": 0, "groundOuts": 0, "runs": 0, "doubles": 0, "triples": 0,
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
                         "gamesPlayed": int(is_starter or is_pitcher), "gamesStarted": 1 if is_starter or (is_pitcher and p['type'] == 'Starter') else 0,
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
        self._batters_faced.update({name: 0 for name in pitcher_stats})
        self._runs_allowed.update({name: 0 for name in pitcher_stats})
        starter = pitcher_stats[current_pitcher_name]
        budget = self.game_rng.gauss(starter['stamina'] + STARTER_PITCH_BUDGET, STARTER_BUDGET_SD)
        if self.game_rng.random() < SHORT_LEASH_RATE:
            budget = self.game_rng.uniform(*SHORT_LEASH_RANGE)
        self._pitch_budget[current_pitcher_name] = budget

    def _setup_defense(self, team_prefix, team_data):
        lineup = getattr(self, f"{team_prefix}_lineup")
        defense = {p['position']['abbreviation']: p for p in lineup}
        setattr(self, f"{team_prefix}_defense", defense)

        infielders = ['1B', '2B', '3B', 'SS']
        outfielders = ['LF', 'CF', 'RF']

        setattr(self, f"{team_prefix}_infielders", [defense[pos] for pos in infielders if pos in defense])
        setattr(self, f"{team_prefix}_outfielders", [defense[pos] for pos in outfielders if pos in defense])
        setattr(self, f"{team_prefix}_catcher", defense.get('C'))

    def _select_pitch_type(self, pitcher, batter, balls=0, strikes=0):
        """Choose from this pitcher's arsenal for the count and batter's side."""
        pitcher_hand = pitcher.get('pitchHand', {}).get('code')
        batter_hand = batter.get('batSide', {}).get('code')
        if batter_hand == 'S' and pitcher_hand in ('L', 'R'):
            batter_hand = 'L' if pitcher_hand == 'R' else 'R'
        known_hands = pitcher_hand in ('L', 'R') and batter_hand in ('L', 'R')
        same_hand = pitcher_hand == batter_hand
        weights = []
        for pitch, details in pitcher['pitch_arsenal'].items():
            weight = details['prob']
            if pitch in ('four-seam fastball', 'sinker', 'cutter'):
                weight *= FASTBALL_COUNT_WEIGHT.get((balls, strikes), 1.0)
            if known_hands:
                # Within the same real pitcher-game, changeups/splitters are
                # about three times as common to the opposite side; sliders
                # and sweepers are nearly twice as common to the same side.
                if pitch in ('changeup', 'splitter'):
                    weight *= 0.55 if same_hand else 1.55
                elif pitch in ('slider', 'sweeper'):
                    weight *= 1.2 if same_hand else 0.75
            weights.append(weight)
        return self.game_rng.choices(list(pitcher['pitch_arsenal']), weights=weights, k=1)[0]

    @staticmethod
    def _player_ref(player):
        return {'id': player['id'], 'fullName': player['legal_name'],
                'link': f"/api/v1/people/{player['id']}"}

    def _substitution_event(self, incoming, outgoing, position, batting_order, event_type):
        event_name = {'offensive_substitution': 'Offensive Substitution',
                      'defensive_substitution': 'Defensive Sub', 'defensive_switch': 'Defensive Switch'}[event_type]
        return {
            'index': 0, 'startTime': self.current_time.isoformat(), 'endTime': self.current_time.isoformat(),
            'isPitch': False, 'isSubstitution': True, 'type': 'action',
            'player': self._player_ref(incoming), 'replacedPlayer': self._player_ref(outgoing),
            'position': position.copy(), 'battingOrder': batting_order,
            'count': {'balls': 0, 'strikes': 0, 'outs': self.outs},
            'details': {'event': event_name, 'eventType': event_type, 'description': '',
                        'code': '', 'isStrike': False},
        }

    def _substitute(self, prefix, slot, incoming, role):
        """Use the bench player once, retaining the replaced man's lineup slot."""
        lineup = getattr(self, f"{prefix}_lineup")
        outgoing = lineup[slot]
        position = outgoing.get('_field_position', outgoing['position'])
        incoming['_field_position'] = position
        incoming['position'] = ({'code': '11' if role == 'PH' else '12',
                                 'name': 'Pinch Hitter' if role == 'PH' else 'Pinch Runner',
                                 'abbreviation': role} if role in ('PH', 'PR') else position.copy())
        lineup[slot] = incoming
        getattr(self, f"{prefix}_bench").remove(incoming)
        side = 'home' if prefix == 'team1' else 'away'
        box = self.gameday_data['liveData']['boxscore']['teams'][side]
        old_entry = box['players'][f"ID{outgoing['id']}"]
        new_entry = box['players'][f"ID{incoming['id']}"]
        order = str(int(old_entry['battingOrder']) + 1)
        new_entry.update(battingOrder=order, position=incoming['position'].copy())
        new_entry['allPositions'] = [incoming['position'].copy()]
        new_entry['gameStatus'].update(isOnBench=False, isSubstitute=True)
        new_entry['stats']['batting']['gamesPlayed'] = 1
        if role not in ('PH', 'PR'):
            new_entry['stats']['fielding'].update(gamesPlayed=1, position=incoming['position'].copy())
        old_entry['gameStatus']['isCurrentBatter'] = False
        box['bench'].remove(incoming['id'])
        box['batters'].append(incoming['id'])
        box['battingOrder'][slot] = incoming['id']
        event_type = 'offensive_substitution' if role in ('PH', 'PR') else 'defensive_substitution'
        event = self._substitution_event(incoming, outgoing, incoming['position'], order, event_type)
        if role in ('PH', 'PR'):
            label = 'Pinch-hitter' if role == 'PH' else 'Pinch-runner'
            event['details']['description'] = f"Offensive Substitution: {label} {incoming['legal_name']} replaces {outgoing['legal_name']}."
            self._pending_defensive_switches[prefix].append((incoming, outgoing, order))
        else:
            event['details']['description'] = (f"Defensive Substitution: {incoming['legal_name']} replaces "
                                               f"{outgoing['legal_name']}, playing {position['name'].lower()}.")
        return event

    @staticmethod
    def _can_replace(incoming, outgoing):
        position = outgoing.get('_field_position', outgoing['position'])['abbreviation']
        return position == 'DH' or position in incoming.get('positions', [incoming['position']['abbreviation']])

    def _manage_offensive_substitutions(self, slot, pitcher):
        if self.inning < 6:
            return []
        prefix = 'team2' if self.top_of_inning else 'team1'
        lineup, bench = getattr(self, f"{prefix}_lineup"), getattr(self, f"{prefix}_bench")
        events = []
        if self.inning >= 8 and abs(self.team1_score - self.team2_score) <= 2:
            for base in (1, 0):
                name = self.bases[base]
                runner_slot = next((i for i, p in enumerate(lineup) if p['legal_name'] == name), None)
                if runner_slot is None:
                    continue
                runner = lineup[runner_slot]
                candidates = [p for p in bench if self._can_replace(p, runner)
                              and p['batting_profile']['stealing_tendency'] >= 0.15]
                if (runner['batting_profile']['stealing_tendency'] <= 0.02 and candidates
                        and self.game_rng.random() < 0.35):
                    incoming = max(candidates, key=self._speed_of)
                    events.append(self._substitute(prefix, runner_slot, incoming, 'PR'))
                    self.bases[base] = incoming['legal_name']
                    # Whoever put the replaced runner on base answers for him.
                    if runner['legal_name'] in self._runner_pitchers:
                        self._runner_pitchers[incoming['legal_name']] = self._runner_pitchers.pop(runner['legal_name'])
                    break
        batter = lineup[slot]
        profile = batter['batting_profile']
        weak_hitter = slot >= 5 and profile['contact'] < 0.86 and profile['power'] < 0.65
        same_hand = (pitcher.get('type') != 'Starter' and
                     batter.get('batSide', {}).get('code') == pitcher.get('pitchHand', {}).get('code', 'R'))
        if not weak_hitter and not (same_hand and slot not in (2, 3) and profile['contact'] < 0.84):
            return events
        candidates = [p for p in bench if self._can_replace(p, batter)]
        if same_hand:
            candidates = [p for p in candidates if p['batSide']['code'] != pitcher.get('pitchHand', {}).get('code', 'R')]
        if candidates and self.game_rng.random() < (0.24 if self.inning == 6 else 0.48):
            incoming = max(candidates, key=lambda p: p['batting_profile']['contact'] + 0.3 * p['batting_profile']['power'])
            events.append(self._substitute(prefix, slot, incoming, 'PH'))
        return events

    def _manage_defensive_substitutions(self):
        prefix = 'team1' if self.top_of_inning else 'team2'
        lineup, bench = getattr(self, f"{prefix}_lineup"), getattr(self, f"{prefix}_bench")
        events = []
        box = self.gameday_data['liveData']['boxscore']['teams'][self._pitching_team_key]
        for incoming, outgoing, order in self._pending_defensive_switches[prefix]:
            # A pinch runner may already have replaced this pinch hitter.
            if incoming not in lineup:
                continue
            position = incoming['_field_position'].copy()
            incoming['position'] = position
            entry = box['players'][f"ID{incoming['id']}"]
            entry['position'] = position.copy()
            entry['allPositions'].append(position.copy())
            entry['stats']['fielding'].update(gamesPlayed=1, position=position.copy())
            event = self._substitution_event(incoming, outgoing, position, order, 'defensive_switch')
            event['details']['description'] = f"{incoming['legal_name']} remains in the game at {position['name'].lower()}."
            events.append(event)
        self._pending_defensive_switches[prefix].clear()
        lead = self.team1_score - self.team2_score if self.top_of_inning else self.team2_score - self.team1_score
        if self.inning >= 7 and 0 < lead <= 4:
            candidates = [(i, p) for i, starter in enumerate(lineup) for p in bench
                          if starter['position']['abbreviation'] not in ('C', 'DH')
                          and self._can_replace(p, starter) and p['fielding_ability'] - starter['fielding_ability'] >= 0.008]
            if candidates and self.game_rng.random() < (0.24 if self.inning == 7 else 0.55):
                slot, incoming = max(candidates, key=lambda ip: ip[1]['fielding_ability'] - lineup[ip[0]]['fielding_ability'])
                natural_position = incoming['position'].copy()
                event = self._substitute(prefix, slot, incoming, 'defense')
                position = incoming['position']
                center = next((p for p in lineup if p['position']['abbreviation'] == 'CF'), None)
                if (natural_position['abbreviation'] == 'CF' and position['abbreviation'] in ('LF', 'RF')
                        and center and center['fielding_ability'] < incoming['fielding_ability']):
                    # The better center fielder takes center; the starter
                    # slides to a corner, retaining his own batting slot.
                    center['position'] = center['_field_position'] = position.copy()
                    center_entry = box['players'][f"ID{center['id']}"]
                    center_entry['position'] = position.copy()
                    center_entry.setdefault('allPositions', []).append(position.copy())
                    center_entry['stats']['fielding']['position'] = position.copy()
                    switch = self._substitution_event(center, center, position, center_entry['battingOrder'], 'defensive_switch')
                    switch.pop('replacedPlayer')
                    switch['details']['description'] = f"{center['legal_name']} moves to {position['name'].lower()}."
                    events.append(switch)
                    incoming['position'] = incoming['_field_position'] = natural_position
                    entry = box['players'][f"ID{incoming['id']}"]
                    entry['position'] = natural_position.copy()
                    entry['allPositions'] = [natural_position.copy()]
                    entry['stats']['fielding']['position'] = natural_position.copy()
                    event['position'] = natural_position.copy()
                    event['details']['description'] = (f"Defensive Substitution: {incoming['legal_name']} replaces "
                                                       f"{event['replacedPlayer']['fullName']}, playing center field.")
                events.append(event)
        self._setup_defense(prefix, getattr(self, f"{prefix}_data"))
        return events

    def _simulate_pitch_trajectory(self, pitcher, batter=None, balls=0, strikes=0):
        """
        Simulates the pitch's path and determines if it's in the strike zone.
        Returns a tuple: (is_strike_loc, zone_code)
        zone_code 1-9 are strike zones.
        11: High (Ball)
        12: Outside (Ball)
        13: Inside (Ball)
        14: Low (Ball)
        """
        stamina = pitcher['stamina'] + (STARTER_STAMINA_BONUS if pitcher.get('type') == 'Starter' else 0)
        fatigue_penalty = min(FATIGUE_PENALTY_CAP, (max(0, self.pitch_counts[pitcher['legal_name']] - stamina) / 15) * 0.1)

        # Determine "pitch around" penalty based on batter threat
        pitch_around_penalty = 0.0
        if batter:
            profile = batter.get('batting_profile', {})
            power = profile.get('power', 0.5)
            contact = profile.get('contact', 0.7)

            # Simple threat model: Power over 0.70 starts to matter
            if power > 0.70:
                pitch_around_penalty += (power - 0.70) * 0.15

            # High contact batters also get some respect if they have decent power
            if contact > 0.85 and power > 0.50:
                pitch_around_penalty += (contact - 0.85) * 0.10

            # Cap the penalty to avoid breaking the game (max ~5% drop in strike rate)
            pitch_around_penalty = min(pitch_around_penalty, 0.06)

        count_boost = COUNT_ZONE_ADJUSTMENTS[(balls, strikes)]
        # Right after a walk or a hit batter, a pitcher attacks the next man
        # rather than staying just as wild (judges read walk-HBP-walk as dice).
        if getattr(self, '_free_pass_pitcher', None) == pitcher['legal_name']:
            count_boost += AFTER_FREE_PASS_ZONE_BOOST
        is_strike = self.game_rng.random() < (pitcher['control'] - fatigue_penalty - 0.012 - pitch_around_penalty - ZONE_RATE_OFFSET + count_boost)

        if is_strike:
            # Weighted distribution for strike zones (1-9)
            # Corners (1, 3, 7, 9) and Edges (2, 4, 6, 8) are more common than Center (5)
            # Weights: Corners=1.5, Edges=1.0, Center=0.6
            zones = [1, 2, 3, 4, 5, 6, 7, 8, 9]
            weights = [1.5, 1.0, 1.5, 1.0, 0.6, 1.0, 1.5, 1.0, 1.5]
            zone = self.game_rng.choices(zones, weights=weights, k=1)[0]
        else:
            # Ball locations: 11 (High-Left), 12 (High-Right), 13 (Low-Left), 14 (Low-Right)
            # Low pitches (dirt) are more common than high misses generally
            # Weights: Low (13, 14)=3.0, High (11, 12)=2.0
            zones = [11, 12, 13, 14]
            weights = [2.0, 2.0, 3.0, 3.0]
            zone = self.game_rng.choices(zones, weights=weights, k=1)[0]

        return is_strike, zone

    def _simulate_bat_swing(self, batter, is_strike_loc, balls=0, strikes=0, zone=None, pitch_type=None):
        """Determines if the batter swings at the pitch."""
        discipline_factor = max(0.1, batter['plate_discipline'].get('Walk', 0.09) / 0.08)
        swing_at_ball_prob = CHASE_RATES[(balls, strikes)] / discipline_factor
        prob = ZONE_SWING_RATES[(balls, strikes)] if is_strike_loc else min(0.97, swing_at_ball_prob)
        if balls == 3 and strikes == 0:
            prob *= self._three_oh_swing_factor(batter, is_strike_loc, zone, pitch_type)
        return self.game_rng.random() < prob

    @staticmethod
    def _three_oh_swing_factor(batter, is_strike_loc, zone, pitch_type):
        """How much of a hitter's normal swing rate survives a 3-0 count.

        Most hitters take 3-0, but sluggers get the green light and will swing
        at a fastball down the middle. Green light strength scales with power:
        none at 0.60 and below, full at 0.90 and above.
        """
        power = batter.get('batting_profile', {}).get('power', 0.5)
        green = min(1.0, max(0.0, (power - 0.60) / 0.30))
        if not is_strike_loc:
            return 0.03 + 0.04 * green          # off the plate: almost never
        factor = 0.065 + 0.40 * green
        if zone == 5:
            factor *= 1.8                        # a cookie down the middle
        kind = (pitch_type or '').lower()
        if 'fastball' in kind or 'sinker' in kind or 'heater' in kind:
            factor *= 1.3
        elif any(k in kind for k in ('curve', 'slider', 'sweeper', 'change', 'knuckle', 'split')):
            factor *= 0.5                        # nobody's sitting on a 3-0 breaking ball
        return min(factor, 1.0)

    def _simulate_batted_ball_physics(self, batter, pitcher=None):
        """Calculates the exit velocity and launch angle of a batted ball."""
        batting_profile = batter['batting_profile']
        if FIELD_SIM:
            # Real 2026 balls in play: EV 87 +/- 15 with a weak-contact tail,
            # LA 14 +/- 29. The outcome table below was tuned to a much
            # narrower spread, so the field model gets its own generator.
            # Draw a real batted ball (EV and LA together, so weak pop-ups and
            # hard liners keep their real shapes) and shift it by the hitter.
            ev, la = self.game_rng.choice(_REAL_BATTED_BALLS)
            power = batting_profile.get('power', 0.5)
            ev = ev + (power - 0.54) * POWER_EV_SHIFT + self.game_rng.normalvariate(0, 2.0)
            la = la + (batting_profile.get('angle', 12.4) - 12.4) * 0.6 + self.game_rng.normalvariate(0, 3.0)
            return {'ev': round(min(max(ev, 35.0), 118.0), 1), 'la': round(la, 1),
                    'spray': self._batted_ball_spray(batter, pitcher, la)}
        # Power influences exit velocity, with some randomness
        ev = round(self.game_rng.normalvariate(80 + batting_profile['power'] * 25, 8), 1)
        # Angle influences launch angle, with some randomness
        # Increase SD to 15.0 to get more popups and grounders
        la = round(self.game_rng.normalvariate(batting_profile['angle'] + 4.5, 15.0), 1)
        return {'ev': ev, 'la': la}

    def _batted_ball_spray(self, batter, pitcher, la):
        """Degrees off center (negative = left field). Real feeds: grounders
        pulled ~17 degrees, liners ~7, fly balls slightly the other way."""
        side = batter.get('batSide', {}).get('code', 'R')
        if side == 'S':
            side = 'L' if (pitcher or {}).get('pitchHand', {}).get('code', 'R') == 'R' else 'R'
        pull = -1 if side == 'R' else 1
        if la < 10:
            mean, sd = 17 * pull, 27
        elif la <= 25:
            mean, sd = 7 * pull, 26
        else:
            mean, sd = -6 * pull, 34
        # Redraw rather than clip: clipping piled balls onto the foul lines
        # (more than half the homers went "down the line").
        for _ in range(8):
            spray = self.game_rng.normalvariate(mean, sd)
            if abs(spray) <= 44.0:
                return round(spray, 1)
        return round(max(-44.0, min(44.0, spray)), 1)

    def _defense_positions(self):
        """Position abbreviation -> player for the team in the field."""
        prefix = 'team1' if self.top_of_inning else 'team2'
        defense = dict(getattr(self, f"{prefix}_defense"))
        defense['P'] = getattr(self, f"{prefix}_pitcher_stats")[getattr(self, f"{prefix}_current_pitcher_name")]
        catcher = getattr(self, f"{prefix}_catcher", None)
        if catcher:
            defense['C'] = catcher
        return defense

    @staticmethod
    def _speed_of(player):
        """League-average runner = 1.0 (the field model was fit to average
        speed); base stealers run a few percent faster."""
        profile = (player or {}).get('batting_profile', {})
        return 1.0 + (min(profile.get('stealing_tendency', 0.0), 0.4) - 0.05) * 0.3

    def _runner_speeds(self):
        """Base number (1-3) -> speed for the runners on base."""
        by_name = {p['legal_name']: p for p in self.team1_lineup + self.team2_lineup}
        return {i + 1: self._speed_of(by_name.get(name)) for i, name in enumerate(self.bases) if name}

    def _apply_runner_dests(self, dests):
        """Move runners per base -> destination (4 = scores); returns runs."""
        old, runs = self.bases[:], 0
        self.bases = [None, None, None]
        for base, dest in dests.items():
            if dest >= 4:
                runs += 1
            else:
                self.bases[dest - 1] = old[base - 1]
        return runs

    def _play_batted_ball(self, batter, batted_ball_data):
        """Run the ball through the field model; returns the outcome name."""
        result = fieldsim.resolve(batted_ball_data['ev'], batted_ball_data['la'],
                                  batted_ball_data.get('spray', 0.0), self.game_rng,
                                  batter_speed=self._speed_of(batter))
        batted_ball_data['field'] = result
        self._play_field = result
        return result.outcome

    def _simulate_bunt_physics(self):
        """Calculates the exit velocity and launch angle for a bunt."""
        ev = round(self.game_rng.uniform(35, 65), 1)
        la = round(self.game_rng.uniform(-50, -20), 1)
        return {'ev': ev, 'la': la}

    def _bunt_plan(self, batter):
        """Mostly bottom-of-the-order hitters, for a base hit or one needed run."""
        profile = batter['batting_profile']
        if profile.get('power', 0.5) >= 0.65:
            return False, False
        lineup = self.team2_lineup if self.top_of_inning else self.team1_lineup
        slot = next(i for i, p in enumerate(lineup) if p['id'] == batter['id'])
        slot_factor = (0.3, 0.3, 0.05, 0.05, 0.8, 0.5, 1.6, 1.1, 4.8)[slot]
        propensity = profile.get('bunt_propensity', 0.0) * slot_factor
        sacrifice = (self.outs < 2 and any(self.bases) and not self.bases[2]
                     and abs(self.team1_score - self.team2_score) <= 3 and self.inning >= 2)
        rate = BUNT_RATE_FACTOR if sacrifice else BUNT_FOR_HIT_FACTOR
        if self.inning == 1:
            rate *= 0.2
        return self.game_rng.random() < min(0.45, propensity * rate), sacrifice

    def _determine_outcome_from_trajectory(self, ev, la):
        """Determines the outcome of a batted ball from its physics."""
        # Weak contact leading to outs
        if ev < 80:
            if la > 38: return "Pop Out"
            if la < 12: return "Groundout"
            return "Flyout"

        # Ground balls
        if la < 12:
            if ev > 108: return "Double Play" # Hard grounder at infielder
            if ev > 102: return "Single" # Hard grounder through the hole
            if ev > 92 and self.game_rng.random() < 0.30: return "Single" # Lucky finder
            return "Groundout"

        # Line drives
        if la < 21:
            if ev > 114: return "Home Run" # Screamer
            if ev > 107: return "Triple" if self.game_rng.random() < 0.10 else "Double"
            if ev > 95: return "Single"
            # Reduce Lineouts by converting weaker ones to Groundouts
            if ev < 85: return "Groundout"
            return "Lineout"

        # Fly balls (real feeds: ~2 pop-ups per team-game; most were flyouts here)
        if la < 43:
            if ev > 104: return "Home Run" # Reduced threshold
            if ev > 103: return "Triple" if self.game_rng.random() < 0.08 else "Double" # Gap shot
            if ev > 94 and self.game_rng.random() < 0.34: return "Double"
            if ev > 90 and self.game_rng.random() < 0.28: return "Single" # Bloop
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
            "Bunt Ground Out": "field_out",
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
        if outcome == "Pop Out": return "popup"
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
                       is_rbi, credits=None):
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
                "earned": is_scoring,
                "teamUnearned": False,
                "playIndex": play_index
            },
            "credits": credits if credits else []
        }

        # Add responsible pitcher if runner scored
        if is_scoring:
            responsible_pitcher = self._responsible_pitcher(runner_name)
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
        margin = -self._pitching_lead()
        score_modifier = 1.0
        if margin <= -2:
            # When several runs are needed, protect the baserunner.
            score_modifier = 0.3 if margin > -4 else 0.05
            if self.inning >= 7:
                score_modifier *= 0.5
        elif margin >= 4:
            score_modifier = 0.35 if margin < 6 else 0.05

        if self.bases[1] and not self.bases[2]:
            runner_name = self.bases[1]
            runner_data = next((p for p in batting_lineup if p['legal_name'] == runner_name), None)
            if runner_data:
                # Third is most useful with one out. Real runners still try
                # it with two outs, but seldom risk it down several runs.
                third_modifier = (0.7, 1.0, 0.55)[self.outs]
                if self.outs == 0 and (margin <= -2 or self.bases[0]):
                    third_modifier *= 0.25
                if runner_name in self._stolen_second_this_inning:
                    third_modifier *= 0.65
                attempt_chance = runner_data['batting_profile']['stealing_tendency'] * STEAL_THIRD_FACTOR * count_modifier * third_modifier * score_modifier
                if self.game_rng.random() < attempt_chance:
                    return 3

        if self.bases[0] and not self.bases[1]:
            runner_name = self.bases[0]
            runner_data = next((p for p in batting_lineup if p['legal_name'] == runner_name), None)
            if runner_data:
                attempt_chance = runner_data['batting_profile']['stealing_tendency'] * STEAL_SECOND_FACTOR * count_modifier * outs_modifier * score_modifier
                if self.game_rng.random() < attempt_chance:
                    return 2

        return None

    def _record_wild_pitch(self, play_events, balls, strikes):
        """A ball in the dirt gets away and the runners move up a base. (Only
        with third base open for now, so it never has to score a run.)"""
        batting_lineup = self.team1_lineup if not self.top_of_inning else self.team2_lineup
        ids = {p['legal_name']: p['id'] for p in batting_lineup}
        moves = []
        for idx in (1, 0):
            name = self.bases[idx]
            if name:
                moves.append({'runner': {'id': ids.get(name), 'fullName': name},
                              'fromBase': ('1B', '2B')[idx], 'toBase': ('2B', '3B')[idx], 'isOut': False})
                self.bases[idx + 1], self.bases[idx] = name, None
        play_events.append({
            'index': self._pitch_event_seq, 'startTime': self.current_time.isoformat(),
            'endTime': self.current_time.isoformat(), 'isPitch': False,
            'count': {'balls': balls, 'strikes': strikes},
            'details': {'description': 'Wild Pitch', 'code': '', 'isStrike': False,
                        'eventType': 'wild_pitch', 'runners': moves},
        })

    def _record_pickoff_throw(self, play_events, balls, strikes, pitcher, base=1):
        """Usually the runner gets back; occasionally he's out or the throw escapes."""
        batting_lineup = self.team1_lineup if not self.top_of_inning else self.team2_lineup
        runner_name = self.bases[base - 1]
        runner = next(p for p in batting_lineup if p['legal_name'] == runner_name)
        start_time = self.current_time.isoformat()
        self.current_time += timedelta(seconds=self.time_rng.uniform(4.0, 8.0))
        draw = self.game_rng.random()
        is_out = draw < PICKOFF_OUT_RATE
        is_error = not is_out and draw < PICKOFF_OUT_RATE + PICKOFF_ERROR_RATE and not self.bases[2]
        caught_stealing = is_out and base < 3 and not self.bases[base] and self.game_rng.random() < 0.5
        target = base + 1 if caught_stealing else base
        event_type = (f'pickoff_caught_stealing_{target}b' if caught_stealing else f'pickoff_{base}b') if is_out else ''
        event = {
            'index': self._pitch_event_seq,
            'startTime': start_time,
            'endTime': self.current_time.isoformat(),
            'isPitch': False, 'type': 'action' if is_out or is_error else 'pickoff',
            'count': {'balls': balls, 'strikes': strikes, 'outs': self.outs + int(is_out)},
            'details': {
                'description': f'Pickoff Attempt {base}B', 'code': str(base), 'isStrike': False,
                'isOut': is_out, 'fromCatcher': base == 3,
                'runners': [{'runner': self._player_ref(runner), 'fromBase': f'{base}B',
                             'toBase': f'{target}B', 'isOut': is_out}],
            },
        }
        if base < 3:
            event['details']['disengagementNum'] = 1 + sum(e.get('type') == 'pickoff' for e in play_events)
        if is_out:
            self.outs += 1
            self.bases[base - 1] = None
            defense = self._defense_positions()
            thrower = defense['C'] if base == 3 else pitcher
            fielder = defense[{1: '1B', 2: 'SS', 3: '3B'}[target]]
            credits = [self._create_credit(thrower, 'assist')]
            if caught_stealing:
                credits.append(self._create_credit(defense['1B' if base == 1 else 'SS'], 'assist'))
            credits.append(self._create_credit(fielder, 'putout'))
            if caught_stealing:
                self._update_batting_stat(self._batting_team_key, runner['id'], 'caughtStealing')
                title = f'Pickoff Caught Stealing {target}B'
            else:
                self._update_batting_stat(self._batting_team_key, runner['id'], 'pickoffs')
                if base != 3:
                    self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'pickoffs')
                else:
                    self._update_fielding_stat(self._pitching_team_key, thrower['id'], 'pickoffs')
                title = f'Pickoff {base}B'
            self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'outs')
            for credit in credits:
                self._update_fielding_stat(self._pitching_team_key, credit['player']['id'],
                                           'assists' if credit['credit'] == 'assist' else 'putOuts')
            event['details'].update(eventType=event_type, event=title,
                                    description=f"{runner_name} picked off at {target}B.")
            event.update(player=self._player_ref(runner), isBaseRunningPlay=True)
            entry = self._build_runner_entry(runner_name, f'{base}B', f'{target}B', True, self.outs,
                                             title, event_type, 'r_pickoff', len(play_events), False, False, credits=credits)
            self._between_pitch_runners.append(entry)
        elif is_error:
            moves = []
            for idx in (1, 0):
                name = self.bases[idx]
                if not name:
                    continue
                player = next(p for p in batting_lineup if p['legal_name'] == name)
                moves.append({'runner': self._player_ref(player), 'fromBase': f'{idx + 1}B',
                              'toBase': f'{idx + 2}B', 'isOut': False})
                self.bases[idx + 1], self.bases[idx] = name, None
                entry = self._build_runner_entry(name, f'{idx + 1}B', f'{idx + 2}B', False, None,
                                                 f'Pickoff Error {base}B', f'pickoff_error_{base}b',
                                                 'r_adv_play', len(play_events), False, False,
                                                 credits=[self._create_credit(pitcher, 'fielding_error')])
                self._between_pitch_runners.append(entry)
            event['details'].update(eventType=f'pickoff_error_{base}b', event=f'Pickoff Error {base}B',
                                    description='Throwing error on the pickoff attempt.', runners=moves)
            self._update_fielding_stat(self._pitching_team_key, pitcher['id'], 'errors')
            self.gameday_data['liveData']['linescore']['teams'][self._pitching_team_key]['errors'] += 1
        play_events.append(event)
        self._pitch_event_seq += 1
        return is_out

    def _steal_movement(self, runner, base_to_steal, is_out):
        """Who ran, as a feed's runner movement for the steal names him. An
        automatic runner caught stealing before the first play of an extra
        inning ends is in no other record of that play."""
        throw = 'in_time'
        if not is_out:
            # The catcher may hold the ball with no play, especially at third.
            no_throw_chance = 0.30 if base_to_steal == 3 else 0.15
            throw = 'none' if self.steal_rng.random() < no_throw_chance else 'not_in_time'
        return {'runner': {'id': runner['id'], 'fullName': runner['legal_name']},
                'fromBase': f'{base_to_steal - 1}B', 'toBase': f'{base_to_steal}B', 'isOut': is_out,
                # Extension fields (a feed has neither): the catcher's throw
                # and the slide, for the narration.
                'throw': throw, 'slide': self.steal_rng.random() < (0.4 if throw == 'none' else 0.9)}

    def _resolve_steal_attempt(self, base_to_steal, play_events: list[PlayEvent], balls, strikes):
        is_home_team_batting = not self.top_of_inning
        batting_lineup = self.team1_lineup if is_home_team_batting else self.team2_lineup
        defensive_catcher = self.team2_catcher if is_home_team_batting else self.team1_catcher

        base_from_idx = base_to_steal - 2
        runner_name = self.bases[base_from_idx]
        runner_data = next((p for p in batting_lineup if p['legal_name'] == runner_name), None)

        if not runner_data:
            return False # Should not happen

        # Advance time for the steal play (throw, tag, etc.)
        steal_duration = self.time_rng.uniform(3.0, 6.0)
        start_time = self.current_time.isoformat()
        self.current_time += timedelta(seconds=steal_duration)
        end_time = self.current_time.isoformat()

        # Third gives the catcher a shorter throw; the same runner needs a
        # better jump than he would stealing second.
        base_bonus = 0.05 if base_to_steal == 2 else -0.02
        success_chance = min(0.96, runner_data['batting_profile']['stealing_success_rate'] + base_bonus - (defensive_catcher['catchers_arm'] * 0.04))
        if self.game_rng.random() < success_chance:
            self.bases[base_to_steal - 1] = runner_name
            self.bases[base_from_idx] = None
            if base_to_steal == 2:
                self._stolen_second_this_inning.add(runner_name)

            self._update_batting_stat(self._batting_team_key, runner_data['id'], 'stolenBases')
            # Record Stolen Base Event
            event: PlayEvent = {
                 'index': self._pitch_event_seq,
                 'startTime': start_time,
                 'endTime': end_time,
                 'isPitch': False,
                 'count': {'balls': balls, 'strikes': strikes},
                 'details': {
                     'description': f"Stolen Base {base_to_steal}B",
                     'code': 'X', # In play/action?
                     'isStrike': False,
                     'type': {'code': 'AS', 'description': 'Action'},
                     'eventType': 'stolen_base',
                     'runners': [self._steal_movement(runner_data, base_to_steal, False)],
                 }
             }
            play_events.append(event)
            self._pitch_event_seq += 1
            return False # Not caught
        else:
            self.outs += 1
            self.bases[base_from_idx] = None

            self._update_batting_stat(self._batting_team_key, runner_data['id'], 'caughtStealing')
            pitcher = self._pitching_side()[2]
            self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'outs')
            defense = self._defense_positions()
            fielder = defense['SS' if base_to_steal == 2 else '3B']
            credits = [self._create_credit(defensive_catcher, 'assist'), self._create_credit(fielder, 'putout')]
            self._update_fielding_stat(self._pitching_team_key, defensive_catcher['id'], 'assists')
            self._update_fielding_stat(self._pitching_team_key, fielder['id'], 'putOuts')
            self._between_pitch_runners.append(self._build_runner_entry(
                runner_name, f'{base_to_steal - 1}B', f'{base_to_steal}B', True, self.outs,
                'Caught Stealing', 'caught_stealing', 'r_caught_stealing', len(play_events), False, False, credits=credits))
            # Record Caught Stealing Event
            event: PlayEvent = {
                 'index': self._pitch_event_seq,
                 'startTime': start_time,
                 'endTime': end_time,
                 'isPitch': False,
                 'count': {'balls': balls, 'strikes': strikes},
                 'details': {
                     'description': f"Caught Stealing {base_to_steal}B",
                     'code': 'X',
                     'isStrike': False,
                     'type': {'code': 'AS', 'description': 'Action'},
                     'eventType': 'caught_stealing',
                     'runners': [self._steal_movement(runner_data, base_to_steal, True)],
                 }
             }
            play_events.append(event)
            self._pitch_event_seq += 1
            return True # Caught stealing

    def _simulate_at_bat(self, batter, pitcher):
        balls, strikes = 0, 0
        play_events: list[PlayEvent] = []
        
        # HBP happens on a pitch outside the zone, mid at-bat, so the pitches
        # before it get narrated (it used to end the PA before the first pitch).
        # The count-dependent model supplies more out-of-zone opportunities;
        # scale the per-PA rating to keep HBP near the real feeds' 1.1% of PA.
        hbp_per_ball = batter['plate_discipline'].get('HBP', 0) * 1.4

        is_bunting, sacrifice = self._bunt_plan(batter)

        while balls < 4 and strikes < 3:
            pitch_start_time = self.current_time.isoformat()
            # Batters give up the bunt with two strikes: a foul bunt there is
            # strike three, so only the rare (pitcher-ish) bunter keeps it on.
            bunting_now = is_bunting and (strikes < 2 or self.game_rng.random() < 0.1)
            if bunting_now and any(e.get('isBunt') for e in play_events):
                # After a failed attempt he usually swings away; three bunt
                # tries in one at-bat was a tell.
                is_bunting = bunting_now = self.game_rng.random() < 0.2
            # Two disengagements per plate appearance under the pitch clock,
            # and a second throw over is rarer than the first.
            throws_this_pa = sum(1 for e in play_events if e.get('type') == 'pickoff'
                                 or e.get('details', {}).get('eventType', '').startswith('pickoff'))
            base = next((i + 1 for i, name in enumerate(self.bases) if name), None)
            if base and throws_this_pa < 2:
                rate = {1: PICKOFF_THROW_RATE, 2: 0.011, 3: 0.008}[base]
                if self.game_rng.random() < rate * (0.5 if throws_this_pa else 1):
                    self._record_pickoff_throw(play_events, balls, strikes, pitcher, base)
                    if self.outs >= 3:
                        return play_events[-1]['details']['event'], None, play_events
                    pitch_start_time = self.current_time.isoformat()

            # Advance time for the pitch (median ~20.4s)
            time_between_pitches = self.time_rng.uniform(18.0, 26.0)
            self.current_time += timedelta(seconds=time_between_pitches)
            pitch_end_time = self.current_time.isoformat()

            pitch_outcome_text = ""
            steal_attempt_base = self._decide_steal_attempt(balls, strikes)
            
            self.pitch_counts[pitcher['legal_name']] += 1
            pitch_selection = self._select_pitch_type(pitcher, batter, balls, strikes)
            pitch_details_team = pitcher['pitch_arsenal'][pitch_selection]
            pitch_velo = round(self.game_rng.uniform(*pitch_details_team['velo_range']), 1)
            pitch_spin = self.game_rng.randint(*pitch_details_team.get('spin_range', (2000, 2500))) if self.game_rng.random() > 0.08 else None
            
            is_strike_loc, pitch_zone = self._simulate_pitch_trajectory(pitcher, batter, balls, strikes)
            if not is_strike_loc and not bunting_now and self.game_rng.random() < hbp_per_ball:
                self._update_batting_stat(self._batting_team_key, batter['id'], 'hitByPitch')
                self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'hitByPitch')
                return "Hit By Pitch", None, play_events
            
            pre_pitch_balls, pre_pitch_strikes = balls, strikes
            event_details: PlayEvent['details'] = {}
            is_in_play = False
            hit_result = None

            swing = self._simulate_bat_swing(batter, is_strike_loc, balls, strikes, pitch_zone, pitch_selection) or bunting_now
            contact_prob = batter['batting_profile']['contact'] + CONTACT_BOOST
            if strikes == 2 or balls >= 2:
                contact_prob += COUNT_CONTACT_BOOST
            if not is_strike_loc:
                contact_prob *= TWO_STRIKE_CHASE_CONTACT_FACTOR if strikes == 2 else CHASE_CONTACT_FACTOR
            contact = self.game_rng.random() < (BUNT_CONTACT_RATE if bunting_now else contact_prob)

            play_event: PlayEvent = {
                'index': self._pitch_event_seq,
                'startTime': pitch_start_time,
                'endTime': pitch_end_time,
                'isPitch': True,
                'count': {'balls': pre_pitch_balls, 'strikes': pre_pitch_strikes}
            }
            if bunting_now:
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
                    # Real two-strike foul rates stay near 24% of pitches,
                    # including after a foul. A large foul bonus followed
                    # by decay produced too many short battles and capped
                    # the rare long ones.
                    foul_share = BUNT_FOUL_SHARE if bunting_now else FOUL_SHARE_OF_CONTACT
                    if strikes == 2 and not bunting_now:
                        foul_share += TWO_STRIKE_FOUL_BONUS
                    elif balls == 3 and strikes == 0 and not bunting_now:
                        foul_share *= 0.65  # green lights are swings at pitches he can drive
                    is_foul = self.game_rng.random() < foul_share
                    if is_foul:
                        if strikes < 2 or bunting_now: strikes += 1
                        pitch_outcome_text = "foul"
                        event_details = {'code': 'F', 'description': 'Foul', 'isStrike': True}
                        self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'strikes')
                        if bunting_now:
                            event_details['description'] = 'Foul Bunt'
                            if strikes == 3: # Foul bunt with 2 strikes is a strikeout
                                pitch_outcome_text = "strikeout"
                    else: # In Play
                        is_in_play = True
                        if bunting_now:
                            batted_ball_data = self._simulate_bunt_physics()
                            if self.game_rng.random() < 0.28:
                                hit_result = "Single"
                                batted_ball_data['bunt_fielder'] = self.game_rng.choices(['P', '3B', '1B', 'C'], [45, 30, 15, 10])[0]
                            else:
                                hit_result = "Sacrifice Bunt" if sacrifice else "Bunt Ground Out"
                        else:
                            batted_ball_data = self._simulate_batted_ball_physics(batter, pitcher)
                            if FIELD_SIM:
                                hit_result = self._play_batted_ball(batter, batted_ball_data)
                            else:
                                hit_result = self._determine_outcome_from_trajectory(batted_ball_data['ev'], batted_ball_data['la'])
                        pitch_outcome_text = "in play"
                        event_details = {'code': 'X', 'description': f'In play, {hit_result}', 'isStrike': True}
                        self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'strikes')

            self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'numberOfPitches')
            event_details['type'] = {'code': GAME_CONTEXT['PITCH_TYPE_MAP'].get(pitch_selection, 'UN'), 'description': pitch_selection.capitalize()}
            event_details['zone'] = pitch_zone

            pitch_data: PitchData = {'startSpeed': pitch_velo, 'zone': pitch_zone}
            if pitch_spin: pitch_data['breaks'] = {'spinRate': pitch_spin}

            play_event['details'] = event_details
            play_event['pitchData'] = pitch_data
            play_events.append(play_event)
            if (event_details.get('code') == 'B' and balls < 4 and not steal_attempt_base
                    and (self.bases[0] or self.bases[1]) and not self.bases[2]
                    and self.game_rng.random() < pitcher.get('wild_pitch_rate', 0.003) * WILD_PITCH_FACTOR):
                self._record_wild_pitch(play_events, balls, strikes)
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
                        'trajectory': self._get_trajectory(hit_result, batted_ball_data.get('la')),
                        # Exit velocity also describes bunts and balls played
                        # without the field model; their hardness is known.
                        'hardness': fieldsim.hardness(batted_ball_data['ev']),
                    }
                    if bunting_now:
                        hit_data['trajectory'] = 'bunt_grounder'
                        hit_data['location'] = batted_ball_data.get('bunt_fielder', 'P')
                        hit_data.update(hardness='soft', depth=None, lane=None)
                    field = batted_ball_data.get('field')
                    if field is not None:
                        hit_data['trajectory'] = field.trajectory
                        hit_data['coordinates'] = field.coordinates
                        hit_data['totalDistance'] = round(field.distance)
                        # The field model knows where the ball went: "into
                        # the gap", "on the warning track", "hard grounder".
                        # Both keys always present: a null says "nothing
                        # notable", so the renderer does not derive its own.
                        hit_data.update({'depth': None, 'lane': None, **fieldsim.spot(field)})
                        if hit_result in ["Single", "Double", "Triple", "Home Run"]:
                            hit_data['location'] = field.location
                    elif not bunting_now and hit_result in ["Single", "Double", "Triple", "Home Run"]:
                        hit_data['location'] = self._determine_hit_location(hit_result, batted_ball_data['ev'], batted_ball_data['la'])
                    play_events[-1]['hitData'] = hit_data
                return hit_result, description_context, play_events

            # If the ball is not in play, now we resolve the steal attempt.
            if steal_attempt_base:
                if pitch_outcome_text == "foul" or balls == 4:
                    # On ball four the runner is waved down (or forced): no steal.
                    pass
                elif strikes == 3 and self.outs >= 2:
                    # Strike three is the third out: the inning is over, and
                    # no steal or caught stealing is scored behind it.
                    pass
                else:
                    caught_stealing = self._resolve_steal_attempt(steal_attempt_base, play_events, balls, strikes)
                    if caught_stealing and self.outs >= 3:
                        return "Caught Stealing", None, play_events
                    elif caught_stealing and strikes == 3:
                        # "Strike 'em out, throw 'em out" double play
                        self.outs += 1
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

        if hit_type in ["Walk", "HBP", "Hit By Pitch"]:
            new_bases = self.bases[:]
            if new_bases[0]:
                if new_bases[1]:
                    if new_bases[2]: runs += 1; rbis += 1; advances.append(f"{new_bases[2]} scores")
                    advances.append(f"{new_bases[1]} to 3B"); new_bases[2] = new_bases[1]
                advances.append(f"{new_bases[0]} to 2B"); new_bases[1] = new_bases[0]
            new_bases[0] = batter_name
            self.bases = new_bases
            return {'runs': runs, 'rbis': rbis, 'advances': advances}

        field = getattr(self, '_play_field', None)
        if FIELD_SIM and field is not None and not was_error and hit_type in ('Single', 'Double'):
            # The field model says how far each runner gets before the throw.
            old_bases = self.bases[:]
            close = {}
            dests, thrown_out = fieldsim.advance_on_hit(field, hit_type, self._runner_speeds(), self.outs,
                                                        self.game_rng, close=close)
            # Runners who took the extra base just ahead of the throw.
            self._close_plays = {old_bases[base - 1] for base in close}
            runs = self._apply_runner_dests(dests)
            for base, dest in sorted(dests.items(), reverse=True):
                name = old_bases[base - 1]
                advances.append(f"{name} scores" if dest == 4 else f"{name} to {dest}B")
            # Runners cut down on the bases (and a batter out stretching):
            # (name, base he started the play on or None for the batter, base he was out at).
            self._thrown_out = [(old_bases[base - 1], base, out_base) for base, out_base in thrown_out.items()]
            if field.batter_out:
                self._thrown_out.append((batter_name, None, field.batter_out))
            else:
                self.bases[{'Single': 0, 'Double': 1}[hit_type]] = batter_name
                if include_batter_advance:
                    advances.append(f"{batter_name} to {'1B' if hit_type == 'Single' else '2B'}")
            self.outs += len(self._thrown_out)
            return {'runs': runs, 'rbis': runs, 'advances': advances}

        old_bases = self.bases[:]
        new_bases = [None, None, None]
        if hit_type == 'Single':
            if old_bases[2]: runs += 1; rbis += (1 if batter_gets_rbi else 0); advances.append(f"{old_bases[2]} scores")
            if old_bases[1]:
                # With two out the runners go on contact instead of waiting
                # to see the ball fall. The field model times this above.
                if self.game_rng.random() < (0.78 if self.outs == 2 else 0.50):
                    runs += 1; rbis += (1 if batter_gets_rbi else 0); advances.append(f"{old_bases[1]} scores")
                else:
                    new_bases[2] = old_bases[1]; advances.append(f"{old_bases[1]} to 3B")
            if old_bases[0]:
                target = 2 if not new_bases[2] and self.game_rng.random() < (0.40 if self.outs == 2 else 0.25) else 1
                new_bases[target] = old_bases[0]; advances.append(f"{old_bases[0]} to {target + 1}B")
            new_bases[0] = batter_name
            if include_batter_advance: advances.append(f"{batter_name} to 1B")
        elif hit_type == 'Double':
            if old_bases[2]: runs += 1; rbis += (1 if batter_gets_rbi else 0); advances.append(f"{old_bases[2]} scores")
            if old_bases[1]: runs += 1; rbis += (1 if batter_gets_rbi else 0); advances.append(f"{old_bases[1]} scores")
            if old_bases[0]:
                if self.game_rng.random() < (0.55 if self.outs == 2 else 0.20):
                    runs += 1; rbis += (1 if batter_gets_rbi else 0); advances.append(f"{old_bases[0]} scores")
                else:
                    new_bases[2] = old_bases[0]; advances.append(f"{old_bases[0]} to 3B")
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

    def _responsible_pitcher(self, runner_name):
        """Who put this runner on base, or the pitcher on the mound if no one was
        recorded for him (a runner who came on some other way)."""
        return self._runner_pitchers.get(runner_name) or self._pitching_side()[2]

    def _pitching_side(self):
        """(prefix, current pitcher's name, his stats, the bullpen) for the team in the field."""
        prefix = 'team1' if self.top_of_inning else 'team2'
        name = getattr(self, f"{prefix}_current_pitcher_name")
        return prefix, name, getattr(self, f"{prefix}_pitcher_stats")[name], getattr(self, f"{prefix}_available_bullpen")

    def _pitching_lead(self):
        """Runs the team in the field leads by (negative when it trails)."""
        lead = self.team1_score - self.team2_score
        return lead if self.top_of_inning else -lead

    def _pick_reliever(self, prefix, bullpen):
        """Who comes in: the closer to protect a late lead, the long man when
        the starter is gone early or the game is out of hand, a setup man late
        and close, otherwise the next middle reliever."""
        stats = getattr(self, f"{prefix}_pitcher_stats")
        lead = self._pitching_lead()

        def first(*roles):
            return next((name for name in bullpen if stats[name].get('type') in roles), None)

        pick = None
        if self.inning >= 9 and 0 <= lead <= 3:
            pick = first('Closer')
        elif self.inning <= 4 or abs(lead) >= BLOWOUT_MARGIN:
            pick = first('Long Reliever')
        elif self.inning >= 7 and 0 <= lead <= 3:
            pick = first('Setup Reliever')
        return (pick or first('Middle Reliever', 'Reliever') or first('Long Reliever')
                or first('Setup Reliever') or bullpen[0])

    def _saving_the_bullpen(self, stats):
        """With the game out of hand nobody burns his best relievers: whoever
        is in stays in while he has pitches left."""
        return abs(self._pitching_lead()) >= BLOWOUT_MARGIN and stats.get('type') != 'Starter'

    def _bring_in(self, prefix, bullpen, mid_inning):
        name = self._pick_reliever(prefix, bullpen)
        self._entered_inning[name] = self.inning
        self._entered_mid_inning[name] = mid_inning
        self._half_pitcher_entry[name] = self.team2_score if self.top_of_inning else self.team1_score
        setattr(self, f"{prefix}_current_pitcher_name", name)
        setattr(self, f"{prefix}_available_bullpen", [n for n in bullpen if n != name])

    def _manage_pitching_change(self):
        """The mid-inning hook, before a batter. Mid-inning hooks are for
        trouble: a starter out of pitches with men on, a pitcher being hit
        hard this inning, a reliever who has faced his three batters and put
        the tying run in scoring position."""
        prefix, name, stats, bullpen = self._pitching_side()
        if not bullpen:
            return
        rng = self.game_rng
        pitches = self.pitch_counts[name]
        faced = self._batters_faced[name]
        if faced < 3:
            # The three-batter minimum applies to starters as well.
            return
        runs = self._runs_allowed[name]
        batting_score = self.team2_score if self.top_of_inning else self.team1_score
        inning_runs = batting_score - self._half_pitcher_entry.get(name, batting_score)
        traffic = self._half_pitcher_traffic.get(name, 0)
        homers = self._half_pitcher_homers.get(name, 0)
        runners_on = any(self.bases)
        scoring_position = bool(self.bases[1] or self.bases[2])
        close = abs(self._pitching_lead()) <= 3
        if stats.get('type') == 'Starter':
            budget = self._pitch_budget[name] - min(16, max(0, runs - 3) * 4)
            change = (
                # (a manager gives him a little longer early, to spare the bullpen)
                inning_runs >= (5 if self.inning <= 2 else 4)
                or homers >= 3
                or (traffic >= 5 and inning_runs >= 2 and self.inning > 2)
                or (inning_runs >= 3 and runners_on and self.inning > 2 and rng.random() < 0.5)
                or (runs >= 6 and runners_on)
                or pitches >= budget + 10
                or (pitches >= budget and runners_on)
                # Third time through the order with the game on the bases.
                or (faced >= 18 and pitches >= budget - 20 and scoring_position
                    and self.inning >= 5 and close and rng.random() < 0.2))
        elif self._saving_the_bullpen(stats):
            change = inning_runs >= 5 or homers >= 3 or pitches >= stats['stamina'] + 25
        else:
            stamina = stats['stamina']
            second_inning = self._entered_inning.get(name, self.inning) < self.inning
            change = (
                inning_runs >= 4
                or (homers >= 2 and traffic >= 4)
                or (traffic >= 5 and inning_runs >= 2)
                or (inning_runs >= 3 and runners_on)
                or (inning_runs >= 2 and runners_on and rng.random() < 0.5)
                or pitches >= stamina + 20
                or (pitches >= stamina + 4 and runners_on)
                # Sent back out for another inning, he's on a short leash.
                or (second_inning and runners_on and rng.random() < 0.15)
                or (self.inning >= 6 and close and scoring_position and stats.get('type') != 'Closer'
                    and rng.random() < LATE_TROUBLE_HOOK_RATE))
        if change:
            self._bring_in(prefix, bullpen, mid_inning=True)

    def _manage_between_innings(self):
        """Change pitchers before the half starts, the way most changes happen:
        a starter near his limit doesn't start an inning he can't finish, and
        relievers work an inning (two or three for the long man)."""
        prefix, name, stats, bullpen = self._pitching_side()
        if not bullpen:
            return
        rng = self.game_rng
        pitches = self.pitch_counts[name]
        faced = self._batters_faced[name]
        runs = self._runs_allowed[name]
        role = stats.get('type', '')
        lead = self._pitching_lead()
        if role == 'Starter':
            budget = self._pitch_budget[name] - min(16, max(0, runs - 3) * 4)
            reserve = 6 if runs <= 1 and faced < 24 else INNING_PITCHES
            if runs >= 4:
                reserve = 14
            change = (
                pitches >= budget - reserve
                or (runs >= 5 and rng.random() < 0.6)
                or (runs >= 4 and faced >= 18 and rng.random() < 0.35)
                or (faced >= 27 and rng.random() < 0.5))
        elif pitches == 0:
            change = False   # he hasn't thrown a pitch yet
        elif self.inning >= 9 and 0 <= lead <= 3 and any(
                getattr(self, f"{prefix}_pitcher_stats")[n].get('type') == 'Closer' for n in bullpen):
            change = True    # the closer's inning
        elif self._saving_the_bullpen(stats):
            change = pitches >= stats['stamina'] + 5
        elif role == 'Long Reliever':
            change = pitches >= stats['stamina'] - 8 or runs >= 3 or rng.random() < 0.1
        elif role == 'Closer':
            change = True
        elif self._entered_mid_inning.get(name) and self._entered_inning.get(name) == self.inning - 1:
            # He got the last out or two of the inning: often back out for the next.
            change = pitches > 20 or runs >= 2 or rng.random() < 0.15
        else:
            # A cheap, scoreless inning can earn him another, particularly
            # early. Late in a close game the next rested arm is more likely.
            hook_chance = 0.65 if self.inning >= 7 and abs(lead) <= 3 else 0.5
            if pitches <= 12 and runs == 0:
                hook_chance *= 0.5
            change = pitches > 20 or runs >= 2 or rng.random() < hook_chance
        if change:
            self._bring_in(prefix, bullpen, mid_inning=False)

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

    def _thrown_out_credits(self, field, out_base):
        """Who gets the assist and the putout on a runner thrown out at
        `out_base` (2, 3, or 4 for home) after a hit: the outfielder who came
        up with the ball, a relay man on a long throw, and whoever has the bag."""
        defense = self._defense_positions()
        thrower = defense.get(field.fielder)
        left_side = field.spray < 0
        receiver = {4: 'C', 3: '3B'}.get(out_base, '2B' if left_side else 'SS')
        chain = [thrower]
        origin = field.release_point or field.landing
        if out_base == 4 and fieldsim.distance(origin, fieldsim.HOME) > 270:
            chain.append(defense.get('SS' if left_side else '2B'))
        credits = [self._create_credit(player, 'assist') for player in chain if player]
        if defense.get(receiver):
            credits.append(self._create_credit(defense[receiver], 'putout'))
        return credits

    def _thrown_out_description(self, batter, outcome, play_events, thrown_out):
        """The feed's description of a hit with a runner thrown out: "Sam Decker
        singles on a line drive to right fielder TJ Hawkins. Leo Vance out at
        home on the throw, right fielder TJ Hawkins to catcher Hank Barrett."""
        field = self._play_field
        fielder = self._defense_positions().get(field.fielder)

        def title(position):
            name = position['name'].lower()
            return name + ('er' if name.endswith('field') else 'man' if name.endswith('base') else '')

        ball = {'ground_ball': 'ground ball', 'line_drive': 'line drive', 'fly_ball': 'fly ball',
                'popup': 'pop up'}.get(field.trajectory, 'ball')
        text = f"{batter['legal_name']} {outcome.lower()}s on a {ball}"
        if fielder:
            text += f" to {title(fielder['position'])} {fielder['legal_name']}"
        text += "."
        for name, out_base, credits in thrown_out:
            where = {2: '2nd', 3: '3rd'}.get(out_base, 'home')
            chain = " to ".join(f"{title(c['position'])} {c['player']['fullName']}" for c in credits)
            text += f" {name} out at {where} on the throw, {chain}."
        return text

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
        
        field = batted_ball_data.get('field')
        if field is not None and out_type not in ('Sacrifice Bunt', 'Bunt Ground Out'):
            # The field model already decided who caught or fielded it.
            fielder = self._defense_positions().get(field.fielder)
        if fielder is not None:
            pass
        elif out_type in ('Sacrifice Bunt', 'Bunt Ground Out'):
            # A bunt is fielded in front of the plate: by the pitcher, a
            # charging corner infielder or the catcher, never "to short".
            bunt_fielders = [(pitcher, 45), (defense.get('3B'), 30), (first_baseman, 15), (catcher, 10)]
            bunt_fielders = [(p, w) for p, w in bunt_fielders if p]
            fielder = self.game_rng.choices([p for p, _ in bunt_fielders], weights=[w for _, w in bunt_fielders], k=1)[0]
        elif out_type in ['Groundout', 'Sacrifice Bunt', 'Lineout', 'Pop Out', 'Forceout', 'Grounded Into DP', 'Double Play']:
            grounder_candidates = [(p, 6) for p in infielders] + [(pitcher, 1)] + ([(catcher, 0.25)] if catcher else [])
            fielder = self.game_rng.choices([c[0] for c in grounder_candidates], weights=[c[1] for c in grounder_candidates], k=1)[0]
            if fielder['position']['abbreviation'] == 'C' and 'ev' in batted_ball_data:
                batted_ball_data['ev'], batted_ball_data['la'] = round(self.game_rng.uniform(50, 70), 1), round(self.game_rng.uniform(-45, -20), 1)
        elif out_type == 'Flyout' or out_type == 'Sac Fly':
            fielder = self.game_rng.choices(outfielders + infielders, weights=[6] * len(outfielders) + [1] * len(infielders), k=1)[0]

        # Batters reach on an error in ~0.8% of PAs (about 0.3 per team-game);
        # MLB's ~0.55 errors per team-game also counts throws on runners. The
        # full fielding-ability miss rate doubled that, and two-error innings
        # read as a dice-rolling engine.
        miss_rate = 1 - fielder['fielding_ability'] * (self.team1_data if self.top_of_inning else self.team2_data)['fielding_prowess'] * 1.006 if fielder else 0
        if fielder and self.game_rng.random() > 1 - miss_rate * 0.5:
            is_error = True

        if is_error:
            credits = [self._create_credit(fielder, 'fielding_error')]
            return 0, True, 0, credits, [], [], False, "Field Error", None

        runs, rbis = 0, 0
        if out_type in ['Flyout', 'Pop Out', 'Lineout']:
            fielder_pos = fielder['position']['abbreviation']
            credits.append(self._create_credit(fielder, 'putout'))

            if field is not None and FIELD_SIM:
                # Runners tag up when the catch is deep enough to beat the throw.
                self.outs += 1
                dests = fieldsim.tag_ups(field, self._runner_speeds(), self.outs, self.game_rng)
                runs = self._apply_runner_dests(dests)
                if runs:
                    return runs, False, runs, credits, [], [], False, "Sac Fly", None
                return 0, False, 0, credits, [], [], False, out_type, None

            # Sac Fly logic
            if self.outs < 2 and self.bases[2] and fielder_pos in ['LF', 'CF', 'RF'] and self.game_rng.random() > 0.15:
                self.outs += 1
                runs, rbis = 1, 1
                runner_on_third, self.bases[2] = self.bases[2], None
                specific_event = "Sac Fly"
                return runs, False, rbis, credits, [], [], False, specific_event, None
            else:
                self.outs += 1
                specific_event = out_type
                return runs, False, rbis, credits, [], [], False, specific_event, None

        if FIELD_SIM and field is not None and out_type == 'Groundout':
            return self._field_ground_out(batter, field, fielder, defense, catcher, first_baseman)

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
                dp_runs = 0
                if self.bases[2] and self.outs < 3:
                    # The runner on third scores on a double play that doesn't end
                    # the inning (no RBI); he used to vanish under the man from second.
                    dp_runs = 1
                    self.bases[2] = None
                if self.bases[1]: self.bases[2], self.bases[1] = self.bases[1], None

                credits_runner, credits_batter = self._get_double_play_participants(fielder, defense)

                # Combine for the main return, but we will access specifics later
                credits = credits_batter

                return dp_runs, False, 0, credits, credits_batter, credits_runner, True, "Double Play", runner_out

            # Bases loaded, fewer than two outs, ball on the infield: the play
            # is home for the force, not to first (which lets the run score).
            if (self.outs < 2 and all(self.bases) and out_type in ('Groundout', 'Forceout')
                    and fielder['position']['abbreviation'] in ('P', 'C', '1B', '2B', '3B', 'SS')
                    and self.game_rng.random() < 0.3):
                forced = self.bases[2]
                self.outs += 1
                self.bases = [batter['legal_name'], self.bases[0], self.bases[1]]
                credits = [self._create_credit(fielder, 'assist'), self._create_credit(catcher, 'putout')] if catcher else [self._create_credit(fielder, 'putout')]
                self._last_force = (forced, '3B', 'score')
                return 0, False, 0, credits, [], credits, False, "Forceout", forced

            # Check for force play situation (not a double play)
            # The force at second also happens with two out (the most common
            # way an inning ends on a ground ball) and with a runner on second
            # too, who is forced to third. Real feeds: ~0.6 forceouts per
            # team-game; this was ~0.3.
            is_force_play = False
            force_base = None
            if (self.bases[0] and not all(self.bases)
                    and self.game_rng.random() < (0.38 if self.outs == 2 else 0.28)):
                is_force_play = True
                force_base = "2B"

            if is_force_play:
                forced = self.bases[0]
                self.outs += 1
                self.bases = [batter['legal_name'], None, self.bases[1] or self.bases[2]]  # Batter reaches
                ss = getattr(self, f"{defensive_team_prefix}_defense").get('SS')
                credits = [self._create_credit(fielder, 'assist'), self._create_credit(ss, 'putout')]
                self._last_force = (forced, '1B', '2B')
                return 0, False, 0, credits, [], credits, False, "Forceout", forced

            self.outs += 1
            if self.outs < 3:
                if self.bases[2]: runs, rbis, self.bases[2] = 1, 1, None
                if self.bases[1]: self.bases[2], self.bases[1] = self.bases[1], None
                if self.bases[0]: self.bases[1], self.bases[0] = self.bases[0], None
            else:
                runs, rbis = 0, 0
            specific_event = "Groundout"

        elif out_type in ('Sacrifice Bunt', 'Bunt Ground Out'):
            runners_advanced = False
            self.outs += 1
            if out_type == 'Sacrifice Bunt' and self.outs < 3 and any(self.bases) and not self.bases[2]:
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

        if out_type in ('Sacrifice Bunt', 'Bunt Ground Out') and fielder['position']['abbreviation'] == '1B' and defense.get('2B'):
            # The first baseman charged the bunt; the second baseman covers first.
            credits = [self._create_credit(fielder, 'assist'), self._create_credit(defense['2B'], 'putout')]
        elif fielder['position']['abbreviation'] == '1B' and first_baseman:
            credits = [self._create_credit(first_baseman, 'putout')]
        elif first_baseman:
            credits = [self._create_credit(fielder, 'assist'), self._create_credit(first_baseman, 'putout')]

        return runs, False, rbis, credits, [], [], False, specific_event, None

    def _field_ground_out(self, batter, field, fielder, defense, catcher, first_baseman):
        """A fielded grounder played the way the field model's clock allows:
        double play, force at home or second, or the sure out at first with
        the runners moving up as far as the throw lets them."""
        play, dests = fieldsim.ground_out_play(field, self._runner_speeds(), self.outs,
                                               self._speed_of(batter), self.game_rng)
        old_bases = self.bases[:]
        pos = fielder['position']['abbreviation']
        if play == 'dp':
            runner_out = old_bases[0]
            self.outs += 2
            runs = self._apply_runner_dests(dests)
            credits_runner, credits_batter = self._get_double_play_participants(fielder, defense)
            return runs, False, 0, credits_batter, credits_batter, credits_runner, True, "Double Play", runner_out
        if play in ('force_home', 'force_second'):
            forced = old_bases[2] if play == 'force_home' else old_bases[0]
            self.outs += 1
            runs = self._apply_runner_dests(dests)
            self.bases[0] = batter['legal_name']
            if play == 'force_home':
                cover = catcher
                self._last_force = (forced, '3B', 'score')
            else:
                # The second baseman covers on a ball to the left side.
                cover = (defense.get('2B') if pos in ('SS', '3B') else defense.get('SS'))
                self._last_force = (forced, '1B', '2B')
            if pos in ('2B', 'SS') and play == 'force_second' and fieldsim.distance(field.release_point, fieldsim.SECOND_BASE) < 30:
                credits = [self._create_credit(fielder, 'putout')]
            elif cover:
                credits = [self._create_credit(fielder, 'assist'), self._create_credit(cover, 'putout')]
            else:
                credits = [self._create_credit(fielder, 'putout')]
            return runs, False, runs, credits, [], credits, False, "Forceout", forced
        self.outs += 1
        runs = self._apply_runner_dests(dests)
        if pos == '1B' and first_baseman and field.pitcher_covers:
            # 3-1: the toss to the pitcher covering first.
            credits = [self._create_credit(first_baseman, 'assist'),
                       self._create_credit(self._defense_positions()['P'], 'putout')]
        elif pos == '1B' and first_baseman:
            credits = [self._create_credit(first_baseman, 'putout')]
        elif first_baseman:
            credits = [self._create_credit(fielder, 'assist'), self._create_credit(first_baseman, 'putout')]
        else:
            credits = []
        return runs, False, runs, credits, [], [], False, "Groundout", None

    def _simulate_half_inning(self):
        self.outs, self.bases = 0, [None, None, None]
        self._runner_pitchers = {}
        self._half_pitcher_entry = {}
        self._half_pitcher_traffic, self._half_pitcher_homers = {}, {}
        self._stolen_second_this_inning = set()
        self._manage_between_innings()
        defensive_events = self._manage_defensive_substitutions()
        self._free_pass_pitcher = None
        self._half_pitcher_entry[self.team1_current_pitcher_name if self.top_of_inning else self.team2_current_pitcher_name] = (
            self.team2_score if self.top_of_inning else self.team1_score)
        is_home_team_batting = not self.top_of_inning
        batting_team_name, lineup, batter_idx_ref = (self.team1_name, self.team1_lineup, 'team1_batter_idx') if is_home_team_batting else (self.team2_name, self.team2_lineup, 'team2_batter_idx')

        if self.inning >= 10:
            last_batter_idx = (getattr(self, batter_idx_ref) - 1 + 9) % 9
            runner_name = lineup[last_batter_idx]['legal_name']
            self.bases[1] = runner_name
            self._runner_pitchers[runner_name] = self._pitching_side()[2]
            # Note: Renderer handles "Automatic runner" text

        first_batter = True
        self._half_plate_appearances = 0
        while self.outs < 3:
            if not first_batter:
                # Time between at-bats (avg ~23.6s)
                self.current_time += timedelta(seconds=self.time_rng.uniform(20.0, 27.0))
            first_batter = False

            ab_start_time = self.current_time.isoformat()

            if self.outs or any(self.bases) or self._half_plate_appearances:
                self._manage_pitching_change()
            self._half_plate_appearances += 1
            pitcher_name = self.team1_current_pitcher_name if self.top_of_inning else self.team2_current_pitcher_name
            pitcher = (self.team1_pitcher_stats if self.top_of_inning else self.team2_pitcher_stats)[pitcher_name]
            pre_events = defensive_events + self._manage_offensive_substitutions(getattr(self, batter_idx_ref), pitcher)
            defensive_events = []
            # Most tracked visits are between batters. These are catcher
            # conversations; they neither spend a coach visit nor pull a pitcher.
            if any(self.bases) and self.texture_rng.random() < MOUND_VISIT_RATE:
                pre_events.append({
                    'index': 0, 'startTime': self.current_time.isoformat(), 'endTime': self.current_time.isoformat(),
                    'isPitch': False, 'type': 'action', 'count': {'balls': 0, 'strikes': 0, 'outs': self.outs},
                    'details': {'event': 'Mound Visit', 'eventType': 'mound_visit', 'description': 'Mound Visit.',
                                'code': '', 'isStrike': False},
                })
            batter = lineup[getattr(self, batter_idx_ref)]

            # Store pre-play base state for matchup
            pre_play_bases = self.bases[:]

            self._play_field = None
            self._thrown_out = []
            self._close_plays = set()
            self._between_pitch_runners = []
            self._pitch_event_seq = len(pre_events)
            outcome, description, play_events = self._simulate_at_bat(batter, pitcher)
            pa_complete = not outcome.startswith(('Caught Stealing', 'Pickoff'))
            if pa_complete:
                self._update_batting_stat(self._batting_team_key, batter['id'], 'plateAppearances')
            old_outs = self.outs
            for runner_entry in self._between_pitch_runners:
                runner_entry['details']['playIndex'] += len(pre_events)
            play_events = pre_events + play_events
            for event_index, event in enumerate(play_events):
                event['index'] = event_index
            self._free_pass_pitcher = pitcher_name if outcome in ("Walk", "Hit By Pitch", "HBP") else None

            ab_end_time = self.current_time.isoformat()

            runs, rbis, was_error = 0, 0, False
            advances, credits = [], []
            runner_list: list[Runner] = self._between_pitch_runners[:]
            is_dp = False
            runner_out_dp = None
            credits_runner_dp = []
            credits_batter_dp = []

            # Store pre-advance base state
            old_bases = self.bases[:]

            if not pa_complete:
                pass  # Runner outs and scorer credits were recorded between pitches.
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

                if is_dp and credits_runner_dp:
                     # The batter's DP credits start with the pivot man; the ball
                     # was hit to whoever started it ("one hopper to short ... 3-6-3").
                     fielder_pos = credits_runner_dp[0]['position']['abbreviation']
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
            elif outcome in ["Single", "Double", "Triple", "Home Run", "Walk", "HBP", "Hit By Pitch"]:
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

            if pa_complete:
                self._batters_faced[pitcher_name] += 1
            if batter['legal_name'] in self.bases or outcome == 'Home Run':
                self._runner_pitchers[batter['legal_name']] = pitcher
            if outcome in ("Single", "Double", "Triple", "Home Run", "Walk", "HBP", "Hit By Pitch"):
                self._half_pitcher_traffic[pitcher_name] = self._half_pitcher_traffic.get(pitcher_name, 0) + 1
            if outcome == "Home Run":
                self._half_pitcher_homers[pitcher_name] = self._half_pitcher_homers.get(pitcher_name, 0) + 1

            play_index = len(play_events) - 1 if play_events else 0
            base_map = {0: "1B", 1: "2B", 2: "3B"}

            # --- Runner tracking logic ---

            thrown_out_text = []
            if outcome in ["Single", "Double", "Triple", "Home Run"]:
                thrown_out = {name: (origin, out_base) for name, origin, out_base in self._thrown_out}
                out_number = self.outs - len(thrown_out)
                for base_idx, runner_name in enumerate(old_bases):
                    if runner_name in thrown_out and runner_name != batter['legal_name']:
                        # Cut down trying for the extra base, as real feeds
                        # record it: a Runner Out with the fielders' credits.
                        out_number += 1
                        out_base = thrown_out[runner_name][1]
                        out_credits = self._thrown_out_credits(self._play_field, out_base)
                        runner_entry = self._build_runner_entry(
                            runner_name=runner_name, origin_base=base_map[base_idx], end_base=f"{out_base}B",
                            is_out=True, out_number=out_number, event="Runner Out", event_type="other_out",
                            movement_reason="r_thrown_out", play_index=play_index,
                            is_scoring=False, is_rbi=False, credits=out_credits)
                        if runner_entry: runner_list.append(runner_entry)
                        thrown_out_text.append((runner_name, out_base, out_credits))
                        continue
                    if runner_name:
                        origin = base_map[base_idx]
                        scored = runner_name not in self.bases
                        end = "score" if scored else base_map[self.bases.index(runner_name)]
                        runner_entry = self._build_runner_entry(
                            runner_name=runner_name, origin_base=origin, end_base=end,
                            is_out=False, out_number=None, event=outcome,
                            event_type=self._get_event_type_code(outcome),
                            movement_reason="r_adv_play", play_index=play_index,
                            is_scoring=scored, is_rbi=scored and not was_error
                        )
                        if runner_entry and runner_name in getattr(self, '_close_plays', ()):
                            # Extension fields: the throw came and he slid in.
                            runner_entry['details'].update(throw='not_in_time', slide=True)
                        if runner_entry: runner_list.append(runner_entry)

                batter_end = {"Single": "1B", "Double": "2B", "Triple": "3B", "Home Run": "score"}[outcome]
                batter_scored = outcome == "Home Run"
                if batter['legal_name'] in thrown_out:
                    # The hit stands, but his only movement ends in an out.
                    out_number += 1
                    out_base = thrown_out[batter['legal_name']][1]
                    out_credits = self._thrown_out_credits(self._play_field, out_base)
                    stretch_entry = self._build_runner_entry(
                        runner_name=batter['legal_name'], origin_base=None, end_base=f"{out_base}B",
                        is_out=True, out_number=out_number, event="Runner Out", event_type="other_out",
                        movement_reason="r_out_stretching", play_index=play_index,
                        is_scoring=False, is_rbi=False, credits=out_credits)
                    if stretch_entry:
                        stretch_entry['movement']['start'] = batter_end
                        runner_list.append(stretch_entry)
                    thrown_out_text.append((batter['legal_name'], out_base, out_credits))
                else:
                    batter_entry = self._build_runner_entry(
                        runner_name=batter['legal_name'], origin_base=None, end_base=batter_end,
                        is_out=False, out_number=None, event=outcome,
                        event_type=self._get_event_type_code(outcome),
                        movement_reason=None, play_index=play_index,
                        is_scoring=batter_scored, is_rbi=batter_scored
                    )
                    if batter_entry and outcome == 'Single':
                        bunt_event = next((event for event in play_events if event.get('isBunt')
                                           and event.get('details', {}).get('code') == 'X'), None)
                        if bunt_event:
                            fielder = self._defense_positions()[bunt_event['hitData']['location']]
                            batter_entry['credits'] = [self._create_credit(fielder, 'f_fielded_ball')]
                    if batter_entry: runner_list.append(batter_entry)
                for _, _, out_credits in thrown_out_text:
                    for credit in out_credits:
                        self._update_fielding_stat(self._pitching_team_key, credit['player']['id'],
                                                   'putOuts' if credit['credit'] == 'putout' else 'assists')
                if thrown_out_text:
                    self._update_pitching_stat(self._pitching_team_key, pitcher['id'], 'outs', len(thrown_out_text))

            elif outcome in ["Walk", "HBP", "Hit By Pitch"]:
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
                            is_scoring=scored, is_rbi=scored
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
                    # Runners from second and third move up (or score) on the DP too.
                    for base_idx, runner_name in enumerate(old_bases):
                        if not runner_name or runner_name == runner_out_dp:
                            continue
                        scored = runner_name not in self.bases
                        end = "score" if scored else base_map[self.bases.index(runner_name)]
                        if end == base_map[base_idx]:
                            continue
                        runner_entry = self._build_runner_entry(
                            runner_name=runner_name, origin_base=base_map[base_idx], end_base=end,
                            is_out=False, out_number=None, event="Grounded Into DP",
                            event_type="grounded_into_double_play", movement_reason="r_adv_play",
                            play_index=play_index, is_scoring=scored, is_rbi=False)
                        if runner_entry: runner_list.append(runner_entry)
                else:
                    # Handle runners who advanced, scored, or were out on a force
                    forced_runner = runner_out_dp if outcome == "Forceout" else None
                    if forced_runner:
                        # The forced runner is out at the force base, not "scored"
                        # because he vanished from the bases.
                        _, f_origin, f_base = self._last_force
                        runner_entry = self._build_runner_entry(
                            runner_name=forced_runner, origin_base=f_origin, end_base=f_base,
                            is_out=True, out_number=self.outs, event=outcome,
                            event_type=self._get_event_type_code(outcome),
                            movement_reason="r_force_out", play_index=play_index,
                            is_scoring=False, is_rbi=False, credits=credits_runner_dp)
                        if runner_entry:
                            runner_entry['movement']['outBase'] = f_base
                            runner_list.append(runner_entry)
                    for base_idx, runner_name in enumerate(old_bases):
                        if runner_name and runner_name != forced_runner:
                            origin = base_map[base_idx]
                            scored = runner_name not in self.bases and runner_name not in [b for b in self.bases if b]
                            advanced = runner_name in self.bases

                            if scored:
                                runner_entry = self._build_runner_entry(
                                    runner_name=runner_name, origin_base=origin, end_base="score",
                                    is_out=False, out_number=None, event=outcome,
                                    event_type=self._get_event_type_code(outcome),
                                    movement_reason="r_sac_fly" if "Sac Fly" in outcome else "r_adv_play",
                                    play_index=play_index, is_scoring=True, is_rbi=True and not was_error
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

                    # Batter's outcome (out, or reached on an error or a force play)
                    batter_reaches = was_error or bool(forced_runner)
                    batter_entry = self._build_runner_entry(
                        runner_name=batter['legal_name'], origin_base=None, end_base="1B",
                        is_out=not batter_reaches, out_number=self.outs if not batter_reaches else None,
                        event=outcome, event_type=self._get_event_type_code(outcome),
                        movement_reason=None, play_index=play_index,
                        is_scoring=False, is_rbi=False, credits=[] if forced_runner else credits
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

            # --- End runner tracking ---

            # Update scoring runners stats
            for runner_entry in runner_list:
                if runner_entry['details']['isScoringEvent']:
                     runner_id = runner_entry['details']['runner']['id']
                     self._update_batting_stat(self._batting_team_key, runner_id, 'runs')
                     runner_name = runner_entry['details']['runner']['fullName']
                     responsible_pitcher = self._responsible_pitcher(runner_name)
                     self._runs_allowed[responsible_pitcher['legal_name']] += 1
                     self._update_pitching_stat(self._pitching_team_key, responsible_pitcher['id'], 'runs')
                     # Keep the feed and box score's simplified earned-run accounting together.
                     runner_entry['details']['earned'] = not was_error
                     runner_entry['details']['teamUnearned'] = was_error
                     if not was_error:
                          self._update_pitching_stat(self._pitching_team_key, responsible_pitcher['id'], 'earnedRuns')
            self._runner_pitchers = {name: p for name, p in self._runner_pitchers.items() if name in self.bases}

            if runs > 0:
                current_inning_idx = self.inning - 1
                if is_home_team_batting:
                    self.gameday_data['liveData']['linescore']['innings'][current_inning_idx]['home']['runs'] += runs
                else:
                    self.gameday_data['liveData']['linescore']['innings'][current_inning_idx]['away']['runs'] += runs

            at_bat_index = len(self.gameday_data['liveData']['plays']['allPlays'])

            final_description = play_description_text if is_dp and play_description_text else ""
            if thrown_out_text:
                final_description = self._thrown_out_description(batter, outcome, play_events, thrown_out_text)

            play_result = PlayResult(type="atBat", event=outcome, eventType=self._get_event_type_code(outcome), description=final_description, rbi=rbis, awayScore=self.team2_score, homeScore=self.team1_score)
            play_about = PlayAbout(atBatIndex=at_bat_index, halfInning="bottom" if is_home_team_batting else "top", isTopInning=not is_home_team_batting, inning=self.inning, isScoringPlay=runs > 0, startTime=ab_start_time, endTime=ab_end_time)
            if not pa_complete:
                play_about['isComplete'] = False
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
            
            if pa_complete:
                setattr(self, batter_idx_ref, (getattr(self, batter_idx_ref) + 1) % 9)
            if self.outs >= 3: break
            if is_home_team_batting and self.team1_score > self.team2_score and self.inning >= 9:
                return

    def _record_decisions(self):
        """The pitchers of record, as a feed's liveData.decisions: the win to
        the pitcher of record when his team went ahead for good (a starter
        needs five innings), the loss to the man on the mound for that run,
        a save to a finisher who protected a lead of three or fewer for an
        inning or pitched the last three."""
        plays = self.gameday_data['liveData']['plays']['allPlays']
        if not plays or self.team1_score == self.team2_score:
            return
        home_won = self.team1_score > self.team2_score
        ahead = lambda result: (result['homeScore'] > result['awayScore']) if home_won else (
            result['awayScore'] > result['homeScore'])
        go_ahead = next(i for i in range(len(plays))
                        if all(ahead(play['result']) for play in plays[i:]))
        # The winners pitch the half-innings in which the losers bat.
        mine = [(i, play) for i, play in enumerate(plays) if play['about']['isTopInning'] == home_won]
        outs = {}
        for i, play in mine:
            before = plays[i - 1]['count']['outs'] if i and plays[i - 1]['about']['halfInning'] == play['about']['halfInning'] \
                and plays[i - 1]['about']['inning'] == play['about']['inning'] else 0
            pid = play['matchup']['pitcher']['id']
            outs[pid] = outs.get(pid, 0) + max(0, play['count']['outs'] - before)
        order = list(dict.fromkeys(play['matchup']['pitcher']['id'] for _, play in mine))
        names = {play['matchup']['pitcher']['id']: play['matchup']['pitcher']['fullName'] for play in plays}
        earlier = [play['matchup']['pitcher']['id'] for i, play in mine if i < go_ahead]
        winner = earlier[-1] if earlier else order[0]
        if winner == order[0] and outs.get(winner, 0) < 15 and len(order) > 1:
            winner = max(order[1:], key=lambda pid: outs.get(pid, 0))
        loser = plays[go_ahead]['matchup']['pitcher']['id']
        decisions = {'winner': {'id': winner, 'fullName': names[winner]},
                     'loser': {'id': loser, 'fullName': names[loser]}}
        finisher = order[-1]
        if finisher != winner:
            entered = next(i for i, play in mine if play['matchup']['pitcher']['id'] == finisher)
            before = plays[entered - 1]['result'] if entered else {'homeScore': 0, 'awayScore': 0}
            lead = abs(before['homeScore'] - before['awayScore'])
            led = entered and ahead(before)
            if led and ((lead <= 3 and outs.get(finisher, 0) >= 3) or outs.get(finisher, 0) >= 9):
                decisions['save'] = {'id': finisher, 'fullName': names[finisher]}
        self.gameday_data['liveData']['decisions'] = decisions

    def play_game(self):
        self._play_innings()
        if self.max_innings is None:
            self._record_decisions()

    def _play_innings(self):
        should_continue = lambda: (self.inning <= 9 or self.team1_score == self.team2_score) if self.max_innings is None else self.inning <= self.max_innings

        while should_continue():
            # Break between innings (or start of game logic)
            if self.inning > 1:
                # Inning break (avg ~119.6s)
                self.current_time += timedelta(seconds=self.time_rng.uniform(115.0, 125.0))

            self.top_of_inning = True
            self._simulate_half_inning()

            # Fix logic: If middle of >=9th inning and Home (Team 1) is ahead, game over.
            if self.inning >= 9 and self.team1_score > self.team2_score:
                break

            if self.max_innings and self.inning >= self.max_innings:
                break

            # Mid-inning break
            self.current_time += timedelta(seconds=self.time_rng.uniform(115.0, 125.0))

            self.top_of_inning = False
            self._simulate_half_inning()

            # Nine (or more) complete innings and somebody leads: the game is
            # over. Checked before the next inning is opened, or a visitors'
            # win in nine left a phantom 0-0 tenth in the linescore.
            if self.inning >= 9 and (self.team1_score > self.team2_score or (
                    self.max_innings is None and self.team1_score != self.team2_score)):
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
    parser.add_argument('--gameday-file', type=str, help="File to read Gameday JSON from, skipping the simulation.")
    parser.add_argument('--game-seed', type=int, help="Seed for the game's random number generator.")
    parser.add_argument('--commentary-seed', type=int, help="Seed for the commentary's random number generator.")
    args = parser.parse_args()

    # 1. Run Simulation or Load Data
    if args.gameday_file:
        with open(args.gameday_file, 'r') as f:
            gameday_data = json.load(f)
    else:
        game = BaseballSimulator(
            TEAMS["BAY_BOMBERS"],
            TEAMS["PC_PILOTS"],
            max_innings=args.max_innings,
            game_seed=args.game_seed
        )
        game.play_game()
        gameday_data = game.gameday_data

    # Persist overrides before exporting so JSON replays the same wording.
    commentary_seed = (args.commentary_seed if args.commentary_seed is not None
                       else args.game_seed)
    if commentary_seed is not None:
        gameday_data['gameData']['commentarySeed'] = commentary_seed

    # 2. Output Gameday JSON
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime): return obj.isoformat()
            return super().default(obj)

    gameday_json = json.dumps(gameday_data, indent=2, cls=DateTimeEncoder)
    if args.gameday_outfile:
        with open(args.gameday_outfile, 'w') as f:
            f.write(gameday_json)
    elif args.commentary == 'gameday':
        print(gameday_json)

    # 3. Output Commentary (PBP or Statcast)
    output_text = ""
    if args.commentary != 'gameday':
        if args.commentary == 'narrative' or args.commentary == 'combo':
            renderer = NarrativeRenderer(gameday_data, verbose=not args.terse,
                                         use_bracketed_ui=args.bracketed_ui)
            output_text = renderer.render()
        elif args.commentary == 'statcast':
            renderer = StatcastRenderer(gameday_data)
            output_text = renderer.render()

        if args.pbp_outfile:
             with open(args.pbp_outfile, 'w') as f:
                f.write(output_text)
        else:
             print(output_text)
