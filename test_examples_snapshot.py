import unittest
from pathlib import Path
import subprocess
import re


def normalize_line(line):
    """Normalize trivial formatting differences for line comparison.

    Regularizes:
    - Count format: "oh and one" <-> "oh-one", "one and oh" <-> "one-oh", etc.
    - Capitalization after punctuation (". Fouled" vs ", fouled")
    - Count separators: ". oh and two" vs ", oh and two"
    - Trailing/leading whitespace
    """
    s = line.strip().lower()
    # Normalize count formats: "oh and one" -> "oh-one", etc.
    count_words = {'oh': '0', 'one': '1', 'two': '2', 'three': '3'}
    for w1, _ in count_words.items():
        for w2, _ in count_words.items():
            s = s.replace(f'{w1} and {w2}', f'{w1}-{w2}')
    # Normalize punctuation before counts: ". oh-" or ", oh-" -> ", oh-"
    s = re.sub(r'[.,]\s+(\w+-\w+)', r', \1', s)
    # Normalize "called a strike" vs "called strike"
    s = s.replace('called a strike', 'called strike')
    # Normalize comma vs period+space before lowercase
    s = re.sub(r'\.\s+([a-z])', r', \1', s)
    return s


def _line_similarity(a, b):
    """Word-level Jaccard between two lines (normalized)."""
    wa = set(re.findall(r'\b\w+\b', normalize_line(a)))
    wb = set(re.findall(r'\b\w+\b', normalize_line(b)))
    if not wa and not wb:
        return 1.0
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def positional_line_match(target_text, rendered_text, wiggle_pct=0.08, wiggle_min=5):
    """Positional fuzzy line matching.

    For each target line at proportional position y%, looks for a match
    within y ± wiggle_pct of the rendered file. Returns (exact, near90,
    near75, n_target).
    """
    target_lines = [l for l in target_text.split('\n') if l.strip()]
    rendered_lines = [l for l in rendered_text.split('\n') if l.strip()]
    target_norm = [normalize_line(l) for l in target_lines]
    rendered_norm = [normalize_line(l) for l in rendered_lines]
    n_target = len(target_lines)
    n_rendered = len(rendered_lines)

    exact = 0
    near90 = 0
    near75 = 0
    used = set()

    for ti, tline in enumerate(target_lines):
        if not tline:
            continue
        prop = ti / n_target if n_target > 0 else 0
        center = int(prop * n_rendered)
        wiggle = max(wiggle_min, int(wiggle_pct * n_rendered))
        lo = max(0, center - wiggle)
        hi = min(n_rendered, center + wiggle + 1)

        best_sim = 0.0
        best_ri = -1
        tn = target_norm[ti]
        for ri in range(lo, hi):
            if ri in used:
                continue
            if rendered_norm[ri] == tn:
                best_sim = 1.0
                best_ri = ri
                break
            sim = _line_similarity(tline, rendered_lines[ri])
            if sim > best_sim:
                best_sim = sim
                best_ri = ri

        if best_sim == 1.0:
            exact += 1
            used.add(best_ri)
        elif best_sim >= 0.9:
            near90 += 1
            used.add(best_ri)
        elif best_sim >= 0.75:
            near75 += 1
            used.add(best_ri)

    return exact, near90, near75, n_target


def positional_line_match_content(target_text, rendered_text, wiggle_pct=0.08, wiggle_min=5):
    """Like positional_line_match but excludes TTS delay markers."""
    def strip_tts(text):
        return '\n'.join(l for l in text.split('\n') if not l.strip().startswith('[TTS SPLIT'))
    return positional_line_match(strip_tts(target_text), strip_tts(rendered_text), wiggle_pct, wiggle_min)


class TestExampleSnapshots(unittest.TestCase):

    def _get_example_logs(self):
        """Helper to read all example logs."""
        logs = {}
        examples_dir = Path(__file__).parent / "examples"
        for i in range(1, 11):
            example_file = examples_dir / f"game_{i:02d}.txt"
            with open(example_file, 'r') as f:
                logs[example_file.name] = f.read()
        return logs

    def test_examples_match_rendered_output(self):
        # Path to the directory containing example game logs
        examples_dir = Path(__file__).parent / "examples"

        # Iterate over each example game log
        for i in range(1, 11):
            example_file = examples_dir / f"game_{i:02d}.txt"
            with open(example_file, 'r') as f:
                snapshot = f.read()

            # Re-run the simulation with the same seed
            # The seed is the file number (e.g., 1 for game_01.txt)
            process = subprocess.run(
                ['python3', 'example_games.py', str(i)],
                capture_output=True,
                text=True,
                check=True
            )
            rendered_output = process.stdout

            # Compare the snapshot with the fresh output
            self.assertEqual(
                snapshot,
                rendered_output,
                f"Example log {example_file} is out of date; "
                "rerun python update_examples.py."
            )

    def test_no_contradictory_takes_and_hits_phrasing(self):
        example_logs = self._get_example_logs()
        batted_ball_results = ["Result: Groundout", "Result: Flyout", "Result: Single", "Result: Double", "Result: Triple", "Result: Home Run", "(", "lines out", "grounds out"]
        for filename, content in example_logs.items():
            with self.subTest(file=filename):
                for line in content.splitlines():
                    if "takes the" in line:
                        self.assertFalse(any(res in line for res in batted_ball_results), f"Contradictory 'takes the' on a batted ball: {line}")

    def test_no_redundant_batter_name_in_play_by_play(self):
        example_logs = self._get_example_logs()
        for filename, content in example_logs.items():
            with self.subTest(file=filename):
                for line in content.splitlines():
                    # Find lines that start with a batter's name
                    match = re.match(r"^\s*([A-Z][a-z]+(?: '[A-Z][a-z]+')? [A-Z][a-z]+) steps to the plate", line)
                    if not match:
                        continue

                    batter_name = match.group(1)
                    # Check the subsequent play-by-play lines for this at-bat
                    ab_lines = content.split(line)[1].split(" | ")[0]
                    for ab_line in ab_lines.splitlines():
                        if batter_name in ab_line:
                            # Check if the name appears more than once, ignoring the initial mention if it exists
                            self.assertEqual(ab_line.count(batter_name), 1, f"Redundant batter name found in line: '{ab_line}'")

    def test_no_clunky_strikeout_results(self):
        example_logs = self._get_example_logs()
        narrative_strikeout_phrases = ["down on strikes", "caught looking", "goes down swinging", "watches strike three go by", "frozen on a pitch"]
        for filename, content in example_logs.items():
            with self.subTest(file=filename):
                for line in content.splitlines():
                    if any(phrase in line for phrase in narrative_strikeout_phrases):
                        self.assertNotIn("Result: Strikeout", line, f"Clunky strikeout result found: {line}")

    def test_no_double_foul_in_commentary(self):
        example_logs = self._get_example_logs()
        for filename, content in example_logs.items():
            with self.subTest(file=filename):
                for line in content.splitlines():
                    foul_mentions = re.findall(r'foul', line, re.IGNORECASE)
                    self.assertLessEqual(len(foul_mentions), 1, f"Double 'foul' mention found: {line}")



    def _assert_pbp_alignment(self, target_file, fixture_file, jaccard_min, ngram_min, line_exact_min,
                              target_skip=0, rendered_skip=0):
        """Shared alignment assertion for PBP examples.

        target_skip / rendered_skip: number of lines to skip from the start
        of each file (to exclude pregame chatter from comparison).
        """
        import json
        from renderers.narrative.renderer import NarrativeRenderer

        with open(target_file, 'r') as f:
            text = '\n'.join(f.read().splitlines()[target_skip:])

        with open(fixture_file, 'r') as f:
            data = json.load(f)

        renderer = NarrativeRenderer(data)
        rendered = '\n'.join(renderer.render().splitlines()[rendered_skip:])

        def get_words(s):
            return set(re.findall(r'\b\w+\b', s.lower()))

        text_words = get_words(text)
        rendered_words = get_words(rendered)

        intersection = text_words.intersection(rendered_words)
        union = text_words.union(rendered_words)
        jaccard = len(intersection) / len(union) if union else 0

        self.assertGreaterEqual(
            jaccard, jaccard_min,
            f"Jaccard similarity of words ({jaccard*100:.2f}%) is below the {jaccard_min*100:.0f}% threshold."
        )

        def get_ngrams(s, n=5):
            words = re.findall(r'\b\w+\b', s.lower())
            return set(tuple(words[i:i+n]) for i in range(len(words)-n+1))

        text_ngrams = get_ngrams(text)
        rendered_ngrams = get_ngrams(rendered)

        intersection_ngrams = text_ngrams.intersection(rendered_ngrams)
        ngram_percentage = len(intersection_ngrams) / len(text_ngrams) if text_ngrams else 0

        self.assertGreaterEqual(
            ngram_percentage, ngram_min,
            f"5-gram match percentage ({ngram_percentage*100:.2f}%) is below the {ngram_min*100:.0f}% threshold."
        )

        exact, near90, near75, n_target = positional_line_match(text, rendered)
        exact_pct = exact / n_target if n_target else 0

        self.assertGreaterEqual(
            exact_pct, line_exact_min,
            f"Positional exact line match ({exact_pct*100:.1f}%) is below the {line_exact_min*100:.0f}% threshold."
        )

    def test_pbp_example_3_match_percentage(self):
        """Asserts that the output of test_fixture_pbp_example_3.json meets a minimum threshold of match with pbp_example_3.txt."""
        self._assert_pbp_alignment(
            'pbp_example_3.txt', 'test_fixture_pbp_example_3.json',
            jaccard_min=0.48, ngram_min=0.12, line_exact_min=0.40,
            target_skip=33, rendered_skip=30,
        )


    def test_pbp_example_3_draft_consistency(self):
        """Asserts that the current output of rendering test_fixture_pbp_example_3.json matches test_fixture_pbp_example_3.txt."""
        import json
        from renderers.narrative.renderer import NarrativeRenderer

        with open('test_fixture_pbp_example_3.json', 'r') as f:
            data = json.load(f)

        renderer = NarrativeRenderer(data)
        rendered = renderer.render()

        with open('test_fixture_pbp_example_3.txt', 'r') as f:
            expected = f.read()

        self.assertEqual(
            rendered, expected,
            "The rendered output of test_fixture_pbp_example_3.json does not match test_fixture_pbp_example_3.txt. Note: If you see this failure after modifying test_fixture_pbp_example_3.json, it simply means you need to regenerate test_fixture_pbp_example_3.txt (e.g. by running `python3 baseball.py --gameday-file test_fixture_pbp_example_3.json --pbp-outfile test_fixture_pbp_example_3.txt`)."
        )

    def test_pbp_example_1_match_percentage(self):
        """Asserts that the output of test_fixture_pbp_example_1.json meets a minimum threshold of match with pbp_example_1.txt."""
        self._assert_pbp_alignment(
            'pbp_example_1.txt', 'test_fixture_pbp_example_1.json',
            jaccard_min=0.48, ngram_min=0.12, line_exact_min=0.40,
            target_skip=28, rendered_skip=30,
        )

    def test_pbp_example_1_draft_consistency(self):
        """Asserts that the current output of rendering test_fixture_pbp_example_1.json matches test_fixture_pbp_example_1.txt."""
        import json
        from renderers.narrative.renderer import NarrativeRenderer

        with open('test_fixture_pbp_example_1.json', 'r') as f:
            data = json.load(f)

        renderer = NarrativeRenderer(data)
        rendered = renderer.render()

        with open('test_fixture_pbp_example_1.txt', 'r') as f:
            expected = f.read()

        self.assertEqual(
            rendered, expected,
            "The rendered output of test_fixture_pbp_example_1.json does not match test_fixture_pbp_example_1.txt. Note: If you see this failure after modifying test_fixture_pbp_example_1.json, it simply means you need to regenerate test_fixture_pbp_example_1.txt (e.g. by running `python3 baseball.py --gameday-file test_fixture_pbp_example_1.json --pbp-outfile test_fixture_pbp_example_1.txt`)."
        )

    def test_pbp_example_2_match_percentage(self):
        """Asserts that the output of test_fixture_pbp_example_2.json meets a minimum threshold of match with pbp_example_2.txt."""
        self._assert_pbp_alignment(
            'pbp_example_2.txt', 'test_fixture_pbp_example_2.json',
            jaccard_min=0.48, ngram_min=0.12, line_exact_min=0.40,
            target_skip=35, rendered_skip=30,
        )

    def test_pbp_example_2_draft_consistency(self):
        """Asserts that the current output of rendering test_fixture_pbp_example_2.json matches test_fixture_pbp_example_2.txt."""
        import json
        from renderers.narrative.renderer import NarrativeRenderer

        with open('test_fixture_pbp_example_2.json', 'r') as f:
            data = json.load(f)

        renderer = NarrativeRenderer(data)
        rendered = renderer.render()

        with open('test_fixture_pbp_example_2.txt', 'r') as f:
            expected = f.read()

        self.assertEqual(
            rendered, expected,
            "The rendered output of test_fixture_pbp_example_2.json does not match test_fixture_pbp_example_2.txt. Note: If you see this failure after modifying test_fixture_pbp_example_2.json, it simply means you need to regenerate test_fixture_pbp_example_2.txt (e.g. by running `python3 baseball.py --gameday-file test_fixture_pbp_example_2.json --pbp-outfile test_fixture_pbp_example_2.txt`)."
        )

    def test_pbp_example_4_match_percentage(self):
        """Asserts that the output of test_fixture_pbp_example_4.json meets a minimum threshold of match with pbp_example_4.txt."""
        self._assert_pbp_alignment(
            'pbp_example_4.txt', 'test_fixture_pbp_example_4.json',
            jaccard_min=0.48, ngram_min=0.12, line_exact_min=0.40,
            target_skip=27, rendered_skip=30,
        )

    def test_pbp_example_4_draft_consistency(self):
        """Asserts that the current output of rendering test_fixture_pbp_example_4.json matches test_fixture_pbp_example_4.txt."""
        import json
        from renderers.narrative.renderer import NarrativeRenderer

        with open('test_fixture_pbp_example_4.json', 'r') as f:
            data = json.load(f)

        renderer = NarrativeRenderer(data)
        rendered = renderer.render()

        with open('test_fixture_pbp_example_4.txt', 'r') as f:
            expected = f.read()

        self.assertEqual(
            rendered, expected,
            "The rendered output of test_fixture_pbp_example_4.json does not match test_fixture_pbp_example_4.txt. Note: If you see this failure after modifying test_fixture_pbp_example_4.json, it simply means you need to regenerate test_fixture_pbp_example_4.txt (e.g. by running `python3 baseball.py --gameday-file test_fixture_pbp_example_4.json --pbp-outfile test_fixture_pbp_example_4.txt`)."
        )

if __name__ == "__main__":
    unittest.main()
