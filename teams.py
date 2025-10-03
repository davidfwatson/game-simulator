"""
This file contains the data for fictional baseball teams and players.
Each player has a name, position, and a dictionary of batting statistics.
The probabilities for each player's outcomes should sum to 1.0.
"""

TEAMS = {
    "SF_SEALS": {
        "name": "San Francisco Seals",
        "players": [
            {'name': 'Stitch Mitchell', 'position': 'CF', 'stats': {'Single': 0.16, 'Double': 0.06, 'Triple': 0.02, 'Home Run': 0.02, 'Walk': 0.09, 'Strikeout': 0.15, 'Groundout': 0.25, 'Flyout': 0.25}},
            {'name': 'Lefty O\'Toole', 'position': 'RF', 'stats': {'Single': 0.18, 'Double': 0.07, 'Triple': 0.01, 'Home Run': 0.04, 'Walk': 0.10, 'Strikeout': 0.14, 'Groundout': 0.23, 'Flyout': 0.23}},
            {'name': 'Buster Posey Jr.', 'position': 'C', 'stats': {'Single': 0.17, 'Double': 0.08, 'Triple': 0.01, 'Home Run': 0.05, 'Walk': 0.12, 'Strikeout': 0.12, 'Groundout': 0.22, 'Flyout': 0.23}},
            {'name': 'Willie Mays Jr.', 'position': 'LF', 'stats': {'Single': 0.15, 'Double': 0.05, 'Triple': 0.02, 'Home Run': 0.08, 'Walk': 0.11, 'Strikeout': 0.18, 'Groundout': 0.20, 'Flyout': 0.21}},
            {'name': 'Frankie Crosetti', 'position': 'SS', 'stats': {'Single': 0.14, 'Double': 0.04, 'Triple': 0.01, 'Home Run': 0.01, 'Walk': 0.07, 'Strikeout': 0.19, 'Groundout': 0.27, 'Flyout': 0.27}},
            {'name': 'Jimmy "The Kid"', 'position': '2B', 'stats': {'Single': 0.19, 'Double': 0.04, 'Triple': 0.01, 'Home Run': 0.01, 'Walk': 0.06, 'Strikeout': 0.10, 'Groundout': 0.30, 'Flyout': 0.29}},
            {'name': '"Ducky" Wucky', 'position': '1B', 'stats': {'Single': 0.13, 'Double': 0.06, 'Triple': 0.00, 'Home Run': 0.06, 'Walk': 0.08, 'Strikeout': 0.22, 'Groundout': 0.22, 'Flyout': 0.23}},
            {'name': 'Casey Stengel', 'position': '3B', 'stats': {'Single': 0.15, 'Double': 0.05, 'Triple': 0.01, 'Home Run': 0.03, 'Walk': 0.09, 'Strikeout': 0.17, 'Groundout': 0.25, 'Flyout': 0.25}},
            {'name': 'Smokey Joe', 'position': 'P', 'stats': {'Single': 0.08, 'Double': 0.02, 'Triple': 0.00, 'Home Run': 0.01, 'Walk': 0.04, 'Strikeout': 0.35, 'Groundout': 0.25, 'Flyout': 0.25}},
        ]
    },
    "OAK_OAKS": {
        "name": "Oakland Oaks",
        "players": [
            {'name': 'Billy Martin', 'position': '2B', 'stats': {'Single': 0.17, 'Double': 0.05, 'Triple': 0.01, 'Home Run': 0.02, 'Walk': 0.07, 'Strikeout': 0.16, 'Groundout': 0.26, 'Flyout': 0.26}},
            {'name': '"Spider" Hughes', 'position': 'CF', 'stats': {'Single': 0.15, 'Double': 0.04, 'Triple': 0.03, 'Home Run': 0.01, 'Walk': 0.08, 'Strikeout': 0.18, 'Groundout': 0.25, 'Flyout': 0.26}},
            {'name': '"Cookie" Lavagetto', 'position': '3B', 'stats': {'Single': 0.16, 'Double': 0.06, 'Triple': 0.01, 'Home Run': 0.04, 'Walk': 0.11, 'Strikeout': 0.15, 'Groundout': 0.23, 'Flyout': 0.24}},
            {'name': 'Buzz Arlett', 'position': 'RF', 'stats': {'Single': 0.14, 'Double': 0.05, 'Triple': 0.01, 'Home Run': 0.09, 'Walk': 0.12, 'Strikeout': 0.21, 'Groundout': 0.19, 'Flyout': 0.19}},
            {'name': 'Gene Ransom', 'position': 'LF', 'stats': {'Single': 0.18, 'Double': 0.07, 'Triple': 0.02, 'Home Run': 0.03, 'Walk': 0.08, 'Strikeout': 0.13, 'Groundout': 0.24, 'Flyout': 0.25}},
            {'name': '"Nine" Gordon', 'position': '1B', 'stats': {'Single': 0.15, 'Double': 0.07, 'Triple': 0.00, 'Home Run': 0.07, 'Walk': 0.09, 'Strikeout': 0.20, 'Groundout': 0.21, 'Flyout': 0.21}},
            {'name': 'Ernie Lombardi', 'position': 'C', 'stats': {'Single': 0.16, 'Double': 0.04, 'Triple': 0.00, 'Home Run': 0.03, 'Walk': 0.07, 'Strikeout': 0.15, 'Groundout': 0.27, 'Flyout': 0.28}},
            {'name': 'Artie Wilson', 'position': 'SS', 'stats': {'Single': 0.20, 'Double': 0.05, 'Triple': 0.02, 'Home Run': 0.01, 'Walk': 0.05, 'Strikeout': 0.08, 'Groundout': 0.29, 'Flyout': 0.30}},
            {'name': '"Lefty" Gomez', 'position': 'P', 'stats': {'Single': 0.09, 'Double': 0.01, 'Triple': 0.00, 'Home Run': 0.00, 'Walk': 0.05, 'Strikeout': 0.38, 'Groundout': 0.24, 'Flyout': 0.23}},
        ]
    }
}
