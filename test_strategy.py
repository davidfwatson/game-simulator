"""Managerial decisions and the situations that call for them."""
import random
import unittest
from unittest.mock import patch

from baseball import BaseballSimulator
from teams import TEAMS


def new_game(seed=1):
    return BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=seed)


class TestStrategyRandomness(unittest.TestCase):
    def test_setup_and_managerial_choices_leave_pitch_randomness_alone(self):
        game = new_game()
        state = random.Random(1).getstate()
        self.assertEqual(game.game_rng.getstate(), state)
        game.inning = 8
        game.bases[0] = game.team2_lineup[0]['legal_name']
        pitcher = game._pitching_side()[2]
        game._bunt_plan(game.team2_lineup[8])
        game._decide_steal_attempt(0, 1)
        game._manage_offensive_substitutions(8, pitcher)
        game._manage_defensive_substitutions()
        game._half_pitcher_entry = {}
        game._batters_faced[pitcher['legal_name']] = 20
        game._manage_pitching_change()
        game._manage_between_innings()
        self.assertEqual(game.game_rng.getstate(), state)

    def test_a_safe_pickoff_throw_does_not_reshuffle_the_next_pitch(self):
        game = new_game()
        game.bases[0] = game.team2_lineup[0]['legal_name']
        pitcher = game._pitching_side()[2]
        state = game.game_rng.getstate()
        events = []
        with patch.object(game.strategy_rng, 'random', return_value=0.9):
            game._record_pickoff_throw(events, 0, 0, pitcher)
        self.assertEqual(game.game_rng.getstate(), state)
        self.assertEqual(game.outs, 0)
        self.assertEqual(len(events), 1)

    def test_strategy_and_texture_streams_are_seeded_independently(self):
        game, replay, other = new_game(), new_game(), new_game(2)
        self.assertEqual(game.strategy_rng.getstate(), replay.strategy_rng.getstate())
        self.assertEqual(game.texture_rng.getstate(), replay.texture_rng.getstate())
        self.assertNotEqual(game.strategy_rng.getstate(), other.strategy_rng.getstate())
        game.strategy_rng.random()
        game.texture_rng.random()
        self.assertEqual(game.game_rng.getstate(), replay.game_rng.getstate())


if __name__ == '__main__':
    unittest.main()
