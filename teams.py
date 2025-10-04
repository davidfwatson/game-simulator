"""
This file contains the data for fictional baseball teams and players
for a modern MLB-style simulation.
- Pitchers have stamina and do not bat.
- A Designated Hitter (DH) is included in the lineup.
- Each team has a bullpen with specific reliever roles.
- Teams have fielding and double play ratings.
"""

TEAMS = {
    "BAY_BOMBERS": {
        "name": "Bay Area Bombers",
        "fielding_prowess": 0.982,  # Higher is better
        "double_play_rate": 0.14, # Likelihood of turning a DP on a groundball
        "players": [
            # Batting Order
            {'name': 'Leo Vance', 'position': 'CF', 'handedness': 'L', 'stats': {'Single': 0.16, 'Double': 0.06, 'Triple': 0.02, 'Home Run': 0.02, 'Walk': 0.09, 'Strikeout': 0.15, 'Groundout': 0.25, 'Flyout': 0.25}},
            {'name': 'Marcus Thorne', 'position': 'RF', 'handedness': 'L', 'stats': {'Single': 0.18, 'Double': 0.07, 'Triple': 0.01, 'Home Run': 0.04, 'Walk': 0.10, 'Strikeout': 0.14, 'Groundout': 0.23, 'Flyout': 0.23}},
            {'name': 'Sam Decker', 'position': 'C', 'handedness': 'R', 'stats': {'Single': 0.17, 'Double': 0.08, 'Triple': 0.01, 'Home Run': 0.05, 'Walk': 0.12, 'Strikeout': 0.12, 'Groundout': 0.22, 'Flyout': 0.23}},
            {'name': 'Jackson "Jax" Riley', 'position': 'DH', 'handedness': 'R', 'stats': {'Single': 0.15, 'Double': 0.05, 'Triple': 0.02, 'Home Run': 0.08, 'Walk': 0.11, 'Strikeout': 0.18, 'Groundout': 0.20, 'Flyout': 0.21}},
            {'name': 'Caleb Jones', 'position': 'SS', 'handedness': 'R', 'stats': {'Single': 0.14, 'Double': 0.04, 'Triple': 0.01, 'Home Run': 0.01, 'Walk': 0.07, 'Strikeout': 0.19, 'Groundout': 0.27, 'Flyout': 0.27}},
            {'name': 'Nate "Kid" Diaz', 'position': '2B', 'handedness': 'R', 'stats': {'Single': 0.19, 'Double': 0.04, 'Triple': 0.01, 'Home Run': 0.01, 'Walk': 0.06, 'Strikeout': 0.10, 'Groundout': 0.30, 'Flyout': 0.29}},
            {'name': 'Owen "Big Duck" Chen', 'position': '1B', 'handedness': 'L', 'stats': {'Single': 0.13, 'Double': 0.06, 'Triple': 0.00, 'Home Run': 0.06, 'Walk': 0.08, 'Strikeout': 0.22, 'Groundout': 0.22, 'Flyout': 0.23}},
            {'name': 'Miles Corbin', 'position': '3B', 'handedness': 'S', 'stats': {'Single': 0.15, 'Double': 0.05, 'Triple': 0.01, 'Home Run': 0.03, 'Walk': 0.09, 'Strikeout': 0.17, 'Groundout': 0.25, 'Flyout': 0.25}},
            {'name': 'Grant Fisher', 'position': 'LF', 'handedness': 'R', 'stats': {'Single': 0.16, 'Double': 0.05, 'Triple': 0.01, 'Home Run': 0.05, 'Walk': 0.08, 'Strikeout': 0.19, 'Groundout': 0.23, 'Flyout': 0.23}},
            # Pitchers
            {
                'name': '"Smokey" Joe Gibson', 'position': 'P', 'handedness': 'R', 'type': 'Starter', 'stamina': 75,
                'pitch_arsenal': {
                    'Fastball': {'prob': 0.6, 'velo': 95},
                    'Slider': {'prob': 0.25, 'velo': 88},
                    'Changeup': {'prob': 0.15, 'velo': 82}
                }, 'control': 0.65
            },
            {
                'name': '"Cyclone" Miller', 'position': 'P', 'handedness': 'R', 'type': 'Long Reliever', 'stamina': 45,
                'pitch_arsenal': {'Sinker': {'prob': 0.7, 'velo': 92}, 'Slider': {'prob': 0.3, 'velo': 87}}, 'control': 0.60
            },
            {
                'name': '"Ace" Adams', 'position': 'P', 'handedness': 'L', 'type': 'Middle Reliever', 'stamina': 25,
                'pitch_arsenal': {'Fastball': {'prob': 0.5, 'velo': 93}, 'Curveball': {'prob': 0.5, 'velo': 78}}, 'control': 0.70
            },
            {
                'name': 'Victor "The Vulture" Stone', 'position': 'P', 'handedness': 'R', 'type': 'Closer', 'stamina': 20,
                'pitch_arsenal': {
                    'Cutter': {'prob': 0.4, 'velo': 91},
                    'Fastball': {'prob': 0.4, 'velo': 96},
                    'Slider': {'prob': 0.2, 'velo': 89}
                }, 'control': 0.75
            },
        ]
    },
    "PC_PILOTS": {
        "name": "Pacific City Pilots",
        "fielding_prowess": 0.975,
        "double_play_rate": 0.13,
        "players": [
            # Batting Order
            {'name': 'Alex Chase', 'position': '2B', 'handedness': 'R', 'stats': {'Single': 0.17, 'Double': 0.05, 'Triple': 0.01, 'Home Run': 0.02, 'Walk': 0.07, 'Strikeout': 0.16, 'Groundout': 0.26, 'Flyout': 0.26}},
            {'name': 'Kevin "Spider" Webb', 'position': 'CF', 'handedness': 'L', 'stats': {'Single': 0.15, 'Double': 0.04, 'Triple': 0.03, 'Home Run': 0.01, 'Walk': 0.08, 'Strikeout': 0.18, 'Groundout': 0.25, 'Flyout': 0.26}},
            {'name': 'Omar "Cookie" Ramirez', 'position': '3B', 'handedness': 'R', 'stats': {'Single': 0.16, 'Double': 0.06, 'Triple': 0.01, 'Home Run': 0.04, 'Walk': 0.11, 'Strikeout': 0.15, 'Groundout': 0.23, 'Flyout': 0.24}},
            {'name': 'Rex "Buzz" Power', 'position': 'DH', 'handedness': 'R', 'stats': {'Single': 0.14, 'Double': 0.05, 'Triple': 0.01, 'Home Run': 0.09, 'Walk': 0.12, 'Strikeout': 0.21, 'Groundout': 0.19, 'Flyout': 0.19}},
            {'name': 'Evan Reed', 'position': 'LF', 'handedness': 'L', 'stats': {'Single': 0.18, 'Double': 0.07, 'Triple': 0.02, 'Home Run': 0.03, 'Walk': 0.08, 'Strikeout': 0.13, 'Groundout': 0.24, 'Flyout': 0.25}},
            {'name': 'Felix "Nine" Washington', 'position': '1B', 'handedness': 'L', 'stats': {'Single': 0.15, 'Double': 0.07, 'Triple': 0.00, 'Home Run': 0.07, 'Walk': 0.09, 'Strikeout': 0.20, 'Groundout': 0.21, 'Flyout': 0.21}},
            {'name': 'Hank Barrett', 'position': 'C', 'handedness': 'R', 'stats': {'Single': 0.16, 'Double': 0.04, 'Triple': 0.00, 'Home Run': 0.03, 'Walk': 0.07, 'Strikeout': 0.15, 'Groundout': 0.27, 'Flyout': 0.28}},
            {'name': 'Wes Griffin', 'position': 'SS', 'handedness': 'S', 'stats': {'Single': 0.20, 'Double': 0.05, 'Triple': 0.02, 'Home Run': 0.01, 'Walk': 0.05, 'Strikeout': 0.08, 'Groundout': 0.29, 'Flyout': 0.30}},
            {'name': 'TJ Hawkins', 'position': 'RF', 'handedness': 'R', 'stats': {'Single': 0.19, 'Double': 0.06, 'Triple': 0.01, 'Home Run': 0.04, 'Walk': 0.09, 'Strikeout': 0.12, 'Groundout': 0.25, 'Flyout': 0.24}},
            # Pitchers
            {
                'name': '"Lefty" Garcia', 'position': 'P', 'handedness': 'L', 'type': 'Starter', 'stamina': 70,
                'pitch_arsenal': {
                    'Fastball': {'prob': 0.5, 'velo': 92},
                    'Curveball': {'prob': 0.3, 'velo': 79},
                    'Slider': {'prob': 0.2, 'velo': 85}
                }, 'control': 0.60
            },
            {
                'name': '"Chief" Logan', 'position': 'P', 'handedness': 'R', 'type': 'Long Reliever', 'stamina': 50,
                'pitch_arsenal': {'Fastball': {'prob': 0.7, 'velo': 94}, 'Curveball': {'prob': 0.3, 'velo': 80}}, 'control': 0.68
            },
            {
                'name': '"Fingers" Malone', 'position': 'P', 'handedness': 'R', 'type': 'Middle Reliever', 'stamina': 30,
                'pitch_arsenal': {'Sinker': {'prob': 0.6, 'velo': 91}, 'Slider': {'prob': 0.4, 'velo': 86}}, 'control': 0.72
            },
            {
                'name': '"Eck" Thompson', 'position': 'P', 'handedness': 'R', 'type': 'Closer', 'stamina': 22,
                'pitch_arsenal': {'Fastball': {'prob': 0.6, 'velo': 98}, 'Slider': {'prob': 0.4, 'velo': 90}}, 'control': 0.80
            },
        ]
    }
}