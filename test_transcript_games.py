"""Full broadcast reconstruction, factual compilation, and integer-draw replay."""

import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import fit_transcript_games as fitting
from renderers import NarrativeRenderer, StatcastRenderer
from renderers.randomness import STREAM_NAMES
import transcript_game_fixtures as fixtures


# Independently reviewed totals: appearances, delivered pitches, nonpitch actions.
REVIEWED_EVENT_COUNTS = {
    1: (73, 254, 10), 5: (73, 270, 2), 11: (50, 198, 2),
    13: (70, 295, 1), 20: (67, 223, 2), 29: (68, 217, 0),
    35: (63, 207, 1), 37: (64, 220, 1), 39: (68, 224, 1),
    41: (62, 199, 1), 45: (72, 237, 3), 46: (76, 254, 0),
    49: (63, 214, 1), 50: (66, 170, 0), 51: (47, 152, 1),
    52: (62, 200, 2), 53: (62, 193, 1),
}
EPISODES = set(REVIEWED_EVENT_COUNTS)


def ledger_with(plays, complete=False):
    """Small, independent input: no dependency on generated corpus snapshots."""
    positions = ('CF', '2B', 'LF', '3B', 'RF', '1B', 'C', 'SS', 'P')
    return {
        'episode': 999, 'source_file': 'synthetic.txt', 'complete': complete,
        'game': {
            'away': 'Sample Visitors', 'home': 'Example Hosts', 'venue': 'Example Field',
            'away_pitcher': 'Away Pitcher', 'home_pitcher': 'Home Pitcher',
            'away_lineup': [{'name': f'Away Batter {i}', 'position': pos}
                            for i, pos in enumerate(positions, 1)],
            'home_lineup': [{'name': f'Home Batter {i}', 'position': pos}
                            for i, pos in enumerate(positions, 1)],
        },
        'plays': plays,
    }


def record(batter='Away Batter 1', outcome='Incomplete', start=1, end=1,
           outs=0, pitches=None, **extra):
    result = {
        'inning': 1, 'top': True, 'batter': batter, 'pitcher': 'Home Pitcher',
        'outcome': outcome, 'source_start': start, 'source_end': end,
        'outs': outs, 'score': [0, 0], 'pitches': pitches or [],
    }
    result.update(extra)
    return result


def movement(name, start, end, out=False):
    return {'name': name, 'start': start, 'end': end, 'out': out}


def replay_with_other_times(data):
    shifted = copy.deepcopy(data)
    shifted['gameData']['datetime'] = {'dateTime': '2049-07-13T01:02:03Z'}
    for index, play in enumerate(shifted['liveData']['plays']['allPlays']):
        play['about'].update(startTime=f'2049-07-13T01:{index % 60:02}:00Z',
                             endTime=f'2049-07-13T02:{index % 60:02}:59Z')
        for event in play['playEvents']:
            event.update(startTime='1997-11-08T09:10:11Z', endTime='2091-01-02T03:04:05Z')
    return NarrativeRenderer(shifted).render()


class TestFullTranscriptCompiler(unittest.TestCase):
    def test_unspecified_strike_is_an_observed_pitch_and_action_is_not(self):
        pitches = [
            {'code': 'U', 'line': 1, 'isStrike': True, 'description': 'Strike, unspecified'},
            {'code': 'A', 'line': 1, 'eventType': 'caught_stealing',
             'description': 'The runner is tagged out at second.'},
            {'code': 'B', 'line': 2}, {'code': 'C', 'line': 3}, {'code': 'S', 'line': 4},
        ]
        play = record(outcome='Strikeout', end=4, outs=2, pitches=pitches,
                      runners=[movement('Earlier Runner', '1B', '2B', True),
                               movement('Away Batter 1', None, None, True)])
        data = fixtures.compile_game(ledger_with([play]), b'Unknown strike and tag.\nBall.\nStrike.\nStrike three.\n')
        compiled = data['liveData']['plays']['allPlays'][0]
        self.assertEqual([event['isPitch'] for event in compiled['playEvents']], [True, False, True, True, True])
        self.assertEqual([(e['count']['balls'], e['count']['strikes']) for e in compiled['playEvents']],
                         [(0, 0), (0, 1), (0, 1), (1, 1), (1, 2)])
        self.assertEqual(compiled['count'], {'balls': 1, 'strikes': 3, 'outs': 2})
        self.assertTrue(compiled['playEvents'][0]['details']['isStrike'])
        self.assertEqual(compiled['playEvents'][0]['details']['description'], 'Strike, unspecified')
        self.assertEqual([r['movement']['outNumber'] for r in compiled['runners']], [1, 2])
        self.assertEqual(compiled['runners'][0]['movement']['outBase'], '2B')

    def test_unseen_pitches_are_not_added_to_an_inherited_count(self):
        first = record(end=1, pitches=[{'code': 'B', 'line': 1}], interrupted_pa=True)
        second = record(batter='Replacement Batter', outcome='Strikeout', start=2, end=4,
                        outs=1, initial_count=[3, 0], continuing_pa=True,
                        pitches=[{'code': 'C', 'line': 2}, {'code': 'F', 'line': 3}, {'code': 'C', 'line': 4}])
        data = fixtures.compile_game(ledger_with([first, second]), b'Ball.\nStrike.\nFoul.\nStrike three.\n')
        plays = data['liveData']['plays']['allPlays']
        self.assertEqual([len(p['playEvents']) for p in plays], [1, 3])
        self.assertFalse(plays[0]['about']['isComplete'])
        self.assertEqual(plays[0]['runners'], [])
        self.assertEqual(plays[1]['playEvents'][0]['count']['balls'], 3)
        self.assertEqual(plays[1]['count']['strikes'], 3)
        self.assertFalse(data['gameData']['broadcast']['complete'])

    def test_walks_advance_only_forced_runners_and_score_loaded_runner(self):
        records = [record(batter=f'Away Batter {i}', outcome='Intentional Walk', start=i, end=i,
                          score=[int(i == 4), 0]) for i in range(1, 5)]
        data = fixtures.compile_game(ledger_with(records), b'Walk.\nWalk.\nWalk.\nWalk.\n')
        plays = data['liveData']['plays']['allPlays']
        second = {r['details']['runner']['fullName']: r['movement']['end'] for r in plays[1]['runners']}
        self.assertEqual(second, {'Away Batter 1': '2B', 'Away Batter 2': '1B'})
        loaded = {r['details']['runner']['fullName']: r['movement']['end'] for r in plays[3]['runners']}
        self.assertEqual(loaded, {'Away Batter 1': 'score', 'Away Batter 2': '3B',
                                  'Away Batter 3': '2B', 'Away Batter 4': '1B'})
        self.assertEqual(plays[3]['result']['rbi'], 1)
        self.assertTrue(all(not p['playEvents'] for p in plays))
        self.assertEqual(data['liveData']['linescore']['teams']['away']['hits'], 0)

        # A runner on second alone is not forced by a walk.
        double = record(outcome='Double', runners=[movement('Away Batter 1', None, '2B')])
        walk = record(batter='Away Batter 2', outcome='Walk', start=2, end=2)
        plays = fixtures.compile_game(ledger_with([double, walk]), b'Double.\nWalk.\n')['liveData']['plays']['allPlays']
        self.assertEqual(len(plays[1]['runners']), 1)
        self.assertEqual(plays[1]['matchup']['postOnSecond']['fullName'], 'Away Batter 1')

    def test_scoring_on_wild_pitch_during_walk_does_not_become_batter_rbi(self):
        triple = record(outcome='Triple', runners=[movement('Away Batter 1', None, '3B')])
        walk = record(batter='Away Batter 2', outcome='Walk', start=2, end=5, score=[1, 0],
                      pitches=[{'code': 'B', 'line': 2},
                               {'code': 'A', 'line': 2, 'eventType': 'wild_pitch',
                                'description': 'Wild pitch; Away Batter 1 scores from third.'},
                               {'code': 'B', 'line': 3}, {'code': 'B', 'line': 4}, {'code': 'B', 'line': 5}],
                      runners=[movement('Away Batter 1', '3B', 'score')])
        data = fixtures.compile_game(ledger_with([triple, walk]), b'Triple.\nWild pitch scores runner.\nBall.\nBall.\nWalk.\n')
        compiled = data['liveData']['plays']['allPlays'][1]
        self.assertEqual(compiled['result']['awayScore'], 1)
        self.assertEqual(compiled['result']['rbi'], 0)
        self.assertNotIn('drives in', StatcastRenderer(data).render())

    def test_error_run_and_explicit_rbi_credit_are_distinct(self):
        for outcome, override, expected in [('Field Error', None, 0), ('Single', 0, 0),
                                             ('Groundout', 1, 1)]:
            with self.subTest(outcome=outcome, override=override):
                first = record(outcome='Triple', runners=[movement('Away Batter 1', None, '3B')])
                second = record(batter='Away Batter 2', outcome=outcome, start=2, end=2,
                                outs=int(outcome == 'Groundout'), score=[1, 0],
                                runners=[movement('Away Batter 1', '3B', 'score')])
                if override is not None:
                    second['rbi'] = override
                data = fixtures.compile_game(ledger_with([first, second]), b'Triple.\nRunner scores.\n')
                self.assertEqual(data['liveData']['plays']['allPlays'][1]['result']['rbi'], expected)

    def test_skipped_inning_score_update_is_not_an_rbi_for_the_next_batter(self):
        first = record(outcome='Groundout', outs=1)
        resumed = record(batter='Home Batter 1', outcome='Groundout', start=2, end=2,
                         inning=2, top=False, outs=1, score=[1, 0])
        data = fixtures.compile_game(ledger_with([first, resumed]), b'First inning out.\nCoverage resumes with visitors leading.\n')
        play = data['liveData']['plays']['allPlays'][1]
        self.assertTrue(play['about']['coverageGapBefore'])
        self.assertEqual(play['result']['awayScore'], 1)
        self.assertEqual(play['result']['rbi'], 0)
        self.assertFalse(play['about']['isScoringPlay'])

    def test_multistage_runner_movement_does_not_leave_a_scoring_runner_on_base(self):
        first = record(outcome='Single')
        second = record(batter='Away Batter 2', outcome='Single', start=2, end=2,
                        score=[1, 0], runners=[movement('Away Batter 1', '1B', '2B'),
                                              movement('Away Batter 1', '2B', 'score')])
        data = fixtures.compile_game(ledger_with([first, second]), b'Single.\nRunner steals then scores on single.\n')
        play = data['liveData']['plays']['allPlays'][1]
        self.assertNotIn('postOnSecond', play['matchup'])
        self.assertEqual(play['matchup']['postOnFirst']['fullName'], 'Away Batter 2')
        self.assertEqual(sum(r['details']['isScoringEvent'] for r in play['runners']), 1)

    def test_structured_steal_then_home_run_keeps_intermediate_and_final_bases(self):
        first = record(outcome='Single')
        second = record(batter='Away Batter 2', outcome='Home Run', start=2, end=3, score=[2, 0],
                        pitches=[{'code': 'B', 'line': 2},
                                 {'code': 'A', 'line': 2, 'eventType': 'stolen_base',
                                  'description': 'UNIQUE SOURCE PROSE MUST NEVER BE REPLAYED',
                                  'runners': [movement('Away Batter 1', '1B', '2B')]},
                                 {'code': 'X', 'line': 3}])
        data = fixtures.compile_game(ledger_with([first, second]), b'Single.\nSteal.\nHome run.\n')
        play = data['liveData']['plays']['allPlays'][1]
        runner_moves = [r['movement'] for r in play['runners']
                        if r['details']['runner']['fullName'] == 'Away Batter 1']
        self.assertEqual([(m['start'], m['end']) for m in runner_moves], [('1B', '2B'), ('2B', 'score')])
        self.assertFalse(any(key.startswith('postOn') for key in play['matchup']))
        self.assertEqual(sum(r['details']['isScoringEvent'] for r in play['runners']), 2)
        action = play['playEvents'][1]['details']
        self.assertEqual(action['runner']['fullName'], 'Away Batter 1')
        self.assertEqual(action['toBase'], '2B')
        self.assertNotIn('UNIQUE SOURCE PROSE', json.dumps(data))
        for Renderer in (NarrativeRenderer, StatcastRenderer):
            self.assertNotIn('UNIQUE SOURCE PROSE', Renderer(data).render())

    def test_duplicate_action_and_terminal_score_is_recorded_once(self):
        first = record(outcome='Triple')
        second = record(batter='Away Batter 2', start=2, end=2, score=[1, 0],
                        pitches=[{'code': 'B', 'line': 2},
                                 {'code': 'A', 'line': 2, 'eventType': 'wild_pitch',
                                  'runners': [{'name': 'Away Batter 1', 'start': '3B', 'end': 'score'}]}],
                        runners=[movement('Away Batter 1', '3B', 'score')])
        data = fixtures.compile_game(ledger_with([first, second]), b'Triple.\nWild pitch scores runner.\n')
        play = data['liveData']['plays']['allPlays'][1]
        self.assertEqual(len(play['runners']), 1)
        self.assertEqual(sum(r['details']['isScoringEvent'] for r in play['runners']), 1)
        self.assertEqual(play['result']['rbi'], 0)
        self.assertFalse(any(key.startswith('postOn') for key in play['matchup']))

    def test_strikeout_and_action_out_follow_actual_event_order(self):
        for caught_after_strikeout in (False, True):
            with self.subTest(caught_after_strikeout=caught_after_strikeout):
                first = record(outcome='Single')
                pitches = [{'code': 'C', 'line': 2}, {'code': 'C', 'line': 3}, {'code': 'S', 'line': 4}]
                action = {'code': 'A', 'line': 4 if caught_after_strikeout else 2,
                          'eventType': 'caught_stealing',
                          'runners': [movement('Away Batter 1', '1B', '2B', True)]}
                pitches.insert(3 if caught_after_strikeout else 1, action)
                second = record(batter='Away Batter 2', outcome='Strikeout', start=2, end=4,
                                outs=2, pitches=pitches)
                data = fixtures.compile_game(ledger_with([first, second]), b'Single.\nStrike.\nStrike.\nStrike three.\n')
                play = data['liveData']['plays']['allPlays'][1]
                out_numbers = {r['details']['runner']['fullName']: r['movement']['outNumber']
                               for r in play['runners'] if r['movement']['isOut']}
                expected = {'Away Batter 1': 2, 'Away Batter 2': 1} if caught_after_strikeout else {
                    'Away Batter 1': 1, 'Away Batter 2': 2}
                self.assertEqual(out_numbers, expected)
                self.assertFalse(any(key.startswith('postOn') for key in play['matchup']))

    def test_double_play_credits_and_runner_outs_keep_their_order(self):
        first = record(outcome='Single')
        second = record(batter='Away Batter 2', outcome='Double Play', start=2, end=2, outs=2,
                        pitches=[{'code': 'X', 'line': 2}],
                        hit={'location': 'SS', 'trajectory': 'ground_ball'},
                        fielders=[{'name': 'Short Stop', 'position': 'SS'},
                                  {'name': 'Second Base', 'position': '2B'},
                                  {'name': 'First Base', 'position': '1B'}],
                        runners=[movement('Away Batter 1', '1B', '2B', True),
                                 movement('Away Batter 2', None, '1B', True)])
        data = fixtures.compile_game(ledger_with([first, second]), b'Single.\nSix four three double play.\n')
        play = data['liveData']['plays']['allPlays'][1]
        self.assertEqual([r['movement']['outNumber'] for r in play['runners']], [1, 2])
        self.assertEqual([r['movement']['outBase'] for r in play['runners']], ['2B', '1B'])
        credits = play['runners'][1]['credits']
        self.assertEqual([(c['position']['abbreviation'], c['credit']) for c in credits],
                         [('SS', 'assist'), ('2B', 'assist'), ('1B', 'putout')])
        self.assertNotIn('postOnFirst', play['matchup'])

    def test_safe_arrival_without_scoring_credit_is_neither_hit_nor_error(self):
        play = record(outcome='Reached Base', pitches=[{'code': 'X', 'line': 1}],
                      runners=[movement('Away Batter 1', None, '1B')],
                      hit={'location': 'P', 'trajectory': 'ground_ball'})
        data = fixtures.compile_game(ledger_with([play]), b'Close play at first, called safe.\n')
        compiled = data['liveData']['plays']['allPlays'][0]
        self.assertEqual(compiled['result']['eventType'], 'reached_base')
        self.assertFalse(compiled['runners'][0]['movement']['isOut'])
        self.assertEqual(data['liveData']['linescore']['teams']['away']['hits'], 0)
        self.assertEqual(data['liveData']['linescore']['teams']['home']['errors'], 0)

    def test_fielding_a_safe_hit_does_not_create_a_putout_credit(self):
        play = record(outcome='Single', pitches=[{'code': 'X', 'line': 1}],
                      hit={'location': 'P', 'trajectory': 'ground_ball'},
                      fielders=[{'name': 'Home Pitcher', 'position': 'P'}])
        data = fixtures.compile_game(ledger_with([play]), b'The pitcher cannot get the runner at first.\n')
        compiled = data['liveData']['plays']['allPlays'][0]
        self.assertEqual(compiled['count']['outs'], 0)
        self.assertFalse(compiled['runners'][0]['movement']['isOut'])
        self.assertEqual([c['credit'] for c in compiled['runners'][0]['credits']], ['fielding'])

    def test_compilation_rejects_bad_provenance_or_impossible_out_progression(self):
        source = b'First.\nSecond.\n'
        for changes in ({'source_start': 0}, {'source_end': 3}, {'pitches': [{'code': 'B', 'line': 2}]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                fixtures.compile_game(ledger_with([record(**changes)]), source)
        with self.assertRaisesRegex(ValueError, 'out progression'):
            fixtures.compile_game(ledger_with([record(outs=2), record(start=2, end=2, outs=1)]), source)


class TestFullTranscriptRendering(unittest.TestCase):
    def test_unspecified_strike_uses_neutral_wording_and_increments_the_count(self):
        play = record(pitches=[{'code': 'U', 'line': 1, 'isStrike': True,
                                'description': 'Strike, unspecified'}])
        data = fixtures.compile_game(ledger_with([play]), b'The count is oh and one.\n')
        renderer = NarrativeRenderer(data)
        text = renderer.render()
        lo, hi = renderer._play_line_map[0]
        body = '\n'.join(text.splitlines()[lo:hi]).lower()
        self.assertIn('strike', body)
        self.assertIn('oh and one', body)
        self.assertNotIn('called', body)
        self.assertNotIn('swing', body)
        statcast = StatcastRenderer(data).render()
        self.assertIn('Strike:', statcast)
        self.assertNotIn('Called Strike:', statcast)
        self.assertNotIn('Swinging Strike:', statcast)

    def test_semantic_pitch_location_overrides_zone_and_batter_handedness(self):
        for side in ('L', 'R', 'U'):
            with self.subTest(side=side):
                play = record(end=2, bat_side=side, pitches=[
                    {'code': 'B', 'line': 1, 'type': 'Slider', 'zone': 12,
                     'location': 'inside', 'commentaryRng': {'event': {'pitch': [0]}}},
                    {'code': 'C', 'line': 2, 'type': 'Curveball', 'zone': 11,
                     'location': 'outside_corner', 'commentaryRng': {'event': {'pitch': [0]}}}])
                data = fixtures.compile_game(ledger_with([play]), b'Slider inside.\nCurveball called outside corner.\n')
                events = data['liveData']['plays']['allPlays'][0]['playEvents']
                self.assertEqual([e['details']['location'] for e in events], ['inside', 'outside_corner'])
                renderer = NarrativeRenderer(data)
                text = renderer.render()
                lo, hi = renderer._play_line_map[0]
                body = '\n'.join(text.splitlines()[lo:hi]).lower()
                self.assertIn('slider misses inside', body)
                self.assertIn('curveball, called a strike on the outside corner', body)
                self.assertIn('one and one', body)

    def test_unknown_ball_location_does_not_acquire_an_invented_location(self):
        play = record(pitches=[{'code': 'B', 'line': 1, 'type': 'Slider',
                                'commentaryRng': {'event': {'pitch': [0]}}}])
        data = fixtures.compile_game(ledger_with([play]), b'Ball one.\n')
        renderer = NarrativeRenderer(data)
        text = renderer.render()
        lo, hi = renderer._play_line_map[0]
        body = '\n'.join(text.splitlines()[lo:hi]).lower()
        self.assertIn('one and oh', body)
        pitch_text = next(line for line in body.splitlines() if 'slider' in line).split('slider', 1)[1]
        self.assertNotRegex(pitch_text, r'outside|inside|dirt|high|low|away|tight|plate|letters|knees')

    def test_unspecified_terminal_strike_never_invents_swinging_or_looking(self):
        play = record(outcome='Strikeout', end=3, outs=1, pitches=[
            {'code': 'C', 'line': 1}, {'code': 'C', 'line': 2},
            {'code': 'U', 'line': 3, 'isStrike': True}])
        data = fixtures.compile_game(ledger_with([play]), b'Strike.\nStrike.\nStrike three.\n')
        for draw in range(4):
            data['liveData']['plays']['allPlays'][0]['commentaryRng'] = {'play_outcome': {'play': [draw]}}
            for Renderer in (NarrativeRenderer, StatcastRenderer):
                with self.subTest(draw=draw, renderer=Renderer.__name__):
                    renderer = Renderer(data)
                    text = renderer.render()
                    if Renderer is NarrativeRenderer:
                        lo, hi = renderer._play_line_map[0]
                        text = '\n'.join(text.splitlines()[lo:hi])
                    self.assertRegex(text.lower(), r'strikes out|down on strikes|strikeout')
                    self.assertNotRegex(text.lower(), r'swinging|looking|swing and a miss|goes down swinging')

    def test_statcast_keeps_the_observed_hit_by_pitch_row(self):
        play = record(outcome='Hit By Pitch', pitches=[{'code': 'H', 'line': 1, 'type': 'Slider'}])
        data = fixtures.compile_game(ledger_with([play]), b'Slider hits the batter.\n')
        text = StatcastRenderer(data).render()
        self.assertIn('  Hit by pitch: Slider', text)
        self.assertIn('Result: Hit by Pitch.', text)

    def test_wholly_unknown_pitch_does_not_assert_an_unchanged_count(self):
        play = record(pitches=[{'code': 'U', 'line': 1}])
        data = fixtures.compile_game(ledger_with([play]), b'A pitch was delivered; its result is unvoiced.\n')
        renderer = NarrativeRenderer(data)
        text = renderer.render()
        lo, hi = renderer._play_line_map[0]
        body = '\n'.join(text.splitlines()[lo:hi]).lower()
        self.assertNotRegex(body, r'oh and oh|ball one|strike one')
        self.assertEqual(len(data['liveData']['plays']['allPlays'][0]['playEvents']), 1)

    def test_unclassified_safe_arrival_uses_the_final_known_destination(self):
        for destination, phrase in [('2B', 'reaches second safely'), ('3B', 'reaches third safely'),
                                     ('score', 'comes around to score')]:
            play = record(outcome='Reached Base', pitches=[{'code': 'X', 'line': 1}],
                          runners=[movement('Away Batter 1', None, destination)],
                          score=[int(destination == 'score'), 0])
            data = fixtures.compile_game(ledger_with([play]), b'The batter safely reaches the announced destination.\n')
            for Renderer in (NarrativeRenderer, StatcastRenderer):
                with self.subTest(destination=destination, renderer=Renderer.__name__):
                    text = Renderer(data).render().lower()
                    self.assertIn(phrase, text)
                    self.assertNotIn('reaches first safely', text)
                    self.assertEqual(data['liveData']['linescore']['teams']['away']['hits'], 0)

    def test_strict_facts_omit_unknown_managers_and_keep_identified_managers(self):
        ledger = ledger_with([record()])
        ledger['game']['away_manager'] = 'Confirmed Manager'
        data = fixtures.compile_game(ledger, b'Observed appearance.\n')
        self.assertTrue(data['gameData']['broadcast']['strictFacts'])
        text = NarrativeRenderer(data).render()
        self.assertIn('Confirmed Manager', text)
        self.assertNotIn('Mick Jenkins', text)
        self.assertNotIn('Manager Samuels', text)

    def test_unlocated_groundball_hit_never_becomes_an_airborne_hit(self):
        for fielders in ([], [{'name': 'Home Pitcher', 'position': 'P'}]):
            with self.subTest(fielders=fielders):
                play = record(outcome='Single', pitches=[{'code': 'X', 'line': 1}],
                              hit={'trajectory': 'ground_ball'}, fielders=fielders)
                data = fixtures.compile_game(ledger_with([play]), b'A ground ball and the batter is safe.\n')
                renderer = NarrativeRenderer(data)
                text = renderer.render()
                lo, hi = renderer._play_line_map[0]
                body = '\n'.join(text.splitlines()[lo:hi]).lower()
                self.assertNotRegex(body, r'\b(lined|liner|looper|fly ball|popped|drops in)\b')
                self.assertNotRegex(body, r'(?:left|right|center) field|up the middle')

    def test_partial_games_never_declare_a_winner_or_game_over(self):
        for number in (1, 51):
            ledger = json.loads((fixtures.LEDGER_DIR / f'episode_{number:03}.json').read_text())
            data = fixtures.compile_game(ledger, (fixtures.SOURCE_DIR / ledger['source_file']).read_bytes())
            for renderer in (NarrativeRenderer, StatcastRenderer):
                with self.subTest(episode=number, renderer=renderer.__name__):
                    text = renderer(data).render()
                    self.assertNotIn('GAME OVER', text)
                    final_lines = '\n'.join(text.splitlines()[-3:])
                    self.assertIn('Score at the end of our coverage:', final_lines)
                    self.assertNotRegex(final_lines.lower(), r'winner|wins|have won|has won|final score')


class TestFullTranscriptFitter(unittest.TestCase):
    def test_fitted_start_and_outcome_draws_survive_production_replay(self):
        source = (b'Welcome to Example Field.\nThe visiting Sample Visitors.\n'
                  b'Away Batter 1 steps in against Home Pitcher.\n'
                  b'Fastball misses low. One and oh.\n'
                  b'Hard grounder to short. Short Stop fires to first for out number one.\n')
        play = record(outcome='Groundout', start=3, end=5, outs=1,
                      pitches=[{'code': 'B', 'type': 'Fastball', 'line': 4},
                               {'code': 'X', 'type': 'pitch', 'line': 5}],
                      hit={'location': 'SS', 'trajectory': 'ground_ball'},
                      fielders=[{'name': 'Short Stop', 'position': 'SS'}])
        ledger = ledger_with([play])
        before_ledger = copy.deepcopy(ledger)
        data, rendered = fitting.fit_game(ledger, source)
        self.assertEqual(ledger, before_ledger)
        saved = json.loads(json.dumps(data))
        play_draws = saved['liveData']['plays']['allPlays'][0]['commentaryRng']
        for point in ('play_start', 'play_outcome'):
            self.assertIn(point, play_draws)
            self.assertEqual(set(play_draws[point]), set(STREAM_NAMES))
            self.assertTrue(any(play_draws[point].values()), f'No captured {point} choices')
            for draws in play_draws[point].values():
                self.assertTrue(all(type(draw) is int and draw >= 0 for draw in draws))
        immutable = copy.deepcopy(saved)
        with patch.object(fitting.FittingRNG, '__init__', side_effect=AssertionError('Replay must not fit')):
            self.assertEqual(NarrativeRenderer(saved).render(), rendered)
            self.assertEqual(NarrativeRenderer(saved).render(), rendered)
            self.assertEqual(replay_with_other_times(saved), rendered)
        self.assertEqual(saved, immutable)

    def test_gates_are_fitted_per_play_not_per_game(self):
        """One game: the source recaps one returning batter and not the other."""
        grounder = dict(hit={'location': 'SS', 'trajectory': 'ground_ball'},
                        fielders=[{'name': 'Home Batter 8', 'position': 'SS'}])
        source = (b'Welcome to Example Field.\n'
                  b'Away Batter 1 steps in.\n'
                  b'And the pitch... Grounder to short, and he is out at first.\n'
                  b'Away Batter 2 steps in.\n'
                  b'And the pitch... Grounder to short, and he is out at first.\n'
                  b'Away Batter 1 steps in. Batter 1 grounded out in the first.\n'
                  b'And the pitch... Grounder to short, and he is out at first.\n'
                  b'Away Batter 2 steps in.\n'
                  b'And the pitch... Grounder to short, and he is out at first.\n')
        plays = [
            record(outcome='Groundout', start=2, end=3, outs=1,
                   pitches=[{'code': 'X', 'type': 'pitch', 'line': 3}], **grounder),
            record(batter='Away Batter 2', outcome='Groundout', start=4, end=5, outs=2,
                   pitches=[{'code': 'X', 'type': 'pitch', 'line': 5}], **grounder),
            record(outcome='Groundout', start=6, end=7, outs=3,
                   pitches=[{'code': 'X', 'type': 'pitch', 'line': 7}], **grounder),
            record(batter='Away Batter 2', outcome='Groundout', start=8, end=9, inning=2, outs=1,
                   pitches=[{'code': 'X', 'type': 'pitch', 'line': 9}], **grounder),
        ]
        data, rendered = fitting.fit_game(ledger_with(plays), source)
        renderer = NarrativeRenderer(copy.deepcopy(data))
        self.assertEqual(renderer.render(), rendered)
        lines = rendered.splitlines()

        def play_text(index):
            low, high = renderer._play_line_map[index]
            return '\n'.join(lines[low:high])
        self.assertIn('grounded out', play_text(2))
        self.assertNotIn('grounded out', play_text(3))
        # The recap gate is the first colour draw at each play start.
        recap = [play['commentaryRng']['play_start']['color'][0]
                 for play in data['liveData']['plays']['allPlays']]
        self.assertLess(recap[2], 70)
        self.assertGreaterEqual(recap[3], 70)

    def test_fitted_episodes_mix_gate_outcomes_within_a_game(self):
        for number in (5, 46):
            with self.subTest(episode=number):
                data = json.loads((fixtures.OUTPUT_DIR / f'episode_{number:03d}.json').read_text())
                plays = data['liveData']['plays']['allPlays']
                recap = {play['commentaryRng']['play_start']['color'][0] < 70 for play in plays}
                optional = {draw < 50 for play in plays
                            for owner in [play] + play['playEvents']
                            for point in owner.get('commentaryRng', {}).values()
                            for draw in point.get('optional', [])}
                self.assertEqual(recap, {True, False})
                self.assertEqual(optional, {True, False})


class TestFullTranscriptCatalog(unittest.TestCase):
    def catalog(self, directory, extension):
        return {int(path.stem.split('_')[1]): path for path in directory.glob(f'episode_*.{extension}')}

    def test_all_seventeen_sources_have_full_ledgers_fixtures_and_snapshots(self):
        for directory, extension in ((fixtures.SOURCE_DIR, 'txt'), (fixtures.LEDGER_DIR, 'json'),
                                     (fixtures.OUTPUT_DIR, 'json'), (fixtures.OUTPUT_DIR, 'txt')):
            with self.subTest(directory=directory, extension=extension):
                self.assertEqual(set(self.catalog(directory, extension)), EPISODES)

    def test_every_observed_play_and_pitch_retains_its_source_reference(self):
        for number, path in self.catalog(fixtures.LEDGER_DIR, 'json').items():
            with self.subTest(episode=number):
                ledger = json.loads(path.read_text())
                source = (fixtures.SOURCE_DIR / ledger['source_file']).read_bytes()
                before = copy.deepcopy(ledger)
                data = fixtures.compile_game(ledger, source)
                self.assertIs(type(ledger['complete']), bool)
                self.assertGreater(len(ledger['plays']), 30)
                self.assertEqual(data['gameData']['source']['sha256'], hashlib.sha256(source).hexdigest())
                self.assertEqual(len(data['liveData']['plays']['allPlays']), len(ledger['plays']))
                for original, compiled in zip(ledger['plays'], data['liveData']['plays']['allPlays']):
                    self.assertEqual(compiled['source'], {'start': original['source_start'], 'end': original['source_end']})
                    expected = [(p['line'], p['code'] != 'A') for p in original['pitches']]
                    # A pinch hitter's Offensive Substitution action comes from the
                    # ledger's `substitution`, not from a pitch line.
                    self.assertEqual([(p['sourceLine'], p['isPitch']) for p in compiled['playEvents']
                                      if not p.get('isSubstitution')], expected)
                    self.assertEqual(any(p.get('isSubstitution') for p in compiled['playEvents']),
                                     'substitution' in original)
                    self.assertEqual(compiled['about']['isComplete'], original['outcome'] != 'Incomplete')
                self.assertEqual(ledger, before)

    def test_reviewed_episode_event_totals_cannot_shrink_silently(self):
        for number, (appearances, pitches, actions) in REVIEWED_EVENT_COUNTS.items():
            with self.subTest(episode=number):
                ledger = json.loads((fixtures.LEDGER_DIR / f'episode_{number:03}.json').read_text())
                self.assertEqual(len(ledger['plays']), appearances)
                self.assertEqual(sum(p['code'] != 'A' for a in ledger['plays'] for p in a['pitches']), pitches)
                self.assertEqual(sum(p['code'] == 'A' for a in ledger['plays'] for p in a['pitches']), actions)

    def test_persisted_fixtures_match_reviewed_baseball_facts(self):
        def without_draws(value):
            if isinstance(value, dict):
                return {key: without_draws(item) for key, item in value.items() if key != 'commentaryRng'}
            if isinstance(value, list):
                return [without_draws(item) for item in value]
            return value

        for number, path in self.catalog(fixtures.LEDGER_DIR, 'json').items():
            with self.subTest(episode=number):
                ledger = json.loads(path.read_text())
                source = (fixtures.SOURCE_DIR / ledger['source_file']).read_bytes()
                expected = fixtures.compile_game(ledger, source)
                saved = json.loads((fixtures.OUTPUT_DIR / path.name).read_text())
                self.assertEqual(without_draws(saved), without_draws(expected))

    def test_audited_steal_pitch_and_pitching_change_keep_their_facts(self):
        one = json.loads((fixtures.LEDGER_DIR / 'episode_001.json').read_text())
        five = json.loads((fixtures.LEDGER_DIR / 'episode_005.json').read_text())
        final_groundout = next(p for p in one['plays'] if p['source_start'] == 436)
        self.assertEqual(final_groundout['fielders'], [{'name': 'Belden Inohosa', 'position': 'P'}])
        steal = next(p for p in five['plays'] if p['source_start'] == 407)
        self.assertEqual([(e['line'], e['code']) for e in steal['pitches'][:3]],
                         [(408, 'B'), (408, 'A'), (409, 'B')])
        ortega = next(p for p in five['plays'] if p['source_start'] == 54)
        self.assertTrue(any(e['line'] == 55 and e['code'] == 'A' for e in ortega['pitches']))
        self.assertNotIn('home_manager', five['game'])

    def test_missing_innings_and_unfinished_broadcasts_are_not_fabricated(self):
        one = json.loads((fixtures.LEDGER_DIR / 'episode_001.json').read_text())
        fifty_one = json.loads((fixtures.LEDGER_DIR / 'episode_051.json').read_text())
        self.assertFalse(one['complete'])
        self.assertFalse(fifty_one['complete'])
        self.assertTrue(one['ending_reason'])
        self.assertTrue(fifty_one['ending_reason'])
        self.assertFalse(any(p['inning'] == 8 and p['top'] for p in one['plays']))
        self.assertEqual(one['plays'][-1]['outcome'], 'Incomplete')
        self.assertEqual(one['plays'][-1]['outs'], 1)
        self.assertEqual([p['code'] for p in one['plays'][-1]['pitches']], ['C', 'B'])
        self.assertEqual({p['inning'] for p in fifty_one['plays']}, {1, 2, 3, 4, 5, 6})
        self.assertFalse(any(p['inning'] == 6 and not p['top'] for p in fifty_one['plays']))
        for ledger in (one, fifty_one):
            data = fixtures.compile_game(ledger, (fixtures.SOURCE_DIR / ledger['source_file']).read_bytes())
            self.assertEqual(len(data['liveData']['plays']['allPlays']), len(ledger['plays']))
            self.assertFalse(data['gameData']['broadcast']['complete'])

    def test_whole_broadcast_comparisons_meet_each_reviewed_minimum(self):
        from full_transcript_comparison import check_full_transcripts

        results = check_full_transcripts()
        self.assertEqual({result['episode'] for result in results}, EPISODES)
        failures = {result['episode']: result['failures'] for result in results if result['failures']}
        self.assertEqual(failures, {}, f'Full broadcast comparison regressed: {failures}')

    def test_wording_similarity_cannot_hide_missing_events_and_counts_cannot_hide_bad_wording(self):
        from full_transcript_comparison import game_failures
        from pbp_comparison import FULL_TRANSCRIPT_MINIMUMS

        for episode, minimums in FULL_TRANSCRIPT_MINIMUMS.items():
            with self.subTest(episode=episode):
                complete = {'episode': episode, **minimums}
                self.assertEqual(game_failures(complete), [])
                fewer_pitches = {**complete, 'pitches': minimums['pitches'] - 1,
                                 'ngram': 1.0, 'mean_play_word_coverage': 1.0}
                self.assertTrue(any('pitches' in failure for failure in game_failures(fewer_pitches)))
                weak_wording = {**complete, 'ngram': 0.0, 'mean_play_word_coverage': 0.0}
                failures = game_failures(weak_wording)
                self.assertTrue(any('ngram' in failure for failure in failures))
                self.assertTrue(any('mean_play_word_coverage' in failure for failure in failures))

    def test_all_full_game_snapshots_replay_from_immutable_json_without_timing_rng(self):
        for number, path in self.catalog(fixtures.OUTPUT_DIR, 'json').items():
            with self.subTest(episode=number):
                data = json.loads(path.read_text())
                before = copy.deepcopy(data)
                expected = path.with_suffix('.txt').read_text()
                self.assertEqual(NarrativeRenderer(data).render(), expected)
                self.assertEqual(NarrativeRenderer(json.loads(json.dumps(data))).render(), expected)
                self.assertEqual(replay_with_other_times(data), expected)
                self.assertEqual(data, before)


if __name__ == '__main__':
    unittest.main()
