import re
import unittest
import random
import io
from copy import deepcopy
from contextlib import redirect_stdout
from unittest.mock import patch
from baseball import BaseballSimulator
from renderers import NarrativeRenderer
from teams import TEAMS

class TestBaseballRealism(unittest.TestCase):
    def setUp(self):
        """Set up a new game for each test with a fixed random seed."""
        random.seed(42)

    def test_impossible_pitching_change(self):
        """Verify that a team cannot make a pitching change while batting."""
        home_team = deepcopy(TEAMS["BAY_BOMBERS"])
        away_team = deepcopy(TEAMS["PC_PILOTS"])

        # Force a situation where a pitching change is likely
        home_team['players'][9]['stamina'] = 1
        away_team['players'][9]['stamina'] = 1

        game = BaseballSimulator(home_team, away_team)
        game.play_game()

        renderer = NarrativeRenderer(game.gameday_data, seed=42)
        log = renderer.render()

        # Check for illegal pitching change for the away team (Pacific City)
        if "Top of Inning 9" in log and "Bottom of Inning 9" in log:
            pacific_city_batting_log = log.split("Top of Inning 9")[1].split("Bottom of Inning 9")[0]
            self.assertNotIn(f"--- Pitching Change for {away_team['name']}", pacific_city_batting_log)

        # Check for illegal pitching change for the home team (Bay Area)
        for i in range(1, 10):
            if f"Bottom of Inning {i}" in log and f"Top of Inning {i+1}" in log:
                bottom_inning_log = log.split(f"Bottom of Inning {i}")[1].split(f"Top of Inning {i+1}")[0]
                self.assertNotIn(f"--- Pitching Change for {home_team['name']}", bottom_inning_log)

    def test_for_complete_games(self):
        """Test for an unrealistically high number of complete games."""
        complete_games = 0
        num_simulations = 20

        for i in range(num_simulations):
            game = BaseballSimulator(deepcopy(TEAMS["BAY_BOMBERS"]), deepcopy(TEAMS["PC_PILOTS"]), game_seed=i)
            game.play_game()

            team1_pitchers_used = len([p for p, count in game.pitch_counts.items() if count > 0 and p in game.team1_pitcher_stats])
            team2_pitchers_used = len([p for p, count in game.pitch_counts.items() if count > 0 and p in game.team2_pitcher_stats])

            if team1_pitchers_used == 1 or team2_pitchers_used == 1:
                complete_games += 1

        self.assertLess(complete_games, num_simulations * 0.1, "Unrealistically high number of complete games found.")

    def test_event_variety(self):
        """Check for a variety of game events like walks, errors, and double plays."""
        events = {"Walk": 0, "Error": 0, "Double Play": 0}
        num_simulations = 20

        for i in range(num_simulations):
            game = BaseballSimulator(deepcopy(TEAMS["BAY_BOMBERS"]), deepcopy(TEAMS["PC_PILOTS"]), game_seed=i)
            game.play_game()

            renderer = NarrativeRenderer(game.gameday_data, seed=i)
            log = renderer.render()

            if "draws a walk" in log: events["Walk"] += 1
            if re.search(r"\b(an error by|on the error|going to be an error|error on)\b", log, re.I): events["Error"] += 1
            if "double play" in log.lower() or "Double Play" in log: events["Double Play"] += 1

        self.assertGreater(events["Walk"], 0, "No walks were recorded in the simulations.")
        self.assertGreater(events["Error"], 0, "No errors were recorded in the simulations.")
        self.assertGreater(events["Double Play"], 0, "No double plays were recorded in the simulations.")

class TestStealMovements(unittest.TestCase):
    def test_safe_steals_vary_throws_and_slides_without_changing_game_draws(self):
        game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=42)
        runner = {'id': 1, 'legal_name': 'Otis Runner'}
        game_state, no_throw_rates = game.game_rng.getstate(), {}
        for base in (2, 3):
            moves = [game._steal_movement(runner, base, False) for _ in range(2000)]
            self.assertEqual({m['throw'] for m in moves}, {'none', 'not_in_time'})
            no_throw_rates[base] = sum(m['throw'] == 'none' for m in moves) / len(moves)
            self.assertGreater(no_throw_rates[base], 0.05)
            self.assertLess(no_throw_rates[base], 0.5)
            for throw in ('none', 'not_in_time'):
                self.assertEqual({m['slide'] for m in moves if m['throw'] == throw}, {True, False})
        self.assertGreater(no_throw_rates[3], no_throw_rates[2])
        self.assertEqual(game.game_rng.getstate(), game_state)

    def test_caught_stealing_always_has_a_throw_in_time(self):
        game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=42)
        runner = {'id': 1, 'legal_name': 'Otis Runner'}
        for base in (2, 3):
            moves = [game._steal_movement(runner, base, True) for _ in range(200)]
            self.assertTrue(all(m['isOut'] and m['throw'] == 'in_time' for m in moves))
            self.assertEqual({m['slide'] for m in moves}, {True, False})


class TestRelieverSelection(unittest.TestCase):
    def test_reliever_who_finishes_the_inning_can_leave_before_three_batters(self):
        for top in (True, False):
            with self.subTest(top=top):
                game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
                game.inning, game.top_of_inning = 6, top
                prefix, starter, _, _ = game._pitching_side()

                def at_bat(batter, pitcher):
                    name = pitcher['legal_name']
                    game.pitch_counts[name] += 3
                    if name == starter and game.outs == 1:
                        game.pitch_counts[name] = game._pitch_budget[name] + 10
                    return 'Strikeout', None, []

                with patch.object(game, '_simulate_at_bat', side_effect=at_bat):
                    game._simulate_half_inning()
                plays = game.gameday_data['liveData']['plays']['allPlays']
                reliever = getattr(game, f'{prefix}_current_pitcher_name')
                self.assertEqual([play['matchup']['pitcher']['fullName'] for play in plays],
                                 [starter, starter, reliever])
                self.assertNotEqual(reliever, starter)
                self.assertEqual([play['count']['outs'] for play in plays], [1, 2, 3])
                self.assertEqual(game._batters_faced[reliever], 1)
                self.assertTrue(game._entered_mid_inning[reliever])

                game.inning, game.outs = 7, 0
                with patch.object(game.game_rng, 'random', return_value=0.0):
                    game._manage_between_innings()
                replacement = getattr(game, f'{prefix}_current_pitcher_name')
                self.assertNotEqual(replacement, reliever)
                self.assertEqual(game._entered_inning[replacement], 7)
                self.assertFalse(game._entered_mid_inning[replacement])

    def test_closer_is_available_for_close_games_in_extra_innings(self):
        game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
        for inning in (9, 10, 12):
            for top in (True, False):
                for lead in (0, 1, 3):
                    with self.subTest(inning=inning, top=top, lead=lead):
                        game.inning, game.top_of_inning = inning, top
                        game.team1_score = 4 + (lead if top else 0)
                        game.team2_score = 4 + (0 if top else lead)
                        prefix, _, stats, bullpen = game._pitching_side()
                        chosen = game._pick_reliever(prefix, bullpen)
                        self.assertEqual(getattr(game, f'{prefix}_pitcher_stats')[chosen]['type'], 'Closer')


if __name__ == '__main__':
    unittest.main()
