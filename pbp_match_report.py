#!/usr/bin/env python3
"""Report PBP alignment using the same catalog and metrics as the tests."""

import argparse
from dataclasses import asdict
import json

from pbp_comparison import compare_example, discover_pbp_examples, render_example


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("examples", type=int, nargs="*", help="Example numbers (default: all)")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable scores")
    parser.add_argument("--check", action="store_true", help="Fail if any comparison minimum is missed")
    args = parser.parse_args(argv)
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
    if args.json:
        print(json.dumps(results, indent=2))
    return int(args.check and any(result["failures"] for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
