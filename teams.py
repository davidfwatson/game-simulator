"""
This file contains the data for fictional baseball teams and players
for a modern MLB-style simulation.
- Pitchers have stamina and do not bat.
- A Designated Hitter (DH) is included in the lineup.
- Each team has a bullpen with specific reliever roles.
- Teams have fielding and double play ratings.
- Player names are structured with legal_name and nickname.
- Pitch velocities are defined as a range [min, max].
- Fielding positions are coded to standard baseball notation (1-9).
"""

TEAMS = {
    "BAY_BOMBERS": {
        "name": "Bay Area Bombers",
        "park": "Bomber Stadium",
        "umpires": {"HP": "John Doe", "1B": "Jane Smith", "2B": "Peter Pan", "3B": "Mary Poppins"},
        "fielding_prowess": 0.982,
        "double_play_rate": 0.14,
        "players": [
            # Batting Order
            {'legal_name': 'Leo Vance', 'nickname': None, 'position': 'CF', 'fielding_position': 8, 'handedness': 'L', 'stats': {'Single': 0.16, 'Double': 0.06, 'Triple': 0.02, 'Home Run': 0.02, 'Walk': 0.09, 'Strikeout': 0.15, 'Groundout': 0.25, 'Flyout': 0.25}},
            {'legal_name': 'Marcus Thorne', 'nickname': None, 'position': 'RF', 'fielding_position': 9, 'handedness': 'L', 'stats': {'Single': 0.18, 'Double': 0.07, 'Triple': 0.01, 'Home Run': 0.04, 'Walk': 0.10, 'Strikeout': 0.14, 'Groundout': 0.23, 'Flyout': 0.23}},
            {'legal_name': 'Sam Decker', 'nickname': None, 'position': 'C', 'fielding_position': 2, 'handedness': 'R', 'stats': {'Single': 0.17, 'Double': 0.08, 'Triple': 0.01, 'Home Run': 0.05, 'Walk': 0.12, 'Strikeout': 0.12, 'Groundout': 0.22, 'Flyout': 0.23}},
            {'legal_name': 'Jackson Riley', 'nickname': 'Jax', 'position': 'DH', 'fielding_position': 0, 'handedness': 'R', 'stats': {'Single': 0.15, 'Double': 0.05, 'Triple': 0.02, 'Home Run': 0.08, 'Walk': 0.11, 'Strikeout': 0.18, 'Groundout': 0.20, 'Flyout': 0.21}},
            {'legal_name': 'Caleb Jones', 'nickname': None, 'position': 'SS', 'fielding_position': 6, 'handedness': 'R', 'stats': {'Single': 0.14, 'Double': 0.04, 'Triple': 0.01, 'Home Run': 0.01, 'Walk': 0.07, 'Strikeout': 0.19, 'Groundout': 0.27, 'Flyout': 0.27}},
            {'legal_name': 'Nate Diaz', 'nickname': 'Kid', 'position': '2B', 'fielding_position': 4, 'handedness': 'R', 'stats': {'Single': 0.19, 'Double': 0.04, 'Triple': 0.01, 'Home Run': 0.01, 'Walk': 0.06, 'Strikeout': 0.10, 'Groundout': 0.30, 'Flyout': 0.29}},
            {'legal_name': 'Owen Chen', 'nickname': 'Big Duck', 'position': '1B', 'fielding_position': 3, 'handedness': 'L', 'stats': {'Single': 0.13, 'Double': 0.06, 'Triple': 0.00, 'Home Run': 0.06, 'Walk': 0.08, 'Strikeout': 0.22, 'Groundout': 0.22, 'Flyout': 0.23}},
            {'legal_name': 'Miles Corbin', 'nickname': None, 'position': '3B', 'fielding_position': 5, 'handedness': 'S', 'stats': {'Single': 0.15, 'Double': 0.05, 'Triple': 0.01, 'Home Run': 0.03, 'Walk': 0.09, 'Strikeout': 0.17, 'Groundout': 0.25, 'Flyout': 0.25}},
            {'legal_name': 'Grant Fisher', 'nickname': None, 'position': 'LF', 'fielding_position': 7, 'handedness': 'R', 'stats': {'Single': 0.16, 'Double': 0.05, 'Triple': 0.01, 'Home Run': 0.05, 'Walk': 0.08, 'Strikeout': 0.19, 'Groundout': 0.23, 'Flyout': 0.23}},
            # Pitchers
            {
                'legal_name': 'Joe Gibson', 'nickname': 'Smokey', 'position': 'P', 'fielding_position': 1, 'handedness': 'R', 'type': 'Starter', 'stamina': 75,
                'pitch_arsenal': {
                    'FF': {'prob': 0.5, 'velo_range': (93, 97)}, # 4-Seam Fastball
                    'SL': {'prob': 0.25, 'velo_range': (86, 89)}, # Slider
                    'CH': {'prob': 0.15, 'velo_range': (81, 84)}, # Changeup
                    'FT': {'prob': 0.10, 'velo_range': (92, 95)}, # 2-Seam Fastball
                }, 'control': 0.65
            },
            {
                'legal_name': 'Miller', 'nickname': 'Cyclone', 'position': 'P', 'fielding_position': 1, 'handedness': 'R', 'type': 'Long Reliever', 'stamina': 45,
                'pitch_arsenal': {
                    'SI': {'prob': 0.6, 'velo_range': (91, 94)}, # Sinker
                    'SL': {'prob': 0.4, 'velo_range': (85, 88)}, # Slider
                }, 'control': 0.60
            },
            {
                'legal_name': 'Adams', 'nickname': 'Ace', 'position': 'P', 'fielding_position': 1, 'handedness': 'L', 'type': 'Middle Reliever', 'stamina': 25,
                'pitch_arsenal': {
                    'FF': {'prob': 0.5, 'velo_range': (92, 95)},
                    'KC': {'prob': 0.5, 'velo_range': (77, 81)}, # Knuckle-Curve
                }, 'control': 0.70
            },
            {
                'legal_name': 'Victor Stone', 'nickname': 'The Vulture', 'position': 'P', 'fielding_position': 1, 'handedness': 'R', 'type': 'Closer', 'stamina': 20,
                'pitch_arsenal': {
                    'CT': {'prob': 0.4, 'velo_range': (90, 93)}, # Cutter
                    'FF': {'prob': 0.4, 'velo_range': (95, 98)},
                    'SL': {'prob': 0.2, 'velo_range': (88, 91)},
                }, 'control': 0.75
            },
        ]
    },
    "PC_PILOTS": {
        "name": "Pacific City Pilots",
        "park": "Pilots Field",
        "umpires": {"HP": "Clark Kent", "1B": "Bruce Wayne", "2B": "Diana Prince", "3B": "Barry Allen"},
        "fielding_prowess": 0.975,
        "double_play_rate": 0.13,
        "players": [
            # Batting Order
            {'legal_name': 'Alex Chase', 'nickname': None, 'position': '2B', 'fielding_position': 4, 'handedness': 'R', 'stats': {'Single': 0.17, 'Double': 0.05, 'Triple': 0.01, 'Home Run': 0.02, 'Walk': 0.07, 'Strikeout': 0.16, 'Groundout': 0.26, 'Flyout': 0.26}},
            {'legal_name': 'Kevin Webb', 'nickname': 'Spider', 'position': 'CF', 'fielding_position': 8, 'handedness': 'L', 'stats': {'Single': 0.15, 'Double': 0.04, 'Triple': 0.03, 'Home Run': 0.01, 'Walk': 0.08, 'Strikeout': 0.18, 'Groundout': 0.25, 'Flyout': 0.26}},
            {'legal_name': 'Omar Ramirez', 'nickname': 'Cookie', 'position': '3B', 'fielding_position': 5, 'handedness': 'R', 'stats': {'Single': 0.16, 'Double': 0.06, 'Triple': 0.01, 'Home Run': 0.04, 'Walk': 0.11, 'Strikeout': 0.15, 'Groundout': 0.23, 'Flyout': 0.24}},
            {'legal_name': 'Rex Power', 'nickname': 'Buzz', 'position': 'DH', 'fielding_position': 0, 'handedness': 'R', 'stats': {'Single': 0.14, 'Double': 0.05, 'Triple': 0.01, 'Home Run': 0.09, 'Walk': 0.12, 'Strikeout': 0.21, 'Groundout': 0.19, 'Flyout': 0.19}},
            {'legal_name': 'Evan Reed', 'nickname': None, 'position': 'LF', 'fielding_position': 7, 'handedness': 'L', 'stats': {'Single': 0.18, 'Double': 0.07, 'Triple': 0.02, 'Home Run': 0.03, 'Walk': 0.08, 'Strikeout': 0.13, 'Groundout': 0.24, 'Flyout': 0.25}},
            {'legal_name': 'Felix Washington', 'nickname': 'Nine', 'position': '1B', 'fielding_position': 3, 'handedness': 'L', 'stats': {'Single': 0.15, 'Double': 0.07, 'Triple': 0.00, 'Home Run': 0.07, 'Walk': 0.09, 'Strikeout': 0.20, 'Groundout': 0.21, 'Flyout': 0.21}},
            {'legal_name': 'Hank Barrett', 'nickname': None, 'position': 'C', 'fielding_position': 2, 'handedness': 'R', 'stats': {'Single': 0.16, 'Double': 0.04, 'Triple': 0.00, 'Home Run': 0.03, 'Walk': 0.07, 'Strikeout': 0.15, 'Groundout': 0.27, 'Flyout': 0.28}},
            {'legal_name': 'Wes Griffin', 'nickname': None, 'position': 'SS', 'fielding_position': 6, 'handedness': 'S', 'stats': {'Single': 0.20, 'Double': 0.05, 'Triple': 0.02, 'Home Run': 0.01, 'Walk': 0.05, 'Strikeout': 0.08, 'Groundout': 0.29, 'Flyout': 0.30}},
            {'legal_name': 'TJ Hawkins', 'nickname': None, 'position': 'RF', 'fielding_position': 9, 'handedness': 'R', 'stats': {'Single': 0.19, 'Double': 0.06, 'Triple': 0.01, 'Home Run': 0.04, 'Walk': 0.09, 'Strikeout': 0.12, 'Groundout': 0.25, 'Flyout': 0.24}},
            # Pitchers
            {
                'legal_name': 'Garcia', 'nickname': 'Lefty', 'position': 'P', 'fielding_position': 1, 'handedness': 'L', 'type': 'Starter', 'stamina': 70,
                'pitch_arsenal': {
                    'FF': {'prob': 0.5, 'velo_range': (90, 94)},
                    'KC': {'prob': 0.3, 'velo_range': (78, 81)},
                    'SL': {'prob': 0.2, 'velo_range': (84, 87)},
                }, 'control': 0.60
            },
            {
                'legal_name': 'Logan', 'nickname': 'Chief', 'position': 'P', 'fielding_position': 1, 'handedness': 'R', 'type': 'Long Reliever', 'stamina': 50,
                'pitch_arsenal': {
                    'FF': {'prob': 0.7, 'velo_range': (92, 96)},
                    'CB': {'prob': 0.3, 'velo_range': (79, 82)}, # Curveball
                }, 'control': 0.68
            },
            {
                'legal_name': 'Malone', 'nickname': 'Fingers', 'position': 'P', 'fielding_position': 1, 'handedness': 'R', 'type': 'Middle Reliever', 'stamina': 30,
                'pitch_arsenal': {
                    'SI': {'prob': 0.6, 'velo_range': (90, 93)},
                    'SL': {'prob': 0.4, 'velo_range': (85, 88)},
                }, 'control': 0.72
            },
            {
                'legal_name': 'Thompson', 'nickname': 'Eck', 'position': 'P', 'fielding_position': 1, 'handedness': 'R', 'type': 'Closer', 'stamina': 22,
                'pitch_arsenal': {
                    'FF': {'prob': 0.6, 'velo_range': (97, 100)},
                    'SL': {'prob': 0.4, 'velo_range': (89, 92)},
                }, 'control': 0.80
            },
        ]
    }
}