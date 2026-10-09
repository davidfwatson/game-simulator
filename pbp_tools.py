#!/usr/bin/env python3
"""Tools for tracing, editing, searching, and comparing PBP commentary.

Commentary draws live in ``owner["commentaryRng"][point][stream]``. Each
nonnegative integer selects ``draw % len(pool)`` for a choice, or
``(draw % 100) / 100`` for a probability gate. Lists can contain any number
of draws. Game initialization belongs to gameData; play_start/play_outcome
belong to the play; event belongs to the pitch event. Timestamps stay intact.

Examples::

    python pbp_tools.py trace fixture.json --play 0
    python pbp_tools.py inspect-play fixture.json --play 0 -v
    python pbp_tools.py set-choice fixture.json --play 0 --point event_0 --set pitch:3:12
    python pbp_tools.py set-choice fixture.json --point init --set color:4:2 --dry-run
    python pbp_tools.py set-gate fixture.json --play 0 --point play_start --stream color --call 2 --below .2
    python pbp_tools.py search "misses a bit low"
    python pbp_tools.py diff fixture.json transcript.txt
"""

import json
import argparse
import math
from commentary import GAME_CONTEXT
from pbp_comparison import compare_transcripts, normalize_line
from renderers.randomness import STREAM_NAMES


class TracingRNG:
    """Record the installed RNG without changing the values it produces."""

    def __init__(self, rng, name=""):
        self.rng = rng
        self.name = name
        self.calls = []

    def choice(self, seq):
        if not seq:
            raise IndexError("Cannot choose from an empty sequence")
        # Ask for an index so duplicate values in a pool remain distinguishable.
        selected_index = self.rng.choice(range(len(seq)))
        value = seq[selected_index]
        self.calls.append({
            'type': 'choice',
            'call_index': len(self.calls),
            'draw': selected_index,
            'pool_size': len(seq),
            'selected_index': selected_index,
            'selected_value': value if isinstance(value, str) else str(value),
            'pool': [item if isinstance(item, str) else str(item) for item in seq],
            'stream': self.name,
        })
        return value

    def random(self):
        value = self.rng.random()
        # Explicit replay supports hundredths; floor preserves the side of all
        # hundredth-aligned comparison thresholds used by commentary gates.
        digit = min(99, math.floor(value * 100 + 1e-12))
        self.calls.append({
            'type': 'random',
            'call_index': len(self.calls),
            'draw': digit,
            'result': value,
            'stream': self.name,
        })
        return value

class TracingRenderer:
    """Instrument every stable point, including constructor initialization."""

    def __init__(self, gameday_data, seed=None):
        from renderers.narrative.renderer import NarrativeRenderer

        self.gameday_data = gameday_data
        self.seed_log = []
        seed_log = self.seed_log

        class InstrumentedRenderer(NarrativeRenderer):
            def _reseed_for_point(renderer, owner, point, timestamp, key):
                super()._reseed_for_point(owner, point, timestamp, key)
                rngs = {}
                for name in STREAM_NAMES:
                    rngs[name] = TracingRNG(getattr(renderer, f'rng_{name}'), name)
                    setattr(renderer, f'rng_{name}', rngs[name])
                renderer.rng = renderer.rng_play
                seed_log.append({
                    'key': key,
                    'point': point,
                    'owner': owner,
                    'timestamp': timestamp,
                    'rngs': rngs,
                })

        self.renderer = InstrumentedRenderer(gameday_data, seed=seed)

    def render(self):
        self.seed_log.clear()
        return self.renderer.render()


def materialize_trace_entry(entry):
    """Store every observed draw at one point, preserving unused explicit draws."""
    points = entry['owner'].setdefault('commentaryRng', {})
    previous = points.get(entry['point'], {})
    draws = {}
    for name, rng in entry['rngs'].items():
        observed = [call['draw'] for call in rng.calls]
        # Keep explicit draws beyond the rendered branch for future edits.
        draws[name] = observed + list(previous.get(name, []))[len(observed):]
    points[entry['point']] = draws
    return draws


# ===========================================================================
# Template Pool Search
# ===========================================================================

def search_all_pools(phrase, outcome=None):
    """Search every string pool, including newly added nested categories.

    When outcome is supplied, restrict outcome-specific pools while retaining
    shared pitch, lineup, and transition phrases.
    """
    results = []
    needle = phrase.casefold()
    outcome_groups = {'narrative_templates', 'statcast_verbs', 'statcast_templates'}

    def visit(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                if outcome and path in outcome_groups and key != outcome:
                    continue
                visit(child, f'{path}.{key}' if path else key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, str) and needle in item.casefold():
                    results.append({'pool': path, 'index': index,
                                    'total': len(value), 'template': item})
                elif isinstance(item, (dict, list)):
                    visit(item, f'{path}.{index}')

    visit(GAME_CONTEXT, '')
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

def diff_rendered_vs_target(rendered_text, target_text):
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

def _print_trace_entry(entry, verbose=False):
    print(f"\nPOINT: {entry['key']} ({entry['point']})")
    print(f"  Timestamp: {entry['timestamp']}")
    for stream_name in STREAM_NAMES:
        for call in entry['rngs'][stream_name].calls:
            prefix = f"  [{stream_name} #{call['call_index']}]"
            if call['type'] == 'choice':
                print(f"{prefix} choice(pool_size={call['pool_size']}), index={call['selected_index']}")
                print(f"    → {call['selected_value']!r}")
                if verbose:
                    for i, option in enumerate(call['pool']):
                        marker = '>>>' if i == call['selected_index'] else '   '
                        print(f"    {marker} [{i}] {option!r}")
            else:
                print(f"{prefix} random() = {call['result']:.6g}, replay draw={call['draw']}")


def cmd_trace(args):
    """Trace the actual renderer RNGs, optionally filtering by stable play key."""
    with open(args.json_file) as f:
        data = json.load(f)
    if args.play is not None:
        get_play_rng_points(data, args.play)  # Validate before rendering.
    tracer = TracingRenderer(data)
    rendered = tracer.render()
    entries = tracer.seed_log
    if args.play is not None:
        entries = [entry for entry in entries if entry['key'].startswith(f'play:{args.play}:')]
    print(f"Total RNG points: {len(entries)}")
    for entry in entries:
        if args.verbose or any(rng.calls for rng in entry['rngs'].values()):
            _print_trace_entry(entry, args.verbose)
    if args.output:
        with open(args.output, 'w') as f:
            f.write(rendered)
        print(f"\nRendered output written to {args.output}")


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

    from transcript_asides import load_asides, strip_asides
    with open(args.target_file) as f:
        target_text = f.read()
    # Annotated host asides count for nothing, as in the regression metrics.
    target_text = strip_asides(target_text, load_asides(args.target_file))

    from renderers.narrative.renderer import NarrativeRenderer
    renderer = NarrativeRenderer(data)
    rendered_text = renderer.render()

    results = diff_rendered_vs_target(rendered_text, target_text)

    matches = sum(1 for r in results if r['match'])
    total = len(results)
    mismatches = [r for r in results if not r['match']]

    print(f"Line comparison: {matches}/{total} lines match ({100*matches/total:.1f}%)\n")

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

    # Use the same ordered exact-match logic as regression tests and reports.
    # Word overlap alone cannot distinguish "runner beats ball" from its reverse.
    target_content = [line.strip() for line in target_text.splitlines()
                      if line.strip() and not line.strip().startswith('[TTS SPLIT')]
    rendered_content = [line.strip() for line in rendered_text.splitlines()
                        if line.strip() and not line.strip().startswith('[TTS SPLIT')]
    identical = set(map(normalize_line, target_content)).intersection(
        map(normalize_line, rendered_content))
    identical_raw = set(target_content).intersection(rendered_content)
    scores = compare_transcripts(target_text, rendered_text)
    content = scores.content_lines
    n_target = content.total
    n_rendered = len(rendered_content)
    denominator = n_target or 1
    total_good = content.exact + content.near90 + content.near75

    print("\n--- Summary ---")
    print(f"Content lines in target: {n_target}")
    print(f"Content lines in rendered: {n_rendered}")
    print(f"Identical content lines (raw): {len(identical_raw)} ({100*len(identical_raw)/denominator:.1f}%)")
    print(f"Identical content lines (normalized): {len(identical)} ({100*len(identical)/denominator:.1f}%)")
    print("\nPositional fuzzy matching (±8% of file):")
    print(f"  Exact match:  {content.exact} ({100*content.exact/denominator:.1f}%)")
    print(f"  ≥90% similar: {content.near90} ({100*content.near90/denominator:.1f}%)")
    print(f"  ≥75% similar: {content.near75} ({100*content.near75/denominator:.1f}%)")
    print(f"  Total ≥75%:   {total_good} ({100*total_good/denominator:.1f}%)")
    print(f"\nWord Jaccard similarity: {100*scores.jaccard:.1f}%")

    if args.output:
        with open(args.output, 'w') as f:
            f.write(rendered_text)
        print(f"\nRendered output written to {args.output}")


def get_play_rng_points(gameday_data, play_index):
    """Locate RNG points by structural position, regardless of timestamps."""
    plays = gameday_data['liveData']['plays']['allPlays']
    if play_index is None or not 0 <= play_index < len(plays):
        raise ValueError(f"Play index {play_index} out of range (0-{len(plays) - 1})")
    play = plays[play_index]
    prefix = f"liveData.plays.allPlays[{play_index}]"
    about = play.get('about', {})
    points = [{
        'point_type': 'play_start', 'point': 'play_start', 'owner': play,
        'key': f'play:{play_index}:start',
        'timestamp': about.get('startTime', ''),
        'json_path': f'{prefix}.commentaryRng.play_start',
    }]
    for i, event in enumerate(play.get('playEvents', [])):
        points.append({
            'point_type': f'event_{i}', 'point': 'event', 'owner': event,
            'key': f'play:{play_index}:event:{i}',
            'timestamp': event.get('startTime', ''),
            'json_path': f'{prefix}.playEvents[{i}].commentaryRng.event',
        })
    points.append({
        'point_type': 'play_outcome', 'point': 'play_outcome', 'owner': play,
        'key': f'play:{play_index}:outcome',
        'timestamp': about.get('endTime', ''),
        'json_path': f'{prefix}.commentaryRng.play_outcome',
    })
    return points


def get_rng_point(gameday_data, play_index, point_type):
    if point_type == 'init':
        owner = gameday_data['gameData']
        return {
            'point_type': 'init', 'point': 'init', 'owner': owner, 'key': 'init',
            'timestamp': owner.get('datetime', {}).get('dateTime', ''),
            'json_path': 'gameData.commentaryRng.init',
        }
    points = get_play_rng_points(gameday_data, play_index)
    for point in points:
        if point['point_type'] == point_type:
            return point
    raise ValueError(f"Unknown point {point_type!r}; choose init or one of "
                     f"{[point['point_type'] for point in points]}")


def cmd_inspect_play(args):
    """Show a play's explicit draws, available selections, and rendered lines."""
    with open(args.json_file) as f:
        data = json.load(f)
    points = get_play_rng_points(data, args.play)
    play = data['liveData']['plays']['allPlays'][args.play]
    matchup = play['matchup']
    print(f"PLAY {args.play}: {matchup['batter']['fullName']} vs {matchup['pitcher']['fullName']}")
    print(f"Result: {play['result']['event']}")
    for point in points:
        draws = point['owner'].get('commentaryRng', {}).get(point['point'])
        print(f"\n{point['json_path']}: {draws if draws is not None else '(fallback RNG)'}")
    tracer = TracingRenderer(data)
    rendered = tracer.render()
    for entry in tracer.seed_log:
        if entry['key'].startswith(f'play:{args.play}:'):
            _print_trace_entry(entry, args.verbose)
    line_map = getattr(tracer.renderer, '_play_line_map', {})
    if args.play in line_map:
        start, end = line_map[args.play]
        print("\nRENDERED OUTPUT FOR THIS PLAY")
        print('\n'.join(rendered.split('\n')[start:end]))


def edit_commentary_draws(data, play_index, point_type, overrides, expected_type=None):
    """Validate and edit arbitrary observed calls at one stable RNG point.

    ``overrides`` maps (stream, zero-based call index) to a choice index or
    probability digit. All current calls at this point are materialized first,
    so editing a late call preserves earlier selections in the same stream.
    """
    point = get_rng_point(data, play_index, point_type)
    tracer = TracingRenderer(data)
    tracer.render()
    entry = next((item for item in tracer.seed_log if item['key'] == point['key']), None)
    if entry is None:
        raise ValueError(f"Point {point['key']} was not reached during rendering")
    if not overrides:
        raise ValueError('Specify at least one draw override')
    for (stream, call_index), value in overrides.items():
        if stream not in STREAM_NAMES:
            raise ValueError(f"Unknown RNG stream {stream!r}; choose {', '.join(STREAM_NAMES)}")
        calls = entry['rngs'][stream].calls
        if not isinstance(call_index, int) or not 0 <= call_index < len(calls):
            raise ValueError(f"{stream} call {call_index} not found at {point['key']} "
                             f"({len(calls)} observed calls)")
        call = calls[call_index]
        if expected_type and call['type'] != expected_type:
            raise ValueError(f"{stream} call {call_index} is {call['type']}(), "
                             f"expected {expected_type}()")
        limit = call['pool_size'] if call['type'] == 'choice' else 100
        if type(value) is not int or not 0 <= value < limit:
            raise ValueError(f"{stream} call {call_index}: value must be an integer "
                             f"in 0-{limit - 1}, got {value!r}")
    draws = materialize_trace_entry(entry)
    for (stream, call_index), value in overrides.items():
        draws[stream][call_index] = value
    return point, entry, draws


def _save_draw_edit(args, data, point, draws):
    prefix = '[DRY RUN] Would update' if getattr(args, 'dry_run', False) else 'Updated'
    if not getattr(args, 'dry_run', False):
        with open(args.json_file, 'w') as f:
            json.dump(data, f, indent=2)
            f.write('\n')
    print(f"{prefix} {point['json_path']}:")
    print(json.dumps(draws, indent=2))


def cmd_set_choice(args):
    """Store explicit draws while preserving other observed calls and timestamps."""
    with open(args.json_file) as f:
        data = json.load(f)
    overrides = {}
    for spec in args.set:
        try:
            stream, call_number, desired_index = spec.split(':')
            overrides[(stream, int(call_number))] = int(desired_index)
        except ValueError as error:
            raise ValueError(f"Invalid --set {spec!r}; expected stream:call_number:desired_index") from error
    point, entry, draws = edit_commentary_draws(data, args.play, args.point, overrides)
    _save_draw_edit(args, data, point, draws)
    for (stream, call_number), value in overrides.items():
        call = entry['rngs'][stream].calls[call_number]
        if call['type'] == 'choice':
            print(f"{stream}#{call_number}: [{call['selected_index']}] {call['selected_value']!r} "
                  f"→ [{value}] {call['pool'][value]!r}")
        else:
            print(f"{stream}#{call_number}: {call['result']:.6g} → {value / 100:.2f}")


def cmd_set_gate(args):
    """Set any observed random() call to a hundredth satisfying the threshold."""
    with open(args.json_file) as f:
        data = json.load(f)
    threshold = args.below if args.below is not None else args.above
    if threshold is None or not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError('Gate threshold must be between 0 and 1')
    if args.below is not None:
        candidates = [digit for digit in range(100) if digit / 100 < threshold]
        direction = f'below {threshold}'
    else:
        candidates = [digit for digit in range(100) if digit / 100 >= threshold]
        direction = f'at or above {threshold}'
    if not candidates:
        raise ValueError(f'No hundredth-valued draw is {direction}')
    digit = candidates[len(candidates) // 2]
    point, _, draws = edit_commentary_draws(
        data, args.play, args.point, {(args.stream, args.call): digit},
        expected_type='random',
    )
    _save_draw_edit(args, data, point, draws)
    print(f"{args.stream}#{args.call}: random() = {digit / 100:.2f} ({direction})")


def cmd_set_zone(args):
    """
    Set the pitch zone for a specific event in a play.

    Zone mapping (from catcher's perspective):
        11 = high-left,  12 = high-right
        13 = low-left,   14 = low-right
    For RHB: left=inside, right=outside
    For LHB: flipped
    """
    with open(args.json_file) as f:
        data = json.load(f)

    play_index = args.play
    event_index = args.event

    plays = data['liveData']['plays']['allPlays']
    if not 0 <= play_index < len(plays):
        raise ValueError(f"Play index {play_index} out of range (0-{len(plays)-1})")

    play = plays[play_index]
    events = play['playEvents']
    if not 0 <= event_index < len(events):
        raise ValueError(f"Event index {event_index} out of range (0-{len(events)-1})")

    # Resolve zone: either numeric or named
    zone_input = args.zone
    try:
        zone_num = int(zone_input)
    except ValueError:
        # Named zone -- resolve using batter handedness
        batter_hand = play['matchup'].get('batSide', {}).get('code', 'R')
        zone_names_rhb = {
            'high_inside': 11, 'high_outside': 12,
            'low_inside': 13, 'low_outside': 14,
        }
        zone_names_lhb = {
            'high_outside': 11, 'high_inside': 12,
            'low_outside': 13, 'low_inside': 14,
        }
        zone_map = zone_names_rhb if batter_hand == 'R' else zone_names_lhb
        if zone_input not in zone_map:
            print(f"Unknown zone name '{zone_input}'. Valid names: {list(zone_names_rhb.keys())}")
            return
        zone_num = zone_map[zone_input]
        print(f"Batter is {batter_hand}HB -> '{zone_input}' resolves to zone {zone_num}")

    # Update the zone
    event = events[event_index]
    old_zone = event.get('details', {}).get('zone')
    if 'details' not in event:
        event['details'] = {}
    event['details']['zone'] = zone_num

    print(f"Play {play_index}, Event {event_index}: zone {old_zone} -> {zone_num}")

    # Show the pool that this zone maps to
    event_type = event.get('details', {}).get('code', event.get('details', {}).get('type', {}).get('code', ''))
    batter_hand = play['matchup'].get('batSide', {}).get('code', 'R')

    if event_type == 'B':
        base_key = 'ball'
    elif event_type in ('C', 'S'):
        base_key = 'strike'
    else:
        base_key = None

    if base_key:
        # Determine category from zone (matching helpers.py logic)
        if base_key == 'ball':
            if batter_hand == 'R':
                zone_to_cat = {11: 'high_inside', 12: 'high_outside', 13: 'low_inside', 14: 'low_outside'}
            else:
                zone_to_cat = {11: 'high_outside', 12: 'high_inside', 13: 'low_outside', 14: 'low_inside'}
            category = zone_to_cat.get(zone_num, 'default')
        else:
            category = 'default'

        pool_path = f"pitch_locations.{base_key}.{category}"
        pool_items = list_pool(pool_path)
        if pool_items:
            print(f"\nPool: {pool_path} ({len(pool_items)} templates)")
            for idx, template in pool_items[:5]:
                print(f"  [{idx}] {repr(template)}")
            if len(pool_items) > 5:
                print(f"  ... and {len(pool_items) - 5} more")

    with open(args.json_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\nSaved {args.json_file}")


def cmd_set_category(args):
    """
    Set categoryOverride on a play's X event hitData to route to a specific template sub-pool.

    Valid categories depend on the outcome:
        Single:   default, bloop, liner, grounder
        Double:   default, liner, wall
        Home Run: default, screamer, moonshot
        Groundout: default, soft, hard, unassisted_1b, pitcher_groundout
        Flyout:   default, deep
        Pop Out:  default
        Lineout:  default
    """
    with open(args.json_file) as f:
        data = json.load(f)

    play_index = args.play
    category = args.category

    plays = data['liveData']['plays']['allPlays']
    if not 0 <= play_index < len(plays):
        raise ValueError(f"Play index {play_index} out of range (0-{len(plays)-1})")

    play = plays[play_index]
    outcome = play['result']['event']

    # Find the X event (batted ball in play)
    x_event = None
    x_event_idx = None
    for idx, event in enumerate(play['playEvents']):
        if event['details'].get('code') == 'X':
            x_event = event
            x_event_idx = idx
            break

    if x_event is None:
        print(f"No X event (ball in play) found in play {play_index} (outcome: {outcome})")
        print("This command only works on plays with a batted ball in play.")
        return

    # Set the categoryOverride in hitData
    if 'hitData' not in x_event:
        x_event['hitData'] = {}
    old_cat = x_event['hitData'].get('categoryOverride')
    x_event['hitData']['categoryOverride'] = category

    print(f"Play {play_index}: {play['matchup']['batter']['fullName']} - {outcome}")
    print(f"Event {x_event_idx} (X): categoryOverride {repr(old_cat)} -> {repr(category)}")

    # Normalize outcome for template lookup (same logic as play_description.py)
    template_outcome = outcome.split('(')[0].strip() if '(' in outcome else outcome
    if template_outcome.startswith("Groundout"):
        template_outcome = "Groundout"
    elif template_outcome.startswith("Flyout"):
        template_outcome = "Flyout"
    elif template_outcome.lower().startswith("grounded into double play") or template_outcome == "Double Play":
        template_outcome = "Double Play"
    elif template_outcome == "Reached on Error":
        template_outcome = "Groundout"
    elif template_outcome == "Popout":
        template_outcome = "Pop Out"

    # Show the resulting template pool
    outcome_templates = GAME_CONTEXT.get('narrative_templates', {}).get(template_outcome, {})
    pool = outcome_templates.get(category, [])
    fallback_used = False
    if not pool:
        pool = outcome_templates.get('default', [])
        fallback_used = True

    if pool:
        if fallback_used:
            print(f"\nNo '{category}' sub-pool for {template_outcome}; will fall back to 'default' ({len(pool)} templates)")
        else:
            print(f"\nTemplate pool: narrative_templates.{template_outcome}.{category} ({len(pool)} templates)")
        for idx, template in enumerate(pool):
            print(f"  [{idx}] {repr(template)}")
    else:
        print(f"\nNo templates found for {template_outcome} (neither '{category}' nor 'default')")

    with open(args.json_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\nSaved {args.json_file}")


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
    p_diff.add_argument('--verbose', '-v', action='store_true', help='Show all mismatches including TTS')
    p_diff.add_argument('--all', action='store_true', help='Show all mismatches (no limit)')
    p_diff.add_argument('--output', '-o', help='Write rendered text to file')

    # inspect-play
    p_inspect = subparsers.add_parser('inspect-play', help='Inspect a single play in detail')
    p_inspect.add_argument('json_file', help='Gameday JSON fixture file')
    p_inspect.add_argument('--play', type=int, required=True, help='Play index')
    p_inspect.add_argument('--verbose', '-v', action='store_true', help='Show full option pools')

    # set-choice
    p_set = subparsers.add_parser('set-choice', help='Store explicit draws to select specific templates')
    p_set.add_argument('json_file', help='Gameday JSON fixture file')
    p_set.add_argument('--play', type=int, help='Play index (omit for init)')
    p_set.add_argument('--point', required=True,
                       help='Point: init, play_start, event_N (e.g., event_0), play_outcome')
    p_set.add_argument('--set', action='append', required=True,
                       help='stream:call_number:desired_index (can repeat)')
    p_set.add_argument('--dry-run', action='store_true', help='Show what would change without writing')

    # set-gate
    p_gate = subparsers.add_parser('set-gate', help='Set a random() gate above or below a threshold')
    p_gate.add_argument('json_file', help='Gameday JSON fixture file')
    p_gate.add_argument('--play', type=int, help='Play index (omit for init)')
    p_gate.add_argument('--point', required=True,
                        help='Point: init, play_start, event_N (e.g., event_0), play_outcome')
    p_gate.add_argument('--stream', required=True, choices=['play', 'pitch', 'flow', 'color'],
                        help='RNG stream name')
    p_gate.add_argument('--call', type=int, required=True, help='Zero-based call index (any observed call)')
    p_gate.add_argument('--dry-run', action='store_true', help='Preview without writing')
    gate_group = p_gate.add_mutually_exclusive_group(required=True)
    gate_group.add_argument('--below', type=float, help='Set digit so random() < threshold')
    gate_group.add_argument('--above', type=float, help='Set digit so random() >= threshold')

    # set-category
    p_cat = subparsers.add_parser('set-category', help='Set batted ball category override for a play')
    p_cat.add_argument('json_file', help='Gameday JSON fixture file')
    p_cat.add_argument('--play', type=int, required=True, help='Play index')
    p_cat.add_argument('--category', required=True,
                       help='Category name (e.g., liner, bloop, grounder, wall, screamer, moonshot, deep, soft, hard, unassisted_1b, pitcher_groundout)')

    # set-zone
    p_zone = subparsers.add_parser('set-zone', help='Set pitch zone for a play event')
    p_zone.add_argument('json_file', help='Gameday JSON fixture file')
    p_zone.add_argument('--play', type=int, required=True, help='Play index')
    p_zone.add_argument('--event', type=int, required=True, help='Event index within the play')
    p_zone.add_argument('--zone', required=True,
                        help='Zone number (11-14) or name (high_inside, high_outside, low_inside, low_outside)')

    args = parser.parse_args()

    commands = {
        'trace': cmd_trace, 'search': cmd_search,
        'list-pool': cmd_list_pool, 'diff': cmd_diff,
        'inspect-play': cmd_inspect_play, 'set-choice': cmd_set_choice,
        'set-gate': cmd_set_gate, 'set-category': cmd_set_category,
        'set-zone': cmd_set_zone,
    }
    if args.command is None:
        parser.print_help()
        return
    try:
        commands[args.command](args)
    except ValueError as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
