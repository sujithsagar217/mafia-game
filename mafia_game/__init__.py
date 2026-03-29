import os
from pathlib import Path

from flask import Flask

from .routes import game_bp


def create_app() -> Flask:
    project_root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
    )
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "mafia-game-dev-secret")
    app.config["HOST_ACCESS_CODE"] = os.environ.get("HOST_ACCESS_CODE", "mafia-host")
    app.config["PLAYER_HEARTBEAT_TIMEOUT_SECONDS"] = int(
        os.environ.get("PLAYER_HEARTBEAT_TIMEOUT_SECONDS", "15")
    )
    app.register_blueprint(game_bp)
    return app
