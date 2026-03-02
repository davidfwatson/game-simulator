import re

with open("renderers.py", "r") as f:
    content = f.read()

# NarrativeRenderer updates
narrative_search_1 = """            if (inning, half) != current_inning_state:
                if current_inning_state[0] != 0:"""
narrative_replace_1 = """            if 'startTime' in about:
                self._reseed_from_timestamp(about['startTime'], "play_start")

            if (inning, half) != current_inning_state:
                if current_inning_state[0] != 0:"""

narrative_search_2 = """            while i < len(play_events):
                event = play_events[i]

                # Timing check"""
narrative_replace_2 = """            while i < len(play_events):
                event = play_events[i]

                if 'startTime' in event:
                    self._reseed_from_timestamp(event['startTime'], "event")

                # Timing check"""

narrative_search_3 = """            outcome_text = ""
            if outcome == "Strikeout":"""
narrative_replace_3 = """            if 'endTime' in about:
                self._reseed_from_timestamp(about['endTime'], "play_outcome")

            outcome_text = ""
            if outcome == "Strikeout":"""

content = content.replace(narrative_search_1, narrative_replace_1)
content = content.replace(narrative_search_2, narrative_replace_2)
content = content.replace(narrative_search_3, narrative_replace_3)

# StatcastRenderer updates
statcast_search_1 = """            if (inning, half) != current_inning_state:
                team_name = self.away_team['name'] if about['isTopInning'] else self.home_team['name']"""
statcast_replace_1 = """            if 'startTime' in about:
                self._reseed_from_timestamp(about['startTime'], "play_start")

            if (inning, half) != current_inning_state:
                team_name = self.away_team['name'] if about['isTopInning'] else self.home_team['name']"""

statcast_search_2 = """            play_events = play['playEvents']
            for event in play_events:
                details = event['details']"""
statcast_replace_2 = """            play_events = play['playEvents']
            for event in play_events:
                if 'startTime' in event:
                    self._reseed_from_timestamp(event['startTime'], "event")

                details = event['details']"""

statcast_search_3 = """            result = play['result']
            outcome = result['event']
            batter_name = play['matchup']['batter']['fullName']"""
statcast_replace_3 = """            if 'endTime' in about:
                self._reseed_from_timestamp(about['endTime'], "play_outcome")

            result = play['result']
            outcome = result['event']
            batter_name = play['matchup']['batter']['fullName']"""

content = content.replace(statcast_search_1, statcast_replace_1)
content = content.replace(statcast_search_2, statcast_replace_2)
content = content.replace(statcast_search_3, statcast_replace_3)

with open("renderers.py", "w") as f:
    f.write(content)
