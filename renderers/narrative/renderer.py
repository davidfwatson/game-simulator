import random
from commentary import GAME_CONTEXT
from gameday import GamedayData
from ..base import GameRenderer
from .helpers import (
    get_ordinal, get_number_word, get_spoken_count,
    get_spoken_score_string, simplify_pitch_type, get_pitch_description_for_location
)

class NarrativeRenderer(GameRenderer):
    def __init__(self, gameday_data: GamedayData, seed: int = None, verbose: bool = True, use_bracketed_ui: bool = False):
        super().__init__(gameday_data, seed)
        self.verbose = verbose
        # use_bracketed_ui is ignored in new format as we don't print status lines
        self.last_foul_phrase = ""
        self.consecutive_fouls = 0

    def _check_and_add_delay(self, block_list, insert_at_index=-1, context='pitch'):
        DELAYS = {'batter': 11.5, 'first_pitch': 9.5, 'pitch': 8.5}
        delay = DELAYS.get(context)
        if delay is None:
            return
        delay_line = f"[TTS SPLIT HERE DELAY:{delay:.1f}s]"
        if insert_at_index >= 0:
            block_list.insert(insert_at_index, delay_line)
        else:
            block_list.append(delay_line)

    def _get_pitch_description_for_location(self, event_type, zone, pitch_type_simple, batter_hand='R'):
        return get_pitch_description_for_location(event_type, zone, pitch_type_simple, self.rng_pitch, batter_hand)

    def _get_foul_description(self):
        # On 2nd+ consecutive foul, chance to say "he fouls another one off"
        # TODO: To make this alignable via set-choice, refactor to use a small
        # pool (e.g. ["he fouls another one off", None]) instead of random() < 0.3
        if self.consecutive_fouls >= 1 and self.rng_pitch.random() < 0.3:
            self.last_foul_phrase = 'he fouls another one off'
            return 'he fouls another one off'

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
        count_str_and = self._get_spoken_count(balls, strikes, connector="and")
        pitcher_last = ' '.join(pitcher_name.split()[1:]) if pitcher_name and len(pitcher_name.split()) > 1 else (pitcher_name or "The pitcher")
        batter_last = batter_name.split()[-1] if batter_name else "the batter"

        context = {
            'count_str': count_str,
            'count_str_and': count_str_and,
            'count_str_cap': count_str.capitalize(),
            'count_str_and_cap': count_str_and.capitalize(),
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

    def _generate_play_description(self, outcome, hit_data, pitch_details, batter_name, fielder_pos=None, fielder_name=None, connector=None, result_outs=None, is_leadoff=False, inning_context="", play=None):
        from .play_description import generate_play_description as gpd
        return gpd(self, outcome, hit_data, pitch_details, batter_name, fielder_pos, fielder_name, connector, result_outs, is_leadoff, inning_context, play)

    def _render_steal_event(self, event):
        from .play_description import render_steal_event as rse
        return rse(self, event)

    def _get_runner_leads_line(self):
        """Return a 'runners take their leads' line if runners are on base, or None."""
        positions = []
        # Order: 3B, 2B, 1B (furthest first)
        for base, label in [('3B', 'third'), ('2B', 'second'), ('1B', 'first')]:
            if self.runners_on_base.get(base):
                runner_last = self.runners_on_base[base].split()[-1]
                positions.append(f"{runner_last} at {label}")
        if not positions:
            return None
        runner_positions = ", ".join(positions)
        if len(positions) == 1:
            templates = [
                "{runner_positions}.",
                "And {runner_positions}.",
            ]
        else:
            templates = GAME_CONTEXT['narrative_strings'].get('runner_leads', [
                "The runners take their leads, {runner_positions}.",
                "{runner_positions}.",
            ])
        return self.rng_flow.choice(templates).format(runner_positions=runner_positions)

    def _get_city_from_team(self, team_name):
        """Extract city from team name (e.g. 'Lake City Loons' -> 'Lake City')."""
        parts = team_name.split()
        if len(parts) > 1:
            return ' '.join(parts[:-1])
        return team_name

    def _get_short_team_name(self, team_dict):
        """Extract short team name (e.g. 'Cadillac Cars' -> 'Cars').

        Uses the teamName field if available, otherwise extracts the last word.
        """
        if isinstance(team_dict, dict) and 'teamName' in team_dict:
            return team_dict['teamName']
        name = team_dict if isinstance(team_dict, str) else team_dict.get('name', '')
        parts = name.split()
        return parts[-1] if parts else name

    def _get_innings_word(self, completed_innings, half):
        """Get phrase like 'one and a half', 'two', 'three and a half'."""
        num_word = self._get_number_word(completed_innings)
        if half == 'Bottom':
            return f"{num_word} and a half"
        return num_word

    def _get_due_up_desc(self, plays, play, batting_team_key):
        """Build 'the 2, 3, and 4 hitters' description from batting order."""
        boxscore = self.gameday_data['liveData'].get('boxscore', {})
        team_box = boxscore.get('teams', {}).get(batting_team_key, {})
        batting_order = team_box.get('battingOrder', [])
        if not batting_order:
            return "the next three hitters"

        batter_id = play['matchup']['batter']['id']
        try:
            idx = batting_order.index(batter_id)
        except ValueError:
            return "the next three hitters"

        spots = []
        for i in range(3):
            spot = (idx + i) % len(batting_order) + 1
            spots.append(str(spot))
        return f"the {', '.join(spots[:-1])}, and {spots[-1]} hitters"

    def _get_consecutive_retired(self):
        """Count consecutive batters retired across recent half-innings."""
        plays = self.gameday_data['liveData']['plays']['allPlays']
        count = 0
        for play in reversed(plays):
            result = play['result']['event']
            if result in ['Single', 'Double', 'Triple', 'Home Run', 'Walk', 'HBP',
                          'Hit By Pitch', 'Field Error', 'Sac Fly']:
                break
            if result in ['Strikeout', 'Groundout', 'Flyout', 'Pop Out', 'Lineout',
                          'Grounded Into DP', 'Double Play', 'Forceout',
                          'Sacrifice Bunt', 'Bunt Ground Out', 'Caught Stealing',
                          'Strikeout Double Play']:
                outs = play['count'].get('outs', 1)
                if result in ['Double Play', 'Grounded Into DP', 'Strikeout Double Play']:
                    count += 2
                else:
                    count += 1
            else:
                break
        return count

    def _get_half_inning_stats(self):
        """Get hits and LOB for the just-completed half-inning."""
        hits = 0
        lob = 0
        for p in self.plays_in_half_inning:
            event = p['result']['event']
            if event in ['Single', 'Double', 'Triple', 'Home Run']:
                hits += 1
            # Count runners left on base at end
        # LOB: runners on base at end of half-inning
        for base in ['1B', '2B', '3B']:
            if self.runners_on_base.get(base):
                lob += 1
        return hits, lob

    def _get_score_context_phrase(self, score_away, score_home):
        """Get a short score context like 'scoreless contest' or 'one-nothing lead'."""
        if score_away == 0 and score_home == 0:
            return "scoreless contest"
        if score_away == score_home:
            return f"tie game at {self._get_number_word(score_away)}"
        lead_team = self.away_team['name'] if score_away > score_home else self.home_team['name']
        return f"{lead_team} lead"

    def _get_natural_score_phrase(self, score_away, score_home):
        """Get a natural language score phrase for intros and recaps.

        Returns phrases like:
        - "a scoreless contest" / "still no score"
        - "tied at one"
        - "Cadillac leading one-nothing"
        - "Big Rapids leading two-to-one"
        """
        NUMBER_WORDS = {0: 'nothing', 1: 'one', 2: 'two', 3: 'three', 4: 'four',
                        5: 'five', 6: 'six', 7: 'seven', 8: 'eight', 9: 'nine',
                        10: 'ten', 11: 'eleven', 12: 'twelve'}

        def score_word(n):
            return NUMBER_WORDS.get(n, str(n))

        if score_away == 0 and score_home == 0:
            phrases = ["a scoreless contest", "still no score", "a scoreless ballgame",
                       "a scoreless game"]
            return self.rng_color.choice(phrases)

        if score_away == score_home:
            return f"tied at {score_word(score_away)}"

        if score_away > score_home:
            lead_team = self.away_team['name']
            lead_score = score_away
            trail_score = score_home
        else:
            lead_team = self.home_team['name']
            lead_score = max(score_away, score_home)
            trail_score = min(score_away, score_home)

        if trail_score == 0:
            return f"{lead_team} leading {score_word(lead_score)}-nothing"
        else:
            return f"{lead_team} leading {score_word(lead_score)}-to-{score_word(trail_score)}"

    def _get_batter_xfory(self, batter_id, batter_last_name):
        """Return X-for-Y aggregate recap like 'is one-for-three with a double in the fifth'."""
        history = self.batter_history.get(batter_id)
        if not history:
            return None

        HIT_EVENTS = {'Single', 'Double', 'Triple', 'Home Run'}
        AB_EVENTS = HIT_EVENTS | {'Groundout', 'Flyout', 'Strikeout', 'Pop Out',
                                   'Lineout', 'Double Play', 'Grounded Into DP',
                                   'Field Error', 'Forceout', 'Bunt Ground Out'}

        abs_count = sum(1 for e in history if e['event'] in AB_EVENTS)
        hits = [e for e in history if e['event'] in HIT_EVENTS]
        hits_count = len(hits)

        if abs_count == 0:
            return None

        NUMBER_WORDS = {0: '0', 1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five'}

        hits_word = NUMBER_WORDS.get(hits_count, str(hits_count))
        abs_word = NUMBER_WORDS.get(abs_count, str(abs_count))

        base = f"{batter_last_name} is {hits_word}-for-{abs_word} this evening"

        if hits_count > 0:
            # Check for pairs of same hit type
            from collections import Counter
            hit_types = Counter(e['event'] for e in hits)
            most_common_type, most_common_count = hit_types.most_common(1)[0]

            type_names = {'Single': 'single', 'Double': 'double', 'Triple': 'triple', 'Home Run': 'home run'}
            type_name = type_names.get(most_common_type, most_common_type.lower())

            if most_common_count >= 2:
                base += f". With a pair of {type_name}s"
                # Check for additional notable events (strikeouts)
                strikeouts = sum(1 for e in history if e['event'] == 'Strikeout')
                if strikeouts > 0:
                    base += f" and a strikeout"
                base += "."
            else:
                # Mention the most notable hit with inning
                notable = hits[-1]  # most recent hit
                ordinal = self._get_ordinal(notable['inning'])
                base += f" with a {type_name} in the {ordinal}."
        else:
            base += "."

        return base

    def _get_batter_recap(self, batter_id, batter_last_name, recap_gate, recap_format):
        """Return a sentence summarizing this batter's prior at-bats, or None.

        recap_gate (0-99): 0-69 = show recap, 70-99 = no recap
        recap_format (0-99): selects format when recap fires:
          0-29: X-for-Y aggregate format
          30-49: X-for-Y simple format
          50-74: event-verb format (legacy)
          75-99: event-verb with "in the Nth inning" variant
        """
        history = self.batter_history.get(batter_id)
        if not history:
            return None

        # X-for-Y formats
        if recap_format < 30:
            return self._get_batter_xfory(batter_id, batter_last_name)
        elif recap_format < 50:
            # Simple X-for-Y: "is 0-for-2 this evening"
            HIT_EVENTS = {'Single', 'Double', 'Triple', 'Home Run'}
            AB_EVENTS = HIT_EVENTS | {'Groundout', 'Flyout', 'Strikeout', 'Pop Out',
                                       'Lineout', 'Double Play', 'Grounded Into DP',
                                       'Field Error', 'Forceout', 'Bunt Ground Out'}
            abs_count = sum(1 for e in history if e['event'] in AB_EVENTS)
            hits_count = sum(1 for e in history if e['event'] in HIT_EVENTS)
            if abs_count == 0:
                return None
            NUMBER_WORDS = {0: '0', 1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five'}
            hits_word = NUMBER_WORDS.get(hits_count, str(hits_count))
            abs_word = NUMBER_WORDS.get(abs_count, str(abs_count))
            return f"{batter_last_name} is {hits_word}-for-{abs_word} this evening."

        # Event-verb formats (legacy behavior)
        variant = 0 if recap_format < 75 else 2  # 50-74 => "in the ordinal", 75-99 => "in the ordinal inning"

        EVENT_VERBS = {
            'Groundout': 'grounded out',
            'Flyout': 'flied out',
            'Strikeout': 'struck out',
            'Pop Out': 'popped out',
            'Lineout': 'lined out',
            'Single': 'had a base hit',
            'Double': 'had a double',
            'Triple': 'tripled',
            'Home Run': 'homered',
            'Walk': 'walked',
            'Double Play': 'grounded into a double play',
            'Grounded Into DP': 'grounded into a double play',
            'Hit By Pitch': 'was hit by a pitch',
            'HBP': 'was hit by a pitch',
            'Field Error': 'reached on an error',
            'Sac Fly': 'flied out',
            'Sacrifice Bunt': 'bunted',
            'Bunt Ground Out': 'bunted',
            'Forceout': 'grounded out',
        }

        def verb_for(entry):
            v = EVENT_VERBS.get(entry['event'], 'reached')
            if entry['scored'] and entry['event'] in ('Single', 'Double', 'Triple', 'Walk', 'Hit By Pitch', 'HBP', 'Field Error'):
                v += ' and scored a run'
            return v

        entries = history[-2:]  # use most recent 2 at most

        if len(entries) == 1:
            e = entries[0]
            v = verb_for(e)
            ordinal = self._get_ordinal(e['inning'])
            if len(history) == 1:
                if variant == 0:
                    return f"{batter_last_name} {v} in the {ordinal}."
                else:
                    return f"{batter_last_name} {v} in the {ordinal} inning."
            else:
                if variant == 0:
                    return f"{batter_last_name} {v} in the {ordinal}."
                else:
                    return f"{batter_last_name} {v} in the {ordinal} inning."

        # Two prior ABs
        e1, e2 = entries
        v1, v2 = verb_for(e1), verb_for(e2)
        return f"{batter_last_name} {v1} in the {self._get_ordinal(e1['inning'])} and {v2} in the {self._get_ordinal(e2['inning'])}."

    def _record_batter_history(self, play):
        """Record a batter's at-bat result for recap purposes."""
        batter_id = play['matchup']['batter']['id']
        event = play['result']['event']
        inning = play['about']['inning']

        # Check if batter scored on this play
        scored = False
        for r in play.get('runners', []):
            if r.get('details', {}).get('runner', {}).get('id') == batter_id:
                if r.get('movement', {}).get('end') == 'score':
                    scored = True
                    break

        if batter_id not in self.batter_history:
            self.batter_history[batter_id] = []
        self.batter_history[batter_id].append({
            'event': event,
            'inning': inning,
            'scored': scored,
        })

    def render(self) -> str:
        lines = []
        self._play_line_map = {}

        venue = self.gameday_data['gameData'].get('venue', 'the ballpark')

        def add_line(text):
            lines.append(text)


        broadcast = self.gameday_data['gameData'].get('broadcast', {})
        network_name = broadcast.get('network_name') or GAME_CONTEXT.get('network_name', 'The Pacific Coast Baseball Network')
        station_call = broadcast.get('station_call') or GAME_CONTEXT.get('station_call', 'KSLP')
        self._network_name = network_name
        self._station_call = station_call
        city = self.home_team.get('locationName') or self._get_city_from_team(self.home_team['name'])
        state = self.home_team.get('state', '')
        away_city = self.away_team.get('locationName') or self._get_city_from_team(self.away_team['name'])
        away_state = self.away_team.get('state', '')
        add_line(self._get_radio_string('station_intro', {'network_name': network_name}))
        welcome = self._get_radio_string('welcome_intro')
        # Build venue intro with city/state when available
        if state:
            venue_loc = f"{venue} in {city}, {state}"
        elif city:
            venue_loc = f"{venue} in {city}"
        else:
            venue_loc = venue
        if away_state:
            away_loc = f" of {away_city}, {away_state}"
        elif away_city:
            away_loc = f" of {away_city}"
        else:
            away_loc = ""
        add_line(f"Tonight, from {venue_loc}, it's the {self.home_team['name']} hosting the {self.away_team['name']}{away_loc}. {welcome}")

        weather = self.gameday_data['gameData'].get('weather')
        if weather:
             add_line(f"And it is a perfect night for a ball game: {weather}.")

        # STARTING LINEUPS
        if 'boxscore' in self.gameday_data['liveData']:
            boxscore = self.gameday_data['liveData']['boxscore']
            players_data = self.gameday_data['gameData'].get('players', {})
            lineup_strings = GAME_CONTEXT.get('lineup_strings', {})

            def get_position_str(pos_code, pos_name):
                """Person form: 'center fielder', 'third baseman'."""
                if pos_code == '1': return "starting pitcher"
                if pos_code == '2': return "catcher"
                if pos_code == '3': return "first baseman"
                if pos_code == '4': return "second baseman"
                if pos_code == '5': return "third baseman"
                if pos_code == '6': return "shortstop"
                if pos_code == '7': return "left fielder"
                if pos_code == '8': return "center fielder"
                if pos_code == '9': return "right fielder"
                if pos_code == 'D': return "designated hitter"
                return pos_name.lower()

            def get_position_place_str(pos_code, pos_name):
                """Place form: 'center field', 'third base'."""
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
                    # Away outro ("Those are the Bombers.") on its own line
                    away_name = self.away_team['name']
                    outro_templates = lineup_strings.get('outro_away', ["Those are the {away_team_name}."])
                    add_line(self.rng_color.choice(outro_templates).format(
                        away_team_name=away_name,
                        away_short=self._get_short_team_name(self.away_team)
                    ))
                    add_line("")  # blank line between teams
                    # Home intro on its own line
                    intro_template = self.rng_color.choice(lineup_strings.get('intro_home', ["Here are the {home_team_name}."]))
                    add_line(intro_template.format(away_team_name=away_name, home_team_name=self.home_team['name']))

                for idx, p_id in enumerate(batting_order):
                    player_key = f"ID{p_id}"
                    if player_key in players_data:
                        player = players_data[player_key]
                        p_name = player.get('fullName', 'Unknown Player')
                        pos_info = player.get('primaryPosition', {})
                        pos_code = pos_info.get('code', '')
                        pos_name = pos_info.get('name', '')
                        pos_str = get_position_str(pos_code, pos_name)
                        pos_place_str = get_position_place_str(pos_code, pos_name)

                        # Fetch the starting pitcher hand if they are batting 9th (or any DH/Pitcher)
                        pitch_hand = player.get('pitchHand', {}).get('description', 'Right').lower()

                        context = {
                            'team_name': team_name,
                            'player_name': p_name,
                            'position': pos_str,
                            'position_place': pos_place_str,
                            'pitch_hand': pitch_hand
                        }

                        # Get string for the specific batting position (1 through 9)
                        # Check for team-specific template first (e.g., batting_4_home)
                        batting_pos = idx + 1
                        team_specific_key = f'batting_{batting_pos}_{team_type}'
                        if team_specific_key in lineup_strings:
                            string_options = lineup_strings[team_specific_key]
                        else:
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

                        # Pitcher stats line (record/ERA) for starting pitchers in the 9th slot
                        if batting_pos == 9 and pos_code == '1':
                            player_data = players_data.get(player_key, {})
                            stats = player_data.get('stats', {}).get('pitching', {})
                            wins = stats.get('wins')
                            losses = stats.get('losses')
                            era = stats.get('era')
                            if wins is not None and losses is not None and era is not None:
                                last_name = p_name.split()[-1] if ' ' in p_name else p_name
                                add_line(f"{last_name} enters tonight's game with a record of {wins} and {losses} with a {era} ERA.")

                # Manager string
                team_data = self.gameday_data['gameData'].get('teams', {}).get(team_type, {})
                manager_name = team_data.get('manager', '')
                if not manager_name:
                    manager_name = "Mick Jenkins" if team_type == 'away' else "Manager Samuels"
                if team_type == 'away':
                    manager_templates = lineup_strings.get('manager_away', ["And the {team_name} are managed by {manager_name}."])
                else:
                    manager_templates = lineup_strings.get('manager_home', ["The {team_name} are managed by {manager_name}."])
                manager_template = self.rng_color.choice(manager_templates)
                add_line(manager_template.format(team_name=team_name, manager_name=manager_name))

            build_lineup('away')
            build_lineup('home')

        if self.rng_color.random() < 0.5:
            add_line(self._get_radio_string('pregame_color', {'venue': venue}))
        underway_options = [
            "And we are underway.",
            f"So, we are underway here at {venue}.",
            f"And we are underway here at {venue}.",
        ]
        add_line(self.rng_color.choice(underway_options))

        lines.append("") # Empty line

        current_inning_state = (0, '')
        self.last_play_inning = None
        self.outs_tracker = 0
        self.runners_on_base = {'1B': None, '2B': None, '3B': None}
        self.current_score = (0, 0)
        self._score_at_half_start = (0, 0)
        self.plays_in_half_inning = []
        self.batter_history = {}  # batter_id -> [{'event': str, 'inning': int, 'scored': bool}]

        plays = self.gameday_data['liveData']['plays']['allPlays']

        for play_idx, play in enumerate(plays):
            play_start_line = len(lines)
            about = play['about']
            matchup = play['matchup']
            inning = about['inning']
            half = "Top" if about['isTopInning'] else "Bottom"

            if 'startTime' in about:
                self._reseed_from_timestamp(about['startTime'], "play_start")

            # Capture recap value immediately after reseed, before inning
            # transitions consume color digits
            recap_val = self.rng_color.random()

            if (inning, half) != current_inning_state:
                if current_inning_state[0] != 0:
                     is_123 = False
                     # 1-2-3 inning: exactly 3 batters, all retired, no baserunners
                     total_outs = sum(
                         sum(1 for r in p['runners'] if r['movement']['isOut'])
                         for p in self.plays_in_half_inning
                     )
                     if len(self.plays_in_half_inning) == 3 and total_outs == 3:
                         is_123 = True
                         for p in self.plays_in_half_inning:
                             for r in p['runners']:
                                 if not r['movement']['isOut'] and r['movement'].get('end') in ['1B', '2B', '3B', 'score']:
                                     is_123 = False
                                     break
                             if not is_123: break

                     prev_half = current_inning_state[1]
                     pitching_team = 'home' if prev_half == 'Top' else 'away'
                     pitcher_name = ' '.join(self.current_pitcher_info[pitching_team]['name'].split()[1:]) if self.current_pitcher_info[pitching_team] and len(self.current_pitcher_info[pitching_team]['name'].split()) > 1 else "The pitcher"

                     score_away, score_home = self.current_score
                     completed_innings = inning - 1 if half == 'Top' else inning
                     prev_score_away, prev_score_home = getattr(self, '_score_at_half_start', (0, 0))
                     runs_scored_this_half = 0
                     if prev_half == 'Top':
                         runs_scored_this_half = score_away - prev_score_away
                     else:
                         runs_scored_this_half = score_home - prev_score_home

                     hits_in_inning, lob = self._get_half_inning_stats()
                     city = self.home_team.get('locationName') or self._get_city_from_team(self.home_team['name'])
                     state = self.home_team.get('state', '')
                     station_call = self._station_call
                     innings_word = self._get_innings_word(completed_innings, prev_half)
                     batting_team_prev = self.away_team['name'] if prev_half == 'Top' else self.home_team['name']
                     fielding_team_prev = self.home_team['name'] if prev_half == 'Top' else self.away_team['name']
                     next_pitcher_name = ' '.join(play['matchup']['pitcher']['fullName'].split()[1:])
                     next_batting_team_key = 'away' if about['isTopInning'] else 'home'
                     next_batting_team = self.away_team['name'] if about['isTopInning'] else self.home_team['name']
                     due_up_desc = self._get_due_up_desc(plays, play, next_batting_team_key)

                     runs_scored_word = self._get_number_word(runs_scored_this_half)
                     runs_scored_str = f"{runs_scored_word} run{'s' if runs_scored_this_half != 1 else ''}"
                     hits_str = f"{self._get_number_word(hits_in_inning)} hit{'s' if hits_in_inning != 1 else ''}" if hits_in_inning > 0 else "no hits"
                     lob_str = f"{'a man' if lob == 1 else self._get_number_word(lob) + ' men'} left" if lob > 0 else "nobody left"

                     # Score string for templates
                     if score_away == 0 and score_home == 0:
                         score_str = "No score"
                     elif score_away == score_home:
                         score_str = f"tied at {self._get_number_word(score_away)}"
                     else:
                         lead_team = self.away_team['name'] if score_away > score_home else self.home_team['name']
                         trail_team = self.home_team['name'] if score_away > score_home else self.away_team['name']
                         score_str = f"{lead_team} {max(score_away, score_home)}, {trail_team} {min(score_away, score_home)}"

                     weather_desc = "perfect night for a ball game"

                     away_short = self._get_short_team_name(self.away_team)
                     home_short = self._get_short_team_name(self.home_team)
                     batting_team_short = away_short if prev_half == 'Top' else home_short
                     fielding_team_short = home_short if prev_half == 'Top' else away_short
                     leading_short = away_short if score_away > score_home else home_short
                     trailing_short = home_short if score_away > score_home else away_short

                     ctx = {
                         'inning_ordinal': self._get_ordinal(completed_innings),
                         'inning_count_word': self._get_number_word(completed_innings),
                         'away_team_name': self.away_team['name'],
                         'home_team_name': self.home_team['name'],
                         'away_short': away_short,
                         'home_short': home_short,
                         'score_away': score_away,
                         'score_home': score_home,
                         'leading_team': self.away_team['name'] if score_away > score_home else self.home_team['name'],
                         'trailing_team': self.home_team['name'] if score_away > score_home else self.away_team['name'],
                         'leading_short': leading_short,
                         'trailing_short': trailing_short,
                         'score_lead': f"{max(score_away, score_home)}-{min(score_away, score_home)}",
                         'leading_score_val': max(score_away, score_home),
                         'score_trail': min(score_away, score_home),
                         'score': self._get_number_word(score_away) if score_away == score_home else score_away,
                         'city': city, 'state': state,
                         'venue': venue,
                         'innings_word': innings_word,
                         'batting_team': batting_team_prev,
                         'fielding_team': fielding_team_prev,
                         'batting_team_short': batting_team_short,
                         'fielding_team_short': fielding_team_short,
                         'pitcher_name': pitcher_name,
                         'hits_str': hits_str,
                         'lob_str': lob_str,
                         'runs_scored_word': runs_scored_word,
                         'runs_scored_str': runs_scored_str,
                         'score_str': score_str,
                         'score_recap': score_str,
                         'next_inning_ordinal': self._get_ordinal(inning) if half == 'Top' else self._get_ordinal(inning + 1),
                         'network_name': network_name,
                         'station_call': station_call,
                         'score_context': self._get_score_context_phrase(score_away, score_home),
                         'consecutive_retired': self._get_consecutive_retired()
                     }

                     summary_lines = []

                     # --- OUTRO: what happened in the half-inning ---
                     if is_123:
                         template = self.rng_flow.choice(GAME_CONTEXT['narrative_strings']['inning_end_123'])
                         summary_lines.append(template.format(pitcher_name=pitcher_name, inning_ordinal=self._get_ordinal(completed_innings)))
                     elif runs_scored_this_half == 0:
                         # Check for consecutive retired streak (impressive enough to mention)
                         consec = ctx['consecutive_retired']
                         if consec >= 9 and self.rng_flow.random() < 0.7:
                             summary_lines.append(self._get_radio_string('inning_outro_streak', ctx))
                         elif self.rng_flow.random() < 0.5:
                             # Pick situationally appropriate no-score outro
                             had_baserunners = hits_in_inning > 0 or lob > 0 or any(
                                 p['result']['event'] in ('Walk', 'Hit By Pitch', 'HBP', 'Field Error')
                                 for p in self.plays_in_half_inning
                             )
                             if is_123:
                                 summary_lines.append(self._get_radio_string('inning_outro_no_score_order', ctx))
                             elif had_baserunners and lob > 0:
                                 summary_lines.append(self._get_radio_string('inning_outro_no_score_jam', ctx))
                             else:
                                 summary_lines.append(self._get_radio_string('inning_outro_no_score', ctx))
                     else:
                         if self.rng_flow.random() < 0.5:
                             # Pick situationally appropriate scored outro
                             is_first_scoring = (prev_score_away == 0 and prev_score_home == 0)
                             was_already_leading = (
                                 (prev_half == 'Top' and prev_score_away > prev_score_home) or
                                 (prev_half != 'Top' and prev_score_home > prev_score_away)
                             )
                             if is_first_scoring:
                                 summary_lines.append(self._get_radio_string('inning_outro_scored_first', ctx))
                             elif runs_scored_this_half == 2:
                                 summary_lines.append(self._get_radio_string('inning_outro_scored_pair', ctx))
                             elif was_already_leading:
                                 summary_lines.append(self._get_radio_string('inning_outro_scored_extend', ctx))
                             else:
                                 summary_lines.append(self._get_radio_string('inning_outro_scored', ctx))

                     # --- SCORE SUMMARY ---
                     # Skip if outro already includes score info
                     outro_text_so_far = " ".join(summary_lines)
                     outro_mentions_score = (score_str.lower() in outro_text_so_far.lower()) or (f"{max(score_away, score_home)}" in outro_text_so_far and score_away != score_home)
                     skip_score_summary = outro_mentions_score
                     if not skip_score_summary:
                         if score_away == score_home:
                             if score_away == 0:
                                 summary_lines.append(self._get_radio_string('inning_summary_scoreless', ctx))
                             else:
                                 summary_lines.append(self._get_radio_string('inning_summary_tied', ctx))
                         elif half == 'Top' and completed_innings > 0:
                             summary_lines.append(self._get_radio_string('inning_summary_score', ctx))
                         elif runs_scored_this_half > 0:
                             # Score just changed this half, use active score report
                             summary_lines.append(self._get_radio_string('inning_summary_score', ctx))
                         else:
                             summary_lines.append(self._get_radio_string('inning_summary_remains', ctx))

                     # --- "WE'LL BE BACK" CLOSER ---
                     if half == 'Top':
                         # Full inning break (Bot→Top): use full closing with inning ordinal
                         summary_lines.append(self._get_radio_string('inning_break_outro', ctx))
                     else:
                         # Mid-inning break (Top→Bot): simpler closing without "next inning"
                         mid_closers = [
                             "We'll be back in a moment with more baseball here on {network_name}.",
                             "We'll be back with more baseball here on {network_name}.",
                             "We'll be back with more baseball here on {station_call}, and {network_name}.",
                             "We'll be back in a moment here on {station_call} and {network_name}."
                         ]
                         summary_lines.append(self.rng_color.choice(mid_closers).format(**ctx))

                     summary_text = " ".join(summary_lines)
                     lines.append(summary_text)
                     lines.append("")

                     # --- OPTIONAL COLOR / RETURN LINE ---
                     # "Wally McCarthy and Producer Phil back with you..." style return
                     if self.rng_color.random() < 0.15 and 3 <= inning <= 8:
                         intro_ctx = {
                             'venue': venue, 'city': city, 'state': state,
                             'score_str': score_str,
                             'weather_desc': weather_desc,
                             'batting_team': next_batting_team,
                             'due_up_desc': due_up_desc,
                             'pitcher_name': next_pitcher_name
                         }
                         return_line = self._get_radio_string('inning_break_return', intro_ctx)
                         lines.append(return_line)
                         lines.append("")

                     # Hardcoded 15s delay for inning break
                     lines.append("[TTS SPLIT HERE DELAY:15.0s]")

                     # --- INNING INTRO ---
                     score_phrase = self._get_natural_score_phrase(score_away, score_home)
                     next_batting_team_short = self._get_short_team_name(self.away_team) if about['isTopInning'] else self._get_short_team_name(self.home_team)
                     intro_ctx = {
                         'half': half, 'half_lower': half.lower(),
                         'inning_ordinal': self._get_ordinal(inning),
                         'venue': venue, 'city': city, 'state': state,
                         'score_str': score_str, 'score_context': self._get_score_context_phrase(score_away, score_home),
                         'score_phrase': score_phrase,
                         'batting_team': next_batting_team,
                         'batting_team_short': next_batting_team_short,
                         'due_up_desc': due_up_desc,
                         'pitcher_name': next_pitcher_name,
                         'weather_desc': weather_desc
                     }
                     if half == "Top":
                         add_line(self._get_radio_string('inning_break_intro_top', intro_ctx))
                     else:
                         add_line(self._get_radio_string('inning_break_intro_bottom', intro_ctx))
                     lines.append("")

                else:
                    # Skip "Top of the first inning." header — it's implicit from "we are underway"
                    if inning > 1 or half != 'Top':
                        # Rich header with score, venue, due-up info
                        score_away, score_home = self.current_score
                        score_phrase = self._get_natural_score_phrase(score_away, score_home)
                        next_pitcher_name = ' '.join(play['matchup']['pitcher']['fullName'].split()[1:])
                        next_batting_team_key = 'away' if about['isTopInning'] else 'home'
                        next_batting_team = self.away_team['name'] if about['isTopInning'] else self.home_team['name']
                        due_up_desc = self._get_due_up_desc(plays, play, next_batting_team_key)
                        next_batting_team_short = self._get_short_team_name(self.away_team) if about['isTopInning'] else self._get_short_team_name(self.home_team)
                        intro_ctx = {
                            'half': half, 'half_lower': half.lower(),
                            'inning_ordinal': self._get_ordinal(inning),
                            'venue': venue, 'city': city, 'state': state,
                            'score_phrase': score_phrase,
                            'score_str': f"It's {score_phrase}",
                            'score_context': self._get_score_context_phrase(score_away, score_home),
                            'batting_team': next_batting_team,
                            'batting_team_short': next_batting_team_short,
                            'due_up_desc': due_up_desc,
                            'pitcher_name': next_pitcher_name,
                            'weather_desc': "perfect night for a ball game"
                        }
                        if half == "Top":
                            add_line(self._get_radio_string('inning_break_intro_top', intro_ctx))
                        else:
                            add_line(self._get_radio_string('inning_break_intro_bottom', intro_ctx))
                        lines.append("")

                # Track score at start of new half-inning
                self._score_at_half_start = self.current_score

                self.plays_in_half_inning = []
                self.runners_on_base = {'1B': None, '2B': None, '3B': None}
                self._prev_matchup_key = None

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
            prev_play_event = plays[play_idx - 1]['result'].get('event', '') if play_idx > 0 else ''
            prev_same_half = (play_idx > 0 and
                              plays[play_idx - 1]['about'].get('inning') == inning and
                              plays[play_idx - 1]['about'].get('isTopInning') == about['isTopInning'])
            bases_just_cleared = (prev_same_half and prev_play_event == 'Home Run'
                                  and len(runners) == 0 and self.outs_tracker > 0)
            if len(runners) == 0:
                if self.outs_tracker == 0:
                     intro_template = self.rng_flow.choice(GAME_CONTEXT['narrative_strings']['batter_intro_leadoff'])
                elif bases_just_cleared:
                     intro_template = self.rng_flow.choice(GAME_CONTEXT['narrative_strings'].get('batter_intro_bases_cleared', GAME_CONTEXT['narrative_strings']['batter_intro_empty']))
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

            # Append prior at-bat recap after batter intro
            # recap_val was captured right after reseed (before inning transitions)
            # Call 0 (recap_val): gate (0-69 = recap, 70-99 = no recap)
            # Call 1 (recap_format_val): format selection when recap fires
            batter_id = matchup['batter']['id']
            batter_last_name = batter_name.split()[-1]
            recap_format_val = self.rng_color.random()
            recap_score_context_val = self.rng_flow.random()
            if recap_val < 0.7:
                recap_gate = int(recap_val * 100)
                recap_format = int(recap_format_val * 100)
                recap = self._get_batter_recap(batter_id, batter_last_name, recap_gate, recap_format)
                if recap:
                    # Optionally append score context (~40% chance)
                    if recap_score_context_val < 0.4:
                        score_away, score_home = self.current_score
                        score_phrase = self._get_natural_score_phrase(score_away, score_home)
                        ordinal = self._get_ordinal(inning)
                        recap += f" {half} of the {ordinal}, {score_phrase}."
                    play_text_blocks.append(recap)

            if self.rng_color.random() < 0.2:
                 bat_side_orig = matchup['batSide']['code']
                 bat_side = bat_side_orig
                 pitch_hand = matchup['pitchHand']['code']
                 if bat_side == 'S': bat_side = 'R' if pitch_hand == 'L' else 'L'
                 matchup_txt = ""
                 if bat_side_orig == 'S':
                     effective = 'left' if bat_side == 'L' else 'right'
                     pitcher_name = self.current_pitcher_info[pitching_team_key]['name']
                     pitcher_last = pitcher_name.split()[-1] if ' ' in pitcher_name else pitcher_name
                     matchup_txt = f"{batter_last_name} is a switch hitter and he'll bat {effective} against {pitcher_last}."
                 elif bat_side == 'R' and pitch_hand == 'R':
                     matchup_options = ["a righty-righty matchup.", "righty against righty."]
                     if getattr(self, '_prev_matchup_key', None) == 'RR':
                         matchup_options.append("another righty-righty matchup.")
                     matchup_txt = self.rng_color.choice(matchup_options)
                 elif bat_side == 'R' and pitch_hand == 'L':
                     matchup_options = ["a righty-lefty matchup.", "righty against the lefty."]
                     matchup_txt = self.rng_color.choice(matchup_options)
                 elif bat_side == 'L' and pitch_hand == 'R':
                     matchup_options = ["a lefty-righty matchup.", "lefty against the righty."]
                     matchup_txt = self.rng_color.choice(matchup_options)
                 elif bat_side == 'L' and pitch_hand == 'L':
                     matchup_options = ["a lefty-lefty matchup.", "lefty against the lefty."]
                     matchup_txt = self.rng_color.choice(matchup_options)
                 self._prev_matchup_key = f"{bat_side}{pitch_hand}"

                 if matchup_txt:
                     if play_text_blocks:
                         play_text_blocks[-1] += " " + matchup_txt
                     else:
                         play_text_blocks.append(matchup_txt)

            result = play['result']
            outcome = result['event']
            play_events = play['playEvents']
            last_pitch_context = None
            i = 0
            x_event_connector = None
            self.consecutive_fouls = 0

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

                # TTS delay markers between pitches/batters
                if i == 0:
                    # 11.5s before batter intro (between at-bats)
                    self._check_and_add_delay(play_text_blocks, insert_at_index=0, context='batter')
                    # 9.5s after batter intro, before first pitch
                    self._check_and_add_delay(play_text_blocks, context='first_pitch')
                else:
                    # 8.5s between pitches
                    self._check_and_add_delay(play_text_blocks, context='pitch')

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
                        self.consecutive_fouls += 1
                    elif code == 'C':
                         if event['count']['strikes'] == 2:
                             key = 'strike_called_three'
                             pbp_line = f"{pitch_type}, {self._get_narrative_string(key, rng=self.rng_pitch)}"
                         else:
                             # Use strike-numbered pools based on resulting strike count
                             strikes_before = event['count']['strikes']
                             if strikes_before == 0:
                                 key = 'strike_called_one'
                             else:
                                 key = 'strike_called_two'
                             pbp_line = f"{pitch_type}, {self._get_narrative_string(key, rng=self.rng_pitch)}"

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

                    # Reset consecutive foul counter on non-foul events
                    if code in ('B', 'C', 'S'):
                        self.consecutive_fouls = 0

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

                            reaches_full = (b == 3 and s == 2 and
                                            not (event['count']['balls'] == 3 and event['count']['strikes'] == 2))

                            if not suppress_count:
                                if reaches_full and self.rng_flow.random() < 0.4:
                                    full_str = self.rng_flow.choice(GAME_CONTEXT['narrative_strings']['count_full'])
                                    if use_comma:
                                        full_str = full_str.lstrip(", ")
                                        pbp_line += f" {full_str}."
                                    else:
                                        clean = full_str.strip(", ")
                                        clean = clean[0].upper() + clean[1:]
                                        pbp_line += f" {clean}."
                                elif repeating_two_strikes:
                                    # Use special "count holds at..." logic
                                    count_hold_str = self._get_narrative_string('count_remains_two_strikes', {'count_str': spoken_count, 'batter_name': batter_name}, rng=self.rng_flow)
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

                        if is_steal_attempt:
                            steal_txt = self._render_steal_event(steal_event)
                            play_text_blocks.append(steal_txt)
                            i += 1

                        # Optionally insert runner-status line between pitches
                        if not is_steal_attempt and any(self.runners_on_base.values()):
                            is_final_pitch = (event == play_events[-1])
                            if not is_final_pitch and i > 1 and self.rng_flow.random() < 0.20:
                                leads_line = self._get_runner_leads_line()
                                if leads_line:
                                    play_text_blocks.append(leads_line)
                else:
                    if code != 'X':
                         txt = f"{desc}."
                         play_text_blocks.append(txt)

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

            elif outcome == "Caught Stealing" or ("Caught Stealing" in outcome and "Single" in outcome):
                 # Handle combined "Caught Stealing 2B / Single" outcomes
                 if "Single" in outcome:
                     x_event = next((e for e in play_events if e['details'].get('code') == 'X'), None)
                     if x_event:
                         hit_data = x_event.get('hitData', {})
                         pitch_details = {'type': x_event['details'].get('type', {}).get('description', 'pitch'), 'velo': x_event.get('pitchData', {}).get('startSpeed')}
                         ordinal = self._get_ordinal(inning)
                         inning_context = f" here in the {half.lower()} of the {ordinal}"
                         is_leadoff = (len(self.plays_in_half_inning) == 0)
                         single_text = self._generate_play_description("Single", hit_data, pitch_details, batter_name, connector=x_event_connector, is_leadoff=is_leadoff, inning_context=inning_context)
                         if single_text:
                             outcome_text = single_text
                     runner_out = next((r for r in play['runners'] if r['movement']['isOut']), None)
                     if runner_out:
                         ob = runner_out['movement']['outBase']
                         base_name = "second" if ob == "2B" else "third" if ob == "3B" else "home"
                         cs_text = f"{runner_out['details']['runner']['fullName']} is caught stealing {base_name}!"
                         if outcome_text:
                             outcome_text += "\n" + cs_text
                         else:
                             outcome_text = cs_text
                 else:
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
                    if not primary_credit and out_credits:
                        primary_credit = out_credits[0]

                    if primary_credit:
                        # Get position from credit if available, else from player data
                        if 'position' in primary_credit:
                            fielder_pos = primary_credit['position']['abbreviation']
                        else:
                            player_id = f"ID{primary_credit['player']['id']}"
                            player_data = self.gameday_data.get('gameData', {}).get('players', {}).get(player_id, {})
                            fielder_pos = player_data.get('primaryPosition', {}).get('abbreviation')
                        # Get fielder name (use lastName to handle multi-word names like "Del Greco")
                        player_id = f"ID{primary_credit['player']['id']}"
                        player_data = self.gameday_data.get('gameData', {}).get('players', {}).get(player_id, {})
                        fielder_name = player_data.get('lastName', '')
                        if not fielder_name:
                            if 'fullName' in primary_credit.get('player', {}):
                                fielder_name = primary_credit['player']['fullName'].split()[-1]
                            else:
                                fielder_name = player_data.get('fullName', 'the fielder').split()[-1]

                    ordinal = self._get_ordinal(inning)
                    inning_context = f" here in the {half.lower()} of the {ordinal}"
                    is_leadoff = (len(self.plays_in_half_inning) == 0)

                    outcome_text = self._generate_play_description(outcome, hit_data, pitch_details, batter_name, fielder_pos, fielder_name, connector=x_event_connector, result_outs=play['count']['outs'], is_leadoff=is_leadoff, inning_context=inning_context, play=play)

            if outcome_text:
                 play_text_blocks.append(outcome_text)

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

                lead_team_short = self._get_short_team_name(self.away_team) if new_away > new_home else self._get_short_team_name(self.home_team)
                ctx = {
                    'team_name': lead_team,
                    'team_name_short': lead_team_short,
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
            self._record_batter_history(play)

            # Join play blocks: group non-TTS content between TTS delays
            # into single continuous lines (radio broadcast style)
            collapsed = []
            current_group = []
            for block in play_text_blocks:
                if block.startswith("[TTS SPLIT"):
                    if current_group:
                        collapsed.append(" ".join(current_group))
                        current_group = []
                    collapsed.append(block)
                else:
                    current_group.append(block)
            if current_group:
                collapsed.append(" ".join(current_group))

            lines.append("\n".join(collapsed))
            lines.append("")
            self._play_line_map[play_idx] = (play_start_line, len(lines))

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
            'network_name': getattr(self, '_network_name', GAME_CONTEXT.get('network_name', 'The Pacific Coast Baseball Network'))
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
