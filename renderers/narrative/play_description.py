from commentary import GAME_CONTEXT
from .helpers import simplify_pitch_type

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

def generate_play_description(renderer, outcome, hit_data, pitch_details, batter_name, fielder_pos=None, fielder_name=None, connector=None, result_outs=None, is_leadoff=False, inning_context=""):
    ev = hit_data.get('launchSpeed')
    la = hit_data.get('launchAngle')
    location_code = hit_data.get('location')

    cat = renderer._get_batted_ball_category(outcome, ev, la)

    specific_templates = []
    if 'narrative_templates' in GAME_CONTEXT:
        outcome_templates = GAME_CONTEXT['narrative_templates'].get(outcome, {})
        specific_templates = outcome_templates.get(cat, [])
        if not specific_templates:
            specific_templates = outcome_templates.get('default', [])

        # Special handling for 1B unassisted groundouts
        if outcome == "Groundout" and fielder_pos == "1B":
            unassisted_templates = outcome_templates.get('unassisted_1b', [])
            if unassisted_templates and renderer.rng_flow.random() < 0.5:
                specific_templates = unassisted_templates

        # Special handling for Pitcher comebacker groundouts
        if outcome == "Groundout" and fielder_pos == "P":
            pitcher_templates = outcome_templates.get('pitcher_groundout', [])
            if pitcher_templates and renderer.rng_flow.random() < 0.5:
                specific_templates = pitcher_templates

    template = None
    if specific_templates and renderer.rng_flow.random() < 0.8:
        template = renderer.rng_play.choice(specific_templates)

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

    orig_pitch_type = pitch_details.get('type', 'pitch')
    simple_pitch_type = simplify_pitch_type(orig_pitch_type, renderer.rng_pitch)

    result_outs_word = "one"
    if result_outs == 2: result_outs_word = "two"
    elif result_outs == 3: result_outs_word = "three"

    out_context_str = f"for out number {result_outs_word}"
    if result_outs == 3:
        out_context_str = "to end the inning"

    context = {
        'batter_name': batter_name,
        'direction': direction,
        'direction_noun': direction_noun,
        'pitch_type': simple_pitch_type,
        'pitch_type_lower': simple_pitch_type.lower(),
        'pitch_velo': pitch_details.get('velo', 'N/A'),
        'fielder_name': fielder_name or "the fielder",
        'result_outs': result_outs,
        'result_outs_word': result_outs_word,
        'out_context_str': out_context_str
    }

    prefix = f"{connector} " if connector else ""
    force_narrative = outcome in ["Groundout", "Flyout", "Pop Out", "Lineout"]

    final_description = ""
    if template or (specific_templates and (force_narrative or renderer.rng_flow.random() < 0.8)):
         if not template: template = renderer.rng_play.choice(specific_templates)
         final_description = prefix + template.format(**context)
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
