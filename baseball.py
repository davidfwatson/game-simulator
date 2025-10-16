import random
import uuid
import json
from datetime import datetime, timezone
from gameday import GamedayData, GameData, LiveData, Linescore, InningLinescore, Play, PlayResult, PlayAbout, PlayCount, PlayEvent, Runner, FielderCredit
from teams import TEAMS
from commentary import GAME_CONTEXT

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

    def __init__(self, team1_data, team2_data, verbose_phrasing=True, use_bracketed_ui=False, commentary_style='narrative', max_innings=None, game_seed=None, commentary_seed=None):
        self.team1_data = team1_data
        self.team2_data = team2_data
        self.team1_name = self.team1_data["name"]
        self.team2_name = self.team2_data["name"]
        self.verbose_phrasing = verbose_phrasing
        self.use_bracketed_ui = use_bracketed_ui
        self.max_innings = max_innings
        self.game_rng = random.Random(game_seed)
        self.commentary_rng = random.Random(commentary_seed)

        self.generate_gameday = commentary_style in ['gameday', 'combo']
        self.base_commentary_style = commentary_style
        if commentary_style == 'combo':
            self.base_commentary_style = 'statcast' if not verbose_phrasing else 'narrative'
        elif commentary_style == 'gameday':
            self.base_commentary_style = 'none' # No play-by-play

        # Setup lineups and pitchers
        self.team1_lineup = [p for p in self.team1_data["players"] if p['position']['abbreviation'] != 'P']
        self.team2_lineup = [p for p in self.team2_data["players"] if p['position']['abbreviation'] != 'P']
        
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

        # Output buffer for narrative/statcast, gameday has its own structure
        self.output_lines = []
        self.gameday_data: GamedayData | None = None
        if self.generate_gameday:
            self._initialize_gameday_data()

        # Game context
        self.umpires = self.commentary_rng.sample(GAME_CONTEXT["umpires"], 4)
        self.weather = self.commentary_rng.choice(GAME_CONTEXT["weather_conditions"])
        self.venue = self.team1_data["venue"]

    def _initialize_gameday_data(self):
        """Sets up the initial structure for Gameday JSON output."""
        self.gameday_data = {
            "gameData": {
                "teams": {
                    "away": {
                        "id": self.team2_data["id"],
                        "name": self.team2_data["name"],
                        "abbreviation": self.team2_data["abbreviation"],
                        "teamName": self.team2_data["teamName"]
                    },
                    "home": {
                        "id": self.team1_data["id"],
                        "name": self.team1_data["name"],
                        "abbreviation": self.team1_data["abbreviation"],
                        "teamName": self.team1_data["teamName"]
                    }
                }
            },
            "liveData": {
                "plays": {"allPlays": []},
                "linescore": {
                    "currentInning": 1, "isTopInning": True, "inningState": "Top",
                    "outs": 0, "balls": 0, "strikes": 0,
                    "teams": {
                        "home": {"runs": 0, "hits": 0, "errors": 0},
                        "away": {"runs": 0, "hits": 0, "errors": 0}
                    },
                    "innings": [{"num": 1, "home": {"runs": 0}, "away": {"runs": 0}}]
                }
            }
        }

    def _print(self, text, end="\n"):
        """Buffer all output to print at the end."""
        if self.output_lines and end == "":
            self.output_lines[-1] += text
        else:
            self.output_lines.append(text)

    def _setup_pitchers(self, team_data, team_prefix):
        all_pitchers = [p for p in team_data["players"] if p['position']['abbreviation'] == 'P']
        pitcher_stats = {p['legal_name']: p.copy() for p in all_pitchers}
        bullpen_candidates = [p['legal_name'] for p in all_pitchers if p['type'] != 'Starter']
        closers = [name for name in bullpen_candidates if pitcher_stats[name]['type'] == 'Closer']
        non_closers = [name for name in bullpen_candidates if pitcher_stats[name]['type'] != 'Closer']
        self.game_rng.shuffle(non_closers)
        available_bullpen = non_closers + closers
        current_pitcher_name = next(p['legal_name'] for p in all_pitchers if p['type'] == 'Starter')

        setattr(self, f"{team_prefix}_pitcher_stats", pitcher_stats)
        setattr(self, f"{team_prefix}_available_bullpen", available_bullpen)
        setattr(self, f"{team_prefix}_current_pitcher_name", current_pitcher_name)

        if not hasattr(self, 'pitch_counts'): self.pitch_counts = {}
        self.pitch_counts.update({name: 0 for name in pitcher_stats.keys()})

    def _setup_defense(self, team_prefix, team_data):
        defense = {p['position']['abbreviation']: p for p in team_data['players']}
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
        return self.game_rng.choices(list(in_play.keys()), weights=list(in_play.values()), k=1)[0]

    def _generate_batted_ball_data(self, hit_type):
        if self.game_rng.random() < 0.05:
            return {}
        ev, la = 0, 0
        if hit_type == "Groundout": ev, la = round(self.game_rng.uniform(70, 95), 1), round(self.game_rng.uniform(-20, 5), 1)
        elif hit_type == "Flyout": ev, la = round(self.game_rng.uniform(85, 105), 1), round(self.game_rng.uniform(25, 50), 1)
        elif hit_type == "Single":
            if self.game_rng.random() < 0.6: ev, la = round(self.game_rng.uniform(80, 100), 1), round(self.game_rng.uniform(-10, 8), 1)
            else: ev, la = round(self.game_rng.uniform(90, 110), 1), round(self.game_rng.uniform(8, 20), 1)
        elif hit_type == "Double": ev, la = round(self.game_rng.uniform(100, 115), 1), round(self.game_rng.uniform(15, 35), 1)
        elif hit_type == "Triple": ev, la = round(self.game_rng.uniform(100, 115), 1), round(self.game_rng.uniform(18, 30), 1)
        elif hit_type == "Home Run":
            ev = round(self.game_rng.uniform(100, 120), 1)
            if ev >= 118: la = round(self.game_rng.uniform(20, 28), 1)
            elif ev > 110: la = round(self.game_rng.uniform(22, 35), 1)
            else: la = round(self.game_rng.uniform(25, 45), 1)
        return {'ev': ev, 'la': la}

    def _describe_contact(self, outcome):
        templates = GAME_CONTEXT['statcast_verbs']
        if outcome in templates:
            # Flatten the dictionary to just a list of verbs
            verbs = [v for cat in templates[outcome].values() for v in cat]
    def _get_hit_location(self, hit_type, ev, la):
        """Determine hit location based on EV and LA."""
        if la is None or ev is None:
            return "fair" # Default if no batted ball data
        if hit_type in ["Single", "Double"]:
            if -10 < la < 10: # Ground ball/liner
                return self.commentary_rng.choice(["up the middle", "through the right side", "through the left side"])
            elif 10 < la < 25: # Line drive
                return self.commentary_rng.choice(["to left field", "to center field", "to right field"])
            else: # Blooper/fly ball
                return self.commentary_rng.choice(["into shallow left", "into shallow center", "into shallow right"])
        elif hit_type == "Triple":
            return self.commentary_rng.choice(["into the right-center gap", "into the left-center gap"])
        elif hit_type == "Home Run":
            if abs(la - 28) < 5 and ev > 105: # Line drive HR
                return "down the line"
            return self.commentary_rng.choice(["to deep left field", "to deep center field", "to deep right field"])
        return "fair"

    def _get_trajectory(self, outcome, la):
        if "Groundout" in outcome: return "ground_ball"
        if la is not None:
            if la < 10: return "ground_ball"
            elif 10 <= la <= 25: return "line_drive"
            elif la > 50: return "popup"
        return "fly_ball"

    def _get_batted_ball_verb(self, outcome, ev, la):
        verb_cats = GAME_CONTEXT['statcast_verbs'].get(outcome, {})
        cat = 'default'
        if ev is not None and la is not None:
            if outcome == "Single":
                if ev < 90 and 10 < la < 30: cat = 'bloop'
                elif ev > 100 and la < 10: cat = 'liner'
                elif ev > 95 and la < 0: cat = 'grounder'
            elif outcome == "Double":
                if ev > 100 and la < 15: cat = 'liner'
                elif ev > 100 and la >= 15: cat = 'wall'
            elif outcome == "Home Run":
                if ev > 105 and la < 22: cat = 'screamer'
                elif ev > 100 and la > 35: cat = 'moonshot'
            elif outcome == "Groundout":
                if ev < 85: cat = 'soft'
                elif ev > 100: cat = 'hard'
            elif outcome == "Flyout":
                if (ev < 95 and la > 50) or (ev < 90 and la > 40): cat = 'popup'
                elif ev > 100 and la > 30: cat = 'deep'
        return self.commentary_rng.choice(verb_cats.get(cat, verb_cats.get('default', ["describes"])))

    def _format_statcast_template(self, outcome, context):
        templates = GAME_CONTEXT.get('statcast_templates', {}).get(outcome)
        if not templates: return None
        template = self.commentary_rng.choice(templates)
        if '{verb_capitalized}' in template:
            context['verb_capitalized'] = context.get('verb', '').capitalize()
        return template.format(**context)

    def _get_narrative_string(self, key, context=None):
        """Helper to get a random narrative string and format it."""
        if context is None:
            context = {}

        # Add team/player context if not already present
        if 'batter_name' not in context:
            batter = (self.team1_lineup if not self.top_of_inning else self.team2_lineup)[getattr(self, 'team1_batter_idx' if not self.top_of_inning else 'team2_batter_idx')]
            context['batter_name'] = batter['legal_name']

        # Add runner context
        if 'runner_name' not in context and self.bases[0]:
             context['runner_name'] = self.bases[0]

        return self.commentary_rng.choice(GAME_CONTEXT['narrative_strings'].get(key, [""])).format(**context)

    def _generate_play_description(self, outcome, batted_ball_data, pitch_details, batter=None, fielder=None):
        """Generates a narrative description for an in-play event."""
        verb = self._get_batted_ball_verb(outcome, batted_ball_data.get('ev'), batted_ball_data.get('la'))
        direction = ""

        # For hits, get a direction
        if outcome in ["Single", "Double", "Triple", "Home Run"]:
            direction = self._get_hit_location(outcome, batted_ball_data.get('ev'), batted_ball_data.get('la'))
        # For outs, get a direction based on the fielder
        elif fielder:
            direction = GAME_CONTEXT['hit_directions'].get(fielder['position']['abbreviation'], "")

        # Construct a more natural sentence.
        # e.g., "Nakamura lines a single to left field."
        # e.g., "Moon grounds out to second."
        if batter and direction:
            template = self.commentary_rng.choice(GAME_CONTEXT['narrative_strings']['play_by_play_templates'])
            return "  " + template.format(
                batter_name=batter['legal_name'],
                verb=verb,
                direction=direction,
                pitch_type=pitch_details.get('type', 'pitch'),
                pitch_velo=pitch_details.get('velo', 'N/A')
            )

        # Fallback for simpler descriptions
        return f"  {verb.capitalize()} {direction}."

    def _simulate_at_bat(self, batter, pitcher):
        balls, strikes = 0, 0
        play_events: list[PlayEvent] = []
        
        if self.base_commentary_style != 'none':
            batter_display_name = self._get_player_display_name(batter)
            outs_str = f"{self.outs} out{'s' if self.outs != 1 else ''}"
            bases_str = self._get_bases_str()
            situation = f"{outs_str}, {bases_str}" if bases_str != "Bases empty" else f"{outs_str}"
            self._print(f"\n{batter_display_name} steps to the plate. {situation}.")

        if self.base_commentary_style == 'narrative' and self.verbose_phrasing:
            if any(self.bases):
                if (self.bases[1] or self.bases[2]) and self.commentary_rng.random() < 0.2:
                    self._print(f"  {self._get_narrative_string('runners_in_scoring_position')}")
                if self.inning > 6 and self.team1_score == self.team2_score and self.commentary_rng.random() < 0.25:
                    self._print(f"  A crucial at-bat here in a tie game.")
            if self.commentary_rng.random() < 0.04: self._print(f"  {self._get_narrative_string('infield_in')}")

        if self.game_rng.random() < batter.get('stats', {}).get('HBP', 0):
            return "HBP", None, play_events

        batter_stats = batter['stats']
        discipline_factor = max(0.1, batter_stats.get('Walk', 0.09) / 0.08)
        swing_at_ball_prob = 0.30 / discipline_factor
        contact_prob = 0.75 / max(0.1, batter_stats.get('Strikeout', 0.17) / 0.17)

        while balls < 4 and strikes < 3:
            self.pitch_counts[pitcher['legal_name']] += 1
            
            pitch_selection = self.game_rng.choices(list(pitcher['pitch_arsenal'].keys()), weights=[v['prob'] for v in pitcher['pitch_arsenal'].values()], k=1)[0]
            pitch_details_team = pitcher['pitch_arsenal'][pitch_selection]
            pitch_velo = round(self.game_rng.uniform(*pitch_details_team['velo_range']), 1)
            pitch_spin = self.game_rng.randint(*pitch_details_team.get('spin_range', (2000, 2500))) if self.game_rng.random() > 0.08 else None
            
            fatigue_penalty = (max(0, self.pitch_counts[pitcher['legal_name']] - pitcher['stamina']) / 15) * 0.1
            is_strike_loc = self.game_rng.random() < (pitcher['control'] - fatigue_penalty)
            
            pre_pitch_balls, pre_pitch_strikes = balls, strikes
            pitch_outcome_text = ""
            event_details: PlayEvent['details'] = {}
            is_in_play = False
            hit_result = None

            swing = self.game_rng.random() < (0.85 if is_strike_loc else swing_at_ball_prob)
            contact = self.game_rng.random() < contact_prob

            if not swing:
                if is_strike_loc:
                    strikes += 1; pitch_outcome_text = "called strike"
                    event_details = {'code': 'C', 'description': 'Called Strike', 'isStrike': True}
                else:
                    balls += 1; pitch_outcome_text = "ball"
                    event_details = {'code': 'B', 'description': 'Ball', 'isStrike': False}
            else: # Swung
                if not contact:
                    strikes += 1; pitch_outcome_text = "swinging strike"
                    event_details = {'code': 'S', 'description': 'Swinging Strike', 'isStrike': True}
                else: # Contact
                    is_foul = self.game_rng.random() < 0.6
                    if is_foul:
                        if strikes < 2: strikes += 1
                        pitch_outcome_text = "foul"
                        event_details = {'code': 'D', 'description': 'Foul', 'isStrike': True}
                    else: # In Play
                        is_in_play = True
                        hit_result = self._get_hit_outcome(batter['stats'])
                        pitch_outcome_text = "in play"
                        event_details = {'code': 'X', 'description': f'In play, {hit_result}', 'isStrike': True}

            if self.generate_gameday:
                event_details['type'] = {'code': GAME_CONTEXT['PITCH_TYPE_MAP'].get(pitch_selection, 'UN'), 'description': pitch_selection.capitalize()}
                pitch_data: PitchData = {'startSpeed': pitch_velo}
                if pitch_spin: pitch_data['breaks'] = {'spinRate': pitch_spin}
                play_events.append({'index': len(play_events), 'details': event_details, 'count': {'balls': pre_pitch_balls, 'strikes': pre_pitch_strikes}, 'pitchData': pitch_data})

            if is_in_play:
                batted_ball_data = self._generate_batted_ball_data(hit_result)
                description_context = {
                    'batted_ball_data': batted_ball_data,
                    'pitch_details': {'type': pitch_selection, 'velo': pitch_velo, 'spin': pitch_spin}
                }
                if self.generate_gameday and 'ev' in batted_ball_data:
                    play_events[-1]['hitData'] = {
                        'launchSpeed': batted_ball_data['ev'], 'launchAngle': batted_ball_data['la'],
                        'trajectory': self._get_trajectory(hit_result, batted_ball_data['la'])
                    }
                return hit_result, description_context, play_events

            if self.base_commentary_style == 'narrative':
                if self.verbose_phrasing:
                    pbp_line = ""
                    if pitch_outcome_text == "foul":
                        pbp_line = f"  Foul, {self.commentary_rng.choice(GAME_CONTEXT['pitch_locations']['foul'])} on a {pitch_selection} ({pitch_velo} mph)."
                    elif pitch_outcome_text == "called strike":
                        pbp_line = f"  {self.commentary_rng.choice(GAME_CONTEXT['narrative_strings']['strike_called'])} with the {pitch_selection} ({pitch_velo} mph)."
                    elif pitch_outcome_text == "swinging strike":
                        pbp_line = f"  {self._get_narrative_string('strike_swinging')} on a {pitch_selection} ({pitch_velo} mph)."
                    else: # Ball
                        pbp_line = f"  {self.commentary_rng.choice(GAME_CONTEXT['pitch_locations']['ball'])} with the {pitch_selection} ({pitch_velo} mph)."
                else:
                    pbp_line = f"  {pitch_outcome_text.capitalize()}."

                if balls < 4 and strikes < 3:
                    pbp_line += f" {balls}-{strikes}."
                self._print(pbp_line)
            elif self.base_commentary_style == 'statcast':
                self._print(f"  {pitch_outcome_text.capitalize()}: {pitch_velo} mph {pitch_selection}")

        if balls == 4:
            return "Walk", None, play_events

        k_type = "looking" if pitch_outcome_text == "called strike" else "swinging"
        verb = self.commentary_rng.choice(GAME_CONTEXT['statcast_verbs']['Strikeout'][k_type])
        description = {'k_type': k_type, 'verb': verb} if self.base_commentary_style != 'narrative' else {}
        if self.base_commentary_style == 'narrative' and self.verbose_phrasing:
            self._print(f"  {batter['legal_name']} {verb}.")
        return "Strikeout", description, play_events

    def _advance_runners(self, hit_type, batter, was_error=False, include_batter_advance=False):
        runs, rbis = 0, 0
        advances = []
        batter_name = batter['legal_name']
        batter_gets_rbi = not was_error

        if hit_type in ["Walk", "HBP"]:
            new_bases = self.bases[:]
            if new_bases[0]:
                if new_bases[1]:
                    if new_bases[2]: runs += 1; rbis += 1; advances.append(f"{new_bases[2]} scores")
                    advances.append(f"{new_bases[1]} to 3B"); new_bases[2] = new_bases[1]
                advances.append(f"{new_bases[0]} to 2B"); new_bases[1] = new_bases[0]
            new_bases[0] = batter_name
            self.bases = new_bases
            return {'runs': runs, 'rbis': rbis, 'advances': advances}

        old_bases = self.bases[:]
        new_bases = [None, None, None]
        if hit_type == 'Single':
            if old_bases[2]: runs += 1; rbis += (1 if batter_gets_rbi else 0); advances.append(f"{old_bases[2]} scores")
            if old_bases[1]: new_bases[2] = old_bases[1]; advances.append(f"{old_bases[1]} to 3B")
            if old_bases[0]: new_bases[1] = old_bases[0]; advances.append(f"{old_bases[0]} to 2B")
            new_bases[0] = batter_name
            if include_batter_advance: advances.append(f"{batter_name} to 1B")
        elif hit_type == 'Double':
            if old_bases[2]: runs += 1; rbis += (1 if batter_gets_rbi else 0); advances.append(f"{old_bases[2]} scores")
            if old_bases[1]: runs += 1; rbis += (1 if batter_gets_rbi else 0); advances.append(f"{old_bases[1]} scores")
            if old_bases[0]: new_bases[2] = old_bases[0]; advances.append(f"{old_bases[0]} to 3B")
            new_bases[1] = batter_name
            if include_batter_advance: advances.append(f"{batter_name} to 2B")
        elif hit_type == 'Triple':
            for runner in old_bases:
                if runner: runs += 1; rbis += (1 if batter_gets_rbi else 0); advances.append(f"{runner} scores")
            new_bases[2] = batter_name
            if include_batter_advance: advances.append(f"{batter_name} to 3B")
        elif hit_type == 'Home Run':
            for runner in old_bases:
                if runner: runs += 1; rbis += 1; advances.append(f"{runner} scores")
            runs += 1; rbis += 1; advances.append(f"{batter_name} scores")

        self.bases = new_bases
        return {'runs': runs, 'rbis': rbis, 'advances': advances}

    def _get_bases_str(self):
        if self.use_bracketed_ui:
            return f"[{'1B' if self.bases[0] else '_'}]-[{'2B' if self.bases[1] else '_'}]-[{'3B' if self.bases[2] else '_'}]"
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
        fatigue_factor = max(0, self.pitch_counts[current_pitcher_name] - pitcher_stats[current_pitcher_name]['stamina'])
        if fatigue_factor > 0 and available_bullpen:
            next_pitcher_name = available_bullpen[0]
            if is_home_team_pitching:
                if self.team1_current_pitcher_name != next_pitcher_name:
                    self._print(f"\n--- Pitching Change for {team_name}: {next_pitcher_name} replaces {self.team1_current_pitcher_name} ---\n")
                    self.team1_current_pitcher_name, self.team1_available_bullpen = next_pitcher_name, available_bullpen[1:]
            else:
                if self.team2_current_pitcher_name != next_pitcher_name:
                    self._print(f"\n--- Pitching Change for {team_name}: {next_pitcher_name} replaces {self.team2_current_pitcher_name} ---\n")
                    self.team2_current_pitcher_name, self.team2_available_bullpen = next_pitcher_name, available_bullpen[1:]

    def _handle_batted_ball_out(self, out_type, batter, context=None):
        defensive_team_prefix = 'team1' if self.top_of_inning else 'team2'
        infielders = getattr(self, f"{defensive_team_prefix}_infielders")
        outfielders = getattr(self, f"{defensive_team_prefix}_outfielders")
        pitcher = getattr(self, f"{defensive_team_prefix}_pitcher_stats")[getattr(self, f"{defensive_team_prefix}_current_pitcher_name")]
        catcher = getattr(self, f"{defensive_team_prefix}_catcher")
        first_baseman = getattr(self, f"{defensive_team_prefix}_defense").get('1B')

        fielder, is_error, credits = None, False, []
        batted_ball_data = context.get('batted_ball_data', {}) if context else {}
        
        if out_type == 'Groundout':
            grounder_candidates = [(p, 6) for p in infielders] + [(pitcher, 1)] + ([(catcher, 0.25)] if catcher else [])
            fielder = self.game_rng.choices([c[0] for c in grounder_candidates], weights=[c[1] for c in grounder_candidates], k=1)[0]
            if fielder['position']['abbreviation'] == 'C' and 'ev' in batted_ball_data:
                batted_ball_data['ev'], batted_ball_data['la'] = round(self.game_rng.uniform(50, 70), 1), round(self.game_rng.uniform(-45, -20), 1)
        elif out_type == 'Flyout':
            fielder = self.game_rng.choices(outfielders + infielders, weights=[6] * len(outfielders) + [1] * len(infielders), k=1)[0]

        if fielder and self.game_rng.random() > fielder['fielding_ability'] * (self.team1_data if self.top_of_inning else self.team2_data)['fielding_prowess']:
            is_error = True

        pos_map = {'P': 1, 'C': 2, '1B': 3, '2B': 4, '3B': 5, 'SS': 6, 'LF': 7, 'CF': 8, 'RF': 9}

        if is_error:
            fielder_pos_abbr = fielder['position']['abbreviation']
            notation = f"E{pos_map.get(fielder_pos_abbr, '')}"
            if self.base_commentary_style == 'narrative' and self.verbose_phrasing:
                self._print(f"  An error by {fielder_pos_abbr} {fielder['legal_name']} allows the batter to reach base.")
            elif self.base_commentary_style == 'statcast':
                return f"{notation} on a {'ground ball' if out_type == 'Groundout' else 'fly ball'} to {fielder_pos_abbr};", 0, True, 0, []
            return f"Reached on Error ({notation})", 0, True, 0, []

        # If not an error, generate the normal out commentary
        if self.base_commentary_style == 'narrative' and context:
            self._print(self._generate_play_description(out_type, batted_ball_data, context.get('pitch_details', {}), batter, fielder))

        runs, rbis, notation = 0, 0, ""
        if out_type == 'Flyout':
            fielder_pos = fielder['position']['abbreviation']
            out_desc = "pop out" if fielder['position']['abbreviation'] in ['P', 'C', '1B', '2B', '3B', 'SS'] else "flyout"
            notation = f"{'P' if out_desc == 'pop out' else 'F'}{fielder['position']['code']}"
            credits.append({'player': {'id': fielder['id']}, 'position': fielder['position'], 'credit': 'putout'})

            if self.outs < 2 and self.bases[2] and fielder_pos in ['LF', 'CF', 'RF'] and self.game_rng.random() > 0.4:
                self.outs += 1; runs, rbis = 1, 1
                runner_on_third, self.bases[2] = self.bases[2], None
                if self.base_commentary_style == 'statcast':
                    return f"Sac fly to {fielder_pos}. {runner_on_third} scores.", runs, False, rbis, credits
                elif self.base_commentary_style == 'narrative' and self.verbose_phrasing:
                    self._print(f"  That's a sacrifice fly. {runner_on_third} tags up and scores!"); notation += " (SF)"
            else:
                self.outs += 1

            if self.base_commentary_style == 'statcast':
                verb = self._get_batted_ball_verb('Flyout', batted_ball_data.get('ev'), batted_ball_data.get('la')) if batted_ball_data else "flies out"
                direction = GAME_CONTEXT['hit_directions'].get(fielder_pos, f"to {fielder_pos}")
                result_line = self._format_statcast_template('Flyout', {'batter_name': batter['legal_name'], 'verb': verb, 'direction': direction, 'fielder_name': fielder['legal_name']})
                return result_line, runs, False, rbis, credits
            return f"{out_desc.capitalize()} to {fielder_pos} ({notation})", runs, False, rbis, credits

        if out_type == 'Groundout':
            if self.outs < 2 and self.bases[0] and self.game_rng.random() < self.team1_data['double_play_rate']:
                self.outs += 2
                self.bases[0] = None
                if self.bases[1]: self.bases[2], self.bases[1] = self.bases[1], None
                ss, sb = getattr(self, f"{defensive_team_prefix}_defense").get('SS'), getattr(self, f"{defensive_team_prefix}_defense").get('2B')
                if fielder['position']['abbreviation'] == 'SS' and sb and first_baseman:
                    notation, credits = "6-4-3", [{'player': {'id': fielder['id']}, 'credit': 'assist'}, {'player': {'id': sb['id']}, 'credit': 'assist'}, {'player': {'id': first_baseman['id']}, 'credit': 'putout'}]
                elif fielder['position']['abbreviation'] == '3B' and sb and first_baseman:
                     notation, credits = "5-4-3", [{'player': {'id': fielder['id']}, 'credit': 'assist'}, {'player': {'id': sb['id']}, 'credit': 'assist'}, {'player': {'id': first_baseman['id']}, 'credit': 'putout'}]
                else:
                    notation, credits = f"{fielder['position']['code']}U", [{'player': {'id': fielder['id']}, 'credit': 'putout'}, {'player': {'id': fielder['id']}, 'credit': 'putout'}]
                if self.base_commentary_style == 'statcast':
                    return f"Grounds into a {notation} double play.", 0, False, 0, credits
                elif self.base_commentary_style == 'narrative' and self.verbose_phrasing:
                    self._print(f"  {self._get_narrative_string('double_play')}")
                return f"Groundout, Double Play ({notation})", 0, False, 0, credits

            self.outs += 1
            if self.outs < 3:
                if self.bases[2]: runs, rbis, self.bases[2] = 1, 1, None
                if self.bases[1]: self.bases[2], self.bases[1] = self.bases[1], None
                if self.bases[0]: self.bases[1], self.bases[0] = self.bases[0], None
            else:
                runs, rbis = 0, 0

            play_label = f"Groundout to {fielder['position']['abbreviation']}"
            if fielder['position']['abbreviation'] == '1B' and first_baseman:
                notation, credits = "3U", [{'player': {'id': first_baseman['id']}, 'credit': 'putout'}]
            elif first_baseman:
                notation = f"{fielder['position']['code']}-3"
                credits = [{'player': {'id': fielder['id']}, 'credit': 'assist'}, {'player': {'id': first_baseman['id']}, 'credit': 'putout'}]
            if self.base_commentary_style == 'statcast':
                verb = self._get_batted_ball_verb('Groundout', batted_ball_data.get('ev'), batted_ball_data.get('la')) if batted_ball_data else "grounds out"
                direction = GAME_CONTEXT['hit_directions'].get(fielder['position']['abbreviation'], f"to {fielder['position']['abbreviation']}")
                result_line = self._format_statcast_template('Groundout', {'batter_name': batter['legal_name'], 'verb': verb, 'direction': direction, 'fielder_name': fielder['legal_name']})
                return result_line, runs, False, rbis, credits
            return f"{play_label} ({notation})", runs, False, rbis, credits
        return "Error", 0, True, 0, []

    def _simulate_half_inning(self):
        self.outs, self.bases = 0, [None, None, None]
        is_home_team_batting = not self.top_of_inning
        batting_team_name, lineup, batter_idx_ref = (self.team1_name, self.team1_lineup, 'team1_batter_idx') if is_home_team_batting else (self.team2_name, self.team2_lineup, 'team2_batter_idx')

        if self.inning >= 10:
            last_batter_idx = (getattr(self, batter_idx_ref) - 1 + 9) % 9
            runner_name = lineup[last_batter_idx]['legal_name']
            self.bases[1] = runner_name
            if self.verbose_phrasing and self.base_commentary_style == 'narrative':
                self._print(f"Automatic runner on second: {runner_name} jogs out to take his lead.")

        if self.base_commentary_style != 'none':
            inning_half = "Bottom" if is_home_team_batting else "Top"
            self._print("-" * 50)
            self._print(f"{inning_half} of Inning {self.inning} | {batting_team_name} batting")

        while self.outs < 3:
            self._manage_pitching_change()
            pitcher_name = self.team1_current_pitcher_name if self.top_of_inning else self.team2_current_pitcher_name
            pitcher = (self.team1_pitcher_stats if self.top_of_inning else self.team2_pitcher_stats)[pitcher_name]
            batter = lineup[getattr(self, batter_idx_ref)]

            outcome, description, play_events = self._simulate_at_bat(batter, pitcher)

            runs, rbis, was_error = 0, 0, False
            advances, credits = [], []

            display_outcome = outcome
            if outcome in ["Groundout", "Flyout"]:
                display_outcome, new_runs, was_error, new_rbis, credits_from_out = self._handle_batted_ball_out(outcome, batter, description)
                runs += new_runs; rbis += new_rbis
                credits.extend(credits_from_out)
                if was_error:
                    outcome = "Field Error"
                    adv_info = self._advance_runners("Single", batter, was_error=True, include_batter_advance=True)
                    runs += adv_info['runs']; advances.extend(adv_info['advances'])
            elif outcome == "Strikeout":
                self.outs += 1
                statcast_data = description.get('batted_ball_data', {}) if description else {}
                if self.base_commentary_style == 'statcast' and statcast_data and 'k_type' in statcast_data:
                    display_outcome = f"{batter['legal_name']} {self.commentary_rng.choice(GAME_CONTEXT['statcast_verbs']['Strikeout'][statcast_data.get('k_type')])}."
            elif outcome in ["Single", "Double", "Triple", "Home Run", "Walk", "HBP"]:
                if self.base_commentary_style == 'narrative' and self.verbose_phrasing:
                    # Use situational narrative strings
                    if self.outs == 0 and outcome in ["Single", "Double", "Walk"]:
                        self._print(f"  {self._get_narrative_string(f'leadoff_{outcome.lower()}', {'batter_name': batter['legal_name']})}")
                    elif self.outs == 2 and outcome in ["Single", "Double", "Walk"]:
                         self._print(f"  {self._get_narrative_string(f'two_out_{outcome.lower()}', {'batter_name': batter['legal_name']})}")
                    elif outcome == "Walk":
                        self._print(f"  {batter['legal_name']} draws a walk.")
                    # Generate detailed description for hits
                    elif description:
                        self._print(self._generate_play_description(outcome, description.get('batted_ball_data', {}), description.get('pitch_details', {}), batter))

                adv_info = self._advance_runners(outcome, batter)
                runs += adv_info['runs']; rbis += adv_info['rbis']; advances.extend(adv_info['advances'])

            if is_home_team_batting: self.team1_score += runs
            else: self.team2_score += runs

            if self.generate_gameday:
                # Update per-inning run totals in linescore
                if runs > 0:
                    current_inning_idx = self.inning - 1
                    if is_home_team_batting:
                        self.gameday_data['liveData']['linescore']['innings'][current_inning_idx]['home']['runs'] += runs
                    else:
                        self.gameday_data['liveData']['linescore']['innings'][current_inning_idx]['away']['runs'] += runs

                at_bat_index = len(self.gameday_data['liveData']['plays']['allPlays'])
                play_result = PlayResult(type="atBat", event=outcome, eventType=outcome.lower(), description="", rbi=rbis, awayScore=self.team2_score, homeScore=self.team1_score)
                play_about = PlayAbout(atBatIndex=at_bat_index, halfInning="bottom" if is_home_team_batting else "top", isTopInning=not is_home_team_batting, inning=self.inning, isScoringPlay=runs > 0)
                final_count = PlayCount(balls=0, strikes=0, outs=self.outs)

                runner_list: list[Runner] = []
                if credits: runner_list.append({"movement": {}, "details": {}, "credits": credits})

                play_data: Play = {"result": play_result, "about": play_about, "count": final_count, "playEvents": play_events, "runners": runner_list}
                self.gameday_data['liveData']['plays']['allPlays'].append(play_data)

                ls = self.gameday_data['liveData']['linescore']
                ls['outs'] = self.outs
                ls['teams']['home']['runs'] = self.team1_score
                ls['teams']['away']['runs'] = self.team2_score
                if outcome not in ["Walk", "Strikeout", "HBP", "Groundout", "Flyout"]:
                    if is_home_team_batting: ls['teams']['home']['hits'] += 1
                    else: ls['teams']['away']['hits'] += 1
                if was_error:
                    if is_home_team_batting: ls['teams']['away']['errors'] += 1
                    else: ls['teams']['home']['errors'] += 1

            if self.base_commentary_style == 'statcast':
                self._print_statcast_result(display_outcome, outcome, description, was_error, advances, rbis, batter)
            elif self.base_commentary_style == 'narrative': # narrative
                self._print_narrative_result(display_outcome, outcome, description)

            if self.base_commentary_style != 'none':
                score_str = f"{self.team1_name}: {self.team1_score}, {self.team2_name}: {self.team2_score}"
                if self.outs < 3: self._print(f" | Outs: {self.outs} | Bases: {self._get_bases_str()} | Score: {score_str}\n")
                else: self._print(f" | Outs: {self.outs} | Score: {score_str}\n")
            
            setattr(self, batter_idx_ref, (getattr(self, batter_idx_ref) + 1) % 9)
            if self.outs >= 3: break
            if is_home_team_batting and self.team1_score > self.team2_score and self.inning >= 9:
                return

    def _print_narrative_result(self, display_outcome, outcome, description):
        # If we have a detailed description, don't print a generic "Result" line for hits.
        if self.verbose_phrasing and description and outcome in ["Single", "Double", "Triple", "Home Run"]:
            return

        result_line = display_outcome
        if outcome in ["Walk", "Strikeout"]: result_line = outcome
        elif outcome == "HBP": result_line = "Hit by Pitch"

        if outcome not in ["Single", "Double", "Triple", "Home Run"]:
             self._print(f" Result: {result_line}", end="")
        else:
             self._print(f" Result: {outcome}", end="")

    def _print_statcast_result(self, display_outcome, outcome, description, was_error, advances, rbis, batter):
        pitch_info = description.get('batted_ball_data', {}) if description else {}
        batted_ball_str = ""
        if outcome not in ["Strikeout", "Walk", "HBP"] and pitch_info and 'ev' in pitch_info and 'la' in pitch_info:
            batted_ball_str = f" (EV: {pitch_info['ev']} mph, LA: {pitch_info['la']}°)"
        result_line = display_outcome
        if was_error:
            result_line = self._format_statcast_template('Error', {'display_outcome': display_outcome, 'adv_str': "; ".join(adv for adv in advances), 'batter_name': batter['legal_name']})
        elif outcome == 'Strikeout' and description and 'k_type' in description:
            result_line = f"{batter['legal_name']} {self.commentary_rng.choice(GAME_CONTEXT['statcast_verbs']['Strikeout'][description.get('k_type')])}."
        elif outcome in GAME_CONTEXT['statcast_verbs'] and outcome not in ['Flyout', 'Groundout']:
            verb = self._get_batted_ball_verb(outcome, pitch_info.get('ev'), pitch_info.get('la')) if pitch_info else self.commentary_rng.choice(GAME_CONTEXT['statcast_verbs'][outcome]['default'])
            direction = self._get_hit_location(outcome, pitch_info.get('ev'), pitch_info.get('la')) if pitch_info else ""
            result_line = self._format_statcast_template(outcome, {'batter_name': batter['legal_name'], 'verb': verb, 'runs': rbis, 'direction': direction}) or f"{batter['legal_name']} {verb}."
        elif outcome == "HBP": result_line = "Hit by Pitch."
        if batted_ball_str: result_line += batted_ball_str
        if rbis > 0 and not was_error: result_line += f" {batter['legal_name']} drives in {rbis}."
        if not was_error and advances:
            if adv_str := "; ".join(advances): result_line += f" ({adv_str})"
        self._print(f"Result: {result_line}")

    def _print_pre_game_summary(self):
        self._print("=" * 20 + " GAME START " + "=" * 20)
        self._print(f"{self.team2_name} vs. {self.team1_name}")
        self._print(f"Venue: {self.venue}")
        self._print(f"Weather: {self.weather}")
        self._print(f"Umpires: HP: {self.umpires[0]}, 1B: {self.umpires[1]}, 2B: {self.umpires[2]}, 3B: {self.umpires[3]}")
        self._print("-" * 50)

    def play_game(self):
        if self.base_commentary_style != 'none': self._print_pre_game_summary()

        # Determine when to stop: max_innings takes precedence if set
        should_continue = lambda: (self.inning <= 9 or self.team1_score == self.team2_score) if self.max_innings is None else self.inning <= self.max_innings

        while should_continue():
            self.top_of_inning = True
            self._simulate_half_inning()

            if self.inning >= 9 and not self.top_of_inning and self.team1_score > self.team2_score:
                break # Home team wins in the bottom of the 9th or later

            if self.max_innings and self.inning >= self.max_innings:
                break

            self.top_of_inning = False
            self._simulate_half_inning()

            if self.inning >= 9 and not self.top_of_inning and self.team1_score > self.team2_score:
                break

            if self.max_innings and self.inning >= self.max_innings:
                break

            self.inning += 1
            if self.generate_gameday:
                self.gameday_data['liveData']['linescore']['currentInning'] = self.inning
                self.gameday_data['liveData']['linescore']['innings'].append({'num': self.inning, 'home': {'runs': 0}, 'away': {'runs': 0}})

        if self.base_commentary_style != 'none' and self.max_innings is None:
            self._print("=" * 20 + " GAME OVER " + "=" * 20)
            self._print(f"\nFinal Score: {self.team1_name} {self.team1_score} - {self.team2_name} {self.team2_score}")
            winner = self.team1_name if self.team1_score > self.team2_score else self.team2_name
            self._print(f"\n{winner} win!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="A realistic baseball simulator.")
    parser.add_argument('--terse', action='store_true', help="Use terse, data-driven phrasing for play-by-play.")
    parser.add_argument('--bracketed-ui', action='store_true', help="Use the classic bracketed UI for base runners.")
    parser.add_argument('--commentary', type=str, choices=['narrative', 'statcast', 'gameday', 'combo'], default='narrative', help="Choose the commentary style.")
    parser.add_argument('--max-innings', type=int, help="Stop simulation after specified number of innings (e.g., 2 for partial game).")
    parser.add_argument('--pbp-outfile', type=str, help="File to write play-by-play output to (stdout by default).")
    parser.add_argument('--gameday-outfile', type=str, help="File to write Gameday JSON output to (stdout by default).")
    parser.add_argument('--game-seed', type=int, help="Seed for the game's random number generator.")
    parser.add_argument('--commentary-seed', type=int, help="Seed for the commentary's random number generator.")
    args = parser.parse_args()
    game = BaseballSimulator(
        TEAMS["BAY_BOMBERS"],
        TEAMS["PC_PILOTS"],
        verbose_phrasing=not args.terse,
        use_bracketed_ui=args.bracketed_ui,
        commentary_style=args.commentary,
        max_innings=args.max_innings,
        game_seed=args.game_seed,
        commentary_seed=args.commentary_seed
    )
    game.play_game()

    if game.base_commentary_style != 'none':
        pbp_output = "\n".join(game.output_lines)
        if args.pbp_outfile:
            with open(args.pbp_outfile, 'w') as f:
                f.write(pbp_output)
        else:
            print(pbp_output)

    if game.generate_gameday:
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime): return obj.isoformat()
                return super().default(obj)

        gameday_json = json.dumps(game.gameday_data, indent=2, cls=DateTimeEncoder)
        if args.gameday_outfile:
            with open(args.gameday_outfile, 'w') as f:
                f.write(gameday_json)
        else:
            print(gameday_json)