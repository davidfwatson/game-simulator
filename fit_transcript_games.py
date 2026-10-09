"""Select reachable commentary draws for reviewed full-game fixtures.

This offline authoring pass searches actual phrase options offered by the
production renderer. The resulting fixture contains integers, not a transcript
or a renderer override. It is a starting point for reviewed wording alignment.
"""
import copy
import json
import re
from collections import Counter
from functools import lru_cache

from renderers import NarrativeRenderer
from renderers.randomness import STREAM_NAMES
from transcript_game_fixtures import LEDGER_DIR, OUTPUT_DIR, SOURCE_DIR, compile_game


@lru_cache(maxsize=32768)
def words(text):
    return tuple(re.findall(r'\w+', re.sub(r'\{[^}]+\}', ' ', text).casefold()))


def grams(tokens, n):
    return Counter(tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1))


class FittingRNG:
    def __init__(self, original, target, draws, gate):
        self.original, self.draws, self.gate = original, draws, gate
        tokens = words(target)
        self.target_grams = {n: grams(tokens, n) for n in (1, 2, 3)}

    def choice(self, options):
        original_choice = self.original.choice(options)
        def score(option):
            tokens = words(str(option))
            if not tokens:
                return 0
            value = 0
            for n, weight in ((1, 1), (2, 3), (3, 6)):
                candidate = grams(tokens, n)
                matches = sum((candidate & self.target_grams[n]).values())
                misses = sum(candidate.values()) - matches
                value += weight * (matches - 0.6 * misses)
            return value
        scores = [score(option) for option in options]
        best = max(scores)
        fallback_index = options.index(original_choice)
        index = fallback_index if scores[fallback_index] == best else scores.index(best)
        self.draws.append(index)
        return options[index]

    def random(self):
        value = self.original.random()
        digit = int(value * 100) if self.gate is None else self.gate
        self.draws.append(digit)
        return digit / 100


class FittingRenderer(NarrativeRenderer):
    def __init__(self, data, source_lines, gate):
        self._source_lines, self._gate = source_lines, gate
        super().__init__(data)

    def _reseed_for_point(self, owner, point, timestamp, key):
        # Never fit against draws left over from an earlier candidate.
        owner.setdefault('commentaryRng', {}).pop(point, None)
        super()._reseed_for_point(owner, point, timestamp, key)
        if point == 'init':
            stop = self.gameday_data['liveData']['plays']['allPlays'][0]['source']['start'] - 1
            target = '\n'.join(self._source_lines[:stop])
        elif point == 'event':
            target = self._source_lines[owner['sourceLine'] - 1]
        else:
            source = owner['source']
            if point == 'play_start':
                target = '\n'.join(self._source_lines[max(0, source['start'] - 4):source['start'] + 1])
            else:
                events = owner['playEvents']
                last_pitch = next((event for event in reversed(events) if event['isPitch']), None)
                start = last_pitch['sourceLine'] if last_pitch else source['start']
                target = '\n'.join(self._source_lines[start - 1:source['end']])
        streams = {name: [] for name in STREAM_NAMES}
        owner['commentaryRng'][point] = streams
        for name in STREAM_NAMES:
            setattr(self, f'rng_{name}', FittingRNG(getattr(self, f'rng_{name}'), target, streams[name], self._gate))
        self.rng = self.rng_play


def fit_game(ledger, source_bytes):
    source_lines = source_bytes.decode('utf-8').splitlines()
    source_grams = grams(words('\n'.join(source_lines)), 3)
    best = None
    for gate in (None, 0, 30, 50, 70, 99):
        data = compile_game(ledger, source_bytes)
        text = FittingRenderer(data, source_lines, gate).render()
        output_grams = grams(words(text), 3)
        common = sum((source_grams & output_grams).values())
        score = 2 * common / (sum(source_grams.values()) + sum(output_grams.values()) or 1)
        if best is None or score > best[0]:
            best = score, data, text
    _, data, text = best
    # Fitting never supplies any source text to production replay.
    replay = NarrativeRenderer(copy.deepcopy(data)).render()
    if replay != text:
        raise ValueError('Fitted draws did not replay through the production renderer')
    return data, text


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(LEDGER_DIR.glob('episode_*.json')):
        ledger = json.loads(path.read_text())
        data, text = fit_game(ledger, (SOURCE_DIR / ledger['source_file']).read_bytes())
        (OUTPUT_DIR / path.name).write_text(json.dumps(data, indent=2) + '\n')
        (OUTPUT_DIR / f'{path.stem}.txt').write_text(text)
        print(f'Fitted {path.stem}: {len(ledger["plays"])} observed appearances')


if __name__ == '__main__':
    main()
