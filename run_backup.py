#!/usr/bin/env python3
"""
Run the original BACKUP version of QK_EARNING on port 5002
Allows comparing the previous version against the new company-centric version.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKUP_DIR = ROOT_DIR / "backup"
BACKUP_STATIC = BACKUP_DIR / "static"

sys.path.insert(0, str(BACKUP_DIR))

# Import backup's app module
import backup.app.config as backup_config
# Ensure DB points to root data/qk_earning.db
backup_config.DB_PATH = ROOT_DIR / "data" / "qk_earning.db"
backup_config.DATA_DIR = ROOT_DIR / "data"

from flask import Flask, send_from_directory
from backup.app.routes.api import api_bp

def create_backup_app():
    static_folder = str(BACKUP_STATIC)
    app = Flask(__name__, static_folder=static_folder, static_url_path="")
    app.config["SECRET_KEY"] = "backup-secret-key"
    app.register_blueprint(api_bp)

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

if __name__ == "__main__":
    port = 5002
    print(f"🚀 Starting BACKUP version server on http://127.0.0.1:{port}")
    app = create_backup_app()
    app.run(host="127.0.0.1", port=port, debug=False)
