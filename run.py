#!/usr/bin/env python3
"""
Entry point to run the QK_EARNING Flask application.
"""
from app import create_app
from app.config import PORT, DEBUG

app = create_app()

if __name__ == "__main__":
    print(f"🚀 Starting QK_EARNING server on http://127.0.0.1:{PORT}")
    app.run(host="127.0.0.1", port=PORT, debug=DEBUG)
