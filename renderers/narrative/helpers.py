from commentary import GAME_CONTEXT

def get_location_phrases(team):
    """Return geographic noun phrases for speech without changing team labels.

    Regions can supply short and state-qualified forms, including articles.
    Legacy/city data keeps the usual locationName and "city, state" wording.
    """
    location = team.get('spokenLocation') or team.get('locationName')
    if not location:
        parts = team.get('name', '').split()
        location = ' '.join(parts[:-1]) if len(parts) > 1 else ' '.join(parts)
    state = team.get('state')
    location_with_state = team.get('spokenLocationWithState') or ', '.join(
        part for part in (location, state) if part
    )
    return {'location': location, 'location_with_state': location_with_state}

def get_ordinal(n):
    words = ["", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth"]
    if 1 <= n <= 9: return words[n]

    ordinals = ["th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th"]
    if 11 <= (n % 100) <= 13: suffix = "th"
    else: suffix = ordinals[n % 10]
    return f"{n}{suffix}"

def get_number_word(n):
    words = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    if 0 <= n <= 9: return words[n]
    return str(n)

def get_spoken_count(balls, strikes, connector="and"):
    nums = ["oh", "one", "two", "three", "four"]
    b_word = nums[balls] if balls < len(nums) else str(balls)
    s_word = nums[strikes] if strikes < len(nums) else str(strikes)

    if connector == "-":
        return f"{b_word}-{s_word}"
    return f"{b_word} {connector} {s_word}"

def get_spoken_score_string(score_a, score_b):
    nums = ["nothing", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]

    def to_word(n):
        if 0 <= n < len(nums): return nums[n]
        return str(n)

    if score_a > score_b:
        lead, trail = score_a, score_b
    else:
        lead, trail = score_b, score_a

    lead_str = to_word(lead)
    trail_str = to_word(trail)

    use_digits = (lead > 2 or trail > 2)
    if use_digits:
        return f"{lead}-to-{trail}"

    if trail == 0:
        return f"{lead_str}-nothing"

    return f"{lead_str}-to-{trail_str}"

def simplify_pitch_type(pitch_type: str, rng_pitch, capitalize=False) -> str:
    simplified = pitch_type
    if pitch_type.lower() == "four-seam fastball":
        r = rng_pitch.random()
        if r < 0.6: simplified = "fastball"
        elif r < 0.7: simplified = "heater"

    if capitalize:
        return simplified.capitalize()
    return simplified

def get_pitch_description_for_location(event_type, zone, pitch_type_simple, rng_pitch, batter_hand='R', location=None, avoid=None):
    # Helper to get description based on zone
    if event_type == 'B':
        base_key = 'ball'
    elif event_type in ['C', 'S']:
        base_key = 'strike'
    else:
        return None

    location_data = GAME_CONTEXT['pitch_locations'].get(base_key, {})

    # Determine category from zone
    category = 'default'
    if event_type == 'B':
        # Zone mapping based on handedness
        # 11: High-Left, 12: High-Right, 13: Low-Left, 14: Low-Right (Catcher's perspective)

        if batter_hand == 'R':
            if zone == 11: category = 'high_inside'
            elif zone == 12: category = 'high_outside'
            elif zone == 13: category = 'low_inside'
            elif zone == 14: category = 'low_outside'
        else: # LHB
            if zone == 11: category = 'high_outside'
            elif zone == 12: category = 'high_inside'
            elif zone == 13: category = 'low_outside'
            elif zone == 14: category = 'low_inside'

    if location in location_data:
        category = location
    options = location_data.get(category, location_data.get('default', []))
    if not options:
        options = location_data.get('default', [])

    choice = rng_pitch.choice(options)
    if choice == avoid and any(option != avoid for option in options):
        # Two pitches in a row with the same phrase ("runs inside", "runs
        # inside") sounds canned. Step to the next different phrase instead
        # of drawing again, so fixture draw streams stay aligned.
        index = options.index(choice)
        choice = next(options[(index + k) % len(options)] for k in range(1, len(options) + 1)
                      if options[(index + k) % len(options)] != avoid)
    return choice
