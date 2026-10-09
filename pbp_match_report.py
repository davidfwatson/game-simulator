#!/usr/bin/env python3
"""Report PBP alignment using the same catalog and metrics as the tests."""

import argparse
from dataclasses import asdict
import json

from pbp_comparison import check_transcript_examples, compare_example, discover_pbp_examples, render_example
from sleep_baseball_corpus import LIMITATIONS, check_corpus, measure_corpus, report_corpus


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("examples", type=int, nargs="*", help="Example numbers (default: all)")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable scores")
    parser.add_argument("--check", action="store_true", help="Fail if any comparison minimum is missed")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument('--corpus-only', action='store_true',
                       help='show automatic phrase-component support across all 21 source games')
    scope.add_argument('--alignment-only', action='store_true',
                       help='show only the original PBP fixture comparisons')
    parser.add_argument('--uncovered-limit', type=int, default=3,
                        help='uncovered component clauses per source; -1 shows all')
    args = parser.parse_args(argv)
    if args.corpus_only:
        if args.examples:
            parser.error('--corpus-only does not accept PBP example numbers')
        reports = (measure_corpus() if args.json else report_corpus(
            uncovered_limit=None if args.uncovered_limit < 0 else args.uncovered_limit))
        failures = check_corpus(reports)
        if args.json:
            print(json.dumps({'scope': 'phrase-component support', 'limitations': LIMITATIONS,
                              'sources': [asdict(r) for r in reports], 'failures': failures}, indent=2))
        else:
            for failure in failures:
                print('  BELOW MINIMUM: ' + failure)
        return int(args.check and bool(failures))
    try:
        examples = discover_pbp_examples()
    except ValueError as error:
        parser.error(str(error))
    if unknown := set(args.examples) - {example.number for example in examples}:
        parser.error("Unknown PBP examples: " + ", ".join(map(str, sorted(unknown))))

    results = []
    for example in examples:
        if args.examples and example.number not in args.examples:
            continue
        scores = compare_example(example, render_example(example))
        failures = scores.failures(example)
        results.append({
            "example": asdict(example),
            "target_file": example.target_file,
            "jaccard": scores.jaccard,
            "ngram": scores.ngram,
            "all_lines": scores.all_lines._asdict(),
            "content_lines": scores.content_lines._asdict(),
            "failures": failures,
        })
        if not args.json:
            print(f"{example.target_file}:")
            print(f"  Jaccard:              {scores.jaccard:.1%}")
            print(f"  5-gram:               {scores.ngram:.1%}")
            for label, match in (("all", scores.all_lines), ("content", scores.content_lines)):
                print(f"  Line exact ({label}):".ljust(24)
                      + f"{match.exact_fraction:.1%} ({match.exact}/{match.total})")
            for failure in failures:
                print(f"  BELOW MINIMUM: {failure}")
            print()
    if not args.examples and not args.alignment_only:
        try:
            counts = check_transcript_examples()
        except ValueError as error:
            parser.error(str(error))
        for episode, count in counts.items():
            results.append({'transcript_episode': episode, 'passing_cases': count, 'failures': []})
        if not args.json:
            print(f'Transcripts: all {sum(counts.values())} source-linked cases pass across {len(counts)} episodes.')
        from full_transcript_comparison import check_full_transcripts
        try:
            full_games = check_full_transcripts()
        except ValueError as error:
            parser.error(str(error))
        for game in full_games:
            results.append({key: value for key, value in game.items() if key != 'plays'})
            if not args.json:
                print(f"episode_{game['episode']:03d}: {game['appearances']} appearances, {game['pitches']} pitches; "
                      f"5-gram recall {game['ngram']:.1%}, ordered words per play {game['mean_play_word_coverage']:.1%}")
                for failure in game['failures']:
                    print('  BELOW MINIMUM: ' + failure)
        reports = (measure_corpus() if args.json else report_corpus(
            uncovered_limit=None if args.uncovered_limit < 0 else args.uncovered_limit))
        component_failures = check_corpus(reports)
        for report in reports:
            results.append({'phrase_component_source': report.source_file,
                            **asdict(report), 'failures': []})
        results.append({'phrase_component_catalog': True, 'limitations': LIMITATIONS,
                        'failures': component_failures})
        if not args.json:
            for failure in component_failures:
                print('  BELOW MINIMUM: ' + failure)
    if args.json:
        print(json.dumps(results, indent=2))
    return int(args.check and any(result["failures"] for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
