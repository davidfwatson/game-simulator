import hashlib
from commentary import GAME_CONTEXT
from gameday import GamedayData
from .randomness import ChoiceRNG, STREAM_NAMES

class GameRenderer:
    def __init__(self, gameday_data: GamedayData, seed: int = None):
        self.gameday_data = gameday_data
        self.base_seed = (seed if seed is not None
                          else gameday_data['gameData'].get('commentarySeed', 0))
        if type(self.base_seed) is not int:
            raise ValueError("commentarySeed must be an integer")
        self.home_team = gameday_data['gameData']['teams']['home']
        self.away_team = gameday_data['gameData']['teams']['away']
        self._reset_render_state()

    def _reset_render_state(self):
        game_data = self.gameday_data['gameData']
        game_start = game_data.get('datetime', {}).get('dateTime', '')
        self._reseed_for_point(game_data, "init", game_start, "init")
        self.current_pitcher_info = {'home': None, 'away': None}

    def _reseed_for_point(self, owner, point, timestamp, key):
        """Seed each stream from point identity and replay any explicit draws.

        Timestamps are carried for inspection only; they never affect wording.
        """
        metadata = owner.get("commentaryRng", {})
        if not isinstance(metadata, dict):
            raise ValueError("commentaryRng must be an object")
        streams = metadata.get(point, {})
        if not isinstance(streams, dict) or set(streams) - set(STREAM_NAMES):
            raise ValueError(f"Invalid commentary streams at {key}")
        for name in STREAM_NAMES:
            seed_text = f"{self.base_seed}_{key}_{name}"
            seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest(), 16)
            setattr(self, "rng_" + name, ChoiceRNG(streams.get(name, []), seed))
        self.rng = self.rng_play

    def render(self) -> str:
        raise NotImplementedError

    @staticmethod
    def _batter_safe_destination(play):
        """Return the batter's final safe base, including multistage advances."""
        batter_id = play['matchup']['batter'].get('id')
        if batter_id is None:
            return None
        destinations = {'1B': 'first', '2B': 'second', '3B': 'third', 'score': 'home'}
        movements = []
        for index, runner in enumerate(play.get('runners', [])):
            details = runner.get('details', {})
            if details.get('runner', {}).get('id') != batter_id:
                continue
            # Gameday can list multiple movements for one runner, sometimes
            # out of event order. With no event index, retain document order.
            event_index = details.get('playIndex')
            order = event_index if type(event_index) is int else index
            movements.append((order, index, runner.get('movement', {})))
        if not movements:
            return None
        _, _, final_movement = max(movements, key=lambda item: item[:2])
        if final_movement.get('isOut', False):
            return None
        return destinations.get(final_movement.get('end'))

    def _get_batted_ball_category(self, outcome, ev, la):
        cat = 'default'
        if ev is not None and la is not None:
            if outcome == "Single":
                if ev > 95 and la < 0: cat = 'grounder'
                elif ev < 90 and 10 < la < 30: cat = 'bloop'
                elif ev > 100 and la < 10: cat = 'liner'
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
