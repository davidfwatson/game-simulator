import unittest
import random
import io
import re
from baseball import BaseballSimulator
from teams import TEAMS

class TestRealism(unittest.TestCase):
    def setUp(self):
        """Set up a new game for each test with a fixed random seed."""
        random.seed(42)
        self.home_team = TEAMS["BAY_BOMBERS"]
        self.away_team = TEAMS["PC_PILOTS"]

        # Run the game and get the log from the simulator's output buffer
        game = BaseballSimulator(self.home_team, self.away_team, verbose_phrasing=True)
        game.play_game()
        self.log = "\n".join(game.output_lines)

    def test_quantized_velocities(self):
        """Test if pitch velocities are too uniform or 'quantized'."""
        velocities = re.findall(r'\((\d{2,3}(?:\.\d)?) mph\)', self.log)
        self.assertGreater(len(velocities), 0, "No velocities found in game log.")
        unique_velocities = set(map(float, velocities))
        self.assertGreater(len(unique_velocities), 10, "Pitch velocities appear quantized and not varied enough.")

    def test_repetitive_phrasing(self):
        """Test for repetitive phrasing in play-by-play output."""
        pitch_lines = re.findall(r'^\s*Pitch:.*', self.log, re.MULTILINE)
        template = r"\s*Pitch: [\w\s-]+ \(\d{2,3}(?:\.\d)? mph\), .*?\."
        matching_lines = [line for line in pitch_lines if re.match(template, line)]
        self.assertGreater(len(pitch_lines), 0, "No pitch lines found in the log.")
        self.assertGreater(len(matching_lines), len(pitch_lines) * 0.9, "Play-by-play phrasing is not descriptive enough.")


    def test_abstract_outcomes(self):
        """Test for abstract outcomes instead of specific scorer's notation."""
        self.assertFalse(re.search(r'Result: Groundout\n', self.log), "Abstract 'Groundout' found. Use scorer's notation.")
        self.assertFalse(re.search(r'Result: Flyout\n', self.log), "Abstract 'Flyout' found. Use scorer's notation.")
        has_fielder_credit = re.search(r'(to [A-Z][a-z]+|\([1-9-]+\)|\(F\d+\))', self.log)
        self.assertIsNotNone(has_fielder_credit, "Outcomes lack specific fielder information.")

    def test_box_state_ui(self):
        """Test for the presence of the unrealistic '[1B]-[2B]-[3B]' base state UI."""
        self.assertNotIn("[1B]-[2B]-[3B]", self.log, "Unrealistic box-state UI is present.")

    def test_extra_innings_banner(self):
        """Test for unrealistic extra-innings banner text."""
        for i in range(20): # Increased range to better find an extra inning game
            random.seed(i)
            game = BaseballSimulator(TEAMS["BAY_BOMBERS"], TEAMS["PC_PILOTS"])
            game.play_game()
            log = "\n".join(game.output_lines)
            if "Inning 10" in log:
                self.assertNotIn("--- Extra Innings: Runner placed on second base ---", log, "Unrealistic extra-innings banner found.")
                return

    def test_nicknames_in_substitutions(self):
        """Test for the use of nicknames in substitution announcements."""
        sub_lines = re.findall(r'--- Pitching Change for.*', self.log)
        pitchers_with_nicknames = [p for p in self.home_team['players'] + self.away_team['players'] if p['position'] == 'P' and p.get('nickname')]
        self.assertTrue(len(pitchers_with_nicknames) > 0, "No pitchers with nicknames found for testing.")
        for line in sub_lines:
            for pitcher in pitchers_with_nicknames:
                self.assertNotIn(f"'{pitcher['nickname']}'", line)

    def test_game_context_missing(self):
        """Test if essential game context like umpires, venue, and weather is missing."""
        self.assertIn("Umpires:", self.log, "Umpire information is missing from the pre-game summary.")
        self.assertIn("Weather:", self.log, "Weather information is missing from the pre-game summary.")
        self.assertIn("Venue:", self.log, "Venue information is missing from the pre-game summary.")

    def test_bracketed_ui_flag(self):
        """Test that the bracketed UI flag correctly changes the base runner display."""
        game_bracketed = BaseballSimulator(self.home_team, self.away_team, use_bracketed_ui=True)
        game_bracketed.play_game()
        log_bracketed = "\n".join(game_bracketed.output_lines)
        self.assertIn("[", log_bracketed, "Bracketed UI not found when flag is enabled.")

        game_named = BaseballSimulator(self.home_team, self.away_team, use_bracketed_ui=False)
        game_named.play_game()
        log_named = "\n".join(game_named.output_lines)
        self.assertNotIn("[", log_named, "Bracketed UI found when flag is disabled.")

    def test_simulation_realism_over_multiple_games(self):
        """Run the simulation multiple times to check for realism issues."""
        num_games = 20
        totals = {"walks": 0, "hbps": 0, "dps": 0, "triples": 0, "go_2_3": 0, "go_3u": 0, "flyouts": 0, "popouts": 0}
        for i in range(num_games):
            random.seed(i)
            game = BaseballSimulator(self.home_team, self.away_team)
            game.play_game()
            log = "\n".join(game.output_lines)
            totals["walks"] += log.count("Result: Walk")
            totals["hbps"] += log.count("Hit by Pitch")
            totals["dps"] += log.count("Double Play")
            totals["triples"] += log.count("Result: Triple")
            totals["go_2_3"] += len(re.findall(r'Groundout to Catcher \(2-3\)', log))
            totals["go_3u"] += len(re.findall(r'Groundout to 1B \(3U\)', log))
            totals["flyouts"] += len(re.findall(r'Flyout to (LF|CF|RF)', log))
            totals["popouts"] += len(re.findall(r'Pop out to (P|C|1B|2B|3B|SS)', log))

        self.assertGreater(totals["walks"], 10)
        self.assertGreater(totals["dps"], 5)
        self.assertLess(totals["triples"], 10)
        self.assertLess(totals["go_2_3"], 3)
        self.assertGreater(totals["go_3u"], 2)
        self.assertGreater(totals["popouts"], 2)
        self.assertGreater(totals["flyouts"], 2)

    def test_no_wp_or_pb_with_bases_empty(self):
        """Test that a wild pitch or passed ball does not occur when the bases are empty."""
        for i in range(20):
            random.seed(i)
            game = BaseballSimulator(self.home_team, self.away_team)
            game.play_game()
            log = "\n".join(game.output_lines)
            lines = log.split('\n')
            last_bases_state = ""
            for line in lines:
                if line.strip().startswith("Result:"):
                    if "Bases: " in line:
                        last_bases_state = line.split("Bases: ")[1].split(" | ")[0]
                if "Wild Pitch!" in line or "Passed Ball!" in line:
                    self.assertNotEqual(last_bases_state, "Bases empty")

if __name__ == '__main__':
    unittest.main()