"""
routes/chat.py — Chat, Auth, Admin, and API routes
"""

import uuid
import json
import os
from datetime import datetime
from functools import wraps
from flask import (Blueprint, request, jsonify, session, redirect,
                   url_for, render_template, Response, stream_with_context, send_file)

from models.db import (
    get_user_by_email, create_user, verify_password,
    save_message, get_chat_history, get_all_chats_admin,
    get_all_faqs, add_faq, update_faq, delete_faq,
    save_feedback, get_top_queries, get_analytics_summary,
    get_courses, get_placements
)
from services.ai_engine import (
    get_response, generate_ai_response_stream, build_embeddings, detect_intent
)

chat_bp = Blueprint("chat", __name__)


# ─────────────────────────── HELPERS ────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("chat.login_page"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


def get_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]


# ─────────────────────────── PAGE ROUTES ────────────────────────────
@chat_bp.route("/")
def index():
    return render_template("index.html",
                           user=session.get("user_name"),
                           user_id=session.get("user_id"))


@chat_bp.route("/login")
def login_page():
    if "user_id" in session:
        return redirect(url_for("chat.index"))
    return render_template("auth.html", mode="login")


@chat_bp.route("/signup")
def signup_page():
    if "user_id" in session:
        return redirect(url_for("chat.index"))
    return render_template("auth.html", mode="signup")


@chat_bp.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    return render_template("admin.html", user=session.get("user_name"))


# ─────────────────────────── AUTH API ────────────────────────────
@chat_bp.route("/api/signup", methods=["POST"])
def api_signup():
    data = request.get_json()
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({"error": "All fields are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if "@" not in email:
        return jsonify({"error": "Invalid email address"}), 400

    user = create_user(name, email, password)
    if not user:
        return jsonify({"error": "Email already registered"}), 409

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["role"] = user["role"]
    return jsonify({"success": True, "name": user["name"]})


@chat_bp.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = get_user_by_email(email)
    if not user or not verify_password(password, user["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["role"] = user["role"]
    return jsonify({"success": True, "name": user["name"], "role": user["role"]})


@chat_bp.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"success": True})


@chat_bp.route("/api/me")
def api_me():
    return jsonify({
        "logged_in": "user_id" in session,
        "name": session.get("user_name"),
        "role": session.get("role"),
    })


# ─────────────────────────── CHAT API ────────────────────────────
@chat_bp.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    query = data.get("message", "").strip()

    if not query:
        return jsonify({"error": "Empty message"}), 400
    if len(query) > 1000:
        return jsonify({"error": "Message too long"}), 400

    session_id = get_session_id()
    user_id = session.get("user_id")
    user_name = session.get("user_name")

    # Save user message
    save_message(session_id, "user", query, user_id)

    # Get recent chat history for context
    history = get_chat_history(session_id, limit=12)

    # Get AI response
    result = get_response(query, session_id, history, user_name)
    answer = result.get("answer", "I'm sorry, I couldn't process that request.")

    # Save bot response
    msg_id = save_message(session_id, "assistant", answer, user_id, result.get("engine", "rule"))

    return jsonify({
        "answer": answer,
        "engine": result.get("engine", "rule"),
        "suggestions": result.get("suggestions", []),
        "msg_id": msg_id,
    })


@chat_bp.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    data = request.get_json()
    query = data.get("message", "").strip()

    if not query or len(query) > 1000:
        return jsonify({"error": "Invalid message"}), 400

    session_id = get_session_id()
    user_id = session.get("user_id")
    history = get_chat_history(session_id, limit=12)

    save_message(session_id, "user", query, user_id)

    def generate():
        full_response = []
        for chunk in generate_ai_response_stream(query, history):
            full_response.append(chunk)
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        final = "".join(full_response)
        msg_id = save_message(session_id, "assistant", final, user_id, "llm")
        yield f"data: {json.dumps({'done': True, 'msg_id': msg_id})}\n\n"

    return Response(stream_with_context(generate()),
                    content_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@chat_bp.route("/api/chat/history")
def api_chat_history():
    session_id = get_session_id()
    history = get_chat_history(session_id, limit=50)
    return jsonify({"history": history})


@chat_bp.route("/api/chat/clear", methods=["POST"])
def api_clear_chat():
    session["session_id"] = str(uuid.uuid4())
    return jsonify({"success": True})


# ─────────────────────────── FEEDBACK ────────────────────────────
@chat_bp.route("/api/feedback", methods=["POST"])
def api_feedback():
    data = request.get_json()
    chat_id = data.get("chat_id")
    rating = data.get("rating")  # 1=positive, 0=negative

    if chat_id is None or rating not in (0, 1):
        return jsonify({"error": "Invalid feedback"}), 400

    session_id = get_session_id()
    save_feedback(chat_id, rating, session_id)
    return jsonify({"success": True})


# ─────────────────────────── FAQ API (Public) ────────────────────────────
@chat_bp.route("/api/faqs")
def api_faqs():
    category = request.args.get("category")
    faqs = get_all_faqs(category)
    return jsonify({"faqs": faqs})


# ─────────────────────────── ADMIN API ────────────────────────────
@chat_bp.route("/api/admin/faqs", methods=["GET"])
@login_required
@admin_required
def admin_get_faqs():
    faqs = get_all_faqs()
    return jsonify({"faqs": faqs})


@chat_bp.route("/api/admin/faqs", methods=["POST"])
@login_required
@admin_required
def admin_add_faq():
    data = request.get_json()
    add_faq(data["category"], data["question"], data["answer"])
    return jsonify({"success": True})


@chat_bp.route("/api/admin/faqs/<int:faq_id>", methods=["PUT"])
@login_required
@admin_required
def admin_update_faq(faq_id):
    data = request.get_json()
    update_faq(faq_id, data["category"], data["question"], data["answer"])
    return jsonify({"success": True})


@chat_bp.route("/api/admin/faqs/<int:faq_id>", methods=["DELETE"])
@login_required
@admin_required
def admin_delete_faq(faq_id):
    delete_faq(faq_id)
    return jsonify({"success": True})


@chat_bp.route("/api/admin/chats")
@login_required
@admin_required
def admin_get_chats():
    chats = get_all_chats_admin()
    return jsonify({"chats": chats})


@chat_bp.route("/api/admin/analytics")
@login_required
@admin_required
def admin_analytics():
    summary = get_analytics_summary()
    top_queries = get_top_queries(10)
    return jsonify({"summary": summary, "top_queries": top_queries})


@chat_bp.route("/api/admin/build-embeddings", methods=["POST"])
@login_required
@admin_required
def admin_build_embeddings():
    count = build_embeddings()
    return jsonify({"success": True, "built": count})


# ─────────────────────────── DATA API ────────────────────────────
@chat_bp.route("/api/courses")
def api_courses():
    return jsonify({"courses": get_courses()})


@chat_bp.route("/api/placements")
def api_placements():
    year = request.args.get("year", type=int)
    return jsonify({"placements": get_placements(year)})


# ─────────────────────────── EXPORT CHAT ────────────────────────────
@chat_bp.route("/api/chat/export")
def export_chat():
    session_id = get_session_id()
    history = get_chat_history(session_id, limit=100)

    try:
        from fpdf import FPDF

        class PDF(FPDF):
            def header(self):
                self.set_font("Helvetica", "B", 14)
                self.cell(0, 10, "BBC College - Chat Export", align="C", new_x="LMARGIN", new_y="NEXT")
                self.set_font("Helvetica", "", 9)
                self.cell(0, 6, f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C", new_x="LMARGIN", new_y="NEXT")
                self.ln(4)

        pdf = PDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        for msg in history:
            role = "You" if msg["role"] == "user" else "BBC Assistant"
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(30, 100, 200) if msg["role"] == "user" else pdf.set_text_color(20, 150, 80)
            pdf.cell(0, 7, f"{role}  [{msg['created_at'][:16]}]", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)
            # Remove markdown symbols
            text = msg["message"].replace("**", "").replace("*", "").replace("##", "").replace("#", "")
            pdf.multi_cell(0, 6, text)
            pdf.ln(2)

        import io
        buf = io.BytesIO()
        pdf.output(buf)
        buf.seek(0)
        return send_file(buf, mimetype="application/pdf",
                         as_attachment=True, download_name="bbc_chat_export.pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
