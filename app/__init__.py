import os
from flask import Flask, send_from_directory
from app.config import BASE_DIR, SECRET_KEY
from app.routes.api import api_bp

def create_app():
    static_folder = str(BASE_DIR / "static")
    app = Flask(__name__, static_folder=static_folder, static_url_path="")
    app.config["SECRET_KEY"] = SECRET_KEY

    # Register API blueprint
    app.register_blueprint(api_bp)

    # Web Page routes (SPA routing to index.html)
    @app.route("/")
    @app.route("/calendar")
    @app.route("/entities")
    @app.route("/entities/<ticker>")
    @app.route("/filings")
    @app.route("/filings/<int:id>")
    @app.route("/beat-miss")
    @app.route("/indicators")
    @app.route("/admin/collect")
    def serve_spa(ticker=None, id=None):
        return send_from_directory(static_folder, "index.html")

    return app
