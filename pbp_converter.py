
import random
from commentary import GAME_CONTEXT
from gameday import GamedayData, Play, PlayEvent

class GamedayConverter:
    def __init__(self, gameday_data: GamedayData, style='narrative', verbose_phrasing=True, use_bracketed_ui=False, commentary_seed=None):
        self.gameday_data = gameday_data
        self.style = style
        self.verbose_phrasing = verbose_phrasing
        self.use_bracketed_ui = use_bracketed_ui
        self.output_lines = []
        self.commentary_rng = random.Random(commentary_seed)

    def _print(self, text, end="\n"):
        """Buffer all output."""
        if self.output_lines and end == "" and self.output_lines[-1]:
            self.output_lines[-1] += text
        else:
            self.output_lines.append(text)

    def _get_player_display_name(self, player):
        # Nicknames are not in Gameday data, so we'll just use fullName
        return player['fullName']

    def _get_narrative_string(self, key, context=None):
        """Helper to get a random narrative string and format it."""
        # This will need careful adaptation since it depends on game state.
        # For now, let's just get a random string.
        # The context will have to be built from the play data.
        if context is None:
            context = {}
        return self.commentary_rng.choice(GAME_CONTEXT['narrative_strings'].get(key, [""])).format(**context)

    def _get_velocity_commentary(self, velo, pitch_type):
        # We don't have pitcher's velocity range in gameday.
        # This will be a simplification. We can decide to show it always or never.
        # For now, let's always show it if verbose.
        if self.verbose_phrasing and velo:
            return f" ({velo} mph)"
        return ""

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

        use_verb = self.commentary_rng.random() < 0.6
        phrase_type = 'verbs' if use_verb else 'nouns'
        phrases = outcome_data.get(phrase_type, outcome_data.get('verbs', {}))
        phrase = self.commentary_rng.choice(phrases.get(cat, phrases.get('default', ["describes"])))
        return phrase, phrase_type

    def _format_statcast_template(self, outcome, context):
        templates = GAME_CONTEXT.get('statcast_templates', {}).get(outcome)
        if not templates: return None
        template = self.commentary_rng.choice(templates)
        if '{verb_capitalized}' in template:
            context['verb_capitalized'] = context.get('verb', '').capitalize()
        return template.format(**context)

    def _get_hit_location_from_runners(self, runners):
        # Find fielder who made the play from credits
        for runner in runners:
            if runner['credits']:
                # The first credit is usually the fielder who made the play
                fielder_pos = runner['credits'][0]['position']['abbreviation']
                return GAME_CONTEXT['hit_directions'].get(fielder_pos, "")
        return "fair"

    def _get_hit_location(self, hit_type, ev, la):
        """Determine hit location based on EV and LA."""
        # This is from the original simulator, we can keep it for variety in hits.
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


    def _generate_play_description(self, play: Play):
        outcome = play['result']['event']
        batter = play['matchup']['batter']

        last_pitch_event = play['playEvents'][-1]
        batted_ball_data = last_pitch_event.get('hitData', {})
        pitch_details = last_pitch_event.get('details', {})
        pitch_data = last_pitch_event.get('pitchData', {})

        ev = batted_ball_data.get('launchSpeed')
        la = batted_ball_data.get('launchAngle')
        pitch_type = pitch_details.get('type', {}).get('description', 'pitch')
        pitch_velo = pitch_data.get('startSpeed')

        phrase, phrase_type = self._get_batted_ball_verb(outcome, ev, la)
        direction = ""

        if outcome in ["Single", "Double", "Triple", "Home Run"]:
            direction = self._get_hit_location(outcome, ev, la)
        else: # Out
            direction = self._get_hit_location_from_runners(play['runners'])

        if batter and direction:
            context = {
                'batter_name': batter['fullName'],
                'verb': phrase,
                'noun': phrase,
                'direction': direction,
                'pitch_type': pitch_type,
                'pitch_velo': pitch_velo
            }
            template_key = 'play_by_play_templates' if phrase_type == 'verbs' else 'play_by_play_noun_templates'
            template = self.commentary_rng.choice(GAME_CONTEXT['narrative_strings'][template_key])
            return "  " + template.format(**context)

        return f"  {phrase.capitalize()} {direction}."


    def _get_bases_str(self, play: Play):
        bases = [
            play['matchup'].get('postOnFirst'),
            play['matchup'].get('postOnSecond'),
            play['matchup'].get('postOnThird')
        ]
        if self.use_bracketed_ui:
            return f"[{'1B' if bases[0] else '_'}]-[{'2B' if bases[1] else '_'}]-[{'3B' if bases[2] else '_'}]"
        else:
            runners = []
            if bases[2]: runners.append(f"3B: {bases[2]['fullName']}")
            if bases[1]: runners.append(f"2B: {bases[1]['fullName']}")
            if bases[0]: runners.append(f"1B: {bases[0]['fullName']}")
            return ", ".join(runners) if runners else "Bases empty"

    def _print_pre_game_summary(self):
        self._print("=" * 20 + " GAME START " + "=" * 20)
        game_data = self.gameday_data['gameData']
        away_team = game_data['teams']['away']['name']
        home_team = game_data['teams']['home']['name']
        self._print(f"{away_team} vs. {home_team}")

        if 'gameInfo' in game_data:
            game_info = game_data['gameInfo']
            self._print(f"Venue: {game_info['venue']}")
            self._print(f"Weather: {game_info['weather']}")
            self._print(f"Umpires: {', '.join(game_info['umpires'])}")

        self._print("-" * 50)

    def _print_narrative_result(self, play: Play):
        outcome = play['result']['event']
        description = play['result']['description']

        outcomes_with_description = ["Single", "Double", "Triple", "Home Run", "Groundout", "Flyout", "Pop Out", "Lineout", "Double Play", "Sac Fly", "Forceout", "Bunt Ground Out", "Sacrifice Bunt"]

        if self.verbose_phrasing and outcome in outcomes_with_description:
            self._print(self._generate_play_description(play))
            return

        result_line = description if description else outcome
        if outcome == "Walk":
            self._print(f"  {play['matchup']['batter']['fullName']} draws a walk.")
            return
        if "error" in outcome.lower():
            self._print(f"  An error by the defense allows the batter to reach base.")
            return
        if outcome in ["Strikeout"]: result_line = outcome
        elif outcome == "HBP": result_line = "Hit by Pitch"

        if outcome not in ["Single", "Double", "Triple", "Home Run"]:
             self._print(f" Result: {result_line}", end="")
        else:
             self._print(f" Result: {outcome}", end="")


    def _print_statcast_result(self, play: Play):
        outcome = play['result']['event']
        batter = play['matchup']['batter']
        rbis = play['result']['rbi']

        last_pitch_event = play['playEvents'][-1] if play['playEvents'] else {}
        batted_ball_data = last_pitch_event.get('hitData', {})
        ev = batted_ball_data.get('launchSpeed')
        la = batted_ball_data.get('launchAngle')

        batted_ball_str = ""
        if outcome not in ["Strikeout", "Walk", "HBP"] and ev and la:
            batted_ball_str = f" (EV: {ev} mph, LA: {la}°)"

        result_line = play['result']['description']

        was_error = 'error' in outcome.lower()
        if was_error:
            # Simplified error description
             result_line = f"{play['result']['description']}"
        elif outcome == 'Strikeout':
            # k_type is not in gameday. Let's pick one randomly.
            k_type = self.commentary_rng.choice(['swinging', 'looking'])
            verb = self.commentary_rng.choice(GAME_CONTEXT['statcast_verbs']['Strikeout'][k_type])
            result_line = f"{batter['fullName']} {verb}."
        elif outcome in GAME_CONTEXT['statcast_verbs']:
            phrase, _ = self._get_batted_ball_verb(outcome, ev, la)
            direction = ""
            if outcome in ["Single", "Double", "Triple", "Home Run"]:
                direction = self._get_hit_location(outcome, ev, la)
            else:
                direction = self._get_hit_location_from_runners(play['runners'])

            result_line = self._format_statcast_template(outcome, {'batter_name': batter['fullName'], 'verb': phrase, 'runs': rbis, 'direction': direction}) or f"{batter['fullName']} {phrase}."
        elif outcome == "HBP":
            result_line = "Hit by Pitch."

        if batted_ball_str: result_line += batted_ball_str
        if rbis > 0 and not was_error: result_line += f" {batter['fullName']} drives in {rbis}."

        advances = []
        for runner in play['runners']:
            if runner['movement']['end'] and runner['movement']['end'] != 'score' and runner['movement']['start'] != runner['movement']['end']:
                advances.append(f"{runner['details']['runner']['fullName']} to {runner['movement']['end']}")
            if runner['movement']['end'] == 'score':
                 advances.append(f"{runner['details']['runner']['fullName']} scores")

        if not was_error and advances:
            if adv_str := "; ".join(adv for adv in advances if adv): result_line += f" ({adv_str})"

        self._print(f"Result: {result_line}")


    def _generate_situational_commentary(self, play: Play):
        if self.style == 'narrative' and self.verbose_phrasing:
            about = play['about']
            pre_play_outs = play['count']['outs'] - sum(1 for r in play['runners'] if r['movement']['isOut'])

            # Pre-play base state
            bases = [
                play['matchup'].get('postOnFirst'),
                play['matchup'].get('postOnSecond'),
                play['matchup'].get('postOnThird')
            ]

            if any(bases):
                if (bases[1] or bases[2]) and self.commentary_rng.random() < 0.2:
                    self._print(f"  {self._get_narrative_string('runners_in_scoring_position')}")
                if about['inning'] > 6 and play['result']['homeScore'] == play['result']['awayScore'] and self.commentary_rng.random() < 0.25:
                    self._print(f"  A crucial at-bat here in a tie game.")

            if self.commentary_rng.random() < 0.04:
                self._print(f"  {self._get_narrative_string('infield_in')}")

    def convert(self):
        if self.style == 'none':
            return ""

        self._print_pre_game_summary()

        current_inning = 0
        is_top_inning = True

        for play in self.gameday_data['liveData']['plays']['allPlays']:
            self._generate_situational_commentary(play)
            about = play['about']
            if about['inning'] != current_inning or about['isTopInning'] != is_top_inning:
                current_inning = about['inning']
                is_top_inning = about['isTopInning']
                inning_half = "Top" if is_top_inning else "Bottom"
                batting_team_name = self.gameday_data['gameData']['teams']['away']['name'] if is_top_inning else self.gameday_data['gameData']['teams']['home']['name']
                self._print("-" * 50)
                self._print(f"{inning_half} of Inning {current_inning} | {batting_team_name} batting")

            batter_display_name = self._get_player_display_name(play['matchup']['batter'])

            # Pre-at-bat situation
            # Gameday data has post-play outs, so we need to calculate pre-play outs.
            # This is tricky. Let's assume the previous play's outs is the pre-play outs for this play.
            # A bit of a simplification.
            # A better way is to sum up outs from runners on the current play.
            outs_this_play = sum(1 for r in play['runners'] if r['movement']['isOut'])
            pre_play_outs = play['count']['outs'] - outs_this_play

            # A similar issue for bases. The matchup has post-play runners.
            # We would need to work backwards from runner movements to get pre-play state.
            # For now, let's omit the pre-play bases string.
            outs_str = f"{pre_play_outs} out{'s' if pre_play_outs != 1 else ''}"
            self._print(f"\n{batter_display_name} steps to the plate. {outs_str}.")

            # Pitch-by-pitch commentary
            if self.style == 'narrative':
                for p_event in play['playEvents']:
                    details = p_event['details']
                    count = p_event['count']
                    pbp_line = ""
                    if self.verbose_phrasing:
                        pitch_data = p_event.get('pitchData', {})
                        pitch_type = details.get('type', {}).get('description', 'pitch')
                        velo = pitch_data.get('startSpeed')
                        velo_commentary = self._get_velocity_commentary(velo, pitch_type)

                        if details['code'] == 'F': # Foul
                             pbp_line = f"  Foul, {self.commentary_rng.choice(GAME_CONTEXT['pitch_locations']['foul'])} on a {pitch_type}{velo_commentary}."
                        elif details['code'] == 'C': # Called Strike
                            pbp_line = f"  {self.commentary_rng.choice(GAME_CONTEXT['narrative_strings']['strike_called'])} with the {pitch_type}{velo_commentary}."
                        elif details['code'] == 'S': # Swinging Strike
                            pbp_line = f"  {self._get_narrative_string('strike_swinging')} on a {pitch_type}{velo_commentary}."
                        elif details['code'] == 'B': # Ball
                             pbp_line = f"  {self.commentary_rng.choice(GAME_CONTEXT['pitch_locations']['ball'])} with the {pitch_type}{velo_commentary}."
                        # 'X' for in play is handled by the result.
                    else: # Not verbose
                        if details['code'] != 'X':
                             pbp_line = f"  {details['description']}."

                    if pbp_line:
                        # Only show count if at bat is not over
                        is_last_pitch = p_event == play['playEvents'][-1]
                        is_ab_ending = play['result']['event'] in ["Walk", "Strikeout", "HBP"]
                        if not (is_last_pitch and is_ab_ending):
                            pbp_line += f" {count['balls'] + (1 if details['code'] == 'B' else 0)}-{count['strikes'] + (1 if details['isStrike'] else 0)}."
                        self._print(pbp_line)

            elif self.style == 'statcast':
                 for p_event in play['playEvents']:
                    details = p_event['details']
                    if details['code'] != 'X':
                        pitch_data = p_event.get('pitchData', {})
                        pitch_type = details.get('type', {}).get('description', 'pitch')
                        velo = pitch_data.get('startSpeed')
                        self._print(f"  {details['description']}: {velo} mph {pitch_type}")

            # Result of at-bat
            if self.style == 'statcast':
                self._print_statcast_result(play)
            elif self.style == 'narrative':
                self._print_narrative_result(play)

            score_str = f"{self.gameday_data['gameData']['teams']['home']['name']}: {play['result']['homeScore']}, {self.gameday_data['gameData']['teams']['away']['name']}: {play['result']['awayScore']}"
            if play['count']['outs'] < 3:
                self._print(f" | Outs: {play['count']['outs']} | Bases: {self._get_bases_str(play)} | Score: {score_str}\n")
            else:
                self._print(f" | Outs: {play['count']['outs']} | Score: {score_str}\n")

        # Game Over
        self._print("=" * 20 + " GAME OVER " + "=" * 20)
        final_score = self.gameday_data['liveData']['linescore']['teams']
        home_team = self.gameday_data['gameData']['teams']['home']
        away_team = self.gameday_data['gameData']['teams']['away']
        self._print(f"\nFinal Score: {home_team['name']} {final_score['home']['runs']} - {away_team['name']} {final_score['away']['runs']}")
        winner = home_team['name'] if final_score['home']['runs'] > final_score['away']['runs'] else away_team['name']
        self._print(f"\n{winner} win!")

        return "\n".join(self.output_lines)
