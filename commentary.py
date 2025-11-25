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
            "back to the screen", "down the line, but wide of the bag", "spoils a good pitch",
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
            "  He tries to lay one down, but it rolls foul.",
            "  He attempts to bunt, but it goes foul.",
            "  He pulls back the bunt at the last second, but it's a foul."
        ],
        "bunt_sac": [
            "  He gets the bunt down, a perfect sacrifice.",
            "  A successful sacrifice bunt moves the runners.",
            "  He lays down the bunt, doing his job."
        ],
        "bunt_missed": [
            "  He offers at the bunt, but misses"
            "  He lays down the bunt, doing his job.",
            "  He bunts the runner over.",
            "  A well-placed bunt advances the runner."
        ],
        "fielding_error": [
            "  An error by {fielder_pos} {fielder_name} allows the batter to reach base.",
            "  {fielder_name} boots it at {fielder_pos}, and the batter is safe.",
            "  A misplay by {fielder_name} at {fielder_pos} leads to an error.",
            "  {fielder_name} can't handle it, and that'll be scored an error."
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
        "Forceout": {
            "verbs": { "default": ["reaches on a forceout"] },
            "nouns": { "default": ["a fielder's choice"] }
        },
        "Sac Fly": {
            "verbs": { "default": ["hits a sacrifice fly"] },
            "nouns": { "default": ["a sacrifice fly"] }
        },
        "Strikeout": {
            "swinging": ["strikes out swinging", "goes down on strikes", "goes down swinging", "takes a big cut and misses for strike three"],
            "looking": ["strikes out looking", "gets caught looking", "is frozen by a pitch right down the middle", "watches strike three go by"]
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
