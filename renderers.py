import random
from commentary import GAME_CONTEXT
from gameday import GamedayData

class GameRenderer:
    def __init__(self, gameday_data: GamedayData, seed: int = None):
        self.gameday_data = gameday_data

        # Master RNG to generate sub-seeds for stability
        master_rng = random.Random(seed)

        # Separate RNGs for different categories of commentary
        # rng_play: Batted ball descriptions, hit locations, specific play outcomes
        self.rng_play = random.Random(master_rng.randint(0, 1_000_000_000))

        # rng_pitch: Pitch types, ball/strike descriptions, foul ball descriptions
        self.rng_pitch = random.Random(master_rng.randint(0, 1_000_000_000))

        # rng_flow: Connectors ("And the 1-1..."), inning transitions, batter intros
        self.rng_flow = random.Random(master_rng.randint(0, 1_000_000_000))

        # rng_color: Station IDs, weather comments, handedness comments, color commentary
        self.rng_color = random.Random(master_rng.randint(0, 1_000_000_000))

        # Fallback/Default
        self.rng = self.rng_play

        self.home_team = gameday_data['gameData']['teams']['home']
        self.away_team = gameday_data['gameData']['teams']['away']
        self.current_pitcher_info = {'home': None, 'away': None}

    def render(self) -> str:
        raise NotImplementedError

    def _get_batted_ball_category(self, outcome, ev, la):
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
        return cat

    def _get_batted_ball_verb(self, outcome, cat, force_type=None):
        outcome_data = GAME_CONTEXT['statcast_verbs'].get(outcome, {})

        if force_type:
            phrase_type = force_type
        else:
            use_verb = self.rng_play.random() < 0.6
            phrase_type = 'verbs' if use_verb else 'nouns'

        phrases = outcome_data.get(phrase_type, outcome_data.get('verbs', {}))
        phrase_list = phrases.get(cat, phrases.get('default', ["describes"]))
        # Fallback if specific category empty
        if not phrase_list:
             phrase_list = phrases.get('default', ["describes"])

        phrase = self.rng_play.choice(phrase_list)
        return phrase, phrase_type

    def _get_hit_location(self, hit_type, ev, la, location_code=None):
        if location_code:
            return GAME_CONTEXT['hit_directions'].get(location_code, "fair")

        if la is None or ev is None: return "fair"
        if hit_type in ["Single", "Double"]:
            if -10 < la < 10: return self.rng_play.choice(["up the middle", "through the right side", "through the left side"])
            elif 10 < la < 25: return self.rng_play.choice(["to left field", "to center field", "to right field"])
            else: return self.rng_play.choice(["into shallow left", "into shallow center", "into shallow right"])
        elif hit_type == "Triple":
            return self.rng_play.choice(["into the right-center gap", "into the left-center gap"])
        elif hit_type == "Home Run":
            if abs(la - 28) < 5 and ev > 105: return "down the line"
            return self.rng_play.choice(["to deep left field", "to deep center field", "to deep right field"])
        return "fair"

    def _format_statcast_template(self, outcome, context):
        templates = GAME_CONTEXT.get('statcast_templates', {}).get(outcome)
        if not templates: return None
        template = self.rng_play.choice(templates)
        if '{verb_capitalized}' in template:
            context['verb_capitalized'] = context.get('verb', '').capitalize()
        return template.format(**context)


class NarrativeRenderer(GameRenderer):
    def __init__(self, gameday_data: GamedayData, seed: int = None, verbose: bool = True, use_bracketed_ui: bool = False):
        super().__init__(gameday_data, seed)
        self.verbose = verbose
        # use_bracketed_ui is ignored in new format as we don't print status lines

    def _get_ordinal(self, n):
        words = ["", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth"]
        if 1 <= n <= 9: return words[n]

        ordinals = ["th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th"]
        if 11 <= (n % 100) <= 13: suffix = "th"
        else: suffix = ordinals[n % 10]
        return f"{n}{suffix}"

    def _get_narrative_string(self, key, context=None, rng=None):
        if context is None: context = {}
        # Default to rng_play if not specified, as most narrative strings are play-related
        selected_rng = rng if rng else self.rng_play
        return selected_rng.choice(GAME_CONTEXT['narrative_strings'].get(key, [""])).format(**context)

    def _get_radio_string(self, key, context=None):
        if context is None: context = {}
        return self.rng_color.choice(GAME_CONTEXT['radio_strings'].get(key, [""])).format(**context)

    def _get_spoken_count(self, balls, strikes, connector="and"):
        nums = ["oh", "one", "two", "three", "four"]
        b_word = nums[balls] if balls < len(nums) else str(balls)
        s_word = nums[strikes] if strikes < len(nums) else str(strikes)

        if connector == "-":
            return f"{b_word}-{s_word}"
        return f"{b_word} {connector} {s_word}"

    def _get_pitch_connector(self, balls, strikes, pitcher_name=None, runners_on_base=False):
        if balls == 3 and strikes == 2:
            return self.rng_flow.choice(GAME_CONTEXT['narrative_strings']['payoff_pitch'])

        count_str = self._get_spoken_count(balls, strikes, connector="-")
        pitcher_last = pitcher_name.split()[-1] if pitcher_name else "The pitcher"

        if balls == 0 and strikes == 0:
            if runners_on_base and self.rng_flow.random() < 0.4:
                 return self.rng_flow.choice(GAME_CONTEXT['narrative_strings'].get('pitch_connectors_stretch', ["And the pitch..."])).format(pitcher_name_last=pitcher_last, count_str=count_str)
            return self.rng_flow.choice(["And the pitch...", "And the pitch..."])

        context = {
            'count_str': count_str,
            'count_str_cap': count_str.capitalize(),
            'pitcher_name_last': pitcher_last
        }

        templates = GAME_CONTEXT['narrative_strings'].get('pitch_connectors', [
            "And the {count_str}...",
            "The {count_str} pitch...",
            "And the {count_str} pitch..."
        ])

        return self.rng_flow.choice(templates).format(**context)

    def _simplify_pitch_type(self, pitch_type: str, capitalize=False) -> str:
        simplified = pitch_type
        if pitch_type.lower() == "four-seam fastball":
            r = self.rng_pitch.random()
            if r < 0.6: simplified = "fastball"
            elif r < 0.7: simplified = "heater"

        if capitalize:
            return simplified.capitalize()
        return simplified

    def _get_spoken_score_string(self, score_a, score_b):
        nums = ["nothing", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]

        def to_word(n):
            if 0 <= n < len(nums): return nums[n]
            return str(n)

        if score_a > score_b:
            lead, trail = score_a, score_b
        else:
            lead, trail = score_b, score_a

        lead_str = to_word(lead)
        trail_str = to_word(trail)

        use_digits = (lead > 2 or trail > 2)
        if use_digits:
            return f"{lead}-to-{trail}"

        if trail == 0:
            return f"{lead_str}-nothing"

        return f"{lead_str}-to-{trail_str}"

    def _get_runner_status_string(self, outcome, batter_name, result_outs, is_leadoff, inning_context):
        key = None
        outcome_lower = outcome.lower()

        if is_leadoff:
             key = f"leadoff_{outcome_lower}"
        elif result_outs == 0:
             key = f"{outcome_lower}_nobody_out"
        elif result_outs == 1:
             key = f"{outcome_lower}_one_out"
        elif result_outs == 2:
             key = f"two_out_{outcome_lower}"

        if not key:
            return ""

        context = {
            'batter_name': batter_name,
            'inning_context': inning_context
        }

        # Use rng_play for status strings
        return self._get_narrative_string(key, context, rng=self.rng_play)


    def _generate_play_description(self, outcome, hit_data, pitch_details, batter_name, fielder_pos=None, fielder_name=None, connector=None, result_outs=None, is_leadoff=False, inning_context=""):
        ev = hit_data.get('launchSpeed')
        la = hit_data.get('launchAngle')
        location_code = hit_data.get('location')

        cat = self._get_batted_ball_category(outcome, ev, la)

        specific_templates = []
        if 'narrative_templates' in GAME_CONTEXT:
            outcome_templates = GAME_CONTEXT['narrative_templates'].get(outcome, {})
            specific_templates = outcome_templates.get(cat, [])
            if not specific_templates:
                specific_templates = outcome_templates.get('default', [])

        template = None
        if specific_templates and self.rng_play.random() < 0.8:
            template = self.rng_play.choice(specific_templates)

        direction = ""
        if location_code:
            direction = self._get_hit_location(outcome, ev, la, location_code)
        elif outcome in ["Single", "Double", "Triple", "Home Run"]:
            direction = self._get_hit_location(outcome, ev, la)
        elif fielder_pos:
            direction = GAME_CONTEXT['hit_directions'].get(fielder_pos, "")

        direction_noun = direction
        if direction == "up the middle":
            direction_noun = "center field"
        elif direction == "through the right side":
            direction_noun = "right field"
        elif direction == "through the left side":
            direction_noun = "left field"
        elif direction == "fair":
            direction_noun = "the outfield"
        elif direction.startswith("to "):
            direction_noun = direction[3:]
        elif direction.startswith("into shallow "):
             direction_noun = direction[13:]
        elif direction.startswith("into "):
             direction_noun = direction[5:]

        orig_pitch_type = pitch_details.get('type', 'pitch')
        simple_pitch_type = self._simplify_pitch_type(orig_pitch_type)

        result_outs_word = "one"
        if result_outs == 2: result_outs_word = "two"
        elif result_outs == 3: result_outs_word = "three"

        out_context_str = f"for out number {result_outs_word}"
        if result_outs == 3:
            out_context_str = "to end the inning"

        context = {
            'batter_name': batter_name,
            'direction': direction,
            'direction_noun': direction_noun,
            'pitch_type': simple_pitch_type,
            'pitch_type_lower': simple_pitch_type.lower(),
            'pitch_velo': pitch_details.get('velo', 'N/A'),
            'fielder_name': fielder_name or "the fielder",
            'result_outs': result_outs,
            'result_outs_word': result_outs_word,
            'out_context_str': out_context_str
        }

        prefix = f"{connector} " if connector else ""
        force_narrative = outcome in ["Groundout", "Flyout", "Pop Out", "Lineout"]

        final_description = ""
        if template or (specific_templates and (force_narrative or self.rng_play.random() < 0.8)):
             if not template: template = self.rng_play.choice(specific_templates)
             final_description = prefix + template.format(**context)
        else:
            phrase, phrase_type = self._get_batted_ball_verb(outcome, cat)
            if connector:
                if phrase_type == 'verbs':
                    template = self.rng_play.choice(GAME_CONTEXT['narrative_strings']['play_by_play_templates'])
                    context['verb'] = phrase
                    context['verb_capitalized'] = phrase.capitalize()
                else:
                    template = self.rng_play.choice(GAME_CONTEXT['narrative_strings']['play_by_play_noun_templates'])
                    context['noun'] = phrase
                    context['noun_capitalized'] = phrase.capitalize()
            else:
                if phrase_type == 'verbs':
                    template = self.rng_play.choice(GAME_CONTEXT['narrative_strings']['play_by_play_templates'])
                    context['verb'] = phrase
                    context['verb_capitalized'] = phrase.capitalize()
                else:
                    template = self.rng_play.choice(GAME_CONTEXT['narrative_strings']['play_by_play_noun_templates'])
                    context['noun'] = phrase
                    context['noun_capitalized'] = phrase.capitalize()
            final_description = prefix + template.format(**context)

        if outcome in ["Single", "Double", "Triple"]:
             status_str = self._get_runner_status_string(outcome, batter_name, result_outs, is_leadoff, inning_context)
             if status_str:
                 final_description += " " + status_str

        return final_description

    def _render_steal_event(self, event):
        details = event['details']
        outcome = details['eventType']
        desc = details['description']

        base_target = "second"
        base_key = "2B"
        prev_base = "1B"
        if "3B" in desc:
            base_target = "third"
            base_key = "3B"
            prev_base = "2B"
        elif "2B" in desc:
            pass
        elif "Home" in desc:
            base_target = "home"
            base_key = "score"
            prev_base = "3B"

        runner_name = self.runners_on_base.get(prev_base)
        if not runner_name:
             runner_name = "The runner"

        if outcome == 'stolen_base':
            self.runners_on_base[base_key] = runner_name
            self.runners_on_base[prev_base] = None
            throw_desc = self.rng_play.choice(GAME_CONTEXT['narrative_strings']['throw_outcome_safe']).format(base=base_target)
            return f"{throw_desc} {runner_name} steals {base_target}."

        elif outcome == 'caught_stealing':
            self.runners_on_base[prev_base] = None
            throw_desc = self.rng_play.choice(GAME_CONTEXT['narrative_strings']['throw_outcome_out']).format(base=base_target)
            return f"{throw_desc} {runner_name} is caught stealing {base_target}."

        return f"{desc}."

    def render(self) -> str:
        lines = []

        venue = self.gameday_data['gameData'].get('venue', 'the ballpark')
        lines.append(self._get_radio_string('station_intro'))
        lines.append(f"Tonight, from {venue}, it's the {self.home_team['name']} hosting the {self.away_team['name']}.")
        lines.append(self._get_radio_string('welcome_intro'))

        weather = self.gameday_data['gameData'].get('weather')
        if weather:
             lines.append(f"And it is a perfect night for a ball game: {weather}.")

        lines.append("And we are underway.")
        lines.append("")

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
                     ctx = {
                         'inning_ordinal': self._get_ordinal(inning - 1) if half == 'Top' else self._get_ordinal(inning),
                         'away_team_name': self.away_team['name'],
                         'home_team_name': self.home_team['name'],
                         'score_away': score_away,
                         'score_home': score_home,
                         'leading_team': self.away_team['name'] if score_away > score_home else self.home_team['name'],
                         'trailing_team': self.home_team['name'] if score_away > score_home else self.away_team['name'],
                         'score_lead': f"{max(score_away, score_home)}-{min(score_away, score_home)}",
                         'score_trail': min(score_away, score_home),
                         'score': score_away
                     }

                     if score_away == score_home:
                         summary_lines.append(self._get_radio_string('inning_summary_tied', ctx))
                     elif half == 'Top' and inning > 1:
                         summary_lines.append(self._get_radio_string('inning_summary_score', ctx))
                     else:
                         summary_lines.append(self._get_radio_string('inning_summary_remains', ctx))

                     summary_lines.append(self._get_radio_string('inning_break_outro', {'next_inning_ordinal': self._get_ordinal(inning)}))

                     lines.append(" ".join(summary_lines))
                     lines.append("")

                     if half == "Top":
                         lines.append(f"Top of the {self._get_ordinal(inning)} inning here at {venue}.")
                     else:
                         lines.append(self._get_radio_string('inning_break_intro', {'venue': venue, 'away_team_name': self.away_team['name'], 'home_team_name': self.home_team['name'], 'score_away': score_away, 'score_home': score_home, 'inning_half': half, 'inning_ordinal': self._get_ordinal(inning)}))
                     lines.append("")

                else:
                    lines.append(f"{half} of the {self._get_ordinal(inning)} inning.")
                    lines.append("")

                self.plays_in_half_inning = []
                self.runners_on_base = {'1B': None, '2B': None, '3B': None}

                if inning >= 10:
                     for r in play['runners']:
                         if r['movement']['start'] == '2B':
                             runner_name = r['details']['runner']['fullName']
                             self.runners_on_base['2B'] = runner_name
                             lines.append(f"Automatic runner on second: {runner_name} jogs out to take his lead.")
                             break

                current_inning_state = (inning, half)
                self.outs_tracker = 0

            pitching_team_key = 'home' if about['isTopInning'] else 'away'
            pitcher_id = matchup['pitcher']['id']
            prev_info = self.current_pitcher_info[pitching_team_key]

            if prev_info and prev_info['id'] != pitcher_id:
                 team_name = self.home_team['name'] if about['isTopInning'] else self.away_team['name']
                 lines.append(f"Pitching Change for {team_name}: {matchup['pitcher']['fullName']} replaces {prev_info['name']}.")
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

                play_text_blocks.append(intro_template.format(
                    batter_name=batter_name,
                    team_name=team_name,
                    outs_str=outs_str,
                    position=batter_pos.lower(),
                    pitcher_name=self.current_pitcher_info[pitching_team_key]['name']
                ))
            else:
                 if len(runners) == 3:
                     base_desc = "the bases loaded"
                     runner_desc = "the bases loaded"
                 elif len(runners) == 2:
                     base_desc = f"{runners[0]} and {runners[1]}"
                     runner_desc = f"runners on {runners[0]} and {runners[1]}"
                 else:
                     base_desc = f"{runners[0]}"
                     runner_desc = f"runner on {runners[0]}"

                 template = self.rng_flow.choice(GAME_CONTEXT['narrative_strings']['batter_intro_runners'])
                 val_to_use = runner_desc
                 if "Runner on {runners_str}" in template: val_to_use = base_desc
                 play_text_blocks.append(template.format(batter_name=batter_name, runners_str=val_to_use, outs_str=outs_str))

            if self.rng_color.random() < 0.2:
                 bat_side = matchup['batSide']['code']
                 pitch_hand = matchup['pitchHand']['code']
                 if bat_side == 'S': bat_side = 'R' if pitch_hand == 'L' else 'L'
                 if bat_side == 'R' and pitch_hand == 'R': play_text_blocks.append("Righty against righty.")
                 elif bat_side == 'R' and pitch_hand == 'L': play_text_blocks.append("Righty against the lefty.")
                 elif bat_side == 'L' and pitch_hand == 'R': play_text_blocks.append("Lefty against the righty.")
                 elif bat_side == 'L' and pitch_hand == 'L': play_text_blocks.append("Lefty against the lefty.")

            result = play['result']
            outcome = result['event']
            play_events = play['playEvents']
            last_pitch_context = None
            i = 0
            x_event_connector = None

            while i < len(play_events):
                event = play_events[i]
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
                        runners_on_base=runners_on
                    )

                    if code == 'X': x_event_connector = connector

                    if is_steal_attempt:
                        connector = f"{connector.rstrip('...')} {self.rng_play.choice(GAME_CONTEXT['narrative_strings']['runner_goes'])}"

                    if code == 'F':
                        if "Bunt" in desc:
                             pbp_line = self.rng_pitch.choice(GAME_CONTEXT['narrative_strings']['bunt_foul']).strip().rstrip('.')
                        else:
                             phrase = self.rng_pitch.choice(GAME_CONTEXT['pitch_locations']['foul'])
                             if any(x in phrase.lower() for x in ["foul", "spoils", "fights"]): pbp_line = f"{phrase}"
                             elif "jams" in phrase.lower(): pbp_line = f"Foul, {phrase}"
                             else: pbp_line = f"Foul, {phrase}"
                    elif code == 'C':
                         key = 'strike_called_three' if event['count']['strikes'] == 2 else 'strike_called'
                         pbp_line = f"{pitch_type}, {self._get_narrative_string(key, rng=self.rng_pitch)}"
                    elif code == 'S':
                         key = 'strike_swinging_three' if event['count']['strikes'] == 2 else 'strike_swinging'
                         pbp_line = f"{pitch_type}, {self._get_narrative_string(key, rng=self.rng_pitch)}"
                    elif code == 'B':
                         pbp_line = f"{pitch_type} {self.rng_pitch.choice(GAME_CONTEXT['pitch_locations']['ball'])}"
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

                            if not suppress_count:
                                if use_comma:
                                     pbp_line += f" {spoken_count}."
                                else:
                                     pbp_line += f" {spoken_count.capitalize()}."
                            elif use_comma:
                                 # If count suppressed but we used a comma, switch to period
                                 pbp_line = pbp_line.rstrip(',') + "."

                        is_final_event = (event == play_events[-1])
                        if is_final_event and outcome in ["Strikeout", "Walk"]:
                            last_pitch_context = pbp_line.rstrip(".")
                            i += 1
                            continue

                        play_text_blocks.append(pbp_line)

                        if is_steal_attempt:
                            play_text_blocks.append(self._render_steal_event(steal_event))
                            i += 1
                else:
                    if code != 'X': play_text_blocks.append(f"{desc}.")

                i += 1

            outcome_text = ""
            if outcome == "Strikeout":
                k_type = "looking" if play_events[-1]['details']['code'] == 'C' else "swinging"
                if last_pitch_context:
                     # Flow Improvement: Check redundancy
                     last_pitch_lower = last_pitch_context.lower()
                     redundant_verbs = ["strikes out", "fans him", "strike three", "caught looking", "rung up"]

                     already_described = any(phrase in last_pitch_lower for phrase in redundant_verbs)

                     if already_described:
                         # Minimal addition
                         outcome_text = f"{last_pitch_context}, and {batter_name} is out."
                     else:
                         if k_type == 'swinging':
                             simple_verb = self.rng_play.choice(["strikes out", "is set down swinging", "goes down swinging", "is out"])
                             outcome_text = f"{last_pitch_context}, and {batter_name} {simple_verb}."
                         else:
                             simple_verb = self.rng_play.choice(["strikes out looking", "is caught looking", "is rung up", "is out looking"])
                             outcome_text = f"{last_pitch_context}, and {batter_name} {simple_verb}."
                else:
                    verb = self.rng_play.choice(GAME_CONTEXT['statcast_verbs']['Strikeout'][k_type])
                    outcome_text = f"{batter_name} {verb}."

            elif outcome == "Walk":
                 if last_pitch_context:
                     outcome_text = f"{last_pitch_context}, and {batter_name} draws a walk."
                 else:
                     outcome_text = f"{batter_name} draws a walk."

            elif outcome in ["HBP", "Hit By Pitch"]:
                outcome_text = f"{batter_name} is hit by the pitch."

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

            if outcome_text: play_text_blocks.append(outcome_text)

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

        lines.append("=" * 20 + " GAME OVER " + "=" * 20)
        final_home = self.gameday_data['liveData']['linescore']['teams']['home']['runs']
        final_away = self.gameday_data['liveData']['linescore']['teams']['away']['runs']
        lines.append(f"Final Score: {self.home_team['name']} {final_home} - {self.away_team['name']} {final_away}")
        winner = self.home_team['name'] if final_home > final_away else self.away_team['name']
        lines.append(f"{winner} win!")

        return "\n".join(lines)


class StatcastRenderer(GameRenderer):
    def render(self) -> str:
        lines = []

        lines.append("=" * 20 + " GAME START " + "=" * 20)
        lines.append(f"{self.away_team['name']} vs. {self.home_team['name']}")
        if 'venue' in self.gameday_data['gameData']: lines.append(f"Venue: {self.gameday_data['gameData']['venue']}")
        if 'weather' in self.gameday_data['gameData']: lines.append(f"Weather: {self.gameday_data['gameData']['weather']}")
        if 'umpires' in self.gameday_data['gameData']:
            u = self.gameday_data['gameData']['umpires']
            lines.append(f"Umpires: HP: {u[0]}, 1B: {u[1]}, 2B: {u[2]}, 3B: {u[3]}")
        lines.append("-" * 50)

        current_inning_state = (0, '')

        plays = self.gameday_data['liveData']['plays']['allPlays']

        for play in plays:
            about = play['about']
            inning = about['inning']
            half = "Top" if about['isTopInning'] else "Bottom"

            if (inning, half) != current_inning_state:
                team_name = self.away_team['name'] if about['isTopInning'] else self.home_team['name']
                lines.append("-" * 50)
                lines.append(f"{half} of Inning {inning} | {team_name} batting")
                current_inning_state = (inning, half)

            pitching_team_key = 'home' if about['isTopInning'] else 'away'
            pitcher_id = play['matchup']['pitcher']['id']
            prev_info = self.current_pitcher_info[pitching_team_key]
            if prev_info and prev_info['id'] != pitcher_id:
                 team_name = self.home_team['name'] if about['isTopInning'] else self.away_team['name']
                 lines.append(f"\n--- Pitching Change for {team_name}: {play['matchup']['pitcher']['fullName']} replaces {prev_info['name']} ---\n")
            self.current_pitcher_info[pitching_team_key] = {'id': pitcher_id, 'name': play['matchup']['pitcher']['fullName']}

            play_events = play['playEvents']
            for event in play_events:
                details = event['details']
                desc = details['description']
                code = details.get('code', '')
                pitch_velo = event.get('pitchData', {}).get('startSpeed')
                pitch_selection = details.get('type', {}).get('description', 'pitch')

                outcome_text = ""
                if code == 'C': outcome_text = "called strike"
                elif code == 'B': outcome_text = "ball"
                elif code == 'S': outcome_text = "swinging strike"
                elif code == 'F': outcome_text = "foul"
                elif code == 'X': outcome_text = "in play"

                if outcome_text:
                     lines.append(f"  {outcome_text.capitalize()}: {pitch_velo} mph {pitch_selection}")

            result = play['result']
            outcome = result['event']
            batter_name = play['matchup']['batter']['fullName']

            x_event = next((e for e in play_events if e['details'].get('code') == 'X'), None)
            pitch_info = {}
            if x_event:
                hit_data = x_event.get('hitData', {})
                pitch_info = {
                    'ev': hit_data.get('launchSpeed'),
                    'la': hit_data.get('launchAngle'),
                    'location': hit_data.get('location')
                }

            batted_ball_str = ""
            if outcome not in ["Strikeout", "Walk", "HBP"] and pitch_info.get('ev') is not None:
                batted_ball_str = f" (EV: {pitch_info['ev']} mph, LA: {pitch_info['la']}°)"

            result_line = outcome

            was_error = outcome == "Field Error"
            rbis = result['rbi']
            advances = []
            for r in play['runners']:
                m = r['movement']
                if m['end'] == 'score':
                    advances.append(f"{r['details']['runner']['fullName']} scores")
                elif m['end'] and m['start'] != m['end']:
                    pass

            if was_error:
                result_line = self._format_statcast_template('Error', {'display_outcome': outcome, 'adv_str': "; ".join(advances), 'batter_name': batter_name})
            elif outcome == "Strikeout":
                k_type = "looking" if play_events[-1]['details']['code'] == 'C' else "swinging"
                result_line = f"{batter_name} {self.rng_play.choice(GAME_CONTEXT['statcast_verbs']['Strikeout'][k_type])}."
            elif outcome in GAME_CONTEXT['statcast_verbs'] and outcome not in ['Flyout', 'Groundout']:
                cat = self._get_batted_ball_category(outcome, pitch_info.get('ev'), pitch_info.get('la'))
                phrase, _ = self._get_batted_ball_verb(outcome, cat)
                direction = self._get_hit_location(outcome, pitch_info.get('ev'), pitch_info.get('la'), pitch_info.get('location'))
                tmpl = self._format_statcast_template(outcome, {'batter_name': batter_name, 'verb': phrase, 'runs': rbis, 'direction': direction})
                result_line = tmpl if tmpl else f"{batter_name} {phrase}."
            elif outcome in ["HBP", "Hit By Pitch"]: result_line = "Hit by Pitch."

            if batted_ball_str: result_line += batted_ball_str
            if rbis > 0 and not was_error: result_line += f" {batter_name} drives in {rbis}."

            lines.append(f"Result: {result_line}")

            outs = play['count']['outs']
            lines.append(f" | Outs: {outs} | Score: {self.home_team['name']}: {result['homeScore']}, {self.away_team['name']}: {result['awayScore']}\n")

        lines.append("=" * 20 + " GAME OVER " + "=" * 20)
        final_home = self.gameday_data['liveData']['linescore']['teams']['home']['runs']
        final_away = self.gameday_data['liveData']['linescore']['teams']['away']['runs']
        lines.append(f"\nFinal Score: {self.home_team['name']} {final_home} - {self.away_team['name']} {final_away}")
        winner = self.home_team['name'] if final_home > final_away else self.away_team['name']
        lines.append(f"\n{winner} win!")

        return "\n".join(lines)
