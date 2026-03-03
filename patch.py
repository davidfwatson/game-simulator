import re

with open('renderers/narrative/renderer.py', 'r') as f:
    content = f.read()

# Replace _get_runner_status_string implementation
content = re.sub(
    r'def _get_runner_status_string\(self, outcome, batter_name, result_outs, is_leadoff, inning_context\):\n\s+from \.play_description import get_runner_status_string as grss\n\s+key = None.*?return self\._get_narrative_string\(key, context, rng=self\.rng_play\)',
    'def _get_runner_status_string(self, outcome, batter_name, result_outs, is_leadoff, inning_context):\n        from .play_description import get_runner_status_string as grss\n        return grss(outcome, batter_name, result_outs, is_leadoff, inning_context, self.rng_play)',
    content,
    flags=re.DOTALL
)

with open('renderers/narrative/renderer.py', 'w') as f:
    f.write(content)
