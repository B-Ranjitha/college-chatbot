"""
services/ai_engine.py — Hybrid AI Engine
Layer 1: Rule-based keyword/intent detection
Layer 2: Semantic search via sentence-transformers + cosine similarity
Layer 3: OpenAI LLM fallback
"""

import os
import json
import re
import numpy as np
from functools import lru_cache
from models.db import get_all_faqs, get_faqs_with_embeddings, save_faq_embedding, track_query

# ── Optional imports with graceful fallback ──
try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SIMILARITY_THRESHOLD = 0.55

# ─────────────────────────── INTENT DETECTION ────────────────────────────
INTENT_KEYWORDS = {
    "admissions": [
        "admission", "apply", "application", "enroll", "enrollment",
        "join", "register", "registration", "form", "entrance", "cutoff",
        "merit", "selection", "document", "certificate", "seat"
    ],
    "courses": [
        "course", "program", "programme", "branch", "department", "degree",
        "btech", "be", "mtech", "me", "mba", "mca", "cse", "ece", "mech",
        "civil", "eee", "electrical", "mechanical", "computer", "study",
        "syllabus", "curriculum", "subject", "specialization"
    ],
    "fees": [
        "fee", "fees", "cost", "price", "tuition", "scholarship",
        "financial", "loan", "installment", "payment", "hostel fee",
        "yearly", "annual", "semester fee", "concession", "waiver"
    ],
    "placements": [
        "placement", "placed", "job", "recruit", "company", "package",
        "salary", "lpa", "hire", "hiring", "campus", "offer", "letter",
        "training", "interview", "aptitude", "career", "opportunity"
    ],
    "campus": [
        "campus", "facility", "facilities", "lab", "library", "hostel",
        "canteen", "sports", "gym", "wifi", "internet", "transport",
        "bus", "medical", "infirmary", "ground", "pool", "swimming"
    ],
    "faculty": [
        "faculty", "professor", "teacher", "staff", "lecturer",
        "phd", "doctor", "hod", "head", "department head", "guide", "mentor"
    ],
    "general": [
        "college", "address", "location", "contact", "phone", "email",
        "timing", "time", "schedule", "naac", "aicte", "anna university",
        "affiliation", "accreditation", "about", "history"
    ],
}

GREETINGS = {"hi", "hello", "hey", "good morning", "good afternoon",
             "good evening", "howdy", "hii", "helo", "hai"}

FAREWELLS = {"bye", "goodbye", "thank you", "thanks", "see you",
             "that's all", "ok thanks", "got it", "ok", "okay"}


def detect_intent(query: str) -> str:
    q = query.lower().strip()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return intent
    return "general"


def is_greeting(query: str) -> bool:
    return query.lower().strip() in GREETINGS


def is_farewell(query: str) -> bool:
    return any(w in query.lower() for w in FAREWELLS)


# ─────────────────────────── RULE-BASED SEARCH ────────────────────────────
def rule_based_search(query: str) -> dict | None:
    """Fast keyword matching against FAQ database."""
    q = query.lower()
    faqs = get_all_faqs()
    best_score = 0
    best_faq = None

    query_words = set(re.findall(r'\b\w+\b', q))

    for faq in faqs:
        faq_words = set(re.findall(r'\b\w+\b', faq["question"].lower()))
        # Jaccard similarity
        intersection = query_words & faq_words
        union = query_words | faq_words
        if not union:
            continue
        score = len(intersection) / len(union)
        if score > best_score:
            best_score = score
            best_faq = faq

    if best_score >= 0.35 and best_faq:
        return {"answer": best_faq["answer"], "score": best_score, "engine": "rule", "faq_id": best_faq["id"]}
    return None


# ─────────────────────────── SEMANTIC SEARCH ────────────────────────────
_st_model = None

def _get_st_model():
    global _st_model
    if _st_model is None and _ST_AVAILABLE:
        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _st_model


def get_embedding(text: str) -> list:
    model = _get_st_model()
    if model is None:
        return []
    return model.encode(text).tolist()


def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / norm) if norm > 0 else 0.0


def build_embeddings():
    """Pre-compute and store embeddings for all FAQs that don't have one."""
    if not _ST_AVAILABLE:
        return 0
    model = _get_st_model()
    faqs = get_all_faqs()
    existing = {f["id"] for f in get_faqs_with_embeddings()}
    count = 0
    for faq in faqs:
        if faq["id"] not in existing:
            emb = model.encode(faq["question"]).tolist()
            save_faq_embedding(faq["id"], emb)
            count += 1
    return count


def semantic_search(query: str) -> dict | None:
    if not _ST_AVAILABLE:
        return None
    model = _get_st_model()
    if model is None:
        return None

    query_emb = model.encode(query).tolist()
    faqs = get_faqs_with_embeddings()

    best_score = 0
    best_faq = None

    for faq in faqs:
        try:
            faq_emb = json.loads(faq["embedding"])
            score = cosine_similarity(query_emb, faq_emb)
            if score > best_score:
                best_score = score
                best_faq = faq
        except Exception:
            continue

    if best_score >= SIMILARITY_THRESHOLD and best_faq:
        return {
            "answer": best_faq["answer"],
            "score": best_score,
            "engine": "semantic",
            "faq_id": best_faq["id"],
        }
    return None


# ─────────────────────────── LLM ENGINE ────────────────────────────
SYSTEM_PROMPT = """You are a professional and friendly college assistant for Bharath Institute of Higher Education and Research (BBC College), Chennai.

Your role:
- Answer ONLY questions related to the college: admissions, courses, fees, placements, campus, faculty, hostel, and student life.
- Be accurate, helpful, concise, and warm.
- Use emojis sparingly for friendliness.
- Format lists with bullet points when appropriate.
- Do NOT make up specific numbers or data — say "please check bbc.edu.in for exact figures" if unsure.
- If a question is completely unrelated to college, politely redirect: "I'm specialized in college-related queries. For [topic], please consult appropriate resources."
- Do NOT hallucinate. Do NOT discuss politics, religion, or controversial topics.
- Always end with a helpful follow-up suggestion if possible.

College context:
- Name: Bharath Institute of Higher Education and Research (BBC College)
- Location: Chennai, Tamil Nadu
- Affiliation: Anna University | Accreditation: NAAC 'A' Grade, AICTE approved
- Website: bbc.edu.in
"""


def generate_ai_response(query: str, chat_history: list = None) -> dict:
    """Call OpenAI API with conversation context."""
    if not _OPENAI_AVAILABLE or not OPENAI_API_KEY:
        return {
            "answer": _fallback_response(query),
            "engine": "fallback",
        }

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if chat_history:
            for msg in chat_history[-8:]:  # last 8 messages for context
                messages.append({
                    "role": msg["role"],
                    "content": msg["message"]
                })

        messages.append({"role": "user", "content": query})

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500,
            temperature=0.7,
            stream=False,
        )
        answer = response.choices[0].message.content.strip()
        return {"answer": answer, "engine": "llm"}

    except Exception as e:
        print(f"[LLM Error] {e}")
        return {"answer": _fallback_response(query), "engine": "fallback"}


def generate_ai_response_stream(query: str, chat_history: list = None):
    """Generator for streaming OpenAI responses."""
    if not _OPENAI_AVAILABLE or not OPENAI_API_KEY:
        yield _fallback_response(query)
        return

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if chat_history:
            for msg in chat_history[-8:]:
                messages.append({"role": msg["role"], "content": msg["message"]})

        messages.append({"role": "user", "content": query})

        stream = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500,
            temperature=0.7,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    except Exception as e:
        print(f"[Stream Error] {e}")
        yield _fallback_response(query)


# ─────────────────────────── ORCHESTRATOR ────────────────────────────
def get_response(query: str, session_id: str, chat_history: list = None, user_name: str = None) -> dict:
    """
    Main orchestration:
    1. Greetings/farewells → immediate response
    2. Rule-based → fast FAQ match
    3. Semantic search → embedding similarity
    4. LLM → GPT fallback
    """
    q = query.strip()

    if is_greeting(q):
        name_part = f", {user_name}" if user_name else ""
        return {
            "answer": f"👋 Hello{name_part}! I'm your BBC College Assistant. How can I help you today?\n\nYou can ask me about **Admissions**, **Courses**, **Fees**, **Placements**, **Campus**, or anything about college life!",
            "engine": "rule",
            "suggestions": ["Tell me about courses", "Admission process", "Fee structure", "Placement record"],
        }

    if is_farewell(q):
        return {
            "answer": "You're welcome! 😊 Feel free to come back anytime you have questions about BBC College. Best of luck with your journey! 🎓",
            "engine": "rule",
        }

    intent = detect_intent(q)
    track_query(q[:200], intent)

    # Layer 1: Rule-based
    rule_result = rule_based_search(q)
    if rule_result and rule_result["score"] >= 0.5:
        rule_result["intent"] = intent
        rule_result["suggestions"] = _get_suggestions(intent)
        return rule_result

    # Layer 2: Semantic
    sem_result = semantic_search(q)
    if sem_result:
        sem_result["intent"] = intent
        sem_result["suggestions"] = _get_suggestions(intent)
        return sem_result

    # Layer 3: LLM
    llm_result = generate_ai_response(q, chat_history)
    llm_result["intent"] = intent
    llm_result["suggestions"] = _get_suggestions(intent)
    return llm_result


def _get_suggestions(intent: str) -> list:
    suggestions_map = {
        "admissions": ["What documents are needed?", "Last date for admission?", "Is there an entrance exam?"],
        "courses": ["CSE fees per year?", "Placement for CSE?", "New courses 2025?"],
        "fees": ["Are scholarships available?", "Can I pay in installments?", "Hostel fee?"],
        "placements": ["Top recruiting companies?", "Average package?", "Placement training?"],
        "campus": ["Is hostel available?", "Sports facilities?", "Wi-Fi on campus?"],
        "faculty": ["Faculty qualifications?", "Student-teacher ratio?"],
        "general": ["How to contact college?", "College timings?", "NAAC grade?"],
    }
    return suggestions_map.get(intent, ["Courses offered", "Admission process", "Fees structure"])


def _fallback_response(query: str) -> str:
    intent = detect_intent(query)
    fallbacks = {
        "admissions": "For admission queries, please visit **bbc.edu.in/admissions** or call **+91-44-2229-0742**. Our admissions team is available Mon–Sat, 9 AM–5 PM.",
        "courses": "We offer B.E. programs in CSE, ECE, Mech, Civil, EEE; M.E. in CSE; MBA and MCA. Visit **bbc.edu.in/academics** for full details.",
        "fees": "Fee details vary by course. Please visit **bbc.edu.in/fees** or contact the accounts office at **accounts@bbc.edu.in**.",
        "placements": "Our T&P cell has an excellent track record. For placement details, visit **bbc.edu.in/placements** or email **tnp@bbc.edu.in**.",
        "campus": "Our campus features modern labs, library, hostel, sports complex, and more. Tour details at **bbc.edu.in/campus**.",
    }
    return fallbacks.get(intent, "I'm having trouble processing your query right now. Please contact us at **info@bbc.edu.in** or **+91-44-2229-0742** for immediate assistance.")
