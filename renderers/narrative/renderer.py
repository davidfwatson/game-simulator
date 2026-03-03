import random
from datetime import datetime
from commentary import GAME_CONTEXT
from gameday import GamedayData
from ..base import GameRenderer
from .helpers import (
    estimate_duration, get_ordinal, get_number_word, get_spoken_count,
    get_spoken_score_string, simplify_pitch_type, get_pitch_description_for_location
)

class NarrativeRenderer(GameRenderer):
    def __init__(self, gameday_data: GamedayData, seed: int = None, verbose: bool = True, use_bracketed_ui: bool = False):
        super().__init__(gameday_data, seed)
        self.verbose = verbose
        # use_bracketed_ui is ignored in new format as we don't print status lines
        self.last_foul_phrase = ""

        # Timing state
        self.last_event_end_time = None
        self.pending_text_buffer = ""

    def _estimate_duration(self, text):
        return estimate_duration(text)

    def _check_and_add_delay(self, current_end_time_iso, block_list, insert_at_index=-1, context='pitch'):
        if not self.last_event_end_time or not current_end_time_iso:
            if current_end_time_iso:
                 self.last_event_end_time = datetime.fromisoformat(current_end_time_iso)
            self.pending_text_buffer = ""
            return

        current_end = datetime.fromisoformat(current_end_time_iso)

        if context == 'inning':
            self.last_event_end_time = current_end
            self.pending_text_buffer = ""
            return

        gap = (current_end - self.last_event_end_time).total_seconds()

        spoken_duration = self._estimate_duration(self.pending_text_buffer)
        raw_delay = gap - spoken_duration

        final_delay = raw_delay
        if context == 'pitch':
             final_delay = raw_delay / 2
        elif context == 'batter':
             final_delay = raw_delay / 3

        if final_delay > 1.0:
            delay_line = f"[TTS SPLIT HERE DELAY:{final_delay:.1f}s]"
            if insert_at_index >= 0:
                block_list.insert(insert_at_index, delay_line)
            else:
                block_list.append(delay_line)

        self.last_event_end_time = current_end
        self.pending_text_buffer = ""

    def _add_to_buffer(self, text):
        if text:
            self.pending_text_buffer += text + " "

    def _get_pitch_description_for_location(self, event_type, zone, pitch_type_simple, batter_hand='R'):
        return get_pitch_description_for_location(event_type, zone, pitch_type_simple, self.rng_pitch, batter_hand)

    def _get_foul_description(self):
        options = GAME_CONTEXT['pitch_locations']['foul']

        for _ in range(10):
            choice = self.rng_pitch.choice(options)

            if choice == self.last_foul_phrase:
                continue

            if self.last_foul_phrase and (choice.startswith(self.last_foul_phrase) or self.last_foul_phrase.startswith(choice)):
                continue

            self.last_foul_phrase = choice
            return choice

        self.last_foul_phrase = choice
        return choice

    def _get_ordinal(self, n):
        return get_ordinal(n)

    def _get_number_word(self, n):
        return get_number_word(n)

    def _get_narrative_string(self, key, context=None, rng=None):
        if context is None: context = {}
        selected_rng = rng if rng else self.rng_play
        return selected_rng.choice(GAME_CONTEXT['narrative_strings'].get(key, [""])).format(**context)

    def _get_radio_string(self, key, context=None):
        if context is None: context = {}
        return self.rng_color.choice(GAME_CONTEXT['radio_strings'].get(key, [""])).format(**context)

    def _get_spoken_count(self, balls, strikes, connector="and"):
        return get_spoken_count(balls, strikes, connector)

    def _get_pitch_connector(self, balls, strikes, pitcher_name=None, batter_name=None, runners_on_base=False):
        if balls == 3 and strikes == 2:
            return self.rng_flow.choice(GAME_CONTEXT['narrative_strings']['payoff_pitch'])

        count_str = self._get_spoken_count(balls, strikes, connector="-")
        pitcher_last = pitcher_name.split()[-1] if pitcher_name else "The pitcher"
        batter_last = batter_name.split()[-1] if batter_name else "the batter"

        context = {
            'count_str': count_str,
            'count_str_cap': count_str.capitalize(),
            'pitcher_name_last': pitcher_last,
            'batter_name_last': batter_last
        }

        if balls == 0 and strikes == 0:
            if runners_on_base and self.rng_flow.random() < 0.5:
                 return self.rng_flow.choice(GAME_CONTEXT['narrative_strings'].get('pitch_connectors_stretch', ["And the pitch..."])).format(**context)

            templates = GAME_CONTEXT['narrative_strings'].get('pitch_connectors_00', ["And the pitch..."])
            return self.rng_flow.choice(templates).format(**context)

        templates = GAME_CONTEXT['narrative_strings'].get('pitch_connectors', [
            "And the {count_str}...",
            "The {count_str} pitch...",
            "And the {count_str} pitch..."
        ])

        return self.rng_flow.choice(templates).format(**context)

    def _simplify_pitch_type(self, pitch_type: str, capitalize=False) -> str:
        return simplify_pitch_type(pitch_type, self.rng_pitch, capitalize)

    def _get_spoken_score_string(self, score_a, score_b):
        return get_spoken_score_string(score_a, score_b)

    def _get_runner_status_string(self, outcome, batter_name, result_outs, is_leadoff, inning_context):
        from .play_description import get_runner_status_string as grss
        return grss(outcome, batter_name, result_outs, is_leadoff, inning_context, self.rng_play)

    def _generate_play_description(self, outcome, hit_data, pitch_details, batter_name, fielder_pos=None, fielder_name=None, connector=None, result_outs=None, is_leadoff=False, inning_context=""):
        from .play_description import generate_play_description as gpd
        return gpd(self, outcome, hit_data, pitch_details, batter_name, fielder_pos, fielder_name, connector, result_outs, is_leadoff, inning_context)

    def _render_steal_event(self, event):
        from .play_description import render_steal_event as rse
        return rse(self, event)

    def render(self) -> str:
        lines = []

        venue = self.gameday_data['gameData'].get('venue', 'the ballpark')

        def add_line(text):
            lines.append(text)
            self._add_to_buffer(text)

        network_name = GAME_CONTEXT.get('network_name', 'The Pacific Coast Baseball Network')
        away_team_city = self.gameday_data['gameData']['teams']['away'].get('locationName', 'City')
        home_team_city = self.gameday_data['gameData']['teams']['home'].get('locationName', 'City')
        away_team = self.gameday_data['gameData']['teams']['away']['name']
        away_team_city = self.gameday_data['gameData']['teams']['away'].get('locationName', 'City')
        home_team_city = self.gameday_data['gameData']['teams']['home'].get('locationName', 'City')
        away_team = self.gameday_data['gameData']['teams']['away']['name']
        add_line(self._get_radio_string('station_intro', {'network_name': network_name, 'away_team_city': away_team_city, 'away_team_name': away_team, 'home_team_city': home_team_city}))
        add_line(f"Tonight, from {venue}, it's the {self.home_team['name']} hosting the {self.away_team['name']}.")
        add_line(self._get_radio_string('welcome_intro'))


        weather = self.gameday_data['gameData'].get('weather')
        if weather:
             add_line(f"And it is a perfect night for a ball game: {weather}.")

        # STARTING LINEUPS
        if 'boxscore' in self.gameday_data['liveData']:
            boxscore = self.gameday_data['liveData']['boxscore']
            players_data = self.gameday_data['gameData'].get('players', {})
            lineup_strings = GAME_CONTEXT.get('lineup_strings', {})

            def get_position_str(pos_code, pos_name):
                # Try to clean up position names for radio
                if pos_code == '1': return "starting pitcher"
                if pos_code == '2': return "catcher"
                if pos_code == '3': return "first base"
                if pos_code == '4': return "second base"
                if pos_code == '5': return "third base"
                if pos_code == '6': return "shortstop"
                if pos_code == '7': return "left field"
                if pos_code == '8': return "center field"
                if pos_code == '9': return "right field"
                if pos_code == 'D': return "designated hitter"
                return pos_name.lower()

            def build_lineup(team_type):
                team_box = boxscore['teams'][team_type]
                batting_order = team_box.get('battingOrder', [])
                team_name = team_box['team']['name']

                if team_type == 'away':
                    intro_template = self.rng_color.choice(lineup_strings.get('intro_away', ["Let's take a look at the Starting 9 for the visiting {team_name}."]))
                    add_line(intro_template.format(team_name=team_name))
                else:
                    intro_template = self.rng_color.choice(lineup_strings.get('intro_home', ["Here are the {home_team_name}."]))
                    add_line(intro_template.format(away_team_name=self.away_team['name'], home_team_name=self.home_team['name']))

                for idx, p_id in enumerate(batting_order):
                    player_key = f"ID{p_id}"
                    if player_key in players_data:
                        player = players_data[player_key]
                        p_name = player.get('fullName', 'Unknown Player')
                        pos_info = player.get('primaryPosition', {})
                        pos_code = pos_info.get('code', '')
                        pos_name = pos_info.get('name', '')
                        pos_str = get_position_str(pos_code, pos_name)

                        # Fetch the starting pitcher hand if they are batting 9th (or any DH/Pitcher)
                        pitch_hand = player.get('pitchHand', {}).get('description', 'Right').lower()

                        context = {
                            'team_name': team_name,
                            'player_name': p_name,
                            'position': pos_str,
                            'pitch_hand': pitch_hand
                        }

                        # Get string for the specific batting position (1 through 9)
                        batting_pos = idx + 1
                        string_options = lineup_strings.get(f'batting_{batting_pos}', [f"Batting {batting_pos}, {p_name}."])

                        # Specific handling for the 9th spot starter vs position player
                        if batting_pos == 9:
                            if pos_code == '1':
                                string_options = [s for s in string_options if 'pitcher' in s]
                            else:
                                string_options = [s for s in string_options if 'pitcher' not in s]
                            if not string_options:
                                string_options = [f"And batting ninth, {pos_str} {p_name}."]

                        # Ensure valid template
                        if not string_options:
                            string_options = [f"Batting {batting_pos}, {p_name}."]

                        template = self.rng_color.choice(string_options)

                        # For lead-off and others, sometimes they are formatted "Name will lead off in position"
                        # Handle name at beginning
                        if template.startswith("{player_name}"):
                            line = template.format(**context)
                        else:
                            # Capitalize first letter of template
                            # (unless the template naturally handles it)
                            line = template.format(**context)
                            line = line[0].upper() + line[1:]

                        add_line(line)

                # Manager string
                if team_type == 'away':
                    manager_template = self.rng_color.choice(lineup_strings.get('manager_away', ["And the {team_name} are managed by veteran Skipper, Mick Jenkins."]))
                    add_line(manager_template.format(team_name=team_name))
                else:
                    manager_template = self.rng_color.choice(lineup_strings.get('manager_home', ["The {team_name} are managed by Manager Samuels."]))
                    add_line(manager_template.format(team_name=team_name))

            build_lineup('away')
            build_lineup('home')

        add_line("And we are underway.")

        lines.append("") # Empty line

        current_inning_state = (0, '')
        self.last_play_inning = None
        self.outs_tracker = 0
        self.runners_on_base = {'1B': None, '2B': None, '3B': None}
        self.current_score = (0, 0)
        self.plays_in_half_inning = []

        plays = self.gameday_data['liveData']['plays']['allPlays']

        for play in plays:
            about = play['about']
            matchup = play['matchup']
            inning = about['inning']
            half = "Top" if about['isTopInning'] else "Bottom"

            if 'startTime' in about:
                self._reseed_from_timestamp(about['startTime'], "play_start")

            if (inning, half) != current_inning_state:
                if current_inning_state[0] != 0:
                     is_123 = False
                     if len(self.plays_in_half_inning) == 3:
                         is_123 = True
                         for p in self.plays_in_half_inning:
                             for r in p['runners']:
                                 if not r['movement']['isOut'] and r['movement'].get('end') in ['1B', '2B', '3B', 'score']:
                                     is_123 = False
                                     break
                             if not is_123: break

                     prev_half = current_inning_state[1]
                     pitching_team = 'home' if prev_half == 'Top' else 'away'
                     pitcher_name = self.current_pitcher_info[pitching_team]['name'].split()[-1] if self.current_pitcher_info[pitching_team] else "The pitcher"

                     summary_lines = []
                     if is_123:
                         # 1-2-3 inning logic is part of game flow
                         template = self.rng_flow.choice(GAME_CONTEXT['narrative_strings']['inning_end_123'])
                         summary_lines.append(template.format(pitcher_name=pitcher_name))

                     score_away, score_home = self.current_score
                     completed_innings = inning - 1 if half == 'Top' else inning
                     ctx = {
                         'inning_ordinal': self._get_ordinal(completed_innings),
                         'inning_count_word': self._get_number_word(completed_innings),
                         'away_team_name': self.away_team['name'],
                         'home_team_name': self.home_team['name'],
                         'score_away': score_away,
                         'score_home': score_home,
                         'leading_team': self.away_team['name'] if score_away > score_home else self.home_team['name'],
                         'trailing_team': self.home_team['name'] if score_away > score_home else self.away_team['name'],
                         'score_lead': f"{max(score_away, score_home)}-{min(score_away, score_home)}",
                         'leading_score_val': max(score_away, score_home),
                         'score_trail': min(score_away, score_home),
                         'score': score_away
                     }

                     if score_away == score_home:
                         summary_lines.append(self._get_radio_string('inning_summary_tied', ctx))
                     elif half == 'Top' and inning > 1:
                         summary_lines.append(self._get_radio_string('inning_summary_score', ctx))
                     else:
                         summary_lines.append(self._get_radio_string('inning_summary_remains', ctx))

                     summary_lines.append(self._get_radio_string('inning_break_outro', {'next_inning_ordinal': self._get_ordinal(inning), 'network_name': network_name}))

                     summary_text = " ".join(summary_lines)
                     lines.append(summary_text)
                     self._add_to_buffer(summary_text)
                     lines.append("")

                     # Hardcoded 15s delay for inning break, placed between summary and welcome back
                     lines.append("[TTS SPLIT HERE DELAY:15.0s]")

                     if half == "Top":
                         add_line(f"Top of the {self._get_ordinal(inning)} inning here at {venue}.")
                     else:
                         add_line(self._get_radio_string('inning_break_intro', {'venue': venue, 'away_team_name': self.away_team['name'], 'home_team_name': self.home_team['name'], 'score_away': score_away, 'score_home': score_home, 'inning_half': half, 'inning_ordinal': self._get_ordinal(inning), 'network_name': network_name}))
                     lines.append("")

                else:
                    add_line(f"{half} of the {self._get_ordinal(inning)} inning.")
                    lines.append("")

                self.plays_in_half_inning = []
                self.runners_on_base = {'1B': None, '2B': None, '3B': None}

                if inning >= 10:
                     for r in play['runners']:
                         if r['movement']['start'] == '2B':
                             runner_name = r['details']['runner']['fullName']
                             self.runners_on_base['2B'] = runner_name
                             add_line(f"Automatic runner on second: {runner_name} jogs out to take his lead.")
                             break

                current_inning_state = (inning, half)
                self.outs_tracker = 0

            pitching_team_key = 'home' if about['isTopInning'] else 'away'
            pitcher_id = matchup['pitcher']['id']
            prev_info = self.current_pitcher_info[pitching_team_key]

            if prev_info and prev_info['id'] != pitcher_id:
                 team_name = self.home_team['name'] if about['isTopInning'] else self.away_team['name']
                 add_line(f"Pitching Change for {team_name}: {matchup['pitcher']['fullName']} replaces {prev_info['name']}.")
                 lines.append("")

            self.current_pitcher_info[pitching_team_key] = {'id': pitcher_id, 'name': matchup['pitcher']['fullName']}

            batter_name = matchup['batter']['fullName']
            play_text_blocks = []

            outs_str = f"{self.outs_tracker} out{'s' if self.outs_tracker != 1 else ''}"
            if self.outs_tracker == 1: outs_str = "one away"
            elif self.outs_tracker == 2: outs_str = "two down"
            else: outs_str = "nobody out"

            team_name = self.home_team['name'] if not about['isTopInning'] else self.away_team['name']

            bases_dict = self.runners_on_base
            runners = []
            if bases_dict.get('1B'): runners.append("first")
            if bases_dict.get('2B'): runners.append("second")
            if bases_dict.get('3B'): runners.append("third")

            intro_template = ""
            if len(runners) == 0:
                if self.outs_tracker == 0:
                     intro_template = self.rng_flow.choice(GAME_CONTEXT['narrative_strings']['batter_intro_leadoff'])
                else:
                     intro_template = self.rng_flow.choice(GAME_CONTEXT['narrative_strings']['batter_intro_empty'])

                # Fetch position from gameData players if available
                batter_pos = "batter"
                batter_id = f"ID{matchup['batter']['id']}"
                if 'players' in self.gameday_data['gameData'] and batter_id in self.gameday_data['gameData']['players']:
                    batter_pos = self.gameday_data['gameData']['players'][batter_id]['primaryPosition']['name']

                pitcher_name = self.current_pitcher_info[pitching_team_key]['name']
                intro_txt = intro_template.format(
                    batter_name=batter_name,
                    team_name=team_name,
                    outs_str=outs_str,
                    position=batter_pos.lower(),
                    pitcher_name=pitcher_name
                )
                play_text_blocks.append(intro_txt)
                self._add_to_buffer(intro_txt)
            else:
                 if len(runners) == 3:
                     base_desc = "the bases loaded"
                     runner_desc = "the bases loaded"
                 elif len(runners) == 2:
                     base_desc = f"{runners[0]} and {runners[1]}"
                     runner_desc = f"runners on {runners[0]} and {runners[1]}"
                 else:
                     base_desc = f"{runners[0]}"
                     runner_desc = f"a runner on {runners[0]}"

                 template = self.rng_flow.choice(GAME_CONTEXT['narrative_strings']['batter_intro_runners'])
                 val_to_use = runner_desc

                 if "Runner on {runners_str}" in template:
                     if len(runners) == 3:
                         template = template.replace("Runner on {runners_str}", "Bases loaded")
                     elif len(runners) == 2:
                         template = template.replace("Runner on", "Runners on")
                         val_to_use = base_desc
                     else:
                         val_to_use = base_desc

                 elif "runner on {runners_str}" in template:
                     if len(runners) == 3:
                         if "So a " in template:
                             template = template.replace("So a runner on {runners_str}", "So with the bases loaded")
                         else:
                             template = template.replace("runner on {runners_str}", "bases loaded")
                     elif len(runners) == 2:
                         if "So a " in template:
                             template = template.replace("So a runner on {runners_str}", "So runners on")
                             val_to_use = base_desc
                         else:
                             template = template.replace("runner on", "runners on")
                             val_to_use = base_desc
                     else:
                         val_to_use = base_desc

                 # If template starts with {runners_str}, ensure it's capitalized
                 if template.strip().startswith("{runners_str}"):
                     val_to_use = val_to_use[0].upper() + val_to_use[1:]
                 # If template puts runner desc after a period and space, capitalize it (e.g. "Batter steps in. a runner on...")
                 elif ". {runners_str}" in template:
                     val_to_use = val_to_use[0].upper() + val_to_use[1:]

                 pitcher_name = self.current_pitcher_info[pitching_team_key]['name']
                 intro_txt = template.format(
                     batter_name=batter_name,
                     runners_str=val_to_use,
                     outs_str=outs_str,
                     pitcher_name=pitcher_name
                 )
                 play_text_blocks.append(intro_txt)
                 self._add_to_buffer(intro_txt)

            if self.rng_color.random() < 0.2:
                 bat_side = matchup['batSide']['code']
                 pitch_hand = matchup['pitchHand']['code']
                 if bat_side == 'S': bat_side = 'R' if pitch_hand == 'L' else 'L'
                 matchup_txt = ""
                 if bat_side == 'R' and pitch_hand == 'R': matchup_txt = "Righty against righty."
                 elif bat_side == 'R' and pitch_hand == 'L': matchup_txt = "Righty against the lefty."
                 elif bat_side == 'L' and pitch_hand == 'R': matchup_txt = "Lefty against the righty."
                 elif bat_side == 'L' and pitch_hand == 'L': matchup_txt = "Lefty against the lefty."

                 if matchup_txt:
                     play_text_blocks.append(matchup_txt)
                     self._add_to_buffer(matchup_txt)

            result = play['result']
            outcome = result['event']
            play_events = play['playEvents']
            last_pitch_context = None
            i = 0
            x_event_connector = None

            is_inning_transition = False
            if (inning, half) != current_inning_state:
                 # Note: current_inning_state is updated earlier in the loop,
                 # but we can detect if we just printed inning start lines by checking logic flow.
                 # Actually, we update current_inning_state at the top.
                 # So we need a better way to flag if this is the first play of the inning.
                 pass

            # Since current_inning_state is updated at the top of the loop, check if play index is 0 in plays_in_half_inning
            # But plays_in_half_inning is cleared.
            # Let's check against self.plays_in_half_inning length BEFORE appending current play?
            # No, that's done at the end.

            # We can check if 'inning' or 'half' changed compared to PREVIOUS play.
            # But we only iterate plays.
            # We can use the fact that we just emitted "Top of the X inning..." lines.

            # Simplified: Use the buffer check or simply track if we did an inning reset this iteration.
            # We reset `self.plays_in_half_inning = []` inside the inning change block.
            # So if `len(self.plays_in_half_inning) == 0`, it's the first play of the half-inning.

            is_first_play_of_inning = (len(self.plays_in_half_inning) == 0)

            while i < len(play_events):
                event = play_events[i]

                if 'startTime' in event:
                    self._reseed_from_timestamp(event['startTime'], "event")

                # Timing check
                insert_idx = 0 if i == 0 else -1

                ctx = 'pitch'
                if i == 0:
                    if is_first_play_of_inning:
                        ctx = 'inning'
                    else:
                        ctx = 'batter'

                self._check_and_add_delay(event.get('endTime'), play_text_blocks, insert_at_index=insert_idx, context=ctx)

                details = event['details']
                desc = details['description']
                code = details.get('code', '')

                is_steal_attempt = False
                steal_event = None
                if i + 1 < len(play_events):
                    next_event = play_events[i+1]
                    if next_event['details'].get('eventType') in ['stolen_base', 'caught_stealing']:
                        is_steal_attempt = True
                        steal_event = next_event

                orig_pitch_type = details.get('type', {}).get('description', 'pitch')
                pitch_type = self._simplify_pitch_type(orig_pitch_type, capitalize=True)

                if self.verbose:
                    pbp_line = ""
                    pitching_team = 'home' if about['isTopInning'] else 'away'
                    current_pitcher_name = self.current_pitcher_info[pitching_team]['name']
                    runners_on = any(self.runners_on_base.values())
                    connector = self._get_pitch_connector(
                        event['count']['balls'],
                        event['count']['strikes'],
                        pitcher_name=current_pitcher_name,
                        batter_name=batter_name,
                        runners_on_base=runners_on
                    )

                    if code == 'X': x_event_connector = connector

                    if is_steal_attempt:
                        connector = f"{connector.rstrip('...')} {self.rng_play.choice(GAME_CONTEXT['narrative_strings']['runner_goes'])}"

                    if code == 'F':
                        if "Bunt" in desc:
                             # Handle repeated bunt fouls
                             options = GAME_CONTEXT['narrative_strings']['bunt_foul']
                             choice = self.rng_pitch.choice(options).strip().rstrip('.')
                             if last_pitch_context and (choice in last_pitch_context or last_pitch_context in choice):
                                 # Try to find a different one
                                 for _ in range(5):
                                     alt = self.rng_pitch.choice(options).strip().rstrip('.')
                                     if alt not in last_pitch_context and last_pitch_context not in alt:
                                         choice = alt
                                         break
                             pbp_line = choice
                        else:
                             pbp_line = self._get_foul_description()
                    elif code == 'C':
                         if event['count']['strikes'] == 2:
                             key = 'strike_called_three'
                             pbp_line = f"{pitch_type}, {self._get_narrative_string(key, rng=self.rng_pitch)}"
                         else:
                             # Use location-aware description if available
                             zone = details.get('zone')
                             desc = self._get_pitch_description_for_location('C', zone, pitch_type, matchup['batSide']['code'])
                             pbp_line = f"{pitch_type}, {desc}"

                    elif code == 'S':
                         if event['count']['strikes'] == 2:
                             key = 'strike_swinging_three'
                             pbp_line = f"{pitch_type}, {self._get_narrative_string(key, rng=self.rng_pitch)}"
                         else:
                             # For swinging strikes, we usually just say "Swing and a miss" but could describe location
                             # "Swing and a miss on a slider in the dirt"
                             key = 'strike_swinging'
                             pbp_line = f"{pitch_type}, {self._get_narrative_string(key, rng=self.rng_pitch)}"

                    elif code == 'B':
                         zone = details.get('zone')
                         desc = self._get_pitch_description_for_location('B', zone, pitch_type, matchup['batSide']['code'])
                         pbp_line = f"{pitch_type} {desc}"

                         if event['count']['balls'] == 2 and event['count']['strikes'] == 2:
                             pbp_line += self.rng_flow.choice(GAME_CONTEXT['narrative_strings']['count_full'])

                    if pbp_line:
                        # Flow Improvement: Use a comma instead of a period, but only if it's not an ellipsis or exclamation
                        # And possibly random variation.

                        use_comma = self.rng_flow.random() < 0.6
                        if use_comma:
                             pbp_line = f"{connector} {pbp_line},"
                        else:
                             pbp_line = f"{connector} {pbp_line}."

                        c = event['count']
                        b, s = c['balls'], c['strikes']
                        if code == 'B': b += 1
                        elif code in ['C', 'S', 'F']:
                            if not (code == 'F' and s == 2): s += 1

                        if b < 4 and s < 3:
                            spoken_count = self._get_spoken_count(b, s, connector="and")
                            # If we used a comma, make count lowercase if it starts with number text,
                            # but `spoken_count` is usually words.
                            # "And the 1-1... Slider outside, two and one."

                            suppress_count = False
                            if "strike one" in pbp_line.lower() and b == 0 and s == 1:
                                suppress_count = True

                            # Check for repeating 2-strike count
                            repeating_two_strikes = False
                            if code == 'F' and s == 2 and event['count']['strikes'] == 2:
                                repeating_two_strikes = True

                            if not suppress_count:
                                if repeating_two_strikes:
                                    # Use special "count holds at..." logic
                                    count_hold_str = self._get_narrative_string('count_remains_two_strikes', {'count_str': spoken_count}, rng=self.rng_flow)
                                    if use_comma:
                                        # pbp_line already ends in comma
                                        # "Fouled back, and we'll do it again."
                                        # strip leading comma from template if present (it is in my template definitions)
                                        count_hold_str = count_hold_str.lstrip(", ")
                                        pbp_line += f" {count_hold_str}."
                                    else:
                                        # pbp_line ends in period.
                                        # "Fouled back. And we'll do it again."
                                        # Need to handle the leading comma/connector in template or construct sentence.
                                        # My templates start with ", ". So replace ", " with "And " or similar if starting new sentence?
                                        # Or just append.
                                        # Let's adjust templates or logic.
                                        # Templates: ", and we'll do it again"
                                        # If period: "Fouled back. And we'll do it again." (Replace ", and" with "And")

                                        clean_hold_str = count_hold_str.strip(", ")
                                        # Capitalize first letter
                                        clean_hold_str = clean_hold_str[0].upper() + clean_hold_str[1:]
                                        pbp_line += f" {clean_hold_str}."

                                else:
                                    if use_comma:
                                         pbp_line += f" {spoken_count}."
                                    else:
                                         pbp_line += f" {spoken_count.capitalize()}."
                            elif use_comma:
                                 # If count suppressed but we used a comma, switch to period
                                 pbp_line = pbp_line.rstrip(',') + "."

                        is_final_event = (event == play_events[-1])
                        if is_final_event and outcome in ["Strikeout", "Walk"]:
                            last_pitch_context = pbp_line.rstrip(".,")
                            i += 1
                            continue

                        # Update last_pitch_context for the next iteration (important for de-duplication)
                        last_pitch_context = pbp_line.rstrip(".,")
                        play_text_blocks.append(pbp_line)
                        self._add_to_buffer(pbp_line)

                        if is_steal_attempt:
                            steal_txt = self._render_steal_event(steal_event)
                            play_text_blocks.append(steal_txt)
                            self._add_to_buffer(steal_txt)
                            if steal_event.get('endTime'):
                                 self.last_event_end_time = datetime.fromisoformat(steal_event['endTime'])
                                 self.pending_text_buffer = ""
                            i += 1
                else:
                    if code != 'X':
                         txt = f"{desc}."
                         play_text_blocks.append(txt)
                         self._add_to_buffer(txt)

                i += 1

            if 'endTime' in about:
                self._reseed_from_timestamp(about['endTime'], "play_outcome")

            outcome_text = ""
            if outcome == "Strikeout":
                k_type = "looking" if play_events[-1]['details']['code'] == 'C' else "swinging"

                result_outs = play['count']['outs']
                result_outs_word = "one"
                if result_outs == 2: result_outs_word = "two"
                elif result_outs == 3: result_outs_word = "three"

                out_context_str = f"for out number {result_outs_word}"
                if result_outs == 3:
                    out_context_str = "to end the inning"

                # Check for specific narrative templates based on context
                template_found = False
                if last_pitch_context and k_type == 'swinging':
                    last_pitch_lower = last_pitch_context.lower()
                    if "dirt" in last_pitch_lower:
                        # Try to find a dirt-specific template
                        dirt_templates = [
                            "He takes an awkward hack at a {pitch_type} in the dirt.",
                            "Chases a {pitch_type} in the dirt."
                        ]
                        if self.rng_play.random() < 0.7:
                            last_event = play_events[-1]
                            orig_p_type = last_event['details'].get('type', {}).get('description', 'pitch')
                            simple_p_type = self._simplify_pitch_type(orig_p_type)
                            outcome_text = self.rng_play.choice(dirt_templates).format(pitch_type=simple_p_type, batter_name=batter_name)
                            template_found = True

                if not template_found:
                    if last_pitch_context:
                         # Flow Improvement: Check for phrases that already imply the out ("rings him up")
                         last_pitch_lower = last_pitch_context.lower()
                         complete_out_phrases = ["rings him up", "fans him", "struck him out", "gets him swinging", "got him looking", "caught looking"]

                         is_complete = any(phrase in last_pitch_lower for phrase in complete_out_phrases)

                         if is_complete:
                             # "Slider, rings him up! Evan Reed goes down for out number two."
                             outcome_text = f"{last_pitch_context}! {batter_name} goes down {out_context_str}."
                         else:
                             # Standard flow: "Slider, called strike three, and Evan Reed strikes out to end the inning."
                             if k_type == 'swinging':
                                 simple_verb = self.rng_play.choice(["strikes out", "is set down swinging", "goes down swinging", "is down on strikes"])
                                 outcome_text = f"{last_pitch_context}, and {batter_name} {simple_verb} {out_context_str}."
                             else:
                                 simple_verb = self.rng_play.choice(["strikes out looking", "is down on strikes", "goes down looking", "is rung up"])
                                 outcome_text = f"{last_pitch_context}, and {batter_name} {simple_verb} {out_context_str}."
                    else:
                        verb = self.rng_play.choice(GAME_CONTEXT['statcast_verbs']['Strikeout'][k_type])
                        outcome_text = f"{batter_name} {verb} {out_context_str}."

            elif outcome == "Walk":
                 is_leadoff_batter = (len(self.plays_in_half_inning) == 0)
                 w_out = "leadoff" if (self.outs_tracker == 0 and is_leadoff_batter) else "no-out"
                 if self.outs_tracker == 1: w_out = "one-out"
                 elif self.outs_tracker == 2: w_out = "two-out"

                 walk_context = {
                     'last_pitch_context': last_pitch_context,
                     'batter_name': batter_name,
                     'outs_str': w_out
                 }

                 templates = GAME_CONTEXT['narrative_templates'].get('Walk', {}).get('default', [])
                 if not templates: templates = ["{batter_name} draws a walk."]

                 valid_templates = [t for t in templates if not ("{last_pitch_context}" in t and not last_pitch_context)]
                 if not valid_templates: valid_templates = ["{batter_name} draws a walk."]

                 outcome_text = self.rng_play.choice(valid_templates).format(**walk_context)

            elif outcome in ["HBP", "Hit By Pitch"]:
                templates = GAME_CONTEXT['narrative_templates'].get('Hit By Pitch', {}).get('default', [])
                if not templates: templates = ["{batter_name} is hit by the pitch."]
                outcome_text = self.rng_play.choice(templates).format(batter_name=batter_name)

            elif outcome == "Strikeout Double Play":
                outcome_text = f"{batter_name} strikes out on a pitch in the dirt, but the runner is gunned down! A strikeout double play."

            elif outcome == "Caught Stealing":
                 runner_out = next((r for r in play['runners'] if r['movement']['isOut']), None)
                 if runner_out:
                     ob = runner_out['movement']['outBase']
                     base_name = "second" if ob == "2B" else "third" if ob == "3B" else "home"
                     outcome_text = f"{runner_out['details']['runner']['fullName']} is caught stealing {base_name}!"

            elif outcome == "Field Error":
                 err_credit = None
                 for r in play['runners']:
                     for c in r.get('credits', []):
                         if c['credit'] == 'fielding_error':
                             err_credit = c
                             break
                     if err_credit: break

                 if err_credit:
                     pos = err_credit['position']['abbreviation']
                     name = err_credit['player']['fullName']
                     outcome_text = f"An error by {pos} {name} allows the batter to reach base."
                 else:
                     outcome_text = "The batter reaches on a fielding error."
            else:
                x_event = next((e for e in play_events if e['details'].get('code') == 'X'), None)
                if x_event:
                    hit_data = x_event.get('hitData', {})
                    pitch_details = {'type': x_event['details'].get('type', {}).get('description', 'pitch'), 'velo': x_event.get('pitchData', {}).get('startSpeed')}

                    fielder_pos = None
                    fielder_name = None
                    out_credits = []
                    for r in play['runners']:
                        if r['movement']['isOut']:
                            out_credits = r.get('credits', [])
                            break
                    if not out_credits:
                        for r in play['runners']:
                             if r.get('credits'):
                                 out_credits = r.get('credits')
                                 break

                    primary_credit = None
                    for c in out_credits:
                        if c['credit'] == 'assist': primary_credit = c; break
                    if not primary_credit:
                        for c in out_credits:
                             if c['credit'] == 'putout': primary_credit = c; break

                    if primary_credit:
                        fielder_pos = primary_credit['position']['abbreviation']
                        fielder_name = primary_credit['player']['fullName'].split()[-1]

                    ordinal = self._get_ordinal(inning)
                    inning_context = f" here in the {half.lower()} of the {ordinal}"
                    is_leadoff = (len(self.plays_in_half_inning) == 0)

                    outcome_text = self._generate_play_description(outcome, hit_data, pitch_details, batter_name, fielder_pos, fielder_name, connector=x_event_connector, result_outs=play['count']['outs'], is_leadoff=is_leadoff, inning_context=inning_context)

            if outcome_text:
                 play_text_blocks.append(outcome_text)
                 self._add_to_buffer(outcome_text)

            new_away = result['awayScore']
            new_home = result['homeScore']
            old_away, old_home = self.current_score

            if new_away != old_away or new_home != old_home:
                lead_team = self.away_team['name'] if new_away > new_home else self.home_team['name']
                score_lead_str = self._get_spoken_score_string(new_away, new_home)

                score_tied_str = "0"
                if new_away == new_home:
                     nums = ["nothing", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
                     if new_away < len(nums) and new_away > 0: score_tied_str = nums[new_away]
                     else: score_tied_str = str(new_away)

                ctx = {
                    'team_name': lead_team,
                    'score_lead': score_lead_str,
                    'score': score_tied_str,
                    'inning': self._get_ordinal(inning),
                    'half': half.lower()
                }

                score_lines = []
                if new_away == new_home:
                    score_lines.append(self._get_radio_string('score_update_tied', ctx))
                else:
                    old_lead_team = self.away_team['name'] if old_away > old_home else self.home_team['name']
                    if old_away != old_home and old_lead_team == lead_team:
                         score_lines.append(self._get_radio_string('score_update_extend', ctx))
                    else:
                         score_lines.append(self._get_radio_string('score_update_lead', ctx))

                score_update_text = " ".join(score_lines)
                self._add_to_buffer(score_update_text)

                if play_text_blocks:
                    last_block = play_text_blocks[-1]
                    if last_block.endswith('...'):
                        play_text_blocks[-1] = last_block.rstrip('.') + ", " + score_update_text + "."
                    elif last_block.endswith('.'):
                        play_text_blocks[-1] = last_block[:-1] + ", " + score_update_text + "."
                    elif last_block.endswith('!'):
                        play_text_blocks[-1] = last_block + " " + score_update_text[0].upper() + score_update_text[1:] + "."
                    else:
                        play_text_blocks[-1] = last_block + " " + score_update_text + "."
                else:
                    play_text_blocks.append(score_update_text[0].upper() + score_update_text[1:] + ".")

            self.current_score = (new_away, new_home)
            self.outs_tracker = play['count']['outs']

            post_bases = { '1B': None, '2B': None, '3B': None }
            if 'postOnFirst' in matchup: post_bases['1B'] = matchup['postOnFirst']['fullName']
            if 'postOnSecond' in matchup: post_bases['2B'] = matchup['postOnSecond']['fullName']
            if 'postOnThird' in matchup: post_bases['3B'] = matchup['postOnThird']['fullName']
            self.runners_on_base = post_bases

            self.plays_in_half_inning.append(play)

            lines.append("\n".join(play_text_blocks))
            lines.append("")

        # --- GAME SUMMARY ---
        linescore_teams = self.gameday_data['liveData']['linescore']['teams']
        home_runs = linescore_teams['home']['runs']
        home_hits = linescore_teams['home']['hits']
        home_errors = linescore_teams['home']['errors']
        away_runs = linescore_teams['away']['runs']
        away_hits = linescore_teams['away']['hits']
        away_errors = linescore_teams['away']['errors']

        if home_runs > away_runs:
             win_team = self.home_team['name']
             win_runs = home_runs
             win_hits = home_hits
             win_errors = home_errors
             lose_team = self.away_team['name']
             lose_runs = away_runs
             lose_hits = away_hits
             lose_errors = away_errors
        else:
             win_team = self.away_team['name']
             win_runs = away_runs
             win_hits = away_hits
             win_errors = away_errors
             lose_team = self.home_team['name']
             lose_runs = home_runs
             lose_hits = home_hits
             lose_errors = home_errors

        summary_lines = []
        ctx = {
            'win_team': win_team, 'win_runs': win_runs, 'win_hits': win_hits, 'win_errors': win_errors,
            'lose_team': lose_team, 'lose_runs': lose_runs, 'lose_hits': lose_hits, 'lose_errors': lose_errors,
            'network_name': GAME_CONTEXT.get('network_name', 'The Pacific Coast Baseball Network')
        }
        summary_text = self._get_radio_string('game_summary', ctx)


        outro_text = self._get_radio_string('outro', ctx)




        if summary_text:
             lines.append(summary_text)
        if outro_text:
             lines.append(outro_text)


        lines.append("")

        lines.append("=" * 20 + " GAME OVER " + "=" * 20)
        final_home = self.gameday_data['liveData']['linescore']['teams']['home']['runs']
        final_away = self.gameday_data['liveData']['linescore']['teams']['away']['runs']
        lines.append(f"Final Score: {self.home_team['name']} {final_home} - {self.away_team['name']} {final_away}")
        winner = self.home_team['name'] if final_home > final_away else self.away_team['name']
        lines.append(f"{winner} win!")

        return "\n".join(lines)
