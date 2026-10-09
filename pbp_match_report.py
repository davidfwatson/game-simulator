#!/usr/bin/env python3
"""Report all Sleep Baseball phrase coverage and fixture alignment."""

import argparse
import json
from pathlib import Path

from pbp_alignment import alignment_metrics
from renderers.narrative.renderer import NarrativeRenderer
from sleep_baseball_corpus import report_corpus

EXAMPLES = [
    ('pbp_example_1.txt', 'test_fixture_pbp_example_1.json', 28, 30),
    ('pbp_example_2.txt', 'test_fixture_pbp_example_2.json', 35, 30),
    ('pbp_example_3.txt', 'test_fixture_pbp_example_3.json', 33, 30),
    ('pbp_example_4.txt', 'test_fixture_pbp_example_4.json', 27, 30),
]


def report(target_file, fixture_file, target_skip, rendered_skip):
    root = Path(__file__).resolve().parent
    with open(root / target_file) as f:
        text = '\n'.join(f.read().splitlines()[target_skip:])
    with open(root / fixture_file) as f:
        data = json.load(f)

    renderer = NarrativeRenderer(data)
    rendered = '\n'.join(renderer.render().splitlines()[rendered_skip:])

    content = alignment_metrics(text, rendered)
    all_lines = alignment_metrics(text, rendered, content_only=False)

    print(f'{target_file}:')
    print(f'  Jaccard (content):    {content.word_jaccard*100:.1f}%')
    print(f'  5-gram (content):     {content.ngram_coverage*100:.1f}%')
    print(f'  Line exact (content): {content.exact_fraction*100:.1f}% ({content.exact}/{content.target_lines})')
    print(f'  Jaccard (all):        {all_lines.word_jaccard*100:.1f}%')
    print(f'  5-gram (all):         {all_lines.ngram_coverage*100:.1f}%')
    print(f'  Line exact (all):     {all_lines.exact_fraction*100:.1f}% ({all_lines.exact}/{all_lines.target_lines})')
    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument('--alignment-only', action='store_true',
                       help='show only the four full-game fixture comparisons')
    scope.add_argument('--corpus-only', action='store_true',
                       help='show phrase-component support across all source games')
    parser.add_argument('--uncovered-limit', type=int, default=3,
                        help='uncovered phrases per source to show; -1 shows all')
    args = parser.parse_args()
    if not args.corpus_only:
        print('Full-game fixture alignment (four games):\n')
        for ex in EXAMPLES:
            report(*ex)
    if not args.alignment_only:
        report_corpus(uncovered_limit=None if args.uncovered_limit < 0 else args.uncovered_limit)


if __name__ == '__main__':
    main()
