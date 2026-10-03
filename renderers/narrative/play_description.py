import re
from commentary import GAME_CONTEXT
from .helpers import simplify_pitch_type

POS_NUMBERS = {'P': 1, 'C': 2, '1B': 3, '2B': 4, '3B': 5, 'SS': 6, 'LF': 7, 'CF': 8, 'RF': 9}

def build_dp_notation(play):
    """Build DP notation like '6-4-3' from runner credits.

    Each runner carries its own credit chain (the lead runner 6-4, the batter
    4-3); join them so the relay to first isn't dropped ('5-4' for a 5-4-3).
    """
    if not play:
        return ""
    chains = []
    for runner in play.get('runners', []):
        positions = [str(POS_NUMBERS[c.get('position', {}).get('abbreviation', '')])
                     for c in runner.get('credits', [])
                     if POS_NUMBERS.get(c.get('position', {}).get('abbreviation', ''))]
        if positions:
            chains.append(positions)
    if not chains or max(len(c) for c in chains) < 2:
        return ""
    # Start from the chain whose first fielder doesn't finish another chain,
    # then follow the relay: 6-4 + 4-3 -> 6-4-3.
    ends = {c[-1] for c in chains}
    start = next((c for c in chains if c[0] not in ends or len(chains) == 1), max(chains, key=len))
    notation, rest = list(start), [c for c in chains if c is not start]
    while rest:
        nxt = next((c for c in rest if c[0] == notation[-1]), None)
        if nxt is None:
            break
        notation += nxt[1:]
        rest.remove(nxt)
    return '-'.join(notation)

def get_runner_status_string(outcome, batter_name, result_outs, is_leadoff, inning_context, rng_play):
    key = None
    outcome_lower = outcome.lower()

    if is_leadoff:
         key = f"leadoff_{outcome_lower}"
    elif result_outs == 0:
         key = f"{outcome_lower}_nobody_out"
    elif result_outs == 1:
         key = f"{outcome_lower}_one_out"
    elif result_outs == 2:
         key = f"two_out_{outcome_lower}"

    if not key:
        return ""

    context = {
        'batter_name': batter_name,
        'inning_context': inning_context
    }

    return rng_play.choice(GAME_CONTEXT['narrative_strings'].get(key, [""])).format(**context)

def strikeout_templates(kind, details, batter_hand):
    """Remove location claims unless the terminal pitch supplies that fact."""
    location = str(details.get('location', ''))
    zone = details.get('zone')
    high = 'high' in location or zone in (1, 2, 3, 11, 12)
    low = 'low' in location or location == 'dirt' or zone in (7, 8, 9, 13, 14)
    outside = 'outside' in location or (batter_hand == 'R' and zone in (12, 14)) or (batter_hand == 'L' and zone in (11, 13))
    dirt = location == 'dirt'
    off_plate = any(x in location for x in ('inside', 'outside', 'dirt')) or zone in (11, 12, 13, 14)
    corner = 'corner' in location or zone in (1, 3, 7, 9)
    result = []
    for template in GAME_CONTEXT['narrative_templates'].get('Strikeout', {}).get(kind, []):
        text = template.lower()
        if ' low ' in text and not low:
            continue
        if ' high ' in text and not high:
            continue
        if 'outside' in text and not outside:
            continue
        if 'dirt' in text and not dirt:
            continue
        if 'out of the zone' in text and not off_plate:
            continue
        if 'corner' in text and not corner:
            continue
        result.append(template)
    return result


def factual_play_category(renderer, outcome, hit_data, pitch_details, fielder_pos, play):
    """Select descriptions that assert a particular recorded fielding sequence."""
    play = play or {}
    runners = play.get('runners', [])
    batter_id = play.get('matchup', {}).get('batter', {}).get('id')
    destination = renderer._batter_safe_destination(play) if play.get('matchup') else None
    outs = [r for r in runners if r.get('movement', {}).get('isOut')]
    runner_outs = [r for r in outs if r.get('details', {}).get('runner', {}).get('id') != batter_id]
    grounder = hit_data.get('trajectory') == 'ground_ball'
    bunt = pitch_details.get('isBunt') or str(hit_data.get('trajectory', '')).startswith('bunt')
    override = hit_data.get('categoryOverride')
    if (outcome == 'Home Run' or (outcome == 'Double' and hit_data.get('hitWall'))) and play.get('result', {}).get('isWalkoff'):
        return 'walkoff'
    if outcome == 'Double':
        if hit_data.get('isGroundRule') or override == 'ground_rule':
            return 'ground_rule'
        if hit_data.get('lostInLights') or override == 'lost_in_lights':
            return 'lost_in_lights'
    if outcome == 'Bunt Ground Out' and fielder_pos == 'P':
        return 'pitcher_groundout'
    if outcome == 'Single':
        if override == 'throwing_error' and destination == 'second' and grounder:
            return 'throwing_error'
        if (hit_data.get('knockedDown') or override == 'infield_knockdown') and grounder and fielder_pos in ('P', '1B', '2B', '3B', 'SS'):
            return 'infield_knockdown'
    if outcome == 'Field Error':
        throwing = any(c.get('credit') == 'throwing_error' for r in runners for c in r.get('credits', [])) or hit_data.get('errorType') == 'throwing'
        if hit_data.get('droppedFly') or override == 'dropped_fly':
            return 'dropped_fly'
        if grounder and not throwing and destination == 'first':
            return 'everybody_safe' if not outs else 'grounder'
    if outcome == 'Forceout' and len(runner_outs) == 1 and grounder:
        runner = runner_outs[0]
        base = runner['movement'].get('outBase')
        positions = [c.get('position', {}).get('abbreviation') for c in runner.get('credits', [])]
        if base == '2B':
            if hit_data.get('forceMechanism') == 'unassisted' and len(positions) == 1 and positions[0] in ('SS', '2B'):
                return 'second_base'
            if hit_data.get('forceMechanism') == 'throw' and len(positions) >= 2 and positions[-1] in ('SS', '2B'):
                return 'second_base_throw'
        if base == '3B' and positions == ['3B'] and hit_data.get('forceMechanism') == 'unassisted':
            return 'third_base'
        if base in ('score', 'home', '4B'):
            return 'home_force'
    if outcome == 'Fielders Choice' and grounder and destination == 'first':
        if any(r['movement'].get('outBase') in ('score', 'home', '4B') for r in runner_outs):
            return 'home_tag'
        if hit_data.get('throwHome') and any(r.get('movement', {}).get('start') == '3B' and r.get('movement', {}).get('end') in ('score', 'home') and not r['movement'].get('isOut') for r in runners):
            return 'home_safe'
    if outcome == 'Double Play' and len(outs) == 2:
        ordered = sorted(outs, key=lambda r: r['movement'].get('outNumber') or 99)
        first, second = ordered
        first_id = first.get('details', {}).get('runner', {}).get('id')
        second_id = second.get('details', {}).get('runner', {}).get('id')
        notation = build_dp_notation(play)
        if grounder and first_id == batter_id and second['movement'].get('outBase') == '2B' and notation in ('3-4', '3-6'):
            return 'first_then_second'
        if grounder and second_id == batter_id and first['movement'].get('outBase') == '2B' and notation in ('6-3', '4-3'):
            return 'unassisted_force'
        if bunt and second_id == batter_id and first['movement'].get('outBase') == '3B' and notation == '2-5-4':
            return 'bunt_third_first'
    return None


def generate_play_description(renderer, outcome, hit_data, pitch_details, batter_name, fielder_pos=None, fielder_name=None, connector=None, result_outs=None, is_leadoff=False, inning_context="", play=None):
    ev = hit_data.get('launchSpeed')
    la = hit_data.get('launchAngle')
    location_code = hit_data.get('location')

    # Normalize outcome for template lookup
    # Strip parenthetical details and descriptive suffixes
    template_outcome = outcome.split('(')[0].strip() if '(' in outcome else outcome
    if template_outcome.startswith("Groundout"):
        template_outcome = "Groundout"
    elif template_outcome.startswith("Flyout"):
        template_outcome = "Flyout"
    elif template_outcome.lower().startswith("grounded into double play") or template_outcome in ("Double Play", "Grounded Into DP"):
        template_outcome = "Double Play"
    elif template_outcome in ("Reached on Error", "Field Error", "Error"):
        template_outcome = "Field Error"
    elif template_outcome == "Popout":
        template_outcome = "Pop Out"

    is_bunt = (pitch_details.get('isBunt', False)
               or str(hit_data.get('trajectory', '')).lower().startswith('bunt'))
    if template_outcome == 'Groundout' and is_bunt:
        template_outcome = 'Bunt Ground Out'
    cat_override = factual_play_category(renderer, template_outcome, hit_data, pitch_details, fielder_pos, play)
    if not cat_override:
        guarded_categories = {
            'walkoff', 'ground_rule', 'lost_in_lights', 'throwing_error', 'infield_knockdown',
            'dropped_fly', 'everybody_safe', 'second_base', 'third_base',
            'second_base_throw', 'home_tag', 'home_safe', 'first_then_second',
            'unassisted_force', 'bunt_third_first', 'pitcher_groundout',
        }
        supplied_override = hit_data.get('categoryOverride')
        if supplied_override in guarded_categories or (template_outcome == 'Field Error' and supplied_override == 'grounder'):
            supplied_override = None
        cat_override = 'bunt' if template_outcome == 'Single' and is_bunt else supplied_override
    if cat_override:
        cat = cat_override
    elif (template_outcome == 'Single' and hit_data.get('trajectory') == 'line_drive'
          and ev is not None and ev < 90):
        cat = 'soft_liner'
    elif (template_outcome == 'Single' and ev is None
          and hit_data.get('trajectory') in ('ground_ball', 'line_drive', 'fly_ball')
          and renderer.gameday_data.get('gameData', {}).get('broadcast', {}).get('strictFacts')):
        cat = hit_data['trajectory']
    else:
        cat = renderer._get_batted_ball_category(template_outcome, ev, la)
    if (template_outcome == 'Field Error' and cat == 'default'
            and not renderer.gameday_data.get('gameData', {}).get('broadcast', {}).get('strictFacts')):
        # The bare "Jones reaches on an error" with no batted ball read as a
        # gap; describe the ball the fielder misplayed.
        airborne = la is not None and la >= 15 or hit_data.get('trajectory') in ('fly_ball', 'popup', 'line_drive')
        cat = 'air' if airborne else 'grounder'
        if cat == 'air' and fielder_pos in ('P', 'C', '1B', '2B', '3B', 'SS'):
            cat = 'popup_error'

    strict = renderer.gameday_data.get('gameData', {}).get('broadcast', {}).get('strictFacts')
    if (template_outcome == 'Flyout' and fielder_pos in ('P', 'C', '1B', '2B', '3B', 'SS')
            and not strict):
        # An infielder doesn't catch a ball "on the warning track" or "deep to
        # second": a fly ball an infielder catches is a pop-up.
        template_outcome, cat = 'Pop Out', 'default'

    specific_templates = []
    if 'narrative_templates' in GAME_CONTEXT:
        outcome_templates = GAME_CONTEXT['narrative_templates'].get(template_outcome, {})
        specific_templates = outcome_templates.get(cat, [])
        if not specific_templates:
            specific_templates = outcome_templates.get('default', [])

        if template_outcome == 'Double' and cat == 'default' and not strict:
            # 13 of the 18 stock doubles reach the wall or the corner; judges
            # read "roll all the way to the wall" again and again as generated.
            specific_templates = specific_templates + outcome_templates.get('no_wall', []) * 2

        if template_outcome == 'Field Error' and cat == 'everybody_safe':
            specific_templates = specific_templates + outcome_templates.get('grounder', [])
        if template_outcome == 'Field Error' and not hit_data.get('bobbled'):
            specific_templates = [t for t in specific_templates if 'bobble' not in t.lower()]

        # Special handling for 1B unassisted groundouts
        if template_outcome == "Groundout" and fielder_pos == "1B":
            unassisted_templates = outcome_templates.get('unassisted_1b', [])
            strict_facts = renderer.gameday_data.get('gameData', {}).get('broadcast', {}).get('strictFacts')
            method = hit_data.get('putoutMethod')
            if unassisted_templates and (method == 'unassisted' or (not strict_facts and not method and renderer.rng_flow.random() < 0.5)):
                specific_templates = unassisted_templates
            elif strict_facts and method not in ('throw', 'unassisted'):
                specific_templates = ['Grounder {direction}. {batter_name} is retired at first {out_context_str}.']

        # Special handling for Pitcher comebacker groundouts
        if template_outcome == "Groundout" and fielder_pos == "P":
            pitcher_templates = outcome_templates.get('pitcher_groundout', [])
            if pitcher_templates and renderer.rng_flow.random() < 0.5:
                specific_templates = pitcher_templates

        # Filter Pop Out templates: "on the infield" only for infield fielders
        if template_outcome == "Pop Out" and fielder_pos in ("LF", "CF", "RF"):
            specific_templates = [t for t in specific_templates if "on the infield" not in t]
            if not specific_templates:
                specific_templates = outcome_templates.get('default', [])

    fact_limited = (renderer.gameday_data.get('gameData', {}).get('broadcast', {}).get('strictFacts')
                    and not location_code)
    if fact_limited:
        specific_templates = GAME_CONTEXT.get('unlocated_contact', {}).get(template_outcome, specific_templates)
    template = None

    direction = ""
    if location_code:
        direction = renderer._get_hit_location(outcome, ev, la, location_code)
    elif not fact_limited and outcome in ["Single", "Double", "Triple", "Home Run"]:
        direction = renderer._get_hit_location(outcome, ev, la)
    elif fielder_pos:
        direction = GAME_CONTEXT['hit_directions'].get(fielder_pos, "")

    direction_noun = direction
    if direction == "up the middle":
        direction_noun = "center field"
    elif direction == "through the right side":
        direction_noun = "right field"
    elif direction == "through the left side":
        direction_noun = "left field"
    elif direction == "fair":
        direction_noun = "the outfield"
    elif direction.startswith("to "):
        direction_noun = direction[3:]
    elif direction.startswith("into shallow "):
         direction_noun = direction[13:]
    elif direction.startswith("into "):
         direction_noun = direction[5:]

    infield_nouns = {'P': 'the mound', '1B': 'first', '2B': 'second', '3B': 'third', 'SS': 'short'}
    if (template_outcome in ('Groundout', 'Double Play', 'Grounded Into DP', 'Forceout', 'Field Error')
            and fielder_pos in infield_nouns and direction_noun.endswith('field')
            and not renderer.gameday_data.get('gameData', {}).get('broadcast', {}).get('strictFacts')):
        # "Hard grounder to center field. Thorne is up with it and tosses to first"
        direction_noun = infield_nouns[fielder_pos]
        if direction.endswith('field'):
            direction = 'to ' + direction_noun

    # Strip "deep " prefix to avoid "deep deep center field" in templates
    if direction_noun.startswith("deep "):
        direction_noun = direction_noun[5:]

    # For Pop Outs, preserve "shallow" prefix from shallow outfield directions
    if template_outcome in ["Pop Out"] and direction.startswith("into shallow "):
        direction_noun = "shallow " + direction_noun

    # Map infield positions to side names for pop-up templates
    side_map = {"first": "right", "second": "right", "third": "left", "short": "left"}
    if template_outcome in ["Pop Out"] and direction_noun in side_map:
        direction_noun = side_map[direction_noun]

    if (direction and specific_templates and not strict and ('center' in direction or 'middle' in direction)
            and 'left' not in direction and 'right' not in direction):
        # A ball to center doesn't "end up all the way in the corner".
        specific_templates = [t for t in specific_templates if 'corner' not in t] or specific_templates

    # Filter out templates with hardcoded directions that contradict the actual direction
    if direction and specific_templates:
        is_middle = direction in ("up the middle", "to second", "to short")
        filtered = [t for t in specific_templates
                    if "up the middle" not in t or is_middle]
        # Also filter "down the line" templates for non-line directions
        if direction not in ("down the line", "down the first base line", "down the third base line"):
            filtered = [t for t in filtered if "down the" not in t.lower() or "{direction" in t]
        # Line directions are already prepositional phrases, not field names.
        # Keep "deep down the line" templates, but avoid "deep to down the
        # line" and "to deep down the line" from field-noun templates.
        if direction.startswith("down "):
            filtered = [t for t in filtered
                        if "deep to {direction_noun}" not in t
                        and "deep {direction_noun}" not in t]
        if filtered:
            specific_templates = filtered

    # Highlight-reel plays are rare: two "spectacular catch"es in three
    # innings read as a template firing. Keep them ~25 balls in play apart.
    renderer._balls_in_play = getattr(renderer, '_balls_in_play', 0) + 1
    if specific_templates and not strict:
        highlight = re.compile(r'spectacular|diving|leaping|great pick|backhanded|on the warning track', re.I)
        if renderer._balls_in_play - getattr(renderer, '_last_highlight', -99) < 25:
            specific_templates = [t for t in specific_templates if not highlight.search(t)] or specific_templates
    if specific_templates and not strict:
        # A blooper doesn't carry to the corner for a triple, and the man who
        # stepped on the bag for the force doesn't then fire to second.
        specific_templates = [t for t in specific_templates
                              if not (template_outcome == 'Triple' and t.startswith('Blooper'))
                              and 'for the force. He fires to second' not in t] or specific_templates

    if specific_templates and (cat == "bunt" or renderer.rng_flow.random() < 0.8):
        template = renderer.rng_play.choice(specific_templates)

    orig_pitch_type = pitch_details.get('type', 'pitch')
    simple_pitch_type = simplify_pitch_type(orig_pitch_type, renderer.rng_pitch)

    result_outs_word = "one"
    if result_outs == 2: result_outs_word = "two"
    elif result_outs == 3: result_outs_word = "three"

    out_context_str = f"for out number {result_outs_word}"
    if result_outs == 3:
        out_context_str = "to end the inning"

    dp_notation = build_dp_notation(play) if play and template_outcome == "Double Play" else ""

    batter_last_name = batter_name.split()[-1] if batter_name else "the batter"

    context = {
        'batter_name': batter_name,
        'batter_last_name': batter_last_name,
        'direction': direction,
        'direction_noun': direction_noun,
        'pitch_type': simple_pitch_type,
        'pitch_type_lower': simple_pitch_type.lower(),
        'pitch_velo': pitch_details.get('velo', 'N/A'),
        'fielder_name': fielder_name or _position_noun(hit_data, direction) or "the fielder",
        'result_outs': result_outs,
        'result_outs_word': result_outs_word,
        'out_context_str': out_context_str,
        'dp_notation': dp_notation
    }

    prefix = f"{connector} " if connector else ""
    force_narrative = fact_limited or template_outcome in ["Groundout", "Flyout", "Pop Out", "Lineout", "Double Play", "Sac Fly", "Field Error", "Forceout", "Fielders Choice"]

    final_description = ""
    if template or (specific_templates and (force_narrative or renderer.rng_flow.random() < 0.8)):
         if not template: template = renderer.rng_play.choice(specific_templates)
         final_description = prefix + template.format(**context)
         if re.search(r'spectacular|diving|leaping|great pick|backhanded|on the warning track', template, re.I):
             renderer._last_highlight = renderer._balls_in_play
         # Clean up double spaces when dp_notation is empty
         if not dp_notation:
             final_description = final_description.replace("a  double play", "a double play")
    else:
        verb_outcome = template_outcome
        if verb_outcome not in GAME_CONTEXT['statcast_verbs']:
            # Outcomes like a fielder's choice have no verb list of their own;
            # the generic fallback verb was literally "describes".
            verb_outcome = {'ground_ball': 'Groundout', 'line_drive': 'Lineout', 'fly_ball': 'Flyout',
                            'popup': 'Pop Out'}.get((hit_data or {}).get('trajectory'), 'Groundout')
        phrase, phrase_type = renderer._get_batted_ball_verb(verb_outcome, cat)
        if phrase_type == 'verbs':
            template = renderer.rng_play.choice(GAME_CONTEXT['narrative_strings']['play_by_play_templates'])
            context['verb'] = phrase
            context['verb_capitalized'] = phrase.capitalize()
        else:
            template = renderer.rng_play.choice(GAME_CONTEXT['narrative_strings']['play_by_play_noun_templates'])
            context['noun'] = phrase
            context['noun_capitalized'] = phrase.capitalize()
        final_description = prefix + template.format(**context)

    final_description = final_description.replace("a diving the ", "the diving ")
    # "over the head of a leaping the center fielder"
    final_description = re.sub(r"\ba (leaping|sliding|charging|backpedaling|lunging) the ", r"the \1 ", final_description)
    # "Bouncer to back to the mound"
    final_description = re.sub(r"\b(to|into) back to the mound", "back to the mound", final_description)
    if (re.search(r'\b(wall|corner)\b', final_description) and 'shallow ' in final_description
            and not renderer.gameday_data.get('gameData', {}).get('broadcast', {}).get('strictFacts')):
        # "Hammered into shallow left... roll all the way to the wall"
        final_description = final_description.replace('shallow ', '')
    if (fielder_pos == '1B' and template_outcome == 'Groundout'
            and not renderer.gameday_data.get('gameData', {}).get('broadcast', {}).get('strictFacts')):
        # The first baseman can't throw to himself: it's a toss to the pitcher covering (3-1).
        final_description = re.sub(r'\b(fires|throws|flips|tosses|shovels|underhands|lobs)( it)? to first\b',
                                   r'\1\2 to the pitcher covering first', final_description, count=1)
    # A template that starts a sentence with {fielder_name} ("the fielder
    # racing back") needs a capital.
    final_description = re.sub(r'([.!?] )(the )', lambda m: m.group(1) + 'The ', final_description)

    if template_outcome == 'Field Error' and 'error' not in final_description.lower():
        final_description += f" An error by {fielder_name or 'the fielder'}."

    if outcome in ["Single", "Double", "Triple"]:
         status_str = get_runner_status_string(outcome, batter_name, result_outs, is_leadoff, inning_context, renderer.rng_play)
         if status_str and batter_name in final_description and batter_name in status_str \
                 and not status_str.startswith(batter_name):
             # "...a base hit for Sam Decker. A two-out base hit for Sam Decker."
             status_str = None
         if status_str:
             if batter_name in final_description and status_str.startswith(batter_name):
                 rest = status_str[len(batter_name):]
                 # "Kramer heading for second" -> keep a name; "He heading" isn't English.
                 status_str = (batter_last_name if rest.startswith(" heading") else "He") + rest
             final_description += " " + status_str

    return final_description

POSITION_NOUNS = {'1': 'the pitcher', '2': 'the catcher', '3': 'the first baseman', '4': 'the second baseman',
                  '5': 'the third baseman', '6': 'the shortstop', '7': 'the left fielder',
                  '8': 'the center fielder', '9': 'the right fielder'}


def _position_noun(hit_data, direction=None):
    """'the center fielder' for an uncredited ball hit to center, else None."""
    location = str((hit_data or {}).get('location') or '')
    if location in POSITION_NOUNS:
        return POSITION_NOUNS[location]
    # Home runs carry no location; the direction phrase still says where.
    text = (direction or '').lower()
    for word, noun in (('center', 'the center fielder'), ('left', 'the left fielder'), ('right', 'the right fielder')):
        if word in text:
            return noun
    return None


def render_steal_event(renderer, event):
    """Render actions from structured movements, never from transcript prose."""
    details = event.get('details', {})
    event_type = details.get('eventType', '')
    movements = details.get('runners')
    if movements is None and 'runner' in details:
        movements = [details]
    if movements is None:
        if renderer.gameday_data.get('gameData', {}).get('broadcast', {}).get('strictFacts'):
            return ''
        return _render_legacy_steal_event(renderer, event)
    if not movements:
        return {'wild_pitch': 'A wild pitch.', 'passed_ball': 'A passed ball.',
                'pickoff_attempt': 'A pickoff attempt.', 'pickoff': 'The runner is picked off.',
                'caught_stealing': 'The runner is caught stealing.', 'stolen_base': 'A stolen base.'}.get(event_type, '')
    base_names = {'1B': 'first', '2B': 'second', '3B': 'third', 'score': 'home', 'home': 'home'}
    lines = []
    for movement in movements:
        origin, target = movement.get('fromBase'), movement.get('toBase')
        # A feed pickoff throw names the base, not the runner: use whoever is
        # standing there.
        name = (movement.get('runner', {}).get('fullName')
                or getattr(renderer, 'runners_on_base', {}).get(origin) or 'the runner')
        lead = name[:1].upper() + name[1:]
        base = base_names.get(target)
        is_out = movement.get('isOut', False)
        if event_type == 'pickoff_attempt' and target and origin and target != origin and not is_out:
            # A pickoff throw that gets away: the runners move up on the error.
            if not lines:
                lines.append("The pickoff throw gets away!")
            lines.append(f'{lead} scores.' if target in ('score', 'home') else f'{lead} takes {base}.')
            if origin in renderer.runners_on_base:
                renderer.runners_on_base[origin] = None
            if target in renderer.runners_on_base:
                renderer.runners_on_base[target] = name
        elif event_type == 'pickoff_attempt':
            if base or origin in base_names:
                lines.append(f'A throw to {base or base_names[origin]}, and {name} gets back safely.')
            else:
                lines.append(f'A pickoff attempt, and {name} gets back safely.')
        elif event_type == 'pickoff':
            where = f' at {base or base_names.get(origin)}' if base or origin in base_names else ''
            lines.append(f'{lead} is picked off{where}.')
        elif event_type == 'caught_stealing':
            if target == origin and base:
                lines.append(f'{lead} is tagged out heading back to {base}.')
            elif base:
                lines.append(f'{lead} is caught stealing {base}.')
            else:
                lines.append(f'{lead} is caught stealing.')
        elif event_type == 'stolen_base':
            lines.append(f'{lead} steals {base}.' if base else f'{lead} steals a base.')
        elif event_type in ('wild_pitch', 'passed_ball'):
            cause = 'wild pitch' if event_type == 'wild_pitch' else 'passed ball'
            if is_out:
                lines.append(f'On a {cause}, {name} is tagged out' + (f' at {base}.' if base else '.'))
            elif target in ('score', 'home'):
                lines.append(f'{lead} scores on a {cause}.')
            elif base:
                lines.append(f'{lead} advances to {base} on a {cause}.')
            else:
                lines.append(f'A {cause}.')
        if event_type != 'pickoff_attempt':
            if origin in renderer.runners_on_base:
                renderer.runners_on_base[origin] = None
            if not is_out and target in renderer.runners_on_base:
                renderer.runners_on_base[target] = name
    return ' '.join(lines)


def _render_legacy_steal_event(renderer, event):
    details = event['details']
    outcome = details['eventType']
    desc = details['description']

    base_target = "second"
    base_key = "2B"
    prev_base = "1B"
    if "3B" in desc:
        base_target = "third"
        base_key = "3B"
        prev_base = "2B"
    elif "2B" in desc:
        pass
    elif "home" in desc.lower():
        base_target = "home"
        base_key = None
        prev_base = "3B"

    runner_name = renderer.runners_on_base.get(prev_base)
    if not runner_name:
         runner_name = "The runner"

    if outcome == 'stolen_base':
        if base_key is not None:
            renderer.runners_on_base[base_key] = runner_name
        renderer.runners_on_base[prev_base] = None
        throw_desc = renderer.rng_play.choice(GAME_CONTEXT['narrative_strings']['throw_outcome_safe']).format(base=base_target)
        return f"{throw_desc} {runner_name} steals {base_target}."

    elif outcome == 'caught_stealing':
        renderer.runners_on_base[prev_base] = None
        throw_desc = renderer.rng_play.choice(GAME_CONTEXT['narrative_strings']['throw_outcome_out']).format(base=base_target)
        return f"{throw_desc} {runner_name} is caught stealing {base_target}."

    return f"{desc}."
