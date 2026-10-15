"""Real-feed details that used to disappear or contradict the fictional rosters."""
import copy
import json
import random
import unittest

from anonymize_real_gameday import anonymize_description, anonymize_gameday_data
import blind_judge
from renderers import NarrativeRenderer
from teams import TEAMS


POSITIONS = {p['position']['code']: p['position'] for p in TEAMS['BAY_BOMBERS']['players']}


def person(pid, position, bat='R', throws='R'):
    return {'id': pid, 'fullName': f'Real Player{pid}',
            'primaryPosition': copy.deepcopy(POSITIONS[position]),
            'batSide': {'code': bat, 'description': {'R': 'Right', 'L': 'Left', 'S': 'Switch'}[bat]},
            'pitchHand': {'code': throws, 'description': 'Left' if throws == 'L' else 'Right'}}


def pitch(index=0, code='X'):
    return {'index': index, 'isPitch': True,
            'count': {'balls': int(code == 'B'), 'strikes': int(code in ('C', 'S')), 'outs': 0},
            'details': {'code': code, 'description': 'In play' if code == 'X' else 'Ball',
                        'type': {'code': 'FF', 'description': 'Four-Seam Fastball'}},
            'pitchData': {'startSpeed': 93.0, 'zone': 11},
            **({'hitData': {'trajectory': 'line_drive', 'location': '9', 'launchSpeed': 95.0,
                            'launchAngle': 15.0}} if code == 'X' else {})}


def runner(pid, start, end, index=0, kind='single', out=False, credits=()):
    return {'movement': {'originBase': start, 'start': start, 'end': None if out else end,
                         'outBase': end if out else None, 'isOut': out, 'outNumber': 3 if out else None},
            'details': {'runner': {'id': pid, 'fullName': f'Real Player{pid}'},
                        'eventType': kind, 'playIndex': index, 'movementReason': 'r_adv_play'},
            'credits': list(credits)}


def credit(pid, position, kind='f_putout'):
    return {'player': {'id': pid}, 'position': POSITIONS[position], 'credit': kind}


def feed(event='Single', events=None, runners=None, outs=0):
    people = [person(1, '6', 'R'), person(2, '1', throws='L'),
              person(3, '4', 'L'), person(4, '9', 'R'), person(5, '2', 'R')]
    play = {'about': {'atBatIndex': 0, 'isTopInning': True, 'halfInning': 'top', 'inning': 1},
            'matchup': {'batter': {'id': 1, 'fullName': 'Real Player1'},
                        'pitcher': {'id': 2, 'fullName': 'Real Player2'},
                        'batSide': people[0]['batSide'], 'pitchHand': people[1]['pitchHand']},
            'result': {'type': 'atBat', 'event': event, 'awayScore': 0, 'homeScore': 0, 'rbi': 0},
            'count': {'balls': 0, 'strikes': 0, 'outs': outs},
            'playEvents': events if events is not None else [pitch()],
            'runners': runners if runners is not None else [runner(1, None, '1B')]}
    return {'gameData': {'teams': {'home': {}, 'away': {}},
                         'players': {f'ID{p["id"]}': p for p in people}},
            'liveData': {'plays': {'allPlays': [play]},
                         'linescore': {'teams': {side: {'runs': 0, 'hits': 1, 'errors': 0}
                                                for side in ('home', 'away')}, 'innings': []}}}


class TestRealIdentities(unittest.TestCase):
    def test_anonymization_is_seeded_and_keeps_real_hands_and_positions(self):
        raw = feed(runners=[runner(1, None, '1B', credits=[credit(4, '9', 'f_fielded_ball')])])
        before = copy.deepcopy(raw)
        one = anonymize_gameday_data(raw, TEAMS, seed=3)
        random.seed(999)
        two = anonymize_gameday_data(raw, TEAMS, seed=3)
        self.assertEqual(one, two)
        self.assertEqual(raw, before)
        self.assert_names_fit(one)
        people = list(one['gameData']['players'].values())
        self.assertEqual(len(people), len({p['fullName'] for p in people}))
        self.assertEqual(len(people), len({p['lastName'] for p in people}))
        matchup = one['liveData']['plays']['allPlays'][0]['matchup']
        pitcher = one['gameData']['players'][f'ID{matchup["pitcher"]["id"]}']
        self.assertEqual(pitcher['pitchHand']['code'], 'L')

    def assert_names_fit(self, data):
        canonical = {p['legal_name']: (side, p) for side, key in (
            ('home', 'BAY_BOMBERS'), ('away', 'PC_PILOTS')) for p in TEAMS[key]['players']}
        sides = blind_judge.player_sides(data)
        for person in data['gameData']['players'].values():
            if person['fullName'] not in canonical:
                continue
            side, expected = canonical[person['fullName']]
            if person['id'] in sides:
                self.assertEqual(sides[person['id']], side)
            self.assertEqual(person['primaryPosition']['code'], expected['position']['code'])
            hand = 'pitchHand' if expected['position']['code'] == '1' else 'batSide'
            self.assertEqual(person[hand]['code'], expected.get(hand, {}).get('code', 'R'))

    def test_handwritten_names_fit_the_same_rosters(self):
        template = anonymize_gameday_data(feed(), TEAMS)['gameData']
        for episode in blind_judge.SLEEP_EPISODES:
            with self.subTest(episode=episode):
                game = blind_judge.sleep_game(episode)
                self.assert_names_fit(blind_judge.remap_names(game, template, seed=17))

    def test_fielder_who_never_bats_stays_on_his_team(self):
        raw = feed(runners=[runner(1, None, '1B', credits=[credit(4, '9', 'f_fielded_ball')])])
        data = anonymize_gameday_data(raw, TEAMS)
        p = data['liveData']['plays']['allPlays'][0]
        self.assertEqual(blind_judge.player_sides(data)[p['runners'][0]['credits'][0]['player']['id']], 'home')
        for seed in range(8):
            remapped = blind_judge.remap_names(data, data['gameData'], seed)
            self.assert_names_fit(remapped)

    def test_overflow_names_do_not_change_hands_or_positions_between_games(self):
        seen = {}
        for position in POSITIONS:
            for hand in ('R', 'L', 'S'):
                raw = feed()
                raw['gameData']['players']['ID1'] = person(1, position, hand, throws=hand if hand != 'S' else 'R')
                raw['liveData']['plays']['allPlays'][0]['matchup']['batSide'] = raw['gameData']['players']['ID1']['batSide']
                data = anonymize_gameday_data(raw, TEAMS)
                ref = data['liveData']['plays']['allPlays'][0]['matchup']['batter']
                role = (position, hand if position != '1' else raw['gameData']['players']['ID1']['pitchHand']['code'])
                self.assertEqual(seen.setdefault(ref['fullName'], role), role)

    def test_names_are_replaced_once_in_free_text(self):
        mapping = {'Joe Gibson': 'Ben Logan', 'Ben Logan': 'Joe Gibson'}
        self.assertEqual(anonymize_description("Joe Gibson's throw to Ben Logan.", mapping),
                         "Ben Logan's throw to Joe Gibson.")

    def test_harness_free_text_does_not_rename_a_replacement_again(self):
        raw = feed()
        raw['gameData']['players']['ID1']['fullName'] = 'Alex Chase'
        raw['gameData']['players']['ID3']['fullName'] = 'Caleb Jones'
        raw['gameData']['players']['ID3']['batSide'] = {'code': 'R', 'description': 'Right'}
        raw['liveData']['plays']['allPlays'][0]['result']['description'] = 'Alex Chase throws to Caleb Jones.'
        data = blind_judge.remap_names(raw, anonymize_gameday_data(feed(), TEAMS)['gameData'], seed=1)
        players = data['gameData']['players']
        self.assertEqual(data['liveData']['plays']['allPlays'][0]['result']['description'],
                         f"{players['ID1']['fullName']} throws to {players['ID3']['fullName']}.")

    def test_designated_hitter_keeps_the_batters_side(self):
        raw = feed()
        raw['liveData']['plays']['allPlays'][0]['matchup']['batter'] = {'id': 2}
        raw['liveData']['plays']['allPlays'][0]['matchup']['batSide'] = {'code': 'L', 'description': 'Left'}
        raw['gameData']['players']['ID2']['batSide'] = {'code': 'L', 'description': 'Left'}
        data = blind_judge.add_designated_hitter(raw)
        self.assertEqual(data['gameData']['players']['ID990002']['batSide']['code'], 'L')


class TestRealFeedEvents(unittest.TestCase):
    def test_credits_keep_the_position_and_use_the_renderers_credit_names(self):
        raw = feed(runners=[runner(1, None, '1B', credits=[credit(4, '9', 'f_fielded_ball')])])
        data = anonymize_gameday_data(raw, TEAMS)
        cr = data['liveData']['plays']['allPlays'][0]['runners'][0]['credits'][0]
        self.assertEqual(cr['credit'], 'fielded_ball')
        self.assertEqual(cr['position']['abbreviation'], 'RF')

    def test_a_prior_steal_does_not_supply_the_batted_balls_fielder(self):
        raw = feed('Flyout', events=[pitch(0, 'B'), pitch(1)], outs=3, runners=[
            runner(3, '1B', '2B', index=0, kind='caught_stealing_2b', out=True,
                   credits=[credit(5, '2', 'f_assist'), credit(4, '6')]),
            runner(1, None, '1B', index=1, kind='field_out', out=True, credits=[credit(4, '9')])])
        raw['liveData']['plays']['allPlays'][0]['playEvents'][1]['hitData']['trajectory'] = 'fly_ball'
        data = anonymize_gameday_data(raw, TEAMS)
        captured = []

        class CaptureFielder(NarrativeRenderer):
            def _generate_play_description(self, *args, **kwargs):
                captured.append((args[4], args[5]))
                return super()._generate_play_description(*args, **kwargs)

        CaptureFielder(data, seed=1).render()
        self.assertEqual(captured[0][0], 'RF')

    def test_pitch_types_are_not_dropped(self):
        events = [pitch(i, 'B') for i in range(3)]
        for event, code, name in zip(events, ('FF', 'ST', 'KC'), ('Four-Seam Fastball', 'Sweeper', 'Knuckle Curve')):
            event['details']['type'] = {'code': code, 'description': name}
        raw = feed('Walk', events=events)
        data = anonymize_gameday_data(raw, TEAMS)
        actual = data['liveData']['plays']['allPlays'][0]['playEvents']
        self.assertEqual([e['details']['type'] for e in actual], [e['details']['type'] for e in events])

    def test_runner_advances_attached_to_a_pitch_are_narrated(self):
        for kind, expected in (('defensive_indiff', 'without a throw'), ('balk', 'balk'),
                               ('forced_balk', 'balk'), ('error', 'on the error')):
            with self.subTest(kind=kind):
                raw = feed('Incomplete', events=[pitch(0, 'B')],
                           runners=[runner(3, '1B', '2B', kind=kind)])
                data = anonymize_gameday_data(raw, TEAMS)
                events = data['liveData']['plays']['allPlays'][0]['playEvents']
                self.assertEqual(len(events), 2)
                text = NarrativeRenderer(data, seed=1).render()
                self.assertIn(expected, text)
                self.assertIn('second', text)

    def test_a_steal_followed_by_an_error_is_not_two_steals(self):
        action = {'index': 1, 'isPitch': False, 'details': {'eventType': 'stolen_base_2b', 'description': 'raw log'}}
        raw = feed('Incomplete', events=[pitch(0, 'B'), action], runners=[
            runner(3, '1B', '2B', index=1, kind='stolen_base_2b'),
            runner(3, '2B', '3B', index=1, kind='error')])
        data = anonymize_gameday_data(raw, TEAMS)
        text = NarrativeRenderer(data, seed=1).render()
        self.assertEqual(text.count('steals second'), 1)
        self.assertNotIn('steals third', text)
        self.assertIn('third on the error', text)

    def test_batter_taking_an_extra_base_on_a_hit_is_explained(self):
        for kind, cause in (('error', 'on the error'), ('single', 'on the play')):
            raw = feed(runners=[runner(1, None, '1B'), runner(1, '1B', '2B', kind=kind)])
            text = NarrativeRenderer(anonymize_gameday_data(raw, TEAMS), seed=1).render()
            self.assertIn(f'moves up to second {cause}', text)

    def test_successive_bases_on_one_advance_are_collapsed(self):
        raw = feed('Incomplete', events=[pitch(0, 'B')], runners=[
            runner(3, '1B', '2B', kind='defensive_indiff'),
            runner(3, '2B', '3B', kind='defensive_indiff')])
        text = NarrativeRenderer(anonymize_gameday_data(raw, TEAMS), seed=1).render()
        self.assertEqual(text.count('without a throw'), 1)
        self.assertIn('third without a throw', text)

    def test_terminal_caught_stealing_is_said_once(self):
        for prefix in ('caught_stealing', 'pickoff_caught_stealing'):
            with self.subTest(prefix=prefix):
                raw = feed('Caught Stealing 2B' if prefix == 'caught_stealing' else 'Pickoff Caught Stealing 2B',
                           events=[pitch(0, 'B')], outs=3,
                           runners=[runner(3, '1B', '2B', kind=prefix + '_2b', out=True)])
                text = NarrativeRenderer(anonymize_gameday_data(raw, TEAMS), seed=1).render()
                self.assertEqual(text.lower().count('caught stealing'), 1, text)

    def test_a_runner_scoring_during_a_caught_stealing_is_safe(self):
        raw = feed('Caught Stealing 2B', events=[pitch(0, 'B')], outs=3, runners=[
            runner(1, '3B', 'score', kind='caught_stealing_2b'),
            runner(3, '1B', '2B', kind='caught_stealing_2b', out=True)])
        data = anonymize_gameday_data(raw, TEAMS)
        text = NarrativeRenderer(data, seed=1).render()
        self.assertEqual(text.lower().count('caught stealing'), 1)
        self.assertIn('comes home', text)
        self.assertNotIn('caught stealing home', text)

    def test_substitutions_use_structured_announcements(self):
        for kind, position, expected in (('offensive_substitution', '12', 'comes in to run'),
                                         ('defensive_substitution', '9', 'comes in to play right'),
                                         ('defensive_switch', '9', 'will play right')):
            with self.subTest(kind=kind):
                event = {'index': 0, 'isPitch': False, 'player': {'id': 4}, 'replacedPlayer': {'id': 3},
                         'position': {'code': position},
                         'details': {'eventType': kind, 'description': 'Substitution for Real Team: raw log.'}}
                raw = feed(events=[event, pitch(1)])
                raw['liveData']['plays']['allPlays'][0]['runners'][0]['details']['playIndex'] = 1
                data = anonymize_gameday_data(raw, TEAMS)
                text = NarrativeRenderer(data, seed=1).render()
                self.assertIn(expected, text)
                self.assertNotIn('Substitution for', text)
                self.assertNotIn('raw log', json.dumps(data))

    def test_pinch_runner_base_can_already_name_the_incoming_player(self):
        renderer = NarrativeRenderer(feed(), seed=1)
        renderer.runners_on_base = {'1B': None, '2B': 'Real Player4', '3B': None}
        event = {'player': {'id': 4}, 'replacedPlayer': {'id': 3},
                 'position': {'code': '12'},
                 'details': {'eventType': 'offensive_substitution'}}
        self.assertEqual(renderer._position_substitution(event),
                         'Real Player4 comes in to run for Real Player3 at second.')
        self.assertEqual(renderer.runners_on_base['2B'], 'Real Player4')

    def test_double_play_notation_excludes_an_earlier_pickoff_out(self):
        from renderers.narrative.play_description import build_dp_notation
        action = {'index': 1, 'isPitch': False, 'details': {'runners': [{'isOut': True}]}}
        play = {'playEvents': [action, pitch(2)], 'runners': [
            runner(3, '2B', '3B', index=1, kind='pickoff_caught_stealing_3b', out=True,
                   credits=[credit(2, '1', 'f_assist'), credit(4, '4', 'f_assist'), credit(5, '5')]),
            runner(4, '1B', '2B', index=2, kind='grounded_into_double_play', out=True,
                   credits=[credit(3, '6', 'f_assist'), credit(5, '4')]),
            runner(1, None, '1B', index=2, kind='grounded_into_double_play', out=True,
                   credits=[credit(5, '4', 'f_assist'), credit(4, '3')]),
        ]}
        self.assertEqual(build_dp_notation(play), '6-4-3')

    def test_real_bunt_labels_get_a_complete_out(self):
        for label, trajectory in (('Sac Bunt', 'bunt_grounder'), ('Bunt Groundout', 'bunt_grounder'),
                                  ('Bunt Pop Out', 'bunt_popup'), ('Bunt Lineout', 'bunt_line_drive')):
            raw = feed(label, runners=[runner(1, None, '1B', kind='field_out', out=True,
                                              credits=[credit(2, '1', 'f_assist'), credit(4, '3')])], outs=3)
            raw['liveData']['plays']['allPlays'][0]['playEvents'][0]['hitData']['trajectory'] = trajectory
            for seed in range(12):
                with self.subTest(label=label, seed=seed):
                    text = NarrativeRenderer(anonymize_gameday_data(raw, TEAMS), seed=seed).render()
                    self.assertRegex(text, r'(?i)retir|out|catch|caught|end the inning|end the frame')

    def test_fielders_choice_out_and_air_double_play_keep_the_outs(self):
        raw = feed('Fielders Choice Out', runners=[
            runner(3, '1B', '2B', out=True, credits=[credit(4, '6', 'f_assist'), credit(5, '4')]),
            runner(1, None, '1B')], outs=1)
        raw['liveData']['plays']['allPlays'][0]['playEvents'][0]['hitData']['trajectory'] = 'ground_ball'
        text = NarrativeRenderer(anonymize_gameday_data(raw, TEAMS), seed=1).render()
        self.assertIn("fielder's choice", text)
        self.assertIn('is out', text)
        for label in ('Double Play', 'Sac Fly Double Play'):
            raw = feed(label, runners=[runner(1, None, '1B', out=True, credits=[credit(4, '9')]),
                                      runner(3, '1B', '1B', out=True, credits=[credit(4, '9', 'f_assist'), credit(5, '3')])], outs=3)
            raw['liveData']['plays']['allPlays'][0]['runners'][1]['details']['movementReason'] = 'r_doubled_off'
            text = NarrativeRenderer(anonymize_gameday_data(raw, TEAMS), seed=1).render()
            self.assertIn('makes the catch', text)
            self.assertIn('doubled off at first', text)
            self.assertIn('double play', text)

    def test_a_contact_only_single_always_gets_its_result(self):
        data = anonymize_gameday_data(feed(), TEAMS)
        for seed in range(120):
            renderer = NarrativeRenderer(data, seed=seed)
            renderer._reset_render_state()
            renderer._optional = lambda name: False
            text = renderer._generate_play_description('Single', {'trajectory': 'line_drive', 'location': 'RF'},
                                                       {'type': 'Fastball'}, 'Caleb Jones', result_outs=1)
            self.assertNotRegex(text, r'^(?:Line drive,|Lined sharply into)[^.]*\.$')


if __name__ == '__main__':
    unittest.main()
