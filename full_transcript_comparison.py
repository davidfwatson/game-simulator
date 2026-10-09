"""Whole-broadcast and per-appearance wording comparisons for all new games."""
from difflib import SequenceMatcher
import json
import re

from pbp_comparison import compare_transcripts, FULL_TRANSCRIPT_MINIMUMS
from renderers import NarrativeRenderer
from transcript_asides import ASIDE_BREAK, metric_source_text
from transcript_game_fixtures import LEDGER_DIR, OUTPUT_DIR, SOURCE_DIR


def spoken_text(text):
    return re.sub(r'\[TTS SPLIT[^\]]*\]', '', text)


def spoken_words(text):
    """Words in order; a removed aside becomes a token no rendering contains,
    so no ordered-match run can join the words on either side of it."""
    return ['\0' if token == ASIDE_BREAK else token
            for token in re.findall(rf'\w+|{ASIDE_BREAK}', spoken_text(text).casefold())]


def ordered_coverage(target, rendered):
    """Fraction of source words matched in order, without counting TTS tags."""
    source, output = spoken_words(target), spoken_words(rendered)
    matches = SequenceMatcher(None, source, output, autojunk=False).get_matching_blocks()
    words = sum(token != '\0' for token in source)
    return sum(match.size for match in matches) / words if words else 0.0


def compare_game(episode):
    stem = f'episode_{episode:03d}'
    # Host asides are blanked like the between-innings breaks cut from the
    # source, keeping line numbers so ledger ranges still apply.
    source = metric_source_text(SOURCE_DIR / f'{stem}.txt')
    data = json.loads((OUTPUT_DIR / f'{stem}.json').read_text())
    ledger = json.loads((LEDGER_DIR / f'{stem}.json').read_text())
    renderer = NarrativeRenderer(data)
    rendered = renderer.render()
    source_lines, output_lines = source.splitlines(), rendered.splitlines()
    per_play = []
    for index, play in enumerate(ledger['plays']):
        start, end = play['source_start'], play['source_end']
        reference = '\n'.join(source_lines[start-1:end])
        lo, hi = renderer._play_line_map[index]
        actual = '\n'.join(output_lines[lo:hi])
        scores = compare_transcripts(spoken_text(reference), spoken_text(actual))
        per_play.append({'play': index, 'inning': play['inning'], 'top': play['top'],
                         'batter': play['batter'], 'source_start': start, 'source_end': end,
                         'ordered_word_coverage': ordered_coverage(reference, actual),
                         'ngram': scores.ngram, 'target': reference, 'rendered': actual})
    scores = compare_transcripts(spoken_text(source), spoken_text(rendered))
    return {'episode': episode, 'appearances': len(per_play),
            'pitches': sum(event['isPitch'] for play in data['liveData']['plays']['allPlays'] for event in play['playEvents']),
            'jaccard': scores.jaccard, 'ngram': scores.ngram,
            'content_exact': scores.content_lines.exact_fraction,
            'mean_play_word_coverage': sum(p['ordered_word_coverage'] for p in per_play) / len(per_play),
            'plays': per_play}


def game_failures(result):
    """Keep both factual coverage and wording above the reviewed baseline."""
    minimums = FULL_TRANSCRIPT_MINIMUMS[result['episode']]
    failures = []
    for key in ('appearances', 'pitches'):
        if result[key] != minimums[key]:
            failures.append(f"{key}: expected {minimums[key]}, found {result[key]}")
    for key in ('ngram', 'mean_play_word_coverage'):
        if result[key] < minimums[key]:
            failures.append(f"{key}: {result[key]:.2%} is below {minimums[key]:.2%}")
    return failures


def check_full_transcripts():
    expected = {f'episode_{episode:03d}' for episode in FULL_TRANSCRIPT_MINIMUMS}
    for directory, pattern in ((SOURCE_DIR, 'episode_*.txt'), (LEDGER_DIR, 'episode_*.json'),
                               (OUTPUT_DIR, 'episode_*.json'), (OUTPUT_DIR, 'episode_*.txt')):
        actual = {path.stem for path in directory.glob(pattern)}
        if actual != expected:
            raise ValueError(f'Full transcript catalog differs in {directory}: '
                             f'missing {sorted(expected - actual)}, unregistered {sorted(actual - expected)}')
    results = []
    for episode in FULL_TRANSCRIPT_MINIMUMS:
        result = compare_game(episode)
        result['failures'] = game_failures(result)
        results.append(result)
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('episodes', nargs='*', type=int)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--check', action='store_true', help='Fail if coverage or wording falls below reviewed minimums')
    parser.add_argument('--gaps', type=int, metavar='N', help='Show the N least-matched appearances per episode')
    args = parser.parse_args()
    if set(args.episodes) - set(FULL_TRANSCRIPT_MINIMUMS):
        parser.error('Unknown transcript episode')
    if args.episodes:
        results = [compare_game(episode) for episode in args.episodes]
        for result in results:
            result['failures'] = game_failures(result)
    else:
        results = check_full_transcripts()
    if args.json:
        print(json.dumps(results, indent=2))
        return int(args.check and any(result['failures'] for result in results))
    for result in results:
        print(f"episode_{result['episode']:03d}: {result['appearances']} appearances, {result['pitches']} pitches; "
              f"word overlap {result['jaccard']:.1%}, 5-grams {result['ngram']:.1%}, "
              f"exact lines {result['content_exact']:.1%}, per-play ordered words {result['mean_play_word_coverage']:.1%}")
        for failure in result['failures']:
            print('  BELOW MINIMUM: ' + failure)
        if args.gaps:
            for play in sorted(result['plays'], key=lambda item: item['ordered_word_coverage'])[:args.gaps]:
                print(f"  Play {play['play']}, {play['batter']}, source {play['source_start']}-{play['source_end']}: "
                      f"{play['ordered_word_coverage']:.1%} ordered word coverage")
                print('    Target: ' + play['target'].replace('\n', ' '))
                print('    Render: ' + play['rendered'].replace('\n', ' '))
    return int(args.check and any(result['failures'] for result in results))


if __name__ == '__main__':
    raise SystemExit(main())
