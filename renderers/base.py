import random
import hashlib
from datetime import datetime
from commentary import GAME_CONTEXT
from gameday import GamedayData

class GameRenderer:
    def __init__(self, gameday_data: GamedayData, seed: int = None):
        self.gameday_data = gameday_data
        self.base_seed = seed

        # Separate RNGs for different categories of commentary
        self.rng_play = random.Random()
        self.rng_pitch = random.Random()
        self.rng_flow = random.Random()
        self.rng_color = random.Random()

        # Fallback/Default
        self.rng = self.rng_play

        # Initial seed based on game start time
        game_start = gameday_data.get('gameData', {}).get('datetime', {}).get('dateTime', '')
        self._reseed_from_timestamp(game_start, "init")

        self.home_team = gameday_data['gameData']['teams']['home']
        self.away_team = gameday_data['gameData']['teams']['away']
        self.current_pitcher_info = {'home': None, 'away': None}

    def _reseed_from_timestamp(self, time_str: str, salt: str = ""):
        if not time_str:
            return

        is_direct_mode = self.gameday_data.get('gameData', {}).get('directMode', False)

        if is_direct_mode:
            try:
                # Extract digits from fractional seconds. e.g., '2025-09-27T23:05:00.12345678Z' -> 12345678
                parts = time_str.split('.')
                if len(parts) > 1:
                    frac_part = parts[1]
                    # Strip timezone suffixes: Z, +00:00, -05:00, etc.
                    import re
                    digits_str = re.split(r'[Z+-]', frac_part)[0]
                    index = int(digits_str)
                else:
                    index = 0
            except ValueError:
                index = 0

            class DirectRNG:
                def __init__(self, start_idx):
                    self.idx = start_idx
                def choice(self, seq):
                    if not seq:
                        raise IndexError("Cannot choose from an empty sequence")
                    val = seq[self.idx % len(seq)]
                    self.idx = self.idx // 100
                    return val
                def random(self):
                    val = (self.idx % 100) / 100.0
                    self.idx = self.idx // 100
                    return val
                def seed(self, *args, **kwargs):
                    pass

            # Each stream gets its own independent portion of the fractional seconds.
            # Fractional digits are split into 4-digit segments (base-10000 values):
            #   digits 0-3  (rightmost) → rng_play
            #   digits 4-7              → rng_pitch
            #   digits 8-11             → rng_flow
            #   digits 12-15            → rng_color
            # Each stream gets 2 controllable calls (4 digits / 2 digits per call).
            self.rng_play  = DirectRNG(index % 10000)
            self.rng_pitch = DirectRNG((index // 10000) % 10000)
            self.rng_flow  = DirectRNG((index // 100000000) % 10000)
            self.rng_color = DirectRNG((index // 1000000000000) % 10000)
            return

        # Combine base seed, timestamp, and salt to create a unique, deterministic hash
        seed_str = f"{self.base_seed}_{time_str}_{salt}"
        hash_obj = hashlib.md5(seed_str.encode('utf-8'))
        hash_int = int(hash_obj.hexdigest(), 16)

        master_rng = random.Random(hash_int)

        # Reseed all specific RNGs deterministically from the master
        self.rng_play.seed(master_rng.randint(0, 1_000_000_000))
        self.rng_pitch.seed(master_rng.randint(0, 1_000_000_000))
        self.rng_flow.seed(master_rng.randint(0, 1_000_000_000))
        self.rng_color.seed(master_rng.randint(0, 1_000_000_000))

    def render(self) -> str:
        raise NotImplementedError

    def _get_batted_ball_category(self, outcome, ev, la):
        cat = 'default'
        if ev is not None and la is not None:
            if outcome == "Single":
                if ev < 90 and 10 < la < 30: cat = 'bloop'
                elif ev > 100 and la < 10: cat = 'liner'
                elif ev > 95 and la < 0: cat = 'grounder'
            elif outcome == "Double":
                if ev > 100 and la < 15: cat = 'liner'
                elif ev > 100 and la >= 15: cat = 'wall'
            elif outcome == "Home Run":
                if ev > 105 and la < 22: cat = 'screamer'
                elif ev > 100 and la > 35: cat = 'moonshot'
            elif outcome == "Groundout":
                if ev < 85: cat = 'soft'
                elif ev > 100: cat = 'hard'
            elif outcome == "Flyout":
                if (ev < 95 and la > 50) or (ev < 90 and la > 40): cat = 'popup'
                elif ev > 100 and la > 30: cat = 'deep'
        return cat

    def _get_batted_ball_verb(self, outcome, cat, force_type=None):
        outcome_data = GAME_CONTEXT['statcast_verbs'].get(outcome, {})

        if force_type:
            phrase_type = force_type
        else:
            use_verb = self.rng_play.random() < 0.6
            phrase_type = 'verbs' if use_verb else 'nouns'

        phrases = outcome_data.get(phrase_type, outcome_data.get('verbs', {}))
        phrase_list = phrases.get(cat, phrases.get('default', ["describes"]))
        # Fallback if specific category empty
        if not phrase_list:
             phrase_list = phrases.get('default', ["describes"])

        phrase = self.rng_play.choice(phrase_list)
        return phrase, phrase_type

    def _get_hit_location(self, hit_type, ev, la, location_code=None):
        if location_code:
            return GAME_CONTEXT['hit_directions'].get(location_code, "fair")

        if la is None or ev is None: return "fair"
        if hit_type in ["Single", "Double"]:
            if -10 < la < 10: return self.rng_play.choice(["up the middle", "through the right side", "through the left side"])
            elif 10 < la < 25: return self.rng_play.choice(["to left field", "to center field", "to right field"])
            else: return self.rng_play.choice(["into shallow left", "into shallow center", "into shallow right"])
        elif hit_type == "Triple":
            return self.rng_play.choice(["into the right-center gap", "into the left-center gap"])
        elif hit_type == "Home Run":
            if abs(la - 28) < 5 and ev > 105: return "down the line"
            return self.rng_play.choice(["to deep left field", "to deep center field", "to deep right field"])
        return "fair"

    def _format_statcast_template(self, outcome, context):
        templates = GAME_CONTEXT.get('statcast_templates', {}).get(outcome)
        if not templates: return None
        template = self.rng_play.choice(templates)
        if '{verb_capitalized}' in template:
            context['verb_capitalized'] = context.get('verb', '').capitalize()
        return template.format(**context)
