import argparse
import os
import random
from typing import Dict, List

from mafia_game import create_app
from mafia_game.routes import service, store


def hard_reset() -> None:
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


def choose_target(options: List[str]) -> str:
    return random.choice(options)


def print_section(title: str) -> None:
    print(f"\n{'=' * 18} {title} {'=' * 18}")


def print_state(state: Dict) -> None:
    print(f"Round: {state['round']}")
    print(f"Phase: {state['phase']}")
    print(f"Alive: {state['alive']}")
    print(f"Dead: {state['eliminated']}")
    print(f"Winner: {state['winner']}")


def simulate_game(player_count: int, seed: int, max_rounds: int) -> int:
    if player_count < 4:
        print("Simulation requires at least 4 players.")
        return 1

    random.seed(seed)
    hard_reset()

    app = create_app()
    client = app.test_client()

    players = [f"Player{i}" for i in range(1, player_count + 1)]

    print_section("Simulation Setup")
    print(f"Seed: {seed}")
    print(f"Players requested: {player_count}")
    print(f"Players: {players}")

    for player in players:
        response = client.post("/join", json={"name": player})
        if response.status_code != 200:
            print(f"Failed to join {player}: {response.get_json()}")
            return 1

    print("\nJoined players:")
    print(client.get("/players").get_json())

    host_access_code = app.config.get(
        "HOST_ACCESS_CODE",
        os.environ.get("HOST_ACCESS_CODE", "mafia-host"),
    )
    host_login_response = client.post(
        "/host/login",
        json={"access_code": host_access_code},
    )
    if host_login_response.status_code != 200:
        print(f"Unable to log in as host: {host_login_response.get_json()}")
        return 1

    start_response = client.post("/start")
    if start_response.status_code != 200:
        print(f"Unable to start game: {start_response.get_json()}")
        return 1

    roles = client.get("/all_roles").get_json()
    police_player = next((name for name, role in roles.items() if role == "Police"), None)

    print_section("Assigned Roles")
    for player in sorted(roles):
        print(f"{player}: {roles[player]}")

    state = client.get("/game_state").get_json()
    print_section("Initial State")
    print_state(state)

    while not state["winner"] and state["round"] <= max_rounds:
        alive = state["alive"][:]
        alive_roles = {player: roles[player] for player in alive}
        print_section(f"Night Round {state['round']}")
        print(f"Alive roles this round: {alive_roles}")

        mafia_players = [player for player in alive if roles[player] == "Mafia"]
        non_mafia_alive = [player for player in alive if roles[player] != "Mafia"]
        doctor_players = [player for player in alive if roles[player] == "Doctor"]
        police_players = [player for player in alive if roles[player] == "Police"]

        if mafia_players and non_mafia_alive:
            mafia_target = choose_target(non_mafia_alive)
            for mafia_player in mafia_players:
                suggest_response = client.post(
                    "/suggest", json={"name": mafia_player, "target": mafia_target}
                )
                action_response = client.post(
                    "/action", json={"name": mafia_player, "target": mafia_target}
                )
                print(
                    f"Mafia {mafia_player} suggested and voted for {mafia_target} | "
                    f"suggest={suggest_response.status_code} action={action_response.status_code}"
                )

        if doctor_players:
            doctor = doctor_players[0]
            save_target = choose_target(alive)
            response = client.post("/action", json={"name": doctor, "target": save_target})
            print(f"Doctor {doctor} saved {save_target} | status={response.status_code}")

        if police_players:
            police = police_players[0]
            police_targets = [player for player in alive if player != police]
            if police_targets:
                investigate_target = choose_target(police_targets)
                response = client.post(
                    "/action", json={"name": police, "target": investigate_target}
                )
                print(
                    f"Police {police} investigated {investigate_target} | status={response.status_code}"
                )

        print("\nNight actions snapshot:")
        print(client.get("/actions").get_json())
        print("Mafia suggestions snapshot:")
        print(client.get("/suggestions").get_json())

        resolve_response = client.post("/resolve")
        print("\nNight resolution:")
        print(resolve_response.get_json())

        state = client.get("/game_state").get_json()
        print_state(state)

        if police_player:
            print(f"Police reports for {police_player}:")
            print(client.get(f"/police_reports/{police_player}").get_json())

        if state["winner"]:
            break

        print_section(f"Day Round {state['round']}")
        start_vote_response = client.post("/start_voting")
        print(f"Start voting response: {start_vote_response.get_json()}")

        voting_state = client.get("/game_state").get_json()
        alive = voting_state["alive"][:]

        for voter in alive:
            targets = [player for player in alive if player != voter]
            if not targets:
                continue
            target = choose_target(targets)
            vote_response = client.post("/vote", json={"name": voter, "target": target})
            live_votes = client.get("/votes").get_json()
            print(
                f"{voter} voted for {target} | status={vote_response.status_code} | "
                f"live votes={live_votes}"
            )

        end_vote_response = client.post("/end_vote")
        print("\nVoting result:")
        print(end_vote_response.get_json())
        print("Vote history:")
        print(client.get("/vote_history").get_json())

        state = client.get("/game_state").get_json()
        print_state(state)

    print_section("Final Result")
    final_result = client.get("/game_result").get_json()
    print(final_result)

    if not final_result["winner"]:
        print(f"Stopped after reaching max rounds ({max_rounds}) without a winner.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Simulate a full Mafia game and print the gameplay step by step."
    )
    parser.add_argument(
        "--players",
        type=int,
        help="Number of players to simulate. Minimum is 4.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="Random seed used for deterministic simulation output.",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=20,
        help="Maximum rounds before the simulation stops.",
    )
    args = parser.parse_args()

    player_count = args.players
    if player_count is None:
        player_count = int(input("Enter number of players to simulate: ").strip())

    return simulate_game(player_count, args.seed, args.max_rounds)


if __name__ == "__main__":
    raise SystemExit(main())
