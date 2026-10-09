#!/usr/bin/env python3
"""Compile reviewed transcript case specs into production draw fixtures/snapshots."""

import argparse
import json
from pathlib import Path
from pbp_comparison import validate_transcript_counts

from transcript_comparison import (
    FIXTURE_DIR, SOURCE_DIR, SPEC_DIR, check_catalog, compile_episode,
    episode_stem, load_specs, snapshot_text,
)


def update_examples(source_dir=SOURCE_DIR, spec_dir=SPEC_DIR, fixture_dir=FIXTURE_DIR):
    # Compile everything before writing so a bad case never leaves half a corpus
    # regenerated. Old extra files are reported by check_catalog, never deleted.
    compiled = [compile_episode(spec, source) for spec, source in load_specs(source_dir, spec_dir)]
    outputs = [(fixture, snapshot_text(fixture)) for fixture in compiled]
    fixture_dir = Path(fixture_dir)
    fixture_dir.mkdir(parents=True, exist_ok=True)
    for fixture, text in outputs:
        stem = episode_stem(fixture['episode'])
        (fixture_dir / f'{stem}.json').write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + '\n')
        (fixture_dir / f'{stem}.txt').write_text(text)
    return check_catalog(source_dir, spec_dir, fixture_dir)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify existing replay fixtures without rewriting')
    args = parser.parse_args()
    try:
        counts = check_catalog() if args.check else update_examples()
        validate_transcript_counts(counts)
    except ValueError as error:
        parser.error(str(error))
    print(f'{"Verified" if args.check else "Updated"} {len(counts)} episodes, '
          f'{sum(counts.values())} representative situation cases')


if __name__ == '__main__':
    main()
