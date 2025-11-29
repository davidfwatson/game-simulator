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
            "snaps over the backdoor", "drops onto the knees",
            "called a strike", "in there for a called strike", "taken for a called strike",
            "called a strike on the inside corner"
        ],
        "ball": [
            "just misses outside", "high and tight", "in the dirt", "way outside",
            "low and away", "a bit inside", "sails over the letters",
            "spikes before the plate", "misses high and wide", "misses low and inside",
            "misses low", "misses outside", "runs high", "runs inside",
            "misses just a bit outside", "down and in",
            "misses low and outside"
        ],
        "foul": [
            "fights it off", "jams him inside", "gets a piece of it",
            "back to the screen", "down the line, but wide of the bag", "spoils a good pitch",
            "back and out of play", "back and into the stands",
            "hammered into the stands", "dribbled along the first base line",
            "chopped on the first base line",
            "tapped down the first base line", "flied out of play",
            "hammered foul and into the stands", "chopped foul on the first base line",
            "flied foul and out of play",
            "dribbled foul on the first base line"
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
    "narrative_templates": {
        "Single": {
            "liner": [
                "Lined {direction}. That one drops in.",
                "Lined into shallow {direction}, and that one will drop in for a base hit.",
                "Lined into shallow {direction}. That one drops in.",
                "Lined sharply into {direction}. That one will drop in for a base hit.",
                "Lined into the gap for a base hit.",
                "That one falls into the gap for a base hit."
            ],
            "bloop": [
                "Blooped {direction}. That one drops in for a hit.",
                "Blooped into shallow {direction}. That one drops in for a hit."
            ],
            "grounder": [
                "Hard grounder up the middle... and that one will squeeze through for a base hit.",
                "Hard grounder {direction}... and that one will squeeze through for a base hit."
            ],
            "default": [
                "Lined into shallow {direction}. That one drops in."
            ]
        },
        "Double": {
            "default": [
                 "Lined {direction}! That one is fair and that one will get all the way to the wall.",
                 "Hammered {direction}! That one will drop in for a hit and roll all the way to the wall.",
                 "That's going to be a stand-up double for {batter_name}."
            ]
        },
        "Home Run": {
             "default": [
                 "Hit in the air {direction}! {fielder_name} racing after it... he will not get there, as that one sails over the wall for a long, lazy home run!",
                 "Sails over the wall for a long, lazy home run!"
             ]
        },
        "Groundout": {
            "default": [
                "Roller {direction}. {fielder_name} scoops it up and fires to first.",
                "Slow roller {direction}. That will move the runner up.",
                "Dribbler {direction}. Backhanded pick by {fielder_name} and he fires to first.",
                "Grounder {direction}. {fielder_name} has it and tosses to first.",
                "Chopper {direction}. {fielder_name} is there and he fires to first.",
                "Hard grounder {direction}. {fielder_name} is up with it and tosses to first.",
                "Low roller {direction}.",
                "Chopper {direction}. {fielder_name}'s got it and he fires to first."
            ]
        },
        "Flyout": {
            "default": [
                "Hit in the air {direction}. {fielder_name} is after it and he makes the catch.",
                "Fly ball, {direction}. {fielder_name} drifting in... and he makes the catch.",
                "Fly ball, deep {direction}. {fielder_name} is racing after it... and he makes the catch on the warning track.",
                "Line drive {direction}. That one is into the glove of {fielder_name}.",
                "Fly ball, {direction}. {fielder_name} is camped under it, and he makes the catch.",
                "Popped up, {direction}. {fielder_name} is calling for it... and he makes the catch.",
                "High fly ball, {direction}... and that one is caught by {fielder_name}.",
                "{fielder_name} drifting in... and he makes the catch.",
                "{fielder_name} is camped under it, and he makes the catch.",
                "{fielder_name} calling for it... and he makes the catch.",
                "Routine play for {fielder_name}, and he makes the catch."
            ]
        },
        "Pop Out": {
             "default": [
                 "Popped up, {direction}. {fielder_name} is after it and he makes the catch.",
                 "Popped up on the infield. {fielder_name} is camped under it... and he makes the catch."
             ]
        },
        "Lineout": {
             "default": [
                 "Hard liner right into the glove of {fielder_name}."
             ]
        },
        "Strikeout": {
             "swinging": [
                 "Swing and a miss on a {pitch_type}, and {batter_name} strikes out.",
                 "He takes an awkward hack at a {pitch_type}, and {batter_name} strikes out.",
                 "Swing and a miss on a low {pitch_type}.",
                 "He takes an awkward hack at a {pitch_type} in the dirt.",
                 "Swing and a miss on a high {pitch_type}."
             ],
             "looking": [
                 "{batter_name} strikes out on a {pitch_type} to end the at-bat.",
                 "He looks at a {pitch_type} for a called strike three.",
                 "{pitch_type} called strike three."
             ]
        }
    },
    "narrative_strings": {
        "strike_called": [
            "called strike one", "called a strike", "in there for a called strike",
            "taken for a called strike", "paints the corner for a strike", "catches the black",
            "called a strike on the inside corner"
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
        "batter_intro_leadoff": [
            "And {batter_name} leads off for the {team_name}.",
            "And leading off for the {team_name}, {batter_name}.",
            "{batter_name} steps in to lead things off.",
            "And {batter_name} will step in at the top of the {team_name} order.",
            "And {batter_name} will lead off the inning."
        ],
        "batter_intro_empty": [
             "And {batter_name} will step in with {outs_str} and nobody on.",
             "And {batter_name} steps in with {outs_str} and the bases empty.",
             "And that will bring {batter_name} to the plate with {outs_str} and the bases empty.",
             "{batter_name} steps to the plate. {outs_str}, bases empty.",
             "And {batter_name} is due up. {outs_str}, bases empty.",
             "And {batter_name} will step in with {outs_str} and the bases empty."
        ],
        "batter_intro_runners": [
             "And {batter_name} steps in with {runners_str} with {outs_str}.",
             "{batter_name} comes to the plate. {runners_str} and {outs_str}.",
             "And that will bring up {batter_name} with {runners_str}.",
             "Runner on {runners_str}, {outs_str}, for {batter_name}.",
             "And {batter_name} will step in with {runners_str} with {outs_str}."
        ],
        "batter_matchup_handedness": [
            "Righty against righty.",
            "Righty against the lefty.",
            "Lefty against the lefty.",
            "Lefty against the righty."
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
                "default": ["singles", "lines a clean single", "gets one to drop in", "pokes a single", "rips a base hit"],
                "bloop": ["singles on a bloop", "bloops one in", "flares one", "muscles one", "fists one"],
                "liner": ["lines a single", "a sharp single", "lined sharply into the outfield", "lines one", "loops one", "drives a base hit"],
                "grounder": ["grounds a single through the infield", "squeezes a grounder through"]
            },
            "nouns": {
                "default": ["a base hit", "a base knock"],
                "bloop": ["a bloop single", "a little flare"],
                "liner": ["a rope to the outfield", "a sharp single that drops in"],
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
                "default": ["homers", "sails one over the wall", "goes yard", "deposits one in the seats"],
                "screamer": ["homers on a liner", "a laser over the fence"],
                "moonshot": ["homers on a fly ball", "hits one a mile in the air", "a high, majestic blast"]
            },
            "nouns": {
                "default": ["a long home run", "a solo shot"],
                "screamer": ["a line drive home run"],
                "moonshot": ["a towering home run", "a long, lazy home run"]
            }
        },
        "Groundout": {
            "verbs": {
                "default": ["grounds out", "bounces one", "taps one"],
                "soft": ["grounds out softly", "taps one", "dribbles one"],
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
                "default": ["flies out", "lifts a fly ball", "skies one"],
                "deep": ["flies out deep", "drives him to the track, but he makes the catch", "racing after it... and he makes the catch", "drifting in... and he makes the catch"]
            },
            "nouns": {
                "default": ["a routine fly ball", "a fly ball", "hit in the air", "a can of corn", "a high fly ball", "a lazy fly"],
                "deep": ["a long fly ball", "a drive to the warning track"]
            }
        },
        "Pop Out": {
            "verbs": { "default": ["pops out"] },
            "nouns": { "default": ["an infield fly", "a high pop up"] }
        },
        "Lineout": {
            "verbs": { "default": ["lines out"] },
            "nouns": { "default": ["a hard line drive", "a screaming liner"] }
        },
        "Grounded Into DP": {
            "verbs": { "default": ["grounds into a double play"] },
            "nouns": { "default": ["a double play ball"] }
        },
        "Double Play": {
            "verbs": { "default": ["grounds into a double play"] },
            "nouns": { "default": ["a double play ball"] }
        },
        "Forceout": {
            "verbs": { "default": ["reaches on a forceout"] },
            "nouns": { "default": ["a fielder's choice"] }
        },
        "Sac Fly": {
            "verbs": { "default": ["hits a sacrifice fly"] },
            "nouns": { "default": ["a sacrifice fly"] }
        },
        "Strikeout": {
            "swinging": ["strikes out swinging", "down on strikes", "goes down swinging", "a big cut and a miss for strike three", "swings through it for strike three", "is set down swinging"],
            "looking": ["strikes out looking", "caught looking", "frozen on a pitch right down the middle", "watches strike three go by", "knew it was a strike", "is rung up"]
        }
    },
    "statcast_templates": {
        "Single": [ "{batter_name} {verb} {direction}." ],
        "Double": [ "{batter_name} {verb} {direction}." ],
        "Triple": [ "{batter_name} {verb} {direction}." ],
        "Home Run": [ "{batter_name} {verb} {direction}." ],
        "Error": [ "{display_outcome} {adv_str}." ],
        "Flyout": [ "{batter_name} {verb} {direction}." ],
        "Pop Out": [ "{batter_name} {verb} {direction}." ],
        "Lineout": [ "{batter_name} {verb} {direction}." ],
        "Groundout": [ "{batter_name} {verb} {direction}." ],
        "Grounded Into DP": [ "{batter_name} {verb}." ],
        "Forceout": [ "{batter_name} {verb}." ],
        "Sac Fly": [ "{batter_name} {verb} {direction}." ],
        "Sac Bunt": [ "{batter_name} {verb}." ]
    }
}
