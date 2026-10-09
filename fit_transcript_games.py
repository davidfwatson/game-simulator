"""Select reachable commentary draws for reviewed full-game fixtures.

This offline authoring pass searches actual phrase options offered by the
production renderer. The resulting fixture contains integers, not a transcript
or a renderer override. It is a starting point for reviewed wording alignment.

Two kinds of draw are fitted:

* ``choice(options)`` calls pick the option whose words best match the
  point's source window (greedy, per call).
* ``random()`` gates decide whether optional sentences are said at all, and
  sometimes which form they take. They are fitted per reseed point: every
  point's rendered text (its segment) is scored against its own source
  window, and each gate takes the value whose outcome scores best there.

Gate fitting is a coordinate descent. A coordinate is the k-th ``random()``
call of one stream at one kind of point (for example the first colour gate at
every ``play_start``). Only thresholds matter, so each coordinate tries one
value per interval between the thresholds the renderer actually compared
that draw against. One render evaluates a value at every point of that kind
at once; each point then keeps whichever value scored best for its own
segment. Points interact only through minor renderer state (repeated-phrase
avoidance), so this costs a few dozen renders per game instead of one per
gate. Host asides are excluded from every window (``transcript_asides``).
"""
import copy
import itertools
import json
import re
import sys
from collections import Counter
from functools import lru_cache

from renderers import NarrativeRenderer
from renderers.randomness import STREAM_NAMES
from transcript_asides import ASIDE_BREAK, load_asides, strip_asides
from transcript_game_fixtures import LEDGER_DIR, OUTPUT_DIR, SOURCE_DIR, compile_game

TTS = re.compile(r'\[TTS SPLIT[^\]]*\]')
# A removed aside: present in windows, never in renderer output, so no n-gram
# spanning it can match.
BREAK = '\0'
# A template placeholder ("The {count_str} pitch..."): options are scored
# before formatting, so a slot is a gap no n-gram spans. Dropping it instead
# made "the pitch" a false bigram that penalised every slotted template.
SLOT = '\1'
_SLOT_WORD = 'zzslotzz'
TOKEN = re.compile(rf'\w+|{ASIDE_BREAK}')
WEIGHTS = ((1, 1), (2, 3), (3, 6))
DEFAULT_GATES = (None, 0, 30, 50, 70, 99)


def tokens(text):
    text = re.sub(r'\{[^}]+\}', f' {_SLOT_WORD} ', TTS.sub(' ', text))
    return tuple(BREAK if token == ASIDE_BREAK else SLOT if token == _SLOT_WORD else token
                 for token in TOKEN.findall(text.casefold()))


@lru_cache(maxsize=65536)
def words(text):
    return tokens(text)


def grams(tokens, n):
    return Counter(gram for gram in (tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1))
                   if SLOT not in gram)


@lru_cache(maxsize=8192)
def target_grams(target_tokens):
    return {n: grams(target_tokens, n) for n, _ in WEIGHTS}


# Gate scoring penalises unmatched words less than option scoring (0.6): a
# sentence is kept when its words mostly appear in the point's source window.
# Swept over 0.15-0.8 on the 17 broadcasts; 0.3 kept exact-line matches at
# their best while recovering most of the recall a stricter penalty loses.
SEGMENT_MISS = 0.3


def match_score(candidate_tokens, target, miss=0.6):
    """Weighted n-gram matches minus a penalty per unmatched n-gram."""
    value = 0.0
    for n, weight in WEIGHTS:
        candidate = grams(candidate_tokens, n)
        matches = sum((candidate & target[n]).values())
        misses = sum(candidate.values()) - matches
        value += weight * (matches - miss * misses)
    return value


@lru_cache(maxsize=262144)
def option_score(option, target_tokens):
    option_tokens = words(option)
    return match_score(option_tokens, target_grams(target_tokens)) if option_tokens else 0


# --- gate threshold discovery -------------------------------------------------

class _Probe:
    """Shared record of what one random() draw was compared against."""
    __slots__ = ('thresholds', 'converted')

    def __init__(self):
        self.thresholds = set()
        self.converted = False


class _TrackedFloat(float):
    """A draw that records every threshold the renderer compares it with.

    Scaling (``value * 100``) keeps tracking. ``int()`` cannot (an integer
    comparison is invisible), so it marks the draw for a fine search instead.
    """

    def __new__(cls, value, probe, scale=1.0):
        obj = super().__new__(cls, value)
        obj.probe, obj.scale = probe, scale
        return obj

    def _note(self, other):
        if isinstance(other, (int, float)) and not isinstance(other, bool):
            self.probe.thresholds.add(round(float(other) / self.scale, 6))

    def __lt__(self, other): self._note(other); return float(self) < other
    def __le__(self, other): self._note(other); return float(self) <= other
    def __gt__(self, other): self._note(other); return float(self) > other
    def __ge__(self, other): self._note(other); return float(self) >= other

    def __mul__(self, other):
        if isinstance(other, (int, float)) and other:
            return _TrackedFloat(float(self) * other, self.probe, self.scale * other)
        return float(self) * other
    __rmul__ = __mul__

    def __int__(self):
        self.probe.converted = True
        return int(float(self))


class GateTracker:
    """Thresholds seen per coordinate (point kind, stream, call ordinal)."""

    # Every renderer threshold is a multiple of 0.05; a draw used as an
    # integer is searched at that resolution.
    FINE = tuple(range(5, 100, 5))

    def __init__(self):
        self.thresholds = {}
        self.converted = set()
        self.probes = []

    def probe(self, coordinate):
        probe = _Probe()
        self.probes.append((coordinate, probe))
        return probe

    def collect(self):
        for coordinate, probe in self.probes:
            self.thresholds.setdefault(coordinate, set()).update(probe.thresholds)
            if probe.converted:
                self.converted.add(coordinate)
        self.probes = []

    def values(self, coordinate):
        return interval_values(self.thresholds.get(coordinate, ()), coordinate in self.converted)


def _cuts(thresholds, converted):
    cuts = {round(t * 100) for t in thresholds if 0 < t * 100 < 100}
    if converted:
        cuts.update(GateTracker.FINE)
    return [0] + sorted(cuts) + [100]


def _representative(low, high):
    # 0 and 99 for the outer intervals, so a fitted draw keeps its meaning if
    # a threshold is later re-measured.
    return 0 if low == 0 else 99 if high == 100 else (low + high - 1) // 2


def interval_values(thresholds, converted=False):
    """One digit per outcome interval between the compared thresholds."""
    bounds = _cuts(thresholds, converted)
    return [_representative(low, high) for low, high in zip(bounds, bounds[1:])]


def canonical_digit(digit, thresholds, converted=False):
    """The representative digit of the interval holding ``digit``."""
    bounds = _cuts(thresholds, converted)
    for low, high in zip(bounds, bounds[1:]):
        if low <= digit < high:
            return _representative(low, high)
    return digit


# --- fitting RNG and renderer -------------------------------------------------

class FittingRNG:
    def __init__(self, original, choice_target, draws, gate_value, default_gate,
                 coordinate=None, tracker=None, fit_choices=True, log=None):
        self.original, self.draws, self.log = original, draws, log
        self.choice_target = choice_target
        self.gate_value, self.default_gate = gate_value, default_gate
        self.coordinate, self.tracker = coordinate, tracker
        self.fit_choices = fit_choices
        self.calls = 0

    def choice(self, options):
        original_choice = self.original.choice(options)
        fallback_index = options.index(original_choice)
        if not self.fit_choices:
            self.draws.append(fallback_index)
            return original_choice
        scores = [option_score(str(option), self.choice_target) for option in options]
        best = max(scores)
        index = fallback_index if scores[fallback_index] == best else scores.index(best)
        self.draws.append(index)
        return options[index]

    def random(self):
        k = self.calls
        self.calls += 1
        value = self.original.random()
        digit = self.gate_value(k)
        if digit is None:
            digit = int(value * 100) if self.default_gate is None else self.default_gate
        self.draws.append(digit)
        probe = self.tracker.probe(self.coordinate + (k,)) if self.tracker else _Probe()
        if self.log is not None:
            self.log.append((self.draws, len(self.draws) - 1, probe))
        return _TrackedFloat(digit / 100, probe)


def _render_frame():
    frame = sys._getframe(2)
    while frame is not None:
        if frame.f_code.co_name == 'render' and 'lines' in frame.f_locals:
            return frame
        frame = frame.f_back
    return None


class FittingRenderer(NarrativeRenderer):
    """Records each reseed point's draws and the words that point produced.

    ``windows`` supplies token tuples: ``choice(point, owner, key)`` for option
    scoring and ``segment(point, owner, key)`` for gate scoring. ``streams``
    names the streams being fitted; other streams replay their saved draws.
    """

    def __init__(self, data, windows, default_gate=None, plan=None, trial=None,
                 tracker=None, streams=STREAM_NAMES, fit_choices=True):
        self._windows, self._default_gate = windows, default_gate
        self._plan, self._trial, self._tracker = plan or {}, trial, tracker
        self._fit_streams, self._fit_choices = tuple(streams), fit_choices
        self.segments, self.kinds = {}, {}
        self._segment_key = None
        self._random_log = []
        super().__init__(data)

    # The renderer only ever appends to `lines`, so the words a point produced
    # are whatever follows the snapshot taken when it began. Blocks of the play
    # in progress count until they are joined into `lines`.
    def _snapshot(self, frame, include_blocks):
        local = frame.f_locals
        lines = local['lines']
        for line in lines[self._lines_seen:]:
            self._line_tokens.extend(tokens(line))
        self._lines_seen = len(lines)
        blocks = ()
        if include_blocks:
            blocks = tokens('\n'.join(list(local.get('play_text_blocks', ())) +
                                      list(local.get('post_outcome_text', ()))))
        return len(self._line_tokens), blocks

    def _close_segment(self, line_tokens, blocks):
        if self._segment_key is None:
            return
        start_lines, start_blocks = self._segment_start
        tail = list(line_tokens[start_lines:]) + list(blocks)
        common = 0
        for old, new in zip(start_blocks, tail):
            if old != new:
                break
            common += 1
        self.segments[self._segment_key] = tuple(tail[common:])

    def _reseed_for_point(self, owner, point, timestamp, key):
        frame = _render_frame()
        if frame is None:
            self._line_tokens, self._lines_seen = [], 0
            self._segment_start = (0, ())
            self.segments = {}
        else:
            line_count, blocks = self._snapshot(frame, point in ('event', 'play_outcome'))
            self._close_segment(self._line_tokens, blocks)
            self._segment_start = (line_count, blocks)
        self._segment_key = key
        self.kinds[key] = point

        saved = copy.deepcopy(owner.get('commentaryRng', {}).get(point, {}))
        if set(self._fit_streams) == set(STREAM_NAMES):
            # Never fit against draws left over from an earlier candidate.
            owner.setdefault('commentaryRng', {}).pop(point, None)
        super()._reseed_for_point(owner, point, timestamp, key)
        choice_target = self._windows.choice(point, owner, key)
        streams = {name: saved[name] for name in STREAM_NAMES
                   if name not in self._fit_streams and name in saved}
        for name in self._fit_streams:
            streams[name] = []
            setattr(self, f'rng_{name}', FittingRNG(
                getattr(self, f'rng_{name}'), choice_target, streams[name],
                self._gate_lookup(point, key, name), self._default_gate,
                (point, name), self._tracker, self._fit_choices, self._random_log))
        owner.setdefault('commentaryRng', {})[point] = {
            name: streams[name] for name in STREAM_NAMES if name in streams}
        self.rng = self.rng_play

    def _gate_lookup(self, point, key, stream):
        trial, plan = self._trial, self._plan

        def lookup(k):
            if trial is not None and (point, stream, k) in trial:
                return trial[(point, stream, k)]
            return plan.get((key, stream, k))
        return lookup

    def render(self):
        self._random_log = []
        text = super().render()
        self._close_segment(tokens(text), ())
        self._segment_key = None
        # Store each gate draw as its interval's representative digit, so the
        # same outcome is recorded the same way whichever value produced it.
        for draws, index, probe in self._random_log:
            draws[index] = canonical_digit(draws[index], probe.thresholds, probe.converted)
        return text

    def segment_scores(self):
        scores = {}
        for key, segment in self.segments.items():
            window = self._windows.segment(self.kinds[key], None, key)
            scores[key] = match_score(segment, target_grams(window), SEGMENT_MISS)
        return scores


# --- source windows for the full-broadcast ledgers -----------------------------

class LedgerWindows:
    """Source windows from ledger line references.

    Segment windows hold only the words that belong to a point: the transition
    and introduction before a play's first pitch, a pitch's own line(s), and
    the play's result. Option scoring uses the same windows, except that a
    pitch's options see only its own line, as in the original fitter.
    """

    def __init__(self, source_lines, data):
        self.lines = source_lines
        self._choice, self._segment = {}, {}
        plays = data['liveData']['plays']['allPlays']
        first_start = plays[0]['source']['start']
        self._choice['init'] = self._segment['init'] = self._text(0, first_start - 1)
        previous_end = None
        for index, play in enumerate(plays):
            start, end = play['source']['start'], play['source']['end']
            events = play['playEvents']
            event_lines = [event.get('sourceLine') for event in events]
            known = [line for line in event_lines if line]
            first_event = min(known) if known else None
            low = start if previous_end is None or previous_end >= start else previous_end + 1
            if first_event is None:
                segment = self._text(low - 1, end)
            elif first_event - 1 >= low:
                segment = self._text(low - 1, first_event - 1)
            else:
                # Introduction and first pitch share a line: only the words
                # before the delivery belong to the introduction.
                head = source_lines[first_event - 1].split('...', 1)
                segment = tokens(head[0]) if len(head) > 1 else ()
            # Introductions scored against this tight window rather than the
            # old five lines around the start: +1.0 word overlap, +1.2 5-gram.
            self._choice[f'play:{index}:start'] = self._segment[f'play:{index}:start'] = segment
            for position, line in enumerate(event_lines):
                key = f'play:{index}:event:{position}'
                if not line:
                    self._choice[key] = self._segment[key] = ()
                    continue
                self._choice[key] = self._text(line - 1, line)
                later = [other for other in event_lines[position + 1:] if other and other > line]
                self._segment[key] = self._text(line - 1, (min(later) - 1) if later else line)
            last_pitch = next((event for event in reversed(events) if event['isPitch']), None)
            outcome_start = last_pitch['sourceLine'] if last_pitch and last_pitch.get('sourceLine') else start
            outcome = self._text(outcome_start - 1, end)
            self._choice[f'play:{index}:outcome'] = self._segment[f'play:{index}:outcome'] = outcome
            previous_end = end

    def _text(self, low, high):
        return tokens('\n'.join(self.lines[max(0, low):max(0, high)]))

    def choice(self, point, owner, key):
        return self._choice.get(key, ())

    def segment(self, point, owner, key):
        return self._segment.get(key, ())


class AlignedWindows:
    """Segment windows for a reference that has no line-level ledger.

    The rendered words are aligned to the source words once. A point's window
    is the source between the last aligned word before its segment and the
    first aligned word after it, so it holds the source's version of that
    stretch, including words the rendering lacks.
    """

    def __init__(self, source_tokens, segments):
        from difflib import SequenceMatcher
        rendered, spans = [], {}
        for key, segment in segments:
            spans[key] = (len(rendered), len(rendered) + len(segment))
            rendered.extend(segment)
        matched = [None] * (len(rendered) + 1)
        matcher = SequenceMatcher(None, source_tokens, rendered, autojunk=False)
        for block in matcher.get_matching_blocks():
            for offset in range(block.size):
                matched[block.b + offset] = block.a + offset
        previous, last = [-1] * (len(rendered) + 1), -1
        for index in range(len(rendered) + 1):
            previous[index] = last
            if matched[index] is not None:
                last = matched[index]
        following, nxt = [len(source_tokens)] * (len(rendered) + 1), len(source_tokens)
        for index in range(len(rendered), -1, -1):
            if matched[index] is not None:
                nxt = matched[index]
            following[index] = nxt
        self._segment = {key: tuple(source_tokens[previous[low] + 1:following[high]])
                         for key, (low, high) in spans.items()}

    def choice(self, point, owner, key):
        return ()

    def segment(self, point, owner, key):
        return self._segment.get(key, ())


class _ChoiceAlignedWindows:
    """Aligned windows used for option scoring as well as gate scoring."""

    def __init__(self, aligned):
        self._segment = aligned._segment

    def choice(self, point, owner, key):
        return self._segment.get(key, ())

    segment = choice


def fit_reference(data, source_text, rounds=2, passes=6):
    """Refit a PBP reference fixture, which has no line-level ledger.

    Its current rendering is aligned to the source to find each point's
    window; the draws are then fitted exactly as for a ledgered broadcast.
    Each further round realigns using the previous round's rendering.
    """
    source_tokens = tokens(source_text)
    current, start = data, None
    for _ in range(rounds):
        replay = FittingRenderer(copy.deepcopy(current), AlignedWindows((), ()), streams=())
        replay.render()
        windows = _ChoiceAlignedWindows(AlignedWindows(source_tokens, list(replay.segments.items())))
        # Later rounds continue from the previous round's gate values; choices
        # are always refitted against the current windows.
        current, text, start = fit_gates(lambda: copy.deepcopy(data), lambda _: windows, source_tokens,
                                         passes=passes, start=start)
    if NarrativeRenderer(copy.deepcopy(current)).render() != text:
        raise ValueError('Fitted draws did not replay through the production renderer')
    return current, text


def game_dice(source_tokens, text):
    """Whole-broadcast trigram Dice overlap (selects the default gate)."""
    source = grams(source_tokens, 3)
    output = grams(tokens(text), 3)
    common = sum((source & output).values())
    return 2 * common / (sum(source.values()) + sum(output.values()) or 1)


def metric_source(source_file, source_bytes):
    """Source text with host asides removed, when the corpus annotates it."""
    text = source_bytes.decode('utf-8')
    path = SOURCE_DIR / source_file if source_file else None
    if path and path.exists() and path.read_bytes() == source_bytes:
        return strip_asides(text, load_asides(path))
    return text


def fit_gates(make_data, windows_for, source_tokens, passes=6, streams=STREAM_NAMES,
              fit_choices=True, defaults=DEFAULT_GATES, start=None):
    """Choose a default gate, then fit every gate draw per point.

    ``make_data()`` returns a fresh Gameday document for each candidate render.
    ``start`` resumes from an earlier result's ``(default, plan)``. Returns the
    fitted document, its rendering and ``(default, plan)``.
    """
    def render(default, plan, trial=None, tracker=None):
        data = make_data()
        renderer = FittingRenderer(data, windows_for(data), default, plan, trial,
                                   tracker, streams, fit_choices)
        return data, renderer.render(), renderer

    if start is None:
        best = None
        for default in defaults:
            _, text, _ = render(default, {})
            score = game_dice(source_tokens, text)
            if best is None or score > best[0]:
                best = score, default
        default, plan = best[1], {}
    else:
        default, plan = start[0], dict(start[1])
    tracker = GateTracker()
    data, text, renderer = render(default, plan, tracker=tracker)
    tracker.collect()
    def discovered():
        return ({c: frozenset(t) for c, t in tracker.thresholds.items()}, frozenset(tracker.converted))

    # Repeat until a pass changes no draw and exposes no new gate or threshold
    # (a changed gate can reveal gates behind it); `passes` caps the loop.
    for _ in range(passes):
        changed = 0
        seen = discovered()
        for coordinate in sorted(tracker.thresholds, key=str):
            point, stream, k = coordinate
            # A gate is searched jointly with the next gate of its stream at
            # the same point, which often decides the form of the sentence the
            # first one turns on (the at-bat recap and its format). Searched
            # alone, neither moves: the recap is never said in the wrong form,
            # and the form never matters while the recap is not said.
            following = (point, stream, k + 1)
            pair = (coordinate, following) if following in tracker.thresholds else (coordinate,)
            base = renderer.segment_scores()
            best_for = {key: (score, tuple(plan.get((key, stream, c[2])) for c in pair))
                        for key, score in base.items() if renderer.kinds.get(key) == point}
            for values in itertools.product(*(tracker.values(c) for c in pair)):
                _, _, trial = render(default, plan, dict(zip(pair, values)), tracker)
                for key, score in trial.segment_scores().items():
                    if key in best_for and score > best_for[key][0] + 1e-9:
                        best_for[key] = (score, values)
            tracker.collect()
            updated = 0
            for key, (_, values) in best_for.items():
                for c, value in zip(pair, values):
                    if value is not None and plan.get((key, stream, c[2])) != value:
                        plan[(key, stream, c[2])] = value
                        updated += 1
            if updated:
                changed += updated
                data, text, renderer = render(default, plan, tracker=tracker)
                tracker.collect()
        if not changed and discovered() == seen:
            break
    return data, text, (default, plan)


def fit_game(ledger, source_bytes, passes=6):
    source_text = metric_source(ledger.get('source_file'), source_bytes)
    source_lines = source_text.splitlines()
    data, text, _ = fit_gates(lambda: compile_game(ledger, source_bytes),
                              lambda data: LedgerWindows(source_lines, data),
                              tokens(source_text), passes=passes)
    # Fitting never supplies any source text to production replay.
    replay = NarrativeRenderer(copy.deepcopy(data)).render()
    if replay != text:
        raise ValueError('Fitted draws did not replay through the production renderer')
    return data, text


def fit_references(numbers=None):
    """Refit the four original PBP reference fixtures."""
    from pbp_comparison import PBP_EXAMPLES, REPOSITORY_ROOT
    from transcript_asides import metric_source_text
    for example in PBP_EXAMPLES:
        if numbers and example.number not in numbers:
            continue
        fixture = REPOSITORY_ROOT / example.fixture_file
        data = json.loads(fixture.read_text())
        source = metric_source_text(REPOSITORY_ROOT / example.target_file)
        fitted, text = fit_reference(data, source)
        fixture.write_text(json.dumps(fitted, indent=2) + '\n')
        (REPOSITORY_ROOT / example.snapshot_file).write_text(text)
        print(f'Fitted {example.fixture_file}', flush=True)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('episodes', nargs='*', type=int, help='Episode numbers (default: all)')
    parser.add_argument('--references', nargs='*', type=int, metavar='N',
                        help='Instead refit the pbp_example reference fixtures (default: all four)')
    args = parser.parse_args()
    if args.references is not None:
        fit_references(args.references)
        return
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(LEDGER_DIR.glob('episode_*.json')):
        ledger = json.loads(path.read_text())
        if args.episodes and ledger['episode'] not in args.episodes:
            continue
        data, text = fit_game(ledger, (SOURCE_DIR / ledger['source_file']).read_bytes())
        (OUTPUT_DIR / path.name).write_text(json.dumps(data, indent=2) + '\n')
        (OUTPUT_DIR / f'{path.stem}.txt').write_text(text)
        print(f'Fitted {path.stem}: {len(ledger["plays"])} observed appearances', flush=True)


if __name__ == '__main__':
    main()
