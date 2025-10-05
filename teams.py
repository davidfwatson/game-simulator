"""
This file contains the data for fictional baseball teams and players
for a modern MLB-style simulation.
- Pitchers have stamina and do not bat.
- A Designated Hitter (DH) is included in the lineup.
- Each team has a bullpen with specific reliever roles.
- Teams have fielding and double play ratings.
- Player fielding ability is rated on a scale where higher is better.
- Pitch velocities are defined as a (min, max) range in MPH.
"""

GAME_CONTEXT = {
    "umpires": [
        "Chuck Thompson", "Larry Phillips", "Frank Rizzo", "Gus Morales", "Stan Friedman"
    ],
    "weather_conditions": [
        "75°F, Clear", "82°F, Sunny", "68°F, Overcast", "55°F, Drizzle", "72°F, Partly Cloudy, Wind 10 mph L to R"
    ],
    "pitch_locations": {
        "strike": [
            "paints the corner", "right down the middle", "catches the black",
            "a perfect strike", "in the zone", "freezes him on the inner edge",
            "snaps over the backdoor", "drops onto the knees"
        ],
        "ball": [
            "just misses outside", "high and tight", "in the dirt", "way outside",
            "low and away", "a bit inside", "sails over the letters",
            "spikes before the plate"
        ]
    },
    "statcast_verbs": {
        "Single": {
            "default": ["gets a single"],
            "bloop": ["bloops a single", "flares one for a single"],      # Low EV, Medium LA
            "liner": ["lines a single", "rips a single"],                # High EV, Low LA
            "grounder": ["grounds a single", "shoots a single through the hole"] # High EV, Negative LA
        },
        "Double": {
            "default": ["hustles for a double"],
            "liner": ["laces a double into the gap", "drills a double"], # High EV, Low LA
            "wall": ["bangs a double off the wall", "one-hops the wall"]   # High EV, Medium LA
        },
        "Triple": {
            "default": ["legs out a triple", "drives one into the gap for three"]
        },
        "Home Run": {
            "default": ["crushes a homer", "launches a no-doubter"],
            "screamer": ["hits a frozen-rope homer", "lines a laser over the fence"], # Very High EV, Low LA
            "moonshot": ["hits a towering home run", "sends a moonshot into the stands"] # High EV, High LA
        },
        "Groundout": {
            "default": ["grounds out"],
            "soft": ["rolls over on one", "bounces out weakly"],     # Low EV
            "hard": ["smashes a groundout", "rips a one-hopper"]      # High EV
        },
        "Flyout": {
            "default": ["flies out"],
            "popup": ["skies a popup", "lifts an infield fly"],      # Low EV, High LA
            "deep": ["drives a deep fly ball", "hits it to the warning track"] # High EV, High LA
        },
        "Strikeout": {
            "swinging": ["strikes out swinging", "goes down swinging", "whiffs"],
            "looking": ["is called out on strikes", "goes down looking", "is frozen for strike three"]
        }
    },
    "statcast_templates": {
        "Home Run": [
            "{batter_name} {verb}.",
            "That ball is GONE! {batter_name} {verb}.",
            "{verb_capitalized}! A {runs}-run homer for {batter_name}!"
        ],
        "Double": [
            "{batter_name} {verb}.",
            "{verb_capitalized}, and that'll be a double for {batter_name}.",
            "{batter_name} legs out a double."
        ],
        "Error": [
            "{display_outcome} {adv_str}.",
            "A fielding error by the defense allows {batter_name} to reach base. {adv_str}.",
            "{batter_name} gets on base thanks to an error. {adv_str}."
        ],
        "Flyout": [
            "{batter_name} {verb} to {fielder_pos}.",
            "It's a fly ball to {fielder_pos}, and {fielder_name} makes the catch for the out.",
            "{batter_name} gets under it and {verb} to {fielder_name} in {fielder_pos}."
        ],
        "Groundout": [
            "{batter_name} {verb} to {fielder_pos}.",
            "A grounder to {fielder_pos}, and {fielder_name} handles it for the out.",
            "{batter_name} hits it on the ground to {fielder_name} at {fielder_pos} for the out."
        ]
    }
}

TEAMS = {
    "BAY_BOMBERS": {
        "name": "Bay Area Bombers",
        "venue": "Waterfront Park",
        "fielding_prowess": 0.982,
        "double_play_rate": 0.14,
        "hbp_rate": 0.004,  # Likelihood of a HBP per at-bat
        "players": [
            # Batting Order (Triples reduced and redistributed)
            {'legal_name': 'Leo Vance', 'nickname': None, 'position': 'CF', 'handedness': 'L', 'fielding_ability': 0.988, 'stats': {'Single': 0.155, 'Double': 0.06, 'Triple': 0.002, 'Home Run': 0.02, 'Walk': 0.10, 'Strikeout': 0.15, 'HBP': 0.005, 'Groundout': 0.25, 'Flyout': 0.258}},
            {'legal_name': 'Marcus Thorne', 'nickname': None, 'position': 'RF', 'handedness': 'L', 'fielding_ability': 0.981, 'stats': {'Single': 0.175, 'Double': 0.07, 'Triple': 0.002, 'Home Run': 0.04, 'Walk': 0.11, 'Strikeout': 0.14, 'HBP': 0.004, 'Groundout': 0.23, 'Flyout': 0.229}},
            {'legal_name': 'Sam Decker', 'nickname': None, 'position': 'C', 'handedness': 'R', 'fielding_ability': 0.995, 'passed_ball_rate': 0.002, 'stats': {'Single': 0.16, 'Double': 0.08, 'Triple': 0.00, 'Home Run': 0.05, 'Walk': 0.13, 'Strikeout': 0.12, 'HBP': 0.003, 'Groundout': 0.22, 'Flyout': 0.237}},
            {'legal_name': 'Jackson Riley', 'nickname': 'Jax', 'position': 'DH', 'handedness': 'R', 'fielding_ability': 0.950, 'stats': {'Single': 0.145, 'Double': 0.05, 'Triple': 0.002, 'Home Run': 0.08, 'Walk': 0.12, 'Strikeout': 0.18, 'HBP': 0.006, 'Groundout': 0.20, 'Flyout': 0.217}},
            {'legal_name': 'Caleb Jones', 'nickname': None, 'position': 'SS', 'handedness': 'R', 'fielding_ability': 0.975, 'stats': {'Single': 0.135, 'Double': 0.04, 'Triple': 0.002, 'Home Run': 0.01, 'Walk': 0.08, 'Strikeout': 0.19, 'HBP': 0.002, 'Groundout': 0.27, 'Flyout': 0.271}},
            {'legal_name': 'Nate Diaz', 'nickname': 'Kid', 'position': '2B', 'handedness': 'R', 'fielding_ability': 0.983, 'stats': {'Single': 0.185, 'Double': 0.04, 'Triple': 0.002, 'Home Run': 0.01, 'Walk': 0.07, 'Strikeout': 0.10, 'HBP': 0.001, 'Groundout': 0.30, 'Flyout': 0.292}},
            {'legal_name': 'Owen Chen', 'nickname': 'Big Duck', 'position': '1B', 'handedness': 'L', 'fielding_ability': 0.991, 'stats': {'Single': 0.12, 'Double': 0.06, 'Triple': 0.00, 'Home Run': 0.06, 'Walk': 0.09, 'Strikeout': 0.22, 'HBP': 0.005, 'Groundout': 0.22, 'Flyout': 0.225}},
            {'legal_name': 'Miles Corbin', 'nickname': None, 'position': '3B', 'handedness': 'S', 'fielding_ability': 0.965, 'stats': {'Single': 0.145, 'Double': 0.05, 'Triple': 0.002, 'Home Run': 0.03, 'Walk': 0.10, 'Strikeout': 0.17, 'HBP': 0.003, 'Groundout': 0.25, 'Flyout': 0.25}},
            {'legal_name': 'Grant Fisher', 'nickname': None, 'position': 'LF', 'handedness': 'R', 'fielding_ability': 0.980, 'stats': {'Single': 0.155, 'Double': 0.05, 'Triple': 0.002, 'Home Run': 0.05, 'Walk': 0.09, 'Strikeout': 0.19, 'HBP': 0.004, 'Groundout': 0.23, 'Flyout': 0.229}},
            # Pitchers
            {
                'legal_name': 'Joe Gibson', 'nickname': 'Smokey', 'position': 'P', 'handedness': 'R', 'type': 'Starter', 'stamina': 75, 'fielding_ability': 0.955,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.5, 'velo_range': (94, 97), 'spin_range': (2200, 2550)},
                    'slider': {'prob': 0.25, 'velo_range': (87, 90), 'spin_range': (2400, 2700)},
                    'changeup': {'prob': 0.15, 'velo_range': (81, 84), 'spin_range': (1600, 1900)},
                    'curveball': {'prob': 0.10, 'velo_range': (78, 81), 'spin_range': (2600, 2900)}
                }, 'control': 0.65, 'wild_pitch_rate': 0.003
            },
            {
                'legal_name': 'Colin Miller', 'nickname': 'Cyclone', 'position': 'P', 'handedness': 'R', 'type': 'Long Reliever', 'stamina': 45, 'fielding_ability': 0.950,
                'pitch_arsenal': {
                    'sinker': {'prob': 0.6, 'velo_range': (91, 94), 'spin_range': (2000, 2250)},
                    'slider': {'prob': 0.4, 'velo_range': (86, 88), 'spin_range': (2500, 2800)}
                }, 'control': 0.60, 'wild_pitch_rate': 0.005
            },
            {
                'legal_name': 'Adam Adams', 'nickname': 'Ace', 'position': 'P', 'handedness': 'L', 'type': 'Middle Reliever', 'stamina': 25, 'fielding_ability': 0.945,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.5, 'velo_range': (92, 95), 'spin_range': (2250, 2600)},
                    'knuckle curve': {'prob': 0.5, 'velo_range': (77, 80), 'spin_range': (2800, 3100)}
                }, 'control': 0.70, 'wild_pitch_rate': 0.002
            },
            {
                'legal_name': 'Victor Stone', 'nickname': 'The Vulture', 'position': 'P', 'handedness': 'R', 'type': 'Closer', 'stamina': 20, 'fielding_ability': 0.960,
                'pitch_arsenal': {
                    'cutter': {'prob': 0.4, 'velo_range': (90, 93), 'spin_range': (2300, 2650)},
                    'four-seam fastball': {'prob': 0.4, 'velo_range': (95, 98), 'spin_range': (2400, 2700)},
                    'slider': {'prob': 0.2, 'velo_range': (88, 91), 'spin_range': (2600, 2900)}
                }, 'control': 0.75, 'wild_pitch_rate': 0.001
            },
        ]
    },
    "PC_PILOTS": {
        "name": "Pacific City Pilots",
        "venue": "Aero Field",
        "fielding_prowess": 0.975,
        "double_play_rate": 0.13,
        "hbp_rate": 0.0035,
        "players": [
            # Batting Order (Triples reduced and redistributed)
            {'legal_name': 'Alex Chase', 'nickname': None, 'position': '2B', 'handedness': 'R', 'fielding_ability': 0.985, 'stats': {'Single': 0.165, 'Double': 0.05, 'Triple': 0.002, 'Home Run': 0.02, 'Walk': 0.08, 'Strikeout': 0.16, 'HBP': 0.003, 'Groundout': 0.26, 'Flyout': 0.26}},
            {'legal_name': 'Kevin Webb', 'nickname': 'Spider', 'position': 'CF', 'handedness': 'L', 'fielding_ability': 0.990, 'stats': {'Single': 0.15, 'Double': 0.04, 'Triple': 0.002, 'Home Run': 0.01, 'Walk': 0.09, 'Strikeout': 0.18, 'HBP': 0.005, 'Groundout': 0.25, 'Flyout': 0.273}},
            {'legal_name': 'Omar Ramirez', 'nickname': 'Cookie', 'position': '3B', 'handedness': 'R', 'fielding_ability': 0.960, 'stats': {'Single': 0.155, 'Double': 0.06, 'Triple': 0.002, 'Home Run': 0.04, 'Walk': 0.12, 'Strikeout': 0.15, 'HBP': 0.002, 'Groundout': 0.23, 'Flyout': 0.241}},
            {'legal_name': 'Rex Power', 'nickname': 'Buzz', 'position': 'DH', 'handedness': 'R', 'fielding_ability': 0.940, 'stats': {'Single': 0.135, 'Double': 0.05, 'Triple': 0.002, 'Home Run': 0.09, 'Walk': 0.13, 'Strikeout': 0.21, 'HBP': 0.008, 'Groundout': 0.19, 'Flyout': 0.185}},
            {'legal_name': 'Evan Reed', 'nickname': None, 'position': 'LF', 'handedness': 'L', 'fielding_ability': 0.978, 'stats': {'Single': 0.175, 'Double': 0.07, 'Triple': 0.002, 'Home Run': 0.03, 'Walk': 0.09, 'Strikeout': 0.13, 'HBP': 0.004, 'Groundout': 0.24, 'Flyout': 0.249}},
            {'legal_name': 'Felix Washington', 'nickname': 'Nine', 'position': '1B', 'handedness': 'L', 'fielding_ability': 0.992, 'stats': {'Single': 0.14, 'Double': 0.07, 'Triple': 0.00, 'Home Run': 0.07, 'Walk': 0.10, 'Strikeout': 0.20, 'HBP': 0.006, 'Groundout': 0.21, 'Flyout': 0.204}},
            {'legal_name': 'Hank Barrett', 'nickname': None, 'position': 'C', 'handedness': 'R', 'fielding_ability': 0.994, 'passed_ball_rate': 0.003, 'stats': {'Single': 0.15, 'Double': 0.04, 'Triple': 0.00, 'Home Run': 0.03, 'Walk': 0.08, 'Strikeout': 0.15, 'HBP': 0.001, 'Groundout': 0.27, 'Flyout': 0.276}},
            {'legal_name': 'Wes Griffin', 'nickname': None, 'position': 'SS', 'handedness': 'S', 'fielding_ability': 0.972, 'stats': {'Single': 0.195, 'Double': 0.05, 'Triple': 0.002, 'Home Run': 0.01, 'Walk': 0.06, 'Strikeout': 0.08, 'HBP': 0.002, 'Groundout': 0.29, 'Flyout': 0.301}},
            {'legal_name': 'TJ Hawkins', 'nickname': None, 'position': 'RF', 'handedness': 'R', 'fielding_ability': 0.982, 'stats': {'Single': 0.185, 'Double': 0.06, 'Triple': 0.002, 'Home Run': 0.04, 'Walk': 0.10, 'Strikeout': 0.12, 'HBP': 0.003, 'Groundout': 0.25, 'Flyout': 0.24}},
            # Pitchers
            {
                'legal_name': 'Miguel Garcia', 'nickname': 'Lefty', 'position': 'P', 'handedness': 'L', 'type': 'Starter', 'stamina': 70, 'fielding_ability': 0.950,
                'pitch_arsenal': {
                    'sinker': {'prob': 0.5, 'velo_range': (90, 93), 'spin_range': (1950, 2200)},
                    'curveball': {'prob': 0.3, 'velo_range': (78, 81), 'spin_range': (2700, 3000)},
                    'slider': {'prob': 0.2, 'velo_range': (84, 87), 'spin_range': (2350, 2650)}
                }, 'control': 0.60, 'wild_pitch_rate': 0.006
            },
            {
                'legal_name': 'Ben Logan', 'nickname': 'Chief', 'position': 'P', 'handedness': 'R', 'type': 'Long Reliever', 'stamina': 50, 'fielding_ability': 0.955,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.7, 'velo_range': (93, 96), 'spin_range': (2100, 2450)},
                    'curveball': {'prob': 0.3, 'velo_range': (79, 82), 'spin_range': (2500, 2800)}
                }, 'control': 0.68, 'wild_pitch_rate': 0.004
            },
            {
                'legal_name': 'Rollie Malone', 'nickname': 'Fingers', 'position': 'P', 'handedness': 'R', 'type': 'Middle Reliever', 'stamina': 30, 'fielding_ability': 0.940,
                'pitch_arsenal': {
                    'sinker': {'prob': 0.6, 'velo_range': (90, 93), 'spin_range': (2050, 2300)},
                    'slider': {'prob': 0.4, 'velo_range': (85, 88), 'spin_range': (2450, 2750)}
                }, 'control': 0.72, 'wild_pitch_rate': 0.002
            },
            {
                'legal_name': 'Dennis Thompson', 'nickname': 'Eck', 'position': 'P', 'handedness': 'R', 'type': 'Closer', 'stamina': 22, 'fielding_ability': 0.965,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.6, 'velo_range': (97, 100), 'spin_range': (2300, 2600)},
                    'slider': {'prob': 0.4, 'velo_range': (89, 92), 'spin_range': (2550, 2850)}
                }, 'control': 0.80, 'wild__pitch_rate': 0.001
            },
        ]
    }
}