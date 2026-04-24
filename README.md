# 🎓 BBC College AI Chatbot

An intelligent college enquiry chatbot with a 3-layer hybrid AI engine (Rule → Semantic → LLM), premium glassmorphism UI, admin dashboard, voice input, and PDF chat export.

---

## ⚡ Quick Start — Windows

### Prerequisites
- Python **3.10, 3.11, 3.12, or 3.13** from https://python.org  
  *(tick "Add Python to PATH" during install)*
- No compiler, no Visual Studio, no extra tools needed

### One-time setup
```
Double-click  →  setup_windows.bat
```
Or in PowerShell:
```powershell
python -m venv venv
venv\Scripts\Activate.ps1       # PowerShell
# OR
venv\Scripts\activate.bat       # Command Prompt

pip install -r requirements.txt
copy .env.example .env
```

### Start the server (every time)
```
Double-click  →  run_windows.bat
```
Or manually:
```powershell
venv\Scripts\activate.bat
python app.py
```
Then open **http://localhost:5000** in your browser.

---

## 🍎 Quick Start — Mac / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

---

## ⚙️ Environment Variables (.env)

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Optional | — | Enables LLM Layer 3. Get at platform.openai.com |
| `SECRET_KEY` | **Yes** | insecure dev key | Change before deploying. Run `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_PATH` | No | `college.db` | SQLite file location |
| `FLASK_DEBUG` | No | `0` | Set to `1` for hot-reload during development |
| `PORT` | No | `5000` | HTTP port |

---

## 👤 Default Accounts

| Role | Email | Password |
|---|---|---|
| Admin | admin@bbc.edu.in | admin@123 |

**Change the admin password after first login.**

---

## 🌐 Pages

| URL | Description |
|---|---|
| http://localhost:5000 | Main chat interface |
| http://localhost:5000/login | Login |
| http://localhost:5000/signup | Register |
| http://localhost:5000/admin | Admin dashboard (admin only) |

---

## 🤖 AI Engine Layers

1. **Rule-based** — Jaccard keyword matching against FAQs. Instant, zero cost.
2. **Semantic search** — Sentence-transformer embeddings + cosine similarity. Needs `sentence-transformers` installed.
3. **LLM (OpenAI)** — GPT-3.5-turbo fallback for complex queries. Needs `OPENAI_API_KEY`.

The chatbot works in **Rule-only mode** with no API key — it answers all 27 seeded FAQs instantly.

### Build semantic embeddings (one-time, after setup)
```
http://localhost:5000/admin  →  Overview tab  →  "Build/Update Embeddings" button
```

---

## 🚀 Deploy to Render (free)

1. Push code to a GitHub repo
2. Go to https://render.com → New Web Service → connect your repo
3. Set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app -c gunicorn.conf.py`
4. Add environment variables: `OPENAI_API_KEY`, `SECRET_KEY`, `DATABASE_PATH=/var/data/college.db`
5. Add a **Persistent Disk** mounted at `/var/data` (so the DB survives deploys)

---

## 🚀 Deploy to Railway

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```
Set env vars in the Railway dashboard.

---

## 🧪 Run Tests

```powershell
# Windows
venv\Scripts\activate.bat
python -m pytest tests/ -v

# Mac / Linux
source venv/bin/activate
pytest tests/ -v
```

---

## 📁 Project Structure

```
college_chatbot/
├── app.py                  # Flask entry point + app factory
├── requirements.txt        # All Python dependencies
├── .env.example            # Environment variable template
├── setup_windows.bat       # One-click Windows setup
├── run_windows.bat         # One-click Windows run
├── Procfile                # Render/Railway deployment
├── gunicorn.conf.py        # Production server config (Linux/Mac)
├── models/
│   └── db.py               # SQLite schema, seed data, all queries
├── services/
│   └── ai_engine.py        # 3-layer AI: rule → semantic → LLM
├── routes/
│   └── chat.py             # All Flask URL routes and API endpoints
├── templates/
│   ├── index.html          # Main chat UI
│   ├── auth.html           # Login / signup
│   └── admin.html          # Admin dashboard
├── static/
│   ├── css/                # main.css · auth.css · admin.css
│   └── js/                 # main.js · auth.js · admin.js
└── tests/
    └── test_app.py         # Unit + integration tests
```

---

## ❓ Troubleshooting

**`source` is not recognized** → You are in PowerShell. Use `venv\Scripts\Activate.ps1` instead of `source venv/bin/activate`.

**`numpy` build error / compiler not found** → Your `requirements.txt` was pinning `numpy==1.26.4` which needs a C compiler on Python 3.13. The updated `requirements.txt` uses `numpy>=2.0.0` which has pre-built Windows wheels — no compiler needed.

**`bcrypt` not found** → Dependencies not installed yet. Run `pip install -r requirements.txt` inside the activated venv.

**`gunicorn` not recognized** → Gunicorn does not run on Windows. Use `python app.py` or `waitress-serve --port=5000 app:app` instead.

**`pytest` not recognized** → Run as `python -m pytest tests/ -v` inside the activated venv.

**PowerShell execution policy error** → Run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
