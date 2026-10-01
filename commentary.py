"""Commentary phrase pools shared by renderers and fixture alignment tools.

Keep phrases within the facts supplied by their category; a generic pool should
not invent a pitch location, runner, fielding play, or scoring situation.
Verb pools contain present-tense predicates that can follow a batter's name;
noun pools contain noun phrases that can follow "hits" or "gets". Location
descriptions omit the pitch type because the renderer supplies it separately.
"""

GAME_CONTEXT = {
    "network_name": "The Pacific Sleep Baseball Network",
    "station_call": "KSLP",
    "umpires": [
        "Chuck Thompson", "Larry Phillips", "Frank Rizzo", "Gus Morales", "Stan Friedman",
        "Bill Miller", "Dan Bellino", "Chris Guccione", "Mark Carlson", "Paul Emmel"
    ],
    "weather_conditions": [
        "75°F, Clear", "82°F, Sunny", "68°F, Overcast", "55°F, Drizzle", "72°F, Partly Cloudy, Wind 10 mph L to R",
        "65°F, Fog rolling in", "70°F, Clear skies over Pacifica", "62°F, Cool breeze", "85°F, Santa Ana winds blowing out", "58°F, Misty night at the ballpark"
    ],
    "pitch_locations": {
        "strike": {
            "outside_corner": ["called a strike on the outside corner",
                "a called strike that nibbles the outside corner",
            ],
            "inside_corner": ["called a strike on the inside corner"],
            "corner": ["paints the corner for a called strike", "catches the corner",
                "hits the corner for a called strike",
                "just kisses the corner for a called strike",
                "nibbles the corner for a called strike",
                "called strike on the corner",
                "paints the black for a called strike",
            ],
            "middle": ["right down the middle for a called strike", "right down Main Street",
                "down the middle for a called strike",
                "right down Main Street for a strike",
                "right down the middle for a strike",
            ],
            "low": ["at the knees for a called strike", "called a strike down low",
                "at the knees, called a strike",
                "called a strike at the knees",
            ],
            "default": [
                "paints the corner", "right down the middle", "catches the black",
                "a perfect strike", "in the zone", "freezes him on the inner edge",
                "snaps over the backdoor", "drops onto the knees",
                "called a strike", "in there for a called strike", "taken for a called strike",
                "called a strike on the inside corner", "called strike", "a strike",
                "paints the corner for a called strike",
                "right down Main Street",
                "caught the corner",
                "in at the knees for a called strike",
                "called a strike on the corner"
            ]
        },
        "ball": {
            "high": ["misses high", "upstairs", "high for a ball",
                "high",
                "very high",
                "just barely high",
            ],
            "low": ["misses low", "downstairs", "low for a ball",
                "just a bit low",
                "low",
                "misses very low",
                "misses down low",
                "runs low",
                "misses just a bit low",
                "taken low",
            ],
            "inside": ["misses inside", "runs inside", "inside for a ball",
                "inside",
                "way inside",
                "just inside",
                "inside, that almost hit him",
                "runs just inside",
                "just misses inside",
                "off the inside",
            ],
            "outside": ["misses outside", "outside for a ball", "off the plate",
                "outside",
                "just a bit outside",
                "just outside",
                "floats outside",
                "misses on the outside corner",
                "runs outside",
                "misses wide",
                "hanging outside",
            ],
            "dirt": ["in the dirt", "bounces in the dirt in front of the plate",
                "in the dirt in front of the plate",
                "bounces in the dirt",
            ],
            "default": [
                "just misses outside", "high and tight", "in the dirt", "way outside",
                "low and away", "a bit inside", "sails over the letters",
                "spikes before the plate", "misses high and wide", "misses low and inside",
                "misses low", "misses outside", "runs high", "runs inside",
                "misses just a bit outside", "down and in",
                "misses low and outside",
                "misses upstairs",
                "misses low and inside", "misses down and in",
                "misses high",
                "misses a bit low",
                "runs a bit low",
                "just off the plate",
                "misses away",
                "high and inside",
                "he bounces one in the dirt",
                "gets away from him and that one misses way outside"
            ],
            "high_inside": [
                "high and tight",
                "high and inside",
                "runs high",
                "misses high",
                "misses upstairs",
                "up in the eyes",
                "over the head",
                "way upstairs",
                "runs inside",
                "a bit inside",
                "nearly hits him",
                "brushes him back",
                "misses up and in",
                "up and in",
                "misses very high",
                "just a touch high",
                "misses just inside",
                "runs high and inside",
                "inside, that one buzzed his tower",
            ],
            "high_outside": [
                "sails over the letters",
                "misses high and wide",
                "runs high",
                "misses upstairs",
                "misses high",
                "up in the eyes",
                "way upstairs",
                "just misses outside",
                "way outside",
                "misses outside",
                "misses just a bit outside",
                "just off the plate",
                "misses away",
                "wide",
                "gets away from him and that one misses way outside",
                "misses just outside",
                "misses very high",
                "misses way outside",
                "taken up and away",
                "just misses a bit outside",
                "misses up and away",
            ],
            "low_inside": [
                "misses low and inside",
                "down and in",
                "misses low",
                "misses a bit low",
                "runs a bit low",
                "in the dirt",
                "bounced in the dirt",
                "runs inside",
                "a bit inside",
                "misses down and in",
                "he bounces one in the dirt",
                "down low",
                "low and inside",
                "just misses low",
                "bounces in the dirt in front of the plate",
                "misses downstairs",
                "downstairs",
                "bounces in front of the plate",
                "runs low and inside",
            ],
            "low_outside": [
                "low and away",
                "spikes before the plate",
                "misses low and outside",
                "misses low",
                "misses a bit low",
                "runs a bit low",
                "in the dirt",
                "bounced in the dirt",
                "just misses outside",
                "way outside",
                "misses outside",
                "misses just a bit outside",
                "just off the plate",
                "misses away",
                "wide",
                "away",
                "down and away",
                "just misses low",
                "misses low and away",
                "low and outside",
                "runs wide",
                "off the plate",
                "off the outside corner",
                "just off the corner",
                "misses down and away",
            ],
            "unlocated": [
                "misses for a ball",
                "is taken for a ball",
                "is called a ball"
            ],
        },
        "foul": [
            "fights it off",
            "he spoils a good pitch",
            "he gets a piece of it",
            "he fouls it off",
            "fouled back",
            "fouled back to the screen",
            "fouled back and out of play",
            "fouled back and into the stands",
            "hammered foul",
            "hammered foul and into the stands",
            "hammered foul and out of play",
            "lined foul",
            "hit foul down the line",
            "fouled down the line",
            "chopped foul",
            "chopped foul and out of play",
            "chopped foul down the first base line",
            "chopped foul and off to the right",
            "chopped foul off to the right",
            "chopped foul and off to the left",
            "dribbled foul down the first base line",
            "tapped foul down the line",
            "lifted foul and out of play",
            "popped foul and out of play",
            "knuckles foul and lands into the stands",
            "just gets a piece of it",
            "fouled away",
            "sent foul and out of play",
            "he fouls that one off",
            "slashed out of play",
            "fisted foul and out of play",
            "hammered foul down the line",
            "hammered foul off third",
            "hammered foul down the third base line",
            "swung on and fouled off",
            "fouled up to the left",
            "fouled off to the left",
            "high foul ball drifting into the stands",
            "foul",
            "slashed foul and out of play",
            "slashed foul into the stands",
            "slashed foul off to the right",
            "skied foul and out of play",
            "skied foul and into the stands",
            "flied foul and out of play",
            "hooked foul down the left field line",
            "lifted foul off third",
            "popped foul off first and into the stands",
            "that one stroked foul down the first base line",
            "fouled off to the right and out of play",
            "chopped softly foul on the first-base line",
            "fouled down the left field line and into the stands",
            "and he smacks that one foul off first",
            "dribbled foul down the third base line",
            "sliced foul down the third base line",
            "popped up into foul territory, and that one will knuckle into the stands",
            "smashed foul into the stands",
            "hammered foul on the first base line",
            "pulled foul and out of play",
            "slashed foul past third base",
            "fisted foul off to the right",
            "ripped foul down the third base line",
            "chopper, foul down the third base line",
            "sliced foul right side",
            "smashed foul down the right field line",
            "that one is knuckling foul and out of play",
            "he slaps one sharply foul and out of play",
            "he fouls one off",
            "slapped foul",
            "he pops that one up, foul, out of play",
            "he slaps that one foul out of play",
            "he smacks that one, foul, out of play",
            "smacked foul, down the third base line",
            "hit sharply, foul",
            "it's a foul out of play",
            "fouled off, out of play",
            "slapped foul, out of play",
            "smacked foul and out of play",
            "fouled off and out of play",
            "that's popped up, foul and out of play",
            "line foul",
            "he slices that one foul, out of play",
            "a long foul ball",
            "tapped foul",
            "chopped foul, went out of play",
            "that's fouled back",
            "line foul down the first base line",
            "fouled off, just got a piece of it",
            "chopped foul down the third-base line",
            "chopped foul past third",
            "chopped foul on the first-base line",
            "fouled back, out of play",
            "chopped foul on the third-base line",
            "hammered foul into the stands",
            "dribbled foul on the third-base line",
            "hammered foul on the left field line and into the stands",
            "foul down the right field line",
            "chopper foul down the first base line",
            "hammered foul down the left field line",
            "chopper foul on the third base line",
            "chopper foul",
            "hammered foul down the first base line",
            "hammered foul on the third base line",
            "he fouls that one back and into the stands",
            "fouled back, into the stands",
            "hammered foul on the first base side",
            "hooked foul and into the stands",
            "slapped foul down the third base line",
            "skied foul, out of play",
            "hammered foul, out of play",
            "fouled off to the right",
            "bouncer foul off to the right",
            "that one's fouled back and out of play",
            "grounded foul",
            "tapped foul off to the right",
            "foul down the first base line",
            "fouled straight back and out of play",
            "hammered foul off to the left",
            "hammered foul off to the right",
            "slashed foul down the first base line",
            "fouled back into the seats",
            "slashed foul, out of play",
            "slashed foul off to the left",
            "ripped foul down the first base line",
            "ripped foul down the right field line and out of play",
            "hammered foul down the right field line",
            "foul back to the screen",
            "foul back and out of play",
            "fisted foul off to the left",
            "dribbled foul off to the right",
            "bouncer foul down the first base line",
            "foul back, out of play",
            "chopped foul down third",
            "fisted foul, out of play",
            "chopped foul off third",
            "that one's fouled back into the seats",
            "sliced foul and into the stands",
            "chopped foul down the left field line",
            "hammered foul, landed into the seats",
            "hammered foul back to the screen",
            "slashed foul off third",
            "bounced foul towards the dugout",
            "fisted foul off third",
            "he fouls that one down the first-base line",
            "that one's fouled off",
            "he takes a monster swing at that one; it's a foul out of play",
            "swing and a foul back",
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
        "LF": "to left field",
        "CF": "to center field",
        "RF": "to right field",
        "MI": "up the middle",
        "RS": "through the right side",
        "LS": "through the left side",
        "SL": "into shallow left",
        "SC": "into shallow center",
        "SR": "into shallow right",
        "RC": "into the right-center gap",
        "LC": "into the left-center gap",
        "DL": "down the line",
        "DLF": "to deep left field",
        "DCF": "to deep center field",
        "DRF": "to deep right field",
        "LCF": "to left-center",
        "RCF": "to right-center",
        "1BL": "down the first base line",
        "3BL": "down the third base line"
    },
    "unlocated_contact": {
        "Single": ["A base hit for {batter_name}.", "And that's a base hit.", "{batter_name} is aboard with a single."],
        "Double": ["{batter_name} has a double.", "And that's a double for {batter_name}.", "{batter_name} is in safely at second with a double."],
        "Triple": ["{batter_name} has a triple.", "And {batter_name} makes it to third with a triple."],
        "Home Run": ["That one is gone! A home run for {batter_name}.", "{batter_name} hits a home run.", "And that's a home run for {batter_name}."],
        "Groundout": ["{batter_name} grounds out {out_context_str}.", "A ground ball out {out_context_str}."],
        "Flyout": ["{batter_name} flies out {out_context_str}.", "That one is caught {out_context_str}."],
        "Pop Out": ["{batter_name} pops out {out_context_str}.", "The pop fly is caught {out_context_str}."],
        "Lineout": ["{batter_name} lines out {out_context_str}.", "A line drive, caught {out_context_str}."],
        "Double Play": ["And that's a double play.", "They turn two. A double play."],
        "Forceout": ["They get the forceout.", "A runner is forced out."],
        "Fielders Choice": ["{batter_name} reaches on a fielder's choice."],
        "Sacrifice Bunt": ["{batter_name} lays down a sacrifice bunt."],
        "Sac Fly": ["{batter_name} hits a sacrifice fly."]
    },
    "narrative_templates": {
        "Single": {
            "ground_ball": [
                "On the ground {direction}. A base hit for {batter_name}.",
                "Ground ball {direction}, and {batter_name} reaches safely.",
                "A grounder {direction}. And that's a base hit."
            ],
            "line_drive": [
                "Lined {direction}. A base hit for {batter_name}.",
                "A line drive {direction}, and {batter_name} is aboard."
            ],
            "fly_ball": [
                "Hit in the air {direction}, and that one drops in for a hit.",
                "A fly ball {direction}. And that's a base hit."
            ],
            "soft_liner": [
                "A soft liner over the head of a leaping {fielder_name}.",
                "Softly lined {direction}. That one drops in for a base hit.",
                "A soft line drive {direction}, and that one falls in.",
                "Lined softly into the gap for a base hit.",
            ],
            "bunt": [
                "Bunted along {direction_noun}. {fielder_name} is in. And he will not have a play on that perfectly executed bunt.",
                "{batter_name} lays down a bunt, perfectly executed for a bunt single.",
                "Bunted towards {direction_noun}, {fielder_name} racing in, and he will not have a play.",
                "{batter_name} lays down a bunt, and he is going to be safe at first.",
                "{batter_name} lays down a bunt. That is a base hit. It was just a textbook bunt.",
            ],
            "liner": [
                "Lined {direction}. That one drops in.",
                "Lined {direction}, and that one will drop in for a base hit.",
                "Lined {direction}. That one drops in.",
                "Lined sharply {direction}. That one will drop in for a base hit.",
                "Lined into the gap for a base hit.",
                "That one falls into the gap for a base hit.",
                "A sharp line drive {direction}, and that's a base hit.",
                "Ripped {direction} for a single.",
                "Lined into shallow {direction_noun}. That one drops in.",
                "Lined sharply into {direction_noun}.",
                "Line drive, {direction_noun}.",
                "Lined into shallow {direction_noun}, and that one will drop in.",
                "Lined into shallow {direction_noun}. That one drops in.",
                "Hard liner {direction}. And that one drops in for a base hit.",
                "Hammered {direction}. And that one drops in."
            ],
            "bloop": [
                "Fly ball into shallow {direction_noun}. And that one drops in front of {fielder_name}.",
                "Blooped {direction}. That one drops in for a hit.",
                "Blooped {direction}. That one drops in for a hit.",
                "A little flare {direction} falls in.",
                "Blooped into shallow {direction_noun}. That one drops in for a hit.",
                "Blooped into shallow {direction_noun}. That one drops in for a hit.",
                "Looper into shallow {direction_noun}. And that one falls in for a base hit.",
                "Hit in the air to shallow {direction_noun}. And that one will drop in for a hit.",
                "Poked into shallow {direction_noun}. And that one lands in front of {fielder_name}.",
                "Flared into shallow {direction_noun}. And that one drops in for a hit.",
                "And that's a little looper into shallow {direction_noun}, and that one falls in for a base hit.",
                "And {batter_name} reaches out and slaps that one into the gap for a base hit.",
                "Looper into shallow {direction_noun}, and that one drops into the gap for a base hit.",
                "Hit in the air to shallow {direction_noun}. {fielder_name} is racing in, and he will not make the catch, as that one drops in.",
            ],
            "grounder": [
                "Hard grounder up the middle... and that one will squeeze through for a base hit.",
                "Hard grounder {direction}... and that one will squeeze through for a base hit.",
                "Finds a hole through the infield.",
                "Seeing-eye single {direction}.",
                "Hard grounder through the hole.",
                "Hard grounder {direction}. And that one gets through the infield for a base hit.",
                "Hard grounder {direction}. Past a diving {fielder_name}.",
                "Hard grounder {direction}. And that one squeaks through the infield for a base hit.",
                "Chopped through the hole. And that one will skip into {direction_noun} for a base hit.",
                "Just a little squibber that squeaked through the infield.",
                "Bounced off the plate {direction}. {fielder_name} will not get there.",
                "Hit on the ground, and that one will squeak through the infield.",
                "Grounder {direction}, and that one squeaks through the infield.",
                "Hard grounder {direction}, and that one skips through the infield for a base hit.",
                "Tough play for {fielder_name}. The throw is not in time.",
                "And {batter_name} hits a little smash {direction} for a base hit.",
                "A bouncer that squeaks through the infield. That's a base hit for {batter_name}.",
                "Grounded {direction} and through the infield for a base hit.",
                "A little squibber that will squeak through the infield for a base hit.",
                "A dribbler that will squeak past {fielder_name} for a base hit.",
                "Grounder {direction}, and that's a seeing-eye single for {batter_name}.",
            ],
            "default": [
                "Lined {direction}. That one drops in.",
                "Lined {direction}. That one drops in.",
                "Base hit {direction}.",
                "Lined into shallow {direction_noun}, and that one will drop in.",
                "Line drive, {direction_noun}.",
                "That one drops in.",
                "Hit {direction}. And that one falls in for a base hit.",
                "Line into shallow {direction_noun}. And that one falls in for a base hit.",
                "Tapped into shallow {direction_noun}. And that one drops in for a base hit.",
                "That one finds the hole {direction}, and that's a base hit for {batter_name}.",
            ],
            "infield_knockdown": [
                "Hard grounder {direction}. {fielder_name} is able to knock it down, but he will not have a play."
            ],
            "throwing_error": [
                "Grounder {direction}. The throw to first sails over the bag, and {batter_name} will scoot up to second base safely."
            ],
        },
        "Double": {
            "default": [
                "Lined {direction}! That one is fair and that one will get all the way to the wall.",
                "Hammered {direction}! That one will drop in for a hit and roll all the way to the wall.",
                "Hammered to {direction_noun}! That one will drop in for a hit and roll all the way to the wall.",
                "Sliced down the {direction_noun} line. That one falls in for a hit, and that one will roll all the way into the corner.",
                "Pulled into {direction_noun}. That one's going to fall in. And that's going to roll all the way to the wall.",
                "Driven {direction}, and that will be good for two bases.",
                "A base hit {direction}. {batter_name} is on his way to second with a double.",
                "Hit {direction}, and {batter_name} makes it into second with a double.",
                "Lifted to {direction_noun}. That one will drop in for a hit, and it'll roll all the way to the wall.",
                "Hit into deep {direction_noun}. That one drops in and bounces off the wall.",
                "Driven {direction}. {fielder_name} will have to play that one off the wall. That's going to be a double for {batter_name}.",
                "Belted {direction}. {fielder_name} hustling after it, and that will fall in for a base hit and roll into the corner.",
                "Ripped into the gap, and that will roll all the way to the wall.",
                "Hit {direction}, and that one will end up all the way in the corner.",
                "Ripped {direction}. {fielder_name} racing back, and that one is going to bounce off the wall.",
                "That one is fair, and past a diving {fielder_name}. It will roll into the outfield, and {batter_name} will be aboard with a stand-up double.",
                "Ripped {direction}. That one drops in and bounces all the way to the wall.",
                "Hit in the air {direction}, still going back, and that one ricochets off the top of the wall.",
            ],
            "ground_rule": [
                "Hammered {direction}, and that will bounce over the wall. That's a ground-rule double for {batter_name}."
            ],
            "lost_in_lights": [
                "Hit in the air {direction}. {fielder_name} will lose that one in the lights, and that one falls in. {batter_name} heads for second with a double."
            ],
            "walkoff": [
                "That one will bounce off the wall, and that will drive in the winning run."
            ],
        },
        "Triple": {
             "default": [
                 "Hit deep into the gap! {batter_name} racing around second... and he's in safely at third with a triple.",
                 "A drive into the gap! {batter_name} on his way to third... and he slides in safely.",
                 "Driven {direction}. {batter_name} is around second and into third with a triple.",
                 "A drive {direction}! {batter_name} keeps running, and he makes it to third with a triple.",
                 "That will be three bases for {batter_name}, who makes it safely into third.",
                 "{batter_name} is going to turn on the gas, and he will end up at third base.",
                 "That one is crushed {direction}, all the way to the wall. {batter_name} is heading for third, and that's a triple.",
                 "{batter_name} rounding second. He's thinking three. And he is going to beat the throw.",
                 "Blooper {direction}. That one falls in, and that will roll all the way into the corner. {batter_name} makes it safely to third.",
             ]
        },
        "Home Run": {
             "default": [
                 "Hit in the air {direction}! {fielder_name} racing after it... he will not get there, as that one sails over the wall for a long, lazy home run!",
                 "Sails over the wall for a long, lazy home run!",
                 "Hit in the air {direction}! {fielder_name} racing after it... he will not get there!",
                 "Deep fly ball {direction}... back, back... gone! A home run for {batter_name}!",
                 "High fly ball {direction}... and that one is gone!",
                 "Swung on, a high drive deep to {direction_noun}, and that one is going to sail over the wall.",
                 "Hit in the air to deep {direction_noun}. {fielder_name} racing back, and he'll run out of room as that one sails over the wall.",
                 "And {batter_name} gets all of that one, sailing leisurely over the wall.",
                 "That one is crushed {direction}, still going back, and that's over the wall.",
                 "And that's going to be a no doubter, way back and over the wall.",
                 "And {batter_name} gets all of that one. That's a long, lazy home run.",
                 "Hit in the air {direction}. That's trouble — {fielder_name} racing back, and he will run out of room, and that one sails over the wall.",
             ],
            "walkoff": [
                "Way back and over the wall. That's a walk-off home run for {batter_name}."
            ],
        },
        "Groundout": {
            "default": [
                "Roller {direction}. {fielder_name} scoops it up and fires to first {out_context_str}.",
                "Dribbler {direction}. Backhanded pick by {fielder_name} and he fires to first {out_context_str}.",
                "Grounder {direction}. {fielder_name} has it and tosses to first {out_context_str}.",
                "Chopper {direction}. {fielder_name} is there and he fires to first {out_context_str}.",
                "Hard grounder {direction}. {fielder_name} is up with it and tosses to first {out_context_str}.",
                "Low roller {direction}. {fielder_name} fields it and throws to first {out_context_str}.",
                "Chopper {direction}. {fielder_name}'s got it and he fires to first {out_context_str}.",
                "Routine play for {fielder_name} and he flips to first {out_context_str}.",
                "Grounded to {fielder_name}, who fields it cleanly and throws to first {out_context_str}.",
                "Sent on the ground {direction}. {fielder_name} up with it, over to first {out_context_str}.",
                "Chopped {direction}. {fielder_name} charges and throws to first {out_context_str}.",
                "Bouncer {direction}. {fielder_name} gloves it and fires to first {out_context_str}.",
                "Grounder {direction}. {fielder_name} backhands it and fires to first {out_context_str}.",
                "Roller to {direction_noun}. {fielder_name} scoops it up and fires to first {out_context_str}.",
                "Hard grounder to {direction_noun}. {fielder_name} is up with it and he fires to first {out_context_str}.",
                "Dribbler to {direction_noun}. Backhanded pick by {fielder_name} and he fires to first in time {out_context_str}.",
                "Hard grounder up the middle... {fielder_name} is there and he fires to first {out_context_str}.",
                "{fielder_name} gloves it and fires to first to retire {batter_name} {out_context_str}.",
                "Routine play for {fielder_name} and he flips to first to retire {batter_name} {out_context_str}.",
                "{fielder_name} scoops it up and fires to first to retire {batter_name} {out_context_str}.",
                "Roller {direction}. {fielder_name} scoops it up and fires to first to retire {batter_name} {out_context_str}.",
                "Roller to {direction_noun}. {fielder_name} scoops it up and fires to first to retire {batter_name} {out_context_str}.",
                "Dribbler to {direction_noun}. Backhanded pick by {fielder_name} and he fires to first to retire {batter_name} {out_context_str}.",
                "{fielder_name} has it and tosses to first to retire {batter_name} {out_context_str}.",
                "Chopper {direction}. {fielder_name} gobbles it up and fires to first {out_context_str}.",
                "One hopper to {fielder_name}, he has it and throws to first {out_context_str}.",
                "Hard grounder to {direction_noun}, smothered by {fielder_name} and he fires to first {out_context_str}.",
                "Hard chopper to {direction_noun}. {fielder_name} snares it and fires to first {out_context_str}.",
                "Slow roller to {direction_noun}. {fielder_name} picks it up and fires to first {out_context_str}.",
                "Bouncer to {direction_noun}. {fielder_name} gloves it and flips to first {out_context_str}.",
                "Hard chopper to {direction_noun}. {fielder_name} snares it and fires to first to get {batter_name} by a step {out_context_str}.",
                "Bouncer to {direction_noun}. Routine play for {fielder_name}. And he scoops it up and flips to first to retire {batter_name} {out_context_str}.",
                "Grounder to {direction_noun}. {fielder_name} has it and tosses over to first to retire {batter_name} {out_context_str}.",
                "Chopper to {direction_noun}. {fielder_name} picks it up and fires to first in time to retire {batter_name} {out_context_str}.",
                "Roller to {direction_noun}. {fielder_name} has it, and fires across to first to get {batter_name} {out_context_str}.",
                "Grounder to {direction_noun}. {fielder_name} is up with it and he tosses to first to retire {batter_name} {out_context_str}.",
                "Tapper to {direction_noun}. {fielder_name} charges and fires to first {out_context_str}.",
                "Bouncer to {direction_noun}. {fielder_name} handles it and flips to first to retire {batter_name} {out_context_str}.",
                "{fielder_name} scoops it up and flips to first to retire {batter_name} {out_context_str}.",
                "Roller to {fielder_name}, he's up with it, and flips to first to retire {batter_name} {out_context_str}.",
                "Grounder {direction}, backhanded by {fielder_name}, and he fires across in time to retire {batter_name} {out_context_str}.",
                "Grounder {direction}, speared by {fielder_name}, who spins and fires to first, just in time to retire {batter_name} {out_context_str}.",
                "Hit hard {direction}, right at {fielder_name}, who shovels to first {out_context_str}.",
                "Ground ball {direction}. {fielder_name} cuts it off, and fires to first in time {out_context_str}.",
                "Grounder {direction}. Easy play for {fielder_name}, who shovels to first to get {batter_name} {out_context_str}.",
                "Chopped {direction}. {fielder_name} scoops it up and shovels to first in time {out_context_str}.",
                "Softly hit on the infield. {fielder_name} scoops it up and tosses to first in time to retire {batter_name} {out_context_str}.",
                "Grounder {direction}, handled by {fielder_name}. The throw to first is in time to retire {batter_name} {out_context_str}.",
                "Hard grounder {direction}. {fielder_name} charges it, and fires to first, just in time to retire {batter_name} {out_context_str}.",
                "Grounder {direction}. {fielder_name} will pick it up and toss to first to retire {batter_name} {out_context_str}.",
                "Hard grounder {direction}. Great pick by {fielder_name}, and he fires to first, just in time to retire {batter_name} {out_context_str}.",
                "Grounder {direction}. {fielder_name} gathers it and shovels to first to retire {batter_name} {out_context_str}.",
                "Grounder {direction}. {fielder_name} with plenty of time, and he scoops it up and flips to first {out_context_str}.",
            ],
            "unassisted_1b": [
                "One hopper to first. {fielder_name} will have it unassisted. And he steps on the bag to retire {batter_name} {out_context_str}.",
                "Roller to first. {fielder_name} will have it unassisted, and he steps on the bag {out_context_str}.",
                "Bouncer to first. {fielder_name} takes it himself and steps on the bag {out_context_str}.",
                "Grounder to first. {fielder_name} scoops it up and steps on the bag {out_context_str}.",
                "Chopper at first. {fielder_name} will have it unassisted and he steps on the bag to retire {batter_name} {out_context_str}.",
                "Bouncer to first. {fielder_name} will have it unassisted and he steps on the bag to retire {batter_name} {out_context_str}.",
                "That's a slow hopper to first. {fielder_name} gingerly scoops it up and steps on the bag to retire {batter_name}.",
                "Hard grounder to first, {fielder_name} spears it, and he steps on the bag to retire {batter_name} {out_context_str}.",
                "Hard grounder, scooped up by {fielder_name} at first base {out_context_str}.",
                "A soft dribbler to first. {fielder_name} picks it up and steps on the bag to retire {batter_name} {out_context_str}.",
            ],
            "pitcher_groundout": [
                "Comebacker to the mound. {fielder_name} handles it and tosses over to first {out_context_str}.",
                "Bouncer back to the mound. {fielder_name} scoops it up and throws to first {out_context_str}.",
                "Chopper back to the box. {fielder_name} fields it cleanly and fires to first {out_context_str}.",
                "Chopper over the mound. {fielder_name} picks it up and fires to first {out_context_str}.",
                "Bouncer back to the mound. {fielder_name} scoops it up and tosses to first {out_context_str}.",
                "Roller back to the mound. {fielder_name} scoops it up and fires to first to retire {batter_last_name} {out_context_str}.",
                "And that's dribbled right back to {fielder_name}, who tosses to first in time {out_context_str}.",
                "Chopper back to the mound. {fielder_name} picks it up and tosses to first to retire {batter_name}.",
                "Dribbler back to the mound. {fielder_name} has it, and he tosses to first to retire {batter_name} {out_context_str}.",
                "Dribbler back to {fielder_name}, and he lobs it to first in time {out_context_str}.",
                "A little dribbler back to the mound. {fielder_name} has it and tosses to first, in time to retire {batter_name} {out_context_str}.",
            ]
        },
        "Flyout": {
            "default": [
                "Hit in the air {direction}. {fielder_name} is after it and he makes the catch {out_context_str}.",
                "Fly ball, {direction}. {fielder_name} drifting in... and he makes the catch {out_context_str}.",
                "Line drive {direction}. That one is into the glove of {fielder_name} {out_context_str}.",
                "Fly ball, {direction}. {fielder_name} is camped under it, and he makes the catch {out_context_str}.",
                "Popped up, {direction}. {fielder_name} is calling for it... and he makes the catch {out_context_str}.",
                "High fly ball, {direction}... and that one is caught by {fielder_name} {out_context_str}.",
                "{fielder_name} drifting in... and he makes the catch {out_context_str}.",
                "{fielder_name} is camped under it, and he makes the catch {out_context_str}.",
                "{fielder_name} calling for it... and he makes the catch {out_context_str}.",
                "Routine play for {fielder_name}, and he makes the catch {out_context_str}.",
                "A high fly ball {direction}, but {fielder_name} has a bead on it. He makes the catch {out_context_str}.",
                "{fielder_name} tracks it down {direction} {out_context_str}.",
                "Hit well {direction}, but {fielder_name} is there to make the catch {out_context_str}.",
                "Sent deep {direction}, but {fielder_name} has plenty of room. He makes the catch {out_context_str}.",
                "Fly ball, {direction_noun}. {fielder_name} drifting in... and he makes the catch {out_context_str}.",
                "Fly ball, {direction_noun}. {fielder_name} is camped under it, and he makes the catch {out_context_str}.",
                "Fly ball, {direction_noun}. {fielder_name} will have room... and he makes the catch {out_context_str}.",
                "Hit in the air to {direction_noun}. {fielder_name} is after it and he makes the catch {out_context_str}.",
                "Fly ball into shallow {direction_noun}. {fielder_name} coming in. And he puts the squeeze on it {out_context_str}.",
                "Lifted into {direction_noun}, routine play for {fielder_name}.",
                "Lifted to shallow {direction_noun}. {fielder_name} drifting back and calling for it. And he makes the catch {out_context_str}.",
                "Pulled into {direction_noun}. {fielder_name} is there and he makes the catch {out_context_str}.",
                "Driven into deep {direction_noun}. {fielder_name} drifting back. And he makes the catch {out_context_str}.",
                "Lifted to {direction_noun}. {fielder_name} is calling for it, and he makes the catch {out_context_str}.",
                "Lifted into {direction_noun}. {fielder_name} is there and he makes the catch {out_context_str}.",
                "Fly ball into {direction_noun}. {fielder_name} calling for it. And he makes the catch {out_context_str}.",
                "Fly ball into {direction_noun}. {fielder_name} is there. And he makes the catch {out_context_str}.",
                "Lifted to shallow {direction_noun}. Routine play for {fielder_name}, and he makes the catch {out_context_str}.",
                "{fielder_name} racing after it, and he makes a diving catch {out_context_str}.",
                "{fielder_name} racing over, and he makes a diving catch {out_context_str}.",
                "Skied into shallow {direction_noun}. {fielder_name} is camped under it, and he puts the squeeze on it {out_context_str}.",
                "{fielder_name} drifting back, and he puts the squeeze on it {out_context_str}.",
                "Sliced {direction}. {fielder_name} is there, and he has it {out_context_str}.",
                "A lazy fly ball {direction}. {fielder_name} drifting in, and he makes the catch {out_context_str}.",
                "Hooked {direction}. {fielder_name} is after it, and he makes the catch {out_context_str}.",
                "Looping fly ball {direction}, a routine play for {fielder_name}, and he makes the catch {out_context_str}.",
                "Fly ball {direction}, routine play for {fielder_name}, and he snags it {out_context_str}.",
                "Hit in the air {direction}. {fielder_name} racing after it, and he makes a spectacular catch {out_context_str}.",
                "Lofted into {direction_noun}. {fielder_name} is calling for it, and he makes the catch {out_context_str}.",
                "Hit softly {direction}. {fielder_name} jogging in, and he makes the catch {out_context_str}.",
                "Hit in the air {direction}. {fielder_name} is tracking it, and he makes the catch {out_context_str}.",
                "Hit in the air {direction}. {fielder_name} is there, and he puts it away {out_context_str}.",
            ],
            "deep": [
                "Hit in the air to deep {direction_noun}. {fielder_name} racing back. And he makes a leaping grab on the warning track to haul it in {out_context_str}.",
                "Fly ball, deep {direction}. {fielder_name} is racing after it... and he makes the catch on the warning track {out_context_str}.",
                "Fly ball, deep {direction_noun}. {fielder_name} is racing after it... and he makes the catch on the warning track {out_context_str}.",
                "{fielder_name} is racing after it... and he makes the catch on the warning track {out_context_str}.",
                "Hit in the air to deep {direction_noun}. {fielder_name} racing back. And he makes a leaping grab to haul it in {out_context_str}.",
                "Sent deep {direction}. {fielder_name} on the run... and he makes the catch {out_context_str}.",
                "Driven into deep {direction_noun}. {fielder_name} drifting back. And he makes the catch on the warning track {out_context_str}.",
                "Fly ball into deep {direction_noun}. {fielder_name} drifting back. And he makes the catch {out_context_str}.",
                "{fielder_name} drifting back, and he makes a leaping catch on the warning track {out_context_str}.",
                "Hit {direction}, playable for {fielder_name}. He's under it and makes the catch {out_context_str}.",
                "Driven {direction}. {fielder_name} is after it, and he makes an overhand catch near the wall {out_context_str}.",
                "Hit in the air {direction}. {fielder_name} sprinting after it, and he makes a spectacular catch on the warning track {out_context_str}.",
            ]
        },
        "Pop Out": {
             "default": [
                 "Popped up, {direction}. {fielder_name} is after it and he makes the catch {out_context_str}.",
                 "Popped up on the infield. {fielder_name} is camped under it... and he makes the catch {out_context_str}.",
                 "Pop fly, {direction}. {fielder_name} drifting back... and he makes the catch {out_context_str}.",
                 "{fielder_name} calling for it... and he puts the squeeze on it {out_context_str}.",
                 "{fielder_name} drifting back... and he makes the catch {out_context_str}.",
                 "Popped up, {direction_noun}. {fielder_name} is calling for it... and he makes the catch {out_context_str}.",
                 "Popped up on the infield. {fielder_name} is camped under it... and he makes the catch {out_context_str}.",
                 "{fielder_name} calling for it... and he makes the squeeze {out_context_str}.",
                 "Popped up on the infield, {direction_noun} side. {fielder_name} is under it, and he makes the catch {out_context_str}.",
                 "Popped up on the infield. {fielder_name} is under it. And he makes the catch {out_context_str}.",
                 "Popped up on the infield, {direction_noun} side. {fielder_name} calling for it, and he makes the catch {out_context_str}.",
                 "Up on the infield, {direction_noun} side. {fielder_name} is under it. And he makes the catch {out_context_str}.",
                 "Popped up softly {direction}, {fielder_name} is under it, and he makes the catch {out_context_str}.",
                 "Popped up, way up, just a can of corn. {fielder_name} is camped under it and makes the catch {out_context_str}.",
                 "Popped up shallow, and {fielder_name} has it {out_context_str}.",
                 "Popped up, and {fielder_name} is under it. He will make the grab {out_context_str}.",
                 "Popped up {direction}. {fielder_name} calls for it, and he has it {out_context_str}.",
                 "{batter_name} gets jammed, pops it up. {fielder_name} is under it, and he makes the catch {out_context_str}.",
                 "Popped up {direction}. {fielder_name} is calling for it, and he hauls it in {out_context_str}.",
             ]
        },
        "Lineout": {
             "default": [
                 "Hard liner right into the glove of {fielder_name} {out_context_str}.",
                 "Lined sharply to {fielder_name} {out_context_str}.",
                 "A screaming liner to {fielder_name}, caught {out_context_str}.",
                 "Lined into the glove of {fielder_name} {out_context_str}.",
                 "Hard liner captured by {fielder_name} {out_context_str}.",
                 "Lined right at {fielder_name}, who makes the catch {out_context_str}.",
                 "A line drive, and {fielder_name} is there to snare it {out_context_str}.",
                 "{fielder_name} catches the liner {out_context_str}.",
                 "A hard hit ball, but right to {fielder_name} {out_context_str}.",
                 "A hard liner, but it's right to {fielder_name}, who makes the grab {out_context_str}.",
                 "Lined and caught by {fielder_name} {out_context_str}.",
                 "Liner {direction}, speared by {fielder_name} {out_context_str}.",
                 "Lined {direction}, {fielder_name} racing in, and he makes a diving catch {out_context_str}.",
                 "Liner right into the glove of {fielder_name}, who puts the squeeze on it {out_context_str}.",
             ]
        },
        "Strikeout": {
             "swinging": [
                 "Swing and a miss on a {pitch_type}, and {batter_name} strikes out.",
                 "He takes an awkward hack at a {pitch_type}, and {batter_name} strikes out.",
                 "Swing and a miss on a low {pitch_type}.",
                 "He takes an awkward hack at a {pitch_type} in the dirt.",
                 "Swing and a miss on a high {pitch_type}.",
                 "He chases a {pitch_type} out of the zone for strike three.",
                 "Way out in front of that {pitch_type}.",
                 "He takes a wild hack at a {pitch_type}.",
                 "Swing and a miss on a low {pitch_type}, and {batter_name} is down on strikes.",
                 "Swing and a miss on a high {pitch_type}, and {batter_name} is down on strikes.",
                 "He takes a wild hack at a {pitch_type} in the dirt.",
                 "Chases a {pitch_type} in the dirt.",
                 "Swing and a miss on a {pitch_type} in the dirt, and {batter_name} is down on strikes.",
                 "Swing and a miss on an outside {pitch_type}, and {batter_name} is down on strikes.",
                 "And a high {pitch_type} gets him swinging.",
                 "And {batter_name} nearly swings out of his shoes, and that's strike number three.",
                 "{batter_name} takes a very awkward whack at that one for a strikeout.",
                 "{batter_name} takes something of a wild swing at that {pitch_type}. Not even close, and that's a strikeout.",
                 "{batter_name} is way out in front of that one for strike three.",
                 "{batter_name} gets fooled on that {pitch_type}, and he is down on strikes.",
             ],
             "looking": [
                 "{batter_name} strikes out on a {pitch_type} to end the at-bat.",
                 "He looks at a {pitch_type} for a called strike three.",
                 "{pitch_type} called strike three.",
                 "Frozen by a {pitch_type} on the corner.",
                 "He couldn't pull the trigger on a {pitch_type}.",
                 "{pitch_type} called strike three, and {batter_name} strikes out.",
                 "{pitch_type} called strike three, and {batter_name} is down on strikes.",
                 "He looks at a {pitch_type} for a called strike three.",
                 "And {batter_name} strikes out looking {out_context_str}.",
             ],
            "swinging_outside": [
                "{batter_name} takes a wild swing on an outside pitch, and he is down on strikes."
            ],
        },
        "Walk": {
             "default": [
                 "{last_pitch_context}, and {batter_name} draws a walk.",
                 "{last_pitch_context}, and {batter_name} is aboard with a walk.",
                 "{last_pitch_context}, and {batter_name} is aboard with a {outs_str} walk.",
                 "{batter_name} draws a walk.",
                 "{last_pitch_context}, and that will put {batter_name} aboard on a walk.",
                 "{last_pitch_context}. A {outs_str} walk for {batter_name}.",
                 "{batter_name} takes his base on a walk.",
                 "A {outs_str} walk puts {batter_name} aboard.",
             ],
            "four_pitch": [
                "That's a four-pitch walk for {batter_name}."
            ],
        },
        "Double Play": {
             "default": [
                 "Ground ball to {direction_noun}, this could be two! And they turn the double play {out_context_str}.",
                 "Roller to {direction_noun}. They get the lead runner at second and turn it for a double play {out_context_str}.",
                 "Grounder to {direction_noun}. Flip to second for one, onto first... double play!",
                 "Tailor-made double play ball to {direction_noun}. And they turn it {out_context_str}!",
                 "Hard grounder to {direction_noun}. Starts the double play {out_context_str}.",
                 "Bouncer to {direction_noun}, and they spin the double play {out_context_str}.",
                 "Grounder to {direction_noun}. {fielder_name} to second for one, over to first in time. And that's a {dp_notation} double play {out_context_str}.",
                 "Bouncer to {direction_noun}. {fielder_name} to second for one, over to first just in time. And that's a {dp_notation} double play {out_context_str}.",
                 "One hopper to {direction_noun}. {fielder_name} steps on the bag for the force. He fires to second in time and that's a {dp_notation} double play {out_context_str}.",
                 "{fielder_name} to second for one, over to first in time. And that's a {dp_notation} double play {out_context_str}.",
                 "Grounder to {direction_noun}. {fielder_name} to second for one, over to first in time. And that's a double play {out_context_str}."
             ],
            "first_then_second": [
                "Hard-hit bouncer to first. {fielder_name} steps on the bag and fires to second, and the runner is tagged out. That's a {dp_notation} double play."
            ],
            "unassisted_force": [
                "Grounder {direction}. {fielder_name} steps on the bag for one, over to first in time. That's a {dp_notation} double play {out_context_str}."
            ],
            "bunt_third_first": [
                "Bunted in front of the plate. They get the lead runner at third, and the long throw to first is in time. That's a {dp_notation} double play {out_context_str}."
            ],
        },
        "Hit By Pitch": {
             "default": [
                 "{batter_name} is hit by the pitch.",
                 "{batter_name} takes one for the team.",
                 "The pitch hits {batter_name}, and he will take first base.",
                 "{batter_name} is aboard after being hit by the pitch.",
                 "That one catches him. He is awarded first base.",
                 "Hit by the pitch, {batter_name} heads down to first.",
                 "And {batter_name} gets hit by the pitch, and he'll trot down to first.",
             ]
        },
        "Sacrifice Bunt": {
            "default": [
                "He lays down a sacrifice bunt {direction}. {fielder_name} fields it and throws to first {out_context_str}.",
                "Bunted {direction}. {fielder_name} scoops it up and fires to first {out_context_str}.",
                "Squares around and bunts it {direction}. {fielder_name} charges and throws to first {out_context_str}.",
                "A well-placed bunt {direction}. {fielder_name} to first {out_context_str}.",
                "The sacrifice is down {direction}. {fielder_name} throws to first {out_context_str}.",
                "Bunted {direction}. {fielder_name} makes the play at first {out_context_str}, and the sacrifice does its job.",
                "Bunted {direction}. {fielder_name} will pick it up and toss it to first to retire {batter_name} {out_context_str}.",
                "Bunted {direction}. That will move the runner up. {fielder_name} collects and fires to first to retire {batter_name} {out_context_str}.",
            ]
        },
        "Bunt Ground Out": {
            "default": [
                 "Bunts {direction}, but {fielder_name} is there and throws to first {out_context_str}.",
                 "He bunts it {direction}. {fielder_name} fields it cleanly and retires the batter at first {out_context_str}.",
                 "A bunt attempt {direction}. {fielder_name} pounces on it and fires to first {out_context_str}.",
                 "Bunted {direction}. {fielder_name} gets to it and throws out {batter_name} {out_context_str}.",
                 "{batter_name} lays down a bunt {direction}. {fielder_name} makes the play at first {out_context_str}.",
            ],
            "pitcher_groundout": [
                "Bunted back to the mound. {fielder_name} scoops it up and fires to first just in time to retire {batter_name} {out_context_str}."
            ],
        },
        "Sac Fly": {
            "default": [
                "Fly ball {direction}. {fielder_name} is under it and he makes the catch. The runner tags and scores.",
                "Fly ball {direction}. {fielder_name} is there and he makes the catch. The runner will tag up and score.",
                "Fly ball into {direction_noun}. {fielder_name} is under it and he makes the catch. And the runner tags and scores on the sacrifice fly.",
                "Fly ball {direction}. {fielder_name} drifts back and makes the catch. The runner tags and scores.",
                "Lifted {direction}. {fielder_name} makes the catch, and the runner comes home on the sacrifice fly.",
                "Hit in the air {direction}. {fielder_name} catches it, but the runner tags and scores.",
                "{fielder_name} takes the fly ball {direction}. The runner tags and comes home to score.",
            ]
        },
        "Field Error": {
            "default": [
                "{batter_name} reaches on an error.",
                "An error allows {batter_name} to reach base.",
                "{batter_name} is aboard, and that will go down as an error on {fielder_name}.",
                "The play results in an error, and {batter_name} reaches safely.",
                "An error by {fielder_name} allows {batter_name} to reach base."
            ],
            "grounder": [
                "Grounder {direction}, and {fielder_name} will not get a handle on that ball. {batter_name} will be safe at first, and that's going to be an error.",
                "Chopper {direction}. {fielder_name} bobbles the ball, and it kicks past him. {batter_name} will be safe at first.",
                "Grounder {direction}, and {fielder_name} can't get a handle on it. {batter_name} reaches on the error."
            ],
            "everybody_safe": [
                "Hard grounder {direction}, and that one skips away from {fielder_name}. Everybody is going to be safe."
            ],
            "dropped_fly": [
                "{fielder_name} gets to it, but he drops the ball. {batter_name} reaches safely on the error."
            ],
        },
        "Forceout": {
            "home_force": [
                "Grounder {direction}. {fielder_name} comes home, and they get the force at the plate {out_context_str}.",
                "On the ground {direction}. {fielder_name} throws home in time for the force {out_context_str}.",
                "Bouncer {direction}. {fielder_name} goes to the plate, and the runner is forced out at home {out_context_str}."
            ],
            "default": [
                "They get the force {out_context_str}. {batter_name} reaches on a fielder's choice.",
                "The defense records a forceout {out_context_str}, with {batter_name} reaching on a fielder's choice.",
                "A force play {out_context_str}. That goes down as a fielder's choice for {batter_name}.",
                "They take the force {out_context_str}, and it's a fielder's choice for {batter_name}."
            ],
            "second_base": [
                "Grounder {direction}. {fielder_name} scoops it up and steps on second to retire the runner {out_context_str}."
            ],
            "third_base": [
                "Bouncer {direction}. {fielder_name} scoops it up and steps on the bag to force the out at third {out_context_str}."
            ],
            "second_base_throw": [
                "Grounder {direction}. {fielder_name} scoops it up and tosses to second to get the force {out_context_str}."
            ],
        },
        "Fielders Choice": {
            "home_tag": [
                "Grounder {direction}. {fielder_name} scoops it up and fires home. The runner is tagged out, sliding into the plate. {batter_name} is safe on a fielder's choice."
            ],
            "home_safe": [
                "Grounder {direction}. {fielder_name} throws home, and the throw is not in time. The runner slides in safely under the tag."
            ]
        },
    },
    "narrative_strings": {
        "strike_called": [
            "called strike one", "called a strike", "in there for a called strike",
            "taken for a called strike", "paints the corner for a strike", "catches the black",
            "called a strike on the inside corner", "called strike", "a strike",
            "paints the corner for a called strike"
        ],
        "strike_called_one": [
            "called strike one",
            "in there for strike one",
            "strike one called",
            "taken for a called strike",
            "paints the corner for strike one",
            "catches the black",
            "called a strike",
            "a strike",
            "in there for a called strike",
            "takes it for strike one",
            "in for a strike",
            "a called first strike",
            "finds the zone for a called strike",
            "in there for a called strike one",
            "taken for a called strike one",
            "in there for a strike",
        ],
        "strike_called_two": [
            "called strike two", "in there for strike two", "strike two",
            "called a strike", "taken for a called strike",
            "paints the corner for a called strike", "catches the black",
            "in there for a called strike", "a strike",
            "takes it for strike two",
            "in for the second strike",
            "a called second strike",
            "in there for a called strike two",
            "in there for a strike",
        ],
        "strike_called_three": [
            "called strike three", "caught looking at strike three", "strike three called",
            "in there for strike three", "rings him up", "got him looking",
            "paints the corner for a called strike three",
            "takes strike three",
            "called third strike",
            "strike three taken",
            "in there for a called strike three",
        ],
        "strike_swinging": [
            "swung on and missed", "cut on and missed", "a big swing and a miss",
            "he hacks at it and misses", "comes up empty",
            "he takes an awkward hack at the pitch",
            "he takes a wild hack at the pitch",
            "swings right through it",
            "he swings and comes up empty",
            "a cut and a miss",
            "he takes a wild wave at that one",
            "he takes a wild swing",
            "swing and a miss",
            "he swings out of his shoes",
            "cut on it, missed",
            "he waves at it",
            "he whiffs at it",
            "he takes an awkward cut",
            "he takes an awkward swing at that",
            "a lazy, noncommittal swing",
            "he takes an awkward whiff at that one",
            "he swings and misses",
            "swung on it, missed",
            "he takes an early swing",
            "he takes a late swing",
            "he takes a noncommittal swing",
        ],
        "strike_swinging_three": [
            "swung on and missed for strike three", "struck him out swinging",
            "swings through it for strike three", "fans him", "gets him swinging",
            "he chases it for strike three",
            "swings and misses for strike three",
            "a swing and a miss for the third strike",
            "comes up empty for strike three",
            "swing and a miss for strike three",
            "he takes something of a wild swing",
            "he takes a very awkward whack at that one for a strikeout",
            "way out in front of that one for strike three",
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
            "{batter_name} starts things off with a leadoff single{inning_context}.",
            "{batter_name} is aboard with a leadoff single{inning_context}.",
            "The inning starts with a base hit from {batter_name}.",
            "A leadoff single for {batter_name} to get things going{inning_context}.",
            "{batter_name} starts the inning with a base hit.",
            "{batter_name} is aboard with a single to lead off the inning."
        ],
        "leadoff_double": [
            "{batter_name} starts the inning with a stand-up double{inning_context}.",
            "A leadoff double for {batter_name}, and the offense is in business.",
            "{batter_name} is aboard with a leadoff double{inning_context}.",
            "And that's a leadoff double for {batter_name}{inning_context}.",
            "{batter_name} will be aboard with a stand-up double{inning_context}.",
            "{batter_name} heading for second, and he'll be aboard safely with a leadoff double{inning_context}.",
            "{batter_name} hustling for second, and he cruises in standing up.",
        ],
        "leadoff_triple": [
            "{batter_name} starts the inning with a triple{inning_context}!",
            "A leadoff triple for {batter_name}!",
            "{batter_name} is aboard with a leadoff triple{inning_context}."
        ],
        "leadoff_walk": [
            "{batter_name} draws a leadoff walk{inning_context}.",
            "The inning begins with a walk to {batter_name}.",
            "{batter_name} is on with a leadoff walk{inning_context}.",
            "A walk to {batter_name} starts the inning.",
            "And that's a leadoff walk for {batter_name}.",
        ],
        "single_nobody_out": [
            "{batter_name} is aboard with a single.",
            "{batter_name} reaches with a base hit.",
            "And {batter_name} is aboard with a single{inning_context}."
        ],
        "double_nobody_out": [
            "{batter_name} is aboard with a double.",
            "And {batter_name} stands at second with a double{inning_context}.",
            "That's going to be a stand-up double for {batter_name}{inning_context}."
        ],
        "triple_nobody_out": [
            "{batter_name} is aboard with a triple.",
            "And {batter_name} stands at third with a triple{inning_context}.",
            "{batter_name} reaches third with nobody out{inning_context}.",
            "A triple puts {batter_name} at third with nobody away.",
        ],
        "single_one_out": [
            "{batter_name} is aboard with a one-out single{inning_context}.",
            "A one-out base hit for {batter_name}.",
            "{batter_name} singles with one away.",
            "{batter_name} is on with a one-out single.",
            "{batter_name} reaches with a one-out single."
        ],
        "double_one_out": [
            "{batter_name} is aboard with a one-out double{inning_context}.",
            "A one-out double for {batter_name}.",
            "{batter_name} doubles with one away.",
            "That's going to be a stand-up double for {batter_name}{inning_context}.",
            "{batter_name} coasts into second with a double.",
            "And that's going to be a one-out double for {batter_name}{inning_context}.",
            "{batter_name} will be aboard with a stand-up double.",
            "{batter_name} heading for second, and he will slide in safely ahead of the throw.",
        ],
        "triple_one_out": [
            "{batter_name} is aboard with a one-out triple{inning_context}.",
            "A one-out triple for {batter_name}.",
            "{batter_name} triples with one away."
        ],
        "two_out_single": [
            "{batter_name} keeps the inning alive with a two-out single{inning_context}.",
            "A two-out base hit for {batter_name}.",
            "{batter_name} is aboard with a two-out single{inning_context}.",
            "And that's going to be a two-out single for {batter_name}."
        ],
        "two_out_double": [
            "A two-out double for {batter_name}!",
            "{batter_name} rips one into the gap for a two-out double.",
            "{batter_name} is aboard with a two-out double{inning_context}.",
            "{batter_name} heading for second, and he's in standing up with a two-out double{inning_context}.",
            "{batter_name} heading for second, and he'll reach standing up with two away.",
        ],
        "two_out_triple": [
            "A two-out triple for {batter_name}!",
            "{batter_name} is aboard with a two-out triple{inning_context}.",
            "{batter_name} reaches third with a two-out triple{inning_context}.",
            "A triple for {batter_name} with two away.",
        ],
        "two_out_walk": [
            "{batter_name} extends the inning with a two-out walk.",
            "A two-out walk puts {batter_name} aboard{inning_context}.",
            "{batter_name} takes a walk with two away.",
            "{batter_name} draws a two-out walk{inning_context}.",
            "And that's a two-out base on balls for {batter_name}.",
        ],
        "runners_in_scoring_position": [
            "The tying run is on second.",
            "A big opportunity here with a runner in scoring position.",
            "The go-ahead run is at third."
        ],
        "infield_in": [
            "The infield is playing in, looking to cut down the run at the plate."
        ],
        "runner_goes": [
            "and the runner goes!",
            "and there he goes!",
            "and the runner is going!",
            "and the runner takes off!",
            "and the runner breaks!"
        ],
        "payoff_pitch": [
            "And the payoff pitch...",
            "The payoff pitch...",
            "Full count, here's the pitch...",
            "And the 3-2 pitch...",
            "Here comes the payoff...",
            "Three and two, the pitch...",
            "And now the payoff pitch...",
            "And here's the payoff pitch...",
        ],
        "count_full": [
            ", and the count runs full",
            ", count is full",
            ", brings the count to 3-2",
            ", and the count is now full",
            ", and now a full count",
            ", three balls and two strikes",
            ", that fills the count",
        ],
        "count_remains_two_strikes": [
            ", and {batter_name} stays alive",
            ", count holds at {count_str}",
            ", count remains {count_str}",
            ", still {count_str}",
            ", and we'll do it again",
            ", and the count stays at {count_str}",
            ", so we'll do it again",
            ", and the at-bat continues",
            ", {batter_name} keeps the at-bat going",
            ", and it remains {count_str}",
            ", one more pitch coming at {count_str}",
        ],
        "inning_end_123": [
             "{pitcher_name} sets them down in order.",
             "Another one-two-three inning for {pitcher_name}.",
             "{pitcher_name} retires the side in order.",
             "Three up, three down for {pitcher_name}.",
             "{pitcher_name} works a 1-2-3 inning.",
             "{pitcher_name} sets down the side with ease.",
             "And that's another one, two, three inning for {pitcher_name}.",
             "{pitcher_name} sets them down in order here in the {inning_ordinal}.",
             "{pitcher_name} works a one-two-three inning here in the {inning_ordinal}."
        ],
        "walk_aboard": [
            "{batter_name} is aboard with a {outs_str} walk.",
            "{batter_name} draws a {outs_str} walk.",
            "Ball misses outside, and {batter_name} is aboard with a {outs_str} walk."
        ],
        "throw_outcome_safe": [
            "The throw down... not in time!",
            "Throw to {base} is not in time.",
            "The throw is late!",
            "The throw arrives too late.",
            "Safe at {base}!",
            "He beats the throw to {base}.",
        ],
        "throw_outcome_out": [
            "The throw down... he got him!",
            "Throw to {base} is in time!",
            "And they got him at {base}!",
            "The throw beats him to {base}!",
            "Out at {base}!",
            "The tag is there in time!",
        ],
        "stolen_base": [
            "{runner_name} takes off for second... and he's in there with a stolen base!",
            "A good jump and a stolen base for {runner_name}.",
            "{runner_name} hustling for second... and he's in there safely with a stolen base!",
            "Throw to second is not in time. {runner_name} steals second.",
            "{runner_name} will slide in under the tag. That's a stolen base for {runner_name}."
        ],
        "stolen_base_third": [
            "{runner_name} takes off for third... and he makes it! A stolen base!",
            "He's going for third! And he's safe! {runner_name} with a great jump.",
            "Throw to third is not in time. {runner_name} steals third."
        ],
        "batter_intro_leadoff": [
            "And {batter_name} leads off for the {team_name}.",
            "And leading off for the {team_name}, {batter_name}.",
            "{batter_name} steps in to lead things off.",
            "And {batter_name} will step in at the top of the {team_name} order.",
            "And {batter_name} will lead off the inning.",
            "Leading off, {batter_name}.",
            "Leading off, {position}, {batter_name}.",
            "Batting first and playing {position}, {batter_name}.",
            "And {batter_name} steps in to start the inning.",
            "{batter_name} digs in. He'll lead off.",
            "And {batter_name} steps into the box against {pitcher_name}.",
            "And {batter_name} will step in against {pitcher_name}.",
            "And {batter_name} checks in against {pitcher_name}.",
            "And {batter_name} checks in.",
            "And {batter_name} will step in to lead us off.",
            "And {batter_name} will bat for the {team_name} to lead us off.",
            "And {batter_name} will step into the box against {pitcher_name}.",
            "And stepping up to the plate for the {team_name} is {position} {batter_name}.",
            "And {batter_name} digs in against {pitcher_name}.",
        ],
        "batter_intro_empty": [
            "And {batter_name} will step in with {outs_str} and nobody on.",
            "And {batter_name} steps in with {outs_str} and the bases empty.",
            "And that will bring {batter_name} to the plate with {outs_str} and the bases empty.",
            "{batter_name} steps to the plate. {outs_str}, bases empty.",
            "And {batter_name} is due up. {outs_str}, bases empty.",
            "And {batter_name} will step in with {outs_str} and the bases empty.",
            "And {batter_name} will step in with {outs_str} and nobody on.",
            "Bases empty, {outs_str}, for {batter_name}.",
            "And {batter_name} steps in against {pitcher_name}. {outs_str}, nobody on.",
            "And {batter_name} checks in with {outs_str} and the bases empty.",
            "And here's {batter_name} with {outs_str} and nobody aboard.",
            "And here's {batter_name} with {outs_str} and nobody on.",
            "So, bases empty, {outs_str} for {batter_name}.",
            "And {batter_name} steps in.",
            "And {batter_name} checks in.",
            "And here's {batter_name} with the bases empty and {outs_str}.",
            "And that brings up {batter_name}.",
            "And {batter_name} will dig in with {outs_str} and nobody on.",
            "Nobody aboard, {outs_str} for {batter_name}.",
            "{outs_str}, bases empty for {position} {batter_name}.",
            "And {batter_name} checks in with {outs_str}, and nobody aboard.",
            "And {batter_name} steps into the box.",
            "And here comes {batter_name}.",
        ],
        "batter_intro_bases_cleared": [
             "Bases cleared, {outs_str} for {batter_name}.",
             "And with the bases now empty, {outs_str}, {batter_name} steps in.",
             "Bases cleared. And {batter_name} will step in with {outs_str} and nobody on.",
            "And {batter_name} steps in with {outs_str} and the bases cleared.",
        ],
        "batter_intro_runners": [
             "And {batter_name} steps in with {runners_str}, {outs_str}.",
             "{batter_name} comes to the plate. {runners_str} and {outs_str}.",
             "And that will bring up {batter_name} with {runners_str}.",
             "Runner on {runners_str}, {outs_str}, for {batter_name}.",
             "And {batter_name} will step in with {runners_str} and {outs_str}.",
             "Runner on {runners_str}, {outs_str}, for {batter_name}.",
             "And {batter_name} steps in. {runners_str}, {outs_str}.",
             "So a runner on {runners_str} and {outs_str} for {batter_name}.",
             "{runners_str}, {outs_str}. {batter_name} at the plate.",
             "And {batter_name} steps in against {pitcher_name}. {runners_str}, {outs_str}.",
             "And here's {batter_name} with {runners_str} and {outs_str}.",
             "So, {runners_str} and {outs_str} for {batter_name}.",
             "So, {runners_str} now, {outs_str} for {batter_name}.",
             "And {batter_name} steps in with {outs_str} and {runners_str}.",
             "And here's {batter_name} with {outs_str} and {runners_str}.",
             "And {batter_name} checks in with {runners_str} and {outs_str}.",
            "And in steps {batter_name}. {outs_str}, {runners_str}.",
            "And {batter_name} digs in with {runners_str} and {outs_str}.",
            "{outs_str}, {runners_str}, and that will bring up {batter_name}.",
            "And that'll bring up {batter_name} with {outs_str} and {runners_str}.",
        ],
        "pitch_connectors": [
            "And the {count_str}...",
            "The {count_str} pitch...",
            "And the {count_str} pitch...",
            "And the {count_str}...",
            "The {count_str}...",
            "Here comes the {count_str}...",
            "{count_str_cap}, pitch on the way...",
            "And {pitcher_name_last}'s pitch...",
            "And {pitcher_name_last} delivers...",
            "{pitcher_name_last} kicks and delivers...",
            "And the pitch...",
            "Here is the {count_str}...",
            "And the {count_str_and}...",
            "And the {count_str} delivery.",
            "And on the {count_str}...",
            "{pitcher_name_last} comes set, and here's the {count_str} pitch...",
            "The pitch...",
            "{pitcher_name_last}'s pitch...",
            "And here's the {count_str} pitch from {pitcher_name_last}...",
            "And now {pitcher_name_last} comes set for the {count_str} pitch...",
            "Here's the {count_str} pitch...",
            "And here's the {count_str} pitch...",
            "The {count_str} delivery...",
            "And {pitcher_name_last} comes set for the {count_str}...",
            "The {count_str} pitch to {batter_name_last}...",
            "There's the {count_str} pitch...",
            "And {pitcher_name_last} with the {count_str} pitch...",
            "And he comes set for the {count_str}...",
            "The {count_str} pitch from {pitcher_name_last}...",
            "And now the {count_str} pitch...",
            "It's the {count_str} pitch...",
        ],
        "pitch_connectors_00": [
            "And the pitch...",
            "And the pitch...",
            "And {pitcher_name_last}'s pitch...",
            "And {pitcher_name_last} delivers...",
            "And the pitch to {batter_name_last}...",
            "{pitcher_name_last} winds and fires...",
            "Here's the pitch...",
            "And {pitcher_name_last} deals...",
            "And {pitcher_name_last} kicks and delivers...",
            "{pitcher_name_last} comes set and the pitch...",
            "The pitch from {pitcher_name_last}...",
            "{pitcher_name_last} comes set and delivers...",
            "And here's the first pitch from {pitcher_name_last}...",
            "And here's the first pitch...",
            "And the first pitch from {pitcher_name_last}...",
            "And here's the pitch...",
            "And here's the first pitch to {batter_name_last}...",
            "Here's the first pitch from {pitcher_name_last}...",
            "And here's the pitch from {pitcher_name_last}...",
            "And here's the pitch to {batter_name_last}...",
            "The pitch to {batter_name_last}...",
            "The first pitch...",
            "The first pitch to {batter_name_last}...",
            "Here's the pitch from {pitcher_name_last}...",
            "And the pitch from {pitcher_name_last}...",
            "And now the pitch to {batter_name_last}...",
            "{pitcher_name_last}'s pitch...",
            "And the first offering...",
            "And {pitcher_name_last} comes set and delivers...",
            "All right, and now the pitch to {batter_name_last}...",
        ],
        "pitch_connectors_stretch": [
             "And {pitcher_name_last} from the stretch...",
             "And the pitch...",
             "And {pitcher_name_last} deals...",
             "And {pitcher_name_last} comes to the plate...",
             "From the belt, the pitch...",
             "And {pitcher_name_last}'s pitch..."
        ],
        "batter_matchup_handedness": [
            "Righty against righty.",
            "Righty against the lefty.",
            "Lefty against the lefty.",
            "Lefty against the righty."
        ],
        "play_by_play_templates": [
            "He {verb} {direction} on a {pitch_velo} mph {pitch_type_lower}.",
            "He {verb} {direction} on a {pitch_type_lower}.",
            "{verb_capitalized} {direction}.",
            "{verb_capitalized} {direction} on a {pitch_type_lower}.",
            "{pitch_type}, {verb} {direction}."
        ],
        "play_by_play_noun_templates": [
             "{noun_capitalized} {direction}.",
             "{noun_capitalized} {direction} off a {pitch_type_lower}.",
             "He hits {noun} {direction}.",
             "He gets {noun} {direction}."
        ],
        "bunt_foul": [
            "He squares to bunt, but fouls it off",
            "Showing bunt, he pushes it foul",
            "He tries to lay one down, but it rolls foul",
            "Bunted foul",
            "He offers at the bunt, but fouls it back",
            "The bunt attempt is fouled off",
            "He attempts to bunt, but it goes foul",
            "Squared around, but he fouls it",
            "Bunted foul off to the right",
            "Bunted foul along the third base line",
            "Bunted foul down the first base line",
            "Bunted foul down the third base line",
            "Bunted foul off to the left",
        ],
        "runner_leads": [
            "The runners take their leads, {runner_positions}.",
            "{runner_positions}.",
            "And {runner_positions}.",
        ],
        "bunt_sac": [
            "  He gets the bunt down, a perfect sacrifice.",
            "  A successful sacrifice bunt moves the runners.",
            "  He lays down the bunt, doing his job."
        ],
        "intentional_walk": [
            "And they're going to intentionally walk {batter_name}.",
            "{batter_name} is given an intentional base on balls.",
            "They'll put {batter_name} on intentionally.",
            "An intentional walk sends {batter_name} to first.",
            "And now they're going to intentionally walk {batter_name}.",
            "And that's an intentional base on balls.",
        ],
        "strikeout_reaches": [
            "Strike three, but {batter_name} is safe at first.",
            "{batter_name} strikes out but reaches first safely.",
            "A strikeout, but {batter_name} is aboard."
        ],
        "strikeout_reaches_wild_pitch": [
            "So, strikeout on a wild pitch, and {batter_name} is aboard.",
            "{batter_name} strikes out, but reaches first on the wild pitch.",
            "Strike three gets away for a wild pitch, and {batter_name} is safe at first."
        ],
        "strikeout_reaches_extra_base": [
            "Strike three, but {batter_name} reaches {base} safely.",
            "{batter_name} strikes out but makes it safely to {base}."
        ],
        "strikeout_reaches_and_scores": [
            "{batter_name} strikes out but reaches safely and comes around to score.",
            "A strikeout, but {batter_name} reaches base and makes it all the way home."
        ],
        "strikeout_bunt": [
            "Bunted foul with two strikes, and {batter_name} is out.",
            "The bunt rolls foul for strike three. {batter_name} is retired."
        ],
        "strikeout_bunt_missed": [
            "{batter_name} misses the bunt for strike three. He strikes out.",
            "The bunt attempt comes up empty, and {batter_name} strikes out.",
            "{batter_name} strikes out trying to bunt."
        ],
        "pitchout": [
            "And that's a pitchout",
            "A pitchout",
            "They pitch out"
        ],
        "bunt_missed": [
            "He offers at the bunt, but misses",
            "He squares to bunt and misses",
            "The bunt attempt comes up empty"
        ],
        "leadoff_walk_four_pitch": [
            "{batter_name} draws a leadoff four-pitch walk."
        ],
        "intentional_walk_pitcher_next": [
            "And it looks like they are going to put him on base to get to the pitcher spot."
        ],
        "walk_forces_run": [
            "Ball four, and that will walk in a run."
        ],
        "batter_intro_pitcher": [
            "And that will bring up the pitcher, {batter_name}."
        ],
        "batter_intro_cleanup": [
            "Here comes the cleanup hitter, {batter_name}."
        ],
        "batter_intro_winning_run": [
            "{batter_name} steps in, representing the winning run."
        ],
        "batter_intro_winning_run_first": [
            "Winning run at first for {batter_name}."
        ],
        "inning_end_123_relief": [
            "And that's a one-two-three inning for {pitcher_name} in relief."
        ],
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
                "liner": ["lines a single", "rifles a single", "lines one sharply", "lines one", "smokes a single", "drives a base hit"],
                "grounder": ["hits a ground ball single", "squeezes a single"]
            },
            "nouns": {
                "default": ["a base hit", "a base knock"],
                "bloop": ["a bloop single", "a little flare"],
                "liner": ["a line drive single", "a sharp single that drops in"],
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
                "screamer": ["homers on a liner", "drives a laser over the fence"],
                "moonshot": ["homers on a fly ball", "hits one a mile in the air", "hits a high, majestic blast"]
            },
            "nouns": {
                "default": ["a long home run", "a home run"],
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
                "deep": ["flies out deep", "lifts a deep fly ball", "drives a fly ball", "hits a long fly ball"]
            },
            "nouns": {
                "default": ["a routine fly ball", "a fly ball", "a fly", "a can of corn", "a high fly ball", "a lazy fly"],
                "deep": ["a long fly ball", "a drive to the warning track"]
            }
        },
        "Pop Out": {
            "verbs": { "default": ["pops out"] },
            "nouns": { "default": ["a pop fly", "a high pop up"] }
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
            "swinging": ["strikes out swinging", "is down on strikes", "goes down swinging", "takes a big cut and misses for strike three", "swings through it for strike three", "is set down swinging"],
            "looking": ["strikes out looking", "is caught looking", "is frozen by strike three", "watches strike three go by", "takes a called third strike", "is rung up"]
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
    },

    "lineup_strings": {
        "intro_away": [
            "Let's take a look at the Starting 9 for the visiting {team_name}."
        ],
        "outro_away": [
            "Those are the {away_team_name}.",
            "Those are the {away_short}."
        ],
        "intro_home": [
            "Here are the {home_team_name}."
        ],
        "manager_away": [
            "And the {team_name} are managed by {manager_name}.",
            "And the {team_name} are managed by veteran skipper {manager_name}.",
            "And the {team_name} are managed by notorious hot head {manager_name}.",
        ],
        "manager_home": [
            "The {team_name} are managed by {manager_name}.",
            "And the {team_name} are managed by veteran skipper {manager_name}.",
        ],
        "batting_1": [
            "{player_name} will lead off in {position_place}.",
            "{position} {player_name} will lead off."
        ],
        "batting_2": [
            "Batting second and playing {position_place}, {player_name}.",
            "Batting second, {position} {player_name}."
        ],
        "batting_3": [
            "{position} {player_name} will bat third."
        ],
        "batting_4": [
            "{position} {player_name} will be in the cleanup spot this evening.",
            "{position} {player_name} will be in the cleanup spot this evening.",
            "In the cleanup spot this evening, {position} {player_name}."
        ],
        "batting_5": [
            "Batting fifth, {position} {player_name}.",
            "{position} {player_name} will bat fifth."
        ],
        "batting_6": [
            "Sixth, {position} {player_name}.",
            "{position} {player_name}.",
            "Batting sixth, {position} {player_name}."
        ],
        "batting_7": [
            "Batting seventh, {position} {player_name}.",
            "{position} {player_name} will bat seventh."
        ],
        "batting_8": [
            "The big man, the {position} {player_name},",
            "{position} {player_name} will bat eighth.",
            "{position} {player_name} will bat eighth."
        ],
        "batting_9": [
            "And batting ninth, {pitch_hand}-handed starting pitcher {player_name}.",
            "And batting ninth, {position} {player_name}."
        ],
        "batting_2_home": [
            "Batting second, {position} {player_name}."
        ],
        "batting_4_home": [
            "In the cleanup spot this evening, {position} {player_name}.",
            "{position} {player_name} will be in the cleanup spot this evening."
        ],
        "batting_5_home": [
            "{position} {player_name} will bat fifth.",
            "Batting fifth, {position} {player_name}."
        ],
        "batting_6_home": [
            "Batting sixth, {position} {player_name}.",
            "{position} {player_name}."
        ],
        "batting_7_home": [
            "{position} {player_name} will bat seventh.",
            "Batting seventh, {position} {player_name}."
        ],
        "batting_8_home": [
            "{position} {player_name} will bat eighth.",
            "The big man, the {position} {player_name},"
        ]
    },
        "radio_strings": {
        "pregame_color": [
             "And before we are underway here at {venue}, it's time for producer Phil to pull a name out of the Fishbowl for tonight's Instagram winner. If you'd like your name to go into the Fishbowl head over to sleepbaseball.com and follow us on Instagram. if that sounds like the kind of thing you're into, and tonight's winner is Anna. Congratulations. And Producer Phil will be in touch on Instagram to sort out the exciting details. And a special happy birthday to listener Tracy Davidson. He'll be turning 28. Phil and I have fun memories of being 28 years old back at the dawn of the radio industry. Here's hoping you have a great birthday Tracy Davidson.",
             "Some pregame flavor..."
        ],
        "station_intro": [
             "{network_name} presents Baseball.",
             "You're listening to {network_name}.",
             "{network_name} presents Sleep Baseball.",
             "Live from the coast, this is {network_name}.",
             "Broadcasting to you from the golden shores, welcome to baseball on {network_name}.",
             "Another night, another game, right here on {network_name}.",
             "From the first pitch to the final out, you're locked into {network_name}.",
             "This is {network_name}, your home for summer baseball.",
             "We are live on {network_name}, bringing you the sounds of the game.",
             "Baseball is on the air, exclusively on {network_name}."
        ],
        "welcome_intro": [
             "Good evening, friends. We're glad to have you back with us.",
             "Hello and welcome to another beautiful night for baseball.",
             "Welcome aboard, baseball fans.",
             "Grab a hot dog and settle in, we've got a great matchup tonight.",
             "It's time for the greatest game on earth.",
            "Good evening, everybody.",
            "And a pleasant good evening once again, friends.",
        ],
        "inning_break_outro": [
             "We'll be back with the {next_inning_ordinal} inning in a moment here on {network_name}.",
             "We'll be back with more baseball here on {network_name}.",
             "We'll be back after these messages.",
             "We'll be back with the {next_inning_ordinal} inning in a moment here on {station_call} and {network_name}.",
             "We'll be back with more baseball here on {station_call}, and {network_name}.",
             "We'll be back with the {next_inning_ordinal} inning after these words on {station_call} and {network_name}.",
             "We'll be back in a moment with more baseball here on {network_name}.",
             "As we go into the {next_inning_ordinal} inning in a moment here on {station_call} and {network_name}.",
            "We'll be right back with more baseball on {network_name}.",
            "We'll be right back with the {next_inning_ordinal} inning. Here on {network_name}.",
            "We'll be right back on {network_name}.",
            "And we'll be back in a moment, here on {network_name}.",
            "But we'll be back with the {next_inning_ordinal} inning after these important messages on {station_call} and {network_name}.",
            "We will be back with more baseball after these words on {station_call} and {network_name}.",
            "We'll be back in a bit with more baseball, here on {network_name}.",
        ],
        "inning_break_intro": [
             "And welcome back with us here from {venue}.",
             "And we're back.",
             "Welcome back."
        ],
        "inning_break_intro_top": [
             "{half} of the {inning_ordinal} inning here at {venue}.",
             "{half} of the {inning_ordinal} inning here at {venue} in {location}.",
             "{half} of the {inning_ordinal} inning here at {venue} in {location_with_state}.",
             "{half} of the {inning_ordinal} at {venue}, as we continue our {score_context} here in {location}.",
             "{half} of the {inning_ordinal} at {venue} in {location_with_state}, as we continue our {score_context}.",
             "{half} of the {inning_ordinal} inning here at {venue}. {score_str} and {batting_team} will bring {due_up_desc} up against {pitcher_name}.",
             "{half} of the {inning_ordinal} inning here at {venue} in {location}. {score_str} and {batting_team} will bring {due_up_desc} up against {pitcher_name}.",
             "{half} of the {inning_ordinal} inning here in {location} at {venue}. {score_str} and they'll bring {due_up_desc} up against {pitcher_name}.",
             "{half} of the {inning_ordinal} inning here in {location}. {score_str} as {due_up_desc} step up against {pitcher_name}.",
             "{half} of the {inning_ordinal} here at {venue} in {location}. It's {score_phrase}.",
             "{half} of the {inning_ordinal} here at {venue}. {score_phrase} as {due_up_desc} step up against {pitcher_name}.",
             "{half} of the {inning_ordinal} here in {location}. {score_phrase}.",
             "{half} of the {inning_ordinal} here at {venue}. Still {score_phrase} and {batting_team} will bring {due_up_desc} up against {pitcher_name}.",
            "And welcome back to {venue}, everybody. We are heading into the {half_lower} of the {inning_ordinal} inning.",
            "And welcome back to {venue}, as we get ready to begin the {half_lower} of the {inning_ordinal} inning.",
            "And welcome back with us at {venue} in {location_with_state}.",
            "And we're back at {venue} here in {location_with_state}.",
            "And greetings again, from {venue} here in {location_with_state}.",
        ],
        "inning_break_intro_bottom": [
             "{half} of the {inning_ordinal}.",
             "{half} of the {inning_ordinal}. {score_str}.",
             "And welcome back with us here from {venue}.",
             "And welcome back with us on this {weather_desc} here in {location}. {score_str}. {batting_team} will bring {due_up_desc} up against {pitcher_name}.",
             "And we're back from {venue} here in {location} for the {half} of the {inning_ordinal}.",
             "And we're back from {venue} here in {location_with_state} for the {half} of the {inning_ordinal}.",
             "The {half_lower} of the {inning_ordinal} inning here in {location} at {venue}. It's {score_phrase} and {due_up_desc} are due up against {pitcher_name}.",
             "Still {score_phrase} here at {venue} as we enter the {half_lower} of the {inning_ordinal}.",
             "{half} of the {inning_ordinal} here at {venue}. {score_phrase} and {batting_team} will bring {due_up_desc} up against {pitcher_name}.",
            "Welcome back to {venue}, everybody. We're about to kick off the {half_lower} of the {inning_ordinal} inning.",
            "And welcome back to {venue}. We're headed to the {half_lower} of the {inning_ordinal}.",
            "And welcome back with us here in {location_with_state}, at {venue}.",
            "And welcome back, friends, to {venue} here in {location_with_state}.",
            "{half} half of the {inning_ordinal} inning here at {venue} in {location}. {score_str}.",
        ],
        "inning_break_return": [
             "Wally McCarthy and Producer Phil back with you, from {location}.",
             "Wally McCarthy and Producer Phil back with you from {venue} here in {location}. {score_str}.",
             "Wally McCarthy and Producer Phil back with you here on this {weather_desc} in {location}. {score_str}. {batting_team} will bring {due_up_desc} up to face {pitcher_name}."
        ],
        "inning_outro_no_score": [
             "{batting_team} do not score.",
             "The {batting_team} do not score.",
             "The {batting_team} do not score and after {innings_word}, {score_recap}.",
             "No runs, {hits_str}, and {lob_str}.",
             "The {batting_team_short} do not score.",
             "{batting_team_short} do not score.",
        ],
        "inning_outro_no_score_jam": [
             "{pitcher_name} wriggles into and out of a jam and the {batting_team} do not score.",
             "The {batting_team} strand {lob_str} and they do not score.",
             "{pitcher_name} wriggles into and out of a jam and the {batting_team_short} do not score.",
            "{pitcher_name} works out of a jam.",
            "{pitcher_name} wriggles out of a jam.",
            "{pitcher_name} does a fine job getting out of that jam.",
        ],
        "inning_outro_no_score_order": [
             "The {batting_team} are retired in order.",
             "The {batting_team_short} are retired in order.",
            "And the {batting_team_short} go down in order.",
        ],
        "inning_outro_scored": [
             "The {batting_team} push a run across.",
             "The {batting_team} plate {runs_scored_word} in the {inning_ordinal}, and after {innings_word} it's {score_str}.",
             "{runs_scored_str}, {hits_str}, and {lob_str}.",
             "The {batting_team_short} push a run across.",
        ],
        "inning_outro_scored_first": [
             "But the {batting_team} break the ice, and after {innings_word}, it's {score_str}.",
             "The {batting_team} push a run across.",
             "The {batting_team} plate {runs_scored_word} in the {inning_ordinal}, and after {innings_word} it's {score_str}.",
             "But the {batting_team_short} break the ice, and after {innings_word}, it's {score_str}.",
            "But the {batting_team_short} are on the board.",
        ],
        "inning_outro_scored_pair": [
             "The {batting_team}, add another pair.",
             "The {batting_team_short}, add another pair.",
            "But the {batting_team_short} add a pair.",
            "And the {batting_team_short} add a pair here in the {inning_ordinal}.",
        ],
        "inning_outro_scored_extend": [
             "And the {batting_team} add to their lead.",
             "The {batting_team} tack on {runs_scored_word} more.",
             "And the {batting_team_short} add to their lead.",
        ],
        "inning_outro_hold": [
             "The {fielding_team}, hold on to a {score_str} lead.",
             "The {batting_team}, do not score and the {fielding_team}, hold on to a {score_str} lead.",
             "The {fielding_team_short}, hold on to a {score_str} lead.",
        ],
        "inning_outro_streak": [
             "And that's {consecutive_retired} in a row, sat down by {pitcher_name}.",
             "And that's {consecutive_retired} in a row set down by {pitcher_name}.",
             "{pitcher_name} has now retired {consecutive_retired} straight."
        ],
        "score_update_lead": [
             "and the {team_name} take a {score_lead} lead",
             "and the {team_name} take a {score_lead} lead here in the {half} of the {inning}",
             "and the {team_name} move out in front, {score_lead}",
             "and the {team_name_short} take a {score_lead} lead",
        ],
        "score_update_tied": [
             "and this game is now tied at {score}",
             "and we are all knotted up at {score}"
        ],
        "score_update_extend": [
             "and the {team_name} extend their lead to {score_lead}",
             "and the {team_name} now lead {score_lead}",
             "and the {team_name} now lead {score_lead} here in the {half} of the {inning}",
             "and the {team_name_short} extend their lead to {score_lead}",
        ],
        "inning_summary_score": [
            "And with {inning_count_word} in the books, it's {away_team_name} {score_away}, {home_team_name} {score_home}.",
            "It's {away_team_name} {score_away}, {home_team_name} {score_home} after {inning_count_word}.",
            "{away_team_name} {score_away}, {home_team_name} {score_home}.",
            "After {innings_word}, it's {away_team_name} {score_away}, {home_team_name} {score_home}.",
            "And as we head into the {next_inning_ordinal}, it's {away_team_name} {score_away}, {home_team_name} {score_home}.",
            "And with {inning_count_word} in the books, it's {away_short} {score_away}, {home_short} {score_home}.",
            "It's {away_short} {score_away}, {home_short} {score_home} after {inning_count_word}.",
            "{away_short} {score_away}, {home_short} {score_home}.",
            "After {innings_word}, it's {away_short} {score_away}, {home_short} {score_home}.",
        ],
        "inning_summary_remains": [
            "And it remains {leading_team} {leading_score_val}, {trailing_team} {score_trail}.",
            "Score remains {leading_team} {leading_score_val}, {trailing_team} {score_trail}.",
            "With {inning_count_word} in the books it remains {leading_team} {leading_score_val}, {trailing_team} {score_trail}.",
            "After {innings_word} it remains {leading_team} {leading_score_val}, {trailing_team} {score_trail}.",
            "And it remains {leading_team} {leading_score_val}, {trailing_team} {score_trail} here in {location}.",
            "And it remains {leading_short} {leading_score_val}, {trailing_short} {score_trail}.",
            "Score remains {leading_short} {leading_score_val}, {trailing_short} {score_trail}.",
            "After {innings_word} it remains {leading_short} {leading_score_val}, {trailing_short} {score_trail}.",
        ],
        "inning_summary_tied": [
            "And we are tied at {score} apiece.",
            "Score is tied at {score}.",
            "And we are all tied up at {score}.",
            "And we're still tied at {score} here in {location}.",
        ],
        "inning_summary_scoreless": [
            "And with {inning_count_word} in the books, it remains a scoreless contest.",
            "After {innings_word}, it remains a scoreless game here in {location}.",
            "We are still scoreless, here in {location}.",
            "Still a scoreless contest here at {venue}.",
            "And we remain scoreless here at {venue}.",
            "At the end of {innings_word}, we're scoreless here in {location}.",
            "We are scoreless here in {location} after {innings_word}.",
            "Still no score here at {venue}.",
            "And we're still scoreless through {innings_word} here at {venue}.",
            "We are still scoreless with {inning_count_word} in the books here at {venue}.",
            "It is still a scoreless contest at the end of {innings_word}.",
            "And it remains a scoreless ballgame.",
        ],
        "game_summary": [
            "For the victorious {win_team}, {win_runs} runs on {win_hits} hits, {win_errors} errors. And for the {lose_team}, {lose_runs} runs on {lose_hits} hits and {lose_errors} errors.",
            "Final line score tonight: The {win_team} take it with {win_runs} runs, {win_hits} hits, and {win_errors} errors. The {lose_team} fall with {lose_runs} runs on {lose_hits} hits and {lose_errors} errors.",
            "The {win_team} win it, finishing with {win_runs} runs, {win_hits} hits, and {win_errors} errors. The {lose_team} manage {lose_runs} runs, {lose_hits} hits, and {lose_errors} errors."
        ],
        "outro": [
             "Producer Phil and I will be back with the post-game show in a moment here on {network_name}.",
             "You're drifting off with {network_name}.",
            "We'll be back with the postgame show in a moment, here on {network_name}.",
        ],
            "inning_outro_no_score_bases_loaded": [
                "{pitcher_name} works his way out of a bases-loaded jam.",
                "{pitcher_name} gets out of a bases-loaded jam."
            ],
            "inning_outro_scored_stranded": [
                "{pitcher_name} prevents further damage in the {inning_ordinal} inning."
            ],
            "inning_outro_scored_take_lead": [
                "But the {batting_team_short} strike back, and they now lead {score_lead}."
            ],
            "inning_outro_no_score_pair": [
                "The {batting_team_short} strand a pair, and they do not score."
            ],
            "inning_outro_no_score_second": [
                "The {batting_team_short} strand a man on second, and they do not score."
            ],
            "inning_outro_no_score_third": [
                "The {batting_team_short} strand a man on third, and they do not score."
            ],
            "inning_break_mid_outro": [
                "And we'll be back with the bottom of the {inning_ordinal} in a moment, here on {network_name}.",
                "We'll be back with the bottom half of the {inning_ordinal} inning in a few moments.",
                "We'll be back with the bottom half of the {inning_ordinal} inning. Here on {network_name}."
            ],
        }
}
