import random
from teams import TEAMS

class BaseballSimulator:
    """
    Simulates a modern MLB game with realistic rules:
    - DH rule is in effect.
    - Extra innings start with a "ghost runner" on second.
    - Realistic bullpen management with pitcher fatigue.
    - Corrected play-by-play logging.
    """

    def __init__(self, team1_data, team2_data):
        self.team1_name = team1_data["name"]
        self.team2_name = team2_data["name"]
        
        self.team1_lineup = [p for p in team1_data["players"] if p['position'] != 'P']
        self.team2_lineup = [p for p in team2_data["players"] if p['position'] != 'P']
        
        # Setup pitching staffs
        all_team1_pitchers = [p for p in team1_data["players"] if p['position'] == 'P']
        self.team1_pitcher_stats = {p['name']: p.copy() for p in all_team1_pitchers}
        self.team1_available_bullpen = [p['name'] for p in all_team1_pitchers if p['type'] != 'Starter']
        
        all_team2_pitchers = [p for p in team2_data["players"] if p['position'] == 'P']
        self.team2_pitcher_stats = {p['name']: p.copy() for p in all_team2_pitchers}
        self.team2_available_bullpen = [p['name'] for p in all_team2_pitchers if p['type'] != 'Starter']

        self.team1_current_pitcher_name = next(p['name'] for p in all_team1_pitchers if p['type'] == 'Starter')
        self.team2_current_pitcher_name = next(p['name'] for p in all_team2_pitchers if p['type'] == 'Starter')
        
        self.pitch_counts = {name: 0 for name in list(self.team1_pitcher_stats.keys()) + list(self.team2_pitcher_stats.keys())}
        
        self.team1_batter_idx, self.team2_batter_idx = 0, 0
        self.team1_score, self.team2_score = 0, 0
        self.inning, self.top_of_inning = 1, True
        self.outs, self.bases = 0, [0, 0, 0]

    def _get_hit_outcome(self, batter_stats):
        in_play = {k: v for k, v in batter_stats.items() if k not in ["Walk", "Strikeout"]}
        return random.choices(list(in_play.keys()), weights=list(in_play.values()), k=1)[0]

    def _simulate_at_bat(self, batter, pitcher):
        balls, strikes = 0, 0
        pitch_locations = ["high", "low", "inside", "outside"]
        
        print(f"Now batting: {batter['name']} ({batter['position']}, {batter['handedness']})")

        while balls < 4 and strikes < 3:
            self.pitch_counts[pitcher['name']] += 1
            pitch_type = random.choices(list(pitcher['pitch_arsenal'].keys()), weights=list(pitcher['pitch_arsenal'].values()))[0]
            
            is_strike_loc = random.random() < pitcher['control']
            location = "in the zone" if is_strike_loc else random.choice(pitch_locations)
            
            swing = random.random() < (0.8 if is_strike_loc else 0.3)
            
            pitch_desc = f"  Pitch: {pitch_type}, {location}."

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
                    if strikes == 3: print(f"{pitch_desc} Swinging Strike.")
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
        # ... (This logic remains the same as before) ...
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
        return f"[{'1B' if self.bases[0] else '_'}]-[{'2B' if self.bases[1] else '_'}]-[{'3B' if self.bases[2] else '_'}]"

    def _manage_pitching_change(self):
        is_home_team = not self.top_of_inning
        current_pitcher_name = self.team1_current_pitcher_name if is_home_team else self.team2_current_pitcher_name
        pitcher_stats = self.team1_pitcher_stats if is_home_team else self.team2_pitcher_stats
        available_bullpen = self.team1_available_bullpen if is_home_team else self.team2_available_bullpen
        
        current_pitcher = pitcher_stats[current_pitcher_name]
        
        if self.pitch_counts[current_pitcher_name] >= current_pitcher['stamina'] and available_bullpen:
            # Simple bullpen logic: find the best available reliever for the situation
            next_pitcher_name = None
            if self.inning >= 9 and 'Closer' in [pitcher_stats[p]['type'] for p in available_bullpen]:
                next_pitcher_name = next(p for p in available_bullpen if pitcher_stats[p]['type'] == 'Closer')
            elif self.inning >= 7 and 'Middle Reliever' in [pitcher_stats[p]['type'] for p in available_bullpen]:
                next_pitcher_name = next(p for p in available_bullpen if pitcher_stats[p]['type'] == 'Middle Reliever')
            elif 'Long Reliever' in [pitcher_stats[p]['type'] for p in available_bullpen]:
                 next_pitcher_name = next(p for p in available_bullpen if pitcher_stats[p]['type'] == 'Long Reliever')
            else:
                next_pitcher_name = available_bullpen[0]

            if is_home_team:
                self.team1_current_pitcher_name = next_pitcher_name
                self.team1_available_bullpen.remove(next_pitcher_name)
                print(f"\n--- Pitching Change for {self.team1_name}: Now pitching, {next_pitcher_name} ---\n")
            else:
                self.team2_current_pitcher_name = next_pitcher_name
                self.team2_available_bullpen.remove(next_pitcher_name)
                print(f"\n--- Pitching Change for {self.team2_name}: Now pitching, {next_pitcher_name} ---\n")

    def _simulate_half_inning(self):
        self.outs, self.bases = 0, [0, 0, 0]
        
        # Implement the "ghost runner" rule for extra innings
        if self.inning >= 10:
            self.bases = [0, 1, 0] # Runner on second
            print("--- Extra Innings: Runner placed on second base ---")

        is_home_team_batting = not self.top_of_inning
        batting_team_name, lineup, batter_idx_ref = (self.team1_name, self.team1_lineup, 'team1_batter_idx') if is_home_team_batting else (self.team2_name, self.team2_lineup, 'team2_batter_idx')
        
        inning_half = "Bottom" if is_home_team_batting else "Top"
        print("-" * 50)
        print(f"{inning_half} of Inning {self.inning} | {batting_team_name} batting")

        while self.outs < 3:
            self._manage_pitching_change()
            pitcher_name = self.team2_current_pitcher_name if self.top_of_inning else self.team1_current_pitcher_name
            pitcher_stats_dict = self.team2_pitcher_stats if self.top_of_inning else self.team1_pitcher_stats
            pitcher = pitcher_stats_dict[pitcher_name]

            if self.outs == 0: # Print pitcher info once at the start of the inning/change
                print(f"Pitching: {pitcher['name']} ({pitcher['handedness']}) - Pitch Count: {self.pitch_counts[pitcher['name']]}")
                print("-" * 50)

            batter_idx = getattr(self, batter_idx_ref)
            batter = lineup[batter_idx]

            outcome = self._simulate_at_bat(batter, pitcher)
            
            if outcome in ["Strikeout", "Groundout", "Flyout"]: self.outs += 1
            else:
                runs = self._advance_runners(outcome)
                if is_home_team_batting: self.team1_score += runs
                else: self.team2_score += runs
            
            score_str = f"{self.team1_name}: {self.team1_score}, {self.team2_name}: {self.team2_score}"
            print(f"Result: {outcome.ljust(12)} | Outs: {self.outs} | Bases: {self._get_bases_str()} | Score: {score_str}\n")
            
            # Check for walk-off win in the bottom of the 9th or extras
            if is_home_team_batting and self.team1_score > self.team2_score and self.inning >= 9:
                return # End the half-inning immediately on a walk-off

            setattr(self, batter_idx_ref, (batter_idx + 1) % 9)

    def play_game(self):
        print("="*20, "PLAY BALL!", "="*20, "\n")
        while self.inning <= 9 or self.team1_score == self.team2_score:
            self.top_of_inning = True
            self._simulate_half_inning()

            if self.inning >= 9 and self.team1_score > self.team2_score: break
                
            self.top_of_inning = False
            self._simulate_half_inning()
            if self.team1_score > self.team2_score and self.inning >=9: break # End on walkoff
            
            self.inning += 1

        print("="*20, "GAME OVER", "="*20)
        print(f"\nFinal Score: {self.team1_name} {self.team1_score} - {self.team2_name} {self.team2_score}")
        winner = self.team1_name if self.team1_score > self.team2_score else self.team2_name
        print(f"\n{winner} win!")

if __name__ == "__main__":
    home_team_key = "BAY_BOMBERS"
    away_team_key = "PC_PILOTS"
    game = BaseballSimulator(TEAMS[home_team_key], TEAMS[away_team_key])
    game.play_game()

