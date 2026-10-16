"""Real-feed details that used to disappear or contradict the fictional rosters."""
import copy
import json
import random
import unittest
from unittest.mock import patch

from anonymize_real_gameday import (
    anonymize_description, anonymize_gameday_data, anonymize_player_reference, assign_player_names,
    collect_players, create_player_mapping, validate_player_names,
)
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
    box = {side: {'players': {}} for side in ('home', 'away')}
    for p in people:
        side = 'away' if p['id'] == 1 else 'home'
        box[side]['players'][f'ID{p["id"]}'] = {'person': {'id': p['id']}}
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
                         'boxscore': {'teams': box},
                         'linescore': {'teams': {side: {'runs': 0, 'hits': 1, 'errors': 0}
                                                for side in ('home', 'away')}, 'innings': []}}}


class TestRealIdentities(unittest.TestCase):
    def test_non_player_event_references_are_not_named_and_their_descriptions_are_dropped(self):
        for kind, pid, uid, description in (
                ('ejection', 667437, 605672,
                 'Giants manager Tony Vitello ejected by HP umpire Jeremie Rehak.'),
                ('umpire_substitution', 545402, 545402,
                 'Umpire change: John Bacon replaces umpire Junior Valentine.')):
            with self.subTest(kind=kind):
                event = {'isPitch': False, 'index': -1,
                         'player': {'id': pid, 'link': f'/api/v1/people/{pid}'},
                         'umpire': {'id': uid, 'link': f'/api/v1/people/{uid}'},
                         'details': {'eventType': kind, 'description': description}}
                raw = feed(events=[event, pitch()])
                raw['liveData']['boxscore']['officials'] = [
                    {'official': event['umpire'], 'officialType': 'Home Plate'}]
                self.assertEqual(set(collect_players(raw)), set(range(1, 6)))
                self.assertEqual(set(assign_player_names(raw, TEAMS, random.Random(1))), set(range(1, 6)))
                validate_player_names(raw)
                data = anonymize_gameday_data(raw, TEAMS)
                validate_player_names(data)
                self.assertEqual(len(data['gameData']['players']), 5)
                self.assertEqual(len(data['liveData']['plays']['allPlays'][0]['playEvents']), 1)
                for name in ('Tony Vitello', 'Jeremie Rehak', 'John Bacon', 'Junior Valentine'):
                    self.assertNotIn(name, json.dumps(data))

    def test_zero_violation_placeholder_is_not_a_player(self):
        event = pitch()
        event['details']['violation'] = {'type': 'defensive_shift', 'player': {'id': 0}}
        raw = feed(events=[event])
        self.assertNotIn(0, collect_players(raw))
        self.assertNotIn(0, assign_player_names(raw, TEAMS, random.Random(1)))
        validate_player_names(raw)
        data = anonymize_gameday_data(raw, TEAMS)
        validate_player_names(data)
        self.assertEqual(len(data['gameData']['players']), 5)
        self.assertNotIn('violation', data['liveData']['plays']['allPlays'][0]['playEvents'][0]['details'])

    def test_boxscore_only_player_is_collected_and_named(self):
        raw = feed()
        raw['liveData']['boxscore']['teams']['away']['players']['ID6'] = {
            'person': {'id': 6, 'fullName': 'Real Player6'}, 'position': POSITIONS['4']}
        self.assertIn(6, collect_players(raw))
        self.assertIn(6, assign_player_names(raw, TEAMS, random.Random(1)))
        data = anonymize_gameday_data(raw, TEAMS)
        validate_player_names(data)
        self.assertEqual(len(data['gameData']['players']), 6)

    def test_player_role_does_not_depend_on_reference_size(self):
        raw = feed()
        del raw['gameData']['players']['ID1']
        del raw['liveData']['boxscore']['teams']['away']['players']['ID1']
        ref = raw['liveData']['plays']['allPlays'][0]['matchup']['batter']
        ref.pop('fullName')
        ref.update(link='/api/v1/people/1', firstName='Real', lastName='Player1')
        raw['liveData']['plays']['allPlays'][0]['runners'] = []
        self.assertIn(1, collect_players(raw))
        with self.assertRaisesRegex(ValueError, 'player 1.*missing from gameData.players'):
            validate_player_names(raw)
        validate_player_names(anonymize_gameday_data(raw, TEAMS))

    def test_player_without_a_side_is_an_error(self):
        raw = feed()
        raw['gameData']['players']['ID6'] = person(6, '6')
        with self.assertRaisesRegex(ValueError, 'player 6.*no team side'):
            assign_player_names(raw, TEAMS, random.Random(1))

    def test_pitching_role_uses_throwing_hand_despite_boxscore_position(self):
        roster_names = {p['legal_name'] for team in TEAMS.values() for p in team['players']}
        for role in ('matchup', 'pitching_substitution'):
            for pitching_credit in (False, True):
                with self.subTest(role=role, pitching_credit=pitching_credit):
                    credits = [credit(4, '9')]
                    if pitching_credit:
                        credits.append(credit(4, '1'))
                    raw = feed(runners=[runner(1, None, '1B', credits=credits)])
                    raw['liveData']['boxscore']['teams']['home']['players']['ID4']['position'] = POSITIONS['9']
                    play = raw['liveData']['plays']['allPlays'][0]
                    if role == 'matchup':
                        relief = copy.deepcopy(play)
                        relief['matchup']['pitcher'] = {'id': 4}
                        raw['liveData']['plays']['allPlays'].append(relief)
                    else:
                        play['playEvents'].insert(0, {
                            'isPitch': False, 'index': -1, 'player': {'id': 4},
                            'replacedPlayer': {'id': 2}, 'position': POSITIONS['1'],
                            'details': {'eventType': 'pitching_substitution'}})
                    names = {}
                    for bat, throws in (('R', 'R'), ('L', 'R'), ('R', 'L')):
                        raw['gameData']['players']['ID4'] = person(4, '9', bat, throws)
                        if role == 'matchup':
                            relief['matchup']['pitchHand'] = raw['gameData']['players']['ID4']['pitchHand']
                        mapping, _ = create_player_mapping(raw, TEAMS, random.Random(1))
                        names[bat, throws] = mapping[4]['legal_name']
                        self.assertNotIn(names[bat, throws], roster_names)
                        validate_player_names(anonymize_gameday_data(raw, TEAMS))
                    self.assertEqual(names['R', 'R'], names['L', 'R'])
                    self.assertNotEqual(names['R', 'R'], names['R', 'L'])
                    raw['gameData']['players']['ID4']['primaryPosition'] = POSITIONS['1']
                    mapping, _ = create_player_mapping(raw, TEAMS, random.Random(1))
                    self.assertEqual(mapping[4]['legal_name'], names['R', 'L'])

    def test_pitching_substitution_does_not_change_the_replaced_hitters_role(self):
        raw = feed()
        raw['gameData']['players']['ID4'] = person(4, '9', bat='R', throws='L')
        before, _ = create_player_mapping(raw, TEAMS)
        raw['liveData']['plays']['allPlays'][0]['playEvents'].insert(0, {
            'isPitch': False, 'index': -1, 'player': {'id': 2},
            'replacedPlayer': {'id': 4}, 'position': POSITIONS['1'],
            'details': {'eventType': 'pitching_substitution'}})
        after, _ = create_player_mapping(raw, TEAMS)
        self.assertEqual(before[4], after[4])

    def test_multiple_positions_do_not_take_a_single_position_roster_name(self):
        raw = feed(runners=[runner(1, None, '1B', credits=[credit(2, '1'), credit(2, '9')])])
        mapping, _ = create_player_mapping(raw, TEAMS)
        self.assertNotIn(mapping[2]['legal_name'],
                         {p['legal_name'] for p in TEAMS['BAY_BOMBERS']['players']})

    def test_unused_roster_pitcher_keeps_his_throwing_hand(self):
        raw = feed()
        raw['gameData']['players']['ID6'] = person(6, '1', bat='R', throws='L')
        raw['liveData']['boxscore']['teams']['home']['players']['ID6'] = {
            'person': {'id': 6}, 'position': POSITIONS['1']}
        self.assert_names_fit(anonymize_gameday_data(raw, TEAMS))

    def test_unmapped_player_reference_fails_before_returning_a_real_id(self):
        for ref in ({'id': 123456}, {'id': 123456, 'fullName': 'Real Player'}):
            with self.subTest(ref=ref):
                with self.assertRaisesRegex(ValueError, 'player 123456.*missing from.*mapping'):
                    anonymize_player_reference(ref, {})

    def test_unused_roster_players_keep_their_sides_when_remapped(self):
        raw = feed()
        box = raw['liveData']['boxscore']['teams']
        box['away']['players']['ID3'] = box['home']['players'].pop('ID3')
        mapping, _ = create_player_mapping(raw, TEAMS)
        data = anonymize_gameday_data(raw, TEAMS)
        sides = blind_judge.player_sides(data)
        for pid, side in blind_judge.player_sides(raw).items():
            self.assertEqual(sides[mapping[pid]['id']], side)
        remapped = blind_judge.remap_names(data, data['gameData'], seed=17)
        validate_player_names(remapped)
        self.assertEqual(blind_judge.player_sides(remapped), sides)
        self.assert_names_fit(remapped)

    def test_credit_and_substitution_only_players_get_distinct_names(self):
        raw = feed(runners=[runner(1, None, '1B', credits=[credit(6, '6'), credit(7, '4')])])
        events = raw['liveData']['plays']['allPlays'][0]['playEvents']
        events.insert(0, {'isPitch': False, 'index': -1, 'player': {'id': 8},
                          'replacedPlayer': {'id': 9}, 'position': POSITIONS['9'],
                          'details': {'eventType': 'defensive_substitution'}})
        events.insert(0, {'isPitch': False, 'index': -2, 'player': {'id': 10},
                          'replacedPlayer': {'id': 3}, 'position': {'code': '12'},
                          'details': {'eventType': 'offensive_substitution'}})
        before = copy.deepcopy(raw)
        template = anonymize_gameday_data(feed(), TEAMS)['gameData']
        for seed in range(12):
            for data in (anonymize_gameday_data(raw, TEAMS, seed),
                         blind_judge.remap_names(raw, template, seed)):
                with self.subTest(seed=seed):
                    validate_player_names(data)
                    self.assertEqual(len(data['gameData']['players']), 10)
                    self.assert_names_fit(data)
                    self.assertNotIn('Real Player', json.dumps(data))
        self.assertEqual(raw, before)

    def test_overflow_names_are_unique_across_both_full_rosters(self):
        raw = feed()
        box = raw['liveData']['boxscore']['teams']
        for pid in range(6, 76):
            raw['gameData']['players'][f'ID{pid}'] = person(pid, '6')
            side = 'home' if pid % 2 else 'away'
            box[side]['players'][f'ID{pid}'] = {'person': {'id': pid}}
        raw['liveData']['boxscore'] = {'teams': box}
        for seed in range(8):
            with self.subTest(seed=seed):
                data = anonymize_gameday_data(raw, TEAMS, seed)
                validate_player_names(data)
                self.assertEqual(len(data['gameData']['players']), 75)

    def test_name_checks_reject_collisions_and_stale_or_missing_references(self):
        data = anonymize_gameday_data(feed(), TEAMS)
        players = list(data['gameData']['players'].values())
        duplicate = copy.deepcopy(data)
        duplicate['gameData']['players'][f'ID{players[1]["id"]}']['fullName'] = players[0]['fullName']
        with self.assertRaisesRegex(ValueError, 'fictional name .* belongs to players'):
            validate_player_names(duplicate)
        surname = copy.deepcopy(data)
        surname['gameData']['players'][f'ID{players[1]["id"]}']['fullName'] = 'Other ' + players[0]['lastName']
        with self.assertRaisesRegex(ValueError, 'fictional name .* belongs to players'):
            validate_player_names(surname)
        stale = copy.deepcopy(data)
        stale['liveData']['plays']['allPlays'][0]['matchup']['batter']['fullName'] = players[1]['fullName']
        with self.assertRaisesRegex(ValueError, 'expected'):
            validate_player_names(stale)
        missing = copy.deepcopy(data)
        missing['liveData']['plays']['allPlays'][0]['runners'][0]['credits'] = [credit(123456, '6')]
        with self.assertRaisesRegex(ValueError, '123456.*missing from gameData.players'):
            validate_player_names(missing)

    def test_duplicate_mapping_fails_before_player_ids_can_be_collapsed(self):
        with patch('anonymize_real_gameday.assign_player_names', return_value={
                pid: 'Theo Vane' for pid in range(1, 6)}):
            with self.assertRaisesRegex(ValueError, 'fictional name .* belongs to players'):
                create_player_mapping(feed(), TEAMS)

    def test_duplicate_fictional_ids_fail_before_the_roster_is_written(self):
        teams = copy.deepcopy(TEAMS)
        by_name = {p['legal_name']: p for team in teams.values() for p in team['players']}
        hitter, pitcher = by_name['Omar Ramirez'], by_name['Joe Gibson']
        hitter['id'] = pitcher['id']
        raw = feed()
        raw['gameData']['players']['ID1'] = person(1, hitter['position']['code'], bat=hitter['batSide']['code'])
        raw['gameData']['players']['ID2'] = person(2, '1', throws=pitcher.get('pitchHand', {}).get('code', 'R'))
        with self.assertRaisesRegex(ValueError, 'fictional player IDs must be unique'):
            anonymize_gameday_data(raw, teams)

    def test_remapping_duplicate_source_names_still_uses_distinct_ids(self):
        raw = feed(runners=[runner(1, None, '1B', credits=[credit(3, '4')])])
        for pid in (1, 3):
            raw['gameData']['players'][f'ID{pid}']['fullName'] = 'Same Source Name'
        data = blind_judge.remap_names(raw, anonymize_gameday_data(feed(), TEAMS)['gameData'], seed=17)
        play = data['liveData']['plays']['allPlays'][0]
        batter = play['matchup']['batter']
        fielder = play['runners'][0]['credits'][0]['player']
        self.assertNotEqual(batter['fullName'], fielder['fullName'])
        self.assertEqual(batter['fullName'], data['gameData']['players']['ID1']['fullName'])
        self.assertEqual(fielder['fullName'], data['gameData']['players']['ID3']['fullName'])
        validate_player_names(data)

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

    def test_a_position_move_without_a_fielding_credit_rules_out_a_roster_name(self):
        roster = {p['legal_name'] for team in TEAMS.values() for p in team['players']}
        raw = feed()
        self.assertIn(assign_player_names(raw, TEAMS, random.Random(1))[5], roster)
        # The catcher also played first base, with no fielding credit there.
        raw['liveData']['boxscore']['teams']['home']['players']['ID5']['allPositions'] = [
            copy.deepcopy(POSITIONS['2']), copy.deepcopy(POSITIONS['3'])]
        self.assertNotIn(assign_player_names(raw, TEAMS, random.Random(1))[5], roster)

    def test_a_null_details_node_is_ignored(self):
        raw = feed()
        raw['liveData']['plays']['allPlays'][0]['playEvents'][0]['details'] = None
        self.assertIn(1, collect_players(raw))

    def test_a_lowercase_word_is_not_a_players_name(self):
        mapping = {'Alex Call': 'Ben Logan', 'Call': 'Logan'}
        self.assertEqual(anonymize_description('Challenged, call on the field was upheld: Alex Call walks.', mapping),
                         'Challenged, call on the field was upheld: Ben Logan walks.')

    def test_a_shared_first_or_last_name_is_not_mapped_alone(self):
        # Every player in the feed is named "Real"; each surname is his own.
        _, names = create_player_mapping(feed(), TEAMS, random.Random(1))
        self.assertNotIn('Real', names)
        self.assertIn('Player1', names)
        self.assertIn('Real Player1', names)

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
    def test_runner_advances_keep_transcript_names_over_stale_roster_names(self):
        from pbp_comparison import discover_pbp_examples, render_example
        example = next(e for e in discover_pbp_examples() if e.number == 3)
        text = render_example(example)
        self.assertIn('Greco moves up to third. Silver moves up to second.', text)
        self.assertIn('Greco comes home on the error. Silver comes home on the error', text)
        self.assertNotIn('Washington moves up to third.', text)
        self.assertNotIn('Barrett comes home on the error.', text)

    def test_simulated_pickoff_caught_stealing_keeps_the_throw_over(self):
        # The simulator identifies this in eventType; the real-feed adapter
        # also puts a pickoff flag on the movement. Both must keep the cause.
        from baseball import BaseballSimulator
        game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
        runner = game.team2_lineup[0]
        game.bases[0] = runner['legal_name']
        events = []
        with patch.object(game.strategy_rng, 'random', side_effect=[0.0, 0.0]):
            game._record_pickoff_throw(events, 1, 0, game._pitching_side()[2])
        renderer = NarrativeRenderer(game.gameday_data, seed=0)
        renderer.runners_on_base = {'1B': runner['legal_name'], '2B': None, '3B': None}
        text = renderer._render_steal_event(events[0])
        self.assertIn('The throw to first catches', text)
        self.assertIn(f"{runner['legal_name']} is caught stealing second.", text)
        self.assertNotIn('gets back safely', text)
        self.assertIsNone(renderer.runners_on_base['1B'])

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


class TestRealFeedRunnerAccounting(unittest.TestCase):
    def test_two_separate_pickoff_throws_distinguish_the_later_out(self):
        for result_kind in ('pickoff_1b', 'pickoff_caught_stealing_2b'):
            for split_result in (False, True):
                events = [{'index': i, 'isPitch': False, 'type': 'pickoff',
                           'details': {'description': 'Pickoff Attempt 1B', 'code': '1'}} for i in (0, 1)]
                if split_result:
                    events.append({'index': 2, 'isPitch': False,
                                   'details': {'eventType': result_kind, 'description': ''}})
                raw = feed('Pickoff 1B' if result_kind == 'pickoff_1b' else 'Pickoff Caught Stealing 2B',
                           events=events, outs=3, runners=[
                               runner(3, '1B', '1B' if result_kind == 'pickoff_1b' else '2B',
                                      index=2 if split_result else 1, kind=result_kind, out=True)])
                data = anonymize_gameday_data(raw, TEAMS)
                self.assertEqual(len(data['liveData']['plays']['allPlays'][0]['playEvents']), 2)
                for seed in range(12):
                    with self.subTest(kind=result_kind, split=split_result, seed=seed):
                        text = NarrativeRenderer(data, seed=seed).render()
                        self.assertEqual(text.count('gets back safely'), 1)
                        self.assertIn('Another ', text)
                        self.assertEqual(text.count('picked off' if result_kind == 'pickoff_1b' else 'caught stealing'), 1)
                        self.assertNotIn('gets back safely. The throw', text)

    def test_a_pitch_between_pickoff_throws_keeps_them_separate(self):
        events = [{'index': 0, 'isPitch': False, 'type': 'pickoff',
                   'details': {'description': 'Pickoff Attempt 1B', 'code': '1'}}, pitch(1, 'B'),
                  {'index': 2, 'isPitch': False, 'details': {'eventType': 'pickoff_caught_stealing_2b'}}]
        raw = feed('Pickoff Caught Stealing 2B', events=events, outs=3,
                   runners=[runner(3, '1B', '2B', index=2, kind='pickoff_caught_stealing_2b', out=True)])
        text = NarrativeRenderer(anonymize_gameday_data(raw, TEAMS), seed=1).render()
        self.assertIn('gets back safely', text)
        self.assertIn('The throw to first catches', text)
        self.assertNotIn('Another throw', text)

    def test_a_force_with_one_fielder_does_not_invent_a_throw_to_himself(self):
        for start, end, position in (('1B', '2B', '5'), ('2B', '3B', '5'), ('3B', 'home', '2')):
            raw = feed('Forceout', outs=3, runners=[
                runner(3, start, end, out=True, credits=[credit(4, position)]), runner(1, None, '1B')])
            raw['liveData']['plays']['allPlays'][0]['playEvents'][0]['hitData']['trajectory'] = 'ground_ball'
            data = anonymize_gameday_data(raw, TEAMS)
            name = data['liveData']['plays']['allPlays'][0]['runners'][0]['credits'][0]['player']['fullName'].split()[-1]
            for seed in range(24):
                with self.subTest(base=end, seed=seed):
                    text = NarrativeRenderer(data, seed=seed).render()
                    self.assertIn(name, text)
                    self.assertRegex(text, 'force[^.]*' + {'2B': 'second', '3B': 'third', 'home': 'the plate'}[end])
                    self.assertNotRegex(text, rf'{name} (?:goes|throws|tosses) to {name}')

    def test_a_known_unassisted_force_keeps_the_step_on_the_bag(self):
        raw = feed('Forceout', outs=3, runners=[runner(3, '1B', '2B', out=True,
                   credits=[credit(4, '4')]), runner(1, None, '1B')])
        raw['liveData']['plays']['allPlays'][0]['playEvents'][0]['hitData']['trajectory'] = 'ground_ball'
        data = anonymize_gameday_data(raw, TEAMS)
        for seed in range(12):
            with self.subTest(seed=seed):
                text = NarrativeRenderer(data, seed=seed).render()
                self.assertIn('steps on second to retire the runner', text)
                self.assertNotIn('to the covering infielder', text)

    def test_a_force_with_two_fielders_keeps_the_named_throw(self):
        raw = feed('Forceout', outs=3, runners=[runner(3, '1B', '2B', out=True,
                   credits=[credit(4, '5', 'f_assist'), credit(5, '4')]), runner(1, None, '1B')])
        raw['liveData']['plays']['allPlays'][0]['playEvents'][0]['hitData']['trajectory'] = 'ground_ball'
        data = anonymize_gameday_data(raw, TEAMS)
        credits = data['liveData']['plays']['allPlays'][0]['runners'][0]['credits']
        fielder, receiver = [c['player']['fullName'].split()[-1] for c in credits]
        for seed in range(24):
            with self.subTest(seed=seed):
                text = NarrativeRenderer(data, seed=seed).render()
                self.assertRegex(text, rf'{fielder} (?:goes|throws|[^.]*tosses) to {receiver}')

    def test_full_inning_summary_keeps_a_leadoff_single_or_walk_stranded(self):
        for leadoff, hits in (('Single', 1), ('Walk', 0)):
            raw = feed(leadoff, runners=[runner(3, None, '1B')])
            plays = raw['liveData']['plays']['allPlays']
            plays[0]['matchup']['batter'] = {'id': 3, 'fullName': 'Real Player3'}
            plays[0]['matchup']['postOnFirst'] = {'id': 3, 'fullName': 'Real Player3'}
            for outs in (1, 2, 3):
                play = feed('Groundout', outs=outs, runners=[runner(1, None, '1B', out=True)])['liveData']['plays']['allPlays'][0]
                play['about']['atBatIndex'] = outs
                play['runners'][0]['movement']['outNumber'] = outs
                if outs < 3:
                    play['matchup']['postOnFirst'] = {'id': 3, 'fullName': 'Real Player3'}
                plays.append(play)
            bottom = copy.deepcopy(plays[-1])
            bottom['about'].update(atBatIndex=4, isTopInning=False, halfInning='bottom')
            plays.append(bottom)
            summaries = []

            class CaptureSummary(NarrativeRenderer):
                def _get_half_inning_stats(self):
                    stats = super()._get_half_inning_stats()
                    summaries.append(stats)
                    return stats

            CaptureSummary(anonymize_gameday_data(raw, TEAMS), seed=1).render()
            self.assertEqual(summaries, [(hits, 1)])

    def test_third_out_retains_a_runner_who_did_not_move(self):
        for outcome in ('Groundout', 'Strikeout', 'Flyout'):
            with self.subTest(outcome=outcome):
                raw = feed(outcome, outs=3, runners=[runner(1, None, '1B', out=True)])
                renderer = NarrativeRenderer(raw, seed=1)
                bases = renderer._post_play_bases(raw['liveData']['plays']['allPlays'][0],
                                                  {'1B': 'Real Player3', '2B': None, '3B': None})
                renderer.runners_on_base = bases
                renderer.plays_in_half_inning = [feed()['liveData']['plays']['allPlays'][0],
                                                 raw['liveData']['plays']['allPlays'][0]]
                self.assertEqual(renderer._get_half_inning_stats(), (1, 1))

    def test_third_out_force_at_third_keeps_two_stranded_runners(self):
        raw = feed('Forceout', outs=3, runners=[runner(4, '2B', '3B', out=True), runner(1, None, '1B')])
        renderer = NarrativeRenderer(raw, seed=1)
        bases = renderer._post_play_bases(raw['liveData']['plays']['allPlays'][0],
                                          {'1B': 'Real Player3', '2B': 'Real Player4', '3B': None})
        self.assertEqual(bases, {'1B': 'Real Player1', '2B': 'Real Player3', '3B': None})

    def test_third_out_removes_a_runner_who_scores_or_is_retired(self):
        raw = feed(outs=3, runners=[runner(3, '2B', 'score'), runner(4, '1B', '3B', out=True),
                                   runner(1, None, '1B')])
        renderer = NarrativeRenderer(raw, seed=1)
        bases = renderer._post_play_bases(raw['liveData']['plays']['allPlays'][0],
                                          {'1B': 'Real Player4', '2B': 'Real Player3', '3B': None})
        self.assertEqual(bases, {'1B': 'Real Player1', '2B': None, '3B': None})

    def test_hit_with_a_runner_out_is_not_an_in_order_inning(self):
        raw = feed(outs=1, runners=[runner(1, None, '2B', out=True)])
        first = raw['liveData']['plays']['allPlays'][0]
        first['runners'][0]['details']['movementReason'] = 'r_out_stretching'
        for outs in (2, 3):
            play = copy.deepcopy(feed('Groundout', outs=outs, runners=[runner(3, None, '1B', out=True)])['liveData']['plays']['allPlays'][0])
            play['about']['atBatIndex'] = outs - 1
            raw['liveData']['plays']['allPlays'].append(play)
        bottom = copy.deepcopy(raw['liveData']['plays']['allPlays'][-1])
        bottom['about'].update(atBatIndex=3, isTopInning=False, halfInning='bottom')
        bottom['count']['outs'] = 1
        raw['liveData']['plays']['allPlays'].append(bottom)
        for seed in range(12):
            text = NarrativeRenderer(anonymize_gameday_data(raw, TEAMS), seed=seed).render()
            self.assertNotRegex(text, r'(?i)three up, three down|retired in order|go down in order|1-2-3 inning')

    def test_every_out_on_a_hit_is_called_even_without_a_throw_reason(self):
        for reason in ('r_rundown', 'r_hbr', 'r_runner_out', None):
            raw = feed(outs=3, runners=[runner(1, None, '1B'), runner(3, '2B', '3B', out=True)])
            raw['liveData']['plays']['allPlays'][0]['runners'][1]['details']['movementReason'] = reason
            data = anonymize_gameday_data(raw, TEAMS)
            name = data['liveData']['plays']['allPlays'][0]['runners'][1]['details']['runner']['fullName'].split()[-1]
            for seed in range(12):
                text = NarrativeRenderer(data, seed=seed).render()
                self.assertRegex(text, rf'{name}[^\n]*(?:out|thrown)')
                if reason != 'r_hbr':
                    self.assertIn('third', text)

    def test_a_prior_runner_action_is_not_replayed_as_an_out_on_the_hit(self):
        action = {'index': 0, 'isPitch': False, 'details': {'eventType': 'caught_stealing_2b'}}
        raw = feed(events=[action, pitch(1)], outs=1, runners=[
            runner(3, '1B', '2B', index=0, kind='caught_stealing_2b', out=True), runner(1, None, '1B', index=1)])
        text = NarrativeRenderer(anonymize_gameday_data(raw, TEAMS), seed=1).render()
        self.assertEqual(text.count('caught stealing second'), 1)
        self.assertNotIn('thrown out', text)

    def test_a_runner_hit_by_the_ball_is_out_without_a_throw(self):
        raw = feed(outs=3, runners=[runner(1, None, '1B'), runner(3, '1B', '2B', out=True)])
        raw['liveData']['plays']['allPlays'][0]['runners'][1]['details']['movementReason'] = 'r_hbr'
        text = NarrativeRenderer(anonymize_gameday_data(raw, TEAMS), seed=1).render()
        self.assertIn('The batted ball hits', text)
        self.assertIn('he is out to end the inning', text)
        self.assertNotIn('throw from', text)

    def test_caught_ball_advances_explain_the_tag_up(self):
        for outcome in ('Lineout', 'Flyout', 'Pop Out'):
            for start, end in (('1B', '2B'), ('2B', '3B')):
                raw = feed(outcome, outs=1, runners=[runner(1, None, '1B', out=True), runner(3, start, end)])
                raw['liveData']['plays']['allPlays'][0]['runners'][0]['movement']['outNumber'] = 1
                data = anonymize_gameday_data(raw, TEAMS)
                for seed in range(12):
                    renderer = NarrativeRenderer(data, seed=seed)
                    renderer._optional = lambda name: False
                    text = renderer.render()
                    self.assertIn('tags up and advances to ' + {'2B': 'second', '3B': 'third'}[end], text)

    def test_sacrifice_fly_names_the_runner_without_repeating_his_score(self):
        raw = feed('Sac Fly', outs=1, runners=[runner(1, None, '1B', out=True), runner(3, '3B', 'score')])
        raw['liveData']['plays']['allPlays'][0]['result'].update(awayScore=1, rbi=1)
        data = anonymize_gameday_data(raw, TEAMS)
        name = data['liveData']['plays']['allPlays'][0]['runners'][1]['details']['runner']['fullName'].split()[-1]
        for seed in range(12):
            text = NarrativeRenderer(data, seed=seed).render()
            self.assertNotIn('The runner', text)
            self.assertEqual(text.count(name), 1, text)

    def test_a_third_out_catch_does_not_start_a_tag_up(self):
        from renderers.narrative.play_description import is_tag_up
        raw = feed('Flyout', outs=3, runners=[runner(1, None, '1B', out=True), runner(3, '2B', '3B')])
        play = raw['liveData']['plays']['allPlays'][0]
        self.assertFalse(is_tag_up(play, play['runners'][1]))

    def test_an_extra_advance_is_called_when_the_optional_sentence_is_dropped(self):
        raw = feed(outs=1, runners=[runner(1, None, '1B'), runner(3, '2B', 'score')])
        renderer = NarrativeRenderer(anonymize_gameday_data(raw, TEAMS), seed=1)
        renderer._optional = lambda name: False
        self.assertIn('comes home', renderer.render())

    def test_multistage_hit_advances_use_the_runners_original_base(self):
        for start, middle, end, expected in (('1B', '2B', '3B', 'moves up to third'),
                                              ('2B', '3B', 'score', 'comes home')):
            raw = feed(outs=1, runners=[runner(1, None, '1B'), runner(3, start, middle), runner(3, middle, end)])
            renderer = NarrativeRenderer(anonymize_gameday_data(raw, TEAMS), seed=1)
            renderer._optional = lambda name: False
            self.assertIn(expected, renderer.render())

    def test_pickoff_throw_and_its_caught_stealing_result_are_one_action(self):
        attempt = {'index': 0, 'isPitch': False, 'type': 'pickoff',
                   'details': {'description': 'Pickoff Attempt 1B', 'code': '1'}}
        result = {'index': 1, 'isPitch': False,
                  'details': {'eventType': 'pickoff_caught_stealing_2b', 'description': 'raw log'}}
        raw = feed('Pickoff Caught Stealing 2B', events=[attempt, result], outs=3,
                   runners=[runner(3, '1B', '2B', index=1, kind='pickoff_caught_stealing_2b', out=True)])
        data = anonymize_gameday_data(raw, TEAMS)
        self.assertEqual(len(data['liveData']['plays']['allPlays'][0]['playEvents']), 1)
        text = NarrativeRenderer(data, seed=1).render()
        self.assertNotIn('gets back safely', text)
        self.assertIn('throw to first', text)
        self.assertEqual(text.count('caught stealing second'), 1)
        self.assertNotIn('Another ', text)

    def test_a_pickoff_caught_stealing_is_not_a_steal_on_the_previous_pitch(self):
        raw = feed('Pickoff Caught Stealing 2B', events=[pitch(0, 'B'),
                   {'index': 1, 'isPitch': False, 'details': {'eventType': 'pickoff_caught_stealing_2b'}}],
                   outs=3, runners=[runner(3, '1B', '2B', index=1, kind='pickoff_caught_stealing_2b', out=True)])
        data = anonymize_gameday_data(raw, TEAMS)
        action = data['liveData']['plays']['allPlays'][0]['playEvents'][1]
        self.assertEqual(action['details']['eventType'], 'pickoff_caught_stealing')
        text = NarrativeRenderer(data, seed=1).render()
        self.assertIn('throw to first', text)
        self.assertEqual(text.count('caught stealing second'), 1)
        self.assertNotRegex(text, r'and (?:the runner (?:goes|breaks|takes off)|there he goes)')

    def test_a_runner_escaping_a_pickoff_on_an_error_is_safe_at_second(self):
        attempt = {'index': 0, 'isPitch': False, 'type': 'pickoff',
                   'details': {'description': 'Pickoff Attempt 1B', 'code': '1'}}
        action = {'index': 1, 'isPitch': False, 'details': {'eventType': 'pickoff_caught_stealing_2b'}}
        raw = feed('Incomplete', events=[attempt, action], runners=[
            runner(3, '1B', '2B', index=1, kind='pickoff_caught_stealing_2b',
                   credits=[credit(2, '1', 'f_throwing_error')])])
        text = NarrativeRenderer(anonymize_gameday_data(raw, TEAMS), seed=1).render()
        self.assertIn('pickoff throw gets away', text)
        self.assertIn('takes second', text)
        self.assertNotIn('gets back safely', text)
        self.assertNotIn('caught stealing', text)

    def test_a_catcher_finishing_strike_three_is_not_a_safe_pickoff(self):
        strike = pitch(0, 'S')
        strike['count']['strikes'] = 3
        throw = {'index': 1, 'isPitch': False, 'type': 'pickoff',
                 'details': {'description': 'Pickoff Attempt 1B', 'code': '1', 'isOut': True, 'fromCatcher': True}}
        raw = feed('Strikeout', events=[strike, throw], outs=3,
                   runners=[runner(1, None, '1B', index=1, kind='strikeout', out=True)])
        data = anonymize_gameday_data(raw, TEAMS)
        self.assertEqual(len(data['liveData']['plays']['allPlays'][0]['playEvents']), 1)
        text = NarrativeRenderer(data, seed=1).render()
        self.assertNotIn('gets back safely', text)
        self.assertNotIn('pickoff', text)
        self.assertRegex(text, r'strikes out|strike three|struck out|down on strikes|strikeout|gets him swinging')

    def test_a_pickoff_out_never_says_the_runner_returns_safely(self):
        renderer = NarrativeRenderer(feed(), seed=1)
        renderer.runners_on_base = {'1B': 'Real Player3', '2B': None, '3B': None}
        event = {'isPitch': False, 'details': {'eventType': 'pickoff_attempt', 'runners': [
            {'runner': {'id': 3, 'fullName': 'Real Player3'}, 'fromBase': '1B', 'toBase': '1B', 'isOut': True}]}}
        text = renderer._render_steal_event(event)
        self.assertIn('picked off at first', text)
        self.assertNotIn('safely', text)


if __name__ == '__main__':
    unittest.main()
