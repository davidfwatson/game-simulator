from commentary import GAME_CONTEXT
from .helpers import simplify_pitch_type

POS_NUMBERS = {'P': 1, 'C': 2, '1B': 3, '2B': 4, '3B': 5, 'SS': 6, 'LF': 7, 'CF': 8, 'RF': 9}

def build_dp_notation(play):
    """Build DP notation like '6-4-3' from runner credits."""
    if not play:
        return ""
    for runner in play.get('runners', []):
        credits = runner.get('credits', [])
        if len(credits) >= 2:
            positions = []
            for c in credits:
                pos_abbr = c.get('position', {}).get('abbreviation', '')
                num = POS_NUMBERS.get(pos_abbr)
                if num:
                    positions.append(str(num))
            if len(positions) >= 2:
                return '-'.join(positions)
    return ""

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
    elif template_outcome.lower().startswith("grounded into double play") or template_outcome == "Double Play":
        template_outcome = "Double Play"
    elif template_outcome == "Reached on Error":
        template_outcome = "Groundout"
    elif template_outcome == "Popout":
        template_outcome = "Pop Out"

    cat_override = hit_data.get('categoryOverride')
    if cat_override:
        cat = cat_override
    else:
        cat = renderer._get_batted_ball_category(template_outcome, ev, la)

    specific_templates = []
    if 'narrative_templates' in GAME_CONTEXT:
        outcome_templates = GAME_CONTEXT['narrative_templates'].get(template_outcome, {})
        specific_templates = outcome_templates.get(cat, [])
        if not specific_templates:
            specific_templates = outcome_templates.get('default', [])

        # Special handling for 1B unassisted groundouts
        if template_outcome == "Groundout" and fielder_pos == "1B":
            unassisted_templates = outcome_templates.get('unassisted_1b', [])
            if unassisted_templates and renderer.rng_flow.random() < 0.5:
                specific_templates = unassisted_templates

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

    template = None

    direction = ""
    if location_code:
        direction = renderer._get_hit_location(outcome, ev, la, location_code)
    elif outcome in ["Single", "Double", "Triple", "Home Run"]:
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

    # Filter out templates with hardcoded directions that contradict the actual direction
    if direction and specific_templates:
        is_middle = direction in ("up the middle", "to second", "to short")
        filtered = [t for t in specific_templates
                    if "up the middle" not in t or is_middle]
        # Also filter "down the line" templates for non-line directions
        if direction not in ("down the line", "down the first base line", "down the third base line"):
            filtered = [t for t in filtered if "down the" not in t.lower() or "{direction" in t]
        if filtered:
            specific_templates = filtered

    if specific_templates and renderer.rng_flow.random() < 0.8:
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
        'fielder_name': fielder_name or "the fielder",
        'result_outs': result_outs,
        'result_outs_word': result_outs_word,
        'out_context_str': out_context_str,
        'dp_notation': dp_notation
    }

    prefix = f"{connector} " if connector else ""
    force_narrative = template_outcome in ["Groundout", "Flyout", "Pop Out", "Lineout", "Double Play", "Sac Fly"]

    final_description = ""
    if template or (specific_templates and (force_narrative or renderer.rng_flow.random() < 0.8)):
         if not template: template = renderer.rng_play.choice(specific_templates)
         final_description = prefix + template.format(**context)
         # Clean up double spaces when dp_notation is empty
         if not dp_notation:
             final_description = final_description.replace("a  double play", "a double play")
    else:
        phrase, phrase_type = renderer._get_batted_ball_verb(outcome, cat)
        if connector:
            if phrase_type == 'verbs':
                template = renderer.rng_play.choice(GAME_CONTEXT['narrative_strings']['play_by_play_templates'])
                context['verb'] = phrase
                context['verb_capitalized'] = phrase.capitalize()
            else:
                template = renderer.rng_play.choice(GAME_CONTEXT['narrative_strings']['play_by_play_noun_templates'])
                context['noun'] = phrase
                context['noun_capitalized'] = phrase.capitalize()
        else:
            if phrase_type == 'verbs':
                template = renderer.rng_play.choice(GAME_CONTEXT['narrative_strings']['play_by_play_templates'])
                context['verb'] = phrase
                context['verb_capitalized'] = phrase.capitalize()
            else:
                template = renderer.rng_play.choice(GAME_CONTEXT['narrative_strings']['play_by_play_noun_templates'])
                context['noun'] = phrase
                context['noun_capitalized'] = phrase.capitalize()
        final_description = prefix + template.format(**context)

    if outcome in ["Single", "Double", "Triple"]:
         status_str = get_runner_status_string(outcome, batter_name, result_outs, is_leadoff, inning_context, renderer.rng_play)
         if status_str:
             final_description += " " + status_str

    return final_description

def render_steal_event(renderer, event):
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
    elif "Home" in desc:
        base_target = "home"
        base_key = "score"
        prev_base = "3B"

    runner_name = renderer.runners_on_base.get(prev_base)
    if not runner_name:
         runner_name = "The runner"

    if outcome == 'stolen_base':
        renderer.runners_on_base[base_key] = runner_name
        renderer.runners_on_base[prev_base] = None
        throw_desc = renderer.rng_play.choice(GAME_CONTEXT['narrative_strings']['throw_outcome_safe']).format(base=base_target)
        return f"{throw_desc} {runner_name} steals {base_target}."

    elif outcome == 'caught_stealing':
        renderer.runners_on_base[prev_base] = None
        throw_desc = renderer.rng_play.choice(GAME_CONTEXT['narrative_strings']['throw_outcome_out']).format(base=base_target)
        return f"{throw_desc} {runner_name} is caught stealing {base_target}."

    return f"{desc}."
