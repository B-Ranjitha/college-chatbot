# ─────────────────────────────────────────────────────────────────
#  Procfile — Render / Railway / Heroku (Linux servers only)
#  This file is NOT used on Windows — see README for Windows run cmd
# ─────────────────────────────────────────────────────────────────
web: gunicorn app:app -c gunicorn.conf.py
# release: python -c "from models.db import init_db; from services.ai_engine import build_embeddings; init_db(); build_embeddings()"
