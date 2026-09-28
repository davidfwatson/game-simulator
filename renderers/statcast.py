from commentary import GAME_CONTEXT
from gameday import GamedayData
from .base import GameRenderer

class StatcastRenderer(GameRenderer):
    def render(self) -> str:
        self._reset_render_state()
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

        for play_idx, play in enumerate(plays):
            about = play['about']
            inning = about['inning']
            half = "Top" if about['isTopInning'] else "Bottom"

            self._reseed_for_point(play, "play_start", about.get('startTime', ''),
                                   f"play:{play_idx}:start")

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
            pitch_events = [event for event in play_events if event.get('isPitch', True)]
            last_pitch_event = pitch_events[-1] if pitch_events else {}
            for event_idx, event in enumerate(play_events):
                self._reseed_for_point(event, "event", event.get('startTime', ''),
                                       f"play:{play_idx}:event:{event_idx}")

                details = event['details']
                desc = details['description']
                if event.get('isPitch') is False:
                    lines.append(f"  Action: {desc}")
                    continue
                code = details.get('code', '')
                pitch_velo = event.get('pitchData', {}).get('startSpeed')
                pitch_selection = details.get('type', {}).get('description', 'pitch')
                is_bunt_pitch = event.get('isBunt', False) or 'bunt' in desc.casefold()

                outcome_text = ""
                if code == 'C': outcome_text = "called strike"
                elif code == 'P' or (code == 'B' and 'pitchout' in desc.casefold()): outcome_text = "pitchout"
                elif code == 'B': outcome_text = "ball"
                elif code == 'S': outcome_text = "missed bunt" if is_bunt_pitch else "swinging strike"
                elif code == 'F': outcome_text = "foul bunt" if is_bunt_pitch else "foul"
                elif code == 'X': outcome_text = "in play"

                if outcome_text:
                     lines.append(f"  {outcome_text.capitalize()}: {pitch_velo} mph {pitch_selection}")

            self._reseed_for_point(play, "play_outcome", about.get('endTime', ''),
                                   f"play:{play_idx}:outcome")

            result = play['result']
            outcome = result['event']
            if (outcome in ('Intent Walk', 'Intentional Walk')
                    or result.get('eventType') in ('intent_walk', 'intentional_walk')):
                outcome = 'Intentional Walk'
            batter_name = play['matchup']['batter']['fullName']

            x_event = next((e for e in pitch_events if e['details'].get('code') == 'X'), None)
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
            elif outcome == 'Intentional Walk':
                result_line = f"{batter_name} is intentionally walked."
            elif outcome == "Strikeout":
                destination = self._batter_safe_destination(play)
                last_details = last_pitch_event.get('details', {})
                last_code = last_details.get('code')
                is_bunt = last_pitch_event.get('isBunt', False) or 'bunt' in last_details.get('description', '').casefold()
                if destination == 'home':
                    result_line = f"{batter_name} strikes out but comes around to score."
                elif destination:
                    result_line = f"{batter_name} strikes out but reaches {destination} safely."
                elif is_bunt and last_code == 'F':
                    result_line = f"{batter_name} strikes out on a foul bunt."
                elif is_bunt and last_code == 'S':
                    result_line = f"{batter_name} strikes out on a missed bunt."
                else:
                    k_type = "looking" if last_code == 'C' else "swinging"
                    result_line = f"{batter_name} {self.rng_play.choice(GAME_CONTEXT['statcast_verbs']['Strikeout'][k_type])}."
            elif (outcome == 'Single' and x_event
                  and (x_event.get('isBunt') or str(x_event.get('hitData', {}).get('trajectory', '')).startswith('bunt'))):
                result_line = f"{batter_name} reaches on a bunt single."
            elif outcome in GAME_CONTEXT['statcast_verbs'] and outcome not in ['Flyout', 'Groundout']:
                cat = self._get_batted_ball_category(outcome, pitch_info.get('ev'), pitch_info.get('la'))
                phrase, phrase_type = self._get_batted_ball_verb(outcome, cat)
                if phrase_type == 'nouns':
                    phrase = f"hits {phrase}"
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
