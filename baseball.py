import random
from teams import TEAMS

class BaseballSimulator:
    """
    A CLI tool to simulate a realistic baseball game using player data.
    """

    def __init__(self, team1_data, team2_data):
        """
        Initializes the game simulator with team data and game state.
        """
        self.team1_name = team1_data["name"]
        self.team2_name = team2_data["name"]
        self.team1_roster = team1_data["players"]
        self.team2_roster = team2_data["players"]
        self.team1_batter_idx = 0
        self.team2_batter_idx = 0
        
        self.team1_score = 0
        self.team2_score = 0
        self.inning = 1
        self.top_of_inning = True
        self.outs = 0
        self.bases = [0, 0, 0]  # Represents first, second, third base

    def _get_at_bat_outcome(self, batter_stats):
        """
        Determines the outcome of a single at-bat based on the batter's stats.
        """
        outcomes = list(batter_stats.keys())
        probabilities = list(batter_stats.values())
        return random.choices(outcomes, weights=probabilities, k=1)[0]

    def _advance_runners(self, hit_type):
        """
        Advances runners on base and calculates runs scored for a given hit.
        """
        runs_scored = 0

        if hit_type == "Single":
            if self.bases[2] == 1:
                runs_scored += 1
                self.bases[2] = 0
            if self.bases[1] == 1:
                self.bases[2] = 1
                self.bases[1] = 0
            if self.bases[0] == 1:
                self.bases[1] = 1
            self.bases[0] = 1

        elif hit_type == "Double":
            if self.bases[2] == 1:
                runs_scored += 1
                self.bases[2] = 0
            if self.bases[1] == 1:
                runs_scored += 1
                self.bases[1] = 0
            if self.bases[0] == 1:
                self.bases[2] = 1
                self.bases[0] = 0
            self.bases[1] = 1

        elif hit_type == "Triple":
            runs_scored += sum(self.bases)
            self.bases = [0, 0, 1]

        elif hit_type == "Home Run":
            runs_scored += sum(self.bases) + 1
            self.bases = [0, 0, 0]

        elif hit_type == "Walk":
            if self.bases == [1, 1, 1]:
                runs_scored += 1
            elif self.bases[0] == 1 and self.bases[1] == 1:
                self.bases[2] = 1
            elif self.bases[0] == 1:
                self.bases[1] = 1
            self.bases[0] = 1
        
        return runs_scored

    def _get_bases_str(self):
        """
        Returns a string representation of the runners on base.
        """
        first = "1B" if self.bases[0] else "_"
        second = "2B" if self.bases[1] else "_"
        third = "3B" if self.bases[2] else "_"
        return f"[{first}]-[{second}]-[{third}]"

    def _simulate_half_inning(self):
        """
        Simulates one half of an inning.
        """
        self.outs = 0
        self.bases = [0, 0, 0]
        current_team_name = self.team2_name if self.top_of_inning else self.team1_name
        
        print("-" * 70)
        inning_half = "Top" if self.top_of_inning else "Bottom"
        print(f"{inning_half} of Inning {self.inning} | {current_team_name} batting")
        print("-" * 70)

        while self.outs < 3:
            if self.top_of_inning:
                batter = self.team2_roster[self.team2_batter_idx]
            else:
                batter = self.team1_roster[self.team1_batter_idx]

            outcome = self._get_at_bat_outcome(batter['stats'])
            
            if outcome in ["Strikeout", "Groundout", "Flyout"]:
                self.outs += 1
            else:
                runs = self._advance_runners(outcome)
                if runs > 0:
                    if self.top_of_inning:
                        self.team2_score += runs
                    else:
                        self.team1_score += runs
            
            score_str = f"{self.team1_name}: {self.team1_score}, {self.team2_name}: {self.team2_score}"
            batter_str = f"At Bat: {batter['name']} ({batter['position']})".ljust(30)
            outcome_str = f"{outcome}!".ljust(12)
            
            print(f"{batter_str} | {outcome_str} | Outs: {self.outs} | Bases: {self._get_bases_str()} | Score: {score_str}")

            if self.top_of_inning:
                self.team2_batter_idx = (self.team2_batter_idx + 1) % 9
            else:
                self.team1_batter_idx = (self.team1_batter_idx + 1) % 9
        
        print()

    def play_game(self):
        """
        Simulates a full 9-inning (or more) baseball game.
        """
        print("="*15, "PLAY BALL!", "="*15)
        while self.inning <= 9 or self.team1_score == self.team2_score:
            self.top_of_inning = True
            self._simulate_half_inning()

            if self.inning >= 9 and self.team1_score > self.team2_score:
                break
                
            self.top_of_inning = False
            self._simulate_half_inning()
            
            self.inning += 1

        print("="*15, "GAME OVER", "="*15)
        print("\nFinal Score:")
        print(f"{self.team1_name}: {self.team1_score}")
        print(f"{self.team2_name}: {self.team2_score}")

        if self.team1_score > self.team2_score:
            print(f"\n{self.team1_name} wins!")
        else:
            print(f"\n{self.team2_name} wins!")

if __name__ == "__main__":
    # You can choose different teams by changing these keys
    home_team_key = "SF_SEALS"
    away_team_key = "OAK_OAKS"
    
    game = BaseballSimulator(
        team1_data=TEAMS[home_team_key], 
        team2_data=TEAMS[away_team_key]
    )
    game.play_game()

