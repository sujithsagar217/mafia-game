import os
from pathlib import Path

from flask import Flask

from .routes import game_bp


GAME_MODES = {"dedicated-host", "lobby-ready"}
DEFAULT_GAME_MODE = "dedicated-host"


def normalize_game_mode(mode: str | None) -> str:
    resolved_mode = (mode or DEFAULT_GAME_MODE).strip().lower()
    if resolved_mode not in GAME_MODES:
        raise ValueError(
            f"Unsupported game mode '{mode}'. Expected one of: {', '.join(sorted(GAME_MODES))}"
        )
    return resolved_mode


def create_app(mode: str | None = None) -> Flask:
    project_root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
    )
    app.config["GAME_MODE"] = normalize_game_mode(
        mode or os.environ.get("GAME_MODE", DEFAULT_GAME_MODE)
    )
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "mafia-game-dev-secret")
    app.config["HOST_ACCESS_CODE"] = os.environ.get("HOST_ACCESS_CODE", "mafia-host")
    app.config["PLAYER_HEARTBEAT_TIMEOUT_SECONDS"] = int(
        os.environ.get("PLAYER_HEARTBEAT_TIMEOUT_SECONDS", "15")
    )
    app.register_blueprint(game_bp)
    return app
