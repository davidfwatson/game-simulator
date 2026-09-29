"""New broadcast phrases must be reachable only for their recorded situations."""
import copy
import unittest
from unittest.mock import patch

from commentary import GAME_CONTEXT
from renderers import NarrativeRenderer
from renderers.randomness import ChoiceRNG
from renderers.narrative.play_description import factual_play_category, strikeout_templates
from test_transcript_games import ledger_with, record, movement
from transcript_game_fixtures import compile_game


def render(records):
    data = compile_game(ledger_with(records), ('Source.\n' * 100).encode())
    with patch.object(ChoiceRNG, 'random', return_value=0.0), patch.object(ChoiceRNG, 'choice', lambda self, seq: seq[-1]):
        return NarrativeRenderer(data).render()


class TestTranscriptPlayRouting(unittest.TestCase):
    def test_contact_helper_accepts_standalone_context_without_full_play(self):
        renderer = NarrativeRenderer({'gameData': {'teams': {'away': {}, 'home': {}}}})
        self.assertIsNone(factual_play_category(renderer, 'Single', {'location': 'CF'}, {}, None, None))
        self.assertTrue(renderer._generate_play_description('Single', {'location': 'CF'}, {'type': 'Slider'}, 'Batter'))

    def test_forceout_and_double_play_sequence_routes(self):
        renderer = NarrativeRenderer({'gameData': {'teams': {'away': {}, 'home': {}}}})
        def out(pid, base, number, positions):
            return {'details': {'runner': {'id': pid}}, 'movement': {'isOut': True, 'outBase': base, 'outNumber': number}, 'credits': [{'position': {'abbreviation': pos}} for pos in positions]}
        play = {'matchup': {'batter': {'id': 1}}, 'runners': [out(2, '2B', 1, ['SS'])]}
        category = lambda outcome, hit=None, pitch=None: factual_play_category(renderer, outcome, hit or {'trajectory': 'ground_ball'}, pitch or {}, 'SS', play)
        self.assertIsNone(category('Forceout'))
        self.assertEqual(category('Forceout', {'trajectory': 'ground_ball', 'forceMechanism': 'unassisted'}), 'second_base')
        play['runners'][0]['credits'].append({'position': {'abbreviation': '2B'}})
        self.assertIsNone(category('Forceout'))
        self.assertEqual(category('Forceout', {'trajectory': 'ground_ball', 'forceMechanism': 'throw'}), 'second_base_throw')
        play['runners'] = [out(2, '2B', 2, ['1B', 'SS']), out(1, '1B', 1, ['1B', 'SS'])]
        self.assertEqual(category('Double Play'), 'first_then_second')
        play['runners'][0]['movement']['outNumber'] = 1
        play['runners'][1]['movement']['outNumber'] = 2
        self.assertIsNone(category('Double Play'))
        for runner in play['runners']:
            runner['credits'] = [{'position': {'abbreviation': pos}} for pos in ('SS', '1B')]
        self.assertEqual(category('Double Play'), 'unassisted_force')
        for runner in play['runners']:
            runner['credits'] = [{'position': {'abbreviation': pos}} for pos in ('SS', '2B', '1B')]
        self.assertIsNone(category('Double Play'))
        play['runners'] = [out(2, '3B', 1, ['C', '3B', '2B']), out(1, '1B', 2, ['C', '3B', '2B'])]
        self.assertEqual(category('Double Play', {'trajectory': 'bunt'}, {'isBunt': True}), 'bunt_third_first')
        self.assertIsNone(category('Double Play'))

    def test_walk_forces_run_only_when_loaded(self):
        records = [record(batter=f'Away Batter {i}', outcome='Intentional Walk', start=i, end=i) for i in range(1, 4)]
        records.append(record(batter='Away Batter 4', outcome='Walk', start=4, end=4, initial_count=[3, 0], score=[1, 0], pitches=[{'code': 'B', 'line': 4}]))
        self.assertIn('Ball four, and that will walk in a run', render(records))
        self.assertNotIn('walk in a run', render(records[-1:]))

    def test_special_intros_and_mid_inning_break_follow_game_state(self):
        cleanup = render([record(batter='Away Batter 4')])
        self.assertIn('Here comes the cleanup hitter, Away Batter 4.', cleanup)
        self.assertNotIn('cleanup hitter', render([record(batter='Away Batter 9')]))
        pitcher = render([record(batter='Away Pitcher')])
        self.assertIn('bring up the pitcher, Away Pitcher.', pitcher)
        self.assertNotIn('representing the winning run', cleanup)
        text = render([record(batter='Home Batter 1', inning=9, top=False, pitcher='Away Pitcher')])
        self.assertIn('representing the winning run', text)
        text = render([record(batter='Home Batter 1', inning=8, top=False, pitcher='Away Pitcher')])
        self.assertNotIn('representing the winning run', text)
        records = [record(batter=f'Away Batter {i}', outcome='Strikeout', outs=i, start=i, end=i) for i in range(1, 4)]
        records.append(record(batter='Home Batter 1', inning=1, top=False, pitcher='Away Pitcher', start=4, end=4))
        self.assertIn("We'll be back with the bottom half of the first inning.", render(records))

    def test_no_score_outro_reports_exact_bases_left(self):
        for count, phrase in [(1, 'strand a man on second'), (2, 'strand a pair'), (3, 'bases-loaded jam')]:
            records = []
            for i in range(1, count + 1):
                records.append(record(batter=f'Away Batter {i}', outcome='Intentional Walk', start=i, end=i))
            if count == 1:
                records[0]['outcome'] = 'Double'
                records[0]['runners'] = [movement('Away Batter 1', None, '2B')]
            for i in range(1, 4):
                records.append(record(batter=f'Away Batter {count + i}', outcome='Strikeout', outs=i, start=count + i, end=count + i))
            records.append(record(batter='Home Batter 1', inning=1, top=False, pitcher='Away Pitcher', start=count + 4, end=count + 4))
            with self.subTest(count=count):
                text = render(records)
                self.assertIn(phrase, text)
                if count < 3:
                    self.assertNotIn('bases-loaded jam', text)

    def test_relief_outro_requires_a_documented_pitcher_change(self):
        records = [record(batter=f'Away Batter {i}', outcome='Strikeout', outs=i, start=i, end=i) for i in range(1, 4)]
        records.append(record(batter='Home Batter 1', inning=1, top=False, pitcher='Away Pitcher', start=4, end=4, outs=3, outcome='Groundout'))
        records.extend(record(batter=f'Away Batter {i+3}', inning=2, pitcher='Relief Pitcher', outcome='Strikeout', outs=i, start=i+4, end=i+4) for i in range(1, 4))
        records.append(record(batter='Home Batter 2', inning=2, top=False, pitcher='Away Pitcher', start=8, end=8))
        self.assertIn('one-two-three inning for Pitcher in relief.', render(records))
        for r in records:
            if r['pitcher'] == 'Relief Pitcher': r['pitcher'] = 'Home Pitcher'
        self.assertNotIn('in relief.', render(records))

    def test_first_baseman_putout_method_must_be_explicit_in_strict_data(self):
        p = record(outcome='Groundout', outs=1, pitches=[{'code': 'X', 'line': 1}], hit={'trajectory': 'ground_ball', 'location': '1B'}, fielders=[{'name': 'First Fielder', 'position': '1B'}])
        text = render([p])
        self.assertIn('is retired at first', text)
        self.assertNotIn('unassisted', text)
        self.assertNotIn('throws', text)
        p['hit']['putoutMethod'] = 'unassisted'
        text = render([p])
        self.assertIn('steps on the bag', text)
        self.assertNotIn('throws', text)

    def test_colorful_terminal_strikeout_still_reports_the_result(self):
        pool = GAME_CONTEXT['narrative_templates']['Strikeout']
        with patch.dict(pool, {'swinging': ['Way out in front of that {pitch_type}.']}):
            text = render([record(outcome='Strikeout', outs=1, initial_count=[0, 2], pitches=[{'code': 'S', 'line': 1}])])
        self.assertIn('Away Batter 1 strikes out for out number one.', text)

    def test_unknown_terminal_strikeout_does_not_invent_swing(self):
        text = render([record(outcome='Strikeout', outs=1, initial_count=[0, 2], pitches=[{'code': 'U', 'line': 1, 'isStrike': True}])])
        self.assertIn('Away Batter 1 strikes out for out number one.', text)
        for claim in ('swinging', 'looking', 'chases', 'in the dirt'):
            self.assertNotIn(claim, text)

    def test_known_terminal_strikes_reach_their_narrative_pools(self):
        for code, phrase in [('S', 'gets fooled on that'), ('C', 'strikes out looking for out number one')]:
            with self.subTest(code=code):
                text = render([record(outcome='Strikeout', outs=1, initial_count=[0, 2], pitches=[{'code': code, 'line': 1, 'type': 'Slider'}])])
                self.assertIn(phrase, text)

    def test_location_claims_require_terminal_pitch_facts(self):
        for kind in ('swinging', 'looking'):
            templates = strikeout_templates(kind, {}, 'U')
            self.assertTrue(templates)
            self.assertFalse(any(any(word in t.lower() for word in ('dirt', ' high ', ' low ', 'outside', 'corner', 'out of the zone')) for t in templates))
        self.assertTrue(any('dirt' in t for t in strikeout_templates('swinging', {'location': 'dirt'}, 'U')))
        self.assertFalse(strikeout_templates('swinging_outside', {}, 'R'))

    def test_strict_unknown_ball_uses_neutral_pool(self):
        text = render([record(pitches=[{'code': 'B', 'line': 1, 'type': 'Slider'}])])
        self.assertIn('Slider is called a ball', text)
        for claim in ('outside', 'inside', 'low and', 'high and'):
            self.assertNotIn(claim, text)

    def test_four_pitch_walk_requires_complete_observed_zero_zero_start(self):
        pitches = [{'code': 'B', 'line': n} for n in range(1, 5)]
        self.assertIn('leadoff four-pitch walk', render([record(outcome='Walk', end=4, pitches=pitches)]))
        self.assertNotIn('four-pitch walk', render([record(outcome='Walk', end=3, initial_count=[1, 0], pitches=pitches[:3])]))
        self.assertNotIn('four-pitch walk', render([record(outcome='Intentional Walk')]))

    def test_location_phrase_steps_past_an_immediate_repeat(self):
        from renderers.narrative.helpers import get_pitch_description_for_location
        from commentary import GAME_CONTEXT
        class First:
            def choice(self, seq):
                return seq[0]
        pool = GAME_CONTEXT['pitch_locations']['ball']['default']
        self.assertEqual(get_pitch_description_for_location('B', None, 'Fastball', First()), pool[0])
        repeat_avoided = get_pitch_description_for_location('B', None, 'Fastball', First(), avoid=pool[0])
        self.assertNotEqual(repeat_avoided, pool[0])
        self.assertIn(repeat_avoided, pool)

    def test_terminal_pitch_call_survives_summary_templates(self):
        # A walk or strikeout template that doesn't embed {last_pitch_context}
        # must not swallow the final pitch call: the at-bat would jump from
        # the three-oh count straight to "That's a four-pitch walk".
        pitches = [{'code': 'B', 'line': n} for n in range(1, 5)]
        text = render([record(outcome='Walk', end=4, pitches=pitches)])
        walk_line = next(line for line in text.splitlines() if 'four-pitch walk' in line)
        self.assertIn('...', walk_line.split('four-pitch walk')[0])
        for code in ('S', 'C'):
            with self.subTest(code=code):
                text = render([record(outcome='Strikeout', outs=1, initial_count=[0, 2],
                                      pitches=[{'code': code, 'line': 1, 'type': 'Slider'}])])
                out_line = next(line for line in text.splitlines() if 'out number' in line or 'strike three' in line.lower())
                self.assertIn('...', out_line)

    def test_groundout_bunt_reaches_pitcher_specific_pool(self):
        p = record(outcome='Groundout', outs=1, pitches=[{'code': 'X', 'line': 1, 'isBunt': True}], hit={'trajectory': 'bunt', 'location': 'P'}, fielders=[{'name': 'Home Pitcher', 'position': 'P'}, {'name': 'First Fielder', 'position': '1B'}])
        self.assertIn('Bunted back to the mound. Pitcher scoops it up', render([p]))

    def test_field_error_grounder_route_is_used_in_complete_render(self):
        p = record(outcome='Field Error', pitches=[{'code': 'X', 'line': 1}], hit={'trajectory': 'ground_ball', 'location': 'SS'}, fielders=[{'name': 'Short Fielder', 'position': 'SS'}])
        self.assertIn("can't get a handle on it", render([p]))
        self.assertNotIn('bobbles', render([p]))

    def test_structured_actions_do_not_copy_source_or_guess_target(self):
        renderer = NarrativeRenderer({'gameData': {'teams': {'away': {}, 'home': {}}, 'broadcast': {'strictFacts': True}}})
        renderer.runners_on_base = {'1B': None, '2B': None, '3B': 'Runner'}
        base = {'runner': {'fullName': 'Runner'}, 'fromBase': '3B', 'toBase': '3B', 'isOut': True}
        event = {'details': {'eventType': 'caught_stealing', 'description': 'NEVER COPY THIS', 'runners': [base]}}
        self.assertEqual(renderer._render_steal_event(event), 'Runner is tagged out heading back to third.')
        self.assertIsNone(renderer.runners_on_base['3B'])
        base['toBase'] = None
        self.assertEqual(renderer._render_steal_event(event), 'Runner is caught stealing.')
        base.update(toBase='score', isOut=False)
        event['details']['eventType'] = 'wild_pitch'
        self.assertEqual(renderer._render_steal_event(event), 'Runner scores on a wild pitch.')

    def test_pickoff_attempt_preserves_runner_and_pickoff_removes_him(self):
        renderer = NarrativeRenderer({'gameData': {'teams': {'away': {}, 'home': {}}, 'broadcast': {'strictFacts': True}}})
        renderer.runners_on_base = {'1B': 'Runner', '2B': None, '3B': None}
        details = {'eventType': 'pickoff_attempt', 'runners': [{'runner': {'fullName': 'Runner'}, 'fromBase': '1B', 'toBase': '1B', 'isOut': False}]}
        self.assertIn('gets back safely', renderer._render_steal_event({'details': details}))
        self.assertEqual(renderer.runners_on_base['1B'], 'Runner')
        details['eventType'] = 'pickoff'; details['runners'][0]['isOut'] = True
        self.assertEqual(renderer._render_steal_event({'details': details}), 'Runner is picked off at first.')
        self.assertIsNone(renderer.runners_on_base['1B'])

    def test_unknown_actions_are_not_transcript_prose(self):
        renderer = NarrativeRenderer({'gameData': {'teams': {'away': {}, 'home': {}}, 'broadcast': {'strictFacts': True}}})
        self.assertEqual(renderer._render_steal_event({'details': {'eventType': 'wild_pitch', 'description': 'COPY ME'}}), '')

    def test_detailed_contact_categories_require_matching_runner_facts(self):
        renderer = NarrativeRenderer({'gameData': {'teams': {'away': {}, 'home': {}}}})
        p = {'matchup': {'batter': {'id': 1}}, 'runners': [{'details': {'runner': {'id': 1}}, 'movement': {'end': '1B', 'isOut': False}}]}
        category = lambda outcome, hit, pos='SS': factual_play_category(renderer, outcome, hit, {}, pos, p)
        self.assertIsNone(category('Single', {'categoryOverride': 'throwing_error', 'trajectory': 'ground_ball'}))
        p['runners'][0]['movement']['end'] = '2B'
        self.assertEqual(category('Single', {'categoryOverride': 'throwing_error', 'trajectory': 'ground_ball'}), 'throwing_error')
        p['result'] = {'isWalkoff': True}
        self.assertIsNone(category('Double', {}))
        self.assertEqual(category('Double', {'hitWall': True}), 'walkoff')
        self.assertEqual(category('Home Run', {}), 'walkoff')


if __name__ == '__main__':
    unittest.main()
