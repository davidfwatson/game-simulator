import random

from gameday import GamedayData, Play, PlayEvent, PlayResult, PlayAbout, PlayCount, Runner
from teams import TEAMS

# Minimal context needed for simulation logic
SIMULATION_CONTEXT = {
    "PITCH_TYPE_MAP": {
        "four-seam fastball": "FF",
        "sinker": "SI",
        "cutter": "FC",
        "slider": "SL",
        "changeup": "CH",
        "curveball": "CU",
        "knuckle curve": "KC"
    },
    "hit_directions": {
        "P": "back to the mound",
        "C": "in front of the plate",
        "1B": "to first",
        "2B": "to second",
        "3B": "to third",
        "SS": "to short",
        "LF": "to left",
        "CF": "to center",
        "RF": "to right"
    }
}


class BaseballSimulator:
    """
    Simulates a modern MLB game with realistic rules and enhanced realism,
    outputting a canonical Gameday JSON data structure.
    """

    def __init__(self, team1_data, team2_data, max_innings=None, game_seed=None, commentary_seed=None):
        self.team1_data = team1_data
        self.team2_data = team2_data
        self.team1_name = self.team1_data["name"]
        self.team2_name = self.team2_data["name"]
        self.max_innings = max_innings
        self.game_rng = random.Random(game_seed)
        # commentary_rng is kept for deterministic elements that are not strictly core-game logic
        # but are part of the descriptive output (e.g., hit locations).
        self.commentary_rng = random.Random(commentary_seed)

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
        self.outs, self.bases = 0, [None, None, None]  # Runners on base by name

        # Gameday data structure
        self.gameday_data: GamedayData | None = None
        self._pitch_event_seq = 0
        self._initialize_gameday_data()

    def _initialize_gameday_data(self):
        """Sets up the initial structure for Gameday JSON output."""
        self.gameday_data = {
            "gameData": {
                "teams": {
                    "away": {
                        "id": self.team2_data["id"], "name": self.team2_data["name"],
                        "abbreviation": self.team2_data["abbreviation"], "teamName": self.team2_data["teamName"]
                    },
                    "home": {
                        "id": self.team1_data["id"], "name": self.team1_data["name"],
                        "abbreviation": self.team1_data["abbreviation"], "teamName": self.team1_data["teamName"]
                    }
                }
            },
            "liveData": {
                "plays": {"allPlays": []},
                "linescore": {
                    "currentInning": 1, "isTopInning": True, "inningState": "Top",
                    "outs": 0, "balls": 0, "strikes": 0,
                    "teams": {"home": {"runs": 0, "hits": 0, "errors": 0}, "away": {"runs": 0, "hits": 0, "errors": 0}},
                    "innings": [{"num": 1, "home": {"runs": 0}, "away": {"runs": 0}}]
                }
            }
        }

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
        fatigue_penalty = (max(0, self.pitch_counts[pitcher['legal_name']] - pitcher['stamina']) / 15) * 0.1
        return self.game_rng.random() < (pitcher['control'] - fatigue_penalty)

    def _simulate_bat_swing(self, batter, is_strike_loc):
        discipline_factor = max(0.1, batter['plate_discipline'].get('Walk', 0.09) / 0.08)
        swing_at_ball_prob = 0.28 / discipline_factor
        return self.game_rng.random() < (0.85 if is_strike_loc else swing_at_ball_prob)

    def _simulate_batted_ball_physics(self, batter):
        batting_profile = batter['batting_profile']
        ev = round(self.game_rng.normalvariate(80 + batting_profile['power'] * 25, 8), 1)
        la = round(self.game_rng.normalvariate(batting_profile['angle'], 10), 1)
        return {'ev': ev, 'la': la}

    def _simulate_bunt_physics(self):
        ev = round(self.game_rng.uniform(60, 75), 1)
        la = round(self.game_rng.uniform(-50, -20), 1)
        return {'ev': ev, 'la': la}

    def _determine_outcome_from_trajectory(self, ev, la):
        if ev < 80: return "Pop Out" if la > 40 else "Groundout" if la < 10 else "Flyout"
        if la < 5: return "Double Play" if ev > 110 else "Single" if ev > 100 else "Groundout"
        if la < 20: return "Home Run" if ev > 115 else "Double" if ev > 105 else "Single" if ev > 90 else "Lineout"
        if la < 35: return "Home Run" if ev > 110 else "Double" if ev > 100 else "Flyout"
        if la < 50: return "Pop Out" if ev < 90 else "Triple" if ev > 105 else "Flyout"
        return "Pop Out"

    def _get_trajectory(self, outcome, la):
        if "Groundout" in outcome: return "ground_ball"
        if la is not None:
            if la < 10: return "ground_ball"
            if 10 <= la <= 25: return "line_drive"
            if la > 50: return "popup"
        return "fly_ball"

    def _get_event_type_code(self, event):
        event_map = {
            "Lineout": "field_out", "Pop Out": "field_out", "Flyout": "field_out",
            "Groundout": "field_out", "Forceout": "force_out", "Double Play": "grounded_into_double_play",
            "Sac Fly": "sac_fly", "Sac Bunt": "sac_bunt", "Sacrifice Bunt": "sac_bunt",
            "Single": "single", "Double": "double", "Triple": "triple", "Home Run": "home_run",
            "Walk": "walk", "Hit By Pitch": "hit_by_pitch", "Strikeout": "strikeout", "Field Error": "field_error"
        }
        return event_map.get(event, event.lower().replace(" ", "_"))

    def _get_men_on_base_split(self, bases):
        if not any(bases): return "Empty"
        if all(bases): return "Loaded"
        return "RISP" if bases[1] or bases[2] else "Men_On"

    def _build_matchup(self, batter, pitcher, pre_play_bases=None):
        batter_info = {"id": batter['id'], "fullName": batter['legal_name'], "link": f"/api/v1/people/{batter['id']}"}
        pitcher_info = {"id": pitcher['id'], "fullName": pitcher['legal_name'], "link": f"/api/v1/people/{pitcher['id']}"}
        pitcher_hand = pitcher.get('pitchHand', {}).get('code', 'R')
        batter_hand_code = batter.get('batSide', {}).get('code', 'R')
        if batter_hand_code == 'S': batter_hand_code = 'L' if pitcher_hand == 'R' else 'R'

        return {
            "batter": batter_info,
            "batSide": {'code': batter_hand_code, 'description': 'Left' if batter_hand_code == 'L' else 'Right'},
            "pitcher": pitcher_info,
            "pitchHand": pitcher.get('pitchHand', {'code': 'R', 'description': 'Right'}),
            "splits": {
                "batter": f"vs_{'RHP' if pitcher_hand == 'R' else 'LHP'}",
                "pitcher": f"vs_{'RHB' if batter_hand_code == 'R' else 'LHB'}",
                "menOnBase": self._get_men_on_base_split(pre_play_bases if pre_play_bases is not None else self.bases)
            }
        }

    def _build_runner_entry(self, runner_name, origin_base, end_base, is_out, out_number,
                            event, event_type, movement_reason, play_index, is_scoring,
                            is_rbi, responsible_pitcher=None, credits=None):
        runner_player = next((p for p in self.team1_lineup + self.team2_lineup if p['legal_name'] == runner_name), None)
        if not runner_player:
            runner_player = next((p for p in self.team1_data['players'] + self.team2_data['players'] if p['legal_name'] == runner_name), None)
        if not runner_player: return None

        runner_entry = {
            "movement": {"originBase": origin_base, "start": origin_base, "end": end_base if not is_out else None,
                         "outBase": end_base if is_out else None, "isOut": is_out, "outNumber": out_number if is_out else None},
            "details": {
                "event": event, "eventType": event_type, "movementReason": movement_reason,
                "runner": {"id": runner_player['id'], "fullName": runner_player['legal_name'], "link": f"/api/v1/people/{runner_player['id']}"},
                "isScoringEvent": is_scoring, "rbi": is_rbi, "earned": is_scoring, "teamUnearned": False, "playIndex": play_index
            },
            "credits": credits if credits else []
        }
        if is_scoring and responsible_pitcher:
            runner_entry["details"]["responsiblePitcher"] = {"id": responsible_pitcher['id'], "link": f"/api/v1/people/{responsible_pitcher['id']}"}
        return runner_entry

    def _decide_steal_attempt(self, balls, strikes):
        count_modifier = 1.0
        if (balls == 0 and strikes in [1, 2]) or (balls == 1 and strikes == 2): count_modifier = 1.2
        elif (balls in [2, 3] and strikes == 0) or (balls == 3 and strikes == 1): count_modifier = 0.8
        outs_modifier = 1.5 if self.outs == 2 else 1.0
        batting_lineup = self.team1_lineup if not self.top_of_inning else self.team2_lineup

        if self.bases[1] and not self.bases[2]:
            runner_data = next((p for p in batting_lineup if p['legal_name'] == self.bases[1]), None)
            if runner_data and self.game_rng.random() < runner_data['batting_profile']['stealing_tendency'] * 0.2 * count_modifier * outs_modifier:
                return 3
        if self.bases[0] and not self.bases[1]:
            runner_data = next((p for p in batting_lineup if p['legal_name'] == self.bases[0]), None)
            if runner_data and self.game_rng.random() < runner_data['batting_profile']['stealing_tendency'] * count_modifier * outs_modifier:
                return 2
        return None

    def _resolve_steal_attempt(self, base_to_steal):
        is_home_team_batting = not self.top_of_inning
        base_from_idx = base_to_steal - 2
        runner_name = self.bases[base_from_idx]
        batting_lineup = self.team1_lineup if is_home_team_batting else self.team2_lineup
        runner_data = next((p for p in batting_lineup if p['legal_name'] == runner_name), None)
        if not runner_data: return False

        defensive_catcher = self.team2_catcher if is_home_team_batting else self.team1_catcher
        success_chance = runner_data['batting_profile']['stealing_success_rate'] - (defensive_catcher['catchers_arm'] * 0.1)
        if self.game_rng.random() < success_chance:
            self.bases[base_to_steal - 1], self.bases[base_from_idx] = runner_name, None
            return False  # Not caught
        else:
            self.outs += 1
            self.bases[base_from_idx] = None
            return True  # Caught stealing

    def _simulate_at_bat(self, batter, pitcher):
        balls, strikes = 0, 0
        play_events: list[PlayEvent] = []
        if self.game_rng.random() < batter['plate_discipline'].get('HBP', 0):
            return "HBP", {}, play_events

        bunt_propensity = batter['batting_profile'].get('bunt_propensity', 0.0)
        bunt_situation = self.outs < 2 and any(self.bases) and not self.bases[2]
        is_bunting = bunt_situation and self.game_rng.random() < bunt_propensity

        while balls < 4 and strikes < 3:
            is_foul = False
            steal_attempt_base = self._decide_steal_attempt(balls, strikes)
            self.pitch_counts[pitcher['legal_name']] += 1
            pitch_selection = self.game_rng.choices(list(pitcher['pitch_arsenal'].keys()), weights=[v['prob'] for v in pitcher['pitch_arsenal'].values()], k=1)[0]
            pitch_details_team = pitcher['pitch_arsenal'][pitch_selection]
            pitch_velo = round(self.game_rng.uniform(*pitch_details_team['velo_range']), 1)
            pitch_spin = self.game_rng.randint(*pitch_details_team.get('spin_range', (2000, 2500))) if self.game_rng.random() > 0.08 else None
            is_strike_loc = self._simulate_pitch_trajectory(pitcher)

            play_event: PlayEvent = {'index': self._pitch_event_seq, 'count': {'balls': balls, 'strikes': strikes}}
            if is_bunting: play_event['isBunt'] = True

            swing = self._simulate_bat_swing(batter, is_strike_loc) or is_bunting
            contact = self.game_rng.random() < batter['batting_profile']['contact'] or (is_bunting and is_strike_loc)
            is_in_play, hit_result = False, None

            if not swing:
                event_details = {'code': 'C' if is_strike_loc else 'B', 'description': 'Called Strike' if is_strike_loc else 'Ball', 'isStrike': is_strike_loc}
                if is_strike_loc: strikes += 1
                else: balls += 1
            elif not contact:
                strikes += 1
                event_details = {'code': 'S', 'description': 'Swinging Strike', 'isStrike': True}
            else:
                is_foul = self.game_rng.random() < 0.6
                if is_foul:
                    if strikes < 2: strikes += 1
                    event_details = {'code': 'F', 'description': 'Foul', 'isStrike': True}
                    if is_bunting: event_details['description'] = 'Foul Bunt'
                    if is_bunting and strikes == 3: break
                else:
                    is_in_play = True
                    batted_ball_data = self._simulate_bunt_physics() if is_bunting else self._simulate_batted_ball_physics(batter)
                    hit_result = "Sacrifice Bunt" if is_bunting else self._determine_outcome_from_trajectory(batted_ball_data['ev'], batted_ball_data['la'])
                    event_details = {'code': 'X', 'description': f'In play, {hit_result}', 'isStrike': True}

            event_details['type'] = {'code': SIMULATION_CONTEXT['PITCH_TYPE_MAP'].get(pitch_selection, 'UN'), 'description': pitch_selection.capitalize()}
            pitch_data = {'startSpeed': pitch_velo}
            if pitch_spin: pitch_data['breaks'] = {'spinRate': pitch_spin}
            play_event['details'] = event_details
            play_event['pitchData'] = pitch_data
            play_events.append(play_event)
            self._pitch_event_seq += 1

            if is_in_play:
                description_context = {'batted_ball_data': batted_ball_data}
                if 'ev' in batted_ball_data:
                    play_events[-1]['hitData'] = {
                        'launchSpeed': batted_ball_data['ev'], 'launchAngle': batted_ball_data['la'],
                        'trajectory': self._get_trajectory(hit_result, batted_ball_data.get('la'))}
                return hit_result, description_context, play_events

            if steal_attempt_base and not is_foul:
                caught_stealing = self._resolve_steal_attempt(steal_attempt_base)
                if caught_stealing and self.outs >= 3: return "Caught Stealing", {}, play_events
                if caught_stealing and strikes == 3:
                    self.outs += 1
                    return "Strikeout Double Play", {}, play_events

        if balls == 4: return "Walk", {}, play_events
        return "Strikeout", {}, play_events

    def _advance_runners(self, hit_type, batter, was_error=False):
        runs, rbis = 0, 0
        old_bases, self.bases = self.bases[:], [None, None, None]
        batter_name = batter['legal_name']
        batter_gets_rbi = not was_error

        if hit_type in ["Walk", "HBP"]:
            new_bases = old_bases[:]
            if new_bases[0]:
                if new_bases[1]:
                    if new_bases[2]: runs += 1; rbis += 1
                    new_bases[2] = new_bases[1]
                new_bases[1] = new_bases[0]
            new_bases[0] = batter_name
            self.bases = new_bases
            return runs, rbis

        if hit_type == 'Single':
            if old_bases[2]: runs += 1; rbis += (1 if batter_gets_rbi else 0)
            if old_bases[1]: self.bases[2] = old_bases[1]
            if old_bases[0]: self.bases[1] = old_bases[0]
            self.bases[0] = batter_name
        elif hit_type == 'Double':
            if old_bases[2]: runs += 1; rbis += (1 if batter_gets_rbi else 0)
            if old_bases[1]: runs += 1; rbis += (1 if batter_gets_rbi else 0)
            if old_bases[0]: self.bases[2] = old_bases[0]
            self.bases[1] = batter_name
        elif hit_type == 'Triple':
            for runner in old_bases:
                if runner: runs += 1; rbis += (1 if batter_gets_rbi else 0)
            self.bases[2] = batter_name
        elif hit_type == 'Home Run':
            for runner in old_bases:
                if runner: runs += 1; rbis += 1
            runs += 1; rbis += 1
        return runs, rbis

    def _manage_pitching_change(self):
        is_home_team_pitching = self.top_of_inning
        prefix = 'team1' if is_home_team_pitching else 'team2'
        current_pitcher_name = getattr(self, f"{prefix}_current_pitcher_name")
        pitcher_stats = getattr(self, f"{prefix}_pitcher_stats")
        available_bullpen = getattr(self, f"{prefix}_available_bullpen")
        fatigue_factor = max(0, self.pitch_counts[current_pitcher_name] - pitcher_stats[current_pitcher_name]['stamina'])
        if fatigue_factor > 0 and available_bullpen:
            next_pitcher_name = available_bullpen[0]
            if current_pitcher_name != next_pitcher_name:
                setattr(self, f"{prefix}_current_pitcher_name", next_pitcher_name)
                setattr(self, f"{prefix}_available_bullpen", available_bullpen[1:])

    def _handle_batted_ball_out(self, out_type, batter, context=None):
        defensive_prefix = 'team1' if self.top_of_inning else 'team2'
        infielders = getattr(self, f"{defensive_prefix}_infielders")
        outfielders = getattr(self, f"{defensive_prefix}_outfielders")
        pitcher = getattr(self, f"{defensive_prefix}_pitcher_stats")[getattr(self, f"{defensive_prefix}_current_pitcher_name")]
        catcher = getattr(self, f"{defensive_prefix}_catcher")
        first_baseman = getattr(self, f"{defensive_prefix}_defense").get('1B')

        if out_type in ['Groundout', 'Sacrifice Bunt', 'Lineout', 'Pop Out', 'Forceout', 'Grounded Into DP']:
            candidates = [(p, 6) for p in infielders] + [(pitcher, 1)] + ([(catcher, 0.25)] if catcher else [])
            fielder = self.game_rng.choices([c[0] for c in candidates], weights=[c[1] for c in candidates], k=1)[0]
        else: # Flyout, Sac Fly
            fielder = self.game_rng.choices(outfielders + infielders, weights=[6] * len(outfielders) + [1] * len(infielders), k=1)[0]

        is_error = fielder and self.game_rng.random() > fielder['fielding_ability']
        if is_error:
            return 0, 0, True, [], False, "Field Error", None, f"Error by {fielder['legal_name']}"

        runs, rbis, credits, is_dp, runner_out_dp, specific_event = 0, 0, [], False, None, out_type
        description = ""
        if out_type in ['Flyout', 'Pop Out', 'Lineout']:
            credits.append({'player': {'id': fielder['id']}, 'position': fielder['position'], 'credit': 'putout'})
            if self.outs < 2 and self.bases[2] and fielder['position']['abbreviation'] in ['LF', 'CF', 'RF'] and self.game_rng.random() > 0.4:
                self.outs += 1; runs, rbis = 1, 1; self.bases[2] = None; specific_event = "Sac Fly"
                description = f"Sac fly to {fielder['position']['abbreviation']}"
            else:
                self.outs += 1
                description = f"{out_type} to {fielder['position']['abbreviation']}"
        elif out_type == 'Groundout':
            if self.outs < 2 and self.bases[0] and self.game_rng.random() < 0.3: # DP attempt
                runner_out_dp = self.bases[0]
                self.outs += 2; self.bases[0] = None; is_dp = True; specific_event = "Double Play"
                sb = getattr(self, f"{defensive_prefix}_defense").get('2B')
                credits = ([{'player': {'id': fielder['id']}, 'credit': 'assist'}, {'player': {'id': sb['id']}, 'credit': 'assist'}, {'player': {'id': first_baseman['id']}, 'credit': 'putout'}])
                description = "Grounds into a double play."
            else:
                self.outs += 1
                if self.outs < 3:
                    if self.bases[2]: runs, rbis, self.bases[2] = 1, 1, None
                    if self.bases[1]: self.bases[2], self.bases[1] = self.bases[1], None
                    if self.bases[0]: self.bases[1], self.bases[0] = self.bases[0], None
                else: runs, rbis = 0, 0
                credits = [{'player': {'id': fielder['id']}, 'credit': 'assist'}, {'player': {'id': first_baseman['id']}, 'credit': 'putout'}]
                description = f"Groundout to {fielder['position']['abbreviation']}"
        elif out_type == 'Sacrifice Bunt':
            self.outs += 1; rbis = 0
            if self.bases[1]: self.bases[2], self.bases[1] = self.bases[1], None
            if self.bases[0]: self.bases[1], self.bases[0] = self.bases[0], None
            credits = [{'player': {'id': fielder['id']}, 'credit': 'assist'}, {'player': {'id': first_baseman['id']}, 'credit': 'putout'}]
            description = f"Sacrifice Bunt to {fielder['position']['abbreviation']}"
        return runs, rbis, is_error, credits, is_dp, specific_event, runner_out_dp, description

    def _simulate_half_inning(self):
        self.outs, self.bases = 0, [None, None, None]
        lineup, batter_idx_ref = (self.team1_lineup, 'team1_batter_idx') if not self.top_of_inning else (self.team2_lineup, 'team2_batter_idx')
        if self.inning >= 10:
            last_batter_idx = (getattr(self, batter_idx_ref) - 1 + 9) % 9
            self.bases[1] = lineup[last_batter_idx]['legal_name']

        while self.outs < 3:
            self._manage_pitching_change()
            pitcher_name = self.team1_current_pitcher_name if self.top_of_inning else self.team2_current_pitcher_name
            pitcher = (self.team1_pitcher_stats if self.top_of_inning else self.team2_pitcher_stats)[pitcher_name]
            batter = lineup[getattr(self, batter_idx_ref)]
            pre_play_bases = self.bases[:]
            outcome, description, play_events = self._simulate_at_bat(batter, pitcher)

            runs, rbis, was_error, credits, is_dp, runner_out_dp, play_description = 0, 0, False, [], False, None, ""
            old_bases = self.bases[:]

            if outcome == "Caught Stealing": pass
            elif "out" in outcome or "Play" in outcome or "Bunt" in outcome:
                runs, rbis, was_error, credits, is_dp, specific_event, runner_out_dp, play_description = self._handle_batted_ball_out(outcome, batter, description)
                if was_error: outcome = "Field Error"
                else: outcome = specific_event
            elif outcome == "Strikeout": self.outs += 1
            elif outcome == "Strikeout Double Play": play_description = "Strike 'em out, throw 'em out double play."

            if outcome not in ["Strikeout", "Caught Stealing", "Double Play"] and "out" not in outcome:
                 new_runs, new_rbis = self._advance_runners(outcome, batter, was_error=was_error)
                 runs += new_runs; rbis += new_rbis

            if not self.top_of_inning: self.team1_score += runs
            else: self.team2_score += runs

            # Gameday Population
            play_index = len(play_events) - 1 if play_events else 0
            base_map = {0: "1B", 1: "2B", 2: "3B"}
            runner_list: list[Runner] = []

            # This is a simplified version, a full implementation would be more robust
            for base_idx, runner_name in enumerate(old_bases):
                if runner_name:
                    is_out = runner_name not in self.bases and runner_name != runner_out_dp
                    scored = runner_name not in self.bases and not is_out
                    end_base = "score" if scored else base_map[self.bases.index(runner_name)] if runner_name in self.bases else None
                    runner_list.append(self._build_runner_entry(runner_name, base_map[base_idx], end_base, is_out, None, outcome, self._get_event_type_code(outcome), None, play_index, scored, scored and not was_error, pitcher if scored else None))

            batter_reaches = not ("out" in outcome or "Play" in outcome or "Strikeout" in outcome)
            batter_end_base = "1B" # Simplified
            if outcome == "Home Run": batter_end_base = "score"

            runner_list.append(self._build_runner_entry(batter['legal_name'], None, batter_end_base if batter_reaches else "1B", not batter_reaches, self.outs if not batter_reaches else None, outcome, self._get_event_type_code(outcome), None, play_index, outcome == "Home Run", rbis > 0, pitcher if outcome=="Home Run" else None, credits))

            at_bat_index = len(self.gameday_data['liveData']['plays']['allPlays'])
            play_result = PlayResult(type="atBat", event=outcome, eventType=self._get_event_type_code(outcome), description=play_description, rbi=rbis, awayScore=self.team2_score, homeScore=self.team1_score)
            play_about = PlayAbout(atBatIndex=at_bat_index, halfInning="bottom" if not self.top_of_inning else "top", isTopInning=self.top_of_inning, inning=self.inning, isScoringPlay=runs > 0)
            final_count = PlayCount(balls=0, strikes=0, outs=self.outs) # Simplified
            matchup = self._build_matchup(batter, pitcher, pre_play_bases)

            play_data: Play = {"result": play_result, "about": play_about, "count": final_count, "matchup": matchup, "playEvents": play_events, "runners": runner_list}
            self.gameday_data['liveData']['plays']['allPlays'].append(play_data)

            ls = self.gameday_data['liveData']['linescore']
            ls['outs'] = self.outs
            ls['teams']['home']['runs'], ls['teams']['away']['runs'] = self.team1_score, self.team2_score
            if outcome in ["Single", "Double", "Triple", "Home Run"]:
                if not self.top_of_inning: ls['teams']['home']['hits'] += 1
                else: ls['teams']['away']['hits'] += 1
            if was_error:
                if not self.top_of_inning: ls['teams']['away']['errors'] += 1
                else: ls['teams']['home']['errors'] += 1

            setattr(self, batter_idx_ref, (getattr(self, batter_idx_ref) + 1) % 9)
            if self.outs >= 3: break
            if not self.top_of_inning and self.team1_score > self.team2_score and self.inning >= 9: return

    def play_game(self) -> GamedayData:
        should_continue = lambda: (self.inning <= 9 or self.team1_score == self.team2_score) if self.max_innings is None else self.inning <= self.max_innings
        while should_continue():
            self.top_of_inning = True
            self._simulate_half_inning()
            if self.inning >= 9 and not self.top_of_inning and self.team1_score > self.team2_score: break
            if self.max_innings and self.inning >= self.max_innings: break

            self.top_of_inning = False
            self._simulate_half_inning()
            if self.inning >= 9 and not self.top_of_inning and self.team1_score > self.team2_score: break
            if self.max_innings and self.inning >= self.max_innings: break

            self.inning += 1
            self.gameday_data['liveData']['linescore']['currentInning'] = self.inning
            self.gameday_data['liveData']['linescore']['innings'].append({'num': self.inning, 'home': {'runs': 0}, 'away': {'runs': 0}})

        return self.gameday_data

