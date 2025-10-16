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
            "taken for a called strike"
        ],
        "strike_swinging": [
            "swung on and missed", "cut on and missed"
        ],
        "mound_visit": [
            "will stroll out to the mound to have a chat with"
        ],
        "double_play": [
            "a 4-6-3 double play"
        ]
    },
    "statcast_verbs": {
        "Single": {
            "default": ["singles", "lines a clean single", "a base hit"],
            "bloop": ["singles on a bloop", "a bloop single", "bloops one"],
            "liner": ["lines a single", "a sharp single", "lined sharply"],
            "grounder": ["grounds a single", "a ground ball single", "hard grounder"]
        },
        "Double": {
            "default": ["doubles", "a stand-up double"],
            "liner": ["doubles on a line drive", "a ringing double", "hammered"],
            "wall": ["doubles off the wall", "a double high off the wall", "lined"]
        },
        "Triple": {
            "default": ["triples", "a triple"]
        },
        "Home Run": {
            "default": ["homers", "a long home run", "sails one over the wall"],
            "screamer": ["homers on a liner", "a line drive home run"],
            "moonshot": ["homers on a fly ball", "a towering home run", "hits one in the air"]
        },
        "Groundout": {
            "default": ["grounds out", "a routine grounder", "a grounder", "a roller", "a bouncer", "a dribbler", "a chopper", "a slow roller"],
            "soft": ["grounds out softly", "a soft grounder"],
            "hard": ["grounds out sharply", "a hard-hit grounder"]
        },
        "Flyout": {
            "default": ["flies out", "a routine fly ball", "a fly ball", "hit in the air"],
            "popup": ["pops out", "an infield fly", "a high pop up", "popped up"],
            "deep": ["flies out deep", "a long fly ball"]
        },
        "Strikeout": {
            "swinging": ["strikes out swinging", "down on strikes", "swing and a miss on a curveball in the dirt", "takes an awkward hack at a slider in the dirt", "swing and a miss on a low curve", "swing and a miss on a high heater"],
            "looking": ["strikes out looking", "caught looking", "looks at a fastball for a called strike three"]
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
