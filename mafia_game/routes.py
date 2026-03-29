from __future__ import annotations

from functools import wraps

from flask import Blueprint, current_app, jsonify, render_template, request, session

from .services import GameService
from .state import GameStore


game_bp = Blueprint("game", __name__)
store = GameStore()
service = GameService(store)


def error_response(message: str, status_code: int = 400):
    return jsonify({"error": message}), status_code


def _game_mode() -> str:
    return current_app.config["GAME_MODE"]


def _is_lobby_ready_mode() -> bool:
    return _game_mode() == "lobby-ready"


def _template_config() -> dict[str, str]:
    return {"game_mode": _game_mode()}


def prune_inactive_players() -> None:
    service.prune_inactive_players(
        current_app.config["PLAYER_HEARTBEAT_TIMEOUT_SECONDS"],
        _game_mode(),
    )


def require_host_access(route_func):
    @wraps(route_func)
    def wrapper(*args, **kwargs):
        if not _session_has_host_access():
            return error_response("Host access required", 403)
        return route_func(*args, **kwargs)

    return wrapper


def _session_is_assigned_host() -> bool:
    return bool(
        store.game_started
        and session.get("player_name")
        and session.get("player_name") == store.host_name
    )


def _session_has_host_access() -> bool:
    if _is_lobby_ready_mode():
        return _session_is_assigned_host()
    return bool(session.get("is_host"))


@game_bp.route("/")
def home():
    prune_inactive_players()
    return render_template("index.html", app_config=_template_config(), game_mode=_game_mode())


@game_bp.route("/host")
def host():
    prune_inactive_players()
    return render_template("host.html", app_config=_template_config(), game_mode=_game_mode())


@game_bp.route("/host/status")
def host_status():
    prune_inactive_players()
    return jsonify(
        {
            "authorized": _session_has_host_access(),
            "mode": _game_mode(),
            "assigned_host": store.host_name,
            "current_player": session.get("player_name"),
            "game_started": store.game_started,
        }
    )


@game_bp.route("/host/login", methods=["POST"])
def host_login():
    if _is_lobby_ready_mode():
        return error_response(
            "Host login is only used in dedicated-host mode",
            400,
        )

    payload = request.get_json(silent=True) or {}
    access_code = payload.get("access_code", "")

    if access_code != current_app.config["HOST_ACCESS_CODE"]:
        session["is_host"] = False
        return error_response("Invalid host access code", 403)

    session["is_host"] = True
    return jsonify({"authorized": True})


@game_bp.route("/host/claim", methods=["POST"])
def host_claim():
    if not _is_lobby_ready_mode():
        return error_response("Host claim is only used in lobby-ready mode", 400)

    payload = request.get_json(silent=True) or {}
    name = payload.get("name") or session.get("player_name")

    if not store.game_started:
        return error_response("The game has not started yet", 400)

    if not name or name not in store.players:
        return error_response("Join the lobby before claiming host access", 404)

    session["player_name"] = name

    if store.host_name != name:
        return error_response("You are not the assigned host for this match", 403)

    return jsonify({"authorized": True})


@game_bp.route("/join", methods=["POST"])
def join():
    prune_inactive_players()
    if store.game_started:
        return error_response("Game started")

    name = request.json.get("name") if request.is_json else None
    players = service.add_player(name)
    if name:
        session["player_name"] = name
    return jsonify(players)


@game_bp.route("/leave", methods=["POST"])
def leave():
    prune_inactive_players()
    payload = request.get_json(silent=True) or {}
    name = payload.get("name")

    if not service.remove_player(name, _game_mode()):
        return jsonify({"removed": False})

    if session.get("player_name") == name:
        session.pop("player_name", None)

    return jsonify({"removed": True})


@game_bp.route("/players")
def get_players():
    prune_inactive_players()
    return jsonify(store.players)


@game_bp.route("/lobby")
def lobby():
    prune_inactive_players()
    ready = {player: store.ready_players.get(player, False) for player in store.players}
    return jsonify(
        {
            "mode": _game_mode(),
            "players": store.players,
            "ready": ready,
            "ready_count": sum(1 for value in ready.values() if value),
            "all_ready": bool(store.players) and all(ready.values()) if _is_lobby_ready_mode() else False,
            "minimum_players": 5 if _is_lobby_ready_mode() else 4,
            "game_started": store.game_started,
            "host_name": store.host_name,
        }
    )


@game_bp.route("/ready", methods=["POST"])
def ready():
    prune_inactive_players()
    payload = request.get_json(silent=True) or {}
    name = payload.get("name")
    is_ready = bool(payload.get("ready", True))

    ok, error, started = service.set_ready(name, is_ready, _game_mode())
    if not ok:
        return error_response(error, 404 if error == "Unknown player" else 400)

    return jsonify(
        {
            "ready": store.ready_players.get(name, False),
            "started": started,
            "host_name": store.host_name,
        }
    )


@game_bp.route("/heartbeat", methods=["POST"])
def heartbeat():
    payload = request.get_json(silent=True) or {}
    name = payload.get("name")

    if not service.touch_player(name):
        return error_response("Unknown player", 404)

    prune_inactive_players()
    return jsonify({"ok": True})


@game_bp.route("/start", methods=["POST"])
def start_game():
    prune_inactive_players()
    if _is_lobby_ready_mode():
        return error_response("Lobby-ready mode starts automatically once everyone is ready")
    if not _session_has_host_access():
        return error_response("Host access required", 403)

    ok, error = service.start_game(_game_mode())
    if not ok:
        return error_response(error)
    return jsonify({"message": "started"})


@game_bp.route("/role/<name>")
def get_role(name: str):
    prune_inactive_players()
    if not store.game_started or name not in store.roles:
        return jsonify({"role": None})
    role = store.roles[name]
    response = {"role": role}
    if role == "Mafia":
        response["mafia_team"] = [
            player
            for player, player_role in store.roles.items()
            if player_role == "Mafia" and player != name
        ]
    return jsonify(response)


@game_bp.route("/all_roles")
@require_host_access
def all_roles():
    prune_inactive_players()
    return jsonify(store.roles)


@game_bp.route("/game_state")
def get_game_state():
    prune_inactive_players()
    return jsonify(store.game_state.to_dict())


@game_bp.route("/action", methods=["POST"])
def submit_action():
    prune_inactive_players()
    data = request.get_json(force=True)
    ok, error = service.submit_night_action(data["name"], data["target"], _game_mode())
    if not ok:
        return error_response(error)
    return jsonify({"ok": True})


@game_bp.route("/suggest", methods=["POST"])
def suggest():
    prune_inactive_players()
    data = request.get_json(force=True)
    ok, error = service.submit_mafia_suggestion(data["name"], data["target"])
    if not ok:
        return error_response(error)
    return jsonify({"ok": True})


@game_bp.route("/suggestions")
@require_host_access
def get_suggestions():
    prune_inactive_players()
    return jsonify(store.mafia_suggestions)


@game_bp.route("/suggestions/<name>")
def get_player_suggestions(name: str):
    prune_inactive_players()
    if store.roles.get(name) != "Mafia":
        return jsonify({})
    return jsonify(store.mafia_suggestions)


@game_bp.route("/actions")
@require_host_access
def get_actions():
    prune_inactive_players()
    alive_players = set(store.game_state.alive)
    doctor_player = next(
        (player for player, role in store.roles.items() if role == "Doctor"),
        None,
    )
    police_player = next(
        (player for player, role in store.roles.items() if role == "Police"),
        None,
    )
    mafia_players = [player for player, role in store.roles.items() if role == "Mafia"]

    def action_status(player: str | None, action_value: str | None) -> str:
        if not player:
            return "Unavailable"
        if player not in alive_players:
            return "Eliminated"
        if action_value:
            return "Submitted"
        return "Pending"

    return jsonify(
        {
            "doctor": store.actions["doctor"],
            "doctor_player": doctor_player,
            "doctor_status": action_status(doctor_player, store.actions["doctor"]),
            "police": store.actions["police"],
            "police_player": police_player,
            "police_status": action_status(police_player, store.actions["police"]),
            "mafia_votes": store.mafia_votes,
            "mafia_players": mafia_players,
            "mafia_alive": [player for player in mafia_players if player in alive_players],
            "mafia_eliminated": [player for player in mafia_players if player not in alive_players],
        }
    )


@game_bp.route("/resolve", methods=["POST"])
@require_host_access
def resolve_night():
    prune_inactive_players()
    ok, error, eliminated = service.resolve_night()
    if not ok:
        return error_response(error)
    return jsonify({"eliminated": eliminated})


@game_bp.route("/start_voting", methods=["POST"])
@require_host_access
def start_voting():
    prune_inactive_players()
    ok, error = service.start_voting()
    if not ok:
        return error_response(error)
    return jsonify({"message": "voting started"})


@game_bp.route("/vote", methods=["POST"])
def vote():
    prune_inactive_players()
    data = request.get_json(force=True)
    ok, error = service.submit_vote(data["name"], data["target"])
    if not ok:
        return error_response(error)
    return jsonify({"message": "vote updated"})


@game_bp.route("/votes")
def get_votes():
    prune_inactive_players()
    return jsonify({"counts": store.votes, "individual": store.voted})


@game_bp.route("/end_vote", methods=["POST"])
@require_host_access
def end_vote():
    prune_inactive_players()
    if not store.votes:
        return jsonify({"message": "No votes"})

    ok, error, eliminated, tied = service.end_vote()
    if not ok:
        return error_response(error)

    if tied:
        return jsonify({"eliminated": None, "message": "Tie vote - nobody eliminated"})

    return jsonify({"eliminated": eliminated, "message": "Vote resolved"})


@game_bp.route("/vote_history")
@require_host_access
def get_vote_history():
    prune_inactive_players()
    return jsonify(store.vote_history)


@game_bp.route("/reset", methods=["POST"])
@require_host_access
def reset_game():
    prune_inactive_players()
    service.reset_game()
    return jsonify({"message": "Game reset"})


@game_bp.route("/game_result")
def game_result():
    prune_inactive_players()
    return jsonify({"winner": store.game_state.winner})


@game_bp.route("/police_reports/<name>")
def get_reports(name: str):
    prune_inactive_players()
    return jsonify(store.police_reports.get(name, []))


@game_bp.route("/next_round", methods=["POST"])
@require_host_access
def next_round():
    prune_inactive_players()
    service.next_round()
    return jsonify({"message": "next"})
