"""
app.py — Flask application entry point
---------------------------------------
Startup sequence:
  1. load_dotenv()          → reads .env (OPENAI_API_KEY, SECRET_KEY, DATABASE_PATH …)
  2. create_app()           → configures Flask, attaches security headers
  3. register_blueprints()  → mounts all routes from the routes/ package
  4. init_db()              → creates SQLite tables + seeds data on first run
  5. serve()                → waitress on Windows, Flask dev server otherwise

Run locally:
  python app.py

Run in production (Linux/Mac):
  gunicorn app:app -c gunicorn.conf.py

Run in production (Windows):
  waitress-serve --port=5000 app:app
"""

import os
import sys
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from models.db import init_db
from routes import register_blueprints


def create_app() -> Flask:
    """Application factory — call once at startup."""
    app = Flask(__name__)

    # ── Session & security ─────────────────────────────────────────
    app.secret_key = os.getenv(
        "SECRET_KEY",
        "dev-secret-CHANGE-THIS-before-deploying-abc123xyz"
    )
    app.config["SESSION_COOKIE_HTTPONLY"]    = True
    app.config["SESSION_COOKIE_SAMESITE"]   = "Lax"
    app.config["SESSION_COOKIE_SECURE"]     = os.getenv("FLASK_ENV") == "production"
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

    # ── Security headers ───────────────────────────────────────────
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"]        = "SAMEORIGIN"
        response.headers["X-XSS-Protection"]       = "1; mode=block"
        response.headers["Referrer-Policy"]         = "strict-origin-when-cross-origin"
        return response

    register_blueprints(app)
    init_db()
    return app


# Module-level instance used by Gunicorn / waitress-serve
app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"

    if sys.platform == "win32" and not debug:
        # waitress is production-grade and works on Windows
        try:
            from waitress import serve
            print(f"  * Running on http://127.0.0.1:{port}  (waitress, Windows)")
            print("  * Press CTRL+C to quit")
            serve(app, host="0.0.0.0", port=port)
        except ImportError:
            print("  [INFO] waitress not installed — falling back to Flask dev server")
            print("         Install with:  pip install waitress")
            app.run(debug=False, host="0.0.0.0", port=port)
    else:
        app.run(debug=debug, host="0.0.0.0", port=port)
