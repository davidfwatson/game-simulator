"""Where a batted ball went and how hard it was hit, as narratable facts.

Three ``hitData`` fields describe a ball beyond its fielder ``location``:

``hardness``
    ``soft``, ``medium`` or ``hard``: the StatsAPI field of that name.
``depth``
    ``shallow``, ``deep``, ``warning_track`` or ``wall`` (the ball reached
    the wall). An extension field: a real feed implies it through
    ``totalDistance`` and ``coordinates``; the simulator writes it from its
    field model, and a transcript ledger records the hosts' words.
``lane``
    ``left_line``, ``left_center``, ``middle``, ``right_center``,
    ``right_line``, ``left_side`` or ``right_side``. Also an extension field,
    likewise implied by a feed's spray coordinates.

Templates that assert one of these ("all the way to the wall", "hard
grounder", "into the gap") are kept only when the ball supports the claim.
When a ball carries none of the fields its claims are unrestricted, except
under ``strictFacts``, where an unrecorded claim is never made.
"""
import re

HIT_SPOT_FIELDS = ('hardness', 'depth', 'lane')
DEPTHS = ('shallow', 'deep', 'warning_track', 'wall')
LANES = ('left_line', 'left_center', 'middle', 'right_center', 'right_line', 'left_side', 'right_side')
HARDNESS = ('soft', 'medium', 'hard')

CLAIMS = {
    'shallow': re.compile(r'\bshallow\b', re.I),
    'deep': re.compile(r'\bdeep\b|way back|still going back|back, back|a long\b', re.I),
    'warning_track': re.compile(r'warning track', re.I),
    'wall': re.compile(r'\bwall\b|\bfence\b', re.I),
    'corner': re.compile(r'\bcorner\b', re.I),
    'gap': re.compile(r'\bgap\b|\balley\b|splits the outfielders|between them', re.I),
    'line': re.compile(r'\bdown the (?:\w+ )*line\b', re.I),
    'middle': re.compile(r'up the middle|through the middle', re.I),
    'hard': re.compile(r'\bhard\b|hammered|sharply|\bsharp\b|ripped|\bsmash|crushed|belted|scorched|smoked|'
                       r'rocket|\bstung\b|hit well', re.I),
    # Only a ball on the ground finds a hole or squeaks through the infield.
    'ground_path': re.compile(r'\bhole\b|through the infield|squeak\w* through|squeez\w* through|seeing-eye|'
                              r'skips? through|gets? through', re.I),
    'soft': re.compile(r'\bsoft|bloop|blooper|looper|\bflare|dribbler|squibber|\blittle\b|slow roller|'
                       r'\btapped\b|\bnubber|\bpoked\b', re.I),
}
LINE_SIDES = {'left_line': 'left', 'right_line': 'right'}
CENTER_SIDES = {'left_center': 'left', 'right_center': 'right'}


def has_spot_facts(hit_data):
    return any((hit_data or {}).get(name) for name in HIT_SPOT_FIELDS)


def supported_claims(hit_data, outcome):
    """The template claims this ball's recorded facts support."""
    hit_data = hit_data or {}
    depth, lane, hardness = hit_data.get('depth'), hit_data.get('lane'), hit_data.get('hardness')
    category = hit_data.get('categoryOverride')
    supported = set()
    if depth == 'shallow':
        supported.add('shallow')
    elif depth in ('deep', 'warning_track', 'wall'):
        supported.add('deep')
        if depth == 'warning_track':
            supported.add('warning_track')
        if depth == 'wall':
            supported.add('wall')
            if lane in LINE_SIDES:
                supported.add('corner')
    if lane in LINE_SIDES:
        supported.add('line')
    elif lane in CENTER_SIDES:
        supported.add('gap')
    elif lane == 'middle':
        supported.add('middle')
    if hardness in ('hard', 'soft'):
        supported.add(hardness)
    if category in ('bloop', 'soft_liner'):
        supported.add('soft')
    if category == 'deep':
        supported.add('deep')
    if category == 'ground_rule':
        # It bounced over the wall.
        supported.update(('deep', 'wall'))
    if hit_data.get('trajectory') in ('ground_ball', 'bunt_grounder'):
        supported.add('ground_path')
    if outcome == 'Home Run':
        # Every home run is deep and over the wall.
        supported.update(('deep', 'wall'))
    return supported


def template_claims(template):
    return {name for name, pattern in CLAIMS.items() if pattern.search(template)}


def gate_templates(templates, supported):
    """Templates whose claims the ball supports (all claims recorded)."""
    return [template for template in templates if template_claims(template) <= supported]


def spot_direction(hit_data, outcome, direction, direction_noun):
    """Direction phrases for a ball with a recorded depth or lane.

    Returns ``(direction, direction_noun)``; the inputs come back unchanged
    when the ball has neither field. ``direction_noun`` is the bare field
    ("left center") that templates such as "Hit in the air to deep
    {direction_noun}" build on, so it never repeats the depth.
    """
    hit_data = hit_data or {}
    depth, lane = hit_data.get('depth'), hit_data.get('lane')
    trajectory = hit_data.get('trajectory')
    grounder = trajectory in ('ground_ball', 'bunt', 'bunt_grounder')
    if lane in LINE_SIDES:
        side = LINE_SIDES[lane]
        if grounder:
            base = 'third' if side == 'left' else 'first'
            return f'down the {base} base line', f'{side} field'
        return f'down the {side} field line', f'{side} field'
    if lane in CENTER_SIDES:
        side = CENTER_SIDES[lane]
        prefix = ('deep ' if depth in ('deep', 'warning_track', 'wall')
                  else 'shallow ' if depth == 'shallow' else '')
        return f'to {prefix}{side} center', f'{side} center'
    if lane == 'middle':
        if grounder or trajectory == 'line_drive':
            return 'up the middle', 'center field'
        prefix = 'deep ' if depth in ('deep', 'warning_track', 'wall') else ''
        return f'to {prefix}center field', 'center field'
    if lane in ('left_side', 'right_side'):
        side = lane.split('_')[0]
        through = outcome in ('Single', 'Double', 'Triple')
        return (f'through the {side} side' if through else f'to the {side} side'), f'{side} field'
    noun = direction_noun or ''
    if noun.startswith(('deep ', 'shallow ')):
        noun = noun.split(' ', 1)[1]
    if not noun.endswith('field') or grounder:
        return direction, direction_noun
    if depth in ('deep', 'warning_track', 'wall'):
        return f'to deep {noun}', noun
    if depth == 'shallow':
        short = noun.replace(' field', '')
        return f'into shallow {short}', short
    return direction, direction_noun
