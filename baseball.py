import random
import uuid
import json
from datetime import datetime, timezone
from gameday import GamedayData, GameData, LiveData, Linescore, InningLinescore, Play, PlayResult, PlayAbout, PlayCount, PlayEvent, Runner, FielderCredit
from teams import TEAMS, GAME_CONTEXT

class BaseballSimulator:
    """
    Simulates a modern MLB game with realistic rules and enhanced realism.
    - DH rule is in effect.
    - Extra innings start with a "ghost runner" on second.
    - Realistic bullpen management with pitcher fatigue.
    - Positional fielding, errors, and scorer's notation for outs.
    - Varied pitch velocities and more descriptive play-by-play.
    - Feature flag for verbose/terse play-by-play output.
    """

    def __init__(self, team1_data, team2_data, verbose_phrasing=True, use_bracketed_ui=False, commentary_style='narrative'):
        self.team1_data = team1_data
        self.team2_data = team2_data
        self.team1_name = self.team1_data["name"]
        self.team2_name = self.team2_data["name"]
        self.verbose_phrasing = verbose_phrasing
        self.use_bracketed_ui = use_bracketed_ui
        self.commentary_style = commentary_style

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

        # Output buffer for narrative/statcast, gameday has its own structure
        self.output_lines = []
        self.gameday_data: GamedayData | None = None
        if self.commentary_style == 'gameday':
            self._initialize_gameday_data()

        # Game context
        self.umpires = random.sample(GAME_CONTEXT["umpires"], 4)
        self.weather = random.choice(GAME_CONTEXT["weather_conditions"])
        self.venue = self.team1_data["venue"]

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
                }
            }
        }

    def _print(self, text, end="\n"):
        """Buffer all output to print at the end."""
        if self.output_lines and end == "":
            # Append to the last line without adding a new line
            self.output_lines[-1] += text
        else:
            self.output_lines.append(text)

    def _setup_pitchers(self, team_data, team_prefix):
        all_pitchers = [p for p in team_data["players"] if p['position']['abbreviation'] == 'P']
        pitcher_stats = {p['legal_name']: p.copy() for p in all_pitchers}
        bullpen_candidates = [p['legal_name'] for p in all_pitchers if p['type'] != 'Starter']
        closers = [name for name in bullpen_candidates if pitcher_stats[name]['type'] == 'Closer']
        non_closers = [name for name in bullpen_candidates if pitcher_stats[name]['type'] != 'Closer']
        random.shuffle(non_closers)
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

    def _get_player_display_name(self, player):
        if player.get('nickname'):
            return f"{player['legal_name']} '{player['nickname']}'"
        return player['legal_name']

    def _get_hit_outcome(self, batter_stats):
        in_play = {k: v for k, v in batter_stats.items() if k not in ["Walk", "Strikeout", "HBP"]}
        return random.choices(list(in_play.keys()), weights=list(in_play.values()), k=1)[0]

    def _generate_batted_ball_data(self, hit_type):
        """Generates realistic exit velocity (EV) and launch angle (LA) for a given hit type."""
        # Occasionally return no data for realism, e.g., on errors or weird plays
        if random.random() < 0.05:
            return {}

        ev, la = 0, 0
        if hit_type == "Groundout":
            ev = round(random.uniform(70, 95), 1)
            la = round(random.uniform(-20, 5), 1)
        elif hit_type == "Flyout":
            ev = round(random.uniform(85, 105), 1)
            la = round(random.uniform(25, 50), 1)
        elif hit_type == "Single":
            # Can be a grounder or a liner
            if random.random() < 0.6: # 60% are grounders
                ev = round(random.uniform(80, 100), 1)
                la = round(random.uniform(-10, 8), 1)
            else: # 40% are liners
                ev = round(random.uniform(90, 110), 1)
                la = round(random.uniform(8, 20), 1)
        elif hit_type == "Double":
            ev = round(random.uniform(100, 115), 1)
            la = round(random.uniform(15, 35), 1)
        elif hit_type == "Triple":
            ev = round(random.uniform(100, 115), 1)
            la = round(random.uniform(18, 30), 1)
        elif hit_type == "Home Run":
            ev = round(random.uniform(100, 120), 1)
            # Correlate LA with EV. The harder it's hit, the lower the typical HR angle.
            if ev >= 118:
                # Max-effort swings that produce top-tier EV are almost never loopy.
                la = round(random.uniform(20, 28), 1)
            elif ev > 110:
                la = round(random.uniform(22, 35), 1)
            else:
                la = round(random.uniform(25, 45), 1)

        coordX = round(random.uniform(50, 200), 1)
        coordY = round(random.uniform(50, 200), 1)
        return {'ev': ev, 'la': la, 'coordX': coordX, 'coordY': coordY}

    def _describe_contact(self, outcome):
        contact_templates = {
            "Single": [
                "shoots a single through the right side",
                "drops a blooper into shallow center for a single",
                "stings a single back up the middle"
            ],
            "Double": [
                "hammers a double into the gap",
                "hooks a double down the line",
                "laces a ringing double off the wall"
            ],
            "Triple": [
                "splits the outfielders and motors for a triple",
                "drives it into the corner for a stand-up triple"
            ],
            "Home Run": [
                "launches it deep and out of here for a home run",
                "crushes a towering homer into the seats"
            ],
            "Groundout": [
                "rolls it over on the ground",
                "chops a bouncer toward the infield"
            ],
            "Flyout": [
                "lifts a routine fly ball",
                "skies it to the outfield"
            ],
            "Strikeout": [
                "goes down swinging",
                "is rung up"
            ]
        }

        if outcome in contact_templates:
            return random.choice(contact_templates[outcome])
        return "puts it in play"

    def _get_trajectory(self, outcome, la):
        """Maps a batted ball outcome and launch angle to a trajectory type."""
        if "Groundout" in outcome:
            return "ground_ball"

        # Simple LA-based heuristic for other outcomes
        if la is not None:
            if la < 10:
                return "ground_ball"
            elif 10 <= la <= 25:
                return "line_drive"
            elif la > 50:
                return "popup"

        return "fly_ball"

    def _get_batted_ball_verb(self, outcome, ev, la):
        """Selects a descriptive verb based on batted ball data."""
        verb_cats = GAME_CONTEXT['statcast_verbs'].get(outcome, {})

        # Determine category based on EV and LA thresholds
        cat = 'default'
        if outcome == "Single":
            if ev < 90 and 10 < la < 30: cat = 'bloop'
            elif ev > 100 and la < 10: cat = 'liner'
            elif ev > 95 and la < 0: cat = 'grounder'
        elif outcome == "Double":
            if ev > 100 and la < 15: cat = 'liner'
            elif ev > 100 and la >= 15: cat = 'wall'
        elif outcome == "Home Run":
            if ev > 105 and la < 22: cat = 'screamer'
            elif ev > 100 and la > 35: cat = 'moonshot'
        elif outcome == "Groundout":
            if ev < 85: cat = 'soft'
            elif ev > 100: cat = 'hard'
        elif outcome == "Flyout":
            # Popups are very high-angle, often weakly hit balls.
            if (ev < 95 and la > 50) or (ev < 90 and la > 40):
                cat = 'popup'
            elif ev > 100 and la > 30:
                cat = 'deep'

        return random.choice(verb_cats.get(cat, verb_cats.get('default', ["describes"])))

    def _format_statcast_template(self, outcome, context):
        """Formats a randomly chosen statcast template."""
        templates = GAME_CONTEXT.get('statcast_templates', {}).get(outcome)
        if not templates:
            return None

        template = random.choice(templates)

        # Ensure verb is capitalized if the template requires it
        if '{verb_capitalized}' in template:
            context['verb_capitalized'] = context.get('verb', '').capitalize()

        return template.format(**context)

    def _advance_runners_on_wp_pb(self, event_type):
        runs = 0
        advances = []
        movement_reason = event_type.lower().replace(' ', '_')

        is_home_team_batting = not self.top_of_inning
        lineup = self.team1_lineup if is_home_team_batting else self.team2_lineup

        # Simplified: runners advance one base.
        # The order of operations is important: 3B, then 2B, then 1B.
        if self.bases[2]:
            runner_name = self.bases[2]
            runner_data = next((p for p in lineup if p['legal_name'] == runner_name), None)
            if runner_data:
                advances.append({
                    'runnerId': runner_data['id'],
                    'start': '3B',
                    'end': 'Home',
                    'isOut': False,
                    'movementReason': movement_reason
                })
            runs += 1
            if self.commentary_style == 'narrative':
                self._print(f"  {runner_name} scores!")
            self.bases[2] = None

        if self.bases[1]:
            runner_name = self.bases[1]
            runner_data = next((p for p in lineup if p['legal_name'] == runner_name), None)
            if runner_data:
                advances.append({
                    'runnerId': runner_data['id'],
                    'start': '2B',
                    'end': '3B',
                    'isOut': False,
                    'movementReason': movement_reason
                })
            self.bases[2] = self.bases[1]
            self.bases[1] = None

        if self.bases[0]:
            runner_name = self.bases[0]
            runner_data = next((p for p in lineup if p['legal_name'] == runner_name), None)
            if runner_data:
                advances.append({
                    'runnerId': runner_data['id'],
                    'start': '1B',
                    'end': '2B',
                    'isOut': False,
                    'movementReason': movement_reason
                })
            self.bases[1] = self.bases[0]
            self.bases[0] = None

        if self.commentary_style == 'narrative' and advances:
            self._print(f"  {event_type}! Runners advance.")

        # Sort advances by base for consistent output
        base_order = {'1B': 0, '2B': 1, '3B': 2}
        advances.sort(key=lambda x: base_order.get(x['start'], -1))

        return {'runs': runs, 'advances': advances}

    def _simulate_base_running_action(self, pitcher, at_bat_index):
        """Simulates non-pitch actions like steals and pickoffs."""
        events = []
        # Less action with 2 outs.
        if self.outs >= 2 or not any(self.bases):
            return events

        is_home_team_batting = not self.top_of_inning
        batting_lineup = self.team1_lineup if is_home_team_batting else self.team2_lineup
        defensive_team_prefix = 'team1' if self.top_of_inning else 'team2'

        # Probabilities for actions
        STEAL_ATTEMPT_PROB = 0.02
        STEAL_SUCCESS_RATE = 0.75
        PICKOFF_ATTEMPT_PROB = 0.015
        PICKOFF_SUCCESS_RATE = 0.05
        BALK_PROB = 0.001

        # Balk check
        if any(self.bases) and random.random() < BALK_PROB:
            balk_runners = []
            new_bases = self.bases[:]
            # Runners advance one base. Order matters.
            if self.bases[2]:
                runner_name = self.bases[2]
                runner_data = next((p for p in batting_lineup if p['legal_name'] == runner_name), None)
                if runner_data:
                    balk_runners.append({
                        'runnerId': runner_data['id'], 'start': '3B', 'end': 'Home', 'isOut': False, 'movementReason': 'balk'
                    })
                if is_home_team_batting: self.team1_score += 1
                else: self.team2_score += 1
            if self.bases[1]:
                runner_name = self.bases[1]
                runner_data = next((p for p in batting_lineup if p['legal_name'] == runner_name), None)
                if runner_data:
                    balk_runners.append({
                        'runnerId': runner_data['id'], 'start': '2B', 'end': '3B', 'isOut': False, 'movementReason': 'balk'
                    })
                new_bases[2] = self.bases[1]
            if self.bases[0]:
                runner_name = self.bases[0]
                runner_data = next((p for p in batting_lineup if p['legal_name'] == runner_name), None)
                if runner_data:
                    balk_runners.append({
                        'runnerId': runner_data['id'], 'start': '1B', 'end': '2B', 'isOut': False, 'movementReason': 'balk'
                    })
                new_bases[1] = self.bases[0]
                new_bases[0] = None

            self.bases = new_bases
            base_order = {'1B': 0, '2B': 1, '3B': 2}
            balk_runners.sort(key=lambda x: base_order.get(x['start'], -1), reverse=True)

            event = {
                "playId": str(uuid.uuid4()), "atBatIndex": at_bat_index, "isPitch": False,
                "type": {"code": "A", "description": "Action"},
                "details": {"code": "BK", "description": "Balk", "eventType": "balk"},
                "runners": balk_runners
            }
            events.append(event)

            for i, event in enumerate(events):
                event['index'] = len(self.play_events) + i
            return events

        # Steal of 3rd
        if self.bases[1] and not self.bases[2] and random.random() < STEAL_ATTEMPT_PROB:
            runner_name = self.bases[1]
            runner_data = next((p for p in batting_lineup if p['legal_name'] == runner_name), None)
            catcher = getattr(self, f"{defensive_team_prefix}_catcher")
            third_baseman = getattr(self, f"{defensive_team_prefix}_defense").get('3B')

            # Ensure players exist before creating event
            if not all([runner_data, catcher, third_baseman]): return []

            if random.random() < STEAL_SUCCESS_RATE * 0.8: # Harder to steal 3rd
                self.bases[2] = self.bases[1]
                self.bases[1] = None
                event = {
                    "playId": str(uuid.uuid4()), "atBatIndex": at_bat_index, "isPitch": False,
                    "type": {"code": "A", "description": "Action"},
                    "details": {"code": "SB", "description": "Stolen Base 3B", "eventType": "stolen_base"},
                    "runners": [{
                        "runnerId": runner_data['id'], "start": "2B", "end": "3B", "isOut": False,
                        "movementReason": "stolen_base", "responsiblePitcherId": pitcher['id'], "responsibleCatcherId": catcher['id']
                    }]
                }
                events.append(event)
            else:
                self.outs += 1
                self.bases[1] = None
                event = {
                    "playId": str(uuid.uuid4()), "atBatIndex": at_bat_index, "isPitch": False,
                    "type": {"code": "A", "description": "Action"},
                    "details": {"code": "CS", "description": "Caught Stealing 3B", "eventType": "caught_stealing"},
                    "runners": [{
                        "runnerId": runner_data['id'], "start": "2B", "end": "3B", "isOut": True, "outBase": "3B",
                        "creditedFielders": [
                            {"playerId": catcher['id'], "position": "C", "credit": "assist"},
                            {"playerId": third_baseman['id'], "position": "3B", "credit": "putout"}
                        ],
                        "movementReason": "caught_stealing"
                    }]
                }
                events.append(event)

            for i, event in enumerate(events):
                event['index'] = len(self.play_events) + i
            return events

        # Action from 1B: Steal or Pickoff.
        if self.bases[0] and not self.bases[1]: # Runner on 1st, 2nd is open
            action_roll = random.random()
            if action_roll < STEAL_ATTEMPT_PROB: # Attempted Steal of 2nd
                runner_name = self.bases[0]
                runner_data = next((p for p in batting_lineup if p['legal_name'] == runner_name), None)
                catcher = getattr(self, f"{defensive_team_prefix}_catcher")
                second_baseman = getattr(self, f"{defensive_team_prefix}_defense").get('2B')
                shortstop = getattr(self, f"{defensive_team_prefix}_defense").get('SS')
                covering_player = random.choice([p for p in [second_baseman, shortstop] if p])

                if not all([runner_data, catcher, covering_player]): return []

                if random.random() < STEAL_SUCCESS_RATE: # Successful Steal
                    self.bases[1] = self.bases[0]
                    self.bases[0] = None
                    event = {
                        "playId": str(uuid.uuid4()), "atBatIndex": at_bat_index, "isPitch": False,
                        "type": {"code": "A", "description": "Action"},
                        "details": {"code": "SB", "description": "Stolen Base 2B", "eventType": "stolen_base"},
                        "runners": [{
                            "runnerId": runner_data['id'], "start": "1B", "end": "2B", "isOut": False,
                            "movementReason": "stolen_base", "responsiblePitcherId": pitcher['id'], "responsibleCatcherId": catcher['id']
                        }]
                    }
                    events.append(event)
                else: # Caught Stealing
                    self.outs += 1
                    self.bases[0] = None
                    event = {
                        "playId": str(uuid.uuid4()), "atBatIndex": at_bat_index, "isPitch": False,
                        "type": {"code": "A", "description": "Action"},
                        "details": {"code": "CS", "description": "Caught Stealing 2B", "eventType": "caught_stealing"},
                        "runners": [{
                            "runnerId": runner_data['id'], "start": "1B", "end": "2B", "isOut": True, "outBase": "2B",
                            "creditedFielders": [
                                {"playerId": catcher['id'], "position": "C", "credit": "assist"},
                                {"playerId": covering_player['id'], "position": covering_player['position'], "credit": "putout"}
                            ],
                            "movementReason": "caught_stealing"
                        }]
                    }
                    events.append(event)

            elif action_roll < STEAL_ATTEMPT_PROB + PICKOFF_ATTEMPT_PROB: # Attempted Pickoff at 1st
                runner_name = self.bases[0]
                runner_data = next((p for p in batting_lineup if p['legal_name'] == runner_name), None)
                first_baseman = getattr(self, f"{defensive_team_prefix}_defense").get('1B')

                if not all([runner_data, first_baseman]): return []

                if random.random() < PICKOFF_SUCCESS_RATE: # Successful Pickoff
                    self.outs += 1
                    self.bases[0] = None
                    event = {
                        "playId": str(uuid.uuid4()), "atBatIndex": at_bat_index, "isPitch": False,
                        "type": {"code": "A", "description": "Action"},
                        "details": {"code": "PO", "description": "Pickoff at 1B", "eventType": "pickoff"},
                        "runners": [{
                            "runnerId": runner_data['id'], "start": "1B", "end": "1B", "isOut": True, "outBase": "1B",
                            "creditedFielders": [
                                {"playerId": pitcher['id'], "position": "P", "credit": "pickoff"},
                                {"playerId": first_baseman['id'], "position": "1B", "credit": "putout"}
                            ],
                            "pickedOff": True
                        }]
                    }
                    events.append(event)

        # Add index to all generated events
        for i, event in enumerate(events):
            event['index'] = len(self.play_events) + len(events) - 1 + i

        return events

    def _simulate_at_bat(self, batter, pitcher):
        balls, strikes = 0, 0
        pitch_number = 0
        play_events: list[PlayEvent] = []
        
        batter_display_name = self._get_player_display_name(batter)
        if self.commentary_style != 'gameday':
            self._print(f"Now batting: {batter_display_name} ({batter.get('position', {}).get('abbreviation', 'P')}, {batter['handedness']})")

        if self.commentary_style == 'narrative':
            if self.verbose_phrasing and random.random() < 0.03: self._print("  Brief delay as the infield huddles on the mound.")
            if self.verbose_phrasing and self.bases[0] and random.random() < 0.05: self._print(f"  Quick throw to first and {self.bases[0]} dives back safely.")
            if self.verbose_phrasing and random.random() < 0.04:
                self._print(f"  Defensive alignment: {random.choice(GAME_CONTEXT.get('defensive_calls', ['Standard defense']))}")

        if random.random() < batter.get('stats', {}).get('HBP', 0):
            return "HBP", None, play_events

        batter_stats = batter['stats']
        batter_walk_rate = batter_stats.get('Walk', 0.09)
        batter_k_rate = batter_stats.get('Strikeout', 0.17)
        discipline_factor = max(0.1, batter_walk_rate / 0.08)
        swing_at_ball_prob = 0.30 / discipline_factor
        contact_prob = 0.75 / max(0.1, batter_k_rate / 0.17)

        while balls < 4 and strikes < 3:
            pitch_number += 1
            self.pitch_counts[pitcher['legal_name']] += 1
            
            pitch_selection = random.choices(list(pitcher['pitch_arsenal'].keys()), weights=[v['prob'] for v in pitcher['pitch_arsenal'].values()], k=1)[0]
            pitch_details_team = pitcher['pitch_arsenal'][pitch_selection]
            pitch_velo = round(random.uniform(*pitch_details_team['velo_range']), 1)
            pitch_spin = random.randint(*pitch_details_team.get('spin_range', (2000, 2500))) if random.random() > 0.08 else None
            
            fatigue_penalty = (max(0, self.pitch_counts[pitcher['legal_name']] - pitcher['stamina']) / 15) * 0.1
            is_strike_loc = random.random() < (pitcher['control'] - fatigue_penalty)
            
            swing = random.random() < (0.85 if is_strike_loc else swing_at_ball_prob)
            contact = random.random() < contact_prob
            is_in_play = swing and contact and (strikes < 2 or random.random() > 0.5)

            pre_pitch_balls, pre_pitch_strikes = balls, strikes
            pitch_outcome_text = ""
            event_details: PlayEvent['details'] = {}

            if is_in_play:
                hit_result = self._get_hit_outcome(batter['stats'])
                pitch_outcome_text = "in play"
                event_details = {'code': 'X', 'description': f'In play, {hit_result}', 'isStrike': True}
            elif swing and not contact:
                strikes += 1; pitch_outcome_text = "swinging strike"
                event_details = {'code': 'S', 'description': 'Swinging Strike', 'isStrike': True}
            elif swing and contact: # Foul
                strikes += 1; pitch_outcome_text = "foul"
                event_details = {'code': 'D', 'description': 'Foul', 'isStrike': True}
            elif not swing and is_strike_loc:
                strikes += 1; pitch_outcome_text = "called strike"
                event_details = {'code': 'C', 'description': 'Called Strike', 'isStrike': True}
            else: # Ball
                balls += 1; pitch_outcome_text = "ball"
                event_details = {'code': 'B', 'description': 'Ball', 'isStrike': False}

            if self.commentary_style == 'gameday':
                event_details['type'] = {'code': GAME_CONTEXT['PITCH_TYPE_MAP'].get(pitch_selection, 'UN'), 'description': pitch_selection.capitalize()}
                pitch_data: PitchData = {'startSpeed': pitch_velo}
                if pitch_spin: pitch_data['breaks'] = {'spinRate': pitch_spin}
                play_events.append({'index': len(play_events), 'details': event_details, 'count': {'balls': pre_pitch_balls, 'strikes': pre_pitch_strikes}, 'pitchData': pitch_data})

            if is_in_play:
                description = None
                batted_ball_data = self._generate_batted_ball_data(hit_result)
                if self.commentary_style == 'statcast':
                    description = {**batted_ball_data, 'pitch_velo': pitch_velo, 'pitch_spin': pitch_spin}
                elif self.commentary_style == 'narrative':
                    pitch_desc = f"Pitch: {pitch_selection} ({pitch_velo} mph)."
                    contact_summary = self._describe_contact(hit_result)
                    description = f"  {pitch_desc} {contact_summary[0].upper() + contact_summary[1:]}{'!' if hit_result in ['Single', 'Double', 'Triple', 'Home Run'] else '.'}"

                if self.commentary_style == 'gameday' and 'ev' in batted_ball_data:
                    play_events[-1]['hitData'] = {
                        'launchSpeed': batted_ball_data['ev'], 'launchAngle': batted_ball_data['la'],
                        'trajectory': self._get_trajectory(hit_result, batted_ball_data['la'])
                    }
                return hit_result, description, play_events

            if self.commentary_style == 'narrative':
                self._print(f"  {pitch_outcome_text.capitalize()}. Count: {balls}-{strikes}")
            elif self.commentary_style == 'statcast':
                self._print(f"  {pitch_outcome_text.capitalize()}: {pitch_velo} mph {pitch_selection}")

        if balls == 4:
            return "Walk", None, play_events

        k_type = "looking" if pitch_outcome_text == "called strike" else "swinging"
        description = {'k_type': k_type} if self.commentary_style != 'narrative' else None
        return "Strikeout", description, play_events

    def _advance_runners(self, hit_type, batter, was_error=False, include_batter_advance=False):
        runs = 0
        rbis = 0
        advances = []
        batter_name = batter['legal_name']
        batter_gets_rbi = not was_error

        if hit_type in ["Walk", "HBP"]:
            new_bases = self.bases[:]
            if new_bases[0]:
                if new_bases[1]:
                    if new_bases[2]:
                        runs += 1; rbis += 1; advances.append(f"{new_bases[2]} scores")
                    advances.append(f"{new_bases[1]} to 3B")
                    new_bases[2] = new_bases[1]
                advances.append(f"{new_bases[0]} to 2B")
                new_bases[1] = new_bases[0]
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
        if self.use_bracketed_ui:
            base1 = '1B' if self.bases[0] is not None else '_'
            base2 = '2B' if self.bases[1] is not None else '_'
            base3 = '3B' if self.bases[2] is not None else '_'
            return f"[{base1}]-[{base2}]-[{base3}]"
        else:
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
        team_name = self.team1_name if is_home_team_pitching else self.team2_name

        current_pitcher = pitcher_stats[current_pitcher_name]
        fatigue_factor = max(0, self.pitch_counts[current_pitcher_name] - current_pitcher['stamina'])

        if fatigue_factor > 0 and available_bullpen:
            # Simplified reliever selection logic
            next_pitcher_name = available_bullpen[0]

            if is_home_team_pitching:
                if self.team1_current_pitcher_name != next_pitcher_name:
                    self._print(f"\n--- Pitching Change for {team_name}: {next_pitcher_name} replaces {self.team1_current_pitcher_name} ---\n")
                    self.team1_current_pitcher_name = next_pitcher_name
                    self.team1_available_bullpen.remove(next_pitcher_name)
            else:
                if self.team2_current_pitcher_name != next_pitcher_name:
                    self._print(f"\n--- Pitching Change for {team_name}: {next_pitcher_name} replaces {self.team2_current_pitcher_name} ---\n")
                    self.team2_current_pitcher_name = next_pitcher_name
                    self.team2_available_bullpen.remove(next_pitcher_name)

    def _handle_batted_ball_out(self, out_type, batter, statcast_data=None):
        defensive_team_prefix = 'team1' if self.top_of_inning else 'team2'
        infielders = getattr(self, f"{defensive_team_prefix}_infielders")
        outfielders = getattr(self, f"{defensive_team_prefix}_outfielders")
        pitcher = getattr(self, f"{defensive_team_prefix}_pitcher_stats")[getattr(self, f"{defensive_team_prefix}_current_pitcher_name")]
        catcher = getattr(self, f"{defensive_team_prefix}_catcher")
        first_baseman = getattr(self, f"{defensive_team_prefix}_defense").get('1B')

        fielder = None
        is_error = False
        credits: list[FielderCredit] = []
        
        if out_type == 'Groundout':
            # Simplified fielder selection for groundouts
            grounder_candidates = [(p, 6) for p in infielders] + [(pitcher, 1)] + ([(catcher, 0.25)] if catcher else [])
            fielder = random.choices([c[0] for c in grounder_candidates], weights=[c[1] for c in grounder_candidates], k=1)[0]
            if fielder['position'] == 'C' and statcast_data and 'ev' in statcast_data:
                statcast_data['ev'], statcast_data['la'] = round(random.uniform(50, 70), 1), round(random.uniform(-45, -20), 1)
        elif out_type == 'Flyout':
            fielder = random.choices(outfielders + infielders, weights=[6] * len(outfielders) + [1] * len(infielders), k=1)[0]

        if fielder:
            team_prowess = self.team1_data['fielding_prowess'] if self.top_of_inning else self.team2_data['fielding_prowess']
            if random.random() > fielder['fielding_ability'] * team_prowess:
                is_error = True

        pos_map = {'P': 1, 'C': 2, '1B': 3, '2B': 4, '3B': 5, 'SS': 6, 'LF': 7, 'CF': 8, 'RF': 9}
        if is_error:
            fielder_pos_abbr = fielder['position']['abbreviation']
            notation = f"E{pos_map.get(fielder_pos_abbr, '')}"
            if self.commentary_style == 'statcast':
                return f"{notation} on a {'ground ball' if out_type == 'Groundout' else 'fly ball'} to {fielder_pos_abbr};", 0, True, 0, []
            elif self.commentary_style == 'narrative':
                self._print(f"  An error by {fielder_pos_abbr} {fielder['legal_name']} allows the batter to reach base.")
            return f"Reached on Error ({notation})", 0, True, 0, []

        runs, rbis = 0, 0
        notation = ""
        if out_type == 'Flyout':
            fielder_pos = fielder['position']['abbreviation']
            out_desc = "pop out" if fielder['position']['abbreviation'] in ['P', 'C', '1B', '2B', '3B', 'SS'] else "flyout"
            notation = f"{'P' if out_desc == 'pop out' else 'F'}{fielder['position']['code']}"
            credits.append({'player': {'id': fielder['id']}, 'position': fielder['position'], 'credit': 'putout'})

            if self.outs < 2 and self.bases[2] and fielder_pos in ['LF', 'CF', 'RF'] and random.random() > 0.4:
                self.outs += 1
                runner_on_third = self.bases[2]
                runs, rbis = 1, 1
                self.bases[2] = None
                if self.commentary_style == 'statcast':
                    return f"Sac fly to {fielder_pos}. {runner_on_third} scores.", runs, False, rbis, credits
                elif self.commentary_style == 'narrative':
                    self._print(f"  Sacrifice fly to {fielder_pos}, {runner_on_third} scores!")
                    notation += " (SF)"
            else:
                self.outs += 1

            if self.commentary_style == 'statcast':
                verb = self._get_batted_ball_verb('Flyout', statcast_data['ev'], statcast_data['la']) if statcast_data and 'ev' in statcast_data else "flies out"
                result_line = self._format_statcast_template('Flyout', {'batter_name': batter['legal_name'], 'verb': verb, 'fielder_pos': fielder_pos, 'fielder_name': fielder['legal_name']})
                return result_line, runs, False, rbis, credits
            return f"{out_desc.capitalize()} to {fielder_pos} ({notation})", runs, False, rbis, credits

        if out_type == 'Groundout':
            if self.outs < 2 and self.bases[0] and random.random() < self.team1_data['double_play_rate']:
                self.outs += 2
                runner_on_first, self.bases[0] = self.bases[0], None
                if self.bases[1]: self.bases[2], self.bases[1] = self.bases[1], None

                ss = getattr(self, f"{defensive_team_prefix}_defense").get('SS')
                sb = getattr(self, f"{defensive_team_prefix}_defense").get('2B')

                # Simplified DP routes for now
                if fielder['position']['abbreviation'] == 'SS' and sb and first_baseman:
                    notation, credits = "6-4-3", [{'player': {'id': fielder['id']}, 'credit': 'assist'}, {'player': {'id': sb['id']}, 'credit': 'assist'}, {'player': {'id': first_baseman['id']}, 'credit': 'putout'}]
                elif fielder['position']['abbreviation'] == '3B' and sb and first_baseman:
                     notation, credits = "5-4-3", [{'player': {'id': fielder['id']}, 'credit': 'assist'}, {'player': {'id': sb['id']}, 'credit': 'assist'}, {'player': {'id': first_baseman['id']}, 'credit': 'putout'}]
                else: # Default unassisted by fielder
                    notation, credits = f"{fielder['position']['code']}U", [{'player': {'id': fielder['id']}, 'credit': 'putout'}, {'player': {'id': fielder['id']}, 'credit': 'putout'}]

                if self.commentary_style == 'statcast':
                    return f"Grounds into a {notation} double play.", 0, False, 0, credits
                return f"Groundout, Double Play ({notation})", 0, False, 0, credits

            self.outs += 1
            if self.outs < 3:
                if self.bases[2]: runs, rbis, self.bases[2] = 1, 1, None
                if self.bases[1]: self.bases[2], self.bases[1] = self.bases[1], None
                if self.bases[0]: self.bases[1], self.bases[0] = self.bases[0], None
            else:
                runs, rbis = 0, 0

            play_label = f"Groundout to {fielder['position']['abbreviation']}"
            if fielder['position']['abbreviation'] == '1B' and first_baseman:
                notation, credits = "3U", [{'player': {'id': first_baseman['id']}, 'credit': 'putout'}]
            elif first_baseman:
                notation = f"{fielder['position']['code']}-3"
                credits = [{'player': {'id': fielder['id']}, 'credit': 'assist'}, {'player': {'id': first_baseman['id']}, 'credit': 'putout'}]

            if self.commentary_style == 'statcast':
                verb = self._get_batted_ball_verb('Groundout', statcast_data['ev'], statcast_data['la']) if statcast_data and 'ev' in statcast_data else "grounds out"
                result_line = self._format_statcast_template('Groundout', {'batter_name': batter['legal_name'], 'verb': verb, 'fielder_pos': fielder['position']['abbreviation'], 'fielder_name': fielder['legal_name']})
                return result_line, runs, False, rbis, credits
            return f"{play_label} ({notation})", runs, False, rbis, credits

        return "Error", 0, True, 0, []

    def _simulate_half_inning(self):
        self.outs, self.bases = 0, [None, None, None]
        is_home_team_batting = not self.top_of_inning
        batting_team_name, lineup, batter_idx_ref = (self.team1_name, self.team1_lineup, 'team1_batter_idx') if is_home_team_batting else (self.team2_name, self.team2_lineup, 'team2_batter_idx')

        if self.inning >= 10:
            last_batter_idx = (getattr(self, batter_idx_ref) - 1 + 9) % 9
            runner_name = lineup[last_batter_idx]['legal_name']
            self.bases[1] = runner_name
            if self.verbose_phrasing and self.commentary_style == 'narrative':
                self._print(f"Automatic runner on second: {runner_name} jogs out to take his lead.")

        if self.commentary_style != 'gameday':
            inning_half = "Bottom" if is_home_team_batting else "Top"
            self._print("-" * 50)
            self._print(f"{inning_half} of Inning {self.inning} | {batting_team_name} batting")

        while self.outs < 3:
            self._manage_pitching_change()
            pitcher_name = self.team1_current_pitcher_name if self.top_of_inning else self.team2_current_pitcher_name
            pitcher_stats_dict = self.team1_pitcher_stats if self.top_of_inning else self.team2_pitcher_stats
            pitcher = pitcher_stats_dict[pitcher_name]

            batter_idx = getattr(self, batter_idx_ref)
            batter = lineup[batter_idx]

            outcome, description, play_events = self._simulate_at_bat(batter, pitcher)

            runs, rbis, was_error = 0, 0, False
            advances, credits = [], []

            display_outcome = outcome
            if outcome in ["Groundout", "Flyout"]:
                display_outcome, new_runs, was_error, new_rbis, credits_from_out = self._handle_batted_ball_out(outcome, batter, description)
                runs += new_runs; rbis += new_rbis
                credits.extend(credits_from_out)
                if was_error:
                    adv_info = self._advance_runners("Single", batter, was_error=True, include_batter_advance=True)
                    runs += adv_info['runs']; advances.extend(adv_info['advances'])
            elif outcome == "Strikeout":
                self.outs += 1
                if self.commentary_style == 'statcast' and description and 'k_type' in description:
                    display_outcome = f"{batter['legal_name']} {random.choice(GAME_CONTEXT['statcast_verbs']['Strikeout'][description['k_type']])}."
            elif outcome in ["Single", "Double", "Triple", "Home Run", "Walk", "HBP"]:
                adv_info = self._advance_runners(outcome, batter)
                runs += adv_info['runs']; rbis += adv_info['rbis']; advances.extend(adv_info['advances'])

            if is_home_team_batting: self.team1_score += runs
            else: self.team2_score += runs

            if self.commentary_style == 'gameday':
                at_bat_index = len(self.gameday_data['liveData']['plays']['allPlays'])
                play_result = PlayResult(type="atBat", event=outcome, eventType=outcome.lower(), description="", rbi=rbis, awayScore=self.team2_score, homeScore=self.team1_score)
                play_about = PlayAbout(atBatIndex=at_bat_index, halfInning="bottom" if is_home_team_batting else "top", isTopInning=not is_home_team_batting, inning=self.inning, isScoringPlay=runs > 0)
                final_count = PlayCount(balls=0, strikes=0, outs=self.outs) # This is the post-play out count

                # Create runner objects for gameday
                runner_list: list[Runner] = []
                # This is a simplified version; a real implementation would track runner movements more granularly.
                if credits:
                    runner_list.append({"movement": {}, "details": {}, "credits": credits})

                play_data: Play = {"result": play_result, "about": play_about, "count": final_count, "playEvents": play_events, "runners": runner_list}
                self.gameday_data['liveData']['plays']['allPlays'].append(play_data)

                # Update linescore
                ls = self.gameday_data['liveData']['linescore']
                ls['outs'] = self.outs
                ls['teams']['home']['runs'] = self.team1_score
                ls['teams']['away']['runs'] = self.team2_score
                if outcome not in ["Walk", "Strikeout", "HBP", "Groundout", "Flyout"]:
                    if is_home_team_batting: ls['teams']['home']['hits'] += 1
                    else: ls['teams']['away']['hits'] += 1
                if was_error:
                    if is_home_team_batting: ls['teams']['away']['errors'] += 1
                    else: ls['teams']['home']['errors'] += 1

            elif self.commentary_style == 'statcast':
                self._print_statcast_result(display_outcome, outcome, description, was_error, advances, rbis, batter)
            else: # narrative
                self._print_narrative_result(display_outcome, outcome, description)

            if self.commentary_style != 'gameday':
                score_str = f"{self.team1_name}: {self.team1_score}, {self.team2_name}: {self.team2_score}"
                if self.outs < 3:
                    self._print(f" | Outs: {self.outs} | Bases: {self._get_bases_str()} | Score: {score_str}\n")
                else:
                    self._print(f" | Outs: {self.outs} | Score: {score_str}\n")
            
            setattr(self, batter_idx_ref, (batter_idx + 1) % 9)
            if self.outs >= 3: break
            if is_home_team_batting and self.team1_score > self.team2_score and self.inning >= 9:
                return

    def _print_narrative_result(self, display_outcome, outcome, description):
        if isinstance(description, str): self._print(description)
        result_line = display_outcome
        if outcome in ["Walk", "Strikeout"]: result_line = outcome
        elif outcome == "HBP": result_line = "Hit by Pitch"

        if outcome not in ["Single", "Double", "Triple", "Home Run"]:
            self._print(f"Result: {result_line.ljust(30)}", end="")
        else:
            self._print(f"Result: {outcome.ljust(30)}", end="")

    def _print_statcast_result(self, display_outcome, outcome, description, was_error, advances, rbis, batter):
        pitch_info = description
        batted_ball_str = ""
        if outcome not in ["Strikeout", "Walk", "HBP"] and pitch_info and 'ev' in pitch_info and 'la' in pitch_info:
            batted_ball_str = f" (EV: {pitch_info['ev']} mph, LA: {pitch_info['la']}°)"

        result_line = display_outcome
        if was_error:
            result_line = self._format_statcast_template('Error', {'display_outcome': display_outcome, 'adv_str': "; ".join(adv for adv in advances), 'batter_name': batter['legal_name']})
        elif outcome == 'Strikeout' and description and 'k_type' in description:
            result_line = f"{batter['legal_name']} {random.choice(GAME_CONTEXT['statcast_verbs']['Strikeout'][description['k_type']])}."
        elif outcome in GAME_CONTEXT['statcast_verbs'] and outcome not in ['Flyout', 'Groundout']:
            verb = self._get_batted_ball_verb(outcome, pitch_info['ev'], pitch_info['la']) if pitch_info and 'ev' in pitch_info else random.choice(GAME_CONTEXT['statcast_verbs'][outcome]['default'])
            result_line = self._format_statcast_template(outcome, {'batter_name': batter['legal_name'], 'verb': verb, 'runs': rbis}) or f"{batter['legal_name']} {verb}."
        elif outcome == "HBP":
            result_line = "Hit by Pitch."

        if batted_ball_str: result_line += batted_ball_str
        if rbis > 0 and not was_error: result_line += f" {batter['legal_name']} drives in {rbis}."
        if not was_error and advances:
            if adv_str := "; ".join(advances): result_line += f" ({adv_str})"
        self._print(f"Result: {result_line}")

    def _print_pre_game_summary(self):
        self._print("=" * 20 + " GAME START " + "=" * 20)
        self._print(f"{self.team2_name} vs. {self.team1_name}")
        self._print(f"Venue: {self.venue}")
        self._print(f"Weather: {self.weather}")
        self._print(f"Umpires: HP: {self.umpires[0]}, 1B: {self.umpires[1]}, 2B: {self.umpires[2]}, 3B: {self.umpires[3]}")
        self._print("-" * 50)

    def play_game(self):
        if self.commentary_style != 'gameday':
            self._print_pre_game_summary()

        while self.inning <= 9 or self.team1_score == self.team2_score:
            self.top_of_inning = True
            self._simulate_half_inning()

            if self.inning >= 9 and not self.top_of_inning and self.team1_score > self.team2_score:
                break

            self.top_of_inning = False
            self._simulate_half_inning()

            if self.inning >= 9 and not self.top_of_inning and self.team1_score > self.team2_score:
                break

            self.inning += 1
            if self.commentary_style == 'gameday':
                self.gameday_data['liveData']['linescore']['currentInning'] = self.inning
                self.gameday_data['liveData']['linescore']['innings'].append({'num': self.inning, 'home': {'runs': 0}, 'away': {'runs': 0}})

        if self.commentary_style != 'gameday':
            self._print("=" * 20 + " GAME OVER " + "=" * 20)
            self._print(f"\nFinal Score: {self.team1_name} {self.team1_score} - {self.team2_name} {self.team2_score}")
            winner = self.team1_name if self.team1_score > self.team2_score else self.team2_name
            self._print(f"\n{winner} win!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="A realistic baseball simulator.")
    parser.add_argument('--terse', action='store_true', help="Use terse, data-driven phrasing for play-by-play.")
    parser.add_argument('--bracketed-ui', action='store_true', help="Use the classic bracketed UI for base runners.")
    parser.add_argument('--commentary', type=str, choices=['narrative', 'statcast', 'gameday'], default='narrative', help="Choose the commentary style.")
    args = parser.parse_args()

    home_team_key = "BAY_BOMBERS"
    away_team_key = "PC_PILOTS"
    game = BaseballSimulator(
        TEAMS[home_team_key],
        TEAMS[away_team_key],
        verbose_phrasing=not args.terse,
        use_bracketed_ui=args.bracketed_ui,
        commentary_style=args.commentary
    )

    game.play_game()

    if args.commentary == 'gameday':
        # Custom JSON encoder to handle datetime objects
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return super().default(obj)
        print(json.dumps(game.gameday_data, indent=2, cls=DateTimeEncoder))
    else:
        for line in game.output_lines:
            print(line)