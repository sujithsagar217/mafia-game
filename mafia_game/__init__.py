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
    app.register_blueprint(game_bp)
    return app
