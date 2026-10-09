"""Representative transcript situations replayed through production commentary.

These cases exercise individual renderer helpers using real words and situations
from Sleep Baseball transcripts. They are not reconstructed full games or a
measurement of whole-transcript similarity. The authoring specs identify an
actual source line, the intended phrase pool, and the helper's real inputs.

Compilation may search probability gates and select an offered target template.
It persists the resulting integer draws. Regression replay uses only production
ChoiceRNG streams installed by GameRenderer._reseed_for_point; it never selects a
template by its text. Case snapshots therefore detect wording, routing, and draw
consumption changes independently of the compiler.
"""

from collections import deque
import copy
import hashlib
import json
from pathlib import Path
import re

from commentary import GAME_CONTEXT
from renderers.narrative.renderer import NarrativeRenderer
from renderers.randomness import STREAM_NAMES

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / 'transcripts' / 'sleep_baseball'
SPEC_DIR = ROOT / 'transcript_cases'
FIXTURE_DIR = ROOT / 'examples' / 'transcript_cases'
SCHEMA_VERSION = 1
METHODS = {
    'pitch_location': '_get_pitch_description_for_location',
    'foul': '_get_foul_description',
    'pitch_connector': '_get_pitch_connector',
    'runner_status': '_get_runner_status_string',
    'play_description': '_generate_play_description',
    'narrative_string': '_get_narrative_string',
    'radio_string': '_get_radio_string',
}
CASE_FIELDS = ('id', 'source_line', 'expected', 'kind', 'pool', 'template', 'inputs')
GATE_VALUES = (0, 20, 30, 40, 50, 60, 70, 80, 99)


def normalized_words(text):
    """Ignore case and punctuation while retaining every word in its order."""
    return re.findall(r'\w+', text.casefold())


def contains_phrase(text, phrase):
    words, needle = normalized_words(text), normalized_words(phrase)
    return bool(needle) and any(words[index:index + len(needle)] == needle
                               for index in range(len(words) - len(needle) + 1))


def episode_number(value):
    if isinstance(value, str) and value.isdigit():
        value = int(value)
    elif isinstance(value, str):
        match = re.fullmatch(r'episode_(\d{3})\.txt', value)
        if match:
            value = int(match.group(1))
    if type(value) is not int or value <= 0:
        raise ValueError(f'Invalid episode number: {value!r}')
    return value


def episode_stem(episode):
    return f'episode_{episode_number(episode):03d}'


def discover_episodes(directory, suffix='.json'):
    """Return the exact numbered catalog; malformed episode filenames fail."""
    episodes = {}
    for path in sorted(Path(directory).glob(f'episode_*{suffix}')):
        match = re.fullmatch(r'episode_(\d{3})' + re.escape(suffix), path.name)
        if not match:
            raise ValueError(f'Invalid episode filename: {path.name}')
        number = episode_number(match.group(1))
        if number in episodes:
            raise ValueError(f'Duplicate episode {number}: {path}')
        episodes[number] = path
    return episodes


def load_specs(source_dir=SOURCE_DIR, spec_dir=SPEC_DIR):
    sources = discover_episodes(source_dir, '.txt')
    specs = discover_episodes(spec_dir)
    if not sources:
        raise ValueError(f'No transcript episodes found in {source_dir}')
    if set(sources) != set(specs):
        raise ValueError(f'Spec catalog differs from transcripts: '
                         f'missing={sorted(set(sources) - set(specs))}, '
                         f'extra={sorted(set(specs) - set(sources))}')
    documents = []
    for number, path in specs.items():
        spec = json.loads(path.read_text())
        if episode_number(spec.get('episode')) != number:
            raise ValueError(f'Episode number does not match {path.name}')
        lines = sources[number].read_text().splitlines()
        validate_spec(spec, lines)
        documents.append((spec, sources[number]))
    return documents


def get_pool(path):
    value = GAME_CONTEXT
    for key in path.split('.'):
        if not isinstance(value, dict) or key not in value:
            raise ValueError(f'Unknown phrase pool: {path}')
        value = value[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f'Phrase pool must be a list of strings: {path}')
    return value


def validate_case_spec(case, source_lines):
    missing = set(CASE_FIELDS + ('source_text',)) - set(case)
    if missing:
        raise ValueError(f'Case is missing fields: {sorted(missing)}')
    case_id = case['id']
    if not isinstance(case_id, str) or not case_id.strip() or '\n' in case_id:
        raise ValueError('Case id must be a nonempty single-line string')
    line_number = case['source_line']
    if type(line_number) is not int or not 1 <= line_number <= len(source_lines):
        raise ValueError(f'{case_id}: source_line must identify a real 1-based line')
    if source_lines[line_number - 1] != case['source_text']:
        raise ValueError(f'{case_id}: source line {line_number} no longer matches source_text')
    if not isinstance(case['expected'], str) or not contains_phrase(case['source_text'], case['expected']):
        raise ValueError(f'{case_id}: expected phrase is not contiguous in the source line')
    if case['kind'] not in METHODS:
        raise ValueError(f'{case_id}: unknown helper kind {case["kind"]!r}')
    if not isinstance(case['inputs'], dict):
        raise ValueError(f'{case_id}: inputs must contain helper keyword arguments')
    if not isinstance(case['pool'], str) or not isinstance(case['template'], str):
        raise ValueError(f'{case_id}: pool and template must be strings')
    if case['template'] not in get_pool(case['pool']):
        raise ValueError(f'{case_id}: target template is missing from {case["pool"]}')
    state = case.get('state', {})
    if not isinstance(state, dict) or set(state) - {'last_foul_phrase', 'consecutive_fouls'}:
        raise ValueError(f'{case_id}: unsupported helper state')
    if 'last_foul_phrase' in state and not isinstance(state['last_foul_phrase'], str):
        raise ValueError(f'{case_id}: last_foul_phrase must be a string')
    if 'consecutive_fouls' in state and (type(state['consecutive_fouls']) is not int or state['consecutive_fouls'] < 0):
        raise ValueError(f'{case_id}: consecutive_fouls must be a nonnegative integer')


def validate_spec(spec, source_lines):
    episode_number(spec.get('episode'))
    cases = spec.get('cases')
    if not isinstance(cases, list) or len(cases) < 3:
        raise ValueError('Each episode requires at least three representative situations')
    ids = []
    for case in cases:
        validate_case_spec(case, source_lines)
        ids.append(case['id'])
    if len(set(ids)) != len(ids):
        raise ValueError(f'Duplicate case ids in episode {spec["episode"]}')


def _new_renderer(state=None):
    renderer = NarrativeRenderer({
        'gameData': {'commentarySeed': 0, 'teams': {
            'home': {'name': 'Home Team'}, 'away': {'name': 'Away Team'},
        }},
        'liveData': {'plays': {'allPlays': []}},
    })
    for name, value in (state or {}).items():
        setattr(renderer, name, value)
    return renderer


def _invoke(renderer, case):
    try:
        result = getattr(renderer, METHODS[case['kind']])(**copy.deepcopy(case['inputs']))
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError(f'{case["id"]}: invalid helper inputs: {error}') from error
    if not isinstance(result, str):
        raise ValueError(f'{case["id"]}: helper returned {result!r} instead of text')
    return result


class _GatePlan:
    def __init__(self, values):
        self.values = values
        self.observed = []

    def next(self):
        index = len(self.observed)
        digit = self.values[index] if index < len(self.values) else 0
        self.observed.append(digit)
        return digit


class _RecordingSelector:
    """Compiler-only selector; never used by regression replay."""

    def __init__(self, template, pool, gate_plan):
        self.template = template
        self.pool = pool
        self.gate_plan = gate_plan
        self.draws = []
        self.selected_target = False

    def choice(self, options):
        if not options:
            raise ValueError('Renderer offered an empty phrase pool')
        # A renderer may filter the target pool for fielding context. Retain
        # that real subset; never offer a template absent from the routed pool.
        target_pool = options is self.pool or all(option in self.pool for option in options)
        if target_pool and self.template in options:
            index = options.index(self.template)
            self.selected_target = True
        else:
            index = 0
        self.draws.append(index)
        return options[index]

    def random(self):
        digit = self.gate_plan.next()
        self.draws.append(digit)
        return digit / 100


def compile_case(case, episode, source_lines):
    """Find offered-template draws once, then verify production replay."""
    validate_case_spec(case, source_lines)
    episode = episode_number(episode)
    target_pool = get_pool(case['pool'])
    plans = deque([()])
    seen = {()}
    attempts = 0
    last_rendered = ''
    reached_target = False
    while plans and attempts < 4096:
        plan = _GatePlan(plans.popleft())
        renderer = _new_renderer(case.get('state'))
        selectors = {name: _RecordingSelector(case['template'], target_pool, plan)
                     for name in STREAM_NAMES}
        for name, selector in selectors.items():
            setattr(renderer, f'rng_{name}', selector)
        renderer.rng = renderer.rng_play
        last_rendered = _invoke(renderer, case)
        selected = any(selector.selected_target for selector in selectors.values())
        reached_target |= selected
        attempts += 1
        if selected and contains_phrase(last_rendered, case['expected']):
            fixture = {field: copy.deepcopy(case[field]) for field in CASE_FIELDS}
            if 'state' in case:
                fixture['state'] = copy.deepcopy(case['state'])
            fixture['commentaryRng'] = {'case': {name: selector.draws for name, selector in selectors.items()}}
            if replay_case(fixture, episode) != last_rendered:
                raise ValueError(f'{case["id"]}: production draw replay differs from compilation')
            return fixture
        # Explore only gates the real helper actually reached. Different branch
        # lengths are handled on the next run; there is no guessed call index.
        observed = tuple(plan.observed)
        for index in range(len(observed)):
            for digit in GATE_VALUES:
                candidate = observed[:index] + (digit,) + observed[index + 1:]
                if candidate not in seen:
                    seen.add(candidate)
                    plans.append(candidate)
    reason = 'target template unreachable through the requested helper/inputs'
    if reached_target:
        reason = f'expected phrase absent from rendered text: {last_rendered!r}'
    raise ValueError(f'{case["id"]}: {reason} ({attempts} gate plans tried)')


def replay_case(case, episode):
    """Replay persisted integers using production RNGs and real helper inputs."""
    streams = case.get('commentaryRng', {}).get('case', {})
    if set(streams) != set(STREAM_NAMES):
        raise ValueError(f'{case["id"]}: fixture must explicitly contain all four RNG streams')
    renderer = _new_renderer(case.get('state'))
    renderer._reseed_for_point(case, 'case', '', f'transcript:{episode_number(episode):03d}:{case["id"]}')
    text = _invoke(renderer, case)
    for name in STREAM_NAMES:
        consumed = getattr(renderer, f'rng_{name}').position
        if consumed != len(streams[name]):
            raise ValueError(f'{case["id"]}: {name} consumed {consumed} draws, '
                             f'fixture contains {len(streams[name])}; regenerate intentionally')
    if not contains_phrase(text, case['expected']):
        raise ValueError(f'{case["id"]}: expected phrase absent from replay: {text!r}')
    return text


def compile_episode(spec, source_path):
    source_path = Path(source_path)
    source_bytes = source_path.read_bytes()
    source_lines = source_bytes.decode('utf-8').splitlines()
    validate_spec(spec, source_lines)
    episode = episode_number(spec['episode'])
    return {
        'schema_version': SCHEMA_VERSION,
        'episode': episode,
        'source_file': source_path.name,
        'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
        'cases': [compile_case(case, episode, source_lines) for case in spec['cases']],
    }


def snapshot_text(fixture):
    blocks = [f'[{case["id"]}]\n{replay_case(case, fixture["episode"])}'
              for case in fixture['cases']]
    return '\n\n'.join(blocks) + '\n'


def validate_compiled_episode(fixture, spec, source_path):
    """Validate provenance, complete case catalog, metadata, and production replay."""
    source_path = Path(source_path)
    source_bytes = source_path.read_bytes()
    validate_spec(spec, source_bytes.decode('utf-8').splitlines())
    if fixture.get('schema_version') != SCHEMA_VERSION or fixture.get('episode') != episode_number(spec['episode']):
        raise ValueError('Fixture schema/episode does not match the authoring spec')
    if fixture.get('source_file') != source_path.name or fixture.get('source_sha256') != hashlib.sha256(source_bytes).hexdigest():
        raise ValueError('Fixture source provenance changed; review and regenerate cases')
    cases = fixture.get('cases', [])
    if [case.get('id') for case in cases] != [case['id'] for case in spec['cases']]:
        raise ValueError('Fixture case catalog differs from the complete authoring spec')
    for compiled, authored in zip(cases, spec['cases']):
        for field in CASE_FIELDS + ('state',):
            if compiled.get(field) != authored.get(field):
                raise ValueError(f'{authored["id"]}: fixture {field} differs from authoring spec')
        replay_case(compiled, fixture['episode'])


def check_catalog(source_dir=SOURCE_DIR, spec_dir=SPEC_DIR, fixture_dir=FIXTURE_DIR):
    documents = load_specs(source_dir, spec_dir)
    fixtures = discover_episodes(fixture_dir)
    snapshots = discover_episodes(fixture_dir, '.txt')
    catalog = {episode_number(spec['episode']) for spec, _ in documents}
    if set(fixtures) != catalog or set(snapshots) != catalog:
        raise ValueError('Persisted fixture/snapshot episode catalogs must exactly match all source episodes')
    counts = {}
    for spec, source in documents:
        episode = episode_number(spec['episode'])
        fixture = json.loads(fixtures[episode].read_text())
        validate_compiled_episode(fixture, spec, source)
        if snapshots[episode].read_text() != snapshot_text(fixture):
            raise ValueError(f'{episode_stem(episode)}: commentary snapshot changed')
        counts[episode] = len(fixture['cases'])
    return counts


if __name__ == '__main__':
    from pbp_comparison import validate_transcript_counts

    try:
        counts = check_catalog()
        validate_transcript_counts(counts)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    for episode, count in counts.items():
        print(f'{episode_stem(episode)}: {count} representative situations passed')
    print(f'{len(counts)} episodes, {sum(counts.values())} cases; representative helper coverage, not full-game reconstruction')
