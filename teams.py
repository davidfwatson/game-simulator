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
        "Chuck Thompson", "Larry Phillips", "Frank Rizzo", "Gus Morales", "Stan Friedman",
        "Herb Washington", "Doug Harvey", "Nestor Chylak", "Al Barlick", "Bill Klem"
    ],
    "weather_conditions": [
        "75°F, Clear", "82°F, Sunny", "68°F, Overcast", "55°F, Drizzle",
        "72°F, Partly Cloudy, Wind 10 mph L to R", "65°F, Calm", "88°F, Humid",
        "78°F, Clear, Wind 5 mph out to CF", "92°F, Sweltering Sun", "60°F, Night, Clear"
    ],
    "pitch_locations": {
        "strike": [
            "paints the corner", "right down the middle", "catches the black",
            "a perfect strike", "in the zone", "buckles the batter's knees", "frozen with the pitch"
        ],
        "ball": [
            "just misses outside", "high and tight", "in the dirt", "way outside",
            "low and away", "a bit inside", "nearly took his head off", "the ump doesn't bite"
        ]
    },
    "play_by_play": {
        "swing_and_miss": [
            "Swinging Strike", "Swing and a miss!", "He swung right through it", "Comes up empty"
        ],
        "called_strike": [
            "Called Strike", "In there for a strike", "Caught him looking"
        ],
        "foul_ball": [
            "Foul", "Fouled back", "Fouled straight back", "A piece of it, fouled away"
        ],
        "hit": {
            "Single": [
                "A sharp single into left field.", "A ground ball single up the middle.", "A bloop single drops in shallow right.", "Beats out an infield single."
            ],
            "Double": [
                "A line drive double into the gap.", "A stand-up double down the line.", "One hops the wall for a double."
            ],
            "Triple": [
                "A shot into the alley, and he's going for three!", "A long drive to center, it's a triple!", "He's racing around the bases for a triple!"
            ],
            "Home Run": [
                "A towering home run to deep left!", "That ball is outta here! Home run!", "A solo shot to right field.", "Back, back, back... GONE! A home run!"
            ]
        },
        "out": {
            "strikeout": [
                "and he's out on strikes!", "a swinging strikeout to end the at-bat.", "caught looking for strike three."
            ],
            "groundout": [
                "Grounds out to {fielder}.", "Hit a weak grounder to {fielder}, thrown out at first.", "An easy ground ball to {fielder} for the out."
            ],
            "flyout": [
                "A fly ball to {fielder_pos}, caught for the out.", "A lazy fly ball to {fielder_pos}.", "He got under it, a flyout to {fielder_pos}."
            ],
            "popout": [
                "A pop fly to {fielder_pos}, who makes the catch for the out.", "Popped up to {fielder_pos}.", "An infield pop-up to {fielder_pos}."
            ]
        },
        "misc": {
            "walk": ["That's ball four, a walk.", "He loses him, it's a walk.", "The pitcher misses, and the batter draws a walk."],
            "hbp": ["Oh, that one got him! That's a hit by pitch.", "He's hit by the pitch, and will take his base.", "The pitch sails inside and hits him. Ruled a hit by pitch."]
        },
        "flavor": [
            "\nThe infield shifts to the right for this batter.",
            "\nA murmur goes through the crowd.",
            "\nThe pitcher checks the runner on first.",
            "\nThe catcher gives the signs.",
            "\nThe batter steps out, adjusts his gloves.",
            "\nA visit to the mound to talk strategy.",
            "\nThe batter takes a practice swing."
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
                    'Four-Seam Fastball': {'prob': 0.5, 'velo_range': (94, 97)}, 'Slider': {'prob': 0.25, 'velo_range': (87, 90)},
                    'Changeup': {'prob': 0.15, 'velo_range': (81, 84)}, 'Curveball': {'prob': 0.10, 'velo_range': (78, 81)}
                }, 'control': 0.65, 'wild_pitch_rate': 0.003
            },
            {
                'legal_name': 'Colin Miller', 'nickname': 'Cyclone', 'position': 'P', 'handedness': 'R', 'type': 'Long Reliever', 'stamina': 45, 'fielding_ability': 0.950,
                'pitch_arsenal': {'Sinker': {'prob': 0.6, 'velo_range': (91, 94)}, 'Slider': {'prob': 0.4, 'velo_range': (86, 88)}}, 'control': 0.60, 'wild_pitch_rate': 0.005
            },
            {
                'legal_name': 'Adam Adams', 'nickname': 'Ace', 'position': 'P', 'handedness': 'L', 'type': 'Middle Reliever', 'stamina': 25, 'fielding_ability': 0.945,
                'pitch_arsenal': {'Four-Seam Fastball': {'prob': 0.5, 'velo_range': (92, 95)}, 'Knuckle-Curve': {'prob': 0.5, 'velo_range': (77, 80)}}, 'control': 0.70, 'wild_pitch_rate': 0.002
            },
            {
                'legal_name': 'Victor Stone', 'nickname': 'The Vulture', 'position': 'P', 'handedness': 'R', 'type': 'Closer', 'stamina': 20, 'fielding_ability': 0.960,
                'pitch_arsenal': {
                    'Cutter': {'prob': 0.4, 'velo_range': (90, 93)}, 'Four-Seam Fastball': {'prob': 0.4, 'velo_range': (95, 98)},
                    'Slider': {'prob': 0.2, 'velo_range': (88, 91)}
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
                    'Two-Seam Fastball': {'prob': 0.5, 'velo_range': (90, 93)}, 'Curveball': {'prob': 0.3, 'velo_range': (78, 81)},
                    'Slider': {'prob': 0.2, 'velo_range': (84, 87)}
                }, 'control': 0.60, 'wild_pitch_rate': 0.006
            },
            {
                'legal_name': 'Ben Logan', 'nickname': 'Chief', 'position': 'P', 'handedness': 'R', 'type': 'Long Reliever', 'stamina': 50, 'fielding_ability': 0.955,
                'pitch_arsenal': {'Four-Seam Fastball': {'prob': 0.7, 'velo_range': (93, 96)}, 'Curveball': {'prob': 0.3, 'velo_range': (79, 82)}}, 'control': 0.68, 'wild_pitch_rate': 0.004
            },
            {
                'legal_name': 'Rollie Malone', 'nickname': 'Fingers', 'position': 'P', 'handedness': 'R', 'type': 'Middle Reliever', 'stamina': 30, 'fielding_ability': 0.940,
                'pitch_arsenal': {'Sinker': {'prob': 0.6, 'velo_range': (90, 93)}, 'Slider': {'prob': 0.4, 'velo_range': (85, 88)}}, 'control': 0.72, 'wild_pitch_rate': 0.002
            },
            {
                'legal_name': 'Dennis Thompson', 'nickname': 'Eck', 'position': 'P', 'handedness': 'R', 'type': 'Closer', 'stamina': 22, 'fielding_ability': 0.965,
                'pitch_arsenal': {'Four-Seam Fastball': {'prob': 0.6, 'velo_range': (97, 100)}, 'Slider': {'prob': 0.4, 'velo_range': (89, 92)}}, 'control': 0.80, 'wild_pitch_rate': 0.001
            },
        ]
    }
}