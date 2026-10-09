"""Annotate batted-ball facts the hosts state: depth, lane and hardness.

An authoring helper like ``annotate_transcript_locations.py``. For every ball
in play it reads the hosts' call of that ball (the in-play pitch's line
through the end of the appearance, host asides removed) and records the
explicit facts in ``hit`` (plus ``categoryOverride: ground_rule`` for a
ground-rule double): ``depth`` (shallow, deep, warning_track, wall),
``lane`` (left_line, left_center, middle, right_center, right_line,
left_side, right_side) and ``hardness`` (soft, hard). Existing values are
kept, contradictory words are skipped for manual review, and nothing is
inferred from a fielder's position alone except which side a "gap" or
"line" is on. The four PBP reference fixtures have no line-level ledger, so
their calls come from the word alignment in ``missed_words.reference_units``
and their facts are written straight into the fixture's ``hitData``.

    python annotate_transcript_facts.py --dry-run     # review table only
    python annotate_transcript_facts.py               # write ledgers + fixtures
"""
import argparse
import json
import re

from transcript_asides import ASIDE_BREAK, metric_source_text
from transcript_game_fixtures import LEDGER_DIR, SOURCE_DIR

SIDE_OF = {'LF': 'left', '3B': 'left', 'SS': 'left', 'RF': 'right', '1B': 'right', '2B': 'right'}


def _has(pattern, text):
    return re.search(pattern, text, re.I) is not None


def ball_call(text):
    """The words about the ball in play: after the last delivery cue."""
    text = text.replace(ASIDE_BREAK, ' ')
    if '...' in text:
        text = text.rsplit('...', 1)[1]
    # A foul earlier on the same line is not this ball.
    return text


def facts_from_words(text, outcome, location, trajectory):
    """Explicit depth, lane and hardness, or None for each."""
    low = text.casefold()
    grounder = trajectory in ('ground_ball', 'bunt') or _has(
        r'\b(?:grounder|ground ball|roller|chopper|bouncer|one-hopper|dribbler|tapper|squibber)\b', low)
    facts = {}
    # --- depth (balls in the air, or hits that reach the outfield) ---
    if outcome != 'Home Run' and not grounder:
        track = _has(r'warning,? track|on the track', low)
        wall = _has(r'\bwall\b|\bfence\b|\bcorner\b', low) and not _has(r'short of the (?:wall|fence)|over the wall', low)
        deep = _has(r'\bdeep\b|way back|still going back', low)
        shallow = _has(r'\bshallow\b', low)
        if shallow and (deep or wall or track):
            pass  # contradictory: review by hand
        elif track:
            facts['depth'] = 'warning_track'
        elif wall:
            facts['depth'] = 'wall'
        elif deep:
            facts['depth'] = 'deep'
        elif shallow:
            facts['depth'] = 'shallow'
    elif outcome != 'Home Run' and _has(r'\bcorner\b|\bwall\b', low) and outcome in ('Double', 'Triple'):
        facts['depth'] = 'wall'
    # --- lane ---
    side_words = [s for s in ('left', 'right') if _has(rf'\b{s}\b', low)]
    side = side_words[0] if len(side_words) == 1 else SIDE_OF.get(location)
    if _has(r'third base line', low):
        facts['lane'] = 'left_line'
    elif _has(r'first base line', low):
        facts['lane'] = 'right_line'
    elif _has(r'down the (?:left|right)[- ]field line|down the line|\b(?:left|right)[- ]field corner|in(?:to)? the corner', low):
        if side:
            facts['lane'] = f'{side}_line'
    elif _has(r'\b(?:left|right)[- ]cent(?:er|re)\b', low):
        facts['lane'] = 'left_center' if _has(r'\bleft[- ]cent', low) else 'right_center'
    elif _has(r'\bgap\b|\balley\b', low) and location in ('LF', 'RF') and side:
        facts['lane'] = f'{side}_center'
    elif _has(r'up the middle|through the middle|straightaway center', low):
        facts['lane'] = 'middle'
    elif _has(r'\b(?:left|right) side\b', low) and len(side_words) == 1:
        facts['lane'] = f'{side_words[0]}_side'
    # --- hardness ---
    hard = _has(r'\bhard\b|hard-hit|hammered|sharply|\bsharp\b|ripped|smoked|scorched|crushed|\brocket|\bstung\b|'
                r'\bsmash|belted', low)
    soft = _has(r'\bsoft|softly|bloop|blooper|looper|\bflare|dribbler|squibber|slow roller|nubber|\btapper|'
                r'\btapped\b|swinging bunt|\bweak', low)
    if hard != soft:
        facts['hardness'] = 'hard' if hard else 'soft'
    if outcome == 'Double' and _has(r'ground[- ]rule', low):
        facts['categoryOverride'] = 'ground_rule'
    return facts


NUMBER_WORDS = {'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,
                'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
                'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20}
RECORD = re.compile(r"record of (\w+) and (\w+)", re.I)
ERA = re.compile(r"(\d\.\d\d) (?:ERA|earned run average)|earned run average of (\d\.\d\d)", re.I)


def _number(word):
    return int(word) if word.isdigit() else NUMBER_WORDS.get(word.casefold())


def season_pitching(lines, pitchers):
    """{name: {'wins', 'losses', 'era'}} from "enters tonight's game with a
    record of 9 and 4 with a 3.86 ERA". The subject is the pitcher this line
    or the line before names (for "He enters...")."""
    found = {}
    for index, line in enumerate(lines):
        record, era = RECORD.search(line), ERA.search(line)
        if not record and not era:
            continue
        stats = {}
        if record and _number(record.group(1)) is not None and _number(record.group(2)) is not None:
            stats.update(wins=_number(record.group(1)), losses=_number(record.group(2)))
        if era:
            stats['era'] = era.group(1) or era.group(2)
        clause = line[:(record or era).start()]
        named = [name for name in pitchers if re.search(rf"\b{re.escape(name.split()[-1])}\b", clause)]
        if not named and index:
            named = [name for name in pitchers if re.search(rf"\b{re.escape(name.split()[-1])}\b", lines[index - 1])]
        if len(named) == 1 and stats and named[0] not in found:
            found[named[0]] = stats
    return found


def ledger_calls(ledger, lines):
    """(record, call text) for every appearance with a ball in play."""
    for record in ledger['plays']:
        in_play = [pitch for pitch in record.get('pitches', []) if pitch['code'] == 'X']
        if not in_play:
            continue
        line = in_play[-1]['line']
        yield record, ball_call('\n'.join(lines[line - 1:record['source_end']]))


def annotate_ledgers(write, report):
    total = 0
    for path in sorted(LEDGER_DIR.glob('episode_*.json')):
        ledger = json.loads(path.read_text())
        lines = metric_source_text(SOURCE_DIR / ledger['source_file']).splitlines()
        changed = 0
        game = ledger['game']
        pitchers = list(dict.fromkeys([game['away_pitcher'], game['home_pitcher']]
                                      + [record['pitcher'] for record in ledger['plays']]))
        stats = game.setdefault('season_stats', {})
        for name, pitching in season_pitching(lines, pitchers).items():
            if name not in stats:
                stats[name] = {'pitching': pitching}
                changed += 1
                report.append((path.stem, 'season', name, pitching, ''))
        if not stats:
            del game['season_stats']
        for index, (record, call) in enumerate(ledger_calls(ledger, lines)):
            hit = record.setdefault('hit', {})
            facts = facts_from_words(call, record['outcome'], hit.get('location'), hit.get('trajectory'))
            new = {key: value for key, value in facts.items() if key not in hit}
            if new:
                hit.update(new)
                changed += 1
                report.append((path.stem, record['source_start'], record['outcome'], new, call))
            if not hit:
                del record['hit']
        total += changed
        if write and changed:
            path.write_text(json.dumps(ledger, indent=2) + '\n')
    return total


def annotate_references(write, report):
    from missed_words import reference_units
    from pbp_comparison import PBP_EXAMPLES, REPOSITORY_ROOT

    total = 0
    for example in PBP_EXAMPLES:
        fixture = REPOSITORY_ROOT / example.fixture_file
        data = json.loads(fixture.read_text())
        plays = data['liveData']['plays']['allPlays']
        changed = 0
        lines = metric_source_text(REPOSITORY_ROOT / example.target_file).splitlines()
        people = data['gameData']['players']
        pitcher_ids = {}
        for side, team in data['liveData']['boxscore']['teams'].items():
            for pid in team.get('battingOrder', []):
                person = people.get(f'ID{pid}', {})
                if person.get('primaryPosition', {}).get('abbreviation') == 'P':
                    pitcher_ids[person['fullName']] = (side, pid)
        for play in plays:
            pitcher = play['matchup']['pitcher']
            side = 'home' if play['about']['isTopInning'] else 'away'
            pitcher_ids.setdefault(pitcher['fullName'], (side, pitcher['id']))
        for name, pitching in season_pitching(lines, list(pitcher_ids)).items():
            side, pid = pitcher_ids[name]
            entry = data['liveData']['boxscore']['teams'][side].setdefault('players', {}).setdefault(
                f'ID{pid}', {'person': {'id': pid, 'fullName': name}})
            season = entry.setdefault('seasonStats', {})
            if not season.get('pitching'):
                season['pitching'] = pitching
                changed += 1
                report.append((example.target_file[:-4], 'season', name, pitching, ''))
        for unit in reference_units(example):
            if not isinstance(unit.index, int):
                continue
            play = plays[unit.index]
            in_play = [event for event in play['playEvents'] if event.get('details', {}).get('code') == 'X']
            if not in_play:
                continue
            hit = in_play[-1].setdefault('hitData', {})
            call = ball_call(unit.text)
            facts = facts_from_words(call, play['result']['event'], hit.get('location'), hit.get('trajectory'))
            new = {key: value for key, value in facts.items() if key not in hit}
            if new:
                hit.update(new)
                changed += 1
                report.append((example.target_file[:-4], unit.index, play['result']['event'], new, call))
        total += changed
        if write and changed:
            fixture.write_text(json.dumps(data, indent=2) + '\n')
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--dry-run', action='store_true', help='print what would be recorded; write nothing')
    parser.add_argument('--references-only', action='store_true')
    parser.add_argument('--ledgers-only', action='store_true')
    args = parser.parse_args()
    report = []
    if not args.references_only:
        print(f'ledgers: {annotate_ledgers(not args.dry_run, report)} balls annotated')
    if not args.ledgers_only:
        print(f'references: {annotate_references(not args.dry_run, report)} balls annotated')
    for source, where, outcome, facts, call in report:
        call = ' '.join(call.split())
        print(f'{source}@{where} {outcome}: {facts} <- {call[:160]}')


if __name__ == '__main__':
    main()
