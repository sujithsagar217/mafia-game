import unittest

from mafia_game import create_app


class UiContractTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_player_page_contains_live_vote_panel_and_police_box(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('id="liveVoteBox"', html)
        self.assertIn('id="policeBox"', html)

    def test_host_page_contains_alive_dead_lists_and_no_next_round_button(self):
        response = self.client.get("/host")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('id="hostAuthPanel"', html)
        self.assertIn('id="hostAccessCode"', html)
        self.assertIn('id="hostPanel"', html)
        self.assertIn('id="alivePlayers"', html)
        self.assertIn('id="deadPlayers"', html)
        self.assertNotIn('id="nextBtn"', html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
