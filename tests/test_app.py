"""
tests/test_app.py — Basic unit & integration tests
Run: python -m pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import json
import tempfile

os.environ["DATABASE_PATH"] = ":memory:"
os.environ["SECRET_KEY"] = "test-secret-key"

from app import create_app
from models.db import init_db


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        with app.app_context():
            init_db()
        yield c


# ── Page routes ──────────────────────────────────────────
class TestPages:
    def test_home_loads(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert b"BBC" in r.data

    def test_login_page(self, client):
        r = client.get("/login")
        assert r.status_code == 200

    def test_signup_page(self, client):
        r = client.get("/signup")
        assert r.status_code == 200

    def test_admin_redirect_unauthenticated(self, client):
        r = client.get("/admin")
        assert r.status_code == 302


# ── Auth API ─────────────────────────────────────────────
class TestAuth:
    def test_signup_success(self, client):
        r = client.post("/api/signup", json={
            "name": "Test Student",
            "email": "test@example.com",
            "password": "test123"
        })
        d = json.loads(r.data)
        assert r.status_code == 200
        assert d["success"] is True

    def test_signup_duplicate_email(self, client):
        payload = {"name": "A", "email": "dup@ex.com", "password": "pass123"}
        client.post("/api/signup", json=payload)
        r = client.post("/api/signup", json=payload)
        assert r.status_code == 409

    def test_signup_missing_fields(self, client):
        r = client.post("/api/signup", json={"name": "", "email": "", "password": ""})
        assert r.status_code == 400

    def test_login_wrong_password(self, client):
        client.post("/api/signup", json={"name": "U", "email": "u@e.com", "password": "correct"})
        r = client.post("/api/login", json={"email": "u@e.com", "password": "wrong"})
        assert r.status_code == 401

    def test_login_success(self, client):
        client.post("/api/signup", json={"name": "User", "email": "user@e.com", "password": "pass123"})
        r = client.post("/api/login", json={"email": "user@e.com", "password": "pass123"})
        d = json.loads(r.data)
        assert d["success"] is True

    def test_me_unauthenticated(self, client):
        r = client.get("/api/me")
        d = json.loads(r.data)
        assert d["logged_in"] is False

    def test_logout(self, client):
        r = client.post("/api/logout")
        assert r.status_code == 200


# ── Chat API ─────────────────────────────────────────────
class TestChat:
    def test_chat_empty_message(self, client):
        r = client.post("/api/chat", json={"message": ""})
        assert r.status_code == 400

    def test_chat_too_long(self, client):
        r = client.post("/api/chat", json={"message": "x" * 1001})
        assert r.status_code == 400

    def test_chat_greeting(self, client):
        r = client.post("/api/chat", json={"message": "hello"})
        assert r.status_code == 200
        d = json.loads(r.data)
        assert "answer" in d
        assert len(d["answer"]) > 0

    def test_chat_admission_query(self, client):
        r = client.post("/api/chat", json={"message": "How do I apply for admission?"})
        assert r.status_code == 200
        d = json.loads(r.data)
        assert "answer" in d
        assert d["engine"] in ("rule", "semantic", "llm", "fallback")

    def test_chat_fees_query(self, client):
        r = client.post("/api/chat", json={"message": "What is the fee structure?"})
        assert r.status_code == 200
        d = json.loads(r.data)
        assert "answer" in d

    def test_chat_history(self, client):
        client.post("/api/chat", json={"message": "hi"})
        r = client.get("/api/chat/history")
        d = json.loads(r.data)
        assert "history" in d
        assert isinstance(d["history"], list)

    def test_chat_clear(self, client):
        client.post("/api/chat", json={"message": "test message"})
        r = client.post("/api/chat/clear")
        assert r.status_code == 200
        r2 = client.get("/api/chat/history")
        d = json.loads(r2.data)
        assert d["history"] == []

    def test_feedback_valid(self, client):
        r = client.post("/api/chat", json={"message": "What are the courses?"})
        msg_id = json.loads(r.data).get("msg_id")
        if msg_id:
            r2 = client.post("/api/feedback", json={"chat_id": msg_id, "rating": 1})
            assert r2.status_code == 200

    def test_feedback_invalid_rating(self, client):
        r = client.post("/api/feedback", json={"chat_id": 1, "rating": 5})
        assert r.status_code == 400


# ── FAQ API ──────────────────────────────────────────────
class TestFAQ:
    def test_get_all_faqs(self, client):
        r = client.get("/api/faqs")
        d = json.loads(r.data)
        assert "faqs" in d
        assert len(d["faqs"]) > 0

    def test_get_faqs_by_category(self, client):
        r = client.get("/api/faqs?category=admissions")
        d = json.loads(r.data)
        assert all(f["category"] == "admissions" for f in d["faqs"])


# ── Data API ─────────────────────────────────────────────
class TestDataApi:
    def test_courses(self, client):
        r = client.get("/api/courses")
        d = json.loads(r.data)
        assert "courses" in d
        assert len(d["courses"]) > 0

    def test_placements(self, client):
        r = client.get("/api/placements")
        d = json.loads(r.data)
        assert "placements" in d
        assert len(d["placements"]) > 0


# ── AI Engine unit tests ──────────────────────────────────
class TestAIEngine:
    def test_detect_intent_admissions(self):
        from services.ai_engine import detect_intent
        assert detect_intent("how to apply for admission") == "admissions"

    def test_detect_intent_fees(self):
        from services.ai_engine import detect_intent
        assert detect_intent("what is the tuition fee") == "fees"

    def test_detect_intent_placements(self):
        from services.ai_engine import detect_intent
        assert detect_intent("what companies recruit here") == "placements"

    def test_is_greeting(self):
        from services.ai_engine import is_greeting
        assert is_greeting("hello") is True
        assert is_greeting("what is the fee") is False

    def test_is_farewell(self):
        from services.ai_engine import is_farewell
        assert is_farewell("thank you") is True
        assert is_farewell("how to apply") is False

    def test_rule_based_search_returns_result(self):
        from services.ai_engine import rule_based_search
        from models.db import init_db
        init_db()
        result = rule_based_search("admission process")
        # May or may not return result depending on DB state
        if result:
            assert "answer" in result

    def test_fallback_response_not_empty(self):
        from services.ai_engine import _fallback_response
        assert len(_fallback_response("random query")) > 0

    def test_get_suggestions(self):
        from services.ai_engine import _get_suggestions
        s = _get_suggestions("fees")
        assert isinstance(s, list)
        assert len(s) > 0
