"""How often each template recurs in simulated games: a guard against tells.

Blind judges try to spot the simulated excerpt, and a phrasing that recurs more
often than the hosts ever said it is exactly what they notice. This renders N
simulated games, records every template a commentary pool hands the renderer
(instrumenting ``ChoiceRNG.choice``, so a template is counted once per draw,
whatever its slots were filled with), and reports how often each recurs per
game.

``--check`` compares the templates added from the sources
(``transcript_wording_additions.json``) with the hosts' own rate: a template
the hosts said ``said`` times in the 17 broadcasts may not appear in a
simulated game more often than ``said / 17`` per game allows, with room for
sampling noise. ``--compare`` reports which templates recur more per game in
one run than in another (run the script on the base commit for "before").

    python template_repetition.py --games 50 --json after.json
    python template_repetition.py --compare before.json after.json
    python template_repetition.py --games 50 --check
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EPISODES = 17


def literal(template):
    """The template's longest run of fixed words, casefolded."""
    pieces = re.split(r'\{[^}]*\}|\.\.\.|[.,;:!?]', template)
    return max((' '.join(p.split()) for p in pieces), key=len, default='').casefold()


def clause_values():
    """Phrases filled into another sentence rather than said as one: how many
    out ("one away") and which out ("for out number two"). The renderer used to
    fix each to one phrase without a draw, so a before/after count would
    compare a pool with nothing; every appearance states them, as the hosts do."""
    from commentary import GAME_CONTEXT
    pools = GAME_CONTEXT['narrative_strings']
    return {phrase for key, values in pools.items()
            if key.startswith(('outs_', 'out_context_')) for phrase in values}


def pattern(template):
    """The template as a regex over rendered text: fixed words in order, a
    slot matching anything within the sentence."""
    parts = re.split(r'\{[^}]*\}', template.strip().casefold())
    return re.compile(r'[^.!?\n]*?'.join(re.escape(part) for part in parts))


def record_games(games=50, first_seed=1000):
    """Template -> list of uses per game, over ``games`` simulated games."""
    from baseball import BaseballSimulator
    from renderers import NarrativeRenderer
    from renderers import randomness
    from teams import TEAMS

    keys = sorted(TEAMS)
    pairs = [(away, home) for away in keys for home in keys if away != home]
    uses = []
    original = randomness.ChoiceRNG.choice

    def recording(self, seq):
        option = original(self, seq)
        if isinstance(option, str) and len(literal(option).split()) >= 2 and option not in clause_values():
            current[option] += 1
        return option

    randomness.ChoiceRNG.choice = recording
    try:
        for index in range(games):
            seed = first_seed + index
            away, home = pairs[index % len(pairs)]
            simulator = BaseballSimulator(TEAMS[away], TEAMS[home], game_seed=seed)
            simulator.play_game()
            simulator.gameday_data['gameData']['commentarySeed'] = seed
            current = Counter()
            text = NarrativeRenderer(simulator.gameday_data, seed=seed).render().casefold()
            # A drawn template counts only as often as it reaches the page:
            # some draws are made and then not said.
            uses.append(Counter({template: min(draws, len(pattern(template).findall(text)))
                                 for template, draws in current.items()}))
    finally:
        randomness.ChoiceRNG.choice = original
    templates = set().union(*uses)
    return {template: [game.get(template, 0) for game in uses] for template in templates}


def summarize(per_game):
    games = len(next(iter(per_game.values()), []))
    rows = []
    for template, counts in per_game.items():
        rows.append({'template': template, 'mean': sum(counts) / games, 'max': max(counts),
                     'repeat_games': sum(c >= 2 for c in counts) / games})
    rows.sort(key=lambda r: (-r['mean'], r['template']))
    worst = [max(game[t] for t in per_game) for game in
             ({t: per_game[t][i] for t in per_game} for i in range(games))]
    return {'games': games, 'rows': rows,
            'mean_max_repeats': sum(worst) / games if games else 0}


def additions():
    path = ROOT / 'transcript_wording_additions.json'
    return json.loads(path.read_text()) if path.exists() else []


def allowance(hosts_per_game, games):
    """Most uses per game a template may average: its hosts' rate plus sampling
    noise (three standard errors of a Poisson mean) and a quarter of its rate,
    since a simulated game can offer a situation more often than a broadcast."""
    return 1.25 * hosts_per_game + 3 * math.sqrt(max(hosts_per_game, 0.05) / games) + 0.05


def check(summary):
    by_template = {r['template']: r for r in summary['rows']}
    failures, lines = [], []
    for row in additions():
        hosts = row['said'] / EPISODES
        sim = by_template.get(row['template'], {'mean': 0.0})['mean']
        limit = allowance(hosts, summary['games'])
        lines.append((sim - limit, row['template'], hosts, sim, limit))
        if sim > limit:
            failures.append(f"{row['template']!r}: {sim:.2f} per game, hosts {hosts:.2f} (limit {limit:.2f})")
    lines.sort(reverse=True)
    print(f"Added templates closest to their limit ({summary['games']} games):")
    for _, template, hosts, sim, limit in lines[:15]:
        print(f'  {sim:5.2f}/game (hosts {hosts:4.2f}, limit {limit:4.2f})  {template}')
    return failures


def print_summary(summary, top):
    print(f"{summary['games']} simulated games; the most-repeated template in a game "
          f"is used {summary['mean_max_repeats']:.1f} times on average.")
    print(f'Top {top} templates by uses per game:')
    for r in summary['rows'][:top]:
        print(f"  {r['mean']:5.2f}/game  max {r['max']:2}  repeated in {r['repeat_games']:4.0%} of games  {r['template'][:90]}")


def compare(before, after, top=25):
    b = {r['template']: r for r in before['rows']}
    a = {r['template']: r for r in after['rows']}
    print(f"Most-repeated template per game: {before['mean_max_repeats']:.2f} before, "
          f"{after['mean_max_repeats']:.2f} after")
    print(f'\nTop {top} templates after, with their rate before:')
    print('| Template | Before (/game) | After (/game) | Repeated in (after) |')
    print('|---|---:|---:|---:|')
    for r in after['rows'][:top]:
        old = b.get(r['template'], {}).get('mean', 0.0)
        print(f"| {r['template'][:80]} | {old:.2f} | {r['mean']:.2f} | {r['repeat_games']:.0%} |")
    hosts = {row['template']: row['said'] / EPISODES for row in additions()}
    rises = sorted(((r['mean'] - b.get(t, {}).get('mean', 0.0), t) for t, r in a.items()), reverse=True)
    print('\nLargest rises in uses per game (hosts\' rate where measured):')
    for rise, t in rises[:15]:
        note = f", hosts {hosts[t]:.2f}" if t in hosts else ''
        print(f"  +{rise:.2f}  {b.get(t, {}).get('mean', 0.0):.2f} -> {a[t]['mean']:.2f}{note}  {t[:90]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--games', type=int, default=50)
    parser.add_argument('--top', type=int, default=25)
    parser.add_argument('--json', metavar='PATH', help='write the summary to PATH')
    parser.add_argument('--check', action='store_true', help='fail if an added template outruns the hosts')
    parser.add_argument('--compare', nargs=2, metavar=('BEFORE', 'AFTER'))
    args = parser.parse_args()
    if args.compare:
        before, after = (json.loads(Path(p).read_text()) for p in args.compare)
        compare(before, after, args.top)
        return
    summary = summarize(record_games(args.games))
    if args.json:
        Path(args.json).write_text(json.dumps(summary, indent=1) + '\n')
    print_summary(summary, args.top)
    if args.check:
        failures = check(summary)
        if failures:
            raise SystemExit('Added templates recur more than the hosts said them:\n  ' + '\n  '.join(failures))


if __name__ == '__main__':
    main()
