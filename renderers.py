import random
from commentary import GAME_CONTEXT
from gameday import GamedayData

class GameRenderer:
    def __init__(self, gameday_data: GamedayData, seed: int = None):
        self.gameday_data = gameday_data
        self.rng = random.Random(seed)
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
            use_verb = self.rng.random() < 0.6
            phrase_type = 'verbs' if use_verb else 'nouns'

        phrases = outcome_data.get(phrase_type, outcome_data.get('verbs', {}))
        phrase_list = phrases.get(cat, phrases.get('default', ["describes"]))
        # Fallback if specific category empty
        if not phrase_list:
             phrase_list = phrases.get('default', ["describes"])

        phrase = self.rng.choice(phrase_list)
        return phrase, phrase_type

    def _get_hit_location(self, hit_type, ev, la):
        if la is None or ev is None: return "fair"
        if hit_type in ["Single", "Double"]:
            if -10 < la < 10: return self.rng.choice(["up the middle", "through the right side", "through the left side"])
            elif 10 < la < 25: return self.rng.choice(["to left field", "to center field", "to right field"])
            else: return self.rng.choice(["into shallow left", "into shallow center", "into shallow right"])
        elif hit_type == "Triple":
            return self.rng.choice(["into the right-center gap", "into the left-center gap"])
        elif hit_type == "Home Run":
            if abs(la - 28) < 5 and ev > 105: return "down the line"
            return self.rng.choice(["to deep left field", "to deep center field", "to deep right field"])
        return "fair"

    def _format_statcast_template(self, outcome, context):
        templates = GAME_CONTEXT.get('statcast_templates', {}).get(outcome)
        if not templates: return None
        template = self.rng.choice(templates)
        if '{verb_capitalized}' in template:
            context['verb_capitalized'] = context.get('verb', '').capitalize()
        return template.format(**context)


class NarrativeRenderer(GameRenderer):
    def __init__(self, gameday_data: GamedayData, seed: int = None, verbose: bool = True, use_bracketed_ui: bool = False):
        super().__init__(gameday_data, seed)
        self.verbose = verbose
        self.use_bracketed_ui = use_bracketed_ui

    def _get_narrative_string(self, key, context=None):
        if context is None: context = {}
        return self.rng.choice(GAME_CONTEXT['narrative_strings'].get(key, [""])).format(**context)

    def _get_pitch_connector(self, balls, strikes):
        if balls == 0 and strikes == 0:
            return self.rng.choice(["And the pitch...", "And the pitch..."])

        count_str = f"{balls}-{strikes}"
        templates = [
            f"And the {count_str}...",
            f"The {count_str} pitch...",
            f"And the {count_str} pitch...",
            f"And the {count_str}..."
        ]
        return self.rng.choice(templates)

    def _generate_play_description(self, outcome, hit_data, pitch_details, batter_name, fielder_pos=None, fielder_name=None, connector=None):
        ev = hit_data.get('launchSpeed')
        la = hit_data.get('launchAngle')

        cat = self._get_batted_ball_category(outcome, ev, la)

        # 1. Try to find a full-sentence narrative template for this outcome/category
        # Structure: GAME_CONTEXT['narrative_templates'][outcome][cat] -> list of templates
        specific_templates = []
        if 'narrative_templates' in GAME_CONTEXT:
            outcome_templates = GAME_CONTEXT['narrative_templates'].get(outcome, {})
            specific_templates = outcome_templates.get(cat, [])
            if not specific_templates:
                specific_templates = outcome_templates.get('default', [])

        # Decide whether to use a specific full-sentence template or build one
        # If specific templates exist, use them 40% of the time for variety, unless it's a special case?
        # Let's use them if available.
        template = None
        if specific_templates and self.rng.random() < 0.5:
            template = self.rng.choice(specific_templates)

        direction = ""
        if outcome in ["Single", "Double", "Triple", "Home Run"]:
            direction = self._get_hit_location(outcome, ev, la)
        elif fielder_pos:
            direction = GAME_CONTEXT['hit_directions'].get(fielder_pos, "")

        context = {
            'batter_name': batter_name,
            'direction': direction,
            'pitch_type': pitch_details.get('type', 'pitch'),
            'pitch_velo': pitch_details.get('velo', 'N/A'),
            'fielder_name': fielder_name or "the fielder"
        }

        # If a connector is provided (e.g. "And the 1-1..."), prepend it.
        prefix = f"  {connector} " if connector else "  "

        if template:
             # These templates are usually self-contained or use simple vars
             # If they need a verb/noun, we might need to fetch one, but the design
             # of these specific templates (e.g. "Lined {direction}") is to avoid generic verbs.
             return prefix + template.format(**context)

        # 2. Fallback to generic construction

        # Decide verb vs noun first? Or let _get_batted_ball_verb decide?
        # We need to pick the template first to know if we need a verb or noun,
        # OR pick the phrase type first and then the template.
        # Let's pick phrase type first.
        phrase, phrase_type = self._get_batted_ball_verb(outcome, cat)

        if connector:
            # If we have a connector, prefer verb-first templates to match flow
            if phrase_type == 'verbs':
                template = self.rng.choice(GAME_CONTEXT['narrative_strings']['play_by_play_templates'])
                context['verb'] = phrase
                context['verb_capitalized'] = phrase.capitalize()
            else:
                # Noun templates
                template = self.rng.choice(GAME_CONTEXT['narrative_strings']['play_by_play_noun_templates'])
                context['noun'] = phrase
                context['noun_capitalized'] = phrase.capitalize()
        else:
            if phrase_type == 'verbs':
                template = self.rng.choice(GAME_CONTEXT['narrative_strings']['play_by_play_templates'])
                context['verb'] = phrase
                context['verb_capitalized'] = phrase.capitalize()
            else:
                template = self.rng.choice(GAME_CONTEXT['narrative_strings']['play_by_play_noun_templates'])
                context['noun'] = phrase
                context['noun_capitalized'] = phrase.capitalize()

        return prefix + template.format(**context)

    def _format_bases_string(self, bases_dict):
        if self.use_bracketed_ui:
            b1 = "1B" if bases_dict.get('1B') else "_"
            b2 = "2B" if bases_dict.get('2B') else "_"
            b3 = "3B" if bases_dict.get('3B') else "_"
            return f"[{b1}]-[{b2}]-[{b3}]"
        else:
            runners = []
            if bases_dict.get('3B'): runners.append(f"3B: {bases_dict['3B']}")
            if bases_dict.get('2B'): runners.append(f"2B: {bases_dict['2B']}")
            if bases_dict.get('1B'): runners.append(f"1B: {bases_dict['1B']}")
            return ", ".join(runners) if runners else "Bases empty"

    def _render_steal_event(self, event):
        details = event['details']
        outcome = details['eventType'] # 'stolen_base' or 'caught_stealing'
        desc = details['description'] # e.g. "Stolen Base 2B"

        base_target = "second"
        base_key = "2B"
        prev_base = "1B"
        if "3B" in desc:
            base_target = "third"
            base_key = "3B"
            prev_base = "2B"
        elif "2B" in desc:
            pass # default
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

            throw_desc = self.rng.choice(GAME_CONTEXT['narrative_strings']['throw_outcome_safe']).format(base=base_target)
            return f"  {throw_desc} {runner_name} steals {base_target}."

        elif outcome == 'caught_stealing':
            self.runners_on_base[prev_base] = None # Out

            throw_desc = self.rng.choice(GAME_CONTEXT['narrative_strings']['throw_outcome_out']).format(base=base_target)
            return f"  {throw_desc} {runner_name} is caught stealing {base_target}."

        return f"  {desc}."

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
        lines.append(f"So, we are underway here at {self.gameday_data['gameData'].get('venue', 'the ballpark')}.")

        current_inning_state = (0, '')
        self.last_play_inning = None
        self.outs_tracker = 0
        self.runners_on_base = {'1B': None, '2B': None, '3B': None}
        self.current_score = (0, 0) # Away, Home

        plays = self.gameday_data['liveData']['plays']['allPlays']

        for play in plays:
            about = play['about']
            matchup = play['matchup']
            inning = about['inning']
            half = "Top" if about['isTopInning'] else "Bottom"

            if (inning, half) != current_inning_state:
                # End of previous inning summary
                if current_inning_state[0] != 0:
                     # Calculate total innings completed so far
                     innings_in_books = inning - 1
                     if half == "Top" and inning > 1:
                         # Start of Top of N means N-1 full innings are done.
                         num = innings_in_books
                         lines.append(f"\nAnd with {num} in the books, it's {self.away_team['name']} {self.current_score[0]}, {self.home_team['name']} {self.current_score[1]}.")

                team_name = self.away_team['name'] if about['isTopInning'] else self.home_team['name']
                lines.append("-" * 50)
                lines.append(f"{half} of Inning {inning} | {team_name} batting")

                self.runners_on_base = {'1B': None, '2B': None, '3B': None}
                if inning >= 10:
                     # Detect ghost runner from play events if it's the start of the inning
                     for r in play['runners']:
                         if r['movement']['start'] == '2B':
                             runner_name = r['details']['runner']['fullName']
                             self.runners_on_base['2B'] = runner_name
                             if self.verbose:
                                 lines.append(f"Automatic runner on second: {runner_name} jogs out to take his lead.")
                             break

                current_inning_state = (inning, half)
                self.outs_tracker = 0 # New inning starts with 0 outs

            # Pitching Change
            pitching_team_key = 'home' if about['isTopInning'] else 'away'
            pitcher_id = matchup['pitcher']['id']
            prev_info = self.current_pitcher_info[pitching_team_key]

            if prev_info and prev_info['id'] != pitcher_id:
                 team_name = self.home_team['name'] if about['isTopInning'] else self.away_team['name']
                 lines.append(f"\n--- Pitching Change for {team_name}: {matchup['pitcher']['fullName']} replaces {prev_info['name']} ---\n")

            self.current_pitcher_info[pitching_team_key] = {'id': pitcher_id, 'name': matchup['pitcher']['fullName']}

            batter_name = matchup['batter']['fullName']

            # Better batter intro
            outs_str = f"{self.outs_tracker} out{'s' if self.outs_tracker != 1 else ''}"
            if self.outs_tracker == 1: outs_str = "one away"
            elif self.outs_tracker == 2: outs_str = "two down"
            else: outs_str = "nobody out"

            team_name = self.home_team['name'] if not about['isTopInning'] else self.away_team['name']

            bases_dict = self.runners_on_base
            runners_str = ""
            runners = []
            if bases_dict.get('1B'): runners.append("first")
            if bases_dict.get('2B'): runners.append("second")
            if bases_dict.get('3B'): runners.append("third")

            if len(runners) == 0:
                if self.outs_tracker == 0:
                     template = self.rng.choice(GAME_CONTEXT['narrative_strings']['batter_intro_leadoff'])
                else:
                     template = self.rng.choice(GAME_CONTEXT['narrative_strings']['batter_intro_empty'])
                lines.append(f"\n{template.format(batter_name=batter_name, team_name=team_name, outs_str=outs_str)}")
            else:
                 # Logic for runner strings
                 if len(runners) == 3:
                     base_desc = "the bases loaded"
                     runner_desc = "the bases loaded"
                 elif len(runners) == 2:
                     base_desc = f"{runners[0]} and {runners[1]}"
                     runner_desc = f"runners on {runners[0]} and {runners[1]}"
                 else:
                     base_desc = f"{runners[0]}"
                     runner_desc = f"runner on {runners[0]}"

                 template = self.rng.choice(GAME_CONTEXT['narrative_strings']['batter_intro_runners'])

                 val_to_use = runner_desc
                 if "Runner on {runners_str}" in template:
                      val_to_use = base_desc

                 lines.append(f"\n{template.format(batter_name=batter_name, runners_str=val_to_use, outs_str=outs_str)}")

            # Handedness matchup
            if self.verbose and self.rng.random() < 0.3:
                 # Check matchup
                 bat_side = matchup['batSide']['code'] # L or R or S
                 pitch_hand = matchup['pitchHand']['code'] # L or R

                 # If switch, we need to know which side they are batting from.
                 # Usually switch hitters bat opposite to pitcher.
                 if bat_side == 'S':
                     bat_side = 'R' if pitch_hand == 'L' else 'L'

                 b_text = "Righty" if bat_side == 'R' else "Lefty"
                 p_text = "righty" if pitch_hand == 'R' else "lefty"

                 # "Righty against righty."
                 matchup_str = f"{b_text} against {p_text}."
                 # Or use template if available, but simple construction works
                 matchup_template = self.rng.choice(GAME_CONTEXT['narrative_strings'].get('batter_matchup_handedness', []))
                 if matchup_template:
                     # Filter for correct one
                     # This is brittle if templates change. Let's just use constructed string for now or map it.
                     pass

                 # Let's map it simply
                 if bat_side == 'R' and pitch_hand == 'R': lines.append("  Righty against righty.")
                 elif bat_side == 'R' and pitch_hand == 'L': lines.append("  Righty against the lefty.")
                 elif bat_side == 'L' and pitch_hand == 'R': lines.append("  Lefty against the righty.")
                 elif bat_side == 'L' and pitch_hand == 'L': lines.append("  Lefty against the lefty.")

            if self.verbose:
                 if 'postOnSecond' in matchup or 'postOnThird' in matchup:
                     if self.rng.random() < 0.2:
                         lines.append(f"  {self._get_narrative_string('runners_in_scoring_position', {'batter_name': batter_name})}")
                 if self.rng.random() < 0.04:
                     lines.append(f"  {self._get_narrative_string('infield_in')}")

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

                # Check ahead for steal
                is_steal_attempt = False
                steal_event = None
                if i + 1 < len(play_events):
                    next_event = play_events[i+1]
                    if next_event['details'].get('eventType') in ['stolen_base', 'caught_stealing']:
                        is_steal_attempt = True
                        steal_event = next_event

                # Pitch info
                pitch_type = details.get('type', {}).get('description', 'pitch')

                if self.verbose:
                    pbp_line = ""
                    connector = self._get_pitch_connector(event['count']['balls'], event['count']['strikes'])

                    if code == 'X':
                        x_event_connector = connector

                    if is_steal_attempt:
                        connector = f"{connector.rstrip('...')} {self.rng.choice(GAME_CONTEXT['narrative_strings']['runner_goes'])}"

                    if code == 'F':
                        if "Bunt" in desc:
                             pbp_line = self.rng.choice(GAME_CONTEXT['narrative_strings']['bunt_foul']).strip().rstrip('.')
                        else:
                             phrase = self.rng.choice(GAME_CONTEXT['pitch_locations']['foul'])
                             if "foul" in phrase.lower() or "spoils" in phrase.lower() or "fights" in phrase.lower() or "jams" in phrase.lower():
                                 pbp_line = f"{phrase}"
                             else:
                                 pbp_line = f"Foul, {phrase}"
                    elif code == 'C':
                         if event['count']['strikes'] == 2:
                             pbp_line = f"{pitch_type}, {self.rng.choice(GAME_CONTEXT['narrative_strings']['strike_called_three'])}"
                         else:
                             pbp_line = f"{pitch_type}, {self.rng.choice(GAME_CONTEXT['narrative_strings']['strike_called'])}"
                    elif code == 'S':
                         if event['count']['strikes'] == 2:
                             pbp_line = f"{pitch_type}, {self.rng.choice(GAME_CONTEXT['narrative_strings']['strike_swinging_three'])}"
                         else:
                             pbp_line = f"{pitch_type}, {self._get_narrative_string('strike_swinging')}"
                    elif code == 'B':
                         pbp_line = f"{pitch_type} {self.rng.choice(GAME_CONTEXT['pitch_locations']['ball'])}"

                    if pbp_line:
                        pbp_line = f"  {connector} {pbp_line}."

                        c = event['count']
                        b, s = c['balls'], c['strikes']
                        if code == 'B': b += 1
                        elif code in ['C', 'S', 'F']:
                            if code == 'F' and s == 2: pass
                            else: s += 1

                        if b < 4 and s < 3:
                            pbp_line += f" {b}-{s}."

                        # Check if this is the final pitch of a Strikeout or Walk
                        # Note: If steal happened, next event is steal, not final pitch event unless steal IS final event (unlikely)
                        # Actually, if Caught Stealing makes 3 outs, then this pitch is final.
                        # But loop will handle steal output, then break loop or continue.

                        is_final_event = (event == play_events[-1])
                        # If steal follows, this is NOT final event of list.

                        if is_final_event and outcome in ["Strikeout", "Walk"]:
                            last_pitch_context = pbp_line.rstrip(".") # Store without trailing period
                            # Don't append line yet, will combine with outcome.
                            i += 1
                            continue

                        lines.append(pbp_line)

                        if is_steal_attempt:
                            lines.append(self._render_steal_event(steal_event))
                            i += 1 # Skip steal event in next iteration
                else:
                    if code != 'X':
                         lines.append(f"  {desc}.")

                i += 1

            # Outcome Logic
            if outcome == "Strikeout":
                k_type = "looking" if play_events[-1]['details']['code'] == 'C' else "swinging"

                if last_pitch_context:
                     # Combined with final pitch context. Use simplified verbs to avoid redundancy.
                     if k_type == 'swinging':
                         simple_verb = self.rng.choice(["strikes out", "is set down swinging", "goes down swinging", "is out"])
                         lines.append(f"{last_pitch_context}, and {batter_name} {simple_verb}.")
                     else: # looking
                         simple_verb = self.rng.choice(["strikes out looking", "is caught looking", "is rung up", "is out looking"])
                         lines.append(f"{last_pitch_context}, and {batter_name} {simple_verb}.")
                else:
                    # Try narrative templates first
                    specific_templates = []
                    if 'narrative_templates' in GAME_CONTEXT:
                        outcome_templates = GAME_CONTEXT['narrative_templates'].get(outcome, {})
                        specific_templates = outcome_templates.get(k_type, [])

                    template = None
                    if specific_templates and self.rng.random() < 0.5:
                         template = self.rng.choice(specific_templates)

                    outcome_text = ""
                    if template:
                         pitch_details = {'type': play_events[-1]['details'].get('type', {}).get('description', 'pitch')}
                         context = {
                            'batter_name': batter_name,
                            'pitch_type': pitch_details['type']
                         }
                         outcome_text = template.format(**context)
                    else:
                        verb = self.rng.choice(GAME_CONTEXT['statcast_verbs']['Strikeout'][k_type])
                        outcome_text = f"{batter_name} {verb}"

                    lines.append(f"  {outcome_text}.")

            elif outcome == "Walk":
                if last_pitch_context:
                    lines.append(f"{last_pitch_context}, and {batter_name} draws a walk.")
                else:
                    lines.append(f"  {batter_name} draws a walk.")
            elif outcome in ["HBP", "Hit By Pitch"]:
                lines.append(f"  {batter_name} is hit by the pitch.")
            elif outcome == "Strikeout Double Play":
                lines.append(f"  {batter_name} strikes out on a pitch in the dirt, but the runner is gunned down! A strikeout double play.")
            elif outcome == "Caught Stealing":
                 runner_out = next((r for r in play['runners'] if r['movement']['isOut']), None)
                 if runner_out:
                     ob = runner_out['movement']['outBase']
                     base_name = "second" if ob == "2B" else "third" if ob == "3B" else "home"
                     lines.append(f"  {runner_out['details']['runner']['fullName']} is caught stealing {base_name}!")
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
                     lines.append(f"  An error by {pos} {name} allows the batter to reach base.")
                 else:
                     lines.append(f"  The batter reaches on a fielding error.")

            else:
                x_event = next((e for e in play_events if e['details'].get('code') == 'X'), None)
                if x_event:
                    hit_data = x_event.get('hitData', {})
                    pitch_details = {'type': x_event['details'].get('type', {}).get('description', 'pitch'), 'velo': x_event.get('pitchData', {}).get('startSpeed')}

                    fielder_pos = None
                    fielder_name = None

                    # Find credits for the out
                    out_credits = []
                    for r in play['runners']:
                        if r['movement']['isOut']:
                            out_credits = r.get('credits', [])
                            break

                    # Fallback to any credits if no out (e.g. single)
                    if not out_credits:
                        for r in play['runners']:
                             if r.get('credits'):
                                 out_credits = r.get('credits')
                                 break

                    # Identify primary fielder (assist preferred for groundouts, otherwise putout)
                    primary_credit = None
                    for c in out_credits:
                        if c['credit'] == 'assist':
                            primary_credit = c
                            break
                    if not primary_credit:
                        for c in out_credits:
                            if c['credit'] == 'putout':
                                primary_credit = c
                                break

                    if primary_credit:
                        fielder_pos = primary_credit['position']['abbreviation']
                        fielder_name = primary_credit['player']['fullName'].split()[-1]

                    desc = self._generate_play_description(outcome, hit_data, pitch_details, batter_name, fielder_pos, fielder_name, connector=x_event_connector)
                    lines.append(desc)

            # Update outs
            self.outs_tracker = play['count']['outs']

            # Score & Status
            post_bases = { '1B': None, '2B': None, '3B': None }
            for r in play['runners']:
                 m = r['movement']
                 if not m['isOut'] and m['end'] in post_bases:
                     post_bases[m['end']] = r['details']['runner']['fullName']

            self.runners_on_base = post_bases

            bases_str = self._format_bases_string(post_bases)

            lines.append(f" | Outs: {self.outs_tracker} | Bases: {bases_str} | Score: {self.home_team['name']}: {result['homeScore']}, {self.away_team['name']}: {result['awayScore']}\n")

            self.current_score = (result['awayScore'], result['homeScore'])

        lines.append("=" * 20 + " GAME OVER " + "=" * 20)
        final_home = self.gameday_data['liveData']['linescore']['teams']['home']['runs']
        final_away = self.gameday_data['liveData']['linescore']['teams']['away']['runs']
        lines.append(f"\nFinal Score: {self.home_team['name']} {final_home} - {self.away_team['name']} {final_away}")
        winner = self.home_team['name'] if final_home > final_away else self.away_team['name']
        lines.append(f"\n{winner} win!")
        lines.append(f"\nFor the victorious {winner}: {max(final_home, final_away)} runs.") # Simplified, don't have hits/errors counts easily without calc

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

            # Pitching Change (omitted in Statcast?)
            # BaseballSimulator Statcast output doesn't seem to print "Pitching Change".
            # `baseball.py`: `if self.base_commentary_style != 'none':` which covers all.
            # So Statcast SHOULD have pitching changes.
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

                # Map code to pitch_outcome_text
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

            # Outcome logic
            # _print_statcast_result logic

            # Need description context (batted_ball_data)
            # Find X event for data
            x_event = next((e for e in play_events if e['details'].get('code') == 'X'), None)
            pitch_info = {}
            if x_event:
                pitch_info = {'ev': x_event.get('hitData', {}).get('launchSpeed'), 'la': x_event.get('hitData', {}).get('launchAngle')}

            batted_ball_str = ""
            if outcome not in ["Strikeout", "Walk", "HBP"] and pitch_info.get('ev') is not None:
                batted_ball_str = f" (EV: {pitch_info['ev']} mph, LA: {pitch_info['la']}°)"

            result_line = outcome # Default

            was_error = outcome == "Field Error" # Or check credits?
            # advances/rbis?
            # rbis are in result['rbi']
            rbis = result['rbi']
            # advances need calculation
            advances = []
            # ... calculate advances ...
            # In baseball.py, advances were passed to _print_statcast_result.
            # Here we can try to reconstruct advances or just ignore them for basic statcast line if complexity too high.
            # BaseballSimulator printed advances: `if not was_error and advances: ...`
            # "Runner scores", "Runner to 3B".
            # We can check runner movement.
            for r in play['runners']:
                m = r['movement']
                if m['end'] == 'score':
                    advances.append(f"{r['details']['runner']['fullName']} scores")
                elif m['end'] and m['start'] != m['end']:
                    # advanced
                    pass # Add to string if needed

            if was_error:
                result_line = self._format_statcast_template('Error', {'display_outcome': outcome, 'adv_str': "; ".join(advances), 'batter_name': batter_name})
            elif outcome == "Strikeout":
                k_type = "looking" if play_events[-1]['details']['code'] == 'C' else "swinging"
                # description['k_type']
                result_line = f"{batter_name} {self.rng.choice(GAME_CONTEXT['statcast_verbs']['Strikeout'][k_type])}."
            elif outcome in GAME_CONTEXT['statcast_verbs'] and outcome not in ['Flyout', 'Groundout']:
                cat = self._get_batted_ball_category(outcome, pitch_info.get('ev'), pitch_info.get('la'))
                phrase, _ = self._get_batted_ball_verb(outcome, cat)
                direction = self._get_hit_location(outcome, pitch_info.get('ev'), pitch_info.get('la'))
                # Template
                tmpl = self._format_statcast_template(outcome, {'batter_name': batter_name, 'verb': phrase, 'runs': rbis, 'direction': direction})
                result_line = tmpl if tmpl else f"{batter_name} {phrase}."
            elif outcome in ["HBP", "Hit By Pitch"]: result_line = "Hit by Pitch."

            if batted_ball_str: result_line += batted_ball_str
            if rbis > 0 and not was_error: result_line += f" {batter_name} drives in {rbis}."

            lines.append(f"Result: {result_line}")

            # Status line
            outs = play['count']['outs']
            lines.append(f" | Outs: {outs} | Score: {self.home_team['name']}: {result['homeScore']}, {self.away_team['name']}: {result['awayScore']}\n")

        lines.append("=" * 20 + " GAME OVER " + "=" * 20)
        final_home = self.gameday_data['liveData']['linescore']['teams']['home']['runs']
        final_away = self.gameday_data['liveData']['linescore']['teams']['away']['runs']
        lines.append(f"\nFinal Score: {self.home_team['name']} {final_home} - {self.away_team['name']} {final_away}")
        winner = self.home_team['name'] if final_home > final_away else self.away_team['name']
        lines.append(f"\n{winner} win!")

        return "\n".join(lines)
