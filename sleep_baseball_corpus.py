"""Conservative, source-linked phrase-component coverage for Sleep Baseball.

This measures isolated pitch/foul/count clauses, not reconstructed games.
Only output emitted by renderer methods counts as supported. Sentence and
delivery boundaries delimit clauses; normalization preserves every word,
its order, repetitions, and numeric spelling.
"""

import argparse
from dataclasses import asdict, dataclass, field
import itertools
import json
from pathlib import Path
import re
import sys

from commentary import GAME_CONTEXT
from renderers.narrative.renderer import NarrativeRenderer
from renderers.randomness import ChoiceRNG
from transcript_asides import metric_source_text


ROOT = Path(__file__).resolve().parent
NUMBER = r'(?:oh|zero|one|two|three|[0-3])'
STRIKE_NUMBER = r'(?:oh|zero|one|two|[0-2])'
COUNT = re.compile(rf'\b({NUMBER})\s*(?:and|-)\s*({STRIKE_NUMBER})\b', re.I)
NUMBER_VALUES = {'oh': 0, 'zero': 0, 'one': 1, 'two': 2, 'three': 3}
PITCH_TYPE = re.compile(
    r'\b(four[- ]seam fastball|two[- ]seam fastball|split[- ]finger(?:ed)? fastball|'
    r'knuckle[- ]curve|curveball|fastball|slider|changeup|sinker|cutter|splitter|'
    r'curve|heater|breaking ball|knuckleball|screwball|slurve)\b', re.I)
SWING = re.compile(r'\b(?:swing and a miss|swung on and missed|cut on (?:it\s*,?\s*)?(?:and\s+)?missed|'
                   r'swings? and misses?|awkward hack|wild hack|swings through|'
                   r'chases? (?:a|an|the))\b', re.I)
CALLED = re.compile(r'\b(?:called (?:a )?strike|strike (?:one|two|three|[123])|'
                    r'for (?:a )?strike|taken for|catches the black|paints the corner)\b', re.I)
BALL = re.compile(r'\b(?:misses|for a ball(?!\s+game)|ball (?:one|two|three|four|[1-4])|'
                  r'does not offer|takes? (?:a|an|the).*?outside)\b', re.I)
LOCATION = re.compile(r'\b(?:low|high|inside|outside|downstairs|upstairs|'
                      r'in the dirt|down and in|down and away|up and in|'
                      r'high and tight|away|wide|at the knees|at the chin)\b', re.I)
OUTCOME = re.compile(r'\b(?:strikes out|down on strikes|out number|'
                     r'first out|second out|third out|end the inning)\b', re.I)
SENTENCE = re.compile(r'[^.!?…]+(?:[.!?…]+|$)')
LIMITATIONS = (
    'Coverage is exact ordered phrase-clause support from renderer components, '
    'not full-game, event-sequence, player, or runner-state reproduction.',
    'Delivery connectors, inning narration, introductions, batted-ball outcomes, '
    'and other commentary are outside the automatic extractor.',
    'Pitch type, count, handedness and verbal location are inferred only when explicit; '
    'tracking zones are never manufactured from words. '
    'Unknown location remains unknown; other missing context is tried across compatible inputs. This is phrase capability, '
    'not verification of the historical pitch.',
    'Case and punctuation are ignored; word order, repetitions, articles and '
    'numeric spelling remain significant. ASR corrections are not counted as exact.',
    'Compound or ambiguous clauses may be conservatively unmatched or omitted. '
    'Uncovered rows retain source file, line, exact substring and inferred inputs.',
)


# (eligible inventory, supported components, supported pitch clauses).
# Counts are rounded down from the corpus scan, independently for every game.
# Pitch floors ensure easy count phrases cannot conceal lost pitch-call support.
# Clauses inside annotated host asides are not eligible (see transcript_asides);
# episode 001's inventory floor dropped from 360 to 355 when three such
# extractor false positives (tendency and delivery talk) left the inventory.
CORPUS_FLOORS = {
    'pbp_example_1.txt': (230, 200, 75),
    'pbp_example_2.txt': (250, 220, 80),
    'pbp_example_3.txt': (200, 110, 35),
    'pbp_example_4.txt': (280, 245, 80),
    'episode_001.txt': (355, 175, 40),
    'episode_005.txt': (270, 125, 45),
    'episode_011.txt': (280, 190, 65),
    'episode_013.txt': (420, 285, 120),
    'episode_020.txt': (300, 250, 95),
    'episode_029.txt': (310, 255, 90),
    'episode_035.txt': (280, 230, 75),
    'episode_037.txt': (300, 265, 90),
    'episode_039.txt': (310, 230, 80),
    'episode_041.txt': (270, 230, 80),
    'episode_045.txt': (310, 235, 80),
    'episode_046.txt': (340, 260, 85),
    'episode_049.txt': (300, 240, 85),
    'episode_050.txt': (200, 165, 60),
    'episode_051.txt': (200, 155, 45),
    'episode_052.txt': (270, 220, 70),
    'episode_053.txt': (250, 215, 75),
}


def normalize_phrase(text):
    """Ignore punctuation/case, without relaxing the source's words or order."""
    return tuple(re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", text.casefold().replace('’', "'")))


def corpus_paths(root=ROOT):
    root = Path(root)
    return sorted(root.glob('pbp_example_*.txt')) + sorted(
        (root / 'transcripts' / 'sleep_baseball').glob('episode_*.txt'))


@dataclass(frozen=True)
class PhraseCandidate:
    source_file: str
    source_line: int
    source_phrase: str
    kind: str
    input: dict
    assertion_scope: str = 'full'


@dataclass
class SourceCoverage:
    source_file: str
    eligible: int = 0
    supported: int = 0
    kinds: dict = field(default_factory=dict)
    uncovered: list = field(default_factory=list)


def _number(word):
    return int(word) if word.isdigit() else NUMBER_VALUES[word.lower()]


def _count(match):
    return (_number(match.group(1)), _number(match.group(2)))


def _pitch_type(text):
    match = PITCH_TYPE.search(text)
    if not match:
        return None
    value = match.group().lower()
    return {'curve': 'Curveball', 'heater': 'Fastball'}.get(value, value.capitalize())


def _code(text, has_delivery=False):
    if re.search(r'\bfoul(?:ed|s)?\b', text, re.I):
        return 'F'
    if SWING.search(text):
        return 'S'
    if CALLED.search(text):
        return 'C'
    if BALL.search(text):
        return 'B'
    if (LOCATION.search(text) and (PITCH_TYPE.search(text) or has_delivery)
            and not re.search(r'\b(?:fly ball|ground ball|grounder|bouncer|roller|'
                              r'line drive|base hit|home run|popped|single|double|triple)\b', text, re.I)):
        return 'B'
    return None


def _strip_delivery(text):
    """Strip only a leading delivery clause; return source substrings intact."""
    # Most broadcasts use ellipses or a sentence boundary. The sentence scanner
    # already separates those. These patterns handle a delivery within a sentence.
    patterns = (
        rf"^(?:And\s+)?(?:here(?:'s| is)\s+)?(?:the\s+)?(?:first\s+|{NUMBER}\s*(?:and|-)\s*{NUMBER}\s+)?pitch(?:\s+from\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)?(?:\s+is\s+|\s*[,.:]\s*)",
        r"^(?:And\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*'s pitch\s*[,.:]\s*",
    )
    for pattern in patterns:
        match = re.match(pattern, text)
        if match:
            return text[match.end():].strip()
    return text.strip()


def pitch_clause(text):
    """Leading pitch clause of a complete strikeout, with scope made explicit."""
    return re.split(r',\s+and\s+|\.\s+', text, maxsplit=1, flags=re.I)[0].strip(' .,!')


def _count_tail(text):
    """Separate an explicit resulting count, retaining its full wording."""
    matches = list(COUNT.finditer(text))
    if not matches:
        return text, None, None
    match = matches[-1]
    if text[match.end():].strip(' .,!'):
        return text, None, None
    before = text[:match.start()]
    # A count in a delivery prefix is not a resulting-count tail.
    if re.search(r'\b(?:pitch|from)\s*$', before, re.I):
        return text, None, None
    cue = re.search(
        r"(?:(?i:(?:\band\s+)?(?:\bit's\s+|\b(?:the\s+)?count\s+(?:is\s+|even(?:s up)?\s+at\s+)))|"
        r'\b(?i:and\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+falls behind\s*,?\s*)$', before)
    start = cue.start() if cue else match.start()
    prefix = text[:start].rstrip(' ,.!')
    tail = text[start:].strip(' .,!')
    if prefix and not cue and not re.search(r'[,.;]\s*$', before):
        return text, None, None
    return prefix, tail, _count(match)


def _infer_input(phrase, code, line, before_count=None):
    data = {'code': code, 'pitch_type': _pitch_type(phrase),
            'balls': before_count[0] if before_count else None,
            'strikes': before_count[1] if before_count else None,
            'batter_hand': None, 'zone': None}
    hand = re.search(r"\bhe'll bat (left|right)\b|\bbatting (left|right)\b", line, re.I)
    if hand:
        data['batter_hand'] = 'L' if 'left' in hand.group().lower() else 'R'
    lower = phrase.lower()
    locations = []
    if re.search(r'\b(?:low|downstairs|down and|at the knees|in the dirt)\b', lower):
        locations.append('low')
    if re.search(r'\b(?:high|upstairs|up and|at the chin)\b', lower):
        locations.append('high')
    if re.search(r'\b(?:inside|(?:low|high|down|up) and in|high and tight)\b', lower):
        locations.append('inside')
    if re.search(r'\b(?:outside|away|wide)\b', lower):
        locations.append('outside')
    data['location'] = None
    if not ({'low', 'high'} <= set(locations) or {'inside', 'outside'} <= set(locations)):
        data['location'] = '_'.join(locations) or None
    if code == 'C' and re.search(r'\b(?:corner|black|edge)\b', lower):
        side = next((s for s in ('inside', 'outside') if s in locations), None)
        data['location'] = f'{side}_corner' if side else 'corner'
    if code == 'C' and re.search(r'\b(?:middle|main street)\b', lower):
        data['location'] = 'middle'
    if 'in the dirt' in lower:
        data['description'] = 'Swinging Strike (in the dirt)' if code == 'S' else 'Ball (in the dirt)'
        data['location'] = 'dirt'
    if lower.startswith('another ') and data['pitch_type']:
        data['previous_pitch_type'] = data['pitch_type']
    numbered = re.search(r'\bstrike (one|two|three|[123])\b', lower)
    if numbered and code in ('C', 'S'):
        data['strikes'] = _number(numbered.group(1)) - 1
    return data


def _source_full_name(surname, text):
    """Resolve compound count-call surnames only from a name in the source."""
    if ' ' not in surname:
        return surname, None
    discourse = {'And', 'The', 'So', 'But', 'Here', 'His', 'For', 'Tonight', 'After',
                 'Before', 'Against', 'Right', 'Left', 'Pitcher', 'Starting'}
    pattern = re.compile(r'\b([A-Z][a-z]+)\s+' + re.escape(surname) + r'\b')
    for line_number, line in enumerate(text.splitlines(), 1):
        for match in pattern.finditer(line):
            if match.group(1) not in discourse:
                return match.group(), line_number
    return surname, None


def extract_phrases(text, source_file):
    """Extract conservative pitch/foul/count candidates in original line order."""
    candidates = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith('[TTS SPLIT'):
            continue
        delivery = bool(re.search(r'\bpitch\b|\b(?:deals|delivers|winds and fires)\b', line, re.I))
        counts = list(COUNT.finditer(line))
        first_delivery = re.search(r'\bpitch\b|\.{3}|…', line, re.I)
        before = next((_count(m) for m in counts if first_delivery and m.start() < first_delivery.end()), None)
        previous_code = None
        for sentence in SENTENCE.finditer(line):
            fragment = sentence.group().strip(' .!?…')
            body = _strip_delivery(fragment)
            phrase, count_tail, resulting = _count_tail(body)
            code = _code(phrase, delivery)
            if code and phrase:
                kind = 'foul' if code == 'F' else 'pitch'
                inputs = _infer_input(phrase, code, line, before)
                scope = 'full'
                # Compare only the named leading pitch clause; outcome accuracy
                # is deliberately outside this component report.
                if code == 'S' and OUTCOME.search(phrase):
                    phrase = pitch_clause(phrase)
                    kind, scope = 'strikeout', 'pitch_clause'
                    inputs['strikes'] = 2
                candidates.append(PhraseCandidate(source_file, line_number, phrase, kind, inputs, scope))
                previous_code = code
            if count_tail and resulting and (code or previous_code or delivery):
                inputs = {'code': code or previous_code or 'B', 'balls': resulting[0], 'strikes': resulting[1]}
                name = re.search(r'\b(?:and\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+falls behind', count_tail)
                if name and name.group(1).lower() != 'he':
                    surname = name.group(1).removeprefix('And ')
                    inputs['pitcher_name'], name_line = _source_full_name(surname, text)
                    if name_line is not None:
                        inputs['pitcher_name_source_line'] = name_line
                candidates.append(PhraseCandidate(source_file, line_number, count_tail, 'count', inputs))
    return candidates


class _ChoiceRNG(ChoiceRNG):
    """Record dynamic pools while replaying real explicit commentary draws."""
    def __init__(self, index=0, random_value=0.99):
        super().__init__([], seed=0)
        self.index, self.random_value = index, random_value
        self.pool_sizes = []

    def choice(self, options):
        self.pool_sizes.append(len(options))
        self.draws += (self.index,)
        return super().choice(options)

    def random(self):
        self.draws += (round(self.random_value * 100),)
        return super().random()


def _renderer(index=0, random_value=0.99, inputs=None):
    inputs = inputs or {}
    renderer = object.__new__(NarrativeRenderer)
    renderer.base_seed = 0
    renderer.gameday_data = {'gameData': {'players': {'ID1': {
        'lastName': inputs.get('batter_last_name', '__BATTER__')}}}}
    renderer.rng_pitch = _ChoiceRNG(index, random_value)
    renderer.rng_play = _ChoiceRNG(index, random_value)
    renderer.rng_flow = _ChoiceRNG(index, random_value)
    renderer.rng_color = _ChoiceRNG(index, random_value)
    renderer.rng = renderer.rng_play
    renderer.last_foul_phrase = ''
    renderer.consecutive_fouls = inputs.get('consecutive_fouls') or 0
    return renderer


def _contexts(inputs):
    pitch_type = inputs.get('pitch_type')
    types = ([pitch_type] if pitch_type and pitch_type.lower() != 'breaking ball' else
             ['Curveball', 'Slider'] if pitch_type else ['Fastball', 'Curveball', 'Slider', 'Changeup'])
    hands = [inputs['batter_hand']] if inputs.get('batter_hand') else ['R', 'L']
    balls = [inputs['balls']] if inputs.get('balls') is not None else range(4)
    strikes = [inputs['strikes']] if inputs.get('strikes') is not None else range(3)
    for pitch_type, hand, b, s in itertools.product(types, hands, balls, strikes):
        yield pitch_type, hand, b, s, inputs.get('zone'), inputs.get('location')


def render_case_variants(case):
    """Emit actual component variants for an extracted or curated input case.

    There is no source-text passthrough: source phrases never enter renderer
    inputs. Every returned string comes from a renderer component method.
    """
    if isinstance(case, PhraseCandidate):
        case = asdict(case)
    kind, inputs = case['kind'], case['input']
    scope = case.get('assertion_scope', 'full')
    for key, maximum in (('balls', 3), ('strikes', 2)):
        value = inputs.get(key)
        if value is not None and (type(value) is not int or not 0 <= value <= maximum):
            return set()
    if kind == 'strikeout' and inputs.get('result_outs', 1) not in (1, 2, 3):
        return set()
    variants = set()
    contexts = [None] if kind in ('count', 'foul') else _contexts(inputs)
    for context in contexts:
        index, total = 0, 1
        while index < total:
            renderer = _renderer(index, inputs=inputs)
            if kind == 'count':
                text = renderer._get_count_call(inputs['balls'], inputs['strikes'], inputs.get('code', 'B'),
                                                inputs.get('pitcher_name', '__PITCHER__'),
                                                inputs.get('batter_name', '__BATTER__'))
            elif kind == 'foul':
                text = renderer._get_foul_description()
            else:
                pitch_type, hand, balls, strikes, zone, location = context
                event = {'details': {'code': inputs['code'], 'zone': zone,
                                     'location': location,
                                     'description': inputs.get('description', '')},
                         'count': {'balls': balls, 'strikes': strikes}}
                if kind == 'strikeout':
                    outs = inputs.get('result_outs', 1)
                    out_context = 'to end the inning' if outs == 3 else f'for out number {("one", "two", "three")[outs - 1]}'
                    text = renderer._get_location_strikeout_description(
                        event, pitch_type, inputs.get('batter_name', '__BATTER__'), out_context, hand, 1)
                else:
                    text = renderer._get_pitch_call(event, pitch_type, hand, inputs.get('previous_pitch_type'))
            if text:
                variants.add(pitch_clause(text) if scope == 'pitch_clause' else text)
            sizes = (renderer.rng_pitch.pool_sizes + renderer.rng_play.pool_sizes +
                     renderer.rng_flow.pool_sizes + renderer.rng_color.pool_sizes)
            total = max([total] + sizes)
            index += 1
    if kind == 'foul' and (inputs.get('consecutive_fouls') is None or inputs['consecutive_fouls'] >= 1):
        repeat_inputs = dict(inputs, consecutive_fouls=max(inputs.get('consecutive_fouls') or 0, 1))
        renderer = _renderer(random_value=0.0, inputs=repeat_inputs)
        variants.add(renderer._get_foul_description())
    return variants


def measure_corpus(root=ROOT):
    root = Path(root)
    reports, cache = [], {}
    for path in corpus_paths(root):
        source = path.relative_to(root).as_posix()
        report = SourceCoverage(source)
        text = metric_source_text(path, root, root / 'transcript_asides')
        for candidate in extract_phrases(text, source):
            key = (candidate.kind, json.dumps(candidate.input, sort_keys=True), candidate.assertion_scope)
            if key not in cache:
                cache[key] = {normalize_phrase(v) for v in render_case_variants(candidate)}
            supported = normalize_phrase(candidate.source_phrase) in cache[key]
            report.eligible += 1
            report.supported += supported
            counts = report.kinds.setdefault(candidate.kind, {'eligible': 0, 'supported': 0})
            counts['eligible'] += 1
            counts['supported'] += supported
            if not supported:
                report.uncovered.append(asdict(candidate))
        reports.append(report)
    return reports


def check_corpus(reports):
    """Check independently recorded inventory and support floors for every source."""
    failures = []
    indexed = {}
    for report in reports:
        name = Path(report.source_file).name
        if name in indexed:
            failures.append(f'{report.source_file}: duplicate source inventory entry')
        indexed[name] = report
    for name, (eligible_min, supported_min, pitch_min) in CORPUS_FLOORS.items():
        if name not in indexed:
            failures.append(f'{name}: missing source inventory entry')
            continue
        report = indexed[name]
        values = ((report.eligible, eligible_min, 'eligible clauses'),
                  (report.supported, supported_min, 'supported components'),
                  (report.kinds.get('pitch', {}).get('supported', 0), pitch_min, 'supported pitch clauses'))
        for actual, minimum, label in values:
            if actual < minimum:
                failures.append(f'{report.source_file}: {label} {actual} below floor {minimum}')
    return failures


def report_corpus(root=ROOT, *, uncovered_limit=3, output=None, reports=None):
    output = output or sys.stdout
    reports = measure_corpus(root) if reports is None else reports
    print('Sleep Baseball phrase-component coverage (exact ordered clauses):', file=output)
    for report in reports:
        percentage = 100 * report.supported / report.eligible if report.eligible else 0
        print(f'  {report.source_file}: {report.supported}/{report.eligible} ({percentage:.1f}%)', file=output)
        print('    ' + '; '.join(f"{kind} {counts['supported']}/{counts['eligible']}"
                                for kind, counts in report.kinds.items()), file=output)
        rows = report.uncovered if uncovered_limit is None else report.uncovered[:uncovered_limit]
        for candidate in rows:
            print(f"    uncovered {candidate['source_file']}:{candidate['source_line']} "
                  f"[{candidate['kind']}]: {candidate['source_phrase']}", file=output)
    print(f'Total: {sum(r.supported for r in reports)}/{sum(r.eligible for r in reports)} '
          f'eligible clauses across {len(reports)} sources.', file=output)
    for limitation in LIMITATIONS:
        print(f'  Limit: {limitation}', file=output)
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='Include every uncovered clause and its inferred inputs.')
    parser.add_argument('--uncovered-limit', type=int, default=3, help='Uncovered rows per source; -1 prints all.')
    args = parser.parse_args()
    if args.json:
        reports = measure_corpus()
        print(json.dumps({'scope': 'phrase-component support', 'limitations': LIMITATIONS,
                          'sources': [asdict(r) for r in reports]}, indent=2))
    else:
        report_corpus(uncovered_limit=None if args.uncovered_limit < 0 else args.uncovered_limit)


if __name__ == '__main__':
    main()
