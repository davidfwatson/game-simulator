import json
import random
import uuid
from datetime import datetime, timezone
from typing import List

from gameday import (
    GamedayPlayEvents,
    PlayEvent,
    Count,
    Details,
    PitchData,
    PitchCoordinates,
    PitchBreaks,
    HitData,
    HitCoordinates,
    PlayEventType,
    DetailsType,
)
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

    def __init__(self, team1_data, team2_data, verbose_phrasing=True, use_bracketed_ui=False, commentary_style='narrative'):
        self.team1_data = team1_data
        self.team2_data = team2_data
        self.team1_name = self.team1_data["name"]
        self.team2_name = self.team2_data["name"]
        self.verbose_phrasing = verbose_phrasing
        self.use_bracketed_ui = use_bracketed_ui
        self.commentary_style = commentary_style

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

        # Gameday event tracking
        self.play_events: GamedayPlayEvents = []
        self.at_bat_index = 0
        self.play_event_index = 0

        # Game context
        self.umpires = random.sample(GAME_CONTEXT["umpires"], 4)
        self.weather = random.choice(GAME_CONTEXT["weather_conditions"])
        self.venue = self.team1_data["venue"]

    def _setup_pitchers(self, team_data, team_prefix):
        all_pitchers = [p for p in team_data["players"] if p['position'] == 'P']
        pitcher_stats = {p['legal_name']: p.copy() for p in all_pitchers}
        bullpen_candidates = [p['legal_name'] for p in all_pitchers if p['type'] != 'Starter']
        closers = [name for name in bullpen_candidates if pitcher_stats[name]['type'] == 'Closer']
        non_closers = [name for name in bullpen_candidates if pitcher_stats[name]['type'] != 'Closer']
        random.shuffle(non_closers)
        available_bullpen = non_closers + closers
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

    def _generate_batted_ball_data(self, hit_type):
        """Generates realistic exit velocity (EV) and launch angle (LA) for a given hit type."""
        # Occasionally return no data for realism, e.g., on errors or weird plays
        if random.random() < 0.05:
            return {}

        ev, la = 0, 0
        if hit_type == "Groundout":
            ev = round(random.uniform(70, 95), 1)
            la = round(random.uniform(-20, 5), 1)
        elif hit_type == "Flyout":
            ev = round(random.uniform(85, 105), 1)
            la = round(random.uniform(25, 50), 1)
        elif hit_type == "Single":
            # Can be a grounder or a liner
            if random.random() < 0.6: # 60% are grounders
                ev = round(random.uniform(80, 100), 1)
                la = round(random.uniform(-10, 8), 1)
            else: # 40% are liners
                ev = round(random.uniform(90, 110), 1)
                la = round(random.uniform(8, 20), 1)
        elif hit_type == "Double":
            ev = round(random.uniform(100, 115), 1)
            la = round(random.uniform(15, 35), 1)
        elif hit_type == "Triple":
            ev = round(random.uniform(100, 115), 1)
            la = round(random.uniform(18, 30), 1)
        elif hit_type == "Home Run":
            ev = round(random.uniform(100, 120), 1)
            # Correlate LA with EV. The harder it's hit, the lower the typical HR angle.
            if ev >= 118:
                # Max-effort swings that produce top-tier EV are almost never loopy.
                la = round(random.uniform(20, 28), 1)
            elif ev > 110:
                la = round(random.uniform(22, 35), 1)
            else:
                la = round(random.uniform(25, 45), 1)

        return {'ev': ev, 'la': la}

    def _describe_contact(self, outcome):
        contact_templates = {
            "Single": [
                "shoots a single through the right side",
                "drops a blooper into shallow center for a single",
                "stings a single back up the middle"
            ],
            "Double": [
                "hammers a double into the gap",
                "hooks a double down the line",
                "laces a ringing double off the wall"
            ],
            "Triple": [
                "splits the outfielders and motors for a triple",
                "drives it into the corner for a stand-up triple"
            ],
            "Home Run": [
                "launches it deep and out of here for a home run",
                "crushes a towering homer into the seats"
            ],
            "Groundout": [
                "rolls it over on the ground",
                "chops a bouncer toward the infield"
            ],
            "Flyout": [
                "lifts a routine fly ball",
                "skies it to the outfield"
            ],
            "Strikeout": [
                "goes down swinging",
                "is rung up"
            ]
        }

        if outcome in contact_templates:
            return random.choice(contact_templates[outcome])
        return "puts it in play"

    def _get_batted_ball_verb(self, outcome, ev, la):
        """Selects a descriptive verb based on batted ball data."""
        verb_cats = GAME_CONTEXT['statcast_verbs'].get(outcome, {})

        # If EV or LA data is missing, return a default verb immediately.
        if ev is None or la is None:
            return random.choice(verb_cats.get('default', ["describes"]))

        # Determine category based on EV and LA thresholds
        cat = 'default'
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
            # Popups are very high-angle, often weakly hit balls.
            if (ev < 95 and la > 50) or (ev < 90 and la > 40):
                cat = 'popup'
            elif ev > 100 and la > 30:
                cat = 'deep'

        return random.choice(verb_cats.get(cat, verb_cats.get('default', ["describes"])))

    def _format_statcast_template(self, outcome, context):
        """Formats a randomly chosen statcast template."""
        templates = GAME_CONTEXT.get('statcast_templates', {}).get(outcome)
        if not templates:
            return None

        template = random.choice(templates)

        # Ensure verb is capitalized if the template requires it
        if '{verb_capitalized}' in template:
            context['verb_capitalized'] = context.get('verb', '').capitalize()

        return template.format(**context)

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

    def _simulate_at_bat(self, batter, pitcher) -> GamedayPlayEvents:
        """
        Simulates a single at-bat, generating a detailed list of Gameday play events.
        This is the new "source of truth" for what happens in a game.
        """
        balls, strikes, pitch_num = 0, 0, 0
        at_bat_events: GamedayPlayEvents = []
        is_at_bat_over = False

        batter_stats = batter['stats']
        batter_walk_rate = batter_stats.get('Walk', 0.09)
        batter_k_rate = batter_stats.get('Strikeout', 0.17)
        discipline_factor = max(0.1, batter_walk_rate / 0.08)
        swing_at_ball_prob = 0.30 / discipline_factor
        k_propensity = max(0.1, batter_k_rate / 0.17)
        contact_prob = 0.75 / k_propensity

        # Pre-at-bat event (e.g., HBP on first pitch)
        if random.random() < batter.get('stats', {}).get('HBP', 0):
            # This is a simplification; a HBP can happen on any pitch.
            # For now, we model it as a pre-at-bat check.
            details = Details(description="Hit by Pitch", event="Hit by Pitch", isStrike=False, isBall=False)
            event = self._create_play_event(pitch_num=1, balls=0, strikes=0, details=details, is_pitch=False)
            event['type']['code'] = 'action'
            at_bat_events.append(event)
            return at_bat_events

        while not is_at_bat_over:
            pitch_num += 1
            self.pitch_counts[pitcher['legal_name']] += 1

            pitch_selection = random.choices(list(pitcher['pitch_arsenal'].keys()),
                                             weights=[v['prob'] for v in pitcher['pitch_arsenal'].values()], k=1)[0]
            pitch_details = pitcher['pitch_arsenal'][pitch_selection]
            pitch_velo = round(random.uniform(*pitch_details['velo_range']), 1)
            pitch_spin = random.randint(*pitch_details.get('spin_range', (2000, 2500))) if random.random() > 0.08 else None

            fatigue_factor = max(0, self.pitch_counts[pitcher['legal_name']] - pitcher['stamina'])
            fatigue_penalty = (fatigue_factor / 15) * 0.1
            is_strike_loc = random.random() < (pitcher['control'] - fatigue_penalty)

            if is_strike_loc:
                px, pz = round(random.uniform(-0.85, 0.85), 2), round(random.uniform(1.5, 3.5), 2)
            else:
                px = round(random.uniform(-1.5, 1.5), 2)
                pz = round(random.uniform(0.5, 4.5), 2)

            swing = random.random() < (0.85 if is_strike_loc else swing_at_ball_prob)
            
            details = Details(isStrike=False, isBall=False, isInPlay=False)
            details['type'] = DetailsType(code=pitch_details.get('code', 'FF'), description=pitch_selection)
            hit_result = None

            if swing:
                contact = random.random() < contact_prob
                if contact:
                    is_foul = random.random() < 0.4 # More realistic foul rate
                    if is_foul:
                        details.update(description="Foul", isStrike=True)
                        if strikes < 2:
                            strikes += 1
                        # At-bat continues on a 2-strike foul
                    else: # Fair ball
                        is_at_bat_over = True
                        details.update(isInPlay=True, isStrike=True)
                        hit_result = self._get_hit_outcome(batter['stats'])
                        details.update(description=f"In play, {hit_result.lower()}", event=hit_result)
                else: # Swing and miss
                    strikes += 1
                    details.update(description="Swinging Strike", isStrike=True)
            else: # No swing (taken pitch)
                if is_strike_loc:
                    strikes += 1
                    details.update(description="Called Strike", isStrike=True)
                else:
                    balls += 1
                    details.update(description="Ball", isBall=True)

            event = self._create_play_event(pitch_num, balls, strikes, details)

            # Add pitch data
            event['pitchData'] = self._create_pitch_data(pitch_velo, pitch_spin, px, pz)

            # Add hit data if in play
            if details.get('isInPlay'):
                batted_ball_data = self._generate_batted_ball_data(hit_result)
                event['hitData'] = HitData(
                    launchSpeed=batted_ball_data.get('ev'),
                    launchAngle=batted_ball_data.get('la'),
                    trajectory=self._get_trajectory(batted_ball_data.get('la')),
                    hardness=self._get_hardness(batted_ball_data.get('ev')),
                )

            at_bat_events.append(event)

            if balls == 4 or strikes == 3:
                is_at_bat_over = True

        # Create a final event for the at-bat outcome (Walk, Strikeout)
        final_event_details = Details(isPitch=False)
        if balls == 4:
            final_event_details.update(event="Walk", description="Walk")
        elif strikes == 3:
            k_type = "Swinging" if at_bat_events[-1]['details']['description'] == "Swinging Strike" else "Looking"
            final_event_details.update(event="Strikeout", description=f"Strikeout ({k_type})")

        if 'event' in final_event_details:
             final_event = self._create_play_event(pitch_num, balls, strikes, final_event_details, is_pitch=False)
             final_event['type']['code'] = 'action'
             at_bat_events.append(final_event)

        return at_bat_events

    def _create_play_event(self, pitch_num: int, balls: int, strikes: int, details: Details, is_pitch: bool = True) -> PlayEvent:
        """Helper to create a new PlayEvent dictionary."""
        return PlayEvent(
            index=self.play_event_index,
            playId=str(uuid.uuid4()),
            atBatIndex=self.at_bat_index,
            pitchNumber=pitch_num,
            isPitch=is_pitch,
            type=PlayEventType(code='pitch'),
            details=details,
            count=Count(balls=balls, strikes=strikes if strikes < 3 else 2), # Count can't be 3
        )

    def _create_pitch_data(self, velo: float, spin: int, px: float, pz: float) -> PitchData:
        """Helper to create a PitchData dictionary."""
        data = PitchData(startSpeed=velo)
        if spin:
            data['breaks'] = PitchBreaks(spinRate=spin)
        data['coordinates'] = PitchCoordinates(pX=px, pZ=pz)
        return data

    def _get_trajectory(self, launch_angle: float) -> str:
        if launch_angle is None: return "unknown"
        if launch_angle < 10: return "ground_ball"
        if launch_angle < 25: return "line_drive"
        if launch_angle < 50: return "fly_ball"
        return "popup"

    def _get_hardness(self, exit_velocity: float) -> str:
        if exit_velocity is None: return "unknown"
        if exit_velocity < 90: return "soft"
        if exit_velocity < 105: return "medium"
        return "hard"

    def _generate_narrative_commentary(self, events: GamedayPlayEvents, batter, outcome_summary) -> List[str]:
        lines = []
        for event in events:
            if not event['isPitch']:
                continue # Skip non-pitch action events for now

            details = event['details']
            pitch_data = event.get('pitchData', {})
            velo = pitch_data.get('startSpeed', '??')
            pitch_type = details.get('type', {}).get('description', 'pitch')

            if self.verbose_phrasing:
                location_desc = random.choice(GAME_CONTEXT['pitch_locations']['strike' if details['isStrike'] else 'ball'])
                pitch_desc = f"Pitch: {pitch_type} ({velo} mph), {location_desc}."
            else:
                pitch_desc = f"Pitch: {pitch_type} ({velo} mph)."

            if details.get('isInPlay'):
                contact_summary = self._describe_contact(details['event'])
                sentence = contact_summary[0].upper() + contact_summary[1:]
                punctuation = '!' if details['event'] in ["Single", "Double", "Triple", "Home Run"] else '.'
                lines.append(f"  {pitch_desc} {sentence}{punctuation}")
            else:
                balls, strikes = event['count']['balls'], event['count']['strikes']
                desc = details['description']
                if "Strike" in desc and strikes == 3:
                     lines.append(f"  {pitch_desc} {desc}{' (Whiff)' if 'Swinging' in desc else ''}.")
                elif "Ball" in desc and balls == 4:
                     lines.append(f"  {pitch_desc} {desc}.")
                else:
                     lines.append(f"  {pitch_desc} {desc}. Count: {balls}-{strikes}")

        lines.append(f"Result: {outcome_summary}")
        return lines

    def _generate_statcast_commentary(self, events: GamedayPlayEvents, batter, outcome_summary, advances, rbis, was_error) -> List[str]:
        lines = []
        # Print pitch-by-pitch info
        for event in events:
            if not event['isPitch'] or event['details'].get('isInPlay'):
                continue

            details = event['details']
            pitch_data = event.get('pitchData', {})
            velo = pitch_data.get('startSpeed', '??')
            spin = pitch_data.get('breaks', {}).get('spinRate')
            px = pitch_data.get('coordinates', {}).get('pX', 0)
            pz = pitch_data.get('coordinates', {}).get('pZ', 0)
            pitch_type = details.get('type', {}).get('description', 'pitch')

            verdict = details['description']
            location_str = f"px {px:.2f}, pz {pz:.2f}"
            spin_str = f" ({spin} rpm)" if spin is not None else ""
            lines.append(f"  {verdict}: {velo} mph {pitch_type}{spin_str}. Loc: ({location_str})")

        # The final result line
        final_event = events[-1]
        outcome = final_event['details']['event']
        hit_data = final_event.get('hitData')

        result_line = outcome_summary
        if was_error:
            adv_str = "; ".join(adv for adv in advances)
            context = {'display_outcome': outcome_summary, 'adv_str': adv_str, 'batter_name': batter['legal_name']}
            result_line = self._format_statcast_template('Error', context)
        elif outcome == 'Strikeout':
            k_type = 'swinging' if 'Swinging' in final_event['details']['description'] else 'looking'
            k_verb = random.choice(GAME_CONTEXT['statcast_verbs']['Strikeout'][k_type])
            result_line = f"{batter['legal_name']} {k_verb}."
        elif outcome in GAME_CONTEXT['statcast_verbs'] and outcome not in ['Flyout', 'Groundout']:
             verb = self._get_batted_ball_verb(outcome, hit_data.get('launchSpeed'), hit_data.get('launchAngle')) if hit_data else 'hits'
             template_context = {'batter_name': batter['legal_name'], 'verb': verb, 'runs': sum(1 for adv in advances if 'scores' in adv)}
             result_line = self._format_statcast_template(outcome, template_context) or f"{batter['legal_name']} {verb}."

        if hit_data and hit_data.get('launchSpeed') is not None:
            result_line += f" (EV: {hit_data['launchSpeed']} mph, LA: {hit_data['launchAngle']}°)"

        if rbis > 0 and not was_error: result_line += f" {batter['legal_name']} drives in {rbis}."
        if not was_error and advances:
            adv_str = "; ".join(advances)
            if adv_str: result_line += f" ({adv_str})"

        lines.append(f"Result: {result_line}")
        return lines

    def _advance_runners(self, hit_type, batter, was_error=False, include_batter_advance=False):
        runs = 0
        rbis = 0
        advances = []
        batter_name = batter['legal_name']
        batter_gets_rbi = not was_error

        if hit_type in ["Walk", "HBP"]:
            new_bases = self.bases[:]
            if new_bases[0]:
                if new_bases[1]:
                    if new_bases[2]:
                        runs += 1; rbis += 1; advances.append(f"{new_bases[2]} scores")
                    advances.append(f"{new_bases[1]} to 3B")
                    new_bases[2] = new_bases[1]
                advances.append(f"{new_bases[0]} to 2B")
                new_bases[1] = new_bases[0]
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

        if fatigue_factor > 0 and available_bullpen:
            # Simplified reliever selection logic
            next_pitcher_name = available_bullpen[0]

            if is_home_team_pitching:
                if self.team1_current_pitcher_name != next_pitcher_name:
                    if self.commentary_style != 'gameday':
                        print(f"\n--- Pitching Change for {team_name}: {next_pitcher_name} replaces {self.team1_current_pitcher_name} ---\n")
                    self.team1_current_pitcher_name = next_pitcher_name
                    self.team1_available_bullpen.remove(next_pitcher_name)
            else:
                if self.team2_current_pitcher_name != next_pitcher_name:
                    if self.commentary_style != 'gameday':
                        print(f"\n--- Pitching Change for {team_name}: {next_pitcher_name} replaces {self.team2_current_pitcher_name} ---\n")
                    self.team2_current_pitcher_name = next_pitcher_name
                    self.team2_available_bullpen.remove(next_pitcher_name)

    def _handle_batted_ball_out(self, out_type, batter, statcast_data=None):
        defensive_team = 'team1' if self.top_of_inning else 'team2'
        infielders = getattr(self, f"{defensive_team}_infielders")
        outfielders = getattr(self, f"{defensive_team}_outfielders")
        pitcher = getattr(self, f"{defensive_team}_pitcher_stats")[getattr(self, f"{defensive_team}_current_pitcher_name")]
        catcher = getattr(self, f"{defensive_team}_catcher")

        fielder = None
        is_error = False
        
        if out_type == 'Groundout':
            grounder_candidates = []
            # Infielders handle the overwhelming majority of routine grounders.
            for infielder in infielders:
                grounder_candidates.append((infielder, 6))

            # Pitchers occasionally field comebackers but not at a high clip.
            grounder_candidates.append((pitcher, 1))

            # Catcher grounders are almost always dribblers or bunt attempts.
            if catcher:
                grounder_candidates.append((catcher, 0.25))

            choices, weights = zip(*grounder_candidates)
            fielder = random.choices(choices, weights=weights, k=1)[0]

        if fielder and fielder['position'] == 'C' and statcast_data and statcast_data.get('launchSpeed'):
                # Force EV/LA to represent a soft dribbler/tapper
            statcast_data['launchSpeed'] = round(random.uniform(50, 70), 1)
            statcast_data['launchAngle'] = round(random.uniform(-45, -20), 1)
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
            pos_code = pos_map.get(fielder['position'], '')
            notation = f"E{pos_code}"
            if self.commentary_style == 'statcast':
                error_desc = 'ground ball' if out_type == 'Groundout' else 'fly ball'
                return f"{notation} on {error_desc} to {fielder['position']};", 0, True, 0

            if self.commentary_style == 'narrative':
                print(f"  An error by {fielder['position']} {fielder['legal_name']} allows the batter to reach base.")
            return f"Reached on Error ({notation})", 0, True, 0

        runs = 0
        rbis = 0
        notation = ""
        if out_type == 'Flyout':
            fielder_pos = fielder['position']
            infield_positions = ['P', 'C', '1B', '2B', '3B', 'SS']
            out_desc = "pop out" if fielder_pos in infield_positions else "flyout"
            notation = f"{'P' if out_desc == 'pop out' else 'F'}{pos_map[fielder_pos]}"

            # A sac fly cannot happen if there are 2 outs.
            is_sac_fly_possible = self.outs < 2 and self.bases[2] and fielder_pos in ['LF', 'CF', 'RF']

            if is_sac_fly_possible and random.random() > 0.4:
                self.outs += 1
                runner_on_third = self.bases[2]
                runs += 1
                rbis += 1
                self.bases[2] = None
                if self.commentary_style == 'statcast':
                    return f"Sac fly to {fielder_pos}. {runner_on_third} scores.", runs, False, rbis
                elif self.commentary_style == 'narrative':
                    print(f"  Sacrifice fly to {fielder_pos}, {runner_on_third} scores!")
                    notation += " (SF)"
            else:
                # Regular flyout, no run scores on the play itself.
                self.outs += 1

            if self.commentary_style == 'statcast':
                verb = self._get_batted_ball_verb('Flyout', statcast_data['ev'], statcast_data['la']) if statcast_data and 'ev' in statcast_data else random.choice(GAME_CONTEXT['statcast_verbs']['Flyout']['default'])

                # An outfielder cannot field an "infield fly". This logic corrects the verb if it's misused.
                is_outfielder = fielder['position'] in ['LF', 'CF', 'RF']
                if "infield fly" in verb and is_outfielder:
                    verb = "skies a popup" # Default to a more generic popup term

                context = {
                    'batter_name': batter['legal_name'],
                    'verb': verb,
                    'fielder_pos': fielder['position'],
                    'fielder_name': fielder['legal_name']
                }
                result_line = self._format_statcast_template('Flyout', context)
                return result_line, runs, False, rbis
            return f"{out_desc.capitalize()} to {fielder_pos} ({notation})", runs, False, rbis

        if out_type == 'Groundout':
            dp_opportunity = self.outs < 2 and self.bases[0] is not None
            dp_rate = self.team1_data['double_play_rate'] if self.top_of_inning else self.team2_data['double_play_rate']

            if dp_opportunity and random.random() < dp_rate:
                self.outs += 2
                runner_on_first = self.bases[0]

                route = "shortstop to second baseman to first baseman"
                notation = "6-4-3"
                if fielder['position'] == '2B':
                    route = "second baseman to shortstop to first baseman"
                    notation = "4-6-3"
                elif fielder['position'] == '1B':
                     route = "first baseman to shortstop to first baseman"
                     notation = "3-6-3"
                elif fielder['position'] == '3B':
                    route = "third baseman to second baseman to first baseman"
                    notation = "5-4-3"

                if self.commentary_style == 'statcast':
                    display_outcome = f"Grounds into a double play, {route} ({notation}); {runner_on_first} out at 2B; {batter['legal_name']} out at 1B."
                elif self.commentary_style == 'narrative':
                    print(f"  Ground ball... it's a {notation} double play!")
                    display_outcome = f"Groundout, Double Play ({notation})"
                else:
                    display_outcome = f"Groundout, Double Play ({notation})"

                self.bases[0] = None
                if self.bases[1]:
                    self.bases[2] = self.bases[1]
                    self.bases[1] = None
                return display_outcome, 0, False, 0

            self.outs += 1
            if self.outs < 3:
                if self.bases[2]:
                    runs += 1
                    rbis += 1
                    self.bases[2] = None
                if self.bases[1]: self.bases[2] = self.bases[1]; self.bases[1] = None
                if self.bases[0]: self.bases[1] = self.bases[0]; self.bases[0] = None
            else:
                # On the third out, no runners can advance or score.
                runs = 0
                rbis = 0

            play_label = f"Groundout to {fielder['position']}"
            if self.commentary_style == 'statcast':
                verb = self._get_batted_ball_verb('Groundout', statcast_data['ev'], statcast_data['la']) if statcast_data and 'ev' in statcast_data else random.choice(GAME_CONTEXT['statcast_verbs']['Groundout']['default'])
                context = {
                    'batter_name': batter['legal_name'],
                    'verb': verb,
                    'fielder_pos': fielder['position'],
                    'fielder_name': fielder['legal_name']
                }
                result_line = self._format_statcast_template('Groundout', context)
                return result_line, runs, False, rbis

            if fielder['position'] == '1B': notation = "3U"
            elif fielder['position'] == 'C': notation = "2-3"
            elif fielder['position'] == 'P': notation = "1-3"
            else: notation = f"{pos_map[fielder['position']]}-3"
            return f"{play_label} ({notation})", runs, False, rbis

        return "Error", 0, True, 0 # Should not be reached

    def _simulate_half_inning(self):
        self.outs, self.bases = 0, [None, None, None]

        is_home_team_batting = not self.top_of_inning
        batting_team_name, lineup, batter_idx_ref = (self.team1_name, self.team1_lineup, 'team1_batter_idx') if is_home_team_batting else (self.team2_name, self.team2_lineup, 'team2_batter_idx')

        if self.inning >= 10:
            last_batter_idx = (getattr(self, batter_idx_ref) - 1 + 9) % 9
            runner_name = lineup[last_batter_idx]['legal_name']
            self.bases[1] = runner_name
            # Gameday doesn't have a formal "ghost runner" event, so we'll just print for narrative.
            if self.verbose_phrasing and self.commentary_style == 'narrative':
                print(f"Automatic runner on second: {runner_name} jogs out to take his lead.")

        if self.commentary_style != 'gameday':
            inning_half = "Bottom" if is_home_team_batting else "Top"
            print("-" * 50)
            print(f"{inning_half} of Inning {self.inning} | {batting_team_name} batting")

        while self.outs < 3:
            self._manage_pitching_change()
            pitcher_name = self.team1_current_pitcher_name if self.top_of_inning else self.team2_current_pitcher_name
            pitcher_stats_dict = self.team1_pitcher_stats if self.top_of_inning else self.team2_pitcher_stats
            pitcher = pitcher_stats_dict[pitcher_name]

            batter_idx = getattr(self, batter_idx_ref)
            batter = lineup[batter_idx]
            if self.commentary_style != 'gameday':
                batter_display_name = self._get_player_display_name(batter)
                print(f"Now batting: {batter_display_name} ({batter['position']}, {batter['handedness']})")

            at_bat_events = self._simulate_at_bat(batter, pitcher)
            self.play_events.extend(at_bat_events)
            self.play_event_index += len(at_bat_events)
            self.at_bat_index += 1

            # The final event in the list determines the outcome of the at-bat.
            final_event = at_bat_events[-1]
            outcome = final_event['details']['event']
            description = final_event['details']['description']
            statcast_data = final_event.get('hitData')

            runs, was_error, rbis, advances = 0, False, 0, []

            display_outcome = outcome
            if outcome in ["Groundout", "Flyout"]:
                # The 'statcast_data' here is now the Gameday hitData, not the old ad-hoc dict
                display_outcome, new_runs, was_error, new_rbis = self._handle_batted_ball_out(outcome, batter, statcast_data)
                runs += new_runs
                rbis += new_rbis
                if was_error:
                    advancement_info = self._advance_runners("Single", batter, was_error=True, include_batter_advance=True)
                    runs += advancement_info['runs']
                    advances.extend(advancement_info['advances'])
            elif outcome == "Strikeout":
                self.outs += 1
            elif outcome in ["Single", "Double", "Triple", "Home Run", "Walk", "HBP"]:
                advancement_info = self._advance_runners(outcome, batter)
                runs += advancement_info['runs']
                rbis += advancement_info['rbis']
                advances.extend(advancement_info['advances'])

            # TODO: Handle WP/PB from Gameday events if they exist in the stream

            if is_home_team_batting: self.team1_score += runs
            else: self.team2_score += runs
            
            score_str = f"{self.team1_name}: {self.team1_score}, {self.team2_name}: {self.team2_score}"

            # --- Result Formatting and Printing ---
            outcome_summary = display_outcome
            if self.commentary_style == 'narrative':
                lines = self._generate_narrative_commentary(at_bat_events, batter, outcome_summary)
                for line in lines:
                    print(line)
            elif self.commentary_style == 'statcast':
                lines = self._generate_statcast_commentary(at_bat_events, batter, outcome_summary, advances, rbis, was_error)
                for line in lines:
                    print(line)
            # Gameday style is handled separately at the end of the game

            # Universal state printing
            if self.commentary_style != 'gameday':
                if self.outs < 3:
                    print(f" | Outs: {self.outs} | Bases: {self._get_bases_str()} | Score: {score_str}\n")
                else:
                    print(f" | Outs: {self.outs} | Score: {score_str}\n")
            
            setattr(self, batter_idx_ref, (batter_idx + 1) % 9)
            if self.outs >= 3: break
            if is_home_team_batting and self.team1_score > self.team2_score and self.inning >= 9:
                return

    def _print_pre_game_summary(self):
        if self.commentary_style == 'gameday':
            return
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

        if self.commentary_style == 'gameday':
            print(json.dumps(self.play_events, indent=2))
        else:
            print("="*20, "GAME OVER", "="*20)
            print(f"\nFinal Score: {self.team1_name} {self.team1_score} - {self.team2_name} {self.team2_score}")
            winner = self.team1_name if self.team1_score > self.team2_score else self.team2_name
            print(f"\n{winner} win!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="A realistic baseball simulator.")
    parser.add_argument('--terse', action='store_true', help="Use terse, data-driven phrasing for play-by-play.")
    parser.add_argument('--bracketed-ui', action='store_true', help="Use the classic bracketed UI for base runners.")
    parser.add_argument('--commentary', type=str, choices=['narrative', 'statcast', 'gameday'], default='narrative', help="Choose the commentary style: 'narrative' for descriptive play-by-play, 'statcast' for data-driven output, or 'gameday' for raw JSON events.")
    args = parser.parse_args()

    home_team_key = "BAY_BOMBERS"
    away_team_key = "PC_PILOTS"
    game = BaseballSimulator(
        TEAMS[home_team_key],
        TEAMS[away_team_key],
        verbose_phrasing=not args.terse,
        use_bracketed_ui=args.bracketed_ui,
        commentary_style=args.commentary
    )
    game.play_game()