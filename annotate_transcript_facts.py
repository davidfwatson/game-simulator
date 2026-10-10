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


# --- throws and slides ------------------------------------------------------

BASE_OF = {'first': '1B', 'first base': '1B', 'second': '2B', 'second base': '2B', 'third': '3B',
           'third base': '3B', 'the plate': 'score', 'home': 'score', 'home plate': 'score'}
_BASE = r"(first base|second base|third base|first|second|third|the plate|home plate|home)"
THROW_LATE = re.compile(rf"(?:throw|play|toss) (?:to|at) {_BASE}[^.;]{{0,25}}?\bnot in time|"
                        rf"(?:throw|play|toss)[^.;]{{0,25}}?\bnot in time", re.I)
THROW_BEATEN = re.compile(r"\bbeats? the throw|ahead of the throw", re.I)
NO_THROW = re.compile(rf"\bno (?:play|throw)(?: at {_BASE})?|\bno (?:time|chance) to get\b(?:[^.;]{{0,25}}? at {_BASE})?", re.I)
SLIDE = re.compile(r"\b(?:slides?|sliding|fl(?:y|ies)) in(?:to \w+)? safely(?:,? (?:just )?(under the tag|ahead of the tag|ahead of the throw))?|"
                   r"\bslide in under the tag", re.I)
THROW_IN_TIME = re.compile(r"\bthrow\b[^.;]{0,30}?\b(?<!not )in time\b", re.I)
DOUBLE_PLAY_THROW = re.compile(r"not in time (?:for|to (?:complete|turn)) the double play", re.I)


def throw_facts_from_words(text, movements, batter):
    """{runner name: {'throw', 'slide'}} for the safe runners whose throw or
    slide the hosts state. ``movements`` are the play's ledger movements with
    the batter's (implicit when safe at first). A clause's subject is the
    runner it names, else the one safe at the base it names, else the only
    safe mover; an unresolved clause is left for manual review."""
    text = text.replace(ASIDE_BREAK, ' ')
    safe = [m for m in movements if not m.get('out')]
    found = {}

    def subject(clause, before, base):
        named = [m for m in safe if re.search(rf"\b{re.escape(m['name'].split()[-1])}\b", clause)]
        if len(named) == 1:
            return named[0]
        at_base = [m for m in safe if base and m.get('end') == base]
        if len(at_base) == 1:
            return at_base[0]
        earlier = [m for m in safe if re.search(rf"\b{re.escape(m['name'].split()[-1])}\b", before)]
        if base is None and earlier:
            # "He" is the runner the call named last.
            return max(earlier, key=lambda m: before.rfind(m['name'].split()[-1]))
        movers = [m for m in safe if m.get('start') != m.get('end')]
        return movers[0] if len(movers) == 1 and base is None else None

    for match in re.finditer(r"[^.!?;]+", text):
        clause, before = match.group(), text[:match.start()]
        if DOUBLE_PLAY_THROW.search(clause):
            target = next((m for m in safe if m['name'] == batter), None)
            if target:
                found.setdefault(target['name'], {})['throw'] = 'not_in_time'
            continue
        late, beaten, none, slide = (rx.search(clause) for rx in (THROW_LATE, THROW_BEATEN, NO_THROW, SLIDE))
        if not (late or beaten or none or slide) or re.search(r'\boffline\b', clause, re.I):
            # An offline throw is its own fact, not a late one.
            continue
        base_word = next((g for m in (late, none) if m for g in m.groups() if g), None)
        base = BASE_OF.get(base_word.casefold()) if base_word else None
        target = subject(clause, before, base)
        if target is None:
            continue
        facts = found.setdefault(target['name'], {})
        if slide:
            how = (slide.group(1) or '').casefold()
            facts['slide'] = {'under the tag': 'under_tag', 'ahead of the tag': 'ahead_of_tag'}.get(how, True)
            if 'under the tag' in clause.casefold():
                facts['slide'] = 'under_tag'
        if late:
            facts['throw'] = 'not_in_time'
        elif beaten:
            facts['throw'] = 'not_in_time' if slide else 'beaten'
        elif none:
            facts['throw'] = 'none'
    return found


def record_movements(record):
    """The play's movements, with the batter's when the compiler would add it."""
    from transcript_game_fixtures import HIT_BASES
    movements = list(record.get('runners', []))
    if not any(m['name'] == record['batter'] for m in movements) and HIT_BASES.get(record['outcome']):
        movements.append({'name': record['batter'], 'start': None, 'end': HIT_BASES[record['outcome']]})
    return movements


def annotate_throws(record, lines, report, stem):
    """Throws and slides on a ball in play and on each steal of one play."""
    changed = 0
    pitches = record.get('pitches', [])
    in_play = [pitch for pitch in pitches if pitch['code'] == 'X']
    if in_play:
        call = ball_call('\n'.join(lines[in_play[-1]['line'] - 1:record['source_end']]))
        for name, facts in throw_facts_from_words(call, record_movements(record), record['batter']).items():
            movement = next((m for m in record.get('runners', []) if m['name'] == name and not m.get('out')), None)
            if movement is None:
                # The batter's own movement, explicit so it can carry the fact.
                from transcript_game_fixtures import HIT_BASES
                movement = {'name': name, 'start': None, 'end': HIT_BASES[record['outcome']]}
                record.setdefault('runners', []).append(movement)
            new = {key: value for key, value in facts.items() if key not in movement}
            if new:
                movement.update(new)
                changed += 1
                report.append((stem, record['source_start'], f"throw:{name}", new, call))
    for index, pitch in enumerate(pitches):
        if pitch['code'] != 'A' or pitch.get('eventType') not in ('stolen_base', 'caught_stealing'):
            continue
        later = [other['line'] for other in pitches[index + 1:] if other['line'] > pitch['line']]
        text = '\n'.join(lines[pitch['line'] - 1:(min(later) - 1) if later else max(pitch['line'], record['source_end'])])
        safe = [m for m in pitch.get('runners', []) if not m.get('out')]
        found = throw_facts_from_words(text, safe, None)
        for movement in pitch.get('runners', []):
            # A runner caught stealing: "the throw to second is in time".
            if movement.get('out') and THROW_IN_TIME.search(text.replace(ASIDE_BREAK, ' ')):
                found[movement['name']] = {'throw': 'in_time'}
        for name, facts in found.items():
            movement = next(m for m in pitch['runners'] if m['name'] == name)
            new = {key: value for key, value in facts.items() if key not in movement}
            if new:
                movement.update(new)
                changed += 1
                report.append((stem, pitch['line'], f"steal:{name}", new, text))
    return changed


# --- pitchers entering the game, and the decisions ----------------------------

def pitcher_entry_facts(name, text):
    """A reliever's hand, role and season line from the words that bring him in."""
    last = re.escape(name.split()[-1])
    facts = {}
    hand = re.search(rf"\b(right|left)[- ]hand(?:ed|er)\b[^.]{{0,40}}?\b{last}\b|\b(lefty|righty)\b[^.]{{0,25}}?\b{last}\b|"
                     rf"\b{last} is a[^.]{{0,25}}?\b(right|left)[- ]hand", text, re.I)
    if hand:
        word = next(g for g in hand.groups() if g).casefold()
        facts['pitch_hand'] = 'L' if word.startswith('left') else 'R'
    if re.search(rf"\bcloser,? (?:\w+ ){{0,2}}{last}\b", text, re.I):
        facts['role'] = 'closer'
    elif re.search(rf"\bstarting pitcher,? (?:\w+ ){{0,2}}{last}\b", text, re.I):
        facts['role'] = 'starter'
    season = re.search(rf"\b{last} has pitched (\w+) innings of work this season with an ERA of (\d+\.\d\d)", text, re.I)
    if season and _number(season.group(1)) is not None:
        facts['season'] = {'inningsPitched': f'{_number(season.group(1))}.0', 'era': season.group(2)}
    return facts


DECISION = re.compile(r"(?:gets|takes|picks up|earns|notches) (?:the|another|a) (win|loss|save)\b", re.I)
SENTENCE = re.compile(r"[^.!?]+")


def decisions_from_words(text, pitchers):
    """{'winner' | 'loser' | 'save': name} from "Ron Nancy gets the save"."""
    found = {}
    for sentence in SENTENCE.findall(text.replace(ASIDE_BREAK, ' ')):
        start = 0
        for match in DECISION.finditer(sentence):
            # "A notches another win, B takes the loss, and C gets the save."
            subject = sentence[start:match.start()]
            start = match.end()
            named = [name for name in pitchers if re.search(rf"\b{re.escape(name.split()[-1])}\b", subject)]
            role = {'win': 'winner', 'loss': 'loser', 'save': 'save'}[match.group(1).casefold()]
            if len(named) == 1 and role not in found:
                found[role] = named[0]
    return found


def annotate_pitchers(ledger, lines, report, stem):
    changed = 0
    game, plays = ledger['game'], ledger['plays']
    starters = {game['away_pitcher'], game['home_pitcher']}
    seen, previous_end = set(), 0
    for record in plays:
        name = record['pitcher']
        side = (name, record['top'])
        if side not in seen and name not in starters:
            first = min([pitch['line'] for pitch in record.get('pitches', []) if pitch.get('line')]
                        or [record['source_end']])
            text = ' '.join(lines[previous_end:max(first, record['source_start'])])
            facts = pitcher_entry_facts(name, text)
            new = {}
            if 'pitch_hand' in facts and not any(r.get('pitch_hand') for r in plays if r['pitcher'] == name):
                for other in plays:
                    if other['pitcher'] == name and other['top'] == record['top']:
                        other['pitch_hand'] = facts['pitch_hand']
                new['pitch_hand'] = facts['pitch_hand']
            if 'role' in facts and name not in game.get('pitcher_roles', {}):
                game.setdefault('pitcher_roles', {})[name] = new['role'] = facts['role']
            if 'season' in facts and not game.get('season_stats', {}).get(name, {}).get('pitching'):
                game.setdefault('season_stats', {}).setdefault(name, {})['pitching'] = new['season'] = facts['season']
            if new:
                changed += 1
                report.append((stem, record['source_start'], f'pitcher:{name}', new, text[-260:]))
        seen.add(side)
        previous_end = max(previous_end, record['source_end'])
    if ledger.get('complete'):
        pitchers = list(dict.fromkeys(record['pitcher'] for record in plays))
        found = decisions_from_words(' '.join(lines[previous_end:]), pitchers)
        new = {role: name for role, name in found.items() if role not in game.get('decisions', {})}
        if new:
            game.setdefault('decisions', {}).update(new)
            changed += 1
            report.append((stem, 'postgame', 'decisions', new, ''))
    return changed


# --- the pregame: states, weather, the crew chief ------------------------------

STATES = ('Michigan', 'Wisconsin', 'Minnesota', 'Iowa', 'Illinois', 'Indiana', 'Ohio', 'South Dakota',
          'North Dakota', 'Nebraska')
WIND_FIELDS = {'left center': 'LCF', 'right center': 'RCF', 'left field': 'LF', 'center field': 'CF',
               'right field': 'RF', 'left': 'LF', 'center': 'CF', 'right': 'RF'}
TEMPERATURE = re.compile(r"\b(\d{2,3}) degrees\b", re.I)
WIND = re.compile(r"breeze blowing (in from|out to|in|out)(?: (left center|right center|left field|center field|"
                  r"right field|left|center|right))?\b", re.I)
CREW_CHIEF = re.compile(r"crew chief,? ((?:[A-Z][\w.]*\.? ?){1,3}?),? (?:has signaled|hollers|says|signals|calls)\b")


def pregame_facts(game, lines, pregame_lines):
    """The state each city is in (said anywhere in the broadcast), and the
    pregame's temperature, wind and crew chief."""
    facts = {}
    text = ' '.join(lines)
    for side in ('away', 'home'):
        city = ' '.join(game[side].split()[:-1])
        states = {state for state in STATES if re.search(rf"\b{re.escape(city)}, {state}\b", text)}
        if len(states) == 1:
            facts[f'{side}_state'] = states.pop()
    pregame = ' '.join(pregame_lines).replace(ASIDE_BREAK, ' ')
    temperature, wind, chief = TEMPERATURE.search(pregame), WIND.search(pregame), CREW_CHIEF.search(pregame)
    if temperature:
        weather = {'temp': temperature.group(1)}
        if wind:
            direction = {'in from': 'In From', 'out to': 'Out To', 'in': 'In', 'out': 'Out'}[wind.group(1).casefold()]
            field = WIND_FIELDS.get((wind.group(2) or '').casefold())
            weather['wind'] = f'{direction} {field}' if field and ' ' in direction else direction.split()[0]
        facts['weather'] = weather
    if chief:
        facts['crew_chief'] = chief.group(1).strip()
    return facts


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
        first = ledger['plays'][0]['source_start']
        for key, value in pregame_facts(game, lines, lines[:first - 1]).items():
            if key not in game:
                game[key] = value
                changed += 1
                report.append((path.stem, 'pregame', key, value, ''))
        for record in ledger['plays']:
            changed += annotate_throws(record, lines, report, path.stem)
        changed += annotate_pitchers(ledger, lines, report, path.stem)
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
        units = reference_units(example)
        current = {}
        for unit in units:
            if unit.index == 'postgame':
                pitchers = list(dict.fromkeys(play['matchup']['pitcher']['fullName'] for play in plays))
                ids = {play['matchup']['pitcher']['fullName']: play['matchup']['pitcher']['id'] for play in plays}
                decisions = data['liveData'].setdefault('decisions', {})
                new = {role: {'id': ids[name], 'fullName': name}
                       for role, name in decisions_from_words(unit.text, pitchers).items() if role not in decisions}
                if new:
                    decisions.update(new)
                    changed += 1
                    report.append((example.target_file[:-4], 'postgame', 'decisions',
                                   {role: person['fullName'] for role, person in new.items()}, ''))
                if not decisions:
                    del data['liveData']['decisions']
            if not isinstance(unit.index, int):
                continue
            play = plays[unit.index]
            pitcher, top = play['matchup']['pitcher'], play['about']['isTopInning']
            if top in current and current[top] != pitcher['id']:
                # A reliever's role, from the words that bring him in.
                role = pitcher_entry_facts(pitcher['fullName'], unit.text.replace('\n', ' ')).get('role')
                person = people.get(f"ID{pitcher['id']}", {})
                if role and person and 'pitcherRole' not in person:
                    person['pitcherRole'] = role
                    changed += 1
                    report.append((example.target_file[:-4], unit.index, f"pitcher:{pitcher['fullName']}", {'role': role}, ''))
            current[top] = pitcher['id']
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
            # Throws and slides, onto the runner's own movement.
            final = {}
            for runner in play['runners']:
                final[runner['details']['runner']['id']] = runner
            movements = [{'name': runner['details']['runner']['fullName'], 'start': runner['movement'].get('start'),
                          'end': runner['movement'].get('end'), 'out': runner['movement'].get('isOut'),
                          'details': runner['details']} for runner in final.values()]
            batter = play['matchup']['batter']['fullName']
            for name, facts in throw_facts_from_words(call, movements, batter).items():
                details = next(m['details'] for m in movements if m['name'] == name and not m['out'])
                new = {key: value for key, value in facts.items() if key not in details}
                if new:
                    details.update(new)
                    changed += 1
                    report.append((example.target_file[:-4], unit.index, f'throw:{name}', new, call))
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
