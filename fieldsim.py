"""Batted-ball physics on a 2D field.

A batted ball (exit velocity, launch angle, spray angle) is flown with drag
and lift, and the defense plays it: who can get there, whether it's caught or
fielded, whether the throw beats the batter, and how far the batter gets on a
hit. Outcome, fielder, hit location and coordinates all come from the same
calculation, so the gameday data can't say "shallow right" and "stand-up
double" about one ball.

Coordinates are feet with home plate at the origin, +y toward center field
and +x toward right field. Spray angles are degrees off the center line,
negative toward left field; the foul lines are at +/-45.
"""

import math
from dataclasses import dataclass, field

# --- field -----------------------------------------------------------------

FIRST_BASE = (63.64, 63.64)
SECOND_BASE = (0.0, 127.28)
THIRD_BASE = (-63.64, 63.64)

# Standard positions, (distance from home, spray angle).
POSITIONS = {
    'P': (60.5, 0.0),
    'C': (3.0, 0.0),
    '1B': (110.0, 33.0),
    '2B': (148.0, 13.0),
    'SS': (148.0, -13.0),
    '3B': (112.0, -33.0),
    'LF': (295.0, -27.0),
    'CF': (320.0, 0.0),
    'RF': (295.0, 27.0),
}
INFIELD = ('P', 'C', '1B', '2B', 'SS', '3B')
OUTFIELD = ('LF', 'CF', 'RF')


def fence_distance(spray):
    """330 down the lines, 375 in the gaps, 400 to center."""
    a = min(abs(spray), 45.0)
    scale = PARAMS.get('fence_scale', 1.0)
    if a <= 22.5:
        return scale * (400.0 - (400.0 - 375.0) * (a / 22.5))
    return scale * (375.0 - (375.0 - 330.0) * ((a - 22.5) / 22.5))


def polar(dist, spray):
    r = math.radians(spray)
    return dist * math.sin(r), dist * math.cos(r)


def spray_of(x, y):
    return math.degrees(math.atan2(x, y))


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


# --- tunables ----------------------------------------------------------------
# Fit by coordinate descent so that 1,140 real 2026 StatsAPI balls in play
# (their exit velocity and launch angle, with spray drawn the way the
# simulator draws it) come out as the real mix of singles, doubles, triples,
# homers and out types. Fitting to the real fielded coordinates instead
# overfit: hits are recorded where they landed, in the holes. Speeds and reactions are
# effective values: fielders here take perfect routes from fixed spots.

PARAMS = {
    'drag_cd': 0.40,
    'lift_cl': 0.20,          # backspin lift on balls hit in the air
    'of_speed': 19.8,          # ft/s, outfielders
    'if_speed': 14.0,          # ft/s, infielders moving to a ball in the air
    'if_lateral': 13.4,        # ft/s, infielders ranging to a grounder
    'of_react': 0.63,          # s before an outfielder is moving
    'if_react': 0.1,
    'catch_k': 5.55,            # steepness of catch probability vs time to spare
    'catch_bias': -0.14,        # s of slack for a dive/stretch
    'gb_speed_factor': 0.73,   # average grounder speed / exit speed
    'gb_slack': 0.02,          # s: an infielder can be this late and still glove it
    'transfer': 0.58,          # s: glove to release
    'throw_speed': 125.0,      # ft/s
    'of_throw_speed': 115.0,
    'home_to_first': 4.35,     # s, average batter
    'base_to_base': 3.75,
    'roll_line_drive': 0.375,   # roll after landing, as a share of carry
    'roll_fly_ball': 0.0,
    'extra_base_margin': 1.0,  # s: a runner only tries for the next base with this much to spare
    'triple_margin': 0.2,      # s more a runner wants before trying for third
    'wall_carom': 2.1,         # s lost when the ball reaches the wall
    'fence_scale': 1.004,
}

MPH_TO_FPS = 1.4667
LIFT_STEEP_MAX = 1.5


# --- flight ----------------------------------------------------------------

@dataclass
class Flight:
    carry: float        # feet in the air
    hang_time: float    # seconds
    apex: float         # feet
    path: list = field(default_factory=list)  # (horizontal ft, height ft)

    def height_at(self, dist):
        prev = (0.0, 3.0)
        for point in self.path:
            if point[0] >= dist:
                span = point[0] - prev[0] or 1.0
                return prev[1] + (point[1] - prev[1]) * (dist - prev[0]) / span
            prev = point
        return -1.0


def fly(ev_mph, la_deg, params=PARAMS):
    """Integrate a batted ball's flight (SI inside, feet out)."""
    m, r, rho = 0.145, 0.0366, 1.2
    area = math.pi * r * r
    v = ev_mph * 0.44704
    th = math.radians(la_deg)
    vx, vz = v * math.cos(th), v * math.sin(th)
    x, z, t, dt = 0.0, 0.9, 0.0, 0.005
    cl = params['lift_cl'] if la_deg > 8 else 0.0
    if la_deg > 35:
        # Balls hit steeply up come off with more backspin, and on the way up
        # that lift points partly backward: pop-ups carried ~25 ft too far.
        cl *= min(LIFT_STEEP_MAX, 1.0 + (la_deg - 35) / 25.0)
    path, apex = [], z
    while z > 0.0 and t < 12.0:
        speed = math.hypot(vx, vz)
        drag = 0.5 * rho * params['drag_cd'] * area * speed * speed / m
        lift = 0.5 * rho * cl * area * speed * speed / m
        ax = -drag * vx / speed - lift * vz / speed
        az = -9.81 - drag * vz / speed + lift * vx / speed
        vx += ax * dt
        vz += az * dt
        x += vx * dt
        z += vz * dt
        t += dt
        apex = max(apex, z)
        if int(t / dt) % 10 == 0:
            path.append((x * 3.281, z * 3.281))
    return Flight(carry=x * 3.281, hang_time=t, apex=apex * 3.281, path=path)


# --- result ----------------------------------------------------------------

@dataclass
class BattedBall:
    outcome: str            # Single, Double, Triple, Home Run, Groundout, Flyout, Lineout, Pop Out
    fielder: str            # position that fielded / caught / retrieved it
    trajectory: str         # ground_ball, line_drive, fly_ball, popup
    location: str           # renderer hit-direction code
    spray: float
    landing: tuple          # (x, y) where it was caught, fielded or landed
    distance: float
    hang_time: float = 0.0
    caught: bool = False
    # When and where the defense can first throw: the fielded grounder, the
    # catch, or the outfielder picking up a hit. Runner advancement races this.
    release: float = 0.0
    release_point: tuple = None

    @property
    def coordinates(self):
        """Statcast-style hc_x / hc_y."""
        return {'coordX': round(125.42 + self.landing[0] / 2.495, 2),
                'coordY': round(198.27 - self.landing[1] / 2.495, 2)}


def trajectory_of(la):
    if la < 10:
        return 'ground_ball'
    if la <= 25:
        return 'line_drive'
    if la <= 50:
        return 'fly_ball'
    return 'popup'


def _location_code(outcome, spray, dist, trajectory):
    side = 'L' if spray < -15 else 'R' if spray > 15 else 'C'
    if outcome == 'Home Run':
        if abs(spray) > 40:
            return 'DL'
        return {'L': 'DLF', 'C': 'DCF', 'R': 'DRF'}[side]
    if trajectory == 'ground_ball' and dist < 200:
        return {'L': 'LS', 'C': 'MI', 'R': 'RS'}[side]
    if dist < 200 and outcome == 'Single':
        return {'L': 'SL', 'C': 'SC', 'R': 'SR'}[side]
    if abs(spray) > 38 and outcome in ('Double', 'Triple'):
        return 'DL'
    if outcome in ('Double', 'Triple') and 8 < abs(spray) < 32 and dist > 280:
        return 'LC' if spray < 0 else 'RC'
    return {'L': 'LF', 'C': 'CF', 'R': 'RF'}[side]


class Defense:
    """Where the fielders stand and how they move. `speeds` maps position to a
    multiplier on the league speed (1.0 = average)."""

    def __init__(self, speeds=None, params=PARAMS):
        self.params = params
        self.spots = {pos: polar(*POSITIONS[pos]) for pos in POSITIONS}
        self.speeds = speeds or {}

    def speed(self, pos, base):
        return base * self.speeds.get(pos, 1.0)


def resolve(ev, la, spray, rng, defense=None, batter_speed=1.0, params=PARAMS):
    """Play one batted ball. `rng` needs .random() and .gauss()."""
    defense = defense or Defense(params=params)
    trajectory = trajectory_of(la)
    if trajectory == 'ground_ball':
        return _ground_ball(ev, la, spray, rng, defense, batter_speed, params)
    return _air_ball(ev, la, spray, rng, defense, batter_speed, params)


def _ground_ball(ev, la, spray, rng, defense, batter_speed, params):
    p = params
    v = max(ev, 40.0) * MPH_TO_FPS * p['gb_speed_factor']
    # A ball pounded into the dirt dies faster.
    if la < -10:
        v *= 0.8
    home_to_first = p['home_to_first'] / batter_speed + rng.gauss(0, 0.12)
    best = None
    for pos in INFIELD:
        if pos == 'C':
            continue
        depth, angle = POSITIONS[pos]
        lateral = depth * math.sin(math.radians(abs(spray - angle)))
        t_ball = depth / v
        reach = p['if_react'] + lateral / defense.speed(pos, p['if_lateral'])
        margin = t_ball + p['gb_slack'] - reach
        if pos == 'P':
            margin -= 0.25   # follow-through: the pitcher gets only what's hit at him
        if best is None or margin > best[1]:
            best = (pos, margin, t_ball, reach, depth)
    pos, margin, t_ball, reach, depth = best
    spot = polar(depth, spray)
    if margin < 0:
        # Through the infield: a single into the outfield.
        ball = polar(min(220.0, 150.0 + ev), spray)
        of = min(OUTFIELD, key=lambda o: distance(defense.spots[o], ball))
        # The outfielder charges and meets the ball partway in.
        meet = polar(min(250.0, distance((0, 0), defense.spots[of]) - 35.0), spray)
        release = distance((0, 0), meet) / (v * 0.85) + p['transfer'] + 0.2
        return BattedBall('Single', of, 'ground_ball', _location_code('Single', spray, 150, 'ground_ball'),
                          spray, ball, distance((0, 0), ball), release=release, release_point=meet)
    t_fielded = max(t_ball, reach) + p['transfer']
    if pos == '1B' and distance(spot, FIRST_BASE) < 45:
        t_out = t_fielded - p['transfer'] + distance(spot, FIRST_BASE) / defense.speed(pos, p['if_speed'])
    else:
        t_out = t_fielded + distance(spot, FIRST_BASE) / p['throw_speed']
    # A slow roller the fielder has to charge: he gains ground coming in.
    if ev < 65:
        t_out -= 0.3
    if t_out < home_to_first:
        return BattedBall('Groundout', pos, 'ground_ball', pos, spray, spot, depth,
                          release=t_fielded, release_point=spot)
    return BattedBall('Single', pos, 'ground_ball', pos, spray, spot, depth,
                      release=t_fielded, release_point=spot)


def _air_ball(ev, la, spray, rng, defense, batter_speed, params):
    p = params
    flight = fly(ev, la, p)
    trajectory = trajectory_of(la)
    land = polar(flight.carry, spray)
    fence = fence_distance(spray)
    if flight.carry > fence and flight.height_at(fence) > 9.0:
        return BattedBall('Home Run', 'CF' if abs(spray) < 15 else ('LF' if spray < 0 else 'RF'),
                          trajectory, _location_code('Home Run', spray, flight.carry, trajectory),
                          spray, land, flight.carry, flight.hang_time)
    # Who can get there, and with how much time to spare?
    best = None
    for pos in POSITIONS:
        if pos == 'C' and flight.carry > 60:
            continue
        of = pos in OUTFIELD
        speed = defense.speed(pos, p['of_speed'] if of else p['if_speed'])
        target = land
        if flight.carry > fence - 5:
            target = polar(fence - 3, spray)   # he can only go to the wall
        need = (p['of_react'] if of else p['if_react']) + distance(defense.spots[pos], target) / speed
        spare = flight.hang_time - need
        # Infielders call off outfielders on pop-ups, not on liners at their feet.
        if best is None or spare > best[1]:
            best = (pos, spare, need)
    pos, spare, need = best
    if flight.carry > fence - 5:
        spare -= 0.5   # catching it at the wall
    p_catch = 1.0 / (1.0 + math.exp(-p['catch_k'] * (spare + p['catch_bias'])))
    if rng.random() < p_catch:
        # StatsAPI names caught balls by launch angle, not by who caught them:
        # Lineout to ~27 degrees, Flyout to ~57, Pop Out above (real feeds).
        if la >= 57:
            outcome = 'Pop Out'
        elif la <= 27:
            outcome = 'Lineout'
        else:
            outcome = 'Flyout'
        return BattedBall(outcome, pos, trajectory, pos, spray, land, flight.carry, flight.hang_time, caught=True,
                          release=flight.hang_time, release_point=land)

    # It drops. Where does it stop, and how long until it's back in?
    roll = flight.carry * (p['roll_line_drive'] if la < 20 else p['roll_fly_ball'])
    stop_dist = min(flight.carry + roll, fence - 2)
    stop = polar(stop_dist, spray)
    retriever = min(OUTFIELD, key=lambda o: distance(defense.spots[o], stop))
    if flight.carry < 140:
        retriever = min(INFIELD[2:] + OUTFIELD, key=lambda o: distance(defense.spots[o], stop))
    speed = defense.speed(retriever, p['of_speed'] if retriever in OUTFIELD else p['if_speed'])
    t_at_stop = flight.hang_time + (roll / max(flight.carry / flight.hang_time * 0.5, 20.0))
    t_fielder = p['of_react'] + distance(defense.spots[retriever], stop) / speed
    t_ball_in = max(t_at_stop, t_fielder) + 0.5
    if flight.carry + roll >= fence - 2:
        t_ball_in += p['wall_carom']   # off the wall or into the corner: he has to chase the carom
    throw = p['of_throw_speed']
    to_second = t_ball_in + distance(stop, SECOND_BASE) / throw + (0.5 if stop_dist > 260 else 0)
    to_third = t_ball_in + distance(stop, THIRD_BASE) / throw + (0.6 if stop_dist > 260 else 0)
    runner = p['home_to_first'] / batter_speed + rng.gauss(0, 0.12)
    at_second = runner + p['base_to_base'] / batter_speed
    at_third = at_second + p['base_to_base'] / batter_speed
    margin = p['extra_base_margin']
    if at_third + margin + p.get('triple_margin', 0.0) < to_third:
        outcome = 'Triple'
    elif at_second + margin < to_second:
        outcome = 'Double'
    else:
        outcome = 'Single'
    return BattedBall(outcome, retriever, trajectory,
                      _location_code(outcome, spray, flight.carry, trajectory),
                      spray, land, flight.carry, flight.hang_time,
                      release=t_ball_in, release_point=stop)


# --- base running ------------------------------------------------------------
# Runners race the throw. `runners` maps the base a runner starts on (1, 2, 3)
# to his speed multiplier. Functions return each runner's destination: 1-3, or
# 4 for a run. Runners are never thrown out here: the third-base coach only
# sends a runner the throw shouldn't beat, so a close play holds him up.

HOME = (0.0, 0.0)
BASE_POINTS = {1: FIRST_BASE, 2: SECOND_BASE, 3: THIRD_BASE, 4: HOME}

# Fit to the real 2026 feeds: a runner on second scores on ~30% of singles
# with fewer than two out and ~56% with two out; first to third on ~32%;
# a runner on third scores on ~90% of caught fly balls to the outfield and
# two-thirds of groundouts when not forced; ~45% of grounders with a runner on
# first and fewer than two out become double plays.
RUN_PARAMS = {
    'lead': {1: 10.0, 2: 15.0, 3: 12.0},   # ft off the bag by contact (secondary lead)
    'read_ground': 0.25,    # s before a runner commits on a ground ball
    'read_air': 0.75,       # on a ball in the air he holds until it drops
    'turn': 0.35,           # s lost rounding a base
    'cutoff': 0.35,         # s added to a long outfield throw for the hop or relay
    'tag': 0.15,            # s to apply the tag
    'send_home': 0.45,      # s the throw must lose by before the runner is sent home
    'send_third': -0.1,
    'two_out_jump': 0.8,   # s gained running on contact with two outs
    'two_out_lead': 18.0,   # ft more lead with two outs (he's off with the pitch)
    'tag_jump': 0.1,        # s from the catch until a tagging runner is moving
    'of_transfer': 0.85,    # s from catch to release on a tag play
    'tag_home': -0.9,       # s the throw home may win by and he still goes (it's often off line)
    'tag_third': 0.15,
    'tag_second': 1.6,
    'pivot': 1.0,           # s for the pivot man to catch, step and throw
    'force_margin': 0.4,    # s the force at second must win by
    'two_out_force': 0.45,  # with two out, s quicker the force at second must be to go there over first
    'unforced_home': -0.3,  # s a runner on third gives the throw home on a grounder
    'r2_go_release': 1.7,   # s: a runner on second takes third if the ball is hit to his left and fielded this late
}


def _run_time(start_base, end_base, speed, lead, delay, rp):
    feet = 90.0 * (end_base - start_base) - lead
    turns = max(0, end_base - start_base - 1)
    return delay + feet / 90.0 * PARAMS['base_to_base'] / speed + turns * rp['turn']


def _throw_time(ball, base, params=PARAMS, rp=RUN_PARAMS):
    origin = ball.release_point or ball.landing
    d = distance(origin, BASE_POINTS[base])
    of = ball.fielder in OUTFIELD
    t = ball.release + d / (params['of_throw_speed'] if of else params['throw_speed'])
    if of and d > 220:
        t += rp['cutoff']
    return t + (rp['tag'] if base == 4 or base == 3 else 0.0)


def advance_on_hit(ball, outcome, runners, outs, rng, rp=RUN_PARAMS):
    """Destinations for the runners on a Single or Double."""
    bases_taken = {'Single': 1, 'Double': 2, 'Triple': 3}.get(outcome, 4)
    dest = {}
    if bases_taken >= 3:
        return {b: 4 for b in runners}
    infield_hit = ball.fielder in INFIELD
    delay = rp['read_ground'] if ball.trajectory == 'ground_ball' else rp['read_air']
    if outs == 2:
        delay = max(0.0, delay - rp['two_out_jump'])
    occupied_after = {bases_taken}   # the batter's base
    for base in sorted(runners, reverse=True):
        speed = runners[base]
        forced = all(b in runners for b in range(1, base))
        minimum = min(4, base + bases_taken) if not infield_hit else (base + 1 if forced else base)
        target = minimum
        if not infield_hit and minimum < 4:
            extra = minimum + 1
            blocked = extra in dest.values() and extra != 4
            if not blocked:
                lead = rp['lead'][base] + (rp['two_out_lead'] if outs == 2 else 0.0)
                run = _run_time(base, extra, speed, lead, delay, rp)
                throw = _throw_time(ball, extra)
                margin = throw - run + rng.gauss(0, 0.3)
                need = rp['send_home'] if extra == 4 else rp['send_third']
                if margin > need:
                    target = extra
        # A runner can't pass the man ahead of him or stay on the batter's base.
        while target < 4 and (target in dest.values() or target in occupied_after):
            target += 1
        dest[base] = target
    return dest


def ground_out_play(ball, runners, outs, batter_speed, rng, params=PARAMS, rp=RUN_PARAMS):
    """How the defense turns a fielded grounder into outs.

    Returns (play, dest): play is 'dp' (force at second and relay to first),
    'force_home', 'force_second' or 'first'; dest maps each runner who stays
    on base or scores to his destination (forced-out runners are left out).
    """
    p = params
    spot = ball.release_point
    pos = ball.fielder
    t0 = ball.release
    home_to_first = p['home_to_first'] / batter_speed + rng.gauss(0, 0.12)
    t_first = t0 + distance(spot, FIRST_BASE) / p['throw_speed']
    forced = {b for b in runners if all(x in runners for x in range(1, b))}

    def runner_time(base, to):
        return _run_time(base, to, runners[base], rp['lead'][base],
                         0.0 if outs == 2 else rp['read_ground'], rp)

    # The force at second: an infielder near the bag steps on it himself.
    if pos in ('2B', 'SS') and distance(spot, SECOND_BASE) < 30:
        t_second = t0 - p['transfer'] + distance(spot, SECOND_BASE) / p['if_speed']
    else:
        t_second = t0 + distance(spot, SECOND_BASE) / p['throw_speed']
    t_home = t0 + distance(spot, HOME) / p['throw_speed']

    play = 'first'
    if 1 in runners and outs < 2:
        beat_runner = t_second + rp['force_margin'] < runner_time(1, 2)
        relay = t_second + rp['pivot'] + distance(SECOND_BASE, FIRST_BASE) / p['throw_speed']
        if beat_runner and relay < home_to_first:
            play = 'dp'
        elif 3 in forced and t_home + rp['force_margin'] < runner_time(3, 4):
            play = 'force_home'
        elif beat_runner:
            play = 'force_second'
    elif 1 in runners and outs == 2:
        # Two out: take whichever out is surer.
        if t_second + rp['two_out_force'] < min(t_first, runner_time(1, 2)):
            play = 'force_second'

    outs_after = outs + (2 if play == 'dp' else 1)
    dest = {}
    for base in sorted(runners, reverse=True):
        if (play in ('dp', 'force_second') and base == 1) or (play == 'force_home' and base == 3):
            continue
        if outs_after >= 3:
            dest[base] = base
            continue
        if base in forced:
            dest[base] = base + 1
            continue
        if base == 3:
            # Unforced on third: he goes if the throw home can't get him.
            go = t_home + rp['tag'] + rng.gauss(0, 0.3) > runner_time(3, 4) + rp['unforced_home']
            dest[base] = 4 if (go and play != 'force_home') else 3
        elif base == 2:
            # Ball hit behind him (or slow, deep in the hole): he takes third.
            behind = pos in ('1B', '2B') or (pos == 'P' and ball.spray > 0)
            go = behind or t0 > rp['r2_go_release']
            dest[base] = 3 if go and 3 not in dest.values() else 2
        else:
            dest[base] = base
    return play, dest


def tag_ups(ball, runners, outs_after, rng, rp=RUN_PARAMS):
    """Runners tagging up on a caught fly ball (outs_after counts the catch)."""
    dest = {b: b for b in runners}
    if outs_after >= 3 or ball.fielder not in OUTFIELD or ball.trajectory == 'popup':
        return dest
    caught = ball.release
    for base in sorted(runners, reverse=True):
        target = base + 1
        if target != 4 and target in dest.values():
            continue
        run = caught + rp['tag_jump'] + _run_time(base, target, runners[base], 0.0, 0.0, rp)
        throw = (caught + rp['of_transfer'] + distance(ball.landing, BASE_POINTS[target]) / PARAMS['of_throw_speed']
                 + (rp['cutoff'] if distance(ball.landing, BASE_POINTS[target]) > 250 else 0.0) + rp['tag'])
        need = {4: rp['tag_home'], 3: rp['tag_third'], 2: rp['tag_second']}[target]
        if throw - run + rng.gauss(0, 0.3) > need:
            dest[base] = target
    return dest
