import random

from gameday import GamedayData, Play, PlayEvent


class GamedayConverter:
    """
    Converts a Gameday JSON object into human-readable play-by-play formats.
    """
    GAME_CONTEXT = {
        "umpires": [
            "Chuck Thompson", "Larry Phillips", "Frank Rizzo", "Gus Morales", "Stan Friedman"
        ],
        "weather_conditions": [
            "75°F, Clear", "82°F, Sunny", "68°F, Overcast", "55°F, Drizzle", "72°F, Partly Cloudy, Wind 10 mph L to R"
        ],
        "pitch_locations": {
            "strike": [
                "paints the corner", "right down the middle", "catches the black",
                "a perfect strike", "in the zone", "freezes him on the inner edge",
                "snaps over the backdoor", "drops onto the knees", "called strike one",
                "called a strike", "in there for a called strike", "taken for a called strike"
            ],
            "ball": [
                "just misses outside", "high and tight", "in the dirt", "way outside",
                "low and away", "a bit inside", "sails over the letters",
                "spikes before the plate", "misses high and wide", "misses low and inside",
                "misses low", "misses outside", "runs high", "runs inside",
                "misses just a bit outside", "down and in"
            ],
            "foul": [
                "fights it off", "jams him inside", "gets a piece of it",
                "back to the screen", "down the line", "but wide of the bag", "spoils a good pitch",
                "back and out of play", "back and into the stands",
                "hammered into the stands", "dribbled along the first base line",
                "chopped on the first base line",
                "tapped down the first base line", "flied out of play"
            ]
        },
        "PITCH_TYPE_MAP": {
            "four-seam fastball": "FF",
            "sinker": "SI",
            "cutter": "FC",
            "slider": "SL",
            "changeup": "CH",
            "curveball": "CU",
            "knuckle curve": "KC"
        },
        "hit_directions": {
            "P": "back to the mound",
            "C": "in front of the plate",
            "1B": "to first",
            "2B": "to second",
            "3B": "to third",
            "SS": "to short",
            "LF": "to left",
            "CF": "to center",
            "RF": "to right"
        },
        "narrative_strings": {
            "strike_called": [
                "called strike one", "called a strike", "in there for a called strike",
                "taken for a called strike", "paints the corner for a strike", "catches the black"
            ],
            "strike_swinging": [
                "swung on and missed", "cut on and missed", "a big swing and a miss",
                "he hacks at it and misses", "comes up empty"
            ],
            "mound_visit": [
                "will stroll out to the mound to have a chat with",
                "the pitching coach heads to the mound for a word with",
                "time for a brief conference on the mound"
            ],
            "double_play": [
                "a 4-6-3 double play", "they turn two", "a tailor-made double play",
                "rolls it up for two"
            ],
            "leadoff_single": [
                "{batter_name} is aboard with a leadoff single.",
                "The inning starts with a base hit from {batter_name}.",
                "A leadoff single for {batter_name} to get things going."
            ],
            "leadoff_double": [
                "{batter_name} starts the inning with a stand-up double.",
                "A leadoff double for {batter_name}, and the offense is in business."
            ],
            "leadoff_walk": [
                "{batter_name} draws a leadoff walk.",
                "The inning begins with a four-pitch walk to {batter_name}."
            ],
            "two_out_single": [
                "{batter_name} keeps the inning alive with a two-out single.",
                "A two-out base hit for {batter_name}."
            ],
            "two_out_double": [
                "A two-out double for {batter_name}!",
                "{batter_name} rips one into the gap for a two-out double."
            ],
            "two_out_walk": [
                "{batter_name} extends the inning with a two-out walk."
            ],
            "runners_in_scoring_position": [
                "The tying run is on second.",
                "A big opportunity here with a runner in scoring position.",
                "The go-ahead run is at third."
            ],
            "infield_in": [
                "The infield is playing in, looking to cut down the run at the plate."
            ],
            "stolen_base": [
                "{runner_name} takes off for second... and he's in there with a stolen base!",
                "A good jump and a stolen base for {runner_name}."
            ],
            "stolen_base_third": [
                "{runner_name} takes off for third... and he makes it! A stolen base!",
                "He's going for third! And he's safe! {runner_name} with a great jump."
            ],
            "play_by_play_templates": [
                "{batter_name} {verb} {direction} on a {pitch_velo} mph {pitch_type}.",
                "A {pitch_velo} mph {pitch_type}, and {batter_name} {verb} {direction}.",
                "And the pitch... a {pitch_type} at {pitch_velo} mph, {batter_name} {verb} {direction}.",
                "{batter_name} gets a {pitch_type} and {verb} {direction}.",
            ],
            "play_by_play_noun_templates": [
                "It's a {pitch_type} and {batter_name} hits {noun} {direction}.",
                "It's a {pitch_type} and {batter_name} gets {noun} {direction}."
            ],
            "bunt_foul": [
                "  He squares to bunt, but fouls it off.",
                "  Showing bunt, he pushes it foul.",
                "  He tries to lay one down, but it rolls foul."
            ],
            "bunt_sac": [
                "  He gets the bunt down, a perfect sacrifice.",
                "  A successful sacrifice bunt moves the runners.",
                "  He lays down the bunt, doing his job."
            ],
            "bunt_missed": [
                "  He offers at the bunt, but misses"
            ]
        },
        "statcast_verbs": {
            "Sacrifice Bunt": {
                "verbs": {
                    "default": ["lays down a sacrifice bunt", "sacrifices"]
                },
                "nouns": {
                    "default": ["a sacrifice bunt"]
                }
            },
            "Bunt Ground Out": {
                "verbs": {
                    "default": ["bunts into a groundout", "grounds out on a bunt"]
                },
                "nouns": {
                    "default": ["a bunt, but it's an out"]
                }
            },
            "Single": {
                "verbs": {
                    "default": ["singles", "lines a clean single", "gets one to drop in"],
                    "bloop": ["singles on a bloop", "bloops one in"],
                    "liner": ["lines a single", "a sharp single", "lined sharply into the outfield"],
                    "grounder": ["grounds a single through the infield"]
                },
                "nouns": {
                    "default": ["a base hit", "a base knock"],
                    "bloop": ["a bloop single", "a little flare"],
                    "liner": ["a rope to the outfield"],
                    "grounder": ["a ground ball single", "a hard grounder that gets through"]
                }
            },
            "Double": {
                "verbs": {
                    "default": ["doubles", "hustles into second with a double"],
                    "liner": ["doubles on a line drive", "hammers one for two bases"],
                    "wall": ["doubles off the wall", "one-hops the wall for a double"]
                },
                "nouns": {
                    "default": ["a stand-up double"],
                    "liner": ["a ringing double into the gap"],
                    "wall": ["a double high off the wall"]
                }
            },
            "Triple": {
                "verbs": {
                    "default": ["triples", "races around to third with a triple"],
                    "gapper": ["hits one in the gap and cruises into third"]
                },
                "nouns": {
                    "default": ["a triple"],
                    "gapper": ["a triple into the alley"]
                }
            },
            "Home Run": {
                "verbs": {
                    "default": ["homers", "sails one over the wall"],
                    "screamer": ["homers on a liner", "a laser over the fence"],
                    "moonshot": ["homers on a fly ball", "hits one a mile in the air", "a high, majestic blast"]
                },
                "nouns": {
                    "default": ["a long home run", "a solo shot"],
                    "screamer": ["a line drive home run"],
                    "moonshot": ["a towering home run"]
                }
            },
            "Groundout": {
                "verbs": {
                    "default": ["grounds out"],
                    "soft": ["grounds out softly"],
                    "hard": ["grounds out sharply", "smokes one on the ground"]
                },
                "nouns": {
                    "default": ["a routine grounder", "a grounder", "a roller", "a bouncer", "a chopper", "a slow roller"],
                    "soft": ["a soft grounder", "a dribbler", "a weak tapper"],
                    "hard": ["a hard-hit grounder", "a one-hopper right at him"]
                }
            },
            "Flyout": {
                "verbs": {
                    "default": ["flies out"],
                    "deep": ["flies out deep", "drives him to the track, but he makes the catch"]
                },
                "nouns": {
                    "default": ["a routine fly ball", "a fly ball", "hit in the air", "a can of corn"],
                    "deep": ["a long fly ball", "a drive to the warning track"]
                }
            },
            "Pop Out": {
                "verbs": {"default": ["pops out"]},
                "nouns": {"default": ["an infield fly", "a high pop up"]}
            },
            "Lineout": {
                "verbs": {"default": ["lines out"]},
                "nouns": {"default": ["a hard line drive", "a screaming liner"]}
            },
            "Grounded Into DP": {
                "verbs": {"default": ["grounds into a double play"]},
                "nouns": {"default": ["a double play ball"]}
            },
            "Forceout": {
                "verbs": {"default": ["reaches on a forceout"]},
                "nouns": {"default": ["a fielder's choice"]}
            },
            "Sac Fly": {
                "verbs": {"default": ["hits a sacrifice fly"]},
                "nouns": {"default": ["a sacrifice fly"]}
            },
            "Strikeout": {
                "swinging": ["strikes out swinging", "down on strikes", "goes down swinging",
                            "a big cut and a miss for strike three"],
                "looking": ["strikes out looking", "caught looking", "frozen on a pitch right down the middle",
                            "watches strike three go by"]
            }
        },
        "statcast_templates": {
            "Single": ["{batter_name} {verb} {direction}."],
            "Double": ["{batter_name} {verb} {direction}."],
            "Triple": ["{batter_name} {verb} {direction}."],
            "Home Run": ["{batter_name} {verb} {direction}."],
            "Error": ["{display_outcome} {adv_str}."],
            "Flyout": ["{batter_name} {verb} {direction}."],
            "Pop Out": ["{batter_name} {verb} {direction}."],
            "Lineout": ["{batter_name} {verb} {direction}."],
            "Groundout": ["{batter_name} {verb} {direction}."],
            "Grounded Into DP": ["{batter_name} {verb}."],
            "Forceout": ["{batter_name} {verb}."],
            "Sac Fly": ["{batter_name} {verb} {direction}."],
            "Sac Bunt": ["{batter_name} {verb}."]
        }
    }

    def __init__(self, gameday_data: GamedayData, commentary_style='narrative', verbose_phrasing=True,
                 use_bracketed_ui=False, commentary_seed=None):
        self.gameday_data = gameday_data
        self.commentary_style = commentary_style
        self.verbose_phrasing = verbose_phrasing
        self.use_bracketed_ui = use_bracketed_ui
        self.commentary_rng = random.Random(commentary_seed)

        self.output_lines = []
        self.bases = [None, None, None]  # Track base state for commentary
        self.current_inning = 0
        self.current_half = ''

        # Game Info
        self.team1_data = self.gameday_data['gameData']['teams']['home']
        self.team2_data = self.gameday_data['gameData']['teams']['away']
        self.team1_name = self.team1_data["name"]
        self.team2_name = self.team2_data["name"]
        self.umpires = self.commentary_rng.sample(self.GAME_CONTEXT["umpires"], 4)
        self.weather = self.commentary_rng.choice(self.GAME_CONTEXT["weather_conditions"])
        self.venue = self.team1_data.get("venue", "Stadium") # Safely access venue

    def _print(self, text, end="\n"):
        """Buffer all output to print at the end."""
        if self.output_lines and end == "":
            self.output_lines[-1] += text
        else:
            self.output_lines.append(text)

    def _get_bases_str(self):
        if self.use_bracketed_ui:
            return f"[{'1B' if self.bases[0] else '_'}]-[{'2B' if self.bases[1] else '_'}]-[{'3B' if self.bases[2] else '_'}]"
        else:
            runners = []
            if self.bases[2]: runners.append(f"3B: {self.bases[2]['fullName']}")
            if self.bases[1]: runners.append(f"2B: {self.bases[1]['fullName']}")
            if self.bases[0]: runners.append(f"1B: {self.bases[0]['fullName']}")
            return ", ".join(runners) if runners else "Bases empty"

    def convert(self) -> str:
        """
        Main conversion function.
        """
        self._print_pre_game_summary()

        for play in self.gameday_data['liveData']['plays']['allPlays']:
            self._process_play(play)

        self._print_game_over_summary()
        return "\n".join(self.output_lines)

    def _process_play(self, play: Play):
        about = play['about']
        if about['inning'] != self.current_inning or about['halfInning'] != self.current_half:
            self.current_inning = about['inning']
            self.current_half = about['halfInning']
            is_home_team_batting = self.current_half == 'bottom'
            batting_team_name = self.team1_name if is_home_team_batting else self.team2_name
            inning_half = "Bottom" if is_home_team_batting else "Top"
            self._print("-" * 50)
            self._print(f"{inning_half} of Inning {self.current_inning} | {batting_team_name} batting")

        # Update base state from matchup
        self.bases = [
            play['matchup'].get('postOnFirst'),
            play['matchup'].get('postOnSecond'),
            play['matchup'].get('postOnThird')
        ]

        batter_name = play['matchup']['batter']['fullName']
        pre_play_outs = play['count']['outs'] - (1 if play['result']['event'] in ["Strikeout", "Groundout", "Flyout", "Lineout", "Pop Out", "Field Error"] else 0)


        outs_str = f"{pre_play_outs} out{'s' if pre_play_outs != 1 else ''}"
        bases_str = self._get_bases_str()
        situation = f"{outs_str}, {bases_str}" if bases_str != "Bases empty" else f"{outs_str}"
        self._print(f"\n{batter_name} steps to the plate. {situation}.")

        for event in play['playEvents']:
            self._process_pitch_event(event, play)

        result = play['result']
        self._print_play_result(result, batter_name)

        score_str = f"{self.team1_name}: {result['homeScore']}, {self.team2_name}: {result['awayScore']}"
        if play['count']['outs'] < 3:
            self._print(f" | Outs: {play['count']['outs']} | Bases: {self._get_bases_str()} | Score: {score_str}\n")
        else:
            self._print(f" | Outs: {play['count']['outs']} | Score: {score_str}\n")

    def _process_pitch_event(self, event: PlayEvent, play: Play):
        details = event['details']
        pitch_data = event.get('pitchData')
        pitch_type = details.get('type', {}).get('description', 'pitch')
        velo = pitch_data.get('startSpeed') if pitch_data else 'N/A'

        if self.commentary_style == 'narrative':
            description = details.get('description', 'Pitch')
            if "Called Strike" in description:
                pbp_line = f"  {self.commentary_rng.choice(self.GAME_CONTEXT['narrative_strings']['strike_called'])}."
            elif "Swinging Strike" in description:
                pbp_line = f"  {self.commentary_rng.choice(self.GAME_CONTEXT['narrative_strings']['strike_swinging'])}."
            elif "Foul" in description:
                pbp_line = f"  Foul, {self.commentary_rng.choice(self.GAME_CONTEXT['pitch_locations']['foul'])}."
            elif "Ball" in description:
                pbp_line = f"  {self.commentary_rng.choice(self.GAME_CONTEXT['pitch_locations']['ball'])}."
            else:
                pbp_line = f"  {description}."

            if self.verbose_phrasing:
                pbp_line += f" ({velo} mph {pitch_type})"
            if event['count']['balls'] < 4 and event['count']['strikes'] < 3:
                pbp_line += f" {event['count']['balls']}-{event['count']['strikes']}."
            self._print(pbp_line)
        elif self.commentary_style == 'statcast':
            self._print(f"  {details.get('description', 'Pitch')}: {velo} mph {pitch_type}")

    def _print_play_result(self, result, batter_name):
        event = result['event']
        if event == 'Walk':
             self._print(f"  {batter_name} draws a walk.", end="")
             return
        if event == 'Hit By Pitch':
            self._print(f"  {batter_name} is hit by the pitch.", end="")
            return
        if event == 'Field Error':
            self._print(f"  An error allows {batter_name} to reach base.", end="")
            return

        if self.commentary_style == 'narrative':
            template = self.commentary_rng.choice(self.GAME_CONTEXT['narrative_strings'].get('play_by_play_templates', []))
            if template:
                direction = self.commentary_rng.choice(list(self.GAME_CONTEXT['hit_directions'].values()))
                self._print(template.format(batter_name=batter_name, verb=event.lower(), direction=direction, pitch_velo="", pitch_type=""))
            else:
                self._print(f" Result: {event}", end="")
        elif self.commentary_style == 'statcast':
             self._print(f"Result: {result.get('description', '')}")

    def _print_pre_game_summary(self):
        self._print("=" * 20 + " GAME START " + "=" * 20)
        self._print(f"{self.team2_name} vs. {self.team1_name}")
        self._print(f"Venue: {self.venue}")
        self._print(f"Weather: {self.weather}")
        self._print(f"Umpires: HP: {self.umpires[0]}, 1B: {self.umpires[1]}, 2B: {self.umpires[2]}, 3B: {self.umpires[3]}")
        self._print("-" * 50)

    def _print_game_over_summary(self):
        self._print("=" * 20 + " GAME OVER " + "=" * 20)
        final_score = self.gameday_data['liveData']['linescore']['teams']
        team1_score = final_score['home']['runs']
        team2_score = final_score['away']['runs']
        self._print(f"\nFinal Score: {self.team1_name} {team1_score} - {self.team2_name} {team2_score}")
        winner = self.team1_name if team1_score > team2_score else self.team2_name
        self._print(f"\n{winner} win!")
