"""Semantic coverage for pitch phrasing heard in the Sleep Baseball examples."""

import copy
import json
from pathlib import Path
import unittest

from commentary import GAME_CONTEXT
from renderers.narrative.helpers import (
    choose_pitch_description,
    get_pitch_location_categories,
    resolve_batter_hand,
)
from renderers.narrative.renderer import NarrativeRenderer


class IndexRNG:
    def __init__(self, index=0):
        self.index = index

    def choice(self, options):
        return options[self.index % len(options)]


class PhraseRNG:
    def __init__(self, phrase):
        self.phrase = phrase

    def choice(self, options):
        # Require the actual routing to offer this phrase before selecting it.
        return next(option for option in options if option == self.phrase)


def make_renderer(index=0):
    renderer = object.__new__(NarrativeRenderer)
    renderer.gameday_data = {
        'gameData': {
            'directMode': True,
            'players': {'ID1': {'lastName': 'De Jesus'}},
        },
    }
    renderer.rng_pitch = IndexRNG(index)
    renderer.rng_play = IndexRNG(index)
    renderer.rng_flow = IndexRNG(index)
    return renderer


def pitch(code, zone=None, strikes=0, description=''):
    return {
        'details': {'code': code, 'zone': zone, 'description': description},
        'count': {'balls': 0, 'strikes': strikes},
    }


class TestSleepBaseballPitchRendering(unittest.TestCase):
    def test_strike_zone_categories_mirror_with_batter_hand(self):
        for zone, right, left in (
            (1, ('high', 'inside'), ('high', 'outside')),
            (4, ('inside',), ('outside',)),
            (6, ('outside',), ('inside',)),
            (9, ('low', 'outside'), ('low', 'inside')),
            (11, ('high', 'inside'), ('high', 'outside')),
            (14, ('low', 'outside'), ('low', 'inside')),
        ):
            with self.subTest(zone=zone):
                self.assertEqual(get_pitch_location_categories(zone, 'R'), right)
                self.assertEqual(get_pitch_location_categories(zone, 'L'), left)
        for zone in (None, 5, 10, 15, '8', True):
            self.assertEqual(get_pitch_location_categories(zone), ())

    def test_switch_hitters_use_effective_side_for_balls_and_strikes(self):
        renderer = make_renderer()
        for pitcher_hand, effective, expected in (
            ('R', 'L', 'outside'), ('L', 'R', 'inside'),
        ):
            with self.subTest(pitcher_hand=pitcher_hand):
                hand = resolve_batter_hand('S', pitcher_hand)
                self.assertEqual(hand, effective)
                called = renderer._get_pitch_call(pitch('C', 4), 'Curveball', hand)
                self.assertIn(f'on the {expected} corner', called)
                ball = renderer._get_pitch_call(pitch('B', 11), 'Curveball', hand)
                self.assertIn('high and tight' if expected == 'inside' else 'letters', ball)

    def test_called_low_strikes_use_actual_strike_number(self):
        # Examples 2:517 and 4:37/601 distinguish a called strike from strike three.
        renderer = make_renderer()
        self.assertEqual(
            renderer._get_pitch_call(pitch('C', 8, 0), 'Fastball'),
            'Fastball, called a strike at the knees',
        )
        self.assertEqual(
            renderer._get_pitch_call(pitch('C', 8, 2), 'Fastball'),
            'Fastball, called strike three at the knees',
        )

    def test_center_and_unknown_zones_keep_generic_calls(self):
        for zone in (None, 5, 14):
            renderer = make_renderer()
            self.assertEqual(
                renderer._get_pitch_call(pitch('C', zone), 'Fastball'),
                'Fastball, called strike one',
            )
            self.assertIsNone(renderer._get_location_strikeout_description(
                pitch('S', None, 2), 'Fastball', 'Billy De Jesus', 'to end the inning'))

    def test_complete_pitch_calls_do_not_repeat_pitch_type(self):
        pool = GAME_CONTEXT['narrative_strings']['strike_called_two']
        renderer = make_renderer(pool.index('And that {pitch_type_lower} is called a strike'))
        self.assertEqual(
            renderer._get_pitch_call(pitch('C', 5, 1), 'Curveball'),
            'And that curveball is called a strike',
        )
        renderer.rng_pitch = PhraseRNG('And he takes a {pitch_type_lower} outside')
        self.assertEqual(
            renderer._get_pitch_call(pitch('B', 14), 'Curveball'),
            'And he takes a curveball outside',
        )
        renderer.rng_pitch = IndexRNG(12)
        self.assertEqual(
            renderer._get_pitch_call(pitch('B', 11), 'Curveball'),
            'Curveball high and tight',
        )

    def test_nonterminal_location_swings_never_announce_a_strikeout(self):
        renderer = make_renderer()
        for strikes in (0, 1):
            for zone, forbidden in ((2, 'low '), (8, 'high '), (6, 'inside ')):
                for index in range(20):
                    renderer.rng_pitch = IndexRNG(index)
                    text = renderer._get_pitch_call(pitch('S', zone, strikes), 'Fastball')
                    self.assertNotIn(forbidden, text)
                    self.assertNotIn('strike three', text)
                    self.assertNotIn('strikes out', text)
                    self.assertNotIn('down on strikes', text)
        generic = GAME_CONTEXT['narrative_strings']['strike_swinging']
        renderer.rng_pitch = IndexRNG(len(generic))
        self.assertEqual(
            renderer._get_pitch_call(pitch('S', 5), 'Curveball'),
            'Swing and a miss at a curveball',
        )

    def test_numbered_ball_calls_use_the_resulting_ball_count(self):
        renderer = make_renderer()
        renderer.rng_pitch = PhraseRNG("And that's {ball_call}")
        event = pitch('B')
        for balls_before, ball_word in enumerate(('one', 'two', 'three', 'four')):
            event['count']['balls'] = balls_before
            self.assertEqual(
                renderer._get_pitch_call(event, 'Slider'), f"And that's ball {ball_word}")

    def test_early_bare_calls_preserve_location_and_omit_pitch_name(self):
        # episode_005:33/51 and episode_001:78 use complete short calls.
        renderer = make_renderer()
        renderer.rng_pitch = PhraseRNG('Low and inside for {ball_call}')
        event = pitch('B', 13)
        event['count']['balls'] = 1
        self.assertEqual(renderer._get_pitch_call(event, 'Slider'), 'Low and inside for ball two')
        renderer.rng_pitch = PhraseRNG('Just a bit outside for a ball')
        self.assertEqual(renderer._get_pitch_call(pitch('B', 13), 'Curveball', 'L'),
                         'Just a bit outside for a ball')
        renderer.rng_pitch = IndexRNG(0)
        self.assertEqual(renderer._get_pitch_call(pitch('B', 13), 'Curveball'),
                         'Curveball misses low and inside')

    def test_low_ball_does_not_invent_dirt_without_explicit_evidence(self):
        renderer = make_renderer()
        for zone in (13, 14):
            for index in range(60):
                renderer.rng_pitch = IndexRNG(index)
                text = renderer._get_pitch_call(pitch('B', zone), 'Slider').lower()
                for unsupported in ('dirt', 'bounc', 'spik'):
                    self.assertNotIn(unsupported, text)
        renderer.rng_pitch = PhraseRNG("And that's in the dirt for a ball")
        self.assertEqual(renderer._get_pitch_call(
            pitch('B', 14, description='Ball (in the dirt)'), 'Slider'),
            "And that's in the dirt for a ball")

    def test_early_bare_called_strikes_use_the_resulting_strike_number(self):
        # episode_005:187/271 say the strike number without a pitch name.
        for before, word in enumerate(('one', 'two', 'three')):
            renderer = make_renderer()
            renderer.rng_pitch = PhraseRNG("That's in there for strike {strike_number_word}")
            self.assertEqual(renderer._get_pitch_call(pitch('C', None, before), 'Fastball'),
                             f"That's in there for strike {word}")

    def test_short_count_continuations_work_outside_special_counts(self):
        renderer = make_renderer(1)
        self.assertEqual(
            renderer._get_count_call(1, 0, 'B', 'Blinky Malone', 'Jesus Ferguson'),
            "it's one and oh",
        )
        self.assertEqual(
            renderer._get_count_call(0, 2, 'S', 'Blinky Malone', 'Jesus Ferguson'),
            "it's oh and two",
        )

    def test_another_pitch_requires_same_pitch_type(self):
        options = ['Another {pitch_type_lower} called a strike', 'called a strike']
        for previous, expected in (
            (None, 'called a strike'),
            ('Slider', 'called a strike'),
            ('Fastball', options[0]),
            ('Four-seam fastball', options[0]),
        ):
            self.assertEqual(
                choose_pitch_description(options, IndexRNG(), 'Fastball', previous), expected)

    def test_location_strikeouts_preserve_out_context_and_compound_surnames(self):
        renderer = make_renderer()
        for zone, phrase in ((2, 'high heater'), (8, 'low heater'), (6, 'outside fastball')):
            with self.subTest(zone=zone):
                text = renderer._get_location_strikeout_description(
                    pitch('S', zone, 2), 'Fastball', 'Billy De Jesus', 'to end the inning', 'R', 1)
                self.assertIn(phrase, text)
                self.assertIn('De Jesus', text)
                self.assertIn('to end the inning', text)
                self.assertNotIn('Billy De Jesus', text)
        dirt = renderer._get_location_strikeout_description(
            pitch('S', 8, 2, 'Swinging Strike (in the dirt)'), 'Slider',
            'Billy De Jesus', 'for out number two', 'R', 1)
        self.assertIn('slider in the dirt', dirt)
        self.assertIn('for out number two', dirt)

    def test_known_location_never_selects_contradictory_strikeout(self):
        renderer = make_renderer()
        for index in range(20):
            renderer.rng_play = IndexRNG(index)
            for zone, forbidden in ((2, ('low ', 'outside ', 'in the dirt')),
                                    (8, ('high ', 'inside ', 'in the dirt')),
                                    (6, ('high ', 'low ', 'inside ', 'in the dirt'))):
                text = renderer._get_location_strikeout_description(
                    pitch('S', zone, 2), 'Fastball', 'Billy De Jesus', 'to end the inning', 'R', 1)
                for phrase in forbidden:
                    self.assertNotIn(phrase, text)

    def test_count_variants_use_independent_stream_after_fastball_choices(self):
        renderer = make_renderer()
        # FF simplification and description consume both pitch-stream calls.
        # The play-stream digit still independently selects 'falls behind'.
        renderer._reseed_from_timestamp('2025-09-27T23:05:00.0000000000000001', 'event')
        pitch_type = renderer._simplify_pitch_type('Four-seam fastball', capitalize=True)
        renderer._get_pitch_call(pitch('B', 14), pitch_type)
        self.assertEqual(
            renderer._get_count_call(3, 1, 'B', 'Javier Von Neumann', 'Billy De Jesus'),
            'and Von Neumann falls behind, three and one',
        )
        self.assertEqual(renderer._get_count_call(2, 1, 'B', 'Javier Von Neumann', 'Billy De Jesus'), 'two and one')
        self.assertEqual(renderer._get_count_call(3, 1, 'C', 'Javier Von Neumann', 'Billy De Jesus'), 'three and one')

    def test_named_batter_connectors_use_metadata_surname(self):
        renderer = make_renderer()
        pool = GAME_CONTEXT['narrative_strings']['pitch_connectors']
        index = next(i for i, template in enumerate(pool) if '{batter_name_last}' in template)
        renderer.rng_flow = IndexRNG(index)
        text = renderer._get_pitch_connector(1, 1, 'Rick Stetson', 'Billy De Jesus', batter_id=1)
        self.assertIn('De Jesus', text)

    def test_renderer_emits_complete_strikeout_and_preserves_count_name_case(self):
        path = Path(__file__).with_name('test_fixture_pbp_example_4.json')
        data = json.loads(path.read_text())
        play = copy.deepcopy(data['liveData']['plays']['allPlays'][0])
        prototype = copy.deepcopy(play['playEvents'][0])
        play['playEvents'] = []
        for code, balls, strikes, zone in (
            ('B', 0, 0, 14), ('B', 1, 0, 14), ('C', 2, 0, 5),
            ('C', 2, 1, 5), ('S', 2, 2, 2),
        ):
            event = copy.deepcopy(prototype)
            event['details'].update(code=code, zone=zone)
            event['details']['type'] = {'code': 'FF', 'description': 'Four-seam fastball'}
            event['count'].update(balls=balls, strikes=strikes)
            # Period after description; count variation is play-stream choice1.
            seed = 9000 * 100000000 + (1 if (balls, strikes) == (1, 0) else 0)
            event['startTime'] = f'2025-09-27T23:05:01.{seed:016d}'
            play['playEvents'].append(event)
        play['about']['endTime'] = '2025-09-27T23:05:19.0000000000000000'
        play['matchup']['pitcher']['fullName'] = 'Javier Von Neumann'
        data['liveData']['plays']['allPlays'] = [play]
        data['gameData']['directMode'] = True
        text = NarrativeRenderer(data).render()
        self.assertIn('And Von Neumann falls behind, two and oh.', text)
        self.assertIn('Swing and a miss on a high heater, and Bradleys is down on strikes for out number one.', text)
        self.assertNotIn('von neumann falls behind', text)

    def test_neutral_strikeout_can_render_without_inventing_location(self):
        data = json.loads(Path(__file__).with_name('test_fixture_pbp_example_4.json').read_text())
        play = copy.deepcopy(data['liveData']['plays']['allPlays'][0])
        final = play['playEvents'][-1]
        final['details'].update(code='S', zone=5, description='Swinging Strike')
        final['details']['type'] = {'code': 'FF', 'description': 'Fastball'}
        final['startTime'] = '2025-09-27T23:05:01.0000000000060000'
        play['about']['endTime'] = '2025-09-27T23:05:19.0000000000000006'
        data['liveData']['plays']['allPlays'] = [play]
        data['gameData']['directMode'] = True
        text = NarrativeRenderer(data).render()
        self.assertIn('Swung on and missed. And down goes Bradleys for out number one.', text)


if __name__ == '__main__':
    unittest.main()
