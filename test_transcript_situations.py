"""Whole-render regressions for unusual plays present in the new transcripts."""
import copy
import json
from pathlib import Path
import unittest

from commentary import GAME_CONTEXT
from renderers import NarrativeRenderer, StatcastRenderer


class TestTranscriptSituations(unittest.TestCase):
    def game(self, outcome='Strikeout', code='S', reaches=False):
        data = json.loads((Path(__file__).parent / 'test_fixture_pbp_example_1.json').read_text())
        play = data['liveData']['plays']['allPlays'][0]
        data['liveData']['plays']['allPlays'] = [play]
        play['commentaryRng'] = {'play_start': {'color': [99] * 20},
                                 'play_outcome': {'play': [0] * 20, 'flow': [0] * 20}}
        play['result'].update(event=outcome, eventType=outcome.lower().replace(' ', '_'))
        play['count']['outs'] = 0 if reaches else 1
        runner = play['runners'][0]
        runner['movement'].update(end='1B' if reaches else None,
                                  outBase=None if reaches else '1B', isOut=not reaches)
        runner['details'].update(event=outcome, eventType=play['result']['eventType'])
        event = copy.deepcopy(play['playEvents'][-1])
        event['details'].update(code=code, description='Swinging Strike' if code == 'S' else 'Foul',
                                eventType='pitch')
        event['count'] = {'balls': 0, 'strikes': 2}
        event['commentaryRng'] = {'event': {name: [0] * 20 for name in ('play', 'pitch', 'flow', 'color')}}
        event.pop('hitData', None)
        play['playEvents'] = [event]
        return data, play, event

    def narrative_play(self, data):
        renderer = NarrativeRenderer(data)
        rendered = renderer.render()
        lo, hi = renderer._play_line_map[0]
        return '\n'.join(rendered.splitlines()[lo:hi])

    def test_dropped_third_strike_does_not_retire_the_batter(self):
        for wild_pitch in (False, True):
            with self.subTest(wild_pitch=wild_pitch):
                data, play, event = self.game(reaches=True)
                if wild_pitch:
                    action = copy.deepcopy(event)
                    action.update(isPitch=False)
                    action['details'].update(code='X', eventType='wild_pitch',
                                             description='The third strike gets away from the catcher')
                    play['playEvents'].append(action)
                text = self.narrative_play(data)
                self.assertTrue('safe at first' in text or 'is aboard' in text, text)
                self.assertNotIn('for out number', text)
                self.assertNotIn('goes down', text)
                if wild_pitch:
                    self.assertIn('strikeout on a wild pitch', text)
                else:
                    self.assertNotIn('wild pitch', text)
                statcast = StatcastRenderer(data).render()
                self.assertIn('reaches first', statcast)

    def test_strikeout_with_other_runner_safe_does_not_award_batter_first(self):
        data, play, event = self.game()
        other = copy.deepcopy(play['runners'][0])
        other['details']['runner'] = {'id': 999999, 'fullName': 'Other Runner'}
        other['movement'].update(isOut=False, end='1B')
        play['runners'].append(other)
        text = self.narrative_play(data)
        self.assertIn('for out number one', text)
        self.assertNotIn('safe at first', text)

    def test_uncaught_third_strike_uses_the_actual_safe_destination(self):
        for end, expected in [('2B', 'reaches second safely'),
                              ('3B', 'reaches third safely'),
                              ('score', 'comes around to score')]:
            with self.subTest(end=end):
                data, play, event = self.game(reaches=True)
                play['runners'][0]['movement']['end'] = end
                text = self.narrative_play(data)
                self.assertIn(expected, text)
                self.assertNotIn('safe at first', text)
                self.assertNotIn('for out number', text)

    def test_earlier_wild_pitch_does_not_explain_a_later_dropped_strike(self):
        data, play, event = self.game(reaches=True)
        action = copy.deepcopy(event)
        action['isPitch'] = False
        action['details'].update(eventType='wild_pitch', description='An earlier pitch gets away')
        play['playEvents'].insert(0, action)
        text = self.narrative_play(data)
        self.assertIn('safe at first', text)
        self.assertNotIn('strikeout on a wild pitch', text)
        self.assertLess(text.index('An earlier pitch gets away'), text.index('Strike three'))

    def test_caught_stealing_after_strike_three_keeps_the_out_order(self):
        data, play, event = self.game()
        play['count']['outs'] = 3
        play['runners'][0]['movement']['outNumber'] = 2
        other = copy.deepcopy(play['runners'][0])
        other['details']['runner'] = {'id': 999999, 'fullName': 'Other Runner'}
        other['movement'].update(start='1B', end=None, outBase='2B', outNumber=3)
        play['runners'].append(other)
        action = copy.deepcopy(event)
        action['isPitch'] = False
        action['details'].update(code='X', eventType='caught_stealing',
                                 description='Caught Stealing 2B')
        play['playEvents'].append(action)
        text = self.narrative_play(data)
        self.assertIn('for out number two', text)
        self.assertNotIn('strikes out to end the inning', text)
        self.assertEqual(text.lower().count('swung on and missed for strike three'), 1, text)
        self.assertLess(text.index('for out number two'), text.lower().index('caught stealing'))

    def test_intentional_walk_without_pitches_is_narrated(self):
        for event_name, event_type in [('Intent Walk', 'intent_walk'), ('Walk', 'intent_walk')]:
            data, play, event = self.game(outcome=event_name, reaches=True)
            play['result']['eventType'] = event_type
            play['playEvents'] = []
            text = self.narrative_play(data)
            self.assertIn("they're going to intentionally walk Pinky Slauson", text)
            self.assertNotIn('four pitches', text)

    def test_bunt_single_requires_bunt_data(self):
        for is_bunt in (False, True):
            data, play, event = self.game(outcome='Single', code='X', reaches=True)
            event['isBunt'] = is_bunt
            event['details']['description'] = 'In play, single'
            event['hitData'] = {'location': '3B', 'trajectory': 'bunt' if is_bunt else 'ground_ball'}
            # The old generic single pool could incorrectly call this a bunt.
            play['commentaryRng']['play_outcome']['play'] = [6, 0]
            text = self.narrative_play(data)
            self.assertEqual('bunt' in text.lower(), is_bunt, text)
            statcast = StatcastRenderer(data).render()
            self.assertEqual('bunt single' in statcast.lower(), is_bunt, statcast)
        self.assertFalse(any('bunt' in text.lower()
                             for text in GAME_CONTEXT['narrative_templates']['Single']['default']))

    def test_bunt_foul_and_miss_use_flags_not_description_spelling(self):
        for code in ('F', 'S'):
            data, play, event = self.game(outcome='Single', code='X', reaches=True)
            event['hitData'] = {'location': 'CF'}
            setup = copy.deepcopy(event)
            setup.pop('hitData')
            setup['isBunt'] = True
            setup['count'] = {'balls': 0, 'strikes': 0}
            setup['details'].update(code=code, description='Foul' if code == 'F' else 'Swinging Strike')
            play['playEvents'].insert(0, setup)
            text = self.narrative_play(data)
            self.assertIn('bunt', text.lower())
            self.assertIn('oh and one', text.lower())

    def test_two_strike_foul_bunt_is_strike_three(self):
        for flagged, description in [(True, 'Foul'), (False, 'bUnT FoUl')]:
            with self.subTest(flagged=flagged, description=description):
                data, play, event = self.game(code='F')
                event['isBunt'] = flagged
                event['details']['description'] = description
                text = self.narrative_play(data)
                self.assertIn('Bunted foul with two strikes', text)
                self.assertIn('Pinky Slauson is out', text)
                self.assertNotIn('still oh and two', text.lower())
                self.assertNotIn("we'll do it again", text.lower())

    def test_pitchout_counts_as_a_ball(self):
        data, play, event = self.game(outcome='Single', code='X', reaches=True)
        event['hitData'] = {'location': 'CF'}
        pitchout = copy.deepcopy(event)
        pitchout.pop('hitData')
        pitchout['details'].update(code='P', description='Pitchout')
        pitchout['count'] = {'balls': 0, 'strikes': 1}
        play['playEvents'].insert(0, pitchout)
        text = self.narrative_play(data)
        self.assertIn('pitchout', text)
        self.assertIn('one and one', text.lower())

    def test_final_missed_bunt_never_uses_a_swinging_strikeout_variant(self):
        for choice in range(6):
            with self.subTest(choice=choice):
                data, play, event = self.game()
                event['isBunt'] = True
                play['commentaryRng']['play_outcome']['play'] = [choice]
                text = self.narrative_play(data)
                self.assertIn('bunt', text.lower())
                self.assertNotIn('swinging', text.lower())
                self.assertNotIn('swung', text.lower())
                self.assertEqual(text.lower().count('strikes out'), 1, text)


if __name__ == '__main__':
    unittest.main()
