"""The last movement determines whether an uncaught-third-strike batter is safe."""

import unittest

from renderers.base import GameRenderer


class TestBatterDestinations(unittest.TestCase):
    def movement(self, end, *, runner_id=7, is_out=False, event_index=None):
        entry = {
            'details': {'runner': {'id': runner_id}},
            'movement': {'end': end, 'isOut': is_out},
        }
        if event_index is not None:
            entry['details']['playIndex'] = event_index
        return entry

    def destination(self, movements, batter=None):
        return GameRenderer._batter_safe_destination({
            'matchup': {'batter': {'id': 7} if batter is None else batter},
            'runners': movements,
        })

    def test_missing_batter_id_cannot_match_an_unidentified_runner(self):
        runner = self.movement('1B')
        runner['details']['runner'].pop('id')
        self.assertIsNone(self.destination([runner], batter={'fullName': 'Batter'}))

    def test_last_document_movement_selects_the_final_safe_base(self):
        self.assertEqual(self.destination([
            self.movement('1B'), self.movement('2B'), self.movement('3B'),
        ]), 'third')

    def test_event_indexes_take_priority_over_unsorted_document_order(self):
        self.assertEqual(self.destination([
            self.movement('score', event_index=8),
            self.movement('1B', event_index=5),
            self.movement('2B', event_index=6),
        ]), 'home')

    def test_later_tag_out_overrides_an_earlier_safe_base(self):
        for movements in (
            [self.movement('1B'), self.movement(None, is_out=True)],
            [self.movement(None, is_out=True, event_index=6),
             self.movement('1B', event_index=5)],
        ):
            with self.subTest(movements=movements):
                self.assertIsNone(self.destination(movements))

    def test_other_runners_do_not_override_the_batters_destination(self):
        self.assertEqual(self.destination([
            self.movement('2B', event_index=5),
            self.movement(None, runner_id=8, is_out=True, event_index=9),
        ]), 'second')
        self.assertIsNone(self.destination([self.movement('1B', runner_id=8)]))

    def test_same_event_uses_the_last_document_movement(self):
        self.assertEqual(self.destination([
            self.movement('1B', event_index=5), self.movement('2B', event_index=5),
        ]), 'second')


if __name__ == '__main__':
    unittest.main()
