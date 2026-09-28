"""Home-run wording must work for both field names and foul-line directions."""

import unittest

from commentary import GAME_CONTEXT
from renderers.narrative.renderer import NarrativeRenderer


class TestHomeRunDirections(unittest.TestCase):
    def describe(self, hit_data, template_index):
        renderer = NarrativeRenderer({'gameData': {'teams': {'home': {}, 'away': {}}}})
        renderer._reseed_for_point({
            'commentaryRng': {'case': {'play': [template_index], 'flow': [0]}},
        }, 'case', '', 'home-run-direction')
        return renderer._generate_play_description(
            'Home Run', hit_data, {'type': 'Slider'}, 'Batter', fielder_name='Jones',
        )

    def test_line_directions_never_use_field_noun_templates(self):
        pool = GAME_CONTEXT['narrative_templates']['Home Run']['default']
        for location in (None, 'DL', '1BL', '3BL'):
            hit_data = {'launchSpeed': 110, 'launchAngle': 28}
            if location:
                hit_data['location'] = location
            for index in range(len(pool)):
                with self.subTest(location=location, index=index):
                    text = self.describe(hit_data, index)
                    self.assertNotIn('deep to down', text)
                    self.assertNotIn('to deep down', text)

    def test_transcript_templates_remain_reachable_for_field_locations(self):
        pool = GAME_CONTEXT['narrative_templates']['Home Run']['default']
        cases = (
            ('DLF', 'Swung on, a high drive deep to {direction_noun}, and that one is going to sail over the wall.',
             'Swung on, a high drive deep to left field, and that one is going to sail over the wall.'),
            ('DRF', "Hit in the air to deep {direction_noun}. {fielder_name} racing back, and he'll run out of room as that one sails over the wall.",
             "Hit in the air to deep right field. Jones racing back, and he'll run out of room as that one sails over the wall."),
        )
        for location, template, expected in cases:
            with self.subTest(location=location):
                self.assertEqual(self.describe({'location': location}, pool.index(template)), expected)


if __name__ == '__main__':
    unittest.main()
