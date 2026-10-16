"""Simulation behaviour that gave simulated games away to blind judges, held
to bands around what 24 real 2026 StatsAPI feeds show.

The prose and structural checks use 200 fixed games (seeds 9000+). Rare
baserunning rates use a shared 2,400-game batch, with the same rate bands.
"""
import collections
import functools
import re
import statistics
import unittest
from unittest.mock import patch

import fieldsim
from baseball import BaseballSimulator
from renderers import NarrativeRenderer, StatcastRenderer
from teams import TEAMS

SEEDS = range(9000, 9200)
THROWN_OUT = ('r_thrown_out', 'r_out_stretching')
HITS = ('single', 'double', 'triple')


def simulate(seed, home="BAY_BOMBERS", away="PC_PILOTS"):
    game = BaseballSimulator(TEAMS[home], TEAMS[away], game_seed=seed)
    game.play_game()
    return game


@functools.lru_cache(maxsize=1)
def baserunning_rate_counts():
    """Rare-event rates need more opportunities than the prose audit batch.

    Use the 2,400 judge-roster games from the integration calibration: the
    advancement, count and strategy reports' seed ranges. Cache only counts,
    so both rate tests share the sample without retaining thousands of feeds.
    """
    counts = collections.Counter()
    for seeds in (range(12000, 12800), range(20000, 21000), range(21000, 21600)):
        for seed in seeds:
            game = simulate(seed)
            counts['games'] += 1
            for play in game.gameday_data['liveData']['plays']['allPlays']:
                thrown_out = [r for r in play['runners']
                              if r['movement']['isOut'] and r['details']['movementReason'] in THROWN_OUT]
                counts['out_plays'] += bool(thrown_out)
                for runner in thrown_out:
                    counts[runner['details']['movementReason'], runner['movement']['outBase']] += 1
                for event in play['playEvents']:
                    details = event['details']
                    kind = details.get('eventType', '')
                    if kind in ('stolen_base', 'caught_stealing') or kind.startswith('pickoff_caught_stealing_'):
                        # The real-feed target includes runners caught after
                        # a pickoff throw, as does the strategy calibration.
                        for move in details['runners']:
                            base = move['toBase']
                            counts[base] += 1
                            counts['cs_' + base] += move['isOut']
    return counts


def pitcher_stints(plays, top):
    """One team's pitchers in order: [pitcher id, plays he pitched, whether he
    came in to start a half-inning]."""
    side = [p for p in plays if p['about']['isTopInning'] == top]
    stints = []
    for i, play in enumerate(side):
        pid = play['matchup']['pitcher']['id']
        if not stints or stints[-1][0] != pid:
            clean = i == 0 or side[i - 1]['about']['inning'] != play['about']['inning']
            stints.append([pid, [], clean])
        stints[-1][1].append((i, play))
    return side, stints


def outs_recorded(side, stint_plays):
    outs = 0
    for i, play in stint_plays:
        same_half = i and side[i - 1]['about']['inning'] == play['about']['inning']
        outs += play['count']['outs'] - (side[i - 1]['count']['outs'] if same_half else 0)
    return outs


def pitch_types(stint_plays):
    return {e['details']['type']['description'] for _, play in stint_plays
            for e in play['playEvents'] if e.get('isPitch')}


def credit_chain(runner):
    return [(c['credit'], c['position']['abbreviation']) for c in runner.get('credits', [])]


class SimulationBatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {seed: simulate(seed).gameday_data for seed in SEEDS}
        cls.all_plays = {seed: data['liveData']['plays']['allPlays'] for seed, data in cls.games.items()}


class TestPitchingChanges(SimulationBatch):
    """Real: 3.29 relievers per team-game; starters 4.7 innings on 76 pitches
    (sd 24), from one inning to eight; a third of the changes mid-inning."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.relievers, cls.starter_outs, cls.starter_pitches = [], [], []
        cls.same_exit = cls.mid = cls.between = cls.short_stints = 0
        for plays in cls.all_plays.values():
            exits = []
            for top in (True, False):
                side, stints = pitcher_stints(plays, top)
                cls.relievers.append(len(stints) - 1)
                for n, (_, stint, clean) in enumerate(stints):
                    last_index, last_play = stint[-1]
                    finished = last_play['count']['outs'] >= 3 or last_index == len(side) - 1
                    if n == 0:
                        outs = outs_recorded(side, stint)
                        cls.starter_outs.append(outs)
                        cls.starter_pitches.append(sum(e.get('isPitch', False) for _, p in stint for e in p['playEvents']))
                        exits.append(outs)
                    else:
                        cls.mid += not clean
                        cls.between += clean
                        cls.short_stints += len(stint) < 3 and not finished
            cls.same_exit += exits[0] == exits[1]

    def test_relievers_per_team_game(self):
        self.assertTrue(2.9 <= statistics.mean(self.relievers) <= 3.9, statistics.mean(self.relievers))
        # Not the same number every night: real teams use from one to six.
        self.assertGreaterEqual(len(set(self.relievers)), 5)
        self.assertLess(max(collections.Counter(self.relievers).values()) / len(self.relievers), 0.45)

    def test_starters_do_not_all_leave_on_the_same_schedule(self):
        innings = [outs / 3 for outs in self.starter_outs]
        self.assertTrue(4.2 <= statistics.mean(innings) <= 5.3, statistics.mean(innings))
        self.assertTrue(66 <= statistics.mean(self.starter_pitches) <= 88, statistics.mean(self.starter_pitches))
        self.assertGreaterEqual(statistics.pstdev(self.starter_pitches), 16)
        # Some are gone by the third, some go seven.
        self.assertGreater(sum(i < 3 for i in innings) / len(innings), 0.04)
        self.assertGreater(sum(i >= 7 for i in innings) / len(innings), 0.04)
        # Both starters out after the same number of outs: 17% in the real feeds.
        self.assertLess(self.same_exit / len(self.games), 0.22)

    def test_some_changes_come_mid_inning_but_most_do_not(self):
        share = self.mid / (self.mid + self.between)
        self.assertTrue(0.2 <= share <= 0.45, share)

    def test_three_batter_minimum(self):
        self.assertEqual(self.short_stints, 0)


class TestRunawayGames(SimulationBatch):
    def test_seed_71_is_not_a_blowout(self):
        """Seed 71 ended 49-2: the closer, last man in a three-man bullpen,
        pitched from the fourth on and walked 27 in the ninth."""
        game = simulate(71)
        runs = game.gameday_data['liveData']['linescore']['teams']
        self.assertLess(max(runs['home']['runs'], runs['away']['runs']), 20)
        self.assertLess(max(game.pitch_counts.values()), 135)

    def test_twenty_run_games_are_rare(self):
        """Twenty runs is a once-a-season game."""
        totals = [runs for plays in self.all_plays.values()
                  for runs in (plays[-1]['result']['awayScore'], plays[-1]['result']['homeScore'])]
        self.assertLessEqual(sum(runs >= 20 for runs in totals), 1)
        self.assertLess(max(totals), 26)

    def test_a_team_out_of_relievers_still_throws_strikes(self):
        """A pitcher left in with nobody behind him tires, but only so far."""
        for seed in (1, 2, 3):
            game = simulate(seed, home="CADILLAC_CARS")   # one pitcher on the roster
            walks = sum(p['result']['event'] == 'Walk' and p['about']['isTopInning']
                        for p in game.gameday_data['liveData']['plays']['allPlays'])
            self.assertLess(walks, 15, f"seed {seed}")


class TestOutsOnTheBases(SimulationBatch):
    """Real: 29 in 136 games (0.213/game) with these two movement reasons
    (first to third, second to home, first to home on a double, the batter
    stretching). The old 0.29 also included rundowns, interference and steals
    before contact; those are separate events from the extra-base races."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plays = [(seed, index, play) for seed, plays in cls.all_plays.items()
                     for index, play in enumerate(plays)
                     if any(r['details']['movementReason'] in THROWN_OUT for r in play['runners'])]

    def test_rate(self):
        counts = baserunning_rate_counts()
        rate = counts['out_plays'] / counts['games']
        self.assertTrue(0.15 <= rate <= 0.42, rate)
        kinds = {key for key in counts if isinstance(key, tuple)}
        self.assertLessEqual({('r_thrown_out', '3B'), ('r_thrown_out', '4B'), ('r_out_stretching', '2B')}, kinds)

    def test_advancement_rates_hold(self):
        second_home, first_third = collections.Counter(), collections.Counter()
        for plays in self.all_plays.values():
            for play in plays:
                if play['result']['eventType'] != 'single':
                    continue
                outs_before = play['count']['outs'] - sum(r['movement']['isOut'] for r in play['runners'])
                for runner in play['runners']:
                    movement = runner['movement']
                    safe_at = None if movement['isOut'] else movement['end']
                    if movement['originBase'] == '2B':
                        second_home[outs_before, 'n'] += 1
                        second_home[outs_before, 'scored'] += safe_at == 'score'
                    if movement['originBase'] == '1B':
                        first_third['n'] += 1
                        first_third['third'] += safe_at in ('3B', 'score')
        # Join successive real-feed movements on one hit: a runner can be
        # recorded first going to third, then scoring on the same single.
        # The 136-feed rates are 34/60/78%, rather than the old pooled 30%.
        for outs, low, high in ((0, 0.20, 0.45), (1, 0.43, 0.73), (2, 0.65, 0.90)):
            self.assertTrue(low <= second_home[outs, 'scored'] / second_home[outs, 'n'] <= high, second_home)
        self.assertTrue(0.28 <= first_third['third'] / first_third['n'] <= 0.42, first_third)

    def test_the_feed_carries_the_out(self):
        for seed, index, play in self.plays:
            where = f"seed {seed} play {index}"
            self.assertIn(play['result']['eventType'], HITS, where)
            all_outs = [r for r in play['runners'] if r['movement']['isOut']]
            out = [r for r in all_outs if r['details']['movementReason'] in THROWN_OUT]
            self.assertEqual(len(out), 1, where)
            runner = out[0]
            self.assertEqual(runner['details']['eventType'], 'other_out', where)
            self.assertIn(runner['movement']['outBase'], ('2B', '3B', '4B'), where)
            self.assertIsNone(runner['movement']['end'], where)
            self.assertEqual(runner['movement']['outNumber'], play['count']['outs'], where)
            chain = credit_chain(runner)
            self.assertEqual(chain[-1][0], 'putout', where)
            self.assertIn(chain[0], [('assist', 'LF'), ('assist', 'CF'), ('assist', 'RF')], where)
            self.assertEqual(chain[-1][1], {'4B': 'C', '3B': '3B'}.get(runner['movement']['outBase'], chain[-1][1]), where)
            self.assertIn(' out at ', play['result']['description'], where)
            # The out is on top of the outs there were, and the inning is over at three.
            previous = self.all_plays[seed][index - 1] if index else None
            same_half = previous and previous['about']['inning'] == play['about']['inning'] \
                and previous['about']['isTopInning'] == play['about']['isTopInning']
            self.assertEqual(play['count']['outs'], (previous['count']['outs'] if same_half else 0) + len(all_outs), where)
            if play['count']['outs'] == 3 and index + 1 < len(self.all_plays[seed]):
                following = self.all_plays[seed][index + 1]['about']
                self.assertNotEqual((following['inning'], following['isTopInning']),
                                    (play['about']['inning'], play['about']['isTopInning']), where)
            # The batter keeps his hit, and is on base unless he was the one thrown out.
            batter_id = play['matchup']['batter']['id']
            batter_moves = [r for r in play['runners'] if r['details']['runner']['id'] == batter_id]
            self.assertEqual(len(batter_moves), 1, where)
            if runner['details']['movementReason'] == 'r_out_stretching':
                self.assertEqual(runner['details']['runner']['id'], batter_id, where)
                self.assertTrue(batter_moves[0]['movement']['isOut'], where)
            else:
                self.assertNotEqual(runner['details']['runner']['id'], batter_id, where)
                self.assertEqual(batter_moves[0]['details']['eventType'], play['result']['eventType'], where)
                self.assertFalse(batter_moves[0]['movement']['isOut'], where)

    def test_the_batter_is_credited_with_his_hit(self):
        seed, _, _ = self.plays[0]
        data = self.games[seed]
        hits = collections.Counter()
        for play in data['liveData']['plays']['allPlays']:
            if play['result']['eventType'] in HITS + ('home_run',):
                hits['away' if play['about']['isTopInning'] else 'home'] += 1
        for side in ('home', 'away'):
            self.assertEqual(data['liveData']['linescore']['teams'][side]['hits'], hits[side])
            self.assertEqual(data['liveData']['boxscore']['teams'][side]['teamStats']['batting']['hits'], hits[side])
        # Every out is charged to a pitcher, the ones on the bases too.
        for side, top in (('home', True), ('away', False)):
            innings = sum(1 for half in {(p['about']['inning']) for p in data['liveData']['plays']['allPlays']
                                         if p['about']['isTopInning'] == top
                                         and p['count']['outs'] == 3})
            self.assertGreaterEqual(data['liveData']['boxscore']['teams'][side]['teamStats']['pitching']['outs'], innings * 3)

    def _rendered_play(self, seed, index):
        renderer = NarrativeRenderer(self.games[seed], seed=seed)
        lines = renderer.render().split('\n')
        start, end = renderer._play_line_map[index]
        return ' '.join(lines[start:end])

    def _first(self, reason, base, third_out):
        for seed, index, play in self.plays:
            runner = next(r for r in play['runners'] if r['details']['movementReason'] in THROWN_OUT)
            if (runner['details']['movementReason'] == reason and runner['movement']['outBase'] == base
                    and (play['count']['outs'] == 3) == third_out):
                return seed, index, play, runner
        self.fail(f"no {reason} at {base} (third out: {third_out}) in the batch")

    def test_narration_of_a_runner_thrown_out_at_the_plate(self):
        seed, index, play, runner = self._first('r_thrown_out', '4B', third_out=False)
        text = self._rendered_play(seed, index)
        name = runner['details']['runner']['fullName'].split()[-1]
        self.assertRegex(text, rf"{name} (is being waved around third|tries to score|rounds third and heads for home)|sending {name}")
        self.assertRegex(text, r"out at the plate|they got him|out at home")
        self.assertRegex(text, r"for (out number (one|two)|the (first|second) out)|\b(one|two) (out|away|down)")
        self.assertNotIn(f"{name} will score", text)
        self.assertNotIn(f"{name} scores", text)

    def test_narration_when_the_out_on_the_bases_ends_the_inning(self):
        for reason, base in (('r_thrown_out', '4B'), ('r_thrown_out', '3B')):
            seed, index, play, runner = self._first(reason, base, third_out=True)
            text = self._rendered_play(seed, index)
            name = runner['details']['runner']['fullName'].split()[-1]
            self.assertIn(name, text)
            self.assertRegex(text, r"to end the (inning|ball ?game)|retire the side|side is retired|inning is over|"
                                   r"that('s| is| will do it for) the|for (out number three|the (third|final) out)")
            # Nothing about the hit's situation after the inning is over.
            self.assertNotRegex(text.split(name)[-1], r"(single|double|base hit) for ")
            # The next thing rendered is the other half, with nobody on.
            following = self.all_plays[seed][index + 1] if index + 1 < len(self.all_plays[seed]) else None
            if following:
                self.assertEqual(following['matchup']['splits']['menOnBase'], 'Empty')

    def test_narration_of_a_batter_out_stretching(self):
        # This rare play need not turn up before the third out in every batch.
        # Make the throw deterministic while keeping the engine's feed and prose.
        game = BaseballSimulator(TEAMS['BAY_BOMBERS'], TEAMS['PC_PILOTS'], game_seed=0)
        field = fieldsim.BattedBall('Single', 'CF', 'line_drive', 'CF', 0.0, (0, 200), 200,
                                   release=5.0, release_point=(0, 200), batter_out=2)
        outcomes = iter(('Single', 'Strikeout', 'Strikeout'))

        def at_bat(batter, pitcher):
            outcome = next(outcomes)
            event = {'index': 0, 'isPitch': True, 'count': {'balls': 0, 'strikes': 0},
                     'details': {'code': 'X' if outcome == 'Single' else 'S',
                                 'description': outcome, 'type': {'code': 'FF', 'description': 'Fastball'}},
                     'pitchData': {'startSpeed': 94.0}}
            if outcome == 'Single':
                game._play_field = field
                event['hitData'] = {'trajectory': field.trajectory, 'location': field.location}
            return outcome, None, [event]

        with patch.object(game, '_simulate_at_bat', side_effect=at_bat):
            game._simulate_half_inning()
        renderer = NarrativeRenderer(game.gameday_data, seed=0)
        lines = renderer.render().splitlines()
        start, end = renderer._play_line_map[0]
        text = ' '.join(lines[start:end])
        self.assertEqual(game.gameday_data['liveData']['plays']['allPlays'][0]['count']['outs'], 1)
        self.assertRegex(text, r"thinking double|stretch it into a double|trying for a double")
        self.assertNotRegex(text, r"\baboard\b|stand-up")

    def test_statcast_log_says_the_runner_was_thrown_out(self):
        seed, index, play, runner = self._first('r_thrown_out', '3B', third_out=False)
        text = StatcastRenderer(self.games[seed], seed=seed).render()
        self.assertIn(f"{runner['details']['runner']['fullName']} is thrown out at third.", text)


class TestWhoFieldsWhat(SimulationBatch):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.groundouts, cls.infield_hits, cls.bunts = collections.Counter(), collections.Counter(), collections.Counter()
        cls.air_outs, cls.double_plays = collections.Counter(), collections.Counter()
        for plays in cls.all_plays.values():
            for play in plays:
                event = play['result']['event']
                batter_id = play['matchup']['batter']['id']
                batter = next((r for r in play['runners'] if r['details']['runner']['id'] == batter_id), None)
                hit_data = next((e['hitData'] for e in play['playEvents'] if 'hitData' in e), {})
                chain = credit_chain(batter) if batter else []
                if event == 'Groundout':
                    cls.groundouts['-'.join(pos for _, pos in chain)] += 1
                elif event in ('Flyout', 'Lineout', 'Pop Out') and chain:
                    cls.air_outs[chain[-1][1]] += 1
                elif event in ('Sacrifice Bunt', 'Bunt Ground Out') and chain:
                    cls.bunts[chain[0][1]] += 1
                elif event == 'Double Play':
                    first = min((r for r in play['runners'] if r['movement']['isOut']),
                                key=lambda r: r['movement']['outNumber'])
                    cls.double_plays[credit_chain(first)[0][1]] += 1
                elif event == 'Single' and hit_data.get('location') in ('P', 'C', '1B', '2B', '3B', 'SS'):
                    cls.infield_hits[hit_data['location']] += 1

    def test_pitcher_covers_first_about_once_a_game(self):
        """Real: 0.96 a game (3-1 putouts), against 1.4 the first baseman takes himself."""
        covers = self.groundouts['1B-P'] / len(self.games)
        self.assertTrue(0.5 <= covers <= 1.45, covers)
        self.assertGreater(self.groundouts['1B'], self.groundouts['1B-P'])

    def test_narration_says_covering_only_when_the_pitcher_covered(self):
        said = 0
        for seed in list(SEEDS)[:40]:
            renderer = NarrativeRenderer(self.games[seed], seed=seed)
            lines = renderer.render().split('\n')
            for index, play in enumerate(self.all_plays[seed]):
                start, end = renderer._play_line_map[index]
                text = ' '.join(lines[start:end])
                batter = next((r for r in play['runners']
                               if r['details']['runner']['id'] == play['matchup']['batter']['id']), None)
                chain = credit_chain(batter) if batter else []
                if play['result']['event'] == 'Groundout' and re.search(r'covering|at the bag', text):
                    said += 1
                    self.assertEqual(chain, [('assist', '1B'), ('putout', 'P')], f"seed {seed} play {index}: {text}")
                if play['result']['event'] == 'Groundout' and chain == [('putout', '1B')]:
                    self.assertNotRegex(text, r'covering|at the bag', f"seed {seed} play {index}")
        self.assertLess(said / 40, 1.5)

    def test_infield_hits_go_to_the_left_side_not_first_base(self):
        """Real, per 100 games: third 38, short 38, second 12, first 4, pitcher 4."""
        games = len(self.games)
        self.assertLess(self.infield_hits['1B'] / games, 0.1)
        self.assertGreater(self.infield_hits['3B'] / games, 0.15)
        self.assertTrue(0.5 <= sum(self.infield_hits.values()) / games <= 1.4, self.infield_hits)

    def test_bunts_are_fielded_in_front_of_the_plate(self):
        self.assertTrue(self.bunts)
        self.assertLessEqual(set(self.bunts), {'P', 'C', '1B', '3B'})

    def test_pitchers_do_not_catch_pop_ups(self):
        """Real: no air out caught by a pitcher in 24 games."""
        self.assertLess(self.air_outs['P'] / sum(self.air_outs.values()), 0.015)

    def test_double_plays_start_in_the_middle_infield(self):
        """Real: short and second start about two in three; it was one in three."""
        total = sum(self.double_plays.values())
        self.assertGreater((self.double_plays['SS'] + self.double_plays['2B']) / total, 0.45)
        self.assertLess((self.double_plays['P'] + self.double_plays['1B']) / total, 0.28)
        self.assertTrue(1.1 <= total / len(self.games) <= 2.0, total / len(self.games))


class TestNarrationOfSimulatedGames(SimulationBatch):
    def test_automatic_runner_is_announced_every_extra_half_inning(self):
        """The feed lists only runners who move, so when the first batter of
        an extra inning struck out the runner on second went unannounced."""
        checked = 0
        for seed, plays in self.all_plays.items():
            halves = {(p['about']['inning'], p['about']['isTopInning']) for p in plays if p['about']['inning'] >= 10}
            if not halves or checked >= 12:
                continue
            text = NarrativeRenderer(self.games[seed], seed=seed).render()
            self.assertEqual(text.count('Automatic runner on second'), len(halves), f"seed {seed}")
            checked += 1
        self.assertGreater(checked, 3)

    def test_batter_intros_name_the_player_not_the_place(self):
        for seed in list(SEEDS)[:25]:
            text = NarrativeRenderer(self.games[seed], seed=seed).render()
            self.assertNotRegex(text, r"for (first|second|third) base [A-Z]|for (left|center|right) field [A-Z]")
            self.assertNotRegex(text, r"playing \w+ (baseman|fielder)")


class TestPitchArsenals(SimulationBatch):
    """Real, distinct pitch types thrown in a game: starters 4-6 (mean 5.0),
    relievers 2-4 (mean 3.5), 5 or more from a reliever one time in six."""

    def test_arsenal_sizes_by_role(self):
        starters, relievers = [], []
        for plays in self.all_plays.values():
            for top in (True, False):
                _, stints = pitcher_stints(plays, top)
                for n, (_, stint, _) in enumerate(stints):
                    (relievers if n else starters).append(len(pitch_types(stint)))
        self.assertTrue(4.2 <= statistics.mean(starters) <= 5.8, statistics.mean(starters))
        self.assertLessEqual(max(starters), 7)
        self.assertTrue(2.6 <= statistics.mean(relievers) <= 3.9, statistics.mean(relievers))
        self.assertLess(sum(n >= 5 for n in relievers) / len(relievers), 0.2)
        self.assertLessEqual(max(relievers), 6)

    def test_rosters_carry_a_real_bullpen(self):
        for key in ("BAY_BOMBERS", "PC_PILOTS"):
            pitchers = [p for p in TEAMS[key]['players'] if p['position']['abbreviation'] == 'P']
            relievers = [p for p in pitchers if p['type'] != 'Starter']
            self.assertGreaterEqual(len(relievers), 7)
            self.assertEqual(sum(p['type'] == 'Closer' for p in relievers), 1)
            for pitcher in relievers:
                self.assertLessEqual(len(pitcher['pitch_arsenal']), 4, pitcher['legal_name'])
            for pitcher in pitchers:
                self.assertAlmostEqual(sum(v['prob'] for v in pitcher['pitch_arsenal'].values()), 1.0, places=6,
                                       msg=pitcher['legal_name'])


if __name__ == "__main__":
    unittest.main()


class TestLeftoverTells(SimulationBatch):
    """Small things a reader of several simulated games notices."""

    def test_linescore_has_no_inning_that_was_not_played(self):
        """A visitors' win in nine left a 0-0 tenth in the linescore."""
        visitors_in_nine = 0
        for seed, data in self.games.items():
            played = max(p['about']['inning'] for p in self.all_plays[seed])
            innings = data['liveData']['linescore']['innings']
            self.assertEqual([i['num'] for i in innings], list(range(1, played + 1)), f"seed {seed}")
            final = self.all_plays[seed][-1]['result']
            visitors_in_nine += played == 9 and final['awayScore'] > final['homeScore']
        self.assertGreater(visitors_in_nine, 20)

    def test_steals_name_their_runner(self):
        steals = 0
        for seed, plays in self.all_plays.items():
            for play in plays:
                for event in play['playEvents']:
                    details = event.get('details', {})
                    if details.get('eventType') not in ('stolen_base', 'caught_stealing'):
                        continue
                    steals += 1
                    (movement,) = details['runners']
                    self.assertTrue(movement['runner']['fullName'] and movement['runner']['id'])
                    self.assertEqual(movement['isOut'], details['eventType'] == 'caught_stealing')
                    self.assertEqual(int(movement['toBase'][0]), int(movement['fromBase'][0]) + 1)
                    if movement['isOut']:
                        self.assertEqual(movement['throw'], 'in_time')
                    else:
                        self.assertIn(movement['throw'], ('not_in_time', 'none'))
                    self.assertIsInstance(movement['slide'], bool)
        self.assertGreater(steals, 200)

    def test_automatic_runner_caught_stealing_is_announced_by_name(self):
        """Caught stealing third before the inning's first play ends: no
        other record of the play names him."""
        from baseball import BaseballSimulator
        game = BaseballSimulator(TEAMS["BAY_BOMBERS"], TEAMS["PC_PILOTS"], game_seed=9000)
        game.play_game()
        data = game.gameday_data
        play = next(p for p in data['liveData']['plays']['allPlays'] if p['about']['isTopInning'])
        runner = play['matchup']['batter']
        play = {**play, 'about': {**play['about'], 'inning': 10, 'isTopInning': True},
                'matchup': {k: v for k, v in play['matchup'].items() if not k.startswith('postOn')},
                'runners': [r for r in play['runners'] if r['movement'].get('start') != '2B']}
        play['matchup']['splits'] = {'menOnBase': 'RISP'}
        pitch = next(e for e in play['playEvents'] if e.get('isPitch'))
        steal = {'isPitch': False, 'index': 99, 'count': dict(pitch['count']),
                 'details': {'description': 'Caught Stealing 3B', 'code': 'X', 'eventType': 'caught_stealing',
                             'runners': [game._steal_movement({'id': 1, 'legal_name': 'Otis Runner'}, 3, True)]}}
        play['playEvents'] = [pitch, steal] + [e for e in play['playEvents'] if e is not pitch]
        data = {**data, 'liveData': {**data['liveData'], 'plays': {'allPlays': [play]}}}
        text = NarrativeRenderer(data, seed=1).render()
        self.assertIn('Automatic runner on second: Otis Runner jogs out to take his lead.', text)
        self.assertNotIn('Automatic runner on second to start the inning.', text)
        self.assertIn('Otis Runner is caught stealing third.', text)

    def test_head_into_the_next_inning_only_after_a_full_inning(self):
        """"And as we head into the fifth" was said after three and a half,
        and again in the sign-off ("As we go into the fifth inning")."""
        said = 0
        ordinals = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', '10th',
                    '11th', '12th', '13th', '14th', '15th']
        for seed in list(self.games)[:60]:
            renderer = NarrativeRenderer(self.games[seed], seed=seed)
            lines = renderer.render().split('\n')
            for index, play in enumerate(self.all_plays[seed]):
                low, high = renderer._play_line_map[index]
                for line in lines[low:high]:
                    match = re.search(r'as we head into the (?!stretch)(\w+),', line)
                    if not match:
                        continue
                    said += 1
                    # The break it closes is the one before the top of that inning.
                    self.assertTrue(play['about']['isTopInning'], f"seed {seed}: {line}")
                    self.assertEqual(match.group(1), ordinals[play['about']['inning'] - 1], f"seed {seed}: {line}")
                    self.assertNotIn('As we go into', line, f"seed {seed}")
        self.assertGreater(said, 10)

    def test_a_pitching_change_is_spoken_once_before_the_new_man_pitches(self):
        changes = 0
        for seed in list(self.games)[:40]:
            data = self.games[seed]
            renderer = NarrativeRenderer(data, seed=seed)
            text = renderer.render()
            self.assertNotIn('Pitching Change', text)
            self.assertNotRegex(text, r'\breplaces\b')
            lines = text.split('\n')
            current = {}
            for index, play in enumerate(self.all_plays[seed]):
                pitcher, top = play['matchup']['pitcher'], play['about']['isTopInning']
                if top in current and current[top] != pitcher['id']:
                    changes += 1
                    low, high = renderer._play_line_map[index]
                    block = [l for l in lines[low:high] if not l.startswith('[TTS')]
                    intro = '\n'.join(block).split('...')[0]
                    described = len(re.findall(rf"(?i)(?:reliever|relief pitcher|closer|starting pitcher),? "
                                               rf"{re.escape(pitcher['fullName'])}|{re.escape(pitcher['fullName'])} "
                                               rf"(?:will take the mound|is the new)|that is {re.escape(pitcher['fullName'])}",
                                               intro))
                    self.assertEqual(described, 1, f"seed {seed} play {index}: {intro}")
                current[top] = pitcher['id']
        self.assertGreater(changes, 100)

    def test_closer_is_called_one_only_when_he_is(self):
        data = self.games[9000]
        roles = {p['fullName']: p.get('pitcherRole') for p in data['gameData']['players'].values()
                 if p['primaryPosition']['abbreviation'] == 'P'}
        self.assertEqual(roles['Victor Stone'], 'closer')
        self.assertEqual(roles['Joe Gibson'], 'starter')
        self.assertEqual(roles['Colin Miller'], 'reliever')
        for seed in list(self.games)[:40]:
            text = NarrativeRenderer(self.games[seed], seed=seed).render()
            for name in re.findall(r'closer,? ([A-Z]\w+ [A-Z]\w+)', text):
                self.assertEqual(roles.get(name), 'closer', f"seed {seed}: {name}")

    def test_decisions_name_pitchers_of_the_right_teams(self):
        saves = 0
        for seed, data in self.games.items():
            plays = self.all_plays[seed]
            final = plays[-1]['result']
            home_won = final['homeScore'] > final['awayScore']
            decisions = data['liveData']['decisions']
            winners = {p['matchup']['pitcher']['id'] for p in plays if p['about']['isTopInning'] == home_won}
            losers = {p['matchup']['pitcher']['id'] for p in plays if p['about']['isTopInning'] != home_won}
            self.assertIn(decisions['winner']['id'], winners)
            self.assertIn(decisions['loser']['id'], losers)
            if 'save' in decisions:
                saves += 1
                self.assertIn(decisions['save']['id'], winners)
                self.assertNotEqual(decisions['save']['id'], decisions['winner']['id'])
                self.assertEqual(decisions['save']['id'],
                                 [p for p in plays if p['about']['isTopInning'] == home_won][-1]['matchup']['pitcher']['id'])
        # Real: a save in roughly half of all games.
        self.assertTrue(0.25 <= saves / len(self.games) <= 0.7, saves / len(self.games))
