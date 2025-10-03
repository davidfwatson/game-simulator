"""
This file contains the data for fictional baseball teams and players
for a modern MLB-style simulation.
- Pitchers have stamina and do not bat.
- A Designated Hitter (DH) is included in the lineup.
- Each team has a bullpen of relief pitchers.
"""

TEAMS = {
    "SF_SEALS": {
        "name": "San Francisco Seals",
        "players": [
            # Batting Order
            {'name': 'Stitch Mitchell', 'position': 'CF', 'handedness': 'L', 'stats': {'Single': 0.16, 'Double': 0.06, 'Triple': 0.02, 'Home Run': 0.02, 'Walk': 0.09, 'Strikeout': 0.15, 'Groundout': 0.25, 'Flyout': 0.25}},
            {'name': 'Lefty O\'Toole', 'position': 'RF', 'handedness': 'L', 'stats': {'Single': 0.18, 'Double': 0.07, 'Triple': 0.01, 'Home Run': 0.04, 'Walk': 0.10, 'Strikeout': 0.14, 'Groundout': 0.23, 'Flyout': 0.23}},
            {'name': 'Buster Posey Jr.', 'position': 'C', 'handedness': 'R', 'stats': {'Single': 0.17, 'Double': 0.08, 'Triple': 0.01, 'Home Run': 0.05, 'Walk': 0.12, 'Strikeout': 0.12, 'Groundout': 0.22, 'Flyout': 0.23}},
            {'name': 'Willie Mays Jr.', 'position': 'DH', 'handedness': 'R', 'stats': {'Single': 0.15, 'Double': 0.05, 'Triple': 0.02, 'Home Run': 0.08, 'Walk': 0.11, 'Strikeout': 0.18, 'Groundout': 0.20, 'Flyout': 0.21}},
            {'name': 'Frankie Crosetti', 'position': 'SS', 'handedness': 'R', 'stats': {'Single': 0.14, 'Double': 0.04, 'Triple': 0.01, 'Home Run': 0.01, 'Walk': 0.07, 'Strikeout': 0.19, 'Groundout': 0.27, 'Flyout': 0.27}},
            {'name': 'Jimmy "The Kid"', 'position': '2B', 'handedness': 'R', 'stats': {'Single': 0.19, 'Double': 0.04, 'Triple': 0.01, 'Home Run': 0.01, 'Walk': 0.06, 'Strikeout': 0.10, 'Groundout': 0.30, 'Flyout': 0.29}},
            {'name': '"Ducky" Wucky', 'position': '1B', 'handedness': 'L', 'stats': {'Single': 0.13, 'Double': 0.06, 'Triple': 0.00, 'Home Run': 0.06, 'Walk': 0.08, 'Strikeout': 0.22, 'Groundout': 0.22, 'Flyout': 0.23}},
            {'name': 'Casey Stengel', 'position': '3B', 'handedness': 'S', 'stats': {'Single': 0.15, 'Double': 0.05, 'Triple': 0.01, 'Home Run': 0.03, 'Walk': 0.09, 'Strikeout': 0.17, 'Groundout': 0.25, 'Flyout': 0.25}},
            {'name': 'Bobby Thomson', 'position': 'LF', 'handedness': 'R', 'stats': {'Single': 0.16, 'Double': 0.05, 'Triple': 0.01, 'Home Run': 0.05, 'Walk': 0.08, 'Strikeout': 0.19, 'Groundout': 0.23, 'Flyout': 0.23}},
            # Pitchers
            {
                'name': 'Smokey Joe', 'position': 'P', 'handedness': 'R', 'type': 'Starter', 'stamina': 100,
                'pitch_arsenal': {'Fastball': 0.6, 'Slider': 0.25, 'Changeup': 0.15}, 'control': 0.65
            },
            {
                'name': 'Cyclone Miller', 'position': 'P', 'handedness': 'R', 'type': 'Reliever', 'stamina': 30,
                'pitch_arsenal': {'Sinker': 0.7, 'Slider': 0.3}, 'control': 0.60
            },
            {
                'name': 'Ace Adams', 'position': 'P', 'handedness': 'L', 'type': 'Reliever', 'stamina': 25,
                'pitch_arsenal': {'Fastball': 0.5, 'Curveball': 0.5}, 'control': 0.70
            },
            {
                'name': 'The Undertaker', 'position': 'P', 'handedness': 'R', 'type': 'Closer', 'stamina': 20,
                'pitch_arsenal': {'Cutter': 0.4, 'Fastball': 0.4, 'Slider': 0.2}, 'control': 0.75
            },
        ]
    },
    "OAK_OAKS": {
        "name": "Oakland Oaks",
        "players": [
            # Batting Order
            {'name': 'Billy Martin', 'position': '2B', 'handedness': 'R', 'stats': {'Single': 0.17, 'Double': 0.05, 'Triple': 0.01, 'Home Run': 0.02, 'Walk': 0.07, 'Strikeout': 0.16, 'Groundout': 0.26, 'Flyout': 0.26}},
            {'name': '"Spider" Hughes', 'position': 'CF', 'handedness': 'L', 'stats': {'Single': 0.15, 'Double': 0.04, 'Triple': 0.03, 'Home Run': 0.01, 'Walk': 0.08, 'Strikeout': 0.18, 'Groundout': 0.25, 'Flyout': 0.26}},
            {'name': '"Cookie" Lavagetto', 'position': '3B', 'handedness': 'R', 'stats': {'Single': 0.16, 'Double': 0.06, 'Triple': 0.01, 'Home Run': 0.04, 'Walk': 0.11, 'Strikeout': 0.15, 'Groundout': 0.23, 'Flyout': 0.24}},
            {'name': 'Buzz Arlett', 'position': 'DH', 'handedness': 'R', 'stats': {'Single': 0.14, 'Double': 0.05, 'Triple': 0.01, 'Home Run': 0.09, 'Walk': 0.12, 'Strikeout': 0.21, 'Groundout': 0.19, 'Flyout': 0.19}},
            {'name': 'Gene Ransom', 'position': 'LF', 'handedness': 'L', 'stats': {'Single': 0.18, 'Double': 0.07, 'Triple': 0.02, 'Home Run': 0.03, 'Walk': 0.08, 'Strikeout': 0.13, 'Groundout': 0.24, 'Flyout': 0.25}},
            {'name': '"Nine" Gordon', 'position': '1B', 'handedness': 'L', 'stats': {'Single': 0.15, 'Double': 0.07, 'Triple': 0.00, 'Home Run': 0.07, 'Walk': 0.09, 'Strikeout': 0.20, 'Groundout': 0.21, 'Flyout': 0.21}},
            {'name': 'Ernie Lombardi', 'position': 'C', 'handedness': 'R', 'stats': {'Single': 0.16, 'Double': 0.04, 'Triple': 0.00, 'Home Run': 0.03, 'Walk': 0.07, 'Strikeout': 0.15, 'Groundout': 0.27, 'Flyout': 0.28}},
            {'name': 'Artie Wilson', 'position': 'SS', 'handedness': 'S', 'stats': {'Single': 0.20, 'Double': 0.05, 'Triple': 0.02, 'Home Run': 0.01, 'Walk': 0.05, 'Strikeout': 0.08, 'Groundout': 0.29, 'Flyout': 0.30}},
            {'name': 'Ike Boone', 'position': 'RF', 'handedness': 'R', 'stats': {'Single': 0.19, 'Double': 0.06, 'Triple': 0.01, 'Home Run': 0.04, 'Walk': 0.09, 'Strikeout': 0.12, 'Groundout': 0.25, 'Flyout': 0.24}},
            # Pitchers
            {
                'name': '"Lefty" Gomez', 'position': 'P', 'handedness': 'L', 'type': 'Starter', 'stamina': 95,
                'pitch_arsenal': {'Fastball': 0.5, 'Curveball': 0.3, 'Slider': 0.2}, 'control': 0.60
            },
            {
                'name': 'Chief Bender', 'position': 'P', 'handedness': 'R', 'type': 'Reliever', 'stamina': 40,
                'pitch_arsenal': {'Fastball': 0.7, 'Curveball': 0.3}, 'control': 0.68
            },
            {
                'name': 'Rollie Fingers', 'position': 'P', 'handedness': 'R', 'type': 'Reliever', 'stamina': 28,
                'pitch_arsenal': {'Sinker': 0.6, 'Slider': 0.4}, 'control': 0.72
            },
            {
                'name': 'Dennis Eckersley', 'position': 'P', 'handedness': 'R', 'type': 'Closer', 'stamina': 22,
                'pitch_arsenal': {'Fastball': 0.6, 'Slider': 0.4}, 'control': 0.80
            },
        ]
    }
}

