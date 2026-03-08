#!/usr/bin/env python3
"""
Tools for aligning PBP narrative output with target text (e.g., Sleep Baseball transcripts).

This module provides utilities for:
1. TRACING: See every RNG choice the renderer makes, organized by seed point
2. SOLVING: Compute a timestamp seed that produces desired template selections
3. SEARCHING: Find phrases in template pools, or identify missing ones
4. DIFFING: Line-by-line comparison of rendered output vs target text

## Key Concepts

The NarrativeRenderer uses DirectRNG in "directMode". Each timestamp encodes
per-stream seeds in its fractional seconds (8 digits):

    "2025-09-27T23:05:19.03050267" → play=67, pitch=02, flow=05, color=03

The fractional seconds are split into 2-digit segments, one per stream:
    digits 0-1 (rightmost) → rng_play
    digits 2-3             → rng_pitch
    digits 4-5             → rng_flow
    digits 6-7             → rng_color

Each stream independently consumes its seed via choice():
    choice(pool) → pool[seed % len(pool)]

Because streams are independent, setting one never conflicts with another.

Reseeds happen at:
    - play.startTime  → controls batter intro, matchup text
    - event.startTime → controls pitch descriptions, connectors
    - play.endTime    → controls outcome description, runner status

## Usage

    # Trace all RNG choices for play 0
    python pbp_tools.py trace test_fixture_pbp_example_3.json --play 0

    # Trace all plays (summary mode)
    python pbp_tools.py trace test_fixture_pbp_example_3.json

    # Search for a phrase across all template pools
    python pbp_tools.py search "misses a bit low"

    # Search only in a specific outcome's templates
    python pbp_tools.py search "Fly ball" --outcome Single

    # Solve for a seed that selects specific templates
    python pbp_tools.py solve --constraints '[{"flow": [10, 0], "color": [100, 19]}, {"pitch": [21, 15]}]'

    # Diff rendered output vs target
    python pbp_tools.py diff test_fixture_pbp_example_3.json pbp_example_3.txt

    # Diff a single play
    python pbp_tools.py diff test_fixture_pbp_example_3.json pbp_example_3.txt --play 0
"""

import json
import sys
import re
import argparse
from collections import defaultdict
from commentary import GAME_CONTEXT


# ===========================================================================
# TracingDirectRNG: Drop-in replacement that logs every call
# ===========================================================================

class TracingDirectRNG:
    """DirectRNG that logs every choice/random call for debugging."""

    def __init__(self, start_idx, name=""):
        self.idx = start_idx
        self.start_idx = start_idx
        self.name = name
        self.calls = []
        self.call_count = 0

    def choice(self, seq):
        if not seq:
            raise IndexError("Cannot choose from an empty sequence")
        digit_pos = self.call_count
        digit_value = self.idx % 100
        selected_index = self.idx % len(seq)
        val = seq[selected_index]

        self.calls.append({
            'type': 'choice',
            'digit_pos': digit_pos,
            'digit_value': digit_value,
            'pool_size': len(seq),
            'selected_index': selected_index,
            'selected_value': val if isinstance(val, str) else str(val),
            'pool': [s if isinstance(s, str) else str(s) for s in seq],
            'stream': self.name
        })

        self.idx = self.idx // 100
        self.call_count += 1
        return val

    def random(self):
        digit_pos = self.call_count
        digit_value = self.idx % 100
        val = digit_value / 100.0

        self.calls.append({
            'type': 'random',
            'digit_pos': digit_pos,
            'digit_value': digit_value,
            'result': val,
            'stream': self.name
        })

        self.idx = self.idx // 100
        self.call_count += 1
        return val

    def seed(self, *args, **kwargs):
        pass


# ===========================================================================
# TracingRenderer: NarrativeRenderer with instrumented RNG
# ===========================================================================

class TracingRenderer:
    """Wraps NarrativeRenderer to intercept all RNG calls and log them."""

    def __init__(self, gameday_data):
        # Import here to avoid circular imports
        from renderers.narrative.renderer import NarrativeRenderer

        self.gameday_data = gameday_data
        self.seed_log = []  # List of {timestamp, salt, seed, rngs: {name: TracingDirectRNG}}

        # Create the real renderer
        self.renderer = NarrativeRenderer(gameday_data)

        # Monkey-patch _reseed_from_timestamp
        original_reseed = self.renderer._reseed_from_timestamp

        def tracing_reseed(time_str, salt=""):
            parts = time_str.split('.')
            if len(parts) > 1:
                # Strip timezone: Z, +HH:MM, -HH:MM
                frac = parts[1]
                frac = re.sub(r'[Zz]$', '', frac)
                frac = re.sub(r'[+-]\d{2}:\d{2}$', '', frac)
                frac = re.sub(r'[+-]\d{2}$', '', frac)
                index = int(frac) if frac else 0
            else:
                index = 0

            # Split index into per-stream seeds (matching base.py)
            play = TracingDirectRNG(index % 100, 'play')
            pitch = TracingDirectRNG((index // 100) % 100, 'pitch')
            flow = TracingDirectRNG((index // 10000) % 100, 'flow')
            color = TracingDirectRNG((index // 1000000) % 100, 'color')

            self.renderer.rng_play = play
            self.renderer.rng_pitch = pitch
            self.renderer.rng_flow = flow
            self.renderer.rng_color = color
            self.renderer.rng = play

            self.seed_log.append({
                'timestamp': time_str,
                'salt': salt,
                'seed': index,
                'rngs': {'play': play, 'pitch': pitch, 'flow': flow, 'color': color}
            })

        self.renderer._reseed_from_timestamp = tracing_reseed

    def render(self):
        return self.renderer.render()


# ===========================================================================
# Seed Solver
# ===========================================================================

def solve_seed(constraints):
    """
    Compute a seed value that satisfies all constraints.

    With the split-stream encoding, each stream has its own independent 2-digit
    portion of the fractional seconds. No cross-stream conflicts are possible.

    Args:
        constraints: list of dicts, one per base-100 digit position.
            Each dict maps stream names to (pool_size, desired_index) tuples.

    Returns:
        (seed, success, conflicts)
    """
    seed = 0
    conflicts = []

    for digit_pos, digit_constraints in enumerate(constraints):
        found = False
        for candidate in range(100):
            if all(candidate % ps == di for ps, di in digit_constraints.values()):
                seed += candidate * (100 ** digit_pos)
                found = True
                break

        if not found:
            conflicts.append((digit_pos, dict(digit_constraints)))
            best = 0
            best_score = 0
            for candidate in range(100):
                score = sum(1 for ps, di in digit_constraints.values() if candidate % ps == di)
                if score > best_score:
                    best_score = score
                    best = candidate
            seed += best * (100 ** digit_pos)

    return seed, len(conflicts) == 0, conflicts


# Stream offsets in the fractional seconds (matching base.py split):
#   play  = index % 100           (digits 0-1, rightmost)
#   pitch = (index // 100) % 100  (digits 2-3)
#   flow  = (index // 10000) % 100 (digits 4-5)
#   color = (index // 1000000) % 100 (digits 6-7)
STREAM_OFFSETS = {
    'play':  (1, 100),        # multiplier to pack into fractional
    'pitch': (100, 100),
    'flow':  (10000, 100),
    'color': (1000000, 100),
}


def pack_stream_seeds(play=0, pitch=0, flow=0, color=0):
    """Pack per-stream seeds into a single fractional-seconds integer."""
    return (play % 100) + (pitch % 100) * 100 + (flow % 100) * 10000 + (color % 100) * 1000000


def unpack_stream_seeds(index):
    """Unpack a fractional-seconds integer into per-stream seeds."""
    return {
        'play':  index % 100,
        'pitch': (index // 100) % 100,
        'flow':  (index // 10000) % 100,
        'color': (index // 1000000) % 100,
    }


def seed_to_fractional(seed, base_timestamp="2025-09-27T23:05:00"):
    """Convert a packed seed to a timestamp with the seed encoded in fractional seconds."""
    return f"{base_timestamp}.{seed:08d}"


def timestamp_to_seed(timestamp):
    """Extract the full packed seed from a timestamp's fractional seconds."""
    parts = timestamp.split('.')
    if len(parts) > 1:
        digits_str = parts[1].replace('Z', '').replace('+', '').split('-')[0]
        return int(digits_str)
    return 0


# ===========================================================================
# Template Pool Search
# ===========================================================================

def search_all_pools(phrase, outcome=None):
    """
    Search all template pools for a phrase.

    Args:
        phrase: text to search for (case-insensitive substring match)
        outcome: optional, restrict to specific outcome type (e.g., "Single", "Groundout")

    Returns:
        list of dicts with pool, index, total, template
    """
    results = []

    # Search narrative_templates
    for out_type, categories in GAME_CONTEXT.get('narrative_templates', {}).items():
        if outcome and out_type != outcome:
            continue
        for cat, templates in categories.items():
            for idx, template in enumerate(templates):
                if phrase.lower() in template.lower():
                    results.append({
                        'pool': f'narrative_templates.{out_type}.{cat}',
                        'index': idx,
                        'total': len(templates),
                        'template': template
                    })

    # Search narrative_strings
    for key, strings in GAME_CONTEXT.get('narrative_strings', {}).items():
        if not isinstance(strings, list):
            continue
        for idx, s in enumerate(strings):
            if phrase.lower() in s.lower():
                results.append({
                    'pool': f'narrative_strings.{key}',
                    'index': idx,
                    'total': len(strings),
                    'template': s
                })

    # Search radio_strings
    for key, strings in GAME_CONTEXT.get('radio_strings', {}).items():
        if not isinstance(strings, list):
            continue
        for idx, s in enumerate(strings):
            if phrase.lower() in s.lower():
                results.append({
                    'pool': f'radio_strings.{key}',
                    'index': idx,
                    'total': len(strings),
                    'template': s
                })

    # Search pitch_locations
    for key, val in GAME_CONTEXT.get('pitch_locations', {}).items():
        if isinstance(val, dict):
            for subkey, strings in val.items():
                if not isinstance(strings, list):
                    continue
                for idx, s in enumerate(strings):
                    if phrase.lower() in s.lower():
                        results.append({
                            'pool': f'pitch_locations.{key}.{subkey}',
                            'index': idx,
                            'total': len(strings),
                            'template': s
                        })
        elif isinstance(val, list):
            for idx, s in enumerate(val):
                if phrase.lower() in s.lower():
                    results.append({
                        'pool': f'pitch_locations.{key}',
                        'index': idx,
                        'total': len(val),
                        'template': s
                    })

    # Search statcast_verbs
    for out_type, type_data in GAME_CONTEXT.get('statcast_verbs', {}).items():
        if outcome and out_type != outcome:
            continue
        for phrase_type, categories in type_data.items():
            if isinstance(categories, dict):
                for cat, strings in categories.items():
                    if not isinstance(strings, list):
                        continue
                    for idx, s in enumerate(strings):
                        if phrase.lower() in s.lower():
                            results.append({
                                'pool': f'statcast_verbs.{out_type}.{phrase_type}.{cat}',
                                'index': idx,
                                'total': len(strings),
                                'template': s
                            })
            elif isinstance(categories, list):
                for idx, s in enumerate(categories):
                    if phrase.lower() in s.lower():
                        results.append({
                            'pool': f'statcast_verbs.{out_type}.{phrase_type}',
                            'index': idx,
                            'total': len(categories),
                            'template': s
                        })

    # Search lineup_strings
    for key, strings in GAME_CONTEXT.get('lineup_strings', {}).items():
        if not isinstance(strings, list):
            continue
        for idx, s in enumerate(strings):
            if phrase.lower() in s.lower():
                results.append({
                    'pool': f'lineup_strings.{key}',
                    'index': idx,
                    'total': len(strings),
                    'template': s
                })

    return results


def list_pool(pool_path):
    """
    List all templates in a specific pool.

    Args:
        pool_path: dotted path like "narrative_templates.Single.default"
                   or "pitch_locations.ball.high_inside"

    Returns:
        list of (index, template) tuples
    """
    parts = pool_path.split('.')
    obj = GAME_CONTEXT

    for part in parts:
        if isinstance(obj, dict):
            obj = obj.get(part, {})
        else:
            return []

    if isinstance(obj, list):
        return list(enumerate(obj))
    return []


# ===========================================================================
# Diff Tool
# ===========================================================================

def diff_rendered_vs_target(rendered_text, target_text, context_lines=0):
    """
    Compare rendered output to target text line by line.

    Returns list of dicts with:
        - line_num: line number in target
        - target: target line
        - rendered: rendered line (if available)
        - match: True/False
        - type: 'match', 'mismatch', 'target_only', 'rendered_only'
    """
    target_lines = [l.strip() for l in target_text.split('\n')]
    rendered_lines = [l.strip() for l in rendered_text.split('\n')]

    results = []

    # Simple sequential comparison
    max_lines = max(len(target_lines), len(rendered_lines))
    for i in range(max_lines):
        t = target_lines[i] if i < len(target_lines) else None
        r = rendered_lines[i] if i < len(rendered_lines) else None

        if t == r:
            results.append({'line_num': i+1, 'target': t, 'rendered': r, 'match': True, 'type': 'match'})
        elif t is None:
            results.append({'line_num': i+1, 'target': None, 'rendered': r, 'match': False, 'type': 'rendered_only'})
        elif r is None:
            results.append({'line_num': i+1, 'target': t, 'rendered': None, 'match': False, 'type': 'target_only'})
        else:
            results.append({'line_num': i+1, 'target': t, 'rendered': r, 'match': False, 'type': 'mismatch'})

    return results


# ===========================================================================
# CLI
# ===========================================================================

def cmd_trace(args):
    """Trace RNG calls for a play or all plays."""
    with open(args.json_file) as f:
        data = json.load(f)

    tracer = TracingRenderer(data)
    rendered = tracer.render()

    plays = data['liveData']['plays']['allPlays']

    # Group seed_log entries by play context
    # Each seed_log entry has salt: "init", "play_start", "event", "play_outcome"
    print(f"Total seed points: {len(tracer.seed_log)}")
    print(f"Total plays: {len(plays)}")
    print()

    for entry in tracer.seed_log:
        salt = entry['salt']
        seed = entry['seed']
        ts = entry['timestamp']

        # Filter by play index if specified
        if args.play is not None and salt not in ('init',):
            # We need to figure out which play this seed point belongs to
            # For now, print all and let the user filter visually
            pass

        # Collect all calls across streams
        all_calls = []
        for stream_name, rng in entry['rngs'].items():
            for call in rng.calls:
                all_calls.append(call)

        if not all_calls and not args.verbose:
            continue

        print(f"{'='*70}")
        print(f"SEED POINT: salt={salt}, seed={seed}, timestamp={ts}")
        print(f"{'='*70}")

        for stream_name in ['flow', 'pitch', 'play', 'color']:
            rng = entry['rngs'][stream_name]
            if not rng.calls:
                continue

            for call in rng.calls:
                if call['type'] == 'choice':
                    print(f"  [{stream_name} #{call['digit_pos']}] choice(pool_size={call['pool_size']})")
                    print(f"    digit_value={call['digit_value']}, {call['digit_value']} % {call['pool_size']} = {call['selected_index']}")
                    print(f"    → {repr(call['selected_value'][:80])}")
                    if args.verbose:
                        for i, opt in enumerate(call['pool']):
                            marker = " >>>" if i == call['selected_index'] else "    "
                            print(f"    {marker} [{i}] {repr(opt[:80])}")
                elif call['type'] == 'random':
                    print(f"  [{stream_name} #{call['digit_pos']}] random()")
                    print(f"    digit_value={call['digit_value']}, result={call['result']:.2f}")

        print()

    if args.output:
        with open(args.output, 'w') as f:
            f.write(rendered)
        print(f"Rendered output written to {args.output}")


def cmd_solve(args):
    """Solve for a seed given constraints."""
    constraints = json.loads(args.constraints)

    # constraints should be a list of dicts: [{"stream": [pool_size, desired_idx]}, ...]
    parsed = []
    for digit_constraints in constraints:
        parsed_digit = {}
        for stream, (pool_size, desired_idx) in digit_constraints.items():
            parsed_digit[stream] = (pool_size, desired_idx)
        parsed.append(parsed_digit)

    seed, success, conflicts = solve_seed(parsed)

    print(f"Seed: {seed}")
    print(f"Success: {success}")

    if conflicts:
        print(f"\nConflicts at {len(conflicts)} digit position(s):")
        for pos, cons in conflicts:
            print(f"  Digit {pos}: {cons}")
            print(f"    No value 0-99 satisfies all constraints simultaneously.")

    # Show verification
    print(f"\nVerification:")
    for digit_pos, digit_constraints in enumerate(parsed):
        digit_value = (seed // (100 ** digit_pos)) % 100
        print(f"  Digit {digit_pos} = {digit_value}:")
        for stream, (pool_size, desired_idx) in digit_constraints.items():
            actual = digit_value % pool_size
            ok = "OK" if actual == desired_idx else "MISMATCH"
            print(f"    {stream}: {digit_value} % {pool_size} = {actual} (wanted {desired_idx}) [{ok}]")

    if args.timestamp:
        ts = seed_to_fractional(seed, args.timestamp)
        print(f"\nTimestamp: {ts}")
    else:
        print(f"\nFractional seconds: .{seed:07d}")


def cmd_search(args):
    """Search template pools for a phrase."""
    results = search_all_pools(args.phrase, outcome=args.outcome)

    if not results:
        print(f"No templates found matching '{args.phrase}'")
        if args.outcome:
            print(f"  (searched only in outcome: {args.outcome})")
        print(f"\nTip: Try a shorter or different search term.")
        return

    print(f"Found {len(results)} match(es) for '{args.phrase}':\n")
    for r in results:
        print(f"  Pool: {r['pool']}")
        print(f"  Index: {r['index']} of {r['total']}")
        print(f"  Template: {repr(r['template'])}")
        print()


def cmd_list_pool(args):
    """List all templates in a pool."""
    items = list_pool(args.pool)

    if not items:
        print(f"Pool '{args.pool}' not found or empty.")
        return

    print(f"Pool: {args.pool} ({len(items)} items)\n")
    for idx, template in items:
        print(f"  [{idx}] {repr(template)}")


def cmd_diff(args):
    """Diff rendered output vs target text."""
    with open(args.json_file) as f:
        data = json.load(f)

    with open(args.target_file) as f:
        target_text = f.read()

    from renderers.narrative.renderer import NarrativeRenderer
    renderer = NarrativeRenderer(data)
    rendered_text = renderer.render()

    results = diff_rendered_vs_target(rendered_text, target_text)

    matches = sum(1 for r in results if r['match'])
    total = len(results)
    mismatches = [r for r in results if not r['match']]

    print(f"Line comparison: {matches}/{total} lines match ({100*matches/total:.1f}%)\n")

    if args.play is not None:
        # Show all lines around a specific play block
        # For now, show all mismatches
        pass

    # Show mismatches (skip empty line mismatches unless verbose)
    shown = 0
    for r in mismatches:
        t = r['target'] or ''
        rv = r['rendered'] or ''

        # Skip TTS marker differences and empty lines unless verbose
        if not args.verbose:
            if not t and not rv:
                continue
            if t.startswith('[TTS') and rv.startswith('[TTS'):
                continue

        print(f"Line {r['line_num']} [{r['type']}]:")
        if t:
            print(f"  TARGET:   {t[:120]}")
        if rv:
            print(f"  RENDERED: {rv[:120]}")
        print()

        shown += 1
        if not args.all and shown >= 50:
            remaining = len(mismatches) - shown
            if remaining > 0:
                print(f"... and {remaining} more mismatches. Use --all to see all.")
            break

    # Summary statistics
    target_lines = set(l.strip() for l in target_text.split('\n') if l.strip() and not l.strip().startswith('[TTS'))
    rendered_lines = set(l.strip() for l in rendered_text.split('\n') if l.strip() and not l.strip().startswith('[TTS'))
    identical = target_lines.intersection(rendered_lines)

    print(f"\n--- Summary ---")
    print(f"Content lines in target: {len(target_lines)}")
    print(f"Content lines in rendered: {len(rendered_lines)}")
    print(f"Identical content lines: {len(identical)} ({100*len(identical)/len(target_lines):.1f}%)")

    # Word-level Jaccard
    def get_words(s):
        return set(re.findall(r'\b\w+\b', s.lower()))
    tw = get_words(target_text)
    rw = get_words(rendered_text)
    jaccard = len(tw & rw) / len(tw | rw) if tw | rw else 0
    print(f"Word Jaccard similarity: {100*jaccard:.1f}%")

    if args.output:
        with open(args.output, 'w') as f:
            f.write(rendered_text)
        print(f"\nRendered output written to {args.output}")


def cmd_whatif(args):
    """
    Show what a specific seed would select from a pool.

    Example:
        python pbp_tools.py whatif 300 narrative_templates.Single.default
        python pbp_tools.py whatif 300 narrative_strings.batter_intro_leadoff
    """
    seed = int(args.seed)
    items = list_pool(args.pool)

    if not items:
        print(f"Pool '{args.pool}' not found or empty.")
        return

    pool_size = len(items)
    selected_idx = seed % pool_size
    remaining = seed // 100

    print(f"Seed: {seed}")
    print(f"Pool: {args.pool} ({pool_size} items)")
    print(f"Selection: {seed} % {pool_size} = {selected_idx}")
    print(f"Remaining seed after consumption: {remaining}")
    print()

    for idx, template in items:
        marker = " >>>" if idx == selected_idx else "    "
        print(f"  {marker} [{idx}] {repr(template)}")

    # Show which seeds (0-99) would select each index
    print(f"\n--- Seed values (0-99) that select each index ---")
    for idx, template in items:
        values = [v for v in range(100) if v % pool_size == idx]
        print(f"  [{idx}] values: {values[:10]}{'...' if len(values) > 10 else ''}")


def get_play_seed_points(gameday_data, play_index):
    """
    Get all seed points for a specific play, in order.

    Returns list of dicts:
        - point_type: 'play_start', 'event_N', 'play_outcome'
        - timestamp: the timestamp string
        - seed: the extracted seed
        - json_path: how to find/update this in the JSON
    """
    play = gameday_data['liveData']['plays']['allPlays'][play_index]
    points = []

    if 'startTime' in play['about']:
        ts = play['about']['startTime']
        points.append({
            'point_type': 'play_start',
            'timestamp': ts,
            'seed': timestamp_to_seed(ts),
            'json_path': f"liveData.plays.allPlays[{play_index}].about.startTime"
        })

    for i, event in enumerate(play['playEvents']):
        if 'startTime' in event:
            ts = event['startTime']
            points.append({
                'point_type': f'event_{i}',
                'timestamp': ts,
                'seed': timestamp_to_seed(ts),
                'json_path': f"liveData.plays.allPlays[{play_index}].playEvents[{i}].startTime"
            })

    if 'endTime' in play['about']:
        ts = play['about']['endTime']
        points.append({
            'point_type': 'play_outcome',
            'timestamp': ts,
            'seed': timestamp_to_seed(ts),
            'json_path': f"liveData.plays.allPlays[{play_index}].about.endTime"
        })

    return points


def cmd_inspect_play(args):
    """
    Inspect a single play: show all seed points, RNG choices, and current output.
    """
    with open(args.json_file) as f:
        data = json.load(f)

    play_index = args.play
    plays = data['liveData']['plays']['allPlays']
    if play_index >= len(plays):
        print(f"Play index {play_index} out of range (0-{len(plays)-1})")
        return

    play = plays[play_index]
    matchup = play['matchup']
    result = play['result']

    print(f"{'='*70}")
    print(f"PLAY {play_index}: {matchup['batter']['fullName']} vs {matchup['pitcher']['fullName']}")
    print(f"Result: {result['event']} | Score: {result['awayScore']}-{result['homeScore']}")
    print(f"Inning: {'Top' if play['about']['isTopInning'] else 'Bot'} {play['about']['inning']}")
    print(f"{'='*70}")

    seed_points = get_play_seed_points(data, play_index)

    for sp in seed_points:
        print(f"\n--- {sp['point_type']} (seed={sp['seed']}) ---")
        print(f"  Timestamp: {sp['timestamp']}")
        print(f"  JSON path: {sp['json_path']}")

        # Show what each stream would select at different digit positions
        seed = sp['seed']
        print(f"  Base-100 digits: ", end="")
        temp = seed
        digits = []
        for _ in range(5):
            digits.append(temp % 100)
            temp //= 100
        print(" | ".join(f"d{i}={d}" for i, d in enumerate(digits)))

    # Now trace the full render and extract just this play's seed points
    tracer = TracingRenderer(data)
    rendered = tracer.render()

    # Map seed_log entries to plays by sequential order.
    # Seed log order: init, then for each play: play_start, event*N, play_outcome
    # We scan the log and group entries between consecutive play_start entries.
    play_entries = []  # list of lists, one per play
    current_play_entries = []
    seen_init = False
    play_counter = -1

    for entry in tracer.seed_log:
        salt = entry['salt']
        if salt == 'init':
            seen_init = True
            continue
        if salt == 'play_start':
            if current_play_entries:
                play_entries.append(current_play_entries)
            current_play_entries = [entry]
            play_counter += 1
        else:
            current_play_entries.append(entry)
    if current_play_entries:
        play_entries.append(current_play_entries)

    if play_index >= len(play_entries):
        print(f"\nCould not find trace entries for play {play_index}")
        return

    my_entries = play_entries[play_index]

    print(f"\n{'='*70}")
    print(f"RNG CALLS FOR THIS PLAY ({len(my_entries)} seed points)")
    print(f"{'='*70}")

    for entry in my_entries:
        print(f"\n--- {entry['salt']} (seed={entry['seed']}, ts={entry['timestamp']}) ---")

        for stream_name in ['flow', 'pitch', 'play', 'color']:
            rng = entry['rngs'][stream_name]
            if not rng.calls:
                continue

            for call in rng.calls:
                if call['type'] == 'choice':
                    print(f"  [{stream_name} #{call['digit_pos']}] choice(pool_size={call['pool_size']})")
                    print(f"    {call['digit_value']} % {call['pool_size']} = {call['selected_index']}")
                    print(f"    → {repr(call['selected_value'][:100])}")
                    if args.verbose:
                        for i, opt in enumerate(call['pool']):
                            marker = " >>>" if i == call['selected_index'] else "    "
                            print(f"    {marker} [{i}] {repr(opt[:100])}")
                elif call['type'] == 'random':
                    threshold_info = ""
                    # Common thresholds
                    if call['result'] < 0.2:
                        threshold_info = " (< 0.2: matchup=True, < 0.5: runners_stretch=True, < 0.6: comma=True, verb=True)"
                    elif call['result'] < 0.5:
                        threshold_info = " (>= 0.2: matchup=False, < 0.5: runners_stretch=True, < 0.6: comma=True, verb=True)"
                    elif call['result'] < 0.6:
                        threshold_info = " (>= 0.5: stretch=False, < 0.6: comma=True, verb=True)"
                    elif call['result'] < 0.8:
                        threshold_info = " (>= 0.6: comma=False, < 0.8: use_template=True)"
                    else:
                        threshold_info = " (>= 0.8: use_template=False)"
                    print(f"  [{stream_name} #{call['digit_pos']}] random() = {call['result']:.2f}{threshold_info}")

    # Show the rendered output for this play
    rendered_lines = rendered.split('\n')
    # Find the output block for this play by looking at empty-line-separated blocks
    blocks = rendered.split('\n\n')
    # The pre-game takes several blocks, then each play is its own block
    # A rough heuristic: count plays to find the right block

    print(f"\n{'='*70}")
    print(f"RENDERED OUTPUT FOR THIS PLAY")
    print(f"{'='*70}")

    # Count non-empty blocks to find plays
    # Pre-game is blocks 0, then inning headers, then plays...
    # Actually, let's just find the batter's name in blocks
    batter_name = matchup['batter']['fullName']
    for i, block in enumerate(blocks):
        if batter_name in block and any(kw in block for kw in ['leads off', 'steps in', 'comes to', 'will step', 'And here', 'Now batting']):
            print(block)
            break
    else:
        # Fallback: search for any block mentioning the batter
        for block in blocks:
            if batter_name in block:
                print(block)
                break


def cmd_set_choice(args):
    """
    Update a seed in the fixture JSON so a specific template is selected.

    This command:
    1. Traces the current rendering at the specified seed point
    2. Preserves all existing selections as constraints
    3. Overrides the specified selection(s)
    4. Solves for a new seed
    5. Updates the JSON file

    Usage:
        # Change play 0's outcome to select index 2 from rng_play's first choice
        python pbp_tools.py set-choice fixture.json --play 0 --point play_outcome \\
            --set play:1:3

        # --set format is stream:call_number:desired_index
        # Multiple --set flags can be used
    """
    with open(args.json_file) as f:
        data = json.load(f)

    play_index = args.play
    point_type = args.point
    overrides = {}

    for s in args.set:
        parts = s.split(':')
        if len(parts) != 3:
            print(f"Invalid --set format '{s}'. Expected stream:call_number:desired_index")
            return
        stream, call_num, desired_idx = parts[0], int(parts[1]), int(parts[2])
        overrides[(stream, call_num)] = desired_idx

    # Find the seed point in the JSON
    seed_points = get_play_seed_points(data, play_index)
    target_sp = None
    for sp in seed_points:
        if sp['point_type'] == point_type:
            target_sp = sp
            break

    if not target_sp:
        print(f"Seed point '{point_type}' not found for play {play_index}")
        print(f"Available: {[sp['point_type'] for sp in seed_points]}")
        return

    # Trace the render to get current selections at this seed point
    tracer = TracingRenderer(data)
    tracer.render()

    # Find the trace entry for this seed point
    target_entry = None
    for entry in tracer.seed_log:
        if entry['timestamp'] == target_sp['timestamp'] and entry['salt'] == point_type.replace('event_', 'event').replace('play_start', 'play_start').replace('play_outcome', 'play_outcome'):
            target_entry = entry
            break

    if not target_entry:
        # Try matching by timestamp only
        for entry in tracer.seed_log:
            if entry['timestamp'] == target_sp['timestamp']:
                target_entry = entry
                break

    if not target_entry:
        print(f"Could not find trace entry for {point_type} at {target_sp['timestamp']}")
        return

    # With split-stream encoding, each stream has its own 2-digit seed.
    # We solve each stream independently — no cross-stream conflicts possible.
    old_packed = target_sp['seed']
    old_streams = unpack_stream_seeds(old_packed)

    print(f"Old packed seed: {old_packed}")
    print(f"Old per-stream: play={old_streams['play']}, pitch={old_streams['pitch']}, flow={old_streams['flow']}, color={old_streams['color']}")

    new_streams = dict(old_streams)

    for (stream_name, call_num), desired_idx in overrides.items():
        rng = target_entry['rngs'].get(stream_name)
        if not rng or call_num >= len(rng.calls):
            print(f"Warning: {stream_name} call {call_num} not found in trace")
            continue

        call = rng.calls[call_num]
        if call_num > 0:
            print(f"Warning: {stream_name} call {call_num} > 0. With split-stream encoding, "
                  f"each stream only has 2 digits (1 meaningful call). Call {call_num} "
                  f"would require a larger seed allocation.")
            continue

        if call['type'] == 'choice':
            pool_size = call['pool_size']
            # Find a 2-digit value where value % pool_size == desired_idx
            found = False
            for candidate in range(100):
                if candidate % pool_size == desired_idx:
                    new_streams[stream_name] = candidate
                    found = True
                    break
            if not found:
                print(f"Error: no value 0-99 satisfies {stream_name} % {pool_size} == {desired_idx}")
        elif call['type'] == 'random':
            new_streams[stream_name] = desired_idx

    new_packed = pack_stream_seeds(**new_streams)
    print(f"New per-stream: play={new_streams['play']}, pitch={new_streams['pitch']}, flow={new_streams['flow']}, color={new_streams['color']}")
    print(f"New packed seed: {new_packed}")

    # Update the JSON
    old_ts = target_sp['timestamp']
    base = old_ts.split('.')[0]
    tz_suffix = ''
    if '+' in old_ts.split('.')[-1]:
        tz_suffix = '+' + old_ts.split('.')[-1].split('+')[1]
    elif old_ts.endswith('Z'):
        tz_suffix = 'Z'
    new_ts = f"{base}.{new_packed:08d}{tz_suffix}"

    if not args.dry_run:
        path = target_sp['json_path']
        parts = re.findall(r'(\w+)|\[(\d+)\]', path)
        obj = data
        for i, (key, idx) in enumerate(parts[:-1]):
            if key:
                obj = obj[key]
            elif idx:
                obj = obj[int(idx)]

        last_key, last_idx = parts[-1]
        if last_key:
            obj[last_key] = new_ts
        elif last_idx:
            obj[int(last_idx)] = new_ts

        with open(args.json_file, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"\nUpdated {target_sp['json_path']}:")
        print(f"  Old: {old_ts}")
        print(f"  New: {new_ts}")
    else:
        print(f"\n[DRY RUN] Would update {target_sp['json_path']}")
        print(f"  Old: {old_ts}")
        print(f"  New: {new_ts}")

    # Show what the overridden selections would produce
    print(f"\nOverrides applied:")
    for (stream, call_num), desired_idx in overrides.items():
        for rng_name, rng in target_entry['rngs'].items():
            if rng_name == stream and call_num < len(rng.calls):
                call = rng.calls[call_num]
                if call['type'] == 'choice':
                    old_val = call['selected_value']
                    new_val = call['pool'][desired_idx] if desired_idx < len(call['pool']) else '???'
                    print(f"  {stream}#{call_num}: [{call['selected_index']}] {repr(old_val[:60])} → [{desired_idx}] {repr(new_val[:60])}")


def main():
    parser = argparse.ArgumentParser(
        description='Tools for aligning PBP output with target text',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # trace
    p_trace = subparsers.add_parser('trace', help='Trace RNG calls during rendering')
    p_trace.add_argument('json_file', help='Gameday JSON fixture file')
    p_trace.add_argument('--play', type=int, default=None, help='Play index to focus on')
    p_trace.add_argument('--verbose', '-v', action='store_true', help='Show full option pools')
    p_trace.add_argument('--output', '-o', help='Write rendered text to file')

    # solve
    p_solve = subparsers.add_parser('solve', help='Solve for a seed from constraints')
    p_solve.add_argument('--constraints', '-c', required=True,
                         help='JSON: list of dicts mapping stream names to [pool_size, desired_index]')
    p_solve.add_argument('--timestamp', '-t', default=None,
                         help='Base timestamp to encode seed into (e.g., "2025-09-27T23:05:00")')

    # search
    p_search = subparsers.add_parser('search', help='Search template pools for a phrase')
    p_search.add_argument('phrase', help='Phrase to search for (case-insensitive)')
    p_search.add_argument('--outcome', help='Restrict search to a specific outcome type')

    # list-pool
    p_list = subparsers.add_parser('list-pool', help='List all templates in a pool')
    p_list.add_argument('pool', help='Dotted pool path (e.g., narrative_templates.Single.default)')

    # diff
    p_diff = subparsers.add_parser('diff', help='Diff rendered output vs target text')
    p_diff.add_argument('json_file', help='Gameday JSON fixture file')
    p_diff.add_argument('target_file', help='Target text file (e.g., pbp_example_3.txt)')
    p_diff.add_argument('--play', type=int, default=None, help='Focus on a specific play')
    p_diff.add_argument('--verbose', '-v', action='store_true', help='Show all mismatches including TTS')
    p_diff.add_argument('--all', action='store_true', help='Show all mismatches (no limit)')
    p_diff.add_argument('--output', '-o', help='Write rendered text to file')

    # whatif
    p_whatif = subparsers.add_parser('whatif', help='Show what a seed selects from a pool')
    p_whatif.add_argument('seed', help='Seed value to test')
    p_whatif.add_argument('pool', help='Dotted pool path')

    # inspect-play
    p_inspect = subparsers.add_parser('inspect-play', help='Inspect a single play in detail')
    p_inspect.add_argument('json_file', help='Gameday JSON fixture file')
    p_inspect.add_argument('--play', type=int, required=True, help='Play index')
    p_inspect.add_argument('--verbose', '-v', action='store_true', help='Show full option pools')

    # set-choice
    p_set = subparsers.add_parser('set-choice', help='Update a seed to select specific templates')
    p_set.add_argument('json_file', help='Gameday JSON fixture file')
    p_set.add_argument('--play', type=int, required=True, help='Play index')
    p_set.add_argument('--point', required=True,
                       help='Seed point type: play_start, event_N (e.g., event_0), play_outcome')
    p_set.add_argument('--set', action='append', required=True,
                       help='stream:call_number:desired_index (can repeat)')
    p_set.add_argument('--dry-run', action='store_true', help='Show what would change without writing')

    args = parser.parse_args()

    if args.command == 'trace':
        cmd_trace(args)
    elif args.command == 'solve':
        cmd_solve(args)
    elif args.command == 'search':
        cmd_search(args)
    elif args.command == 'list-pool':
        cmd_list_pool(args)
    elif args.command == 'diff':
        cmd_diff(args)
    elif args.command == 'whatif':
        cmd_whatif(args)
    elif args.command == 'inspect-play':
        cmd_inspect_play(args)
    elif args.command == 'set-choice':
        cmd_set_choice(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
