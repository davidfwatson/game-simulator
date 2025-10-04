import random
from teams import TEAMS

class BaseballSimulator:
    """
    Simulates a modern MLB game with realistic rules and enhanced realism.
    - DH rule is in effect.
    - Extra innings start with a "ghost runner" on second.
    - Realistic bullpen management with pitcher fatigue.
    - Detailed play-by-play with varied phrasing and official scorer codes.
    - Player names are distinguished by legal vs. nickname.
    - Pitch velocities are randomized within a defined range.
    """

    def __init__(self, team1_data, team2_data, varied_phrasing=False):
        self.team1_data = team1_data
        self.team2_data = team2_data
        self.team1_name = self.team1_data["name"]
        self.team2_name = self.team2_data["name"]
        self.varied_phrasing = varied_phrasing

        self.park = team1_data["park"]
        self.umpires = team1_data["umpires"]
        
        self.team1_lineup = [p for p in self.team1_data["players"] if p['position'] != 'P']
        self.team2_lineup = [p for p in self.team2_data["players"] if p['position'] != 'P']
        
        all_team1_pitchers = [p for p in self.team1_data["players"] if p['position'] == 'P']
        self.team1_pitcher_stats = {p['legal_name']: p.copy() for p in all_team1_pitchers}
        self.team1_available_bullpen = [p['legal_name'] for p in all_team1_pitchers if p['type'] != 'Starter']
        
        all_team2_pitchers = [p for p in self.team2_data["players"] if p['position'] == 'P']
        self.team2_pitcher_stats = {p['legal_name']: p.copy() for p in all_team2_pitchers}
        self.team2_available_bullpen = [p['legal_name'] for p in all_team2_pitchers if p['type'] != 'Starter']

        self.team1_current_pitcher_name = next(p['legal_name'] for p in all_team1_pitchers if p['type'] == 'Starter')
        self.team2_current_pitcher_name = next(p['legal_name'] for p in all_team2_pitchers if p['type'] == 'Starter')
        
        self.pitch_counts = {name: 0 for name in list(self.team1_pitcher_stats.keys()) + list(self.team2_pitcher_stats.keys())}
        
        self.team1_batter_idx, self.team2_batter_idx = 0, 0
        self.team1_score, self.team2_score = 0, 0
        self.inning, self.top_of_inning = 1, True
        self.outs, self.bases = 0, [0, 0, 0]

    def _get_player_display_name(self, player):
        if player['nickname']:
            return f"{player['legal_name']} ('{player['nickname']}')"
        return player['legal_name']

    def _get_hit_outcome(self, batter_stats):
        in_play = {k: v for k, v in batter_stats.items() if k not in ["Walk", "Strikeout"]}
        return random.choices(list(in_play.keys()), weights=list(in_play.values()), k=1)[0]

    def _simulate_at_bat(self, batter, pitcher):
        balls, strikes = 0, 0
        
        display_name = self._get_player_display_name(batter)
        print(f"Now batting: {display_name} ({batter['position']}, {batter['handedness']})")

        while balls < 4 and strikes < 3:
            self.pitch_counts[pitcher['legal_name']] += 1
            
            pitch_selection = random.choices(list(pitcher['pitch_arsenal'].keys()),
                                             weights=[v['prob'] for v in pitcher['pitch_arsenal'].values()], k=1)[0]
            pitch_details = pitcher['pitch_arsenal'][pitch_selection]
            pitch_velo = random.randint(*pitch_details['velo_range'])

            fatigue_factor = max(0, self.pitch_counts[pitcher['legal_name']] - pitcher['stamina'])
            fatigue_penalty = (fatigue_factor / 15) * 0.1
            effective_control = pitcher['control'] - fatigue_penalty

            is_strike_loc = random.random() < effective_control
            
            swing = random.random() < (0.8 if is_strike_loc else 0.3)
            
            if self.varied_phrasing:
                location_desc = "over the heart of the plate" if is_strike_loc else random.choice(["high and tight", "low and away", "just off the corner"])
                pitch_desc = f"  The {pitch_selection} comes in at {pitch_velo} mph, {location_desc}."
            else:
                location = "in the zone" if is_strike_loc else random.choice(["high", "low", "inside", "outside"])
                pitch_desc = f"  Pitch: {pitch_selection} ({pitch_velo} mph), {location}."

            if swing:
                if random.random() < 0.7: # Contact
                    if strikes < 2 and random.random() < 0.5: # Foul
                        strikes += 1
                        print(f"{pitch_desc} Foul. Count: {balls}-{strikes}")
                    else: # In Play
                        hit_result = self._get_hit_outcome(batter['stats'])
                        print(f"{pitch_desc} In play -> {hit_result}!")
                        return hit_result
                else: # Swing and miss
                    strikes += 1
                    if strikes == 3: print(f"{pitch_desc} Swinging Strike (Whiff).")
                    else: print(f"{pitch_desc} Swinging Strike. Count: {balls}-{strikes}")
            else: # Taken pitch
                if is_strike_loc:
                    strikes += 1
                    if strikes == 3: print(f"{pitch_desc} Called Strike.")
                    else: print(f"{pitch_desc} Called Strike. Count: {balls}-{strikes}")
                else:
                    balls += 1
                    if balls == 4: print(f"{pitch_desc} Ball.")
                    else: print(f"{pitch_desc} Ball. Count: {balls}-{strikes}")
        
        return "Walk" if balls == 4 else "Strikeout"

    def _advance_runners(self, hit_type):
        runs = 0
        if hit_type == "Single":
            if self.bases[2]: runs += 1; self.bases[2] = 0
            if self.bases[1]: self.bases[2] = 1; self.bases[1] = 0
            if self.bases[0]: self.bases[1] = 1
            self.bases[0] = 1
        elif hit_type == "Double":
            if self.bases[2]: runs += 1; self.bases[2] = 0
            if self.bases[1]: runs += 1; self.bases[1] = 0
            if self.bases[0]: self.bases[2] = 1; self.bases[0] = 0
            self.bases[1] = 1
        elif hit_type == "Triple":
            runs += sum(self.bases); self.bases = [0, 0, 1]
        elif hit_type == "Home Run":
            runs += sum(self.bases) + 1; self.bases = [0, 0, 0]
        elif hit_type == "Walk":
            if self.bases == [1,1,1]: runs += 1
            elif self.bases[0] and self.bases[1]: self.bases[2] = 1
            elif self.bases[0]: self.bases[1] = 1
            self.bases[0] = 1
        return runs

    def _get_bases_str(self):
        if self.varied_phrasing:
            runners = []
            if self.bases[0]: runners.append("1st")
            if self.bases[1]: runners.append("2nd")
            if self.bases[2]: runners.append("3rd")

            if not runners: return "Bases empty"
            if len(runners) == 3: return "Bases loaded"
            if runners == ["1st", "3rd"]: return "Runners on the corners"

            return f"Runner{'s' if len(runners) > 1 else ''} on {', '.join(runners)}"
        else:
            return f"Bases: [{'1B' if self.bases[0] else '_'}]-[{'2B' if self.bases[1] else '_'}]-[{'3B' if self.bases[2] else '_'}]"


    def _manage_pitching_change(self):
        is_home_team_pitching = self.top_of_inning
        
        current_pitcher_name = self.team1_current_pitcher_name if is_home_team_pitching else self.team2_current_pitcher_name
        pitcher_stats = self.team1_pitcher_stats if is_home_team_pitching else self.team2_pitcher_stats
        available_bullpen = self.team1_available_bullpen if is_home_team_pitching else self.team2_available_bullpen
        team_name = self.team1_name if is_home_team_pitching else self.team2_name

        current_pitcher = pitcher_stats[current_pitcher_name]
        
        fatigue_factor = max(0, self.pitch_counts[current_pitcher_name] - current_pitcher['stamina'])

        if fatigue_factor > 0 and available_bullpen:
            next_pitcher_name = None
            if self.inning >= 9 and 'Closer' in [pitcher_stats[p]['type'] for p in available_bullpen]:
                next_pitcher_name = next((p for p in available_bullpen if pitcher_stats[p]['type'] == 'Closer'), available_bullpen[0])
            elif self.inning >= 7 and 'Middle Reliever' in [pitcher_stats[p]['type'] for p in available_bullpen]:
                next_pitcher_name = next((p for p in available_bullpen if pitcher_stats[p]['type'] == 'Middle Reliever'), available_bullpen[0])
            elif 'Long Reliever' in [pitcher_stats[p]['type'] for p in available_bullpen]:
                 next_pitcher_name = next((p for p in available_bullpen if pitcher_stats[p]['type'] == 'Long Reliever'), available_bullpen[0])
            else:
                next_pitcher_name = available_bullpen[0]

            if is_home_team_pitching:
                if self.team1_current_pitcher_name != next_pitcher_name:
                    self.team1_current_pitcher_name = next_pitcher_name
                    self.team1_available_bullpen.remove(next_pitcher_name)
                    print(f"\n--- Pitching Change for {team_name}: Now pitching, {next_pitcher_name} ---\n")
            else:
                if self.team2_current_pitcher_name != next_pitcher_name:
                    self.team2_current_pitcher_name = next_pitcher_name
                    self.team2_available_bullpen.remove(next_pitcher_name)
                    print(f"\n--- Pitching Change for {team_name}: Now pitching, {next_pitcher_name} ---\n")

    def _get_defensive_assist(self, outcome, defensive_lineup):
        if outcome == "Groundout":
            # Common groundout paths: 6-3 (SS-1B), 4-3 (2B-1B), 5-3 (3B-1B), 1-3 (P-1B)
            fielder1_pos = random.choice([6, 4, 5, 1])
            # fielder1 = next((p for p in defensive_lineup if p['fielding_position'] == fielder1_pos), None)
            # fielder2 = next((p for p in defensive_lineup if p['fielding_position'] == 3), None)
            return f"({fielder1_pos}-3)"
        elif outcome == "Flyout":
            fielder_pos = random.choice([7, 8, 9]) # Outfielders
            # fielder = next((p for p in defensive_lineup if p['fielding_position'] == fielder_pos), None)
            return f"(F{fielder_pos})"
        return ""

    def _simulate_half_inning(self):
        self.outs, self.bases = 0, [0, 0, 0]
        
        if self.inning >= 10:
            self.bases = [0, 1, 0]
            print("Runner on second to start the inning.")

        is_home_team_batting = not self.top_of_inning
        batting_team_name, lineup, batter_idx_ref = (self.team1_name, self.team1_lineup, 'team1_batter_idx') if is_home_team_batting else (self.team2_name, self.team2_lineup, 'team2_batter_idx')
        
        defensive_team_data = self.team1_data if self.top_of_inning else self.team2_data
        defensive_lineup = [p for p in defensive_team_data['players'] if p.get('fielding_position', 0) > 0]

        inning_half = "Bottom" if is_home_team_batting else "Top"
        print("-" * 50)
        print(f"{inning_half} of Inning {self.inning} | {batting_team_name} batting")

        while self.outs < 3:
            self._manage_pitching_change()
            pitcher_name = self.team1_current_pitcher_name if self.top_of_inning else self.team2_current_pitcher_name
            pitcher_stats_dict = self.team1_pitcher_stats if self.top_of_inning else self.team2_pitcher_stats
            pitcher = pitcher_stats_dict[pitcher_name]

            batter_idx = getattr(self, batter_idx_ref)
            batter = lineup[batter_idx]

            outcome = self._simulate_at_bat(batter, pitcher)
            defensive_team_data = self.team1_data if self.top_of_inning else self.team2_data
            runs = 0
            outcome_detail = ""

            if outcome in ["Groundout", "Flyout"]:
                if random.random() > defensive_team_data["fielding_prowess"]:
                    outcome = "Error"
                    fielder_pos = random.choice([3,4,5,6,7,8,9]) # Non-pitcher/catcher
                    fielder = next((p for p in defensive_lineup if p['fielding_position'] == fielder_pos), None)
                    outcome_detail = f" (E{fielder['fielding_position']})"
                    print(f"  An error by the defense! {fielder['legal_name']} mishandles the play.")
            
            if outcome == "Error":
                runs = self._advance_runners("Single")
            elif outcome == "Strikeout":
                self.outs += 1
            elif outcome == "Flyout":
                self.outs += 1
                outcome_detail = self._get_defensive_assist(outcome, defensive_lineup)
                if self.outs < 3 and self.bases[2] and random.random() > 0.5:
                    runs += 1; self.bases[2] = 0
                    outcome_detail += " Sac Fly"
                    print("  A run scores on the sacrifice fly!")
            elif outcome == "Groundout":
                if self.outs < 2 and self.bases[0] == 1 and random.random() < defensive_team_data["double_play_rate"]:
                    self.outs += 2
                    outcome = "Double Play"
                    fielder1_pos, fielder2_pos, fielder3_pos = random.choice([(6,4,3), (4,6,3), (5,4,3)])
                    f1 = next((p['legal_name'] for p in defensive_lineup if p['fielding_position'] == fielder1_pos), '')
                    f2 = next((p['legal_name'] for p in defensive_lineup if p['fielding_position'] == fielder2_pos), '')
                    f3 = next((p['legal_name'] for p in defensive_lineup if p['fielding_position'] == fielder3_pos), '')
                    outcome_detail = f" ({f1}-{f2}-{f3})"
                    if self.outs <= 3:
                        if self.bases[2]: runs += 1
                        self.bases[2] = self.bases[1]; self.bases[1] = 0; self.bases[0] = 0
                else:
                    self.outs += 1
                    outcome_detail = self._get_defensive_assist(outcome, defensive_lineup)
                    if self.outs < 3 and any(self.bases):
                        if self.bases[2]: runs += 1; self.bases[2] = 0
                        if self.bases[1]: self.bases[2] = 1; self.bases[1] = 0
                        if self.bases[0]: self.bases[1] = 1; self.bases[0] = 0
            else:
                runs = self._advance_runners(outcome)

            if is_home_team_batting: self.team1_score += runs
            else: self.team2_score += runs
            
            score_str = f"{self.team1_name}: {self.team1_score}, {self.team2_name}: {self.team2_score}"
            final_outcome = f"{outcome} {outcome_detail}".strip()
            print(f"Result: {final_outcome.ljust(20)} | Outs: {self.outs} | {self._get_bases_str()} | Score: {score_str}\n")
            
            if is_home_team_batting and self.team1_score > self.team2_score and self.inning >= 9:
                return
            setattr(self, batter_idx_ref, (batter_idx + 1) % 9)

    def play_game(self):
        print("="*20, "PLAY BALL!", "="*20)
        print(f"Welcome to {self.park} for today's game between the {self.team2_name} and the {self.team1_name}.")
        print(f"Umpires: HP-{self.umpires['HP']}, 1B-{self.umpires['1B']}, 2B-{self.umpires['2B']}, 3B-{self.umpires['3B']}\n")

        while self.inning <= 9 or self.team1_score == self.team2_score:
            self.top_of_inning = True
            self._simulate_half_inning()
            if self.inning >= 9 and self.team1_score > self.team2_score: break
            self.top_of_inning = False
            self._simulate_half_inning()
            if self.inning >=9 and self.team1_score > self.team2_score: break
            self.inning += 1
        print("="*20, "GAME OVER", "="*20)
        print(f"\nFinal Score: {self.team1_name} {self.team1_score} - {self.team2_name} {self.team2_score}")
        winner = self.team1_name if self.team1_score > self.team2_score else self.team2_name
        print(f"\n{winner} win!")

if __name__ == "__main__":
    home_team_key = "BAY_BOMBERS"
    away_team_key = "PC_PILOTS"
    # To test varied phrasing, set varied_phrasing=True
    game = BaseballSimulator(TEAMS[home_team_key], TEAMS[away_team_key], varied_phrasing=False)
    game.play_game()