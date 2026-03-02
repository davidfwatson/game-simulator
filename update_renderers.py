import re

with open("renderers.py", "r") as f:
    content = f.read()

# Add hashlib import if not present
if "import hashlib" not in content:
    content = content.replace("import random\n", "import random\nimport hashlib\n")

# Modify __init__ and add _reseed_from_timestamp
init_search = """class GameRenderer:
    def __init__(self, gameday_data: GamedayData, seed: int = None):
        self.gameday_data = gameday_data

        # Master RNG to generate sub-seeds for stability
        master_rng = random.Random(seed)

        # Separate RNGs for different categories of commentary
        # rng_play: Batted ball descriptions, hit locations, specific play outcomes
        self.rng_play = random.Random(master_rng.randint(0, 1_000_000_000))

        # rng_pitch: Pitch types, ball/strike descriptions, foul ball descriptions
        self.rng_pitch = random.Random(master_rng.randint(0, 1_000_000_000))

        # rng_flow: Connectors ("And the 1-1..."), inning transitions, batter intros
        self.rng_flow = random.Random(master_rng.randint(0, 1_000_000_000))

        # rng_color: Station IDs, weather comments, handedness comments, color commentary
        self.rng_color = random.Random(master_rng.randint(0, 1_000_000_000))

        # Fallback/Default
        self.rng = self.rng_play

        self.home_team = gameday_data['gameData']['teams']['home']
        self.away_team = gameday_data['gameData']['teams']['away']
        self.current_pitcher_info = {'home': None, 'away': None}"""

init_replace = """class GameRenderer:
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

        # Combine base seed, timestamp, and salt to create a unique, deterministic hash
        seed_str = f"{self.base_seed}_{time_str}_{salt}"
        hash_obj = hashlib.md5(seed_str.encode('utf-8'))
        hash_int = int(hash_obj.hexdigest(), 16)

        master_rng = random.Random(hash_int)

        # Reseed all specific RNGs deterministically from the master
        self.rng_play.seed(master_rng.randint(0, 1_000_000_000))
        self.rng_pitch.seed(master_rng.randint(0, 1_000_000_000))
        self.rng_flow.seed(master_rng.randint(0, 1_000_000_000))
        self.rng_color.seed(master_rng.randint(0, 1_000_000_000))"""

content = content.replace(init_search, init_replace)

with open("renderers.py", "w") as f:
    f.write(content)
