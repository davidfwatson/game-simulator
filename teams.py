"""
This file contains the data for fictional baseball teams and players
for a modern MLB-style simulation.
- Pitchers have stamina and do not bat.
- A Designated Hitter (DH) is included in the lineup.
- Each team has a bullpen with specific reliever roles.
- Teams have fielding and double play ratings.
- Player fielding ability is rated on a scale where higher is better.
- Pitch velocities are defined as a (min, max) range in MPH.
- Spin rates (RPM) are included for more realistic Statcast data.
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
        "single": ["lines a single", "shoots a single", "drops a blooper for a single", "finds a hole for a single"],
        "double": ["drills a double", "one-hops the wall for a double", "slices a double down the line"],
        "home_run": ["crushes a homer", "launches a no-doubter", "sends it over the wall"],
        "groundout": ["grounds out", "rolls over on one", "hits a chopper", "bounces out"],
        "flyout": ["flies out", "skies one", "lifts a fly ball"],
        "strikeout": ["strikes out swinging", "caught looking", "goes down on strikes"]
    },
    "statcast_events": {
        "mound_visit": [
            "Mound visit: Pitching coach out for a chat.",
            "The catcher heads to the mound to talk strategy.",
            "Brief meeting on the mound to settle the pitcher down."
        ],
        "challenge": [
            "The offensive manager is challenging the call on the field.",
            "A challenge flag is thrown; the umpires will review the play.",
            "It looks like they'll take another look at that one."
        ]
    }
}

TEAMS = {
    "BAY_BOMBERS": {
        "name": "Bay Area Bombers",
        "venue": "Waterfront Park",
        "fielding_prowess": 0.982,
        "double_play_rate": 0.14,
        "hbp_rate": 0.004,
        "defensive_positioning": {
            "shift_L": 0.55, # Probability of shifting against a lefty
            "shift_R": 0.20, # Probability of shifting against a righty
            "infield_in": 0.10 # Base probability of bringing the infield in with runner on 3rd
        },
        "players": [
            # Batting Order
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
                    'four-seam fastball': {'prob': 0.5, 'velo_range': (92, 98), 'rpm_range': (2200, 2550)},
                    'slider': {'prob': 0.25, 'velo_range': (85, 91), 'rpm_range': (2500, 2800)},
                    'changeup': {'prob': 0.15, 'velo_range': (80, 85), 'rpm_range': (1600, 1900)},
                    'curveball': {'prob': 0.10, 'velo_range': (76, 82), 'rpm_range': (2700, 3100)}
                }, 'control': 0.65, 'wild_pitch_rate': 0.003
            },
            {
                'legal_name': 'Colin Miller', 'nickname': 'Cyclone', 'position': 'P', 'handedness': 'R', 'type': 'Long Reliever', 'stamina': 45, 'fielding_ability': 0.950,
                'pitch_arsenal': {
                    'sinker': {'prob': 0.6, 'velo_range': (89, 95), 'rpm_range': (1900, 2200)},
                    'slider': {'prob': 0.4, 'velo_range': (84, 88), 'rpm_range': (2400, 2700)}
                }, 'control': 0.60, 'wild_pitch_rate': 0.005
            },
            {
                'legal_name': 'Adam Adams', 'nickname': 'Ace', 'position': 'P', 'handedness': 'L', 'type': 'Middle Reliever', 'stamina': 25, 'fielding_ability': 0.945,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.5, 'velo_range': (91, 95), 'rpm_range': (2100, 2400)},
                    'knuckle curve': {'prob': 0.5, 'velo_range': (75, 81), 'rpm_range': (2800, 3200)}
                }, 'control': 0.70, 'wild_pitch_rate': 0.002
            },
            {
                'legal_name': 'Victor Stone', 'nickname': 'The Vulture', 'position': 'P', 'handedness': 'R', 'type': 'Closer', 'stamina': 20, 'fielding_ability': 0.960,
                'pitch_arsenal': {
                    'cutter': {'prob': 0.4, 'velo_range': (88, 93), 'rpm_range': (2300, 2600)},
                    'four-seam fastball': {'prob': 0.4, 'velo_range': (96, 99), 'rpm_range': (2400, 2700)},
                    'slider': {'prob': 0.2, 'velo_range': (88, 92), 'rpm_range': (2600, 2900)}
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
        "defensive_positioning": {
            "shift_L": 0.65, # High tendency to shift lefties
            "shift_R": 0.15, # Low tendency to shift righties
            "infield_in": 0.12
        },
        "players": [
            # Batting Order
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
                    'sinker': {'prob': 0.5, 'velo_range': (88, 94), 'rpm_range': (2000, 2300)},
                    'curveball': {'prob': 0.3, 'velo_range': (74, 80), 'rpm_range': (2800, 3300)},
                    'slider': {'prob': 0.2, 'velo_range': (82, 87), 'rpm_range': (2400, 2750)}
                }, 'control': 0.60, 'wild_pitch_rate': 0.006
            },
            {
                'legal_name': 'Ben Logan', 'nickname': 'Chief', 'position': 'P', 'handedness': 'R', 'type': 'Long Reliever', 'stamina': 50, 'fielding_ability': 0.955,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.7, 'velo_range': (93, 97), 'rpm_range': (2150, 2450)},
                    'curveball': {'prob': 0.3, 'velo_range': (79, 83), 'rpm_range': (2600, 2900)}
                }, 'control': 0.68, 'wild_pitch_rate': 0.004
            },
            {
                'legal_name': 'Rollie Malone', 'nickname': 'Fingers', 'position': 'P', 'handedness': 'R', 'type': 'Middle Reliever', 'stamina': 30, 'fielding_ability': 0.940,
                'pitch_arsenal': {
                    'sinker': {'prob': 0.6, 'velo_range': (90, 94), 'rpm_range': (2050, 2350)},
                    'slider': {'prob': 0.4, 'velo_range': (85, 89), 'rpm_range': (2550, 2850)}
                }, 'control': 0.72, 'wild_pitch_rate': 0.002
            },
            {
                'legal_name': 'Dennis Thompson', 'nickname': 'Eck', 'position': 'P', 'handedness': 'R', 'type': 'Closer', 'stamina': 22, 'fielding_ability': 0.965,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.6, 'velo_range': (96, 101), 'rpm_range': (2300, 2600)},
                    'slider': {'prob': 0.4, 'velo_range': (88, 93), 'rpm_range': (2700, 3000)}
                }, 'control': 0.80, 'wild_pitch_rate': 0.001
            },
        ]
    }
}