import random
from teams import TEAMS, GAME_CONTEXT

class BaseballSimulator:
    """
    Simulates a modern MLB game with realistic rules and enhanced realism.
    - DH rule is in effect.
    - Extra innings start with a "ghost runner" on second.
    - Realistic bullpen management with pitcher fatigue.
    - Positional fielding, errors, and scorer's notation for outs.
    - Varied pitch velocities and more descriptive play-by-play.
    - Feature flag for verbose/terse play-by-play output.
    """

    def __init__(self, team1_data, team2_data, verbose_phrasing=True, use_bracketed_ui=False):
        self.team1_data = team1_data
        self.team2_data = team2_data
        self.team1_name = self.team1_data["name"]
        self.team2_name = self.team2_data["name"]
        self.verbose_phrasing = verbose_phrasing
        self.use_bracketed_ui = use_bracketed_ui

        # Setup lineups and pitchers
        self.team1_lineup = [p for p in self.team1_data["players"] if p['position'] != 'P']
        self.team2_lineup = [p for p in self.team2_data["players"] if p['position'] != 'P']
        
        self._setup_pitchers(self.team1_data, 'team1')
        self._setup_pitchers(self.team2_data, 'team2')

        # Setup defensive positions
        self._setup_defense('team1', self.team1_data)
        self._setup_defense('team2', self.team2_data)

        # Game state
        self.team1_batter_idx, self.team2_batter_idx = 0, 0
        self.team1_score, self.team2_score = 0, 0
        self.inning, self.top_of_inning = 1, True
        self.outs, self.bases = 0, [None, None, None] # Runners on base by name

        # Game context
        self.umpires = random.sample(GAME_CONTEXT["umpires"], 4)
        self.weather = random.choice(GAME_CONTEXT["weather_conditions"])
        self.venue = self.team1_data["venue"]

    def _setup_pitchers(self, team_data, team_prefix):
        all_pitchers = [p for p in team_data["players"] if p['position'] == 'P']
        pitcher_stats = {p['legal_name']: p.copy() for p in all_pitchers}
        available_bullpen = [p['legal_name'] for p in all_pitchers if p['type'] != 'Starter']
        current_pitcher_name = next(p['legal_name'] for p in all_pitchers if p['type'] == 'Starter')

        setattr(self, f"{team_prefix}_pitcher_stats", pitcher_stats)
        setattr(self, f"{team_prefix}_available_bullpen", available_bullpen)
        setattr(self, f"{team_prefix}_current_pitcher_name", current_pitcher_name)

        if not hasattr(self, 'pitch_counts'): self.pitch_counts = {}
        self.pitch_counts.update({name: 0 for name in pitcher_stats.keys()})

    def _setup_defense(self, team_prefix, team_data):
        defense = {p['position']: p for p in team_data['players']}
        setattr(self, f"{team_prefix}_defense", defense)

        infielders = ['1B', '2B', '3B', 'SS']
        outfielders = ['LF', 'CF', 'RF']

        setattr(self, f"{team_prefix}_infielders", [defense[pos] for pos in infielders if pos in defense])
        setattr(self, f"{team_prefix}_outfielders", [defense[pos] for pos in outfielders if pos in defense])
        setattr(self, f"{team_prefix}_catcher", defense.get('C'))

    def _get_player_display_name(self, player):
        if player.get('nickname'):
            return f"{player['legal_name']} '{player['nickname']}'"
        return player['legal_name']

    def _get_hit_outcome(self, batter_stats):
        in_play = {k: v for k, v in batter_stats.items() if k not in ["Walk", "Strikeout", "HBP"]}
        return random.choices(list(in_play.keys()), weights=list(in_play.values()), k=1)[0]

    def _advance_runners_on_wp_pb(self, event_type):
        runs = 0
        print(f"  {event_type}! Runners advance.")
        # Simplified: runners advance one base.
        if self.bases[2]:
            runs += 1
            print(f"  {self.bases[2]} scores!")
            self.bases[2] = None
        if self.bases[1]:
            self.bases[2] = self.bases[1]
            self.bases[1] = None
        if self.bases[0]:
            self.bases[1] = self.bases[0]
            self.bases[0] = None
        return runs

    def _simulate_at_bat(self, batter, pitcher):
        balls, strikes = 0, 0
        
        batter_display_name = self._get_player_display_name(batter)
        print(f"Now batting: {batter_display_name} ({batter['position']}, {batter['handedness']})")

        # Check for HBP at the start of the at-bat using batter-specific stats
        if random.random() < batter.get('stats', {}).get('HBP', 0):
            return "HBP"

        batter_stats = batter['stats']
        batter_walk_rate = batter_stats.get('Walk', 0.09)
        batter_k_rate = batter_stats.get('Strikeout', 0.17)

        # Plate discipline affects swing decisions, especially on pitches outside the zone.
        # A more disciplined batter (higher walk rate) is less likely to swing at a ball.
        discipline_factor = max(0.1, batter_walk_rate / 0.08) # Lowered baseline for more discipline
        swing_at_ball_prob = 0.30 / discipline_factor # Lowered base swing prob

        # Contact ability is influenced by the batter's strikeout rate.
        # A higher K-rate means a lower chance of making contact on a swing.
        k_propensity = max(0.1, batter_k_rate / 0.17)
        contact_prob = 0.75 / k_propensity

        while balls < 4 and strikes < 3:
            self.pitch_counts[pitcher['legal_name']] += 1
            
            pitch_selection = random.choices(list(pitcher['pitch_arsenal'].keys()),
                                             weights=[v['prob'] for v in pitcher['pitch_arsenal'].values()], k=1)[0]
            pitch_details = pitcher['pitch_arsenal'][pitch_selection]
            min_velo, max_velo = pitch_details['velo_range']
            # Use random.uniform for more realistic, non-integer velocities.
            pitch_velo = round(random.uniform(min_velo, max_velo), 1)

            fatigue_factor = max(0, self.pitch_counts[pitcher['legal_name']] - pitcher['stamina'])
            fatigue_penalty = (fatigue_factor / 15) * 0.1
            effective_control = pitcher['control'] - fatigue_penalty

            is_strike_loc = random.random() < effective_control
            
            if self.verbose_phrasing:
                if is_strike_loc:
                    location_desc = random.choice(GAME_CONTEXT['pitch_locations']['strike'])
                else:
                    location_desc = random.choice(GAME_CONTEXT['pitch_locations']['ball'])
                pitch_desc = f"  Pitch: {pitch_selection} ({pitch_velo} mph), {location_desc}."
            else:
                pitch_desc = f"  Pitch: {pitch_selection} ({pitch_velo} mph)."

            swing_prob = 0.85 if is_strike_loc else swing_at_ball_prob
            swing = random.random() < swing_prob
            
            if swing:
                if random.random() < contact_prob: # Contact
                    if strikes < 2 and random.random() < 0.5: # Foul
                        strikes += 1
                        print(f"{pitch_desc} Foul. Count: {balls}-{strikes}")
                    else: # In Play
                        print(f"{pitch_desc} Ball in play...")
                        return self._get_hit_outcome(batter['stats'])
                else: # Swing and miss
                    strikes += 1
                    swing_miss_phrasing = random.choice(GAME_CONTEXT['play_by_play']['swing_and_miss'])
                    print(f"{pitch_desc} {swing_miss_phrasing}{'!' if strikes == 3 else '.'}{' Count: ' + str(balls) + '-' + str(strikes) if strikes < 3 else ''}")
            else: # Taken pitch
                if is_strike_loc:
                    strikes += 1
                    called_strike_phrasing = random.choice(GAME_CONTEXT['play_by_play']['called_strike'])
                    print(f"{pitch_desc} {called_strike_phrasing}.{' Count: ' + str(balls) + '-' + str(strikes) if strikes < 3 else ''}")
                else:
                    # Check for Wild Pitch or Passed Ball on a ball that is not swung at, only if bases are occupied.
                    if any(self.bases):
                        defensive_team = 'team1' if self.top_of_inning else 'team2'
                        catcher = getattr(self, f"{defensive_team}_catcher")
                        runs = 0

                        is_wp = random.random() < pitcher.get('wild_pitch_rate', 0)
                        is_pb = not is_wp and random.random() < catcher.get('passed_ball_rate', 0)

                        if is_wp:
                            runs = self._advance_runners_on_wp_pb("Wild Pitch")
                        elif is_pb:
                            runs = self._advance_runners_on_wp_pb("Passed Ball")

                        if runs > 0:
                            if self.top_of_inning: self.team2_score += runs
                            else: self.team1_score += runs

                    balls += 1
                    print(f"{pitch_desc} Ball.{' Count: ' + str(balls) + '-' + str(strikes) if balls < 4 else ''}")

        if balls == 4:
            return "Walk"
        else:
            print(f"  ...{random.choice(GAME_CONTEXT['play_by_play']['out']['strikeout'])}")
            return "Strikeout"

    def _advance_runners(self, hit_type, batter):
        runs = 0

        if hit_type in ["Walk", "HBP"]:
            new_bases = self.bases[:] # Make a copy
            if new_bases[0]: # If 1B is occupied
                if new_bases[1]: # If 1B and 2B are occupied
                    if new_bases[2]: # If bases are loaded
                        runs += 1 # Runner from 3B scores
                    new_bases[2] = new_bases[1] # Runner from 2B to 3B
                new_bases[1] = new_bases[0] # Runner from 1B to 2B
            new_bases[0] = batter['legal_name'] # Batter to 1B
            self.bases = new_bases
            return runs

        # Simplified runner advancement logic for hits
        new_bases = [None, None, None]
        if hit_type == 'Single':
            if self.bases[2]: runs += 1
            if self.bases[1]: new_bases[2] = self.bases[1]
            if self.bases[0]: new_bases[1] = self.bases[0]
            new_bases[0] = batter['legal_name']
        elif hit_type == 'Double':
            if self.bases[2]: runs += 1
            if self.bases[1]: runs += 1
            if self.bases[0]: new_bases[2] = self.bases[0]
            new_bases[1] = batter['legal_name']
        elif hit_type == 'Triple':
            runs += sum(1 for r in self.bases if r is not None)
            new_bases[2] = batter['legal_name']
        elif hit_type == 'Home Run':
            runs += sum(1 for r in self.bases if r is not None) + 1

        self.bases = new_bases
        return runs

    def _get_bases_str(self):
        if self.use_bracketed_ui:
            base1 = '1B' if self.bases[0] is not None else '_'
            base2 = '2B' if self.bases[1] is not None else '_'
            base3 = '3B' if self.bases[2] is not None else '_'
            return f"[{base1}]-[{base2}]-[{base3}]"
        else:
            runners = []
            if self.bases[2]: runners.append(f"3B: {self.bases[2]}")
            if self.bases[1]: runners.append(f"2B: {self.bases[1]}")
            if self.bases[0]: runners.append(f"1B: {self.bases[0]}")
            return ", ".join(runners) if runners else "Bases empty"

    def _manage_pitching_change(self):
        is_home_team_pitching = self.top_of_inning
        
        current_pitcher_name = self.team1_current_pitcher_name if is_home_team_pitching else self.team2_current_pitcher_name
        pitcher_stats = self.team1_pitcher_stats if is_home_team_pitching else self.team2_pitcher_stats
        available_bullpen = self.team1_available_bullpen if is_home_team_pitching else self.team2_available_bullpen
        team_name = self.team1_name if is_home_team_pitching else self.team2_name

        current_pitcher = pitcher_stats[current_pitcher_name]
        fatigue_factor = max(0, self.pitch_counts[current_pitcher_name] - current_pitcher['stamina'])

        # The chance of being pulled increases with fatigue.
        # A pitcher with a fatigue_factor of 10 has a 25% chance of being pulled.
        pull_probability = (fatigue_factor / 20) ** 2

        if random.random() < pull_probability and available_bullpen:
            # Randomly select a reliever instead of the first one available.
            next_pitcher_name = random.choice(available_bullpen)

            if is_home_team_pitching:
                if self.team1_current_pitcher_name != next_pitcher_name:
                    print(f"\n--- Pitching Change for {team_name}: {next_pitcher_name} replaces {self.team1_current_pitcher_name} ---\n")
                    self.team1_current_pitcher_name = next_pitcher_name
                    self.team1_available_bullpen.remove(next_pitcher_name)
            else:
                if self.team2_current_pitcher_name != next_pitcher_name:
                    print(f"\n--- Pitching Change for {team_name}: {next_pitcher_name} replaces {self.team2_current_pitcher_name} ---\n")
                    self.team2_current_pitcher_name = next_pitcher_name
                    self.team2_available_bullpen.remove(next_pitcher_name)

    def _handle_batted_ball_out(self, out_type, batter):
        defensive_team = 'team1' if self.top_of_inning else 'team2'
        infielders = getattr(self, f"{defensive_team}_infielders")
        outfielders = getattr(self, f"{defensive_team}_outfielders")
        pitcher = getattr(self, f"{defensive_team}_pitcher_stats")[getattr(self, f"{defensive_team}_current_pitcher_name")]
        catcher = getattr(self, f"{defensive_team}_catcher")

        fielder = None
        is_error = False
        
        if out_type == 'Groundout':
            # Weighted distribution for groundouts for realism.
            # Catcher (2-3) and Pitcher (1-3) groundouts are now much rarer.
            potential_fielders = infielders + [pitcher, catcher]
            pos_weights = {'SS': 35, '2B': 30, '3B': 20, '1B': 10, 'P': 4, 'C': 1}
            weights = [pos_weights.get(p['position'], 0) for p in potential_fielders]

            if sum(weights) > 0:
                fielder = random.choices(potential_fielders, weights=weights, k=1)[0]
            else: # Fallback to original logic if weights are misconfigured
                fielder = random.choice(infielders + [pitcher, catcher])
        elif out_type == 'Flyout':
            fielder = random.choices(
                population=outfielders + infielders,
                weights=[6] * len(outfielders) + [1] * len(infielders),
                k=1
            )[0]

        if fielder:
            team_prowess = self.team1_data['fielding_prowess'] if self.top_of_inning else self.team2_data['fielding_prowess']
            fielding_success_rate = fielder['fielding_ability'] * team_prowess
            if random.random() > fielding_success_rate:
                is_error = True

        pos_map = {'P': 1, 'C': 2, '1B': 3, '2B': 4, '3B': 5, 'SS': 6, 'LF': 7, 'CF': 8, 'RF': 9}
        if is_error:
            notation = f"E{pos_map.get(fielder['position'], '')}"
            print(f"  An error by {fielder['position']} {fielder['legal_name']} allows the batter to reach base.")
            return f"Reached on Error ({notation})", 0, True

        runs = 0
        notation = ""
        if out_type == 'Flyout':
            self.outs += 1
            fielder_pos = fielder['position']
            infield_positions = ['P', 'C', '1B', '2B', '3B', 'SS']

            if fielder_pos in infield_positions:
                out_desc = random.choice(GAME_CONTEXT['play_by_play']['out']['popout']).format(fielder_pos=fielder_pos)
                notation = f"P{pos_map[fielder_pos]}"
            else:
                out_desc = random.choice(GAME_CONTEXT['play_by_play']['out']['flyout']).format(fielder_pos=fielder_pos)
                notation = f"F{pos_map[fielder_pos]}"

            if self.outs < 3 and self.bases[2] and fielder_pos in ['LF', 'CF', 'RF']:
                if random.random() > 0.4:
                    runs += 1
                    print(f"  Sacrifice fly to {fielder_pos}, {self.bases[2]} scores!")
                    self.bases[2] = None
                    notation += " (SF)"
            return f"{out_desc} ({notation})", runs, False

        if out_type == 'Groundout':
            dp_opportunity = self.outs < 2 and self.bases[0] is not None
            dp_rate = self.team1_data['double_play_rate'] if self.top_of_inning else self.team2_data['double_play_rate']

            if dp_opportunity and random.random() < dp_rate:
                self.outs += 2
                if fielder['position'] == 'SS':
                    notation = "GDP (6-4-3)"
                    print(f"  Ground ball to short... 6-4-3 double play!")
                elif fielder['position'] == '2B':
                    notation = "GDP (4-6-3)"
                    print(f"  Ground ball to second... 4-6-3 double play!")
                else:
                    notation = f"GDP ({pos_map[fielder['position']]}-4-3)"
                    print(f"  Ground ball to {fielder['position']}... double play!")

                self.bases[0] = None
                if self.bases[1]:
                    self.bases[2] = self.bases[1]
                    self.bases[1] = None
                return f"Groundout, Double Play ({notation})", runs, False

            self.outs += 1
            if self.outs < 3:
                if self.bases[2]: runs += 1; self.bases[2] = None
                if self.bases[1]: self.bases[2] = self.bases[1]; self.bases[1] = None
                if self.bases[0]: self.bases[1] = self.bases[0]; self.bases[0] = None

            if fielder['position'] == '1B':
                notation = "3U"
            else:
                notation = f"{pos_map[fielder['position']]}-3"

            out_desc = random.choice(GAME_CONTEXT['play_by_play']['out']['groundout']).format(fielder=fielder['position'])
            return f"{out_desc} ({notation})", runs, False

        return "Error", 0, True # Should not be reached

    def _simulate_half_inning(self):
        self.outs, self.bases = 0, [None, None, None]

        is_home_team_batting = not self.top_of_inning
        batting_team_name, lineup, batter_idx_ref = (self.team1_name, self.team1_lineup, 'team1_batter_idx') if is_home_team_batting else (self.team2_name, self.team2_lineup, 'team2_batter_idx')

        inning_half = "Bottom" if is_home_team_batting else "Top"
        print("-" * 50)
        print(f"{inning_half} of Inning {self.inning} | {batting_team_name} batting")

        if self.inning >= 10:
            last_batter_idx = (getattr(self, batter_idx_ref) - 1 + 9) % 9
            runner_name = lineup[last_batter_idx]['legal_name']
            self.bases[1] = runner_name
            if self.verbose_phrasing:
                print(f"  Note: Per extra-inning rules, {runner_name} begins the inning on second base.")

        while self.outs < 3:
            self._manage_pitching_change()
            pitcher_name = self.team1_current_pitcher_name if self.top_of_inning else self.team2_current_pitcher_name
            pitcher_stats_dict = self.team1_pitcher_stats if self.top_of_inning else self.team2_pitcher_stats
            pitcher = pitcher_stats_dict[pitcher_name]

            batter_idx = getattr(self, batter_idx_ref)
            batter = lineup[batter_idx]

            outcome = self._simulate_at_bat(batter, pitcher)
            runs = 0

            display_outcome = outcome
            if outcome == "HBP":
                display_outcome = "Hit by Pitch"

            if outcome in ["Groundout", "Flyout"]:
                display_outcome, new_runs, was_error = self._handle_batted_ball_out(outcome, batter)
                runs += new_runs
                if was_error:
                    runs += self._advance_runners("Single", batter)
            elif outcome == "Strikeout":
                self.outs += 1
                display_outcome = "Strikeout"
            elif outcome in ["Single", "Double", "Triple", "Home Run"]:
                display_outcome = random.choice(GAME_CONTEXT['play_by_play']['hit'][outcome])
                runs += self._advance_runners(outcome, batter)
            elif outcome == "Walk":
                display_outcome = random.choice(GAME_CONTEXT['play_by_play']['misc']['walk'])
                runs += self._advance_runners(outcome, batter)
            elif outcome == "HBP":
                display_outcome = random.choice(GAME_CONTEXT['play_by_play']['misc']['hbp'])
                runs += self._advance_runners(outcome, batter)


            if is_home_team_batting: self.team1_score += runs
            else: self.team2_score += runs
            
            score_str = f"{self.team1_name}: {self.team1_score}, {self.team2_name}: {self.team2_score}"
            print(f"  {display_outcome.ljust(12)}")
            print(f"  Outs: {self.outs} | Bases: {self._get_bases_str()} | Score: {score_str}\n")

            if random.random() < 0.15: # 15% chance of flavor text
                print(random.choice(GAME_CONTEXT['play_by_play']['flavor']))
            
            setattr(self, batter_idx_ref, (batter_idx + 1) % 9)
            if self.outs >= 3: break
            if is_home_team_batting and self.team1_score > self.team2_score and self.inning >= 9:
                return

    def _print_pre_game_summary(self):
        print("="*20, "GAME START", "="*20)
        print(f"{self.team2_name} vs. {self.team1_name}")
        print(f"Venue: {self.venue}")
        print(f"Weather: {self.weather}")
        print(f"Umpires: HP: {self.umpires[0]}, 1B: {self.umpires[1]}, 2B: {self.umpires[2]}, 3B: {self.umpires[3]}")
        print("-" * 50)

    def play_game(self):
        self._print_pre_game_summary()
        while self.inning <= 9 or self.team1_score == self.team2_score:
            self.top_of_inning = True
            self._simulate_half_inning()

            # Check for walk-off win
            if self.inning >= 9 and not self.top_of_inning and self.team1_score > self.team2_score:
                break

            self.top_of_inning = False
            self._simulate_half_inning()

            if self.inning >= 9 and not self.top_of_inning and self.team1_score > self.team2_score:
                break

            self.inning += 1

        print("="*20, "GAME OVER", "="*20)
        print(f"\nFinal Score: {self.team1_name} {self.team1_score} - {self.team2_name} {self.team2_score}")
        winner = self.team1_name if self.team1_score > self.team2_score else self.team2_name
        print(f"\n{winner} win!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="A realistic baseball simulator.")
    parser.add_argument('--terse', action='store_true', help="Use terse, data-driven phrasing for play-by-play.")
    parser.add_argument('--bracketed-ui', action='store_true', help="Use the classic bracketed UI for base runners.")
    args = parser.parse_args()

    home_team_key = "BAY_BOMBERS"
    away_team_key = "PC_PILOTS"
    game = BaseballSimulator(
        TEAMS[home_team_key],
        TEAMS[away_team_key],
        verbose_phrasing=not args.terse,
        use_bracketed_ui=args.bracketed_ui
    )
    game.play_game()