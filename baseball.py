import random
import time

class BaseballSimulator:
    """
    A CLI tool to simulate a realistic baseball game.
    """

    def __init__(self, team1_name="Home", team2_name="Away"):
        """
        Initializes the game simulator with team names and game state.
        """
        self.team1_name = team1_name
        self.team2_name = team2_name
        self.team1_score = 0
        self.team2_score = 0
        self.inning = 1
        self.top_of_inning = True
        self.outs = 0
        self.bases = [0, 0, 0]  # Represents first, second, third base

        # Realistic probabilities for at-bat outcomes
        self.outcomes = {
            "Single": 0.150,
            "Double": 0.050,
            "Triple": 0.005,
            "Home Run": 0.030,
            "Walk": 0.080,
            "Strikeout": 0.220,
            "Groundout": 0.250,
            "Flyout": 0.215,
        }

    def _get_at_bat_outcome(self):
        """
        Determines the outcome of a single at-bat based on weighted probabilities.
        """
        outcomes = list(self.outcomes.keys())
        probabilities = list(self.outcomes.values())
        return random.choices(outcomes, weights=probabilities, k=1)[0]

    def _advance_runners(self, hit_type):
        """
        Advances runners on base and calculates runs scored for a given hit.
        """
        runs_scored = 0

        if hit_type == "Single":
            # Simple advancement: each runner moves up one base.
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
            # If bases are loaded, a walk scores a run.
            if self.bases == [1, 1, 1]:
                runs_scored += 1
            # Otherwise, advance runners only if forced.
            elif self.bases[0] == 1 and self.bases[1] == 1:
                self.bases[2] = 1
            elif self.bases[0] == 1:
                self.bases[1] = 1
            self.bases[0] = 1
        
        return runs_scored

    def _print_bases(self):
        """
        Prints a visual representation of the runners on base.
        """
        base_str = "Bases: [{}]-[{}]-[{}]"
        first = "1B" if self.bases[0] else " "
        second = "2B" if self.bases[1] else " "
        third = "3B" if self.bases[2] else " "
        print(base_str.format(first, second, third))


    def _simulate_half_inning(self):
        """
        Simulates one half of an inning.
        """
        self.outs = 0
        self.bases = [0, 0, 0]
        current_team = self.team2_name if self.top_of_inning else self.team1_name
        
        print("-" * 30)
        inning_half = "Top" if self.top_of_inning else "Bottom"
        print(f"{inning_half} of Inning {self.inning} | {current_team} batting")
        print("-" * 30)

        while self.outs < 3:
            time.sleep(0.5) # Pause for readability
            outcome = self._get_at_bat_outcome()
            
            print(f"At bat... {outcome}!")

            if outcome in ["Strikeout", "Groundout", "Flyout"]:
                self.outs += 1
            else:
                runs = self._advance_runners(outcome)
                if runs > 0:
                    print(f"*** {runs} run(s) score! ***")
                    if self.top_of_inning:
                        self.team2_score += runs
                    else:
                        self.team1_score += runs
            
            print(f"Outs: {self.outs}")
            self._print_bases()
            print(f"Score: {self.team1_name}: {self.team1_score}, {self.team2_name}: {self.team2_score}\n")

    def play_game(self):
        """
        Simulates a full 9-inning (or more) baseball game.
        """
        print("="*10, "PLAY BALL!", "="*10)
        while self.inning <= 9 or self.team1_score == self.team2_score:
            self.top_of_inning = True
            self._simulate_half_inning()

            # The game can end after the top of the 9th if the home team is winning
            if self.inning >= 9 and self.team1_score > self.team2_score:
                break
                
            self.top_of_inning = False
            self._simulate_half_inning()
            
            self.inning += 1

        print("="*10, "GAME OVER", "="*10)
        print("\nFinal Score:")
        print(f"{self.team1_name}: {self.team1_score}")
        print(f"{self.team2_name}: {self.team2_score}")

        if self.team1_score > self.team2_score:
            print(f"\n{self.team1_name} wins!")
        else:
            print(f"\n{self.team2_name} wins!")


if __name__ == "__main__":
    # You can customize team names here
    game = BaseballSimulator(team1_name="Giants", team2_name="Dodgers")
    game.play_game()
