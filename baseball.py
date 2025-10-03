import random
from teams import TEAMS

class BaseballSimulator:
    """
    A CLI tool to simulate a realistic, modern MLB game with DH and bullpens.
    """

    def __init__(self, team1_data, team2_data):
        """ Initializes the game with teams, rosters, and game state. """
        self.team1_name = team1_data["name"]
        self.team2_name = team2_data["name"]
        
        # Separate lineups and pitchers, implementing the DH rule
        self.team1_lineup = [p for p in team1_data["players"] if p['position'] != 'P']
        self.team2_lineup = [p for p in team2_data["players"] if p['position'] != 'P']
        
        self.team1_pitchers = {p['type']: p for p in team1_data["players"] if p['position'] == 'P'}
        self.team2_pitchers = {p['type']: p for p in team2_data["players"] if p['position'] == 'P'}

        # Set the starting pitchers
        self.team1_current_pitcher = self.team1_pitchers['Starter']
        self.team2_current_pitcher = self.team2_pitchers['Starter']
        
        # Track pitch counts for fatigue
        self.team1_pitch_count = 0
        self.team2_pitch_count = 0

        self.team1_batter_idx = 0
        self.team2_batter_idx = 0
        
        self.team1_score = 0
        self.team2_score = 0
        self.inning = 1
        self.top_of_inning = True
        self.outs = 0
        self.bases = [0, 0, 0]

    def _get_hit_outcome(self, batter_stats):
        """ Determines outcome of a ball in play based on batter's stats. """
        in_play = {k: v for k, v in batter_stats.items() if k not in ["Walk", "Strikeout"]}
        return random.choices(list(in_play.keys()), weights=list(in_play.values()), k=1)[0]

    def _simulate_at_bat(self, batter, pitcher):
        """ Simulates a single at-bat pitch-by-pitch and fixes count logging. """
        balls, strikes = 0, 0
        pitch_locations = ["high", "low", "inside", "outside"]
        
        print(f"Now batting: {batter['name']} ({batter['position']}, {batter['handedness']})")

        while balls < 4 and strikes < 3:
            pitch_type = random.choices(list(pitcher['pitch_arsenal'].keys()), weights=list(pitcher['pitch_arsenal'].values()))[0]
            
            # Increment pitch count for the correct team
            if self.top_of_inning: self.team1_pitch_count += 1
            else: self.team2_pitch_count += 1

            is_strike_location = random.random() < pitcher['control']
            location = "in the zone" if is_strike_location else random.choice(pitch_locations)
            
            # Simplified swing logic
            swing_prob = 0.8 if is_strike_location else 0.3
            swings = random.random() < swing_prob
            
            outcome_log = ""
            if swings:
                contact = random.random() < 0.7 
                if contact:
                    if strikes < 2 and random.random() < 0.5:
                        strikes += 1
                        outcome_log = f"Foul. Count: {balls}-{strikes}"
                    else: # Ball is in play
                        hit_result = self._get_hit_outcome(batter['stats'])
                        print(f"  In play -> {hit_result}!")
                        return hit_result
                else:
                    strikes += 1
                    outcome_log = f"Swinging Strike. Count: {balls}-{strikes}"
            else: # Batter doesn't swing
                if is_strike_location:
                    strikes += 1
                    outcome_log = f"Called Strike. Count: {balls}-{strikes}"
                else:
                    balls += 1
                    outcome_log = f"Ball. Count: {balls}-{strikes}"
            
            print(f"  Pitch: {pitch_type}, {location}. {outcome_log}")
        
        return "Walk" if balls == 4 else "Strikeout"

    def _advance_runners(self, hit_type):
        """ Advances runners on base according to the type of hit. """
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
        """ Returns a string representation of the runners on base. """
        return f"[{'1B' if self.bases[0] else '_'}]-[{'2B' if self.bases[1] else '_'}]-[{'3B' if self.bases[2] else '_'}]"

    def _check_pitcher_fatigue(self):
        """ Checks if the current pitcher is tired and makes a change from the bullpen. """
        pitching_team_data = (self.team1_name, self.team1_current_pitcher, self.team1_pitch_count, self.team1_pitchers) if self.top_of_inning else (self.team2_name, self.team2_current_pitcher, self.team2_pitch_count, self.team2_pitchers)
        team_name, pitcher, pitch_count, bullpen = pitching_team_data

        if pitch_count > pitcher['stamina']:
            # Simplified bullpen logic: go to a reliever, then closer if available
            new_pitcher = None
            if self.inning >= 8 and 'Closer' in bullpen:
                new_pitcher = bullpen['Closer']
            elif 'Reliever' in bullpen:
                 # In a more complex sim, you might cycle through multiple relievers
                new_pitcher = bullpen['Reliever']

            if new_pitcher and new_pitcher != pitcher:
                if self.top_of_inning: self.team1_current_pitcher = new_pitcher
                else: self.team2_current_pitcher = new_pitcher
                print(f"\n--- Pitching Change for {team_name}: Now pitching, {new_pitcher['name']} ---\n")

    def _simulate_half_inning(self):
        """ Simulates a half-inning with fatigue checks and modern rules. """
        self.outs, self.bases = 0, [0, 0, 0]
        
        batting_team_name, lineup, batter_idx_ref = (self.team2_name, self.team2_lineup, 'team2_batter_idx') if self.top_of_inning else (self.team1_name, self.team1_lineup, 'team1_batter_idx')
        
        inning_half = "Top" if self.top_of_inning else "Bottom"
        print("-" * 50)
        print(f"{inning_half} of Inning {self.inning} | {batting_team_name} batting")
        
        # Display current pitcher info before the inning starts
        pitcher = self.team1_current_pitcher if self.top_of_inning else self.team2_current_pitcher
        pitch_count = self.team1_pitch_count if self.top_of_inning else self.team2_pitch_count
        print(f"Pitching: {pitcher['name']} ({pitcher['handedness']}) - Pitch Count: {pitch_count}")
        print("-" * 50)

        while self.outs < 3:
            self._check_pitcher_fatigue()
            pitcher = self.team1_current_pitcher if self.top_of_inning else self.team2_current_pitcher # Re-assign in case of change
            batter_idx = getattr(self, batter_idx_ref)
            batter = lineup[batter_idx]

            outcome = self._simulate_at_bat(batter, pitcher)
            
            if outcome in ["Strikeout", "Groundout", "Flyout"]: self.outs += 1
            else:
                runs = self._advance_runners(outcome)
                if self.top_of_inning: self.team2_score += runs
                else: self.team1_score += runs
            
            score_str = f"{self.team1_name}: {self.team1_score}, {self.team2_name}: {self.team2_score}"
            print(f"Result: {outcome.ljust(12)} | Outs: {self.outs} | Bases: {self._get_bases_str()} | Score: {score_str}\n")

            setattr(self, batter_idx_ref, (batter_idx + 1) % 9)

    def play_game(self):
        """ Simulates a full game until a winner is decided. """
        print("="*20, "PLAY BALL!", "="*20, "\n")
        while self.inning <= 9 or self.team1_score == self.team2_score:
            self.top_of_inning = True
            self._simulate_half_inning()

            # Walk-off win condition
            if self.inning >= 9 and self.team1_score > self.team2_score: break
                
            self.top_of_inning = False
            self._simulate_half_inning()
            
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

