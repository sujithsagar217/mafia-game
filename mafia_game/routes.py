from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from .services import GameService
from .state import GameStore


game_bp = Blueprint("game", __name__)
store = GameStore()
service = GameService(store)


def error_response(message: str, status_code: int = 400):
    return jsonify({"error": message}), status_code


@game_bp.route("/")
def home():
    return render_template("index.html")


@game_bp.route("/host")
def host():
    return render_template("host.html")


@game_bp.route("/join", methods=["POST"])
def join():
    if store.game_started:
        return error_response("Game started")

    name = request.json.get("name") if request.is_json else None
    return jsonify(service.add_player(name))


@game_bp.route("/players")
def get_players():
    return jsonify(store.players)


@game_bp.route("/start", methods=["POST"])
def start_game():
    ok, error = service.start_game()
    if not ok:
        return error_response(error)
    return jsonify({"message": "started"})


@game_bp.route("/role/<name>")
def get_role(name: str):
    if not store.game_started or name not in store.roles:
        return jsonify({"role": None})
    return jsonify({"role": store.roles[name]})


@game_bp.route("/all_roles")
def all_roles():
    return jsonify(store.roles)


@game_bp.route("/game_state")
def get_game_state():
    return jsonify(store.game_state.to_dict())


@game_bp.route("/action", methods=["POST"])
def submit_action():
    data = request.get_json(force=True)
    ok, error = service.submit_night_action(data["name"], data["target"])
    if not ok:
        return error_response(error)
    return jsonify({"ok": True})


@game_bp.route("/suggest", methods=["POST"])
def suggest():
    data = request.get_json(force=True)
    ok, error = service.submit_mafia_suggestion(data["name"], data["target"])
    if not ok:
        return error_response(error)
    return jsonify({"ok": True})


@game_bp.route("/suggestions")
def get_suggestions():
    return jsonify(store.mafia_suggestions)


@game_bp.route("/actions")
def get_actions():
    return jsonify(
        {
            "doctor": store.actions["doctor"],
            "police": store.actions["police"],
            "mafia_votes": store.mafia_votes,
        }
    )


@game_bp.route("/resolve", methods=["POST"])
def resolve_night():
    ok, error, eliminated = service.resolve_night()
    if not ok:
        return error_response(error)
    return jsonify({"eliminated": eliminated})


@game_bp.route("/start_voting", methods=["POST"])
def start_voting():
    ok, error = service.start_voting()
    if not ok:
        return error_response(error)
    return jsonify({"message": "voting started"})


@game_bp.route("/vote", methods=["POST"])
def vote():
    data = request.get_json(force=True)
    ok, error = service.submit_vote(data["name"], data["target"])
    if not ok:
        return error_response(error)
    return jsonify({"message": "vote updated"})


@game_bp.route("/votes")
def get_votes():
    return jsonify({"counts": store.votes, "individual": store.voted})


@game_bp.route("/end_vote", methods=["POST"])
def end_vote():
    if not store.votes:
        return jsonify({"message": "No votes"})

    ok, error, eliminated = service.end_vote()
    if not ok:
        return error_response(error)

    return jsonify({"eliminated": eliminated})


@game_bp.route("/vote_history")
def get_vote_history():
    return jsonify(store.vote_history)


@game_bp.route("/reset", methods=["POST"])
def reset_game():
    service.reset_game()
    return jsonify({"message": "Game reset"})


@game_bp.route("/game_result")
def game_result():
    return jsonify({"winner": store.game_state.winner})


@game_bp.route("/police_reports/<name>")
def get_reports(name: str):
    return jsonify(store.police_reports.get(name, []))


@game_bp.route("/next_round", methods=["POST"])
def next_round():
    service.next_round()
    return jsonify({"message": "next"})
