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
        # Sleep Baseball calls it "fastball" essentially every time ("four-seam"
        # appears once in the corpus); letting one pitcher's fastball drift
        # between "Fastball", "Four-seam fastball" and "Heater" read as
        # generated. The draw is kept so the pitch RNG stream doesn't shift.
        rng_pitch.random()
        simplified = "fastball"

    if capitalize:
        return simplified.capitalize()
    return simplified

def resolve_batter_hand(batter_hand, pitcher_hand='R'):
    if batter_hand == 'S':
        return 'R' if pitcher_hand == 'L' else 'L'
    return batter_hand


def get_pitch_location_categories(zone, batter_hand='R'):
    """Describe a pitch's height and side from the catcher's zone grid.

    The center zone and missing/unknown zones carry no location claim. The
    outside zones (11-14) can also describe swinging strikes on chased pitches.
    """
    if not isinstance(zone, int) or isinstance(zone, bool):
        return ()

    categories = []
    if zone in (1, 2, 3, 11, 12):
        categories.append('high')
    elif zone in (7, 8, 9, 13, 14):
        categories.append('low')

    if batter_hand in ('L', 'R') and zone in (1, 4, 7, 11, 13):
        categories.append('outside' if batter_hand == 'L' else 'inside')
    elif batter_hand in ('L', 'R') and zone in (3, 6, 9, 12, 14):
        categories.append('inside' if batter_hand == 'L' else 'outside')
    return tuple(categories)


def get_pitch_type_short(pitch_type):
    """Common broadcast names used in complete pitch and strikeout phrases."""
    lower = pitch_type.lower()
    if lower in ('fastball', 'four-seam fastball', 'four seam fastball', 'heater'):
        return 'heater'
    if lower in ('curveball', 'curve', 'knuckle curve'):
        return 'curve'
    return lower


def get_pitch_type_family(pitch_type):
    lower = pitch_type.lower()
    if lower in ('curveball', 'curve', 'knuckle curve', 'slider', 'slurve'):
        return 'breaking ball'
    return lower


def choose_pitch_description(options, rng_pitch, pitch_type, previous_pitch_type=None, avoid=None):
    """Only describe 'another' pitch when its type matches the previous one."""
    if not previous_pitch_type or get_pitch_type_short(previous_pitch_type) != get_pitch_type_short(pitch_type):
        options = [option for option in options if not option.lower().startswith('another ')]
    choice = rng_pitch.choice(options)
    if choice == avoid and any(option != avoid for option in options):
        # Keep the number of draws stable while avoiding identical location
        # calls on consecutive pitches of the same type.
        index = options.index(choice)
        choice = next(options[(index + offset) % len(options)]
                      for offset in range(1, len(options) + 1)
                      if options[(index + offset) % len(options)] != avoid)
    return choice


def format_pitch_call(description, pitch_type, event_type, strikes_before=0, balls_before=0):
    """Format complete utterances or prefix legacy lowercase fragments.

    Capitalized templates are complete calls, including early broadcast forms
    that omit the pitch name. Parameterized pitch names also mark complete
    calls; older lowercase fragments retain their implicit pitch prefix.
    """
    is_complete = ('{pitch_type' in description or
                   bool(description and description[0].isupper()) or
                   description.startswith(('{ball_call}', '{strike_call}')))
    context = {
        'pitch_type': pitch_type,
        'pitch_type_lower': pitch_type.lower(),
        'pitch_type_short': get_pitch_type_short(pitch_type),
        'pitch_type_family': get_pitch_type_family(pitch_type),
        'strike_call': 'strike three' if strikes_before == 2 else 'a strike',
        'strike_number_word': get_number_word(strikes_before + 1),
        'ball_number_word': get_number_word(balls_before + 1),
        'ball_call': f'ball {get_number_word(balls_before + 1)}',
    }
    description = description.format(**context)
    if is_complete:
        return description
    separator = ' ' if event_type == 'B' else ', '
    return f"{pitch_type}{separator}{description}"


def get_verbal_pitch_location_categories(location):
    """Use the recorded announcer location before any inferred zone geometry."""
    if not isinstance(location, str):
        return None
    if location == 'dirt':
        return ('dirt',)
    if location in ('unlocated', 'middle', 'corner', 'default'):
        return ()
    categories = tuple(part for part in location.split('_')
                       if part in ('low', 'high', 'inside', 'outside'))
    return categories or None


def get_pitch_description_for_location(event_type, zone, pitch_type_simple, rng_pitch,
                                       batter_hand='R', location=None,
                                       previous_pitch_type=None, pitch_description='', avoid=None):
    # Verbal locations retain the production API used by transcript ledgers.
    base_key = 'ball' if event_type == 'B' else 'strike'
    if event_type not in ('B', 'C', 'S'):
        return None
    location_data = GAME_CONTEXT['pitch_locations'].get(base_key, {})
    category = 'default'
    if location in location_data:
        category = location
    elif event_type == 'B':
        if zone in (11, 12, 13, 14) and batter_hand in ('R', 'L'):
            categories = get_pitch_location_categories(zone, batter_hand)
            category = '_'.join(categories)
        else:
            category = 'unlocated' if 'unlocated' in location_data else 'default'
    elif event_type == 'C':
        categories = get_verbal_pitch_location_categories(location)
        if categories is None and zone in range(1, 10):
            categories = get_pitch_location_categories(zone, batter_hand)
        category = categories[0] if categories else 'default'
    options = location_data.get(category, location_data.get('default', []))
    if not options:
        options = location_data.get('default', [])
    # A low quadrant establishes height, not contact with the ground.
    if event_type == 'B' and location != 'dirt' and not any(
            word in pitch_description.lower() for word in ('dirt', 'bounc', 'spik')):
        safe_options = [option for option in options
                        if not any(word in option.lower() for word in ('dirt', 'bounc', 'spik'))]
        # Keep explicit commentary draws at their existing pool positions.
        # Unsupported ground claims fall back to a fact-safe location call.
        if safe_options:
            options = [option if option in safe_options else safe_options[0]
                       for option in options]
    return choose_pitch_description(options, rng_pitch, pitch_type_simple, previous_pitch_type, avoid)
