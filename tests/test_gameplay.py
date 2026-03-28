import unittest

from mafia_game import create_app
from mafia_game.routes import service, store


class MafiaGameTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.reset_store()

    def tearDown(self):
        self.reset_store()

    def reset_store(self):
        service.reset_game()
        store.players = []
        store.roles = {}
        store.game_started = False
        store.game_state.alive = []
        store.game_state.eliminated = []
        store.game_state.phase = "waiting"
        store.game_state.round = 1
        store.game_state.winner = None
        store.actions = {"doctor": None, "police": None}
        store.mafia_votes = {}
        store.mafia_suggestions = {}
        store.police_reports = {}
        store.votes = {}
        store.voted = {}
        store.vote_history = []

    def join_players(self, names):
        for name in names:
            response = self.client.post("/join", json={"name": name})
            self.assertEqual(response.status_code, 200)

    def start_four_player_game(self):
        players = ["A", "B", "C", "D"]
        self.join_players(players)
        response = self.client.post("/start")
        self.assertEqual(response.status_code, 200)
        return response

    def test_join_and_duplicate_names(self):
        response = self.client.post("/join", json={"name": "Alice"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), ["Alice"])

        response = self.client.post("/join", json={"name": "Alice"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), ["Alice"])

    def test_role_is_none_before_game_start(self):
        self.join_players(["Alice"])
        response = self.client.get("/role/Alice")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"role": None})

    def test_cannot_start_with_fewer_than_four_players(self):
        self.join_players(["A", "B", "C"])
        response = self.client.post("/start")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Minimum 4 players required")

    def test_role_distribution_for_four_players(self):
        self.start_four_player_game()
        roles = self.client.get("/all_roles").get_json()

        self.assertEqual(len(roles), 4)
        self.assertEqual(sum(role == "Mafia" for role in roles.values()), 1)
        self.assertEqual(sum(role == "Doctor" for role in roles.values()), 1)
        self.assertEqual(sum(role == "Police" for role in roles.values()), 1)
        self.assertEqual(sum(role == "Villager" for role in roles.values()), 1)

    def test_role_distribution_for_six_players(self):
        self.join_players(["A", "B", "C", "D", "E", "F"])
        response = self.client.post("/start")
        self.assertEqual(response.status_code, 200)
        roles = self.client.get("/all_roles").get_json()

        self.assertEqual(sum(role == "Mafia" for role in roles.values()), 2)
        self.assertEqual(sum(role == "Doctor" for role in roles.values()), 1)
        self.assertEqual(sum(role == "Police" for role in roles.values()), 1)
        self.assertEqual(sum(role == "Villager" for role in roles.values()), 2)

    def test_doctor_save_and_police_report(self):
        self.start_four_player_game()
        roles = self.client.get("/all_roles").get_json()

        mafia = next(name for name, role in roles.items() if role == "Mafia")
        doctor = next(name for name, role in roles.items() if role == "Doctor")
        police = next(name for name, role in roles.items() if role == "Police")
        villager = next(name for name, role in roles.items() if role == "Villager")

        self.client.post("/action", json={"name": mafia, "target": villager})
        self.client.post("/action", json={"name": doctor, "target": villager})
        self.client.post("/action", json={"name": police, "target": mafia})

        response = self.client.post("/resolve")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.get_json()["eliminated"])

        game_state = self.client.get("/game_state").get_json()
        self.assertIn(villager, game_state["alive"])
        self.assertEqual(game_state["phase"], "day")

        reports = self.client.get(f"/police_reports/{police}").get_json()
        self.assertIn(f"{mafia} is Mafia", reports)

    def test_non_police_player_has_no_police_reports(self):
        self.start_four_player_game()
        roles = self.client.get("/all_roles").get_json()
        non_police = next(name for name, role in roles.items() if role != "Police")

        response = self.client.get(f"/police_reports/{non_police}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])

    def test_police_reports_persist_across_multiple_rounds(self):
        self.start_four_player_game()
        roles = self.client.get("/all_roles").get_json()

        mafia = next(name for name, role in roles.items() if role == "Mafia")
        doctor = next(name for name, role in roles.items() if role == "Doctor")
        police = next(name for name, role in roles.items() if role == "Police")
        villager = next(name for name, role in roles.items() if role == "Villager")

        self.client.post("/action", json={"name": mafia, "target": villager})
        self.client.post("/action", json={"name": doctor, "target": doctor})
        self.client.post("/action", json={"name": police, "target": mafia})
        self.client.post("/resolve")

        self.client.post("/start_voting")
        self.client.post("/vote", json={"name": mafia, "target": villager})
        self.client.post("/vote", json={"name": doctor, "target": mafia})
        self.client.post("/vote", json={"name": police, "target": villager})
        self.client.post("/vote", json={"name": villager, "target": mafia})
        self.client.post("/end_vote")

        self.client.post("/action", json={"name": doctor, "target": doctor})
        self.client.post("/action", json={"name": police, "target": villager})
        self.client.post("/resolve")

        reports = self.client.get(f"/police_reports/{police}").get_json()
        self.assertEqual(len(reports), 2)
        self.assertEqual(reports[0], f"{mafia} is Mafia")
        self.assertEqual(reports[1], f"{villager} is NOT Mafia")

    def test_mafia_cannot_target_fellow_mafia(self):
        self.join_players(["A", "B", "C", "D", "E", "F"])
        self.client.post("/start")
        roles = self.client.get("/all_roles").get_json()
        mafia_players = [name for name, role in roles.items() if role == "Mafia"]

        response = self.client.post(
            "/action",
            json={"name": mafia_players[0], "target": mafia_players[1]},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Cannot target fellow mafia")

    def test_non_mafia_cannot_submit_suggestion(self):
        self.start_four_player_game()
        roles = self.client.get("/all_roles").get_json()
        non_mafia = next(name for name, role in roles.items() if role != "Mafia")
        target = next(name for name in roles if name != non_mafia)

        response = self.client.post("/suggest", json={"name": non_mafia, "target": target})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Only mafia can suggest")

    def test_action_is_blocked_outside_night_phase(self):
        self.start_four_player_game()
        self.client.post("/resolve")
        roles = self.client.get("/all_roles").get_json()
        actor = next(iter(roles))
        target = next(name for name in roles if name != actor)

        response = self.client.post("/action", json={"name": actor, "target": target})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Not night phase")

    def test_start_voting_is_blocked_outside_day_phase(self):
        self.start_four_player_game()
        response = self.client.post("/start_voting")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Not day phase")

    def test_vote_is_blocked_for_self_vote(self):
        self.start_four_player_game()
        self.client.post("/resolve")
        self.client.post("/start_voting")

        response = self.client.post("/vote", json={"name": "A", "target": "A"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Cannot vote yourself")

    def test_dead_player_cannot_vote(self):
        self.start_four_player_game()
        self.client.post("/resolve")
        self.client.post("/start_voting")
        self.client.post("/vote", json={"name": "A", "target": "D"})
        self.client.post("/vote", json={"name": "B", "target": "D"})
        self.client.post("/vote", json={"name": "C", "target": "D"})
        self.client.post("/end_vote")

        response = self.client.post("/vote", json={"name": "D", "target": "A"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Voting not active")

    def test_dead_player_cannot_act_at_night(self):
        self.start_four_player_game()
        self.client.post("/resolve")
        self.client.post("/start_voting")
        self.client.post("/vote", json={"name": "A", "target": "D"})
        self.client.post("/vote", json={"name": "B", "target": "D"})
        self.client.post("/vote", json={"name": "C", "target": "D"})
        self.client.post("/end_vote")

        response = self.client.post("/action", json={"name": "D", "target": "A"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Dead players cannot act")

    def test_voting_flow_and_round_progression(self):
        self.start_four_player_game()
        roles = self.client.get("/all_roles").get_json()
        alive_players = list(roles.keys())

        self.client.post("/resolve")
        self.client.post("/start_voting")

        voters = alive_players[:3]
        target = alive_players[3]
        for voter in voters:
            self.client.post("/vote", json={"name": voter, "target": target})

        votes = self.client.get("/votes").get_json()
        self.assertEqual(votes["counts"][target], 3)
        self.assertEqual(len(votes["individual"]), 3)

        end_vote_response = self.client.post("/end_vote")
        self.assertEqual(end_vote_response.status_code, 200)
        self.assertEqual(end_vote_response.get_json()["eliminated"], target)

        game_state = self.client.get("/game_state").get_json()
        self.assertEqual(game_state["phase"], "night")
        self.assertEqual(game_state["round"], 2)
        self.assertIn(target, game_state["eliminated"])

        votes_after = self.client.get("/votes").get_json()
        self.assertEqual(votes_after["counts"], {})
        self.assertEqual(votes_after["individual"], {})

    def test_end_vote_without_votes_returns_no_votes_message(self):
        self.start_four_player_game()
        self.client.post("/resolve")
        self.client.post("/start_voting")

        response = self.client.post("/end_vote")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["message"], "No votes")

    def test_join_is_blocked_mid_game(self):
        self.start_four_player_game()
        response = self.client.post("/join", json={"name": "Late"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Game started")

    def test_leave_removes_player_from_lobby_and_alive_state(self):
        self.start_four_player_game()
        leaving_player = "C"

        response = self.client.post("/leave", json={"name": leaving_player})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["removed"])

        players = self.client.get("/players").get_json()
        self.assertNotIn(leaving_player, players)

        state = self.client.get("/game_state").get_json()
        self.assertNotIn(leaving_player, state["alive"])
        self.assertIn(leaving_player, state["eliminated"])

    def test_leave_cleans_up_live_votes(self):
        self.start_four_player_game()
        self.client.post("/resolve")
        self.client.post("/start_voting")

        self.client.post("/vote", json={"name": "A", "target": "D"})
        self.client.post("/vote", json={"name": "B", "target": "D"})
        self.client.post("/vote", json={"name": "C", "target": "A"})

        response = self.client.post("/leave", json={"name": "D"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["removed"])

        votes = self.client.get("/votes").get_json()
        self.assertEqual(votes["counts"], {"A": 1})
        self.assertEqual(votes["individual"], {"C": "A"})

    def test_leave_unknown_player_returns_false(self):
        response = self.client.post("/leave", json={"name": "Ghost"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"removed": False})

    def test_reset_clears_match_state_but_keeps_joined_players(self):
        self.start_four_player_game()
        response = self.client.post("/reset")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["message"], "Game reset")

        players = self.client.get("/players").get_json()
        game_state = self.client.get("/game_state").get_json()
        roles = self.client.get("/all_roles").get_json()

        self.assertEqual(players, ["A", "B", "C", "D"])
        self.assertEqual(roles, {})
        self.assertEqual(game_state["phase"], "waiting")
        self.assertEqual(game_state["alive"], [])
        self.assertEqual(game_state["eliminated"], [])
        self.assertIsNone(game_state["winner"])

    def test_villagers_win_when_all_mafia_are_removed(self):
        self.start_four_player_game()
        roles = self.client.get("/all_roles").get_json()
        mafia = next(name for name, role in roles.items() if role == "Mafia")

        store.game_state.alive.remove(mafia)
        store.game_state.eliminated.append(mafia)
        service.check_winner()

        response = self.client.get("/game_result")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["winner"], "Villagers")

    def test_mafia_win_when_mafia_count_reaches_parity(self):
        self.join_players(["A", "B", "C", "D", "E", "F"])
        self.client.post("/start")
        roles = self.client.get("/all_roles").get_json()
        mafia_players = [name for name, role in roles.items() if role == "Mafia"]
        non_mafia_players = [name for name, role in roles.items() if role != "Mafia"]

        store.game_state.alive = mafia_players + non_mafia_players[:2]
        store.game_state.eliminated = non_mafia_players[2:]
        service.check_winner()

        response = self.client.get("/game_result")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["winner"], "Mafia")


if __name__ == "__main__":
    unittest.main(verbosity=2)
