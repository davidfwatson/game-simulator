"""Baserunning and fielding tells reported by the round-17 blind judges."""
import random
import re
import unittest
from unittest.mock import patch

import fieldsim
from baseball import BaseballSimulator
from renderers import NarrativeRenderer
from teams import TEAMS


def simulate(seed):
    game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=seed)
    game.play_game()
    return game


def renderer(seed=0):
    return NarrativeRenderer({'gameData': {'teams': {'away': {}, 'home': {}}}}, seed=seed)


class TestUnfinishedPlateAppearance(unittest.TestCase):
    def test_caught_stealing_third_out_keeps_the_same_batter(self):
        for top in (True, False):
            with self.subTest(top=top):
                game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
                # Two called strikeouts, a walk, then a ball on which the
                # runner is caught. Play the opposing half and the next half
                # through the real at-bat engine to check the lineup/count reset.
                locations = iter([(True, 5)] * 6 + [(False, 12)] * 5 + [(True, 5)] * 18)
                with patch.object(game, '_simulate_pitch_trajectory', side_effect=lambda *args: next(locations)), \
                        patch.object(game, '_simulate_bat_swing', return_value=False), \
                        patch.object(game, '_decide_steal_attempt', side_effect=lambda *args:
                                     2 if game.outs == 2 and game.bases[0] else None), \
                        patch.object(game.game_rng, 'random', return_value=0.99), \
                        patch.object(game, '_manage_between_innings'), \
                        patch.object(game, '_manage_pitching_change'):
                    for inning, half in ((1, top), (1 if top else 2, not top), (2, top)):
                        game.inning, game.top_of_inning = inning, half
                        game._simulate_half_inning()
                plays = game.gameday_data['liveData']['plays']['allPlays']
                announcer = NarrativeRenderer(game.gameday_data, seed=0)
                lines = announcer.render().splitlines()
                caught = [(i, p) for i, p in enumerate(plays) if p['result']['event'] == 'Caught Stealing']
                self.assertEqual(len(caught), 1)
                index, play = caught[0]
                self.assertEqual(play['count']['outs'], 3)
                following = next(p for p in plays[index + 1:]
                                 if p['about']['isTopInning'] == play['about']['isTopInning'])
                self.assertEqual(play['matchup']['batter'], following['matchup']['batter'])
                self.assertFalse(play['about']['isComplete'])
                self.assertTrue(any(r['movement']['isOut'] for r in play['runners']))
                low, high = announcer._play_line_map[index]
                self.assertEqual(' '.join(lines[low:high]).count('is caught stealing'), 1)
                first_pitch = next(e for e in following['playEvents'] if e.get('isPitch'))
                self.assertEqual(first_pitch['count']['balls'], 0)
                self.assertEqual(first_pitch['count']['strikes'], 0)
                for side in ('away', 'home'):
                    team = game.gameday_data['liveData']['boxscore']['teams'][side]
                    for player_id, player in team['players'].items():
                        appearances = sum(p['matchup']['batter']['id'] == int(player_id[2:])
                                          and p['about'].get('isComplete') is not False for p in plays)
                        self.assertEqual(player['stats']['batting']['plateAppearances'], appearances)

    def test_pickoff_third_out_also_keeps_the_batter(self):
        game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=1)
        outcomes = iter(['Walk', 'Strikeout', 'Strikeout', 'Pickoff 1B'])

        def at_bat(batter, pitcher):
            outcome = next(outcomes)
            event = {'index': 0, 'isPitch': outcome != 'Pickoff 1B',
                     'count': {'balls': 0, 'strikes': 0}, 'details': {'code': 'B'}}
            if outcome == 'Pickoff 1B':
                events = []
                with patch.object(game.strategy_rng, 'random', side_effect=[0.01, 0.9]):
                    game._record_pickoff_throw(events, 0, 0, pitcher)
                return outcome, None, events
            return outcome, None, [event]

        with patch.object(game, '_simulate_at_bat', side_effect=at_bat), \
                patch.object(game, '_manage_between_innings'), \
                patch.object(game, '_manage_pitching_change'):
            game._simulate_half_inning()
        self.assertEqual(game.team2_batter_idx, 3)
        play = game.gameday_data['liveData']['plays']['allPlays'][-1]
        self.assertFalse(play['about']['isComplete'])
        self.assertEqual(play['runners'][0]['movement']['outBase'], '1B')


class TestTwoOutAdvancement(unittest.TestCase):
    def test_runner_on_third_scores_on_every_kind_of_two_out_hit(self):
        for trajectory in ('ground_ball', 'line_drive', 'fly_ball'):
            for position in ('SS', '2B', 'CF'):
                for outcome in ('Single', 'Double', 'Triple', 'Home Run'):
                    with self.subTest(trajectory=trajectory, position=position, outcome=outcome):
                        ball = fieldsim.BattedBall(outcome, position, trajectory, position, 0,
                                                  (0, 148), 148, release=4.0, release_point=(0, 148))
                        dests, thrown_out = fieldsim.advance_on_hit(ball, outcome, {3: 1.0}, 2, random.Random(0))
                        self.assertEqual(dests, {3: 4})
                        self.assertFalse(thrown_out)

    def test_runner_holds_on_an_unforced_infield_hit_with_fewer_than_two_out(self):
        ball = fieldsim.BattedBall('Single', 'SS', 'ground_ball', 'SS', 0, (0, 148), 148)
        for outs in (0, 1):
            dests, _ = fieldsim.advance_on_hit(ball, 'Single', {3: 1.0}, outs, random.Random(0))
            self.assertEqual(dests, {3: 3})

    def test_two_out_infield_hits_keep_runners_in_order_and_clear_the_batters_base(self):
        for outcome, expected in (('Single', {3: 4, 2: 3, 1: 2}), ('Double', {3: 4, 2: 4, 1: 3})):
            ball = fieldsim.BattedBall(outcome, 'SS', 'ground_ball', 'SS', 0, (0, 148), 148)
            dests, thrown_out = fieldsim.advance_on_hit(ball, outcome, {1: 1.0, 2: 1.0, 3: 1.0}, 2, random.Random(0))
            self.assertEqual(dests, expected)
            self.assertFalse(thrown_out)

    def test_fallback_advances_runners_with_a_two_out_head_start(self):
        game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=1)
        batter = game.team2_lineup[3]
        game._play_field = None
        for outcome, base in (('Single', 2), ('Double', 1), ('Triple', 1), ('Home Run', 1)):
            scores = []
            for outs in (0, 2):
                runs = 0
                for seed in range(300):
                    game.outs = outs
                    game.bases = [None, None, None]
                    game.bases[base - 1] = game.team2_lineup[0]['legal_name']
                    game.game_rng.seed(seed)
                    with patch('baseball.FIELD_SIM', False):
                        result = game._advance_runners(outcome, batter)
                    runs += result['runs']
                scores.append(runs)
            if outcome in ('Single', 'Double'):
                self.assertGreater(scores[1], scores[0] + 40, (outcome, scores))
            else:
                self.assertEqual(scores, [300 * (2 if outcome == 'Home Run' else 1)] * 2)


class TestNarrativeFieldingBugs(unittest.TestCase):
    def test_contact_never_prints_raw_pitch_velocity(self):
        for seed in range(150):
            announcer = renderer(seed)
            with patch.object(announcer.rng_flow, 'random', return_value=1.0), \
                    patch.object(announcer, '_get_batted_ball_verb', return_value=('fists one', 'verbs')):
                text = announcer._generate_play_description(
                    'Single', {'location': 'RC', 'launchSpeed': 85.0, 'launchAngle': 15.0},
                    {'type': 'Changeup', 'velo': 84.9}, 'Rex Power')
            self.assertNotRegex(text, r'\d(?:\.\d)? mph|84\.9')

    def test_home_run_calls_always_say_it_clears_the_fence(self):
        for seed in range(250):
            text = renderer(seed)._generate_play_description(
                'Home Run', {'location': 'DLF', 'launchSpeed': 104.0, 'launchAngle': 30.0},
                {'type': 'Fastball', 'velo': 95.0}, 'Rex Power', 'LF', 'Chase')
            self.assertRegex(text.lower(), r'home run|homer|gone|over the (?:wall|fence)')

    def test_a_generic_home_run_call_also_finishes_over_the_wall(self):
        announcer = renderer()
        announcer.gameday_data['gameData']['broadcast'] = {'strictFacts': True}
        with patch.object(announcer.rng_flow, 'random', return_value=1.0), \
                patch.object(announcer, '_get_batted_ball_verb', return_value=('hits one a mile in the air', 'verbs')):
            text = announcer._generate_play_description(
                'Home Run', {'location': 'LF', 'launchSpeed': 100.0, 'launchAngle': 55.0},
                {'type': 'Fastball'}, 'Rex Power')
        self.assertIn('carries over the wall', text)

    def test_forceout_names_both_fielders_and_the_base_without_extension_fields(self):
        for base, positions in (('2B', ('SS', '2B')), ('3B', ('SS', '3B')), ('4B', ('3B', 'C'))):
            play = {'matchup': {'batter': {'id': 1}}, 'runners': [{
                'details': {'runner': {'id': 2}},
                'movement': {'isOut': True, 'outBase': base},
                'credits': [{'credit': credit, 'position': {'abbreviation': pos},
                             'player': {'id': i + 10, 'fullName': name}}
                            for i, (credit, pos, name) in enumerate(zip(
                                ('assist', 'putout'), positions, ('Sam Chase', 'Alex Chen')))]}]}
            for seed in range(40):
                text = renderer(seed)._generate_play_description(
                    'Forceout', {'location': positions[0], 'trajectory': 'ground_ball'},
                    {'type': 'Sinker'}, 'Rex Power', positions[0], 'Chase', result_outs=3, play=play)
                self.assertIn('Chase', text)
                self.assertIn('Chen', text)
                self.assertIn({'2B': 'second', '3B': 'third', '4B': 'plate'}[base], text)
                self.assertNotIn('defense records', text)

    def test_a_batter_does_not_get_the_same_wall_double_call_twice(self):
        hit = {'location': 'RC', 'trajectory': 'fly_ball', 'launchSpeed': 100.0, 'launchAngle': 28.0,
               'depth': 'wall', 'lane': 'right_center', 'hardness': 'hard',
               'coordinates': {'coordX': 160, 'coordY': 55}, 'totalDistance': 370}
        announcer = renderer()
        calls = []
        choose_top = lambda pool: next((t for t in pool if 'top of the wall' in t), pool[0])
        with patch.object(announcer.rng_play, 'choice', side_effect=choose_top), \
                patch.object(announcer.rng_flow, 'random', return_value=0.0):
            for _ in range(2):
                calls.append(announcer._generate_play_description(
                    'Double', hit, {'type': 'Fastball'}, 'Rex Power'))
        self.assertIn('top of the wall', calls[0])
        self.assertNotIn('top of the wall', calls[1])


class TestFieldingCalibration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {seed: simulate(seed).gameday_data for seed in range(30200, 30360)}

    def test_groundouts_and_middle_infield_forceouts_match_real_feeds(self):
        groundouts = forces = middle_forces = 0
        for data in self.games.values():
            for play in data['liveData']['plays']['allPlays']:
                groundouts += play['result']['event'] == 'Groundout'
                if play['result']['event'] == 'Forceout':
                    forces += 1
                    out = next(r for r in play['runners'] if r['movement']['isOut'])
                    chain = [c['position']['abbreviation'] for c in out.get('credits', [])]
                    middle_forces += chain in (['2B', 'SS'], ['SS', '2B'])
        # 136 real feeds: 12.87 groundouts/game, 54.6% of forces are 4-6 or 6-4.
        self.assertTrue(11.5 < groundouts / len(self.games) < 13.6, groundouts / len(self.games))
        self.assertTrue(0.40 < middle_forces / forces < 0.75, middle_forces / forces)

    def test_runner_from_first_scores_on_about_a_third_of_doubles(self):
        opportunities = scores = 0
        for data in self.games.values():
            for play in data['liveData']['plays']['allPlays']:
                if play['result']['event'] != 'Double':
                    continue
                for runner in play['runners']:
                    if runner['movement'].get('originBase') == '1B':
                        opportunities += 1
                        scores += runner['movement'].get('end') == 'score'
        self.assertGreater(opportunities, 90)
        self.assertTrue(0.20 < scores / opportunities < 0.46, scores / opportunities)

    def test_pitchers_leave_pop_ups_to_the_infielders(self):
        popups = 0
        for data in self.games.values():
            for play in data['liveData']['plays']['allPlays']:
                hit = next((e['hitData'] for e in play['playEvents'] if 'hitData' in e), {})
                if hit.get('trajectory') == 'popup' and play['result']['event'] == 'Pop Out':
                    popups += 1
                    self.assertNotEqual(hit.get('location'), 'P')
        self.assertGreater(popups, 200)

    def test_ground_ball_outs_are_described_at_the_fielders_location(self):
        checked = 0
        for seed, data in list(self.games.items())[:15]:
            announcer = NarrativeRenderer(data, seed=seed)
            lines = announcer.render().splitlines()
            for index, play in enumerate(data['liveData']['plays']['allPlays']):
                if play['result']['event'] not in ('Groundout', 'Forceout', 'Double Play'):
                    continue
                checked += 1
                low, high = announcer._play_line_map[index]
                text = ' '.join(lines[low:high])
                self.assertNotRegex(text, r'(?i)(?:grounder|bouncer|ball|roller) (?:to|through) (?:\w+ )?(?:left|center|right) field')
        self.assertGreater(checked, 150)

    def test_lineup_slot_phrases_use_the_recorded_order(self):
        cleanup = top = lineup_slots = 0
        ordinals = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth']
        for seed, data in list(self.games.items())[:25]:
            announcer = NarrativeRenderer(data, seed=seed)
            lines = announcer.render().splitlines()
            boxscore = data['liveData']['boxscore']['teams']
            starting_orders = {side: [p['person']['id'] for p in sorted(
                (p for p in box['players'].values()
                 if p.get('battingOrder') and int(p['battingOrder']) % 100 == 0),
                key=lambda p: int(p['battingOrder']))] for side, box in boxscore.items()}
            for line in lines[:announcer._play_line_map[0][0]]:
                match = re.search(r'\b(?:batting|bat) (' + '|'.join(ordinals) + r')\b', line.lower())
                spot = ordinals.index(match.group(1)) if match else None
                if 'cleanup' in line:
                    spot = 3
                elif re.search(r'lead off|leading off|lead things off|leadoff', line.lower()):
                    spot = 0
                if spot is not None:
                    lineup_slots += 1
                    names = [data['gameData']['players'][f"ID{starting_orders[side][spot]}"]['fullName']
                             for side in ('away', 'home')]
                    self.assertTrue(any(name in line for name in names), line)
            for index, play in enumerate(data['liveData']['plays']['allPlays']):
                low, high = announcer._play_line_map[index]
                text = ' '.join(lines[low:high]).split('...')[0]
                side = 'away' if play['about']['isTopInning'] else 'home'
                batter = play['matchup']['batter']['id']
                slot = int(boxscore[side]['players'][f'ID{batter}']['battingOrder']) // 100 - 1
                if 'cleanup hitter' in text:
                    cleanup += 1
                    self.assertEqual(slot, 3)
                if re.search(r'top of the .+ order|Batting first', text):
                    top += 1
                    self.assertEqual(slot, 0)
        self.assertGreater(cleanup, 15)
        self.assertGreater(top, 5)
        self.assertGreater(lineup_slots, 250)


if __name__ == '__main__':
    unittest.main()
