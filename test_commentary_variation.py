"""Context and outcome regressions for the shared commentary phrase pools."""

import unittest
from unittest.mock import Mock

from commentary import GAME_CONTEXT
from renderers import NarrativeRenderer, StatcastRenderer


class TestCommentaryVariation(unittest.TestCase):
    def make_renderer(self, choice_index=0, flow=0.0):
        renderer = NarrativeRenderer({
            'gameData': {'teams': {'home': {'name': 'Home'}, 'away': {'name': 'Away'}}},
        }, seed=42)
        # Exercise each wording directly, including the branch that declines the
        # initial template selection. Correct outcome descriptions must still win.
        for name in ('rng_play', 'rng_pitch', 'rng_flow'):
            rng = Mock()
            rng.random.return_value = flow
            rng.choice.side_effect = lambda options: options[choice_index % len(options)]
            setattr(renderer, name, rng)
        return renderer

    def describe(self, renderer, outcome, **kwargs):
        return renderer._generate_play_description(
            outcome,
            {'launchSpeed': 95.0, 'launchAngle': -5.0, 'location': 'SS'},
            {'type': 'slider', 'velo': 85},
            'Alex Batter',
            fielder_pos='SS',
            fielder_name='Sam Fielder',
            **kwargs,
        )

    def make_statcast_game(self, outcome, events, runs=0):
        return {
            'gameData': {'teams': {'home': {'name': 'Home'}, 'away': {'name': 'Away'}}},
            'liveData': {
                'plays': {'allPlays': [{
                    'about': {'inning': 1, 'isTopInning': True},
                    'matchup': {
                        'batter': {'fullName': 'Alex Batter'},
                        'pitcher': {'id': 1, 'fullName': 'Pat Pitcher'},
                    },
                    'playEvents': events,
                    'result': {'event': outcome, 'rbi': runs, 'homeScore': 0, 'awayScore': runs},
                    'count': {'outs': 1},
                    'runners': [],
                }]},
                'linescore': {'teams': {'home': {'runs': 0}, 'away': {'runs': runs}}},
            },
        }

    def test_error_variants_never_describe_a_retired_batter(self):
        variants = GAME_CONTEXT['narrative_templates']['Field Error']['default']
        for outcome in ('Reached on Error', 'Reached on Error (E6)', 'Field Error', 'Error'):
            for index in range(len(variants)):
                for flow in (0.0, 0.99):
                    with self.subTest(outcome=outcome, variant=index, flow=flow):
                        text = self.describe(self.make_renderer(index, flow), outcome, result_outs=1)
                        self.assertIn('error', text.lower())
                        self.assertIn('Alex Batter', text)
                        self.assertNotIn('out number', text)
                        self.assertNotIn('retire', text)
                        self.assertNotIn('throws to first', text)

    def test_forceout_variants_preserve_the_batter_and_out_context(self):
        variants = GAME_CONTEXT['narrative_templates']['Forceout']['default']
        for index in range(len(variants)):
            for outs, context in ((1, 'out number one'), (2, 'out number two'), (3, 'end the inning')):
                with self.subTest(variant=index, outs=outs):
                    text = self.describe(self.make_renderer(index, 0.99), 'Forceout', result_outs=outs)
                    self.assertIn("fielder's choice", text)
                    self.assertIn('Alex Batter', text)
                    self.assertIn(context, text)
                    self.assertNotIn('describes', text)
                    self.assertNotIn('retire Alex Batter', text)

    def test_double_play_aliases_use_the_same_narrative_pool(self):
        variants = GAME_CONTEXT['narrative_templates']['Double Play']['default']
        for index in range(len(variants)):
            with self.subTest(variant=index):
                expected = self.describe(self.make_renderer(index), 'Double Play', result_outs=2)
                for alias in ('Grounded Into DP', 'Grounded Into Double Play', 'Grounded Into DP (6-4-3)'):
                    text = self.describe(self.make_renderer(index), alias, result_outs=2)
                    self.assertEqual(expected, text)
                    self.assertNotIn('describes', text)

    def test_runner_status_variants_match_each_out_count(self):
        for outcome in ('Single', 'Double', 'Triple', 'Walk'):
            for outs, leadoff, prefix in (
                (0, True, 'leadoff_'), (0, False, None),
                (1, False, None), (2, False, 'two_out_'),
            ):
                key = (prefix + outcome.lower()) if prefix else f'{outcome.lower()}_{"nobody_out" if outs == 0 else "one_out"}'
                variants = GAME_CONTEXT['narrative_strings'].get(key, [])
                for index in range(len(variants)):
                    with self.subTest(key=key, variant=index):
                        text = self.make_renderer(index)._get_runner_status_string(
                            outcome, 'Alex Batter', outs, leadoff, ' here in the sixth',
                        )
                        self.assertIn('Alex Batter', text)
                        self.assertNotIn('{', text)
                        self.assertNotIn('}', text)
                        if outs == 2:
                            self.assertTrue('two-out' in text or 'two away' in text)
                        elif outs == 1:
                            self.assertNotIn('two-out', text)
                            self.assertNotIn('leadoff', text)

    def test_count_hold_variants_accept_the_live_count_context(self):
        variants = GAME_CONTEXT['narrative_strings']['count_remains_two_strikes']
        for count in ('oh and two', 'one and two', 'two and two', 'three and two'):
            for index in range(len(variants)):
                with self.subTest(count=count, variant=index):
                    text = self.make_renderer(index)._get_narrative_string(
                        'count_remains_two_strikes',
                        {'batter_name': 'Alex Batter', 'count_str': count},
                    )
                    self.assertNotIn('{', text)
                    self.assertTrue(text.startswith(', '))
                    if '{count_str}' in variants[index]:
                        self.assertIn(count, text)

    def test_steal_variants_keep_only_actual_bases_occupied(self):
        for event_type, phrase_pool in (('stolen_base', 'throw_outcome_safe'), ('caught_stealing', 'throw_outcome_out')):
            for description, origin, target, spoken_base in (
                ('Stolen Base 2B', '1B', '2B', 'second'),
                ('Stolen Base 3B', '2B', '3B', 'third'),
                ('Stolen Base Home', '3B', None, 'home'),
                ('Runner steals home', '3B', None, 'home'),
            ):
                for index in range(len(GAME_CONTEXT['narrative_strings'][phrase_pool])):
                    with self.subTest(event=event_type, description=description, variant=index):
                        renderer = self.make_renderer(index)
                        renderer.runners_on_base = {'1B': None, '2B': None, '3B': None}
                        renderer.runners_on_base[origin] = 'Robin Runner'
                        text = renderer._render_steal_event({'details': {
                            'eventType': event_type, 'description': description,
                        }})
                        self.assertIn('Robin Runner', text)
                        self.assertIn(spoken_base, text)
                        self.assertEqual({'1B', '2B', '3B'}, set(renderer.runners_on_base))
                        expected = {'1B': None, '2B': None, '3B': None}
                        if event_type == 'stolen_base' and target:
                            expected[target] = 'Robin Runner'
                        self.assertEqual(expected, renderer.runners_on_base)

    def test_negative_launch_angle_singles_are_not_described_as_liners(self):
        renderer = self.make_renderer()
        for speed in (96, 98, 101, 110):
            with self.subTest(speed=speed):
                self.assertEqual('grounder', renderer._get_batted_ball_category('Single', speed, -5))
        self.assertEqual('liner', renderer._get_batted_ball_category('Single', 105, 0))
        self.assertEqual('bloop', renderer._get_batted_ball_category('Single', 85, 20))

    def test_ball_location_variants_do_not_change_or_repeat_the_pitch_type(self):
        for hand in ('R', 'L'):
            for zone in (None, 11, 12, 13, 14):
                for pitch_type in ('Slider', 'Changeup', 'Curveball', 'Fastball'):
                    for index in range(max(map(len, GAME_CONTEXT['pitch_locations']['ball'].values()))):
                        with self.subTest(hand=hand, zone=zone, pitch=pitch_type, variant=index):
                            renderer = self.make_renderer(index)
                            text = renderer._get_pitch_call({
                                'details': {'code': 'B', 'zone': zone, 'description': 'Ball'},
                                'count': {'balls': 0, 'strikes': 0},
                            }, pitch_type, hand).lower()
                            # Complete calls can omit the pitch name; when
                            # stated, it must occur only once and stay factual.
                            self.assertLessEqual(text.count(pitch_type.lower()), 1)
                            for other_type in ('Slider', 'Changeup', 'Curveball', 'Fastball'):
                                if other_type != pitch_type:
                                    self.assertNotIn(other_type.lower(), text)

    def test_verb_variants_can_follow_a_batters_name(self):
        # The renderer supplies the subject. These predicates must use the
        # third-person present tense, rather than noun or participle fragments.
        for outcome, categories in GAME_CONTEXT['statcast_verbs'].items():
            if outcome == 'Strikeout':
                pools = categories
            else:
                pools = categories['verbs']
            for category, phrases in pools.items():
                for phrase in phrases:
                    with self.subTest(outcome=outcome, category=category, phrase=phrase):
                        self.assertRegex(phrase, r"^[\w-]+s(?:\s|$)")
                        self.assertNotRegex(phrase, r'^(?:a|an|the)\s')

    def test_statcast_noun_variants_render_complete_sentences(self):
        for outcome, noun in (('Single', 'a sharp single'), ('Home Run', 'a home run')):
            with self.subTest(outcome=outcome):
                runs = 4 if outcome == 'Home Run' else 0
                game = self.make_statcast_game(outcome, [{
                    'details': {'code': 'X', 'description': 'In play'},
                    'hitData': {'launchSpeed': 105, 'launchAngle': 20, 'location': 'LF'},
                }], runs=runs)
                renderer = StatcastRenderer(game, seed=42)
                renderer._get_batted_ball_verb = Mock(return_value=(noun, 'nouns'))
                text = renderer.render()
                self.assertIn(f'Result: Alex Batter hits {noun} to left field.', text)
                self.assertNotIn(f'Alex Batter {noun}', text)

    def test_a_steal_after_strike_three_is_not_a_batted_ball_or_swinging_strike(self):
        game = self.make_statcast_game('Strikeout', [
            {'isPitch': True, 'details': {'code': 'C', 'description': 'Called Strike'}},
            {'isPitch': False, 'details': {
                'code': 'X', 'description': 'Stolen Base 2B', 'eventType': 'stolen_base',
                'type': {'description': 'Action'},
            }},
        ])
        text = StatcastRenderer(game, seed=42).render()
        self.assertNotIn('In play:', text)
        self.assertNotIn('mph Action', text)
        self.assertTrue(any(
            f'Result: Alex Batter {phrase}.' in text
            for phrase in GAME_CONTEXT['statcast_verbs']['Strikeout']['looking']
        ), text)

    def test_home_run_fallback_variants_do_not_assume_a_solo_homer(self):
        for category, phrases in GAME_CONTEXT['statcast_verbs']['Home Run']['nouns'].items():
            for index in range(len(phrases)):
                with self.subTest(category=category, variant=index):
                    renderer = self.make_renderer(index, 0.99)
                    renderer.runners_on_base = {'1B': 'First Runner', '2B': 'Second Runner', '3B': 'Third Runner'}
                    text = renderer._generate_play_description(
                        'Home Run', {'categoryOverride': category, 'location': 'LF'},
                        {'type': 'slider', 'velo': 85}, 'Alex Batter', result_outs=0,
                    )
                    self.assertNotIn('solo', text)
                    self.assertNotIn('one-run', text)


if __name__ == '__main__':
    unittest.main()
