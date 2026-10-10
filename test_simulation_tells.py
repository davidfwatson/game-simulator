"""Simulation behaviour that gave simulated games away to blind judges, held
to bands around what 24 real 2026 StatsAPI feeds show.

One fixed batch of games (seeds 9000+) is simulated once and every test
measures it, so the bands are deterministic.
"""
import collections
import re
import statistics
import unittest

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


if __name__ == "__main__":
    unittest.main()
