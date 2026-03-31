#!/usr/bin/env python3
"""Report match percentages for all PBP examples (skipping pregame chatter)."""

import re
import json
import sys

sys.path.insert(0, '.')
from test_examples_snapshot import positional_line_match, positional_line_match_content
from renderers.narrative.renderer import NarrativeRenderer

EXAMPLES = [
    ('pbp_example_1.txt', 'test_fixture_pbp_example_1.json', 28, 30),
    ('pbp_example_2.txt', 'test_fixture_pbp_example_2.json', 35, 30),
    ('pbp_example_3.txt', 'test_fixture_pbp_example_3.json', 33, 30),
    ('pbp_example_4.txt', 'test_fixture_pbp_example_4.json', 27, 30),
]


def get_ngrams(s, n=5):
    words = re.findall(r'\b\w+\b', s.lower())
    return set(tuple(words[i:i+n]) for i in range(len(words) - n + 1))


def report(target_file, fixture_file, target_skip, rendered_skip):
    with open(target_file) as f:
        text = '\n'.join(f.read().splitlines()[target_skip:])
    with open(fixture_file) as f:
        data = json.load(f)

    renderer = NarrativeRenderer(data)
    rendered = '\n'.join(renderer.render().splitlines()[rendered_skip:])

    text_words = set(re.findall(r'\b\w+\b', text.lower()))
    rendered_words = set(re.findall(r'\b\w+\b', rendered.lower()))
    jaccard = len(text_words & rendered_words) / len(text_words | rendered_words) if text_words | rendered_words else 0

    t_ng = get_ngrams(text)
    r_ng = get_ngrams(rendered)
    ngram = len(t_ng & r_ng) / len(t_ng) if t_ng else 0

    exact, near90, near75, n_target = positional_line_match(text, rendered)
    exact_pct = exact / n_target if n_target else 0

    c_exact, c_near90, c_near75, c_n_target = positional_line_match_content(text, rendered)
    c_exact_pct = c_exact / c_n_target if c_n_target else 0

    print(f'{target_file}:')
    print(f'  Jaccard:              {jaccard*100:.1f}%')
    print(f'  5-gram:               {ngram*100:.1f}%')
    print(f'  Line exact (all):     {exact_pct*100:.1f}% ({exact}/{n_target})')
    print(f'  Line exact (content): {c_exact_pct*100:.1f}% ({c_exact}/{c_n_target})')
    print()


def main():
    for ex in EXAMPLES:
        report(*ex)


if __name__ == '__main__':
    main()
