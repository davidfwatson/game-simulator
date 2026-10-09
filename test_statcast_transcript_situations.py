"""Statcast regressions for unusual outcomes found in the transcript corpus."""

import copy
import unittest

from renderers import StatcastRenderer
import test_transcript_situations


class TestStatcastTranscriptSituations(unittest.TestCase):
    def game(self, **kwargs):
        return test_transcript_situations.TestTranscriptSituations().game(**kwargs)

    def test_pitchouts_are_visible_for_both_supported_pitch_codes(self):
        for code in ('P', 'B'):
            with self.subTest(code=code):
                data, play, event = self.game(outcome='Single', code='X', reaches=True)
                event['hitData'] = {'location': 'CF'}
                pitchout = copy.deepcopy(event)
                pitchout.pop('hitData')
                pitchout['details'].update(code=code, description='Pitchout')
                pitchout['count'] = {'balls': 0, 'strikes': 1}
                play['playEvents'].insert(0, pitchout)
                text = StatcastRenderer(data).render()
                self.assertEqual(1, text.count('  Pitchout:'))
                self.assertIn('  In play:', text)

    def test_foul_bunt_strikeout_never_becomes_a_swinging_strikeout(self):
        for flagged, description in ((True, 'Foul'), (False, 'bUnT FoUl')):
            with self.subTest(flagged=flagged, description=description):
                data, play, event = self.game(code='F')
                event['isBunt'] = flagged
                event['details']['description'] = description
                text = StatcastRenderer(data).render()
                self.assertIn('  Foul bunt:', text)
                self.assertIn('Result: Pinky Slauson strikes out on a foul bunt.', text)
                self.assertNotIn('strikes out swinging', text)
                self.assertNotIn('Swinging strike:', text)

    def test_missed_bunt_strikeout_keeps_the_bunt_context(self):
        for flagged, description in ((True, 'Swinging Strike'), (False, 'Missed Bunt')):
            with self.subTest(flagged=flagged, description=description):
                data, play, event = self.game(code='S')
                event['isBunt'] = flagged
                event['details']['description'] = description
                text = StatcastRenderer(data).render()
                self.assertIn('  Missed bunt:', text)
                self.assertIn('Result: Pinky Slauson strikes out on a missed bunt.', text)
                self.assertNotIn('Swinging strike:', text)

    def test_intentional_walk_aliases_are_explicit_without_pitches(self):
        for outcome, event_type in (
            ('Intent Walk', 'intent_walk'),
            ('Intentional Walk', 'intentional_walk'),
            ('Walk', 'intent_walk'),
            ('Walk', 'intentional_walk'),
        ):
            with self.subTest(outcome=outcome, event_type=event_type):
                data, play, event = self.game(outcome=outcome, reaches=True)
                play['result']['eventType'] = event_type
                play['playEvents'] = []
                text = StatcastRenderer(data).render()
                self.assertIn('Result: Pinky Slauson is intentionally walked.', text)
                self.assertNotIn('four pitches', text)
                self.assertNotIn('Result: Walk', text)

    def test_uncaught_third_strike_reports_the_batters_actual_destination(self):
        for end, expected in (
            ('1B', 'reaches first safely'),
            ('2B', 'reaches second safely'),
            ('3B', 'reaches third safely'),
            ('score', 'comes around to score'),
        ):
            with self.subTest(end=end):
                data, play, event = self.game(reaches=True)
                play['runners'][0]['movement']['end'] = end
                text = StatcastRenderer(data).render()
                self.assertIn(f'Result: Pinky Slauson strikes out but {expected}.', text)
                self.assertNotIn('strikes out swinging', text)
                if end != '1B':
                    self.assertNotIn('reaches first safely', text)

    def test_another_runner_reaching_safely_does_not_rescue_a_retired_batter(self):
        data, play, event = self.game()
        other = copy.deepcopy(play['runners'][0])
        other['details']['runner'] = {'id': 999999, 'fullName': 'Other Runner'}
        other['movement'].update(isOut=False, end='2B')
        play['runners'].append(other)
        text = StatcastRenderer(data).render()
        self.assertIn('Result: Pinky Slauson strikes out swinging.', text)
        self.assertNotIn('reaches second safely', text)


if __name__ == '__main__':
    unittest.main()
