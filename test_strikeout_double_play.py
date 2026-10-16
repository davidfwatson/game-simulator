"""Strike three precedes the caught-stealing tag in a strikeout double play."""
import unittest
from unittest.mock import patch

from baseball import BaseballSimulator
from renderers import NarrativeRenderer
from teams import TEAMS


class TestStrikeoutDoublePlay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = []
        for seed in (26, 81, 146, 213):
            game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=seed)
            game.play_game()
            cls.games.append((seed, game.gameday_data))

    def test_both_outs_are_recorded_in_order_on_their_own_events(self):
        for seed, data in self.games:
            play = next(p for p in data['liveData']['plays']['allPlays']
                        if p['result']['event'] == 'Strikeout Double Play')
            with self.subTest(seed=seed):
                outs = [r for r in play['runners'] if r['movement']['isOut']]
                self.assertEqual(len(outs), 2)
                batter = next(r for r in outs if r['details']['runner']['id'] == play['matchup']['batter']['id'])
                runner = next(r for r in outs if r is not batter)
                self.assertEqual(batter['movement']['outNumber'], play['count']['outs'] - 1)
                self.assertEqual(runner['movement']['outNumber'], play['count']['outs'])
                pitch = next(e for e in reversed(play['playEvents']) if e.get('isPitch'))
                self.assertEqual(batter['details']['playIndex'], pitch['index'])
                self.assertGreater(runner['details']['playIndex'], pitch['index'])
                half = [p for p in data['liveData']['plays']['allPlays']
                        if (p['about']['inning'], p['about']['isTopInning'])
                        == (play['about']['inning'], play['about']['isTopInning'])]
                self.assertEqual(sum(r['movement']['isOut'] for p in half for r in p['runners']), 3)
                self.assertIsNone(NarrativeRenderer(data)._struck_out_the_side(half))

    def test_strike_three_is_a_complete_sentence_before_the_throw(self):
        for seed, data in self.games:
            renderer = NarrativeRenderer(data, seed=seed)
            calls = {}
            original = renderer._render_steal_event

            def record(event):
                text = original(event)
                calls[id(event)] = text
                return text

            with patch.object(renderer, '_render_steal_event', side_effect=record):
                lines = renderer.render().splitlines()
            play = next(p for p in data['liveData']['plays']['allPlays']
                        if p['result']['event'] == 'Strikeout Double Play')
            action = play['playEvents'][-1]
            low, high = renderer._play_line_map[play['about']['atBatIndex']]
            text = '\n'.join(lines[low:high])
            with self.subTest(seed=seed):
                self.assertIn(calls[id(action)], text)
                before_throw = text[:text.index(calls[id(action)])].rstrip()
                self.assertIn(before_throw[-1], '.!?', before_throw)


if __name__ == '__main__':
    unittest.main()
