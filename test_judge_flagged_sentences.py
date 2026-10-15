"""Regression coverage for sentences blind judges flagged in simulated games."""

import copy
import re
import unittest

from baseball import BaseballSimulator
from renderers import NarrativeRenderer
from renderers.narrative.batted_ball import passed_infielder
from teams import TEAMS

STEALS = ('stolen_base', 'caught_stealing')


def simulate(seed):
    game = BaseballSimulator(TEAMS["BAY_BOMBERS"], TEAMS["PC_PILOTS"], game_seed=seed)
    game.play_game()
    return game.gameday_data


def bare_renderer(seed=0):
    renderer = NarrativeRenderer({'gameData': {'teams': {'away': {}, 'home': {}}}}, seed=seed)
    renderer._reset_render_state()
    return renderer


def descriptions(outcome, hit_data, fielder_pos=None, fielder_name=None, seeds=60):
    """The play's description under many commentary seeds."""
    texts = []
    for seed in range(seeds):
        renderer = bare_renderer(seed)
        texts.append(renderer._generate_play_description(
            outcome, dict(hit_data), {'type': 'Sinker', 'velo': 92.0}, 'Sam Decker',
            fielder_pos, fielder_name, result_outs=1))
    return texts


class TestStealBehindInningEndingStrikeout(unittest.TestCase):
    def test_simulator_scores_no_steal_behind_strike_three_for_the_third_out(self):
        # Seeds 38, 50 and 95 each had a runner going on such a pitch.
        for seed in (38, 50, 95, 7):
            with self.subTest(seed=seed):
                for play in simulate(seed)['liveData']['plays']['allPlays']:
                    if play['result']['event'] != 'Strikeout' or play['count']['outs'] != 3:
                        continue
                    pitches = [i for i, event in enumerate(play['playEvents']) if event.get('isPitch')]
                    trailing = play['playEvents'][pitches[-1] + 1:]
                    self.assertFalse([e for e in trailing if e['details'].get('eventType') in STEALS])

    def test_renderer_ignores_a_steal_recorded_behind_the_third_out(self):
        data = simulate(7)
        plays = data['liveData']['plays']['allPlays']
        index, play = next((i, p) for i, p in enumerate(plays)
                           if p['result']['event'] == 'Strikeout' and p['count']['outs'] == 3
                           and not any(e['details'].get('eventType') in STEALS for e in p['playEvents']))
        expected = NarrativeRenderer(copy.deepcopy(data), seed=7).render()
        last = play['playEvents'][-1]
        play['playEvents'].append({
            'index': last['index'] + 1, 'startTime': last['endTime'], 'endTime': last['endTime'],
            'isPitch': False, 'count': {'balls': last['count']['balls'], 'strikes': 3},
            'details': {'description': 'Stolen Base 2B', 'code': 'X', 'isStrike': False,
                        'type': {'code': 'AS', 'description': 'Action'}, 'eventType': 'stolen_base'}})
        rendered = NarrativeRenderer(data, seed=7).render()
        self.assertEqual(rendered.count('steals'), expected.count('steals'))
        self.assertEqual(rendered, expected)


class TestBatterRecap(unittest.TestCase):
    def recap(self, entries, current_inning=7, recap_format=60):
        renderer = bare_renderer()
        renderer.batter_history = {1: [{'event': event, 'inning': inning, 'scored': scored}
                                       for event, inning, scored in entries]}
        renderer._recap_current_inning = current_inning
        return renderer._get_batter_recap(1, 'Chen', 0, recap_format)

    def test_same_result_twice_is_not_listed_twice(self):
        cases = [
            ([('Single', 1, False), ('Single', 3, False)], 'Chen had a base hit in the first and another in the third.'),
            ([('Strikeout', 2, False), ('Strikeout', 4, False)], 'Chen struck out in the second and again in the fourth.'),
            ([('Groundout', 2, False), ('Forceout', 5, False)], 'Chen grounded out in the second and again in the fifth.'),
            ([('Single', 3, False), ('Single', 3, False)], 'Chen had two base hits in the third.'),
            ([('Walk', 7, False), ('Walk', 7, False)], 'Chen walked twice earlier this inning.'),
            ([('Double', 1, True), ('Double', 4, True)],
             'Chen had a double and scored a run in the first and another in the fourth.'),
            ([('Walk', 1, False), ('Walk', 4, True)],
             'Chen walked in the first and walked again and scored a run in the fourth.'),
            ([('Single', 1, True), ('Single', 4, False)],
             'Chen had a base hit and scored a run in the first and had another base hit in the fourth.'),
        ]
        for entries, expected in cases:
            with self.subTest(entries=entries):
                self.assertEqual(self.recap(entries), expected)

    def test_every_appearance_keeps_its_inning(self):
        events = ('Single', 'Double', 'Walk', 'Strikeout', 'Groundout', 'Flyout', 'Home Run', 'Hit By Pitch')
        for first in events:
            for second in events:
                for innings in ((1, 3), (3, 3)):
                    for recap_format in (60, 90):
                        text = self.recap([(first, innings[0], False), (second, innings[1], False)],
                                          recap_format=recap_format)
                        with self.subTest(text=text):
                            self.assertNotRegex(text, r'\b(\w+(?: \w+){1,3}) and \1 ')
                            self.assertEqual(len(re.findall(r'in the (?:first|third)\b', text)),
                                             len(set(innings)))

    def test_different_results_read_as_before(self):
        self.assertEqual(self.recap([('Walk', 1, False), ('Strikeout', 3, False)]),
                         'Chen walked in the first and struck out in the third.')
        self.assertEqual(self.recap([('Walk', 7, False), ('Single', 7, False)]),
                         'Chen walked and had a base hit earlier this inning.')


OUTFIELDER = re.compile(r'\b(left|center|right) fielder\b')
AIR_WORDS = re.compile(r'\blined\b|line drive|liner|drops? in\b|falls? in\b|in the air|bloop', re.I)


class TestGroundBallHitWording(unittest.TestCase):
    def test_grounder_through_the_infield_goes_past_an_infielder(self):
        balls = {
            'the second baseman': {'trajectory': 'ground_ball', 'hardness': 'soft', 'lane': 'right_side',
                                   'location': 'RS', 'launchSpeed': 70.1, 'launchAngle': -8.0,
                                   'coordinates': {'coordX': 160.0, 'coordY': 118.0}, 'totalDistance': 220},
            'the shortstop': {'trajectory': 'ground_ball', 'hardness': 'hard', 'lane': 'left_side',
                              'location': 'LS', 'launchSpeed': 104.0, 'launchAngle': -4.0,
                              'coordinates': {'coordX': 92.4, 'coordY': 116.5}, 'totalDistance': 220},
            'the first baseman': {'trajectory': 'ground_ball', 'hardness': 'medium', 'lane': 'right_line',
                                  'location': 'RS', 'launchSpeed': 88.0, 'launchAngle': -3.0,
                                  'coordinates': {'coordX': 184.9, 'coordY': 133.2}, 'totalDistance': 220},
        }
        for infielder, hit_data in balls.items():
            with self.subTest(infielder=infielder):
                self.assertEqual(passed_infielder(hit_data), infielder)
                texts = descriptions('Single', hit_data)
                for text in texts:
                    self.assertNotRegex(text, OUTFIELDER)
                    self.assertNotRegex(text, AIR_WORDS)
                    self.assertNotIn('the fielder', text)
                    if hit_data['hardness'] != 'soft':
                        self.assertNotRegex(text, r'(?i)dribbler|squibber|slow roller')
                    if 'past' in text or 'will not get there' in text:
                        self.assertIn(infielder.replace('the ', ''), text)
        soft = ' '.join(descriptions('Single', balls['the second baseman'], seeds=200))
        self.assertIn('squeak past the second baseman', soft)

    def test_infield_hit_stays_in_the_infield(self):
        for location, noun, where in (('SS', 'shortstop', 'short'), ('2B', 'second baseman', 'second'),
                                      ('3B', 'third baseman', 'third'), ('1B', 'first baseman', 'first')):
            hit_data = {'trajectory': 'ground_ball', 'hardness': 'soft', 'depth': None, 'lane': None,
                        'location': location, 'launchSpeed': 52.0, 'launchAngle': -20.0,
                        'coordinates': {'coordX': 104.2, 'coordY': 142.9}, 'totalDistance': 148}
            with self.subTest(location=location):
                for text in descriptions('Single', hit_data):
                    self.assertNotRegex(text, OUTFIELDER)
                    self.assertNotRegex(text, AIR_WORDS)
                    self.assertNotRegex(text, r'(left|center|right) field\b|through the|squeak|hole')
                    self.assertRegex(text, rf'\bto {where}\b')
                    if re.search(r'baseman|shortstop', text):
                        self.assertIn(noun, text)
                    if location == '1B':
                        self.assertNotRegex(text, r'throws? to first|the throw is')

    def test_ball_in_the_air_is_not_past_a_diving_fielder_into_the_outfield(self):
        hit_data = {'trajectory': 'fly_ball', 'hardness': 'hard', 'depth': 'wall', 'lane': 'right_center',
                    'location': 'RC', 'launchSpeed': 102.4, 'launchAngle': 28.1,
                    'coordinates': {'coordX': 176.1, 'coordY': 51.9}, 'totalDistance': 386}
        for text in descriptions('Double', hit_data, seeds=150):
            self.assertNotIn('past the diving', text)
            self.assertNotIn('roll into the outfield', text)

    def test_liner_down_the_line_gets_past_the_corner_infielder(self):
        hit_data = {'trajectory': 'line_drive', 'hardness': 'medium', 'depth': 'wall', 'lane': 'left_line',
                    'location': 'DL', 'launchSpeed': 94.1, 'launchAngle': 15.3,
                    'coordinates': {'coordX': 53.0, 'coordY': 104.6}, 'totalDistance': 295}
        texts = descriptions('Double', hit_data, seeds=300)
        past = [text for text in texts if 'past the diving' in text]
        self.assertTrue(past)
        for text in past:
            self.assertIn('past the diving third baseman', text)

    def test_grounder_fielded_by_an_infielder_is_not_hit_to_the_outfield(self):
        middle = {'trajectory': 'ground_ball', 'hardness': 'soft', 'depth': None, 'lane': 'middle',
                  'location': '2B', 'launchSpeed': 71.2, 'launchAngle': -22.4,
                  'coordinates': {'coordX': 128.8, 'coordY': 139.1}, 'totalDistance': 148}
        line = dict(middle, lane='left_line', location='3B', coordinates={'coordX': 96.5, 'coordY': 164.0})
        comebacker = dict(middle, hardness='hard', launchSpeed=111.0, location='P',
                          coordinates={'coordX': 124.4, 'coordY': 174.0}, totalDistance=60)
        for hit_data, position in ((middle, '2B'), (line, '3B'), (comebacker, 'P')):
            with self.subTest(position=position):
                for text in descriptions('Groundout', hit_data, position, 'Chase'):
                    self.assertNotRegex(text, r'(left|center|right) field\b')
                    if position == 'P':
                        self.assertNotRegex(text, r'(?i)tapper|dribbler|slow roller|up the middle')

    def test_transcript_ledger_ball_without_coordinates_is_unchanged(self):
        # A ledger's location is the direction the hosts gave: "Grounder to
        # short, and that one squeaks through the infield" stays reachable.
        hit_data = {'trajectory': 'ground_ball', 'location': 'SS', 'launchSpeed': 98.0, 'launchAngle': -5.0}
        texts = descriptions('Single', hit_data, seeds=200)
        self.assertTrue(any('through the infield' in text for text in texts))
        self.assertFalse(any('infield hit' in text or 'infield single' in text for text in texts))


class TestSentenceStarts(unittest.TestCase):
    def test_sentences_start_with_a_capital(self):
        text = NarrativeRenderer(simulate(3), seed=3).render()
        lowercase = [m.group() for m in re.finditer(r'.{25}[a-z][.!?] [a-z].{15}', text)
                     if 'Instagram. if' not in m.group()]
        self.assertEqual(lowercase, [])
        self.assertNotRegex(text, r'\bHe \w+ing\b')
        self.assertNotRegex(text, r'\bdown down\b')


if __name__ == '__main__':
    unittest.main()
