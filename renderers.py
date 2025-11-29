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

    def _get_batted_ball_verb(self, outcome, ev, la):
        outcome_data = GAME_CONTEXT['statcast_verbs'].get(outcome, {})
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

        use_verb = self.rng.random() < 0.6
        phrase_type = 'verbs' if use_verb else 'nouns'
        phrases = outcome_data.get(phrase_type, outcome_data.get('verbs', {}))
        phrase = self.rng.choice(phrases.get(cat, phrases.get('default', ["describes"])))
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

    def _generate_play_description(self, outcome, hit_data, pitch_details, batter_name, fielder_pos=None):
        ev = hit_data.get('launchSpeed')
        la = hit_data.get('launchAngle')
        phrase, phrase_type = self._get_batted_ball_verb(outcome, ev, la)
        direction = ""

        if outcome in ["Single", "Double", "Triple", "Home Run"]:
            direction = self._get_hit_location(outcome, ev, la)
        elif fielder_pos:
            direction = GAME_CONTEXT['hit_directions'].get(fielder_pos, "")

        if batter_name and direction:
            if phrase_type == 'verbs':
                template = self.rng.choice(GAME_CONTEXT['narrative_strings']['play_by_play_templates'])
                return "  " + template.format(
                    batter_name=batter_name, verb=phrase, direction=direction,
                    pitch_type=pitch_details.get('type', 'pitch'),
                    pitch_velo=pitch_details.get('velo', 'N/A')
                )
            else:
                template = self.rng.choice(GAME_CONTEXT['narrative_strings']['play_by_play_noun_templates'])
                return "  " + template.format(
                    batter_name=batter_name, noun=phrase, direction=direction,
                    pitch_type=pitch_details.get('type', 'pitch'),
                    pitch_velo=pitch_details.get('velo', 'N/A')
                )
        return f"  {phrase.capitalize()} {direction}."

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
        self.last_play_inning = None
        self.outs_tracker = 0
        self.runners_on_base = {'1B': None, '2B': None, '3B': None}

        plays = self.gameday_data['liveData']['plays']['allPlays']

        for play in plays:
            about = play['about']
            matchup = play['matchup']
            inning = about['inning']
            half = "Top" if about['isTopInning'] else "Bottom"

            if (inning, half) != current_inning_state:
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
                 runners_str = " and ".join(runners)
                 # Adjust runners_str for specific templates or make templates agnostic
                 # Problem: "runner on {runners_str}" -> "runner on runner on first"

                 # Let's clean up `runners_str` to just be the locations
                 if len(runners) == 3: runners_str = "the bases loaded"
                 elif len(runners) == 2: runners_str = f"{runners[0]} and {runners[1]}"
                 else: runners_str = f"{runners[0]}"

                 template = self.rng.choice(GAME_CONTEXT['narrative_strings']['batter_intro_runners'])
                 # Special handling if the template expects just the bases or the full "runner on X" phrase
                 # Looking at commentary.py:
                 # "Runner on {runners_str}, {outs_str}, for {batter_name}." -> Needs "first" or "first and second"
                 # "And {batter_name} steps in with {runners_str} with {outs_str}." -> "runners on first and second"

                 # I need to separate templates that include "runner on" vs those that don't.
                 # Or standardize my templates.

                 # Let's fix the templates in memory (by logic here) or better yet, fix the templates in commentary.py?
                 # Fixing `commentary.py` is better but I am in renderers.py.
                 # I'll update logic here to match the current templates in `commentary.py`.

                 # Templates:
                 # 1. "And {batter_name} steps in with {runners_str} with {outs_str}." -> wants "runners on first and second"
                 # 2. "{batter_name} comes to the plate. {runners_str} and {outs_str}." -> wants "Runners on first and second" (Capitalized?)
                 # 3. "And that will bring up {batter_name} with {runners_str}." -> wants "runners on first and second"
                 # 4. "Runner on {runners_str}, {outs_str}, for {batter_name}." -> wants "first"

                 # This is tricky because the templates are mixed.
                 # I will simplify the usage here by creating a "situation string" based on the template selected?
                 # No, that's hard because I pick template random.

                 # I'll modify the logic to use a smarter replacement.

                 if len(runners) == 3:
                     base_desc = "the bases loaded"
                     runner_desc = "the bases loaded"
                 elif len(runners) == 2:
                     base_desc = f"{runners[0]} and {runners[1]}"
                     runner_desc = f"runners on {runners[0]} and {runners[1]}"
                 else:
                     base_desc = f"{runners[0]}"
                     runner_desc = f"runner on {runners[0]}" # "runner on first"

                 # I need to pick a template and then format it correctly.
                 template = self.rng.choice(GAME_CONTEXT['narrative_strings']['batter_intro_runners'])

                 # Hack: Check if template starts with "Runner on" or contains "with {runners_str}" where it expects full desc.

                 val_to_use = runner_desc
                 if "Runner on {runners_str}" in template:
                      val_to_use = base_desc

                 lines.append(f"\n{template.format(batter_name=batter_name, runners_str=val_to_use, outs_str=outs_str)}")

            if self.verbose:
                 if 'postOnSecond' in matchup or 'postOnThird' in matchup:
                     if self.rng.random() < 0.2:
                         lines.append(f"  {self._get_narrative_string('runners_in_scoring_position', {'batter_name': batter_name})}")
                 if self.rng.random() < 0.04:
                     lines.append(f"  {self._get_narrative_string('infield_in')}")

            play_events = play['playEvents']
            for event in play_events:
                details = event['details']
                desc = details['description']
                code = details.get('code', '')

                # Pitch info
                pitch_type = details.get('type', {}).get('description', 'pitch')

                if self.verbose:
                    pbp_line = ""
                    connector = self._get_pitch_connector(event['count']['balls'], event['count']['strikes'])

                    if code == 'F':
                        if "Bunt" in desc:
                             pbp_line = self.rng.choice(GAME_CONTEXT['narrative_strings']['bunt_foul']).strip().rstrip('.')
                        else:
                             pbp_line = f"Foul, {self.rng.choice(GAME_CONTEXT['pitch_locations']['foul'])} on a {pitch_type}"
                    elif code == 'C':
                         pbp_line = f"{pitch_type}, {self.rng.choice(GAME_CONTEXT['narrative_strings']['strike_called'])}"
                    elif code == 'S':
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
                        lines.append(pbp_line)
                else:
                    if code != 'X':
                         lines.append(f"  {desc}.")

            result = play['result']
            outcome = result['event']

            # Outcome Logic
            if outcome == "Strikeout":
                k_type = "looking" if play_events[-1]['details']['code'] == 'C' else "swinging"
                verb = self.rng.choice(GAME_CONTEXT['statcast_verbs']['Strikeout'][k_type])
                lines.append(f"  {batter_name} {verb}.")
            elif outcome == "Walk":
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
                    for r in play['runners']:
                         for c in r.get('credits', []):
                             if c['credit'] == 'putout':
                                 fielder_pos = c['position']['abbreviation']
                                 break
                         if fielder_pos: break

                    desc = self._generate_play_description(outcome, hit_data, pitch_details, batter_name, fielder_pos)
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

        lines.append("=" * 20 + " GAME OVER " + "=" * 20)
        final_home = self.gameday_data['liveData']['linescore']['teams']['home']['runs']
        final_away = self.gameday_data['liveData']['linescore']['teams']['away']['runs']
        lines.append(f"\nFinal Score: {self.home_team['name']} {final_home} - {self.away_team['name']} {final_away}")
        winner = self.home_team['name'] if final_home > final_away else self.away_team['name']
        lines.append(f"\n{winner} win!")

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
                phrase, _ = self._get_batted_ball_verb(outcome, pitch_info.get('ev'), pitch_info.get('la'))
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
