"""The missed-word census classifies clauses and accounts for every word."""
import unittest

from missed_words import Unit, all_units, census, classify, summarize


def unit(index=3):
    return Unit('episode_049', index, '', '')


class ClassifyTest(unittest.TestCase):
    def test_missing_facts(self):
        for clause, kind in [
            ('lined into the gap in left field', 'hit_spot'),
            ('and that one will end up all the way in the corner', 'hit_spot'),
            ('Hard grounder to short', 'contact_quality'),
            ('Royce Babcock steps in to pinch-hit for Brocktune Shemper', 'substitution'),
            ('He enters tonight\'s game with a record of five and three', 'season_stats'),
        ]:
            self.assertEqual(classify(clause, unit()), ('missing_fact', kind), clause)

    def test_recorded_but_unsaid(self):
        self.assertEqual(classify('Nomo will score', unit()), ('unnarrated_fact', 'runner_scores'))
        self.assertEqual(classify("And that's a two-run homer for Steve McDykel", unit()),
                         ('unnarrated_fact', 'run_count'))

    def test_wording(self):
        self.assertEqual(classify('Swing and a miss on a low fastball', unit())[0], 'wording')
        self.assertEqual(classify('The Timbers do not score', unit())[0], 'wording')
        self.assertEqual(classify('Kosinski walked in the first', unit())[0], 'wording')
        # Pitch context is not a batted-ball spot.
        self.assertEqual(classify('Change-up paints the corner for a called strike two', unit())[0], 'wording')

    def test_pregame_lineups_are_wording(self):
        self.assertEqual(classify('Prudence Jefferson is in the cleanup spot this evening', unit('pregame')),
                         ('wording', 'pregame_postgame'))


class CensusTest(unittest.TestCase):
    def test_every_missed_word_is_classified(self):
        units = all_units({'episode_049'})
        misses = census(units)
        summary = summarize(misses, units)
        unmatched = sum(1 for u in units for token, ok in zip(u.tokens, u.matched)
                        if not ok and token[0] != '‖')
        self.assertEqual(summary['missed_words'], unmatched)
        self.assertEqual(sum(summary['by_cause'].values()), unmatched)
        self.assertGreater(summary['source_words'], 4000)


if __name__ == '__main__':
    unittest.main()
