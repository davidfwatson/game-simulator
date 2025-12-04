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

TEAMS = {
    "BAY_BOMBERS": {
        "id": 133,
        "name": "Bay Area Bombers",
        "abbreviation": "BAY",
        "teamName": "Bombers",
        "venue": "Waterfront Park",
        "fielding_prowess": 0.982,
        "double_play_rate": 0.42,
        "hbp_rate": 0.004,  # Likelihood of a HBP per at-bat
        "players": [
            # Batting Order
            {'id': 545101, 'legal_name': 'Leo Vance', 'nickname': None, 'position': {'code': '8', 'name': 'Center Field', 'abbreviation': 'CF'}, 'batSide': {'code': 'L', 'description': 'Left'}, 'fielding_ability': 0.988, 'plate_discipline': {'Walk': 0.10, 'Strikeout': 0.15, 'HBP': 0.005}, 'batting_profile': {'contact': 0.75, 'power': 0.40, 'angle': 12.0, 'bunt_propensity': 0.4, 'stealing_tendency': 0.016, 'stealing_success_rate': 0.79}},
            {'id': 545102, 'legal_name': 'Marcus Thorne', 'nickname': None, 'position': {'code': '9', 'name': 'Right Field', 'abbreviation': 'RF'}, 'batSide': {'code': 'L', 'description': 'Left'}, 'fielding_ability': 0.981, 'plate_discipline': {'Walk': 0.11, 'Strikeout': 0.14, 'HBP': 0.004}, 'batting_profile': {'contact': 0.80, 'power': 0.55, 'angle': 12.0, 'bunt_propensity': 0.1, 'stealing_tendency': 0.016, 'stealing_success_rate': 0.79}},
            {'id': 545103, 'legal_name': 'Sam Decker', 'nickname': None, 'position': {'code': '2', 'name': 'Catcher', 'abbreviation': 'C'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.995, 'catchers_arm': 0.8, 'passed_ball_rate': 0.002, 'plate_discipline': {'Walk': 0.13, 'Strikeout': 0.12, 'HBP': 0.003}, 'batting_profile': {'contact': 0.85, 'power': 0.65, 'angle': 14.0, 'bunt_propensity': 0.05, 'stealing_tendency': 0.001, 'stealing_success_rate': 0.6}},
            {'id': 545104, 'legal_name': 'Jackson Riley', 'nickname': 'Jax', 'position': {'code': 'D', 'name': 'Designated Hitter', 'abbreviation': 'DH'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.950, 'plate_discipline': {'Walk': 0.12, 'Strikeout': 0.18, 'HBP': 0.006}, 'batting_profile': {'contact': 0.70, 'power': 0.80, 'angle': 16.0, 'bunt_propensity': 0.02, 'stealing_tendency': 0.001, 'stealing_success_rate': 0.65}},
            {'id': 545105, 'legal_name': 'Caleb Jones', 'nickname': None, 'position': {'code': '6', 'name': 'Shortstop', 'abbreviation': 'SS'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.975, 'plate_discipline': {'Walk': 0.08, 'Strikeout': 0.19, 'HBP': 0.002}, 'batting_profile': {'contact': 0.65, 'power': 0.30, 'angle': 10.0, 'bunt_propensity': 0.3, 'stealing_tendency': 0.018, 'stealing_success_rate': 0.80}},
            {'id': 545106, 'legal_name': 'Nate Diaz', 'nickname': 'Kid', 'position': {'code': '4', 'name': 'Second Base', 'abbreviation': '2B'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.983, 'plate_discipline': {'Walk': 0.07, 'Strikeout': 0.10, 'HBP': 0.001}, 'batting_profile': {'contact': 0.90, 'power': 0.35, 'angle': 8.0, 'bunt_propensity': 0.5, 'stealing_tendency': 0.10, 'stealing_success_rate': 0.9}},
            {'id': 545107, 'legal_name': 'Owen Chen', 'nickname': 'Big Duck', 'position': {'code': '3', 'name': 'First Base', 'abbreviation': '1B'}, 'batSide': {'code': 'L', 'description': 'Left'}, 'fielding_ability': 0.991, 'plate_discipline': {'Walk': 0.09, 'Strikeout': 0.22, 'HBP': 0.005}, 'batting_profile': {'contact': 0.60, 'power': 0.70, 'angle': 15.0, 'bunt_propensity': 0.05, 'stealing_tendency': 0.001, 'stealing_success_rate': 0.6}},
            {'id': 545108, 'legal_name': 'Miles Corbin', 'nickname': None, 'position': {'code': '5', 'name': 'Third Base', 'abbreviation': '3B'}, 'batSide': {'code': 'S', 'description': 'Switch'}, 'fielding_ability': 0.965, 'plate_discipline': {'Walk': 0.10, 'Strikeout': 0.17, 'HBP': 0.003}, 'batting_profile': {'contact': 0.72, 'power': 0.50, 'angle': 12.0, 'bunt_propensity': 0.15, 'stealing_tendency': 0.015, 'stealing_success_rate': 0.75}},
            {'id': 545109, 'legal_name': 'Grant Fisher', 'nickname': None, 'position': {'code': '7', 'name': 'Left Field', 'abbreviation': 'LF'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.980, 'plate_discipline': {'Walk': 0.09, 'Strikeout': 0.19, 'HBP': 0.004}, 'batting_profile': {'contact': 0.68, 'power': 0.60, 'angle': 13.0, 'bunt_propensity': 0.1, 'stealing_tendency': 0.015, 'stealing_success_rate': 0.75}},
            # Pitchers
            {
                'id': 605110, 'legal_name': 'Joe Gibson', 'nickname': 'Smokey', 'position': {'code': '1', 'name': 'Pitcher', 'abbreviation': 'P'}, 'pitchHand': {'code': 'R', 'description': 'Right'}, 'type': 'Starter', 'stamina': 75, 'fielding_ability': 0.955,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.5, 'velo_range': (94, 97), 'spin_range': (2200, 2550)},
                    'slider': {'prob': 0.25, 'velo_range': (87, 90), 'spin_range': (2400, 2700)},
                    'changeup': {'prob': 0.15, 'velo_range': (81, 84), 'spin_range': (1600, 1900)},
                    'curveball': {'prob': 0.10, 'velo_range': (78, 81), 'spin_range': (2600, 2900)}
                }, 'control': 0.65, 'wild_pitch_rate': 0.003
            },
            {
                'id': 605111, 'legal_name': 'Colin Miller', 'nickname': 'Cyclone', 'position': {'code': '1', 'name': 'Pitcher', 'abbreviation': 'P'}, 'pitchHand': {'code': 'R', 'description': 'Right'}, 'type': 'Long Reliever', 'stamina': 45, 'fielding_ability': 0.950,
                'pitch_arsenal': {
                    'sinker': {'prob': 0.6, 'velo_range': (91, 94), 'spin_range': (2000, 2250)},
                    'slider': {'prob': 0.4, 'velo_range': (86, 88), 'spin_range': (2500, 2800)}
                }, 'control': 0.60, 'wild_pitch_rate': 0.005
            },
            {
                'id': 605112, 'legal_name': 'Adam Adams', 'nickname': 'Ace', 'position': {'code': '1', 'name': 'Pitcher', 'abbreviation': 'P'}, 'pitchHand': {'code': 'L', 'description': 'Left'}, 'type': 'Middle Reliever', 'stamina': 25, 'fielding_ability': 0.945,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.5, 'velo_range': (92, 95), 'spin_range': (2250, 2600)},
                    'knuckle curve': {'prob': 0.5, 'velo_range': (77, 80), 'spin_range': (2800, 3100)}
                }, 'control': 0.70, 'wild_pitch_rate': 0.002
            },
            {
                'id': 605113, 'legal_name': 'Victor Stone', 'nickname': 'The Vulture', 'position': {'code': '1', 'name': 'Pitcher', 'abbreviation': 'P'}, 'pitchHand': {'code': 'R', 'description': 'Right'}, 'type': 'Closer', 'stamina': 20, 'fielding_ability': 0.960,
                'pitch_arsenal': {
                    'cutter': {'prob': 0.4, 'velo_range': (90, 93), 'spin_range': (2300, 2650)},
                    'four-seam fastball': {'prob': 0.4, 'velo_range': (95, 98), 'spin_range': (2400, 2700)},
                    'slider': {'prob': 0.2, 'velo_range': (88, 91), 'spin_range': (2600, 2900)}
                }, 'control': 0.75, 'wild_pitch_rate': 0.001
            },
        ]
    },
    "PC_PILOTS": {
        "id": 134,
        "name": "Pacific City Pilots",
        "abbreviation": "PCP",
        "teamName": "Pilots",
        "venue": "Aero Field",
        "fielding_prowess": 0.975,
        "double_play_rate": 0.42,
        "hbp_rate": 0.0035,
        "players": [
            # Batting Order
            {'id': 625201, 'legal_name': 'Alex Chase', 'nickname': None, 'position': {'code': '4', 'name': 'Second Base', 'abbreviation': '2B'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.985, 'plate_discipline': {'Walk': 0.08, 'Strikeout': 0.16, 'HBP': 0.003}, 'batting_profile': {'contact': 0.78, 'power': 0.42, 'angle': 11.0, 'bunt_propensity': 0.4, 'stealing_tendency': 0.08, 'stealing_success_rate': 0.88}},
            {'id': 625202, 'legal_name': 'Kevin Webb', 'nickname': 'Spider', 'position': {'code': '8', 'name': 'Center Field', 'abbreviation': 'CF'}, 'batSide': {'code': 'L', 'description': 'Left'}, 'fielding_ability': 0.990, 'plate_discipline': {'Walk': 0.09, 'Strikeout': 0.18, 'HBP': 0.005}, 'batting_profile': {'contact': 0.70, 'power': 0.35, 'angle': 9.0, 'bunt_propensity': 0.5, 'stealing_tendency': 0.12, 'stealing_success_rate': 0.92}},
            {'id': 625203, 'legal_name': 'Omar Ramirez', 'nickname': 'Cookie', 'position': {'code': '5', 'name': 'Third Base', 'abbreviation': '3B'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.960, 'plate_discipline': {'Walk': 0.12, 'Strikeout': 0.15, 'HBP': 0.002}, 'batting_profile': {'contact': 0.82, 'power': 0.58, 'angle': 13.0, 'bunt_propensity': 0.1, 'stealing_tendency': 0.015, 'stealing_success_rate': 0.7}},
            {'id': 625204, 'legal_name': 'Rex Power', 'nickname': 'Buzz', 'position': {'code': 'D', 'name': 'Designated Hitter', 'abbreviation': 'DH'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.940, 'plate_discipline': {'Walk': 0.13, 'Strikeout': 0.21, 'HBP': 0.008}, 'batting_profile': {'contact': 0.65, 'power': 0.85, 'angle': 18.0, 'bunt_propensity': 0.01, 'stealing_tendency': 0.001, 'stealing_success_rate': 0.5}},
            {'id': 625205, 'legal_name': 'Evan Reed', 'nickname': None, 'position': {'code': '7', 'name': 'Left Field', 'abbreviation': 'LF'}, 'batSide': {'code': 'L', 'description': 'Left'}, 'fielding_ability': 0.978, 'plate_discipline': {'Walk': 0.09, 'Strikeout': 0.13, 'HBP': 0.004}, 'batting_profile': {'contact': 0.88, 'power': 0.50, 'angle': 14.0, 'bunt_propensity': 0.1, 'stealing_tendency': 0.015, 'stealing_success_rate': 0.75}},
            {'id': 625206, 'legal_name': 'Felix Washington', 'nickname': 'Nine', 'position': {'code': '3', 'name': 'First Base', 'abbreviation': '1B'}, 'batSide': {'code': 'L', 'description': 'Left'}, 'fielding_ability': 0.992, 'plate_discipline': {'Walk': 0.10, 'Strikeout': 0.20, 'HBP': 0.006}, 'batting_profile': {'contact': 0.68, 'power': 0.75, 'angle': 17.0, 'bunt_propensity': 0.05, 'stealing_tendency': 0.001, 'stealing_success_rate': 0.6}},
            {'id': 625207, 'legal_name': 'Hank Barrett', 'nickname': None, 'position': {'code': '2', 'name': 'Catcher', 'abbreviation': 'C'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.994, 'catchers_arm': 0.85, 'passed_ball_rate': 0.003, 'plate_discipline': {'Walk': 0.08, 'Strikeout': 0.15, 'HBP': 0.001}, 'batting_profile': {'contact': 0.80, 'power': 0.45, 'angle': 10.0, 'bunt_propensity': 0.25, 'stealing_tendency': 0.001, 'stealing_success_rate': 0.65}},
            {'id': 625208, 'legal_name': 'Wes Griffin', 'nickname': None, 'position': {'code': '6', 'name': 'Shortstop', 'abbreviation': 'SS'}, 'batSide': {'code': 'S', 'description': 'Switch'}, 'fielding_ability': 0.972, 'plate_discipline': {'Walk': 0.06, 'Strikeout': 0.08, 'HBP': 0.002}, 'batting_profile': {'contact': 0.92, 'power': 0.38, 'angle': 7.0, 'bunt_propensity': 0.6, 'stealing_tendency': 0.02, 'stealing_success_rate': 0.8}},
            {'id': 625209, 'legal_name': 'TJ Hawkins', 'nickname': None, 'position': {'code': '9', 'name': 'Right Field', 'abbreviation': 'RF'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.982, 'plate_discipline': {'Walk': 0.10, 'Strikeout': 0.12, 'HBP': 0.003}, 'batting_profile': {'contact': 0.86, 'power': 0.62, 'angle': 12.0, 'bunt_propensity': 0.15, 'stealing_tendency': 0.018, 'stealing_success_rate': 0.78}},
            # Pitchers
            {
                'id': 645210, 'legal_name': 'Miguel Garcia', 'nickname': 'Lefty', 'position': {'code': '1', 'name': 'Pitcher', 'abbreviation': 'P'}, 'pitchHand': {'code': 'L', 'description': 'Left'}, 'type': 'Starter', 'stamina': 70, 'fielding_ability': 0.950,
                'pitch_arsenal': {
                    'sinker': {'prob': 0.5, 'velo_range': (90, 93), 'spin_range': (1950, 2200)},
                    'curveball': {'prob': 0.3, 'velo_range': (78, 81), 'spin_range': (2700, 3000)},
                    'slider': {'prob': 0.2, 'velo_range': (84, 87), 'spin_range': (2350, 2650)}
                }, 'control': 0.60, 'wild_pitch_rate': 0.006
            },
            {
                'id': 645211, 'legal_name': 'Ben Logan', 'nickname': 'Chief', 'position': {'code': '1', 'name': 'Pitcher', 'abbreviation': 'P'}, 'pitchHand': {'code': 'R', 'description': 'Right'}, 'type': 'Long Reliever', 'stamina': 50, 'fielding_ability': 0.955,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.7, 'velo_range': (93, 96), 'spin_range': (2100, 2450)},
                    'curveball': {'prob': 0.3, 'velo_range': (79, 82), 'spin_range': (2500, 2800)}
                }, 'control': 0.68, 'wild_pitch_rate': 0.004
            },
            {
                'id': 645212, 'legal_name': 'Rollie Malone', 'nickname': 'Fingers', 'position': {'code': '1', 'name': 'Pitcher', 'abbreviation': 'P'}, 'pitchHand': {'code': 'R', 'description': 'Right'}, 'type': 'Middle Reliever', 'stamina': 30, 'fielding_ability': 0.940,
                'pitch_arsenal': {
                    'sinker': {'prob': 0.6, 'velo_range': (90, 93), 'spin_range': (2050, 2300)},
                    'slider': {'prob': 0.4, 'velo_range': (85, 88), 'spin_range': (2450, 2750)}
                }, 'control': 0.72, 'wild_pitch_rate': 0.002
            },
            {
                'id': 645213, 'legal_name': 'Dennis Thompson', 'nickname': 'Eck', 'position': {'code': '1', 'name': 'Pitcher', 'abbreviation': 'P'}, 'pitchHand': {'code': 'R', 'description': 'Right'}, 'type': 'Closer', 'stamina': 22, 'fielding_ability': 0.965,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.6, 'velo_range': (97, 100), 'spin_range': (2300, 2600)},
                    'slider': {'prob': 0.4, 'velo_range': (89, 92), 'spin_range': (2550, 2850)}
                }, 'control': 0.80, 'wild_pitch_rate': 0.001
            },
        ]
    },
    "COASTAL_VIPERS": {
        "id": 135,
        "name": "Coastal Vipers",
        "abbreviation": "VIP",
        "teamName": "Vipers",
        "venue": "Snake Pit Stadium",
        "fielding_prowess": 0.985,
        "double_play_rate": 0.44,
        "hbp_rate": 0.003,
        "players": [
            {'id': 565301, 'legal_name': 'Ricky Henderson', 'nickname': 'Speedy', 'position': {'code': '7', 'name': 'Left Field', 'abbreviation': 'LF'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.990, 'plate_discipline': {'Walk': 0.15, 'Strikeout': 0.10, 'HBP': 0.002}, 'batting_profile': {'contact': 0.85, 'power': 0.45, 'angle': 12.0, 'bunt_propensity': 0.2, 'stealing_tendency': 0.30, 'stealing_success_rate': 0.85}},
            {'id': 565302, 'legal_name': 'Dante Cole', 'nickname': None, 'position': {'code': '8', 'name': 'Center Field', 'abbreviation': 'CF'}, 'batSide': {'code': 'L', 'description': 'Left'}, 'fielding_ability': 0.985, 'plate_discipline': {'Walk': 0.08, 'Strikeout': 0.14, 'HBP': 0.003}, 'batting_profile': {'contact': 0.78, 'power': 0.60, 'angle': 14.0, 'bunt_propensity': 0.1, 'stealing_tendency': 0.05, 'stealing_success_rate': 0.80}},
            {'id': 565303, 'legal_name': 'Jason Giambi', 'nickname': 'G', 'position': {'code': '3', 'name': 'First Base', 'abbreviation': '1B'}, 'batSide': {'code': 'L', 'description': 'Left'}, 'fielding_ability': 0.970, 'plate_discipline': {'Walk': 0.14, 'Strikeout': 0.20, 'HBP': 0.005}, 'batting_profile': {'contact': 0.75, 'power': 0.85, 'angle': 18.0, 'bunt_propensity': 0.01, 'stealing_tendency': 0.001, 'stealing_success_rate': 0.50}},
            {'id': 565304, 'legal_name': 'Mark Mac', 'nickname': 'Big Mac', 'position': {'code': 'D', 'name': 'Designated Hitter', 'abbreviation': 'DH'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.900, 'plate_discipline': {'Walk': 0.12, 'Strikeout': 0.25, 'HBP': 0.008}, 'batting_profile': {'contact': 0.65, 'power': 0.95, 'angle': 20.0, 'bunt_propensity': 0.0, 'stealing_tendency': 0.0, 'stealing_success_rate': 0.40}},
            {'id': 565305, 'legal_name': 'Matt Chapman', 'nickname': 'Chappy', 'position': {'code': '5', 'name': 'Third Base', 'abbreviation': '3B'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.995, 'plate_discipline': {'Walk': 0.10, 'Strikeout': 0.18, 'HBP': 0.004}, 'batting_profile': {'contact': 0.70, 'power': 0.75, 'angle': 16.0, 'bunt_propensity': 0.05, 'stealing_tendency': 0.01, 'stealing_success_rate': 0.60}},
            {'id': 565306, 'legal_name': 'Marcus Semi', 'nickname': None, 'position': {'code': '6', 'name': 'Shortstop', 'abbreviation': 'SS'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.980, 'plate_discipline': {'Walk': 0.09, 'Strikeout': 0.15, 'HBP': 0.002}, 'batting_profile': {'contact': 0.76, 'power': 0.65, 'angle': 14.0, 'bunt_propensity': 0.05, 'stealing_tendency': 0.08, 'stealing_success_rate': 0.75}},
            {'id': 565307, 'legal_name': 'Jed Lowrie', 'nickname': 'Jed', 'position': {'code': '4', 'name': 'Second Base', 'abbreviation': '2B'}, 'batSide': {'code': 'S', 'description': 'Switch'}, 'fielding_ability': 0.975, 'plate_discipline': {'Walk': 0.08, 'Strikeout': 0.12, 'HBP': 0.002}, 'batting_profile': {'contact': 0.82, 'power': 0.50, 'angle': 12.0, 'bunt_propensity': 0.1, 'stealing_tendency': 0.02, 'stealing_success_rate': 0.65}},
            {'id': 565308, 'legal_name': 'Stephen Vogt', 'nickname': 'I Believe', 'position': {'code': '2', 'name': 'Catcher', 'abbreviation': 'C'}, 'batSide': {'code': 'L', 'description': 'Left'}, 'fielding_ability': 0.980, 'catchers_arm': 0.75, 'passed_ball_rate': 0.004, 'plate_discipline': {'Walk': 0.07, 'Strikeout': 0.14, 'HBP': 0.002}, 'batting_profile': {'contact': 0.78, 'power': 0.55, 'angle': 13.0, 'bunt_propensity': 0.05, 'stealing_tendency': 0.001, 'stealing_success_rate': 0.50}},
            {'id': 565309, 'legal_name': 'Josh Reddick', 'nickname': 'Spiderman', 'position': {'code': '9', 'name': 'Right Field', 'abbreviation': 'RF'}, 'batSide': {'code': 'L', 'description': 'Left'}, 'fielding_ability': 0.988, 'plate_discipline': {'Walk': 0.08, 'Strikeout': 0.13, 'HBP': 0.003}, 'batting_profile': {'contact': 0.75, 'power': 0.60, 'angle': 14.0, 'bunt_propensity': 0.05, 'stealing_tendency': 0.05, 'stealing_success_rate': 0.70}},
            # Pitchers
            {
                'id': 665310, 'legal_name': 'Tim Hudson', 'nickname': 'Huddy', 'position': {'code': '1', 'name': 'Pitcher', 'abbreviation': 'P'}, 'pitchHand': {'code': 'R', 'description': 'Right'}, 'type': 'Starter', 'stamina': 80, 'fielding_ability': 0.970,
                'pitch_arsenal': {
                    'sinker': {'prob': 0.5, 'velo_range': (91, 94), 'spin_range': (2100, 2400)},
                    'slider': {'prob': 0.2, 'velo_range': (84, 87), 'spin_range': (2300, 2600)},
                    'changeup': {'prob': 0.2, 'velo_range': (82, 85), 'spin_range': (1700, 2000)},
                    'curveball': {'prob': 0.1, 'velo_range': (76, 79), 'spin_range': (2500, 2800)}
                }, 'control': 0.75, 'wild_pitch_rate': 0.002
            },
            {
                'id': 665311, 'legal_name': 'Barry Zito', 'nickname': 'Zeets', 'position': {'code': '1', 'name': 'Pitcher', 'abbreviation': 'P'}, 'pitchHand': {'code': 'L', 'description': 'Left'}, 'type': 'Long Reliever', 'stamina': 55, 'fielding_ability': 0.960,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.4, 'velo_range': (87, 90), 'spin_range': (2000, 2300)},
                    'curveball': {'prob': 0.5, 'velo_range': (72, 76), 'spin_range': (2800, 3200)},
                    'changeup': {'prob': 0.1, 'velo_range': (78, 81), 'spin_range': (1600, 1900)}
                }, 'control': 0.65, 'wild_pitch_rate': 0.004
            },
            {
                'id': 665312, 'legal_name': 'Sean Doolittle', 'nickname': 'Doo', 'position': {'code': '1', 'name': 'Pitcher', 'abbreviation': 'P'}, 'pitchHand': {'code': 'L', 'description': 'Left'}, 'type': 'Middle Reliever', 'stamina': 30, 'fielding_ability': 0.950,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.85, 'velo_range': (94, 97), 'spin_range': (2400, 2700)},
                    'slider': {'prob': 0.15, 'velo_range': (85, 88), 'spin_range': (2300, 2600)}
                }, 'control': 0.80, 'wild_pitch_rate': 0.001
            },
            {
                'id': 665313, 'legal_name': 'Liam Hendriks', 'nickname': 'Slydah', 'position': {'code': '1', 'name': 'Pitcher', 'abbreviation': 'P'}, 'pitchHand': {'code': 'R', 'description': 'Right'}, 'type': 'Closer', 'stamina': 25, 'fielding_ability': 0.965,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.5, 'velo_range': (96, 99), 'spin_range': (2500, 2800)},
                    'slider': {'prob': 0.4, 'velo_range': (88, 91), 'spin_range': (2600, 2900)},
                    'curveball': {'prob': 0.1, 'velo_range': (82, 85), 'spin_range': (2700, 3000)}
                }, 'control': 0.82, 'wild_pitch_rate': 0.001
            },
        ]
    },
    "DESERT_SCORPIONS": {
        "id": 136,
        "name": "Desert Scorpions",
        "abbreviation": "DES",
        "teamName": "Scorpions",
        "venue": "Cactus League Park",
        "fielding_prowess": 0.970,
        "double_play_rate": 0.40,
        "hbp_rate": 0.005,
        "players": [
            {'id': 585401, 'legal_name': 'Ketel Star', 'nickname': None, 'position': {'code': '8', 'name': 'Center Field', 'abbreviation': 'CF'}, 'batSide': {'code': 'S', 'description': 'Switch'}, 'fielding_ability': 0.980, 'plate_discipline': {'Walk': 0.09, 'Strikeout': 0.12, 'HBP': 0.003}, 'batting_profile': {'contact': 0.88, 'power': 0.55, 'angle': 13.0, 'bunt_propensity': 0.1, 'stealing_tendency': 0.15, 'stealing_success_rate': 0.82}},
            {'id': 585402, 'legal_name': 'Corbin Carroll', 'nickname': 'CC', 'position': {'code': '9', 'name': 'Right Field', 'abbreviation': 'RF'}, 'batSide': {'code': 'L', 'description': 'Left'}, 'fielding_ability': 0.985, 'plate_discipline': {'Walk': 0.10, 'Strikeout': 0.18, 'HBP': 0.004}, 'batting_profile': {'contact': 0.78, 'power': 0.65, 'angle': 12.0, 'bunt_propensity': 0.2, 'stealing_tendency': 0.40, 'stealing_success_rate': 0.88}},
            {'id': 585403, 'legal_name': 'Christian Walk', 'nickname': 'Walkie', 'position': {'code': '3', 'name': 'First Base', 'abbreviation': '1B'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.990, 'plate_discipline': {'Walk': 0.12, 'Strikeout': 0.22, 'HBP': 0.006}, 'batting_profile': {'contact': 0.72, 'power': 0.82, 'angle': 17.0, 'bunt_propensity': 0.01, 'stealing_tendency': 0.01, 'stealing_success_rate': 0.60}},
            {'id': 585404, 'legal_name': 'Lourdes Gurriel', 'nickname': 'Piña', 'position': {'code': '7', 'name': 'Left Field', 'abbreviation': 'LF'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.975, 'plate_discipline': {'Walk': 0.06, 'Strikeout': 0.15, 'HBP': 0.003}, 'batting_profile': {'contact': 0.80, 'power': 0.68, 'angle': 15.0, 'bunt_propensity': 0.05, 'stealing_tendency': 0.02, 'stealing_success_rate': 0.65}},
            {'id': 585405, 'legal_name': 'Eugenio Suarez', 'nickname': 'Geno', 'position': {'code': '5', 'name': 'Third Base', 'abbreviation': '3B'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.965, 'plate_discipline': {'Walk': 0.10, 'Strikeout': 0.28, 'HBP': 0.007}, 'batting_profile': {'contact': 0.65, 'power': 0.88, 'angle': 19.0, 'bunt_propensity': 0.02, 'stealing_tendency': 0.01, 'stealing_success_rate': 0.55}},
            {'id': 585406, 'legal_name': 'Gabriel Moreno', 'nickname': 'Gaby', 'position': {'code': '2', 'name': 'Catcher', 'abbreviation': 'C'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.992, 'catchers_arm': 0.88, 'passed_ball_rate': 0.002, 'plate_discipline': {'Walk': 0.08, 'Strikeout': 0.14, 'HBP': 0.002}, 'batting_profile': {'contact': 0.84, 'power': 0.45, 'angle': 11.0, 'bunt_propensity': 0.1, 'stealing_tendency': 0.03, 'stealing_success_rate': 0.70}},
            {'id': 585407, 'legal_name': 'Joc Pederson', 'nickname': 'Champ', 'position': {'code': 'D', 'name': 'Designated Hitter', 'abbreviation': 'DH'}, 'batSide': {'code': 'L', 'description': 'Left'}, 'fielding_ability': 0.950, 'plate_discipline': {'Walk': 0.13, 'Strikeout': 0.24, 'HBP': 0.005}, 'batting_profile': {'contact': 0.68, 'power': 0.85, 'angle': 22.0, 'bunt_propensity': 0.0, 'stealing_tendency': 0.01, 'stealing_success_rate': 0.50}},
            {'id': 585408, 'legal_name': 'Geraldo Perdomo', 'nickname': 'Domo', 'position': {'code': '6', 'name': 'Shortstop', 'abbreviation': 'SS'}, 'batSide': {'code': 'S', 'description': 'Switch'}, 'fielding_ability': 0.985, 'plate_discipline': {'Walk': 0.11, 'Strikeout': 0.13, 'HBP': 0.003}, 'batting_profile': {'contact': 0.75, 'power': 0.35, 'angle': 10.0, 'bunt_propensity': 0.3, 'stealing_tendency': 0.12, 'stealing_success_rate': 0.80}},
            {'id': 585409, 'legal_name': 'Blaze Alexander', 'nickname': None, 'position': {'code': '4', 'name': 'Second Base', 'abbreviation': '2B'}, 'batSide': {'code': 'R', 'description': 'Right'}, 'fielding_ability': 0.970, 'plate_discipline': {'Walk': 0.07, 'Strikeout': 0.20, 'HBP': 0.004}, 'batting_profile': {'contact': 0.72, 'power': 0.50, 'angle': 12.0, 'bunt_propensity': 0.1, 'stealing_tendency': 0.05, 'stealing_success_rate': 0.70}},
            # Pitchers
            {
                'id': 685410, 'legal_name': 'Zac Gallen', 'nickname': 'Milkman', 'position': {'code': '1', 'name': 'Pitcher', 'abbreviation': 'P'}, 'pitchHand': {'code': 'R', 'description': 'Right'}, 'type': 'Starter', 'stamina': 78, 'fielding_ability': 0.960,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.45, 'velo_range': (93, 96), 'spin_range': (2300, 2600)},
                    'knuckle curve': {'prob': 0.25, 'velo_range': (80, 83), 'spin_range': (2800, 3100)},
                    'changeup': {'prob': 0.2, 'velo_range': (84, 87), 'spin_range': (1600, 1900)},
                    'cutter': {'prob': 0.1, 'velo_range': (88, 91), 'spin_range': (2400, 2700)}
                }, 'control': 0.78, 'wild_pitch_rate': 0.002
            },
            {
                'id': 685411, 'legal_name': 'Merrill Kelly', 'nickname': 'Desert Fox', 'position': {'code': '1', 'name': 'Pitcher', 'abbreviation': 'P'}, 'pitchHand': {'code': 'R', 'description': 'Right'}, 'type': 'Long Reliever', 'stamina': 60, 'fielding_ability': 0.965,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.4, 'velo_range': (91, 94), 'spin_range': (2200, 2500)},
                    'changeup': {'prob': 0.25, 'velo_range': (84, 87), 'spin_range': (1700, 2000)},
                    'cutter': {'prob': 0.2, 'velo_range': (88, 91), 'spin_range': (2300, 2600)},
                    'curveball': {'prob': 0.15, 'velo_range': (78, 81), 'spin_range': (2600, 2900)}
                }, 'control': 0.72, 'wild_pitch_rate': 0.003
            },
            {
                'id': 685412, 'legal_name': 'Kevin Ginkel', 'nickname': 'Gink', 'position': {'code': '1', 'name': 'Pitcher', 'abbreviation': 'P'}, 'pitchHand': {'code': 'R', 'description': 'Right'}, 'type': 'Middle Reliever', 'stamina': 30, 'fielding_ability': 0.945,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.5, 'velo_range': (95, 98), 'spin_range': (2300, 2600)},
                    'slider': {'prob': 0.5, 'velo_range': (85, 88), 'spin_range': (2500, 2800)}
                }, 'control': 0.68, 'wild_pitch_rate': 0.004
            },
            {
                'id': 685413, 'legal_name': 'Paul Sewald', 'nickname': 'Waldo', 'position': {'code': '1', 'name': 'Pitcher', 'abbreviation': 'P'}, 'pitchHand': {'code': 'R', 'description': 'Right'}, 'type': 'Closer', 'stamina': 25, 'fielding_ability': 0.950,
                'pitch_arsenal': {
                    'four-seam fastball': {'prob': 0.6, 'velo_range': (91, 94), 'spin_range': (2400, 2700)},
                    'slider': {'prob': 0.4, 'velo_range': (82, 85), 'spin_range': (2600, 2900)}
                }, 'control': 0.75, 'wild_pitch_rate': 0.002
            },
        ]
    }
}
