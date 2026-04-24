"""
routes/__init__.py
-------------------
Makes `routes` a proper Python package and provides a single
`register_blueprints(app)` helper so that app.py stays clean.

Usage in app.py:
    from routes import register_blueprints
    register_blueprints(app)

Adding a new blueprint later is a one-liner here — no changes
needed in app.py.
"""

from flask import Flask
from routes.chat import chat_bp


def register_blueprints(app: Flask) -> None:
    """Attach all blueprints to the Flask application instance."""
    app.register_blueprint(chat_bp)
    # Future blueprints — uncomment when added:
    # from routes.api_v2 import api_v2_bp
    # app.register_blueprint(api_v2_bp, url_prefix="/api/v2")


__all__ = ["register_blueprints"]

