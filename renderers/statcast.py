from commentary import GAME_CONTEXT
from gameday import GamedayData
from .base import GameRenderer

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

            if 'startTime' in about:
                self._reseed_from_timestamp(about['startTime'], "play_start")

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
                if 'startTime' in event:
                    self._reseed_from_timestamp(event['startTime'], "event")

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

            if 'endTime' in about:
                self._reseed_from_timestamp(about['endTime'], "play_outcome")

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
