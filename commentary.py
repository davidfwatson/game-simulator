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
            "spikes before the plate", "misses high and the", "misses low and inside",
            "misses low", "misses outside", "runs high", "runs inside",
            "misses just a bit outside", "down and in"
        ],
        "foul": [
            "fights it off", "jams him inside", "gets a piece of it",
            "back to the screen", "down the line, foul", "spoils a good pitch",
            "fouled back and out of play", "fouled back and into the stands",
            "hammered foul and into the stands", "dribbled foul on the first base line",
            "chopped foul on the first base line",
            "tapped down the first base line", "flied foul and out of play"
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
        ]
    },
    "statcast_verbs": {
        "Single": {
            "default": ["singles", "lines a clean single", "a base hit", "gets one to drop in", "a base knock"],
            "bloop": ["singles on a bloop", "a bloop single", "bloops one in", "a little flare"],
            "liner": ["lines a single", "a sharp single", "lined sharply into the outfield", "a rope to the outfield"],
            "grounder": ["grounds a single through the infield", "a ground ball single", "a hard grounder that gets through"]
        },
        "Double": {
            "default": ["doubles", "a stand-up double", "hustles into second with a double"],
            "liner": ["doubles on a line drive", "a ringing double into the gap", "hammers one for two bases"],
            "wall": ["doubles off the wall", "a double high off the wall", "one-hops the wall for a double"]
        },
        "Triple": {
            "default": ["triples", "a triple", "races around to third with a triple"],
            "gapper": ["hits one in the gap and cruises into third", "a triple into the alley"]
        },
        "Home Run": {
            "default": ["homers", "a long home run", "sails one over the wall", "a solo shot"],
            "screamer": ["homers on a liner", "a line drive home run", "a laser over the fence"],
            "moonshot": ["homers on a fly ball", "a towering home run", "hits one a mile in the air", "a high, majestic blast"]
        },
        "Groundout": {
            "default": ["grounds out", "a routine grounder", "a grounder", "a roller", "a bouncer", "a chopper", "a slow roller"],
            "soft": ["grounds out softly", "a soft grounder", "a dribbler", "a weak tapper"],
            "hard": ["grounds out sharply", "a hard-hit grounder", "a one-hopper right at him", "smokes one on the ground"]
        },
        "Flyout": {
            "default": ["flies out", "a routine fly ball", "a fly ball", "hit in the air", "a can of corn", "lines out"],
            "popup": ["pops out", "an infield fly", "a high pop up", "popped up on the infield"],
            "deep": ["flies out deep", "a long fly ball to the warning track", "drives him to the track, but he makes the catch"]
        },
        "Strikeout": {
            "swinging": ["strikes out swinging", "down on strikes", "swing and a miss", "a big cut and a miss for strike three"],
            "looking": ["strikes out looking", "caught looking", "frozen on a pitch right down the middle", "watches strike three go by"]
        }
    },
    "statcast_templates": {
        "Single": [
            "{batter_name} {verb} {direction}."
        ],
        "Double": [
            "{batter_name} {verb} {direction}."
        ],
        "Triple": [
            "{batter_name} {verb} {direction}."
        ],
        "Home Run": [
            "{batter_name} {verb} {direction}."
        ],
        "Error": [
            "{display_outcome} {adv_str}."
        ],
        "Flyout": [
            "{batter_name} {verb} {direction}."
        ],
        "Groundout": [
            "{batter_name} {verb} {direction}."
        ]
    }
}
