import unittest
import json
import re
import os
from renderers.narrative.renderer import NarrativeRenderer

class TestExample3Similarity(unittest.TestCase):
    def fuzzy_match(self, line, lines):
        line = re.sub(r'\[TTS SPLIT HERE DELAY:[0-9\.]+s\]', '', line).strip()
        if not line: return False

        for o in lines:
            o_clean = re.sub(r'\[TTS SPLIT HERE DELAY:[0-9\.]+s\]', '', o).strip()
            if not o_clean: continue
            # Just do a simplistic substring match
            if len(line) > 10 and line in o_clean:
                return True
            if len(o_clean) > 10 and o_clean in line:
                return True
        return False

    def test_example_3_similarity(self):
        # Load the draft JSON
        with open(os.path.join(os.path.dirname(__file__), 'pbp_example_3_draft.json'), 'r') as f:
            data = json.load(f)

        renderer = NarrativeRenderer(data)
        generated_output = renderer.render()
        generated_lines = [l.strip() for l in generated_output.split('\n') if l.strip()]

        # Load the original text
        with open(os.path.join(os.path.dirname(__file__), 'pbp_example_3.txt'), 'r') as f:
            original_text = f.read()
        original_lines = [l.strip() for l in original_text.split('\n') if l.strip()]

        matches = 0
        for gl in generated_lines:
            if self.fuzzy_match(gl, original_lines):
                matches += 1

        # Assert a minimum percentage of identical/similar lines (e.g., 5%)
        percentage = matches / len(generated_lines) if generated_lines else 0.0
        self.assertGreaterEqual(percentage, 0.05, f"Similarity should be greater than 5%, was {percentage*100:.1f}%")

if __name__ == '__main__':
    unittest.main()
