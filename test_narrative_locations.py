"""Regression coverage for place names used in generated broadcast dialogue."""

from collections import defaultdict
from copy import deepcopy
import unittest
from unittest.mock import patch

from anonymize_real_gameday import anonymize_gameday_data
from baseball import BaseballSimulator
from commentary import GAME_CONTEXT
from renderers import NarrativeRenderer
from renderers.narrative.helpers import get_location_phrases
from teams import TEAMS


class TestNarrativeLocations(unittest.TestCase):
    def test_city_defaults_and_missing_state(self):
        cases = [
            ({"locationName": "Pacific City", "state": "Oregon"},
             "Pacific City", "Pacific City, Oregon"),
            ({"locationName": "Pacific City"}, "Pacific City", "Pacific City"),
            ({"locationName": "Pacific City", "state": ""},
             "Pacific City", "Pacific City"),
            ({"name": "Lake City Loons", "state": "Minnesota"},
             "Lake City", "Lake City, Minnesota"),
            ({"name": "Lake City Loons", "locationName": ""},
             "Lake City", "Lake City"),
        ]
        for team, short, full in cases:
            with self.subTest(team=team):
                self.assertEqual(get_location_phrases(team), {
                    "location": short, "location_with_state": full,
                })

    def test_region_phrases_are_explicit_and_preserve_team_identity(self):
        bay = deepcopy(TEAMS["BAY_BOMBERS"])
        self.assertEqual(get_location_phrases(bay), {
            "location": "the Bay Area",
            "location_with_state": "California's Bay Area",
        })
        self.assertEqual(bay["name"], "Bay Area Bombers")
        self.assertEqual(bay["locationName"], "Bay Area")

        custom_team = {
            "name": "Coastal Vipers", "locationName": "Coastal", "state": "Florida",
            "spokenLocation": "the coast",
            "spokenLocationWithState": "coastal Florida",
        }
        self.assertEqual(get_location_phrases(custom_team), {
            "location": "the coast", "location_with_state": "coastal Florida",
        })

    def test_every_location_template_handles_regions_and_cities_without_states(self):
        teams = [TEAMS["BAY_BOMBERS"], {"locationName": "Pacific City"}]
        checked = 0
        for pool, templates in GAME_CONTEXT["radio_strings"].items():
            for template in templates:
                if not any(token in template for token in ("{city}", "{state}", "{location")):
                    continue
                checked += 1
                for team in teams:
                    with self.subTest(pool=pool, template=template, team=team["locationName"]):
                        phrases = get_location_phrases(team)
                        context = defaultdict(lambda: "example", phrases)
                        text = template.format_map(context)
                        self.assertNotIn("{city}", template)
                        self.assertNotIn("{state}", template)
                        self.assertNotIn("in Bay Area", text)
                        self.assertNotIn("Bay Area, California", text)
                        self.assertNotIn(", .", text)
                        self.assertNotIn(",  ", text)
                        self.assertNotIn(", ,", text)
                        self.assertTrue(any(phrase in text for phrase in phrases.values()))
        self.assertGreater(checked, 10)

    @staticmethod
    def _new_game(home_key="BAY_BOMBERS", away_key="PC_PILOTS"):
        game = BaseballSimulator(
            deepcopy(TEAMS[home_key]), deepcopy(TEAMS[away_key]),
            max_innings=3, game_seed=1,
        )
        game.play_game()
        return game

    def test_new_home_game_uses_region_phrases_throughout_broadcast(self):
        game = self._new_game()
        renderer = NarrativeRenderer(game.gameday_data, seed=1)
        with patch.object(renderer, "_get_radio_string", wraps=renderer._get_radio_string) as radio:
            text = renderer.render()

        self.assertIn("Waterfront Park in California's Bay Area", text)
        self.assertIn("here in the Bay Area", text)
        self.assertIn("Bay Area Bombers", text)
        self.assertNotIn("in Bay Area", text)
        self.assertNotIn("Bay Area, California", text)
        self.assertNotIn("the the Bay Area", text)
        location_calls = 0
        for call in radio.call_args_list:
            pool = call.args[0]
            if any("{location" in template for template in GAME_CONTEXT["radio_strings"].get(pool, [])):
                location_calls += 1
                self.assertEqual(call.args[1]["location"], "the Bay Area")
                self.assertEqual(call.args[1]["location_with_state"], "California's Bay Area")
        self.assertGreater(location_calls, 0)

    def test_away_region_uses_full_phrase_in_pregame_introduction(self):
        game = self._new_game("PC_PILOTS", "BAY_BOMBERS")
        text = NarrativeRenderer(game.gameday_data, seed=1).render()
        self.assertIn("Aero Field in Pacific City, Oregon", text)
        self.assertIn("hosting the Bay Area Bombers of California's Bay Area", text)
        self.assertNotIn("of Bay Area, California", text)
        self.assertEqual(game.gameday_data["gameData"]["teams"]["away"]["locationName"], "Bay Area")

    def test_anonymized_games_keep_spoken_location_overrides(self):
        fictional_teams = {
            "BAY_BOMBERS": deepcopy(TEAMS["BAY_BOMBERS"]),
            "PC_PILOTS": deepcopy(TEAMS["PC_PILOTS"]),
        }
        fictional_teams["PC_PILOTS"]["spokenLocation"] = "the Pacific coast"
        fictional_teams["PC_PILOTS"]["spokenLocationWithState"] = "Oregon's Pacific coast"
        result = anonymize_gameday_data(
            {"gameData": {"teams": {"home": {}, "away": {}}}}, fictional_teams,
        )
        for side, key in (("home", "BAY_BOMBERS"), ("away", "PC_PILOTS")):
            with self.subTest(side=side):
                output = result["gameData"]["teams"][side]
                source = fictional_teams[key]
                for field in ("name", "locationName", "spokenLocation", "spokenLocationWithState"):
                    self.assertEqual(output[field], source[field])

    def test_spoken_location_metadata_does_not_change_simulation(self):
        with_metadata = self._new_game()
        home = deepcopy(TEAMS["BAY_BOMBERS"])
        home.pop("spokenLocation", None)
        home.pop("spokenLocationWithState", None)
        without_metadata = BaseballSimulator(
            home, deepcopy(TEAMS["PC_PILOTS"]), max_innings=3, game_seed=1,
        )
        without_metadata.play_game()
        self.assertEqual(with_metadata.gameday_data["liveData"], without_metadata.gameday_data["liveData"])


if __name__ == "__main__":
    unittest.main()
