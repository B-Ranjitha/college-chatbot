"""
models/db.py — Database layer: schema creation, seeding, and all query helpers.
Uses parameterized queries throughout to prevent SQL injection.
"""

import sqlite3
import json
import os
import hashlib
import bcrypt
from datetime import datetime

DB_PATH = os.getenv("DATABASE_PATH", "college.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ─────────────────────────── SCHEMA ────────────────────────────
def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL,
        email       TEXT    UNIQUE NOT NULL,
        password    TEXT    NOT NULL,
        role        TEXT    DEFAULT 'student',
        created_at  TEXT    DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS courses (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL,
        department  TEXT    NOT NULL,
        duration    TEXT    NOT NULL,
        fee_per_year INTEGER NOT NULL,
        seats       INTEGER NOT NULL,
        description TEXT,
        eligibility TEXT
    );

    CREATE TABLE IF NOT EXISTS admissions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        year        INTEGER NOT NULL,
        process     TEXT,
        start_date  TEXT,
        end_date    TEXT,
        documents   TEXT,
        contact     TEXT
    );

    CREATE TABLE IF NOT EXISTS placements (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        year        INTEGER NOT NULL,
        company     TEXT    NOT NULL,
        package_lpa REAL    NOT NULL,
        students_placed INTEGER DEFAULT 0,
        domain      TEXT
    );

    CREATE TABLE IF NOT EXISTS faqs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        category    TEXT    NOT NULL,
        question    TEXT    NOT NULL,
        answer      TEXT    NOT NULL,
        embedding   TEXT,
        helpful_yes INTEGER DEFAULT 0,
        helpful_no  INTEGER DEFAULT 0,
        created_at  TEXT    DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS chat_history (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id  TEXT    NOT NULL,
        user_id     INTEGER,
        role        TEXT    NOT NULL,
        message     TEXT    NOT NULL,
        engine_used TEXT    DEFAULT 'rule',
        created_at  TEXT    DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS feedback (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id     INTEGER NOT NULL,
        rating      INTEGER NOT NULL,
        session_id  TEXT,
        created_at  TEXT    DEFAULT (datetime('now')),
        FOREIGN KEY (chat_id) REFERENCES chat_history(id)
    );

    CREATE TABLE IF NOT EXISTS query_analytics (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        query       TEXT    NOT NULL,
        category    TEXT,
        count       INTEGER DEFAULT 1,
        last_asked  TEXT    DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id);
    CREATE INDEX IF NOT EXISTS idx_faq_category ON faqs(category);
    CREATE INDEX IF NOT EXISTS idx_analytics_query ON query_analytics(query);
    """)

    conn.commit()
    conn.close()
    try:
        _seed_data()
    except Exception as e:
        print(f"[DB] Seed warning: {e}")


# ─────────────────────────── SEED DATA ────────────────────────────
def _seed_data():
    conn = get_conn()
    c = conn.cursor()

    try:
        count = c.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    except Exception:
        conn.close()
        return

    # Only seed if empty
    if count > 0:
        conn.close()
        return

    # ── Courses ──
    courses = [
        ("B.E. Computer Science & Engineering", "Engineering", "4 Years", 95000, 120,
         "Industry-aligned curriculum covering AI, ML, cloud, and software engineering.",
         "10+2 with PCM, min 60%"),
        ("B.E. Electronics & Communication Engineering", "Engineering", "4 Years", 90000, 60,
         "Core electronics, VLSI, embedded systems, and IoT.",
         "10+2 with PCM, min 60%"),
        ("B.E. Mechanical Engineering", "Engineering", "4 Years", 85000, 60,
         "Design, manufacturing, thermodynamics, and robotics.",
         "10+2 with PCM, min 60%"),
        ("B.E. Civil Engineering", "Engineering", "4 Years", 80000, 60,
         "Structural design, construction management, and environmental engineering.",
         "10+2 with PCM, min 55%"),
        ("B.E. Electrical Engineering", "Engineering", "4 Years", 85000, 60,
         "Power systems, control systems, and renewable energy.",
         "10+2 with PCM, min 60%"),
        ("M.E. Computer Science & Engineering", "Engineering", "2 Years", 110000, 30,
         "Advanced specialization in AI, cybersecurity, or data science.",
         "B.E./B.Tech CSE or equivalent, min 60%"),
        ("MBA", "Management", "2 Years", 120000, 60,
         "Business management, marketing, finance, and entrepreneurship.",
         "Bachelor's degree any discipline, min 50%"),
        ("MCA", "Computer Applications", "2 Years", 100000, 30,
         "Advanced computing, software development, and enterprise systems.",
         "BCA/B.Sc CS, min 60%"),
    ]
    c.executemany(
        "INSERT INTO courses (name,department,duration,fee_per_year,seats,description,eligibility) VALUES (?,?,?,?,?,?,?)",
        courses
    )

    # ── Admissions ──
    c.execute("""INSERT INTO admissions (year,process,start_date,end_date,documents,contact)
                 VALUES (2025,
                 'Apply online → Entrance exam / merit list → Document verification → Fee payment',
                 '2025-05-01','2025-07-31',
                 '10th & 12th marksheets, Transfer Certificate, Migration Certificate, Conduct Certificate, Passport photos (6), Aadhar card, Caste certificate (if applicable)',
                 'admissions@bbc.edu.in | +91-44-1234-5678')""")

    # ── Placements ──
    placements = [
        (2024, "TCS", 7.5, 45, "IT"),
        (2024, "Infosys", 6.5, 38, "IT"),
        (2024, "Wipro", 6.0, 30, "IT"),
        (2024, "Cognizant", 5.5, 25, "IT"),
        (2024, "HCL Technologies", 6.0, 20, "IT"),
        (2024, "L&T Technology Services", 8.0, 15, "Core"),
        (2024, "Zoho Corporation", 10.0, 12, "Product"),
        (2024, "Freshworks", 14.0, 8, "Product"),
        (2024, "Amazon", 18.0, 5, "Tech"),
        (2024, "Microsoft", 22.0, 3, "Tech"),
        (2023, "TCS", 7.0, 42, "IT"),
        (2023, "Infosys", 6.0, 35, "IT"),
        (2023, "Accenture", 7.5, 28, "IT"),
        (2023, "Capgemini", 5.5, 22, "IT"),
    ]
    c.executemany(
        "INSERT INTO placements (year,company,package_lpa,students_placed,domain) VALUES (?,?,?,?,?)",
        placements
    )

    # ── FAQs ──
    faqs = [
        # Admissions
        ("admissions", "How do I apply for admission?",
         "Applications are accepted online at bbc.edu.in/apply. The process: 1) Register online 2) Fill the application form 3) Upload documents 4) Pay application fee (₹500) 5) Appear for entrance test / submit merit list 6) Attend counselling 7) Pay tuition fee to confirm seat. Admissions for 2025 open May 1st."),
        ("admissions", "What is the last date for admission 2025?",
         "The last date for admission for 2025-26 batch is July 31, 2025. We strongly recommend applying early as seats fill quickly. For late admissions, contact: admissions@bbc.edu.in."),
        ("admissions", "What documents are required for admission?",
         "Required documents: ✅ 10th & 12th mark sheets (original + 2 copies) ✅ Transfer Certificate ✅ Migration Certificate ✅ Conduct Certificate ✅ 6 passport-size photos ✅ Aadhar card ✅ Caste/community certificate (if applicable) ✅ Medical fitness certificate."),
        ("admissions", "Is there an entrance exam?",
         "Admission is primarily merit-based on 12th marks. Students can also qualify through TNEA (Tamil Nadu Engineering Admissions) counselling. A college-level aptitude test is conducted for management quota seats."),
        ("admissions", "What is the application fee?",
         "The application fee is ₹500 (non-refundable), payable online via UPI, net banking, or credit/debit card."),

        # Courses
        ("courses", "What courses are offered?",
         "We offer: 🎓 B.E. in CSE, ECE, Mechanical, Civil, Electrical (4 years) | M.E. in CSE (2 years) | MBA (2 years) | MCA (2 years). New specializations in AI & Data Science are being added for 2025-26."),
        ("courses", "What is the duration of B.E. programs?",
         "All B.E./B.Tech programs are 4 years (8 semesters). M.E./MBA/MCA programs are 2 years (4 semesters)."),
        ("courses", "Which is the most popular course?",
         "B.E. Computer Science & Engineering is our most popular program with 120 seats and highest placement record. B.E. ECE and Mechanical are also highly sought after."),
        ("courses", "Are there any new courses for 2025?",
         "Yes! From 2025-26, we are introducing: B.E. AI & Machine Learning, B.E. Cybersecurity, and a 6-month industry certification track in Data Science in collaboration with IBM."),

        # Fees
        ("fees", "What is the tuition fee?",
         "Approximate annual fees: B.E. CSE: ₹95,000/year | B.E. ECE: ₹90,000/year | B.E. Mech/Civil/EEE: ₹80,000–₹85,000/year | M.E.: ₹1,10,000/year | MBA: ₹1,20,000/year | MCA: ₹1,00,000/year. Fees include tuition, exam, and lab charges."),
        ("fees", "Are scholarships available?",
         "Yes, multiple scholarships: 🏆 Merit scholarship: Top 5% students get 25% fee waiver | 🏛 Government scholarships: SC/ST/OBC/MBC (state govt funded) | 💼 Management scholarship: Sports/arts achievers | 🤝 Alumni scholarship for financially needy students. Apply via scholarship portal after admission."),
        ("fees", "What are the hostel fees?",
         "Hostel fees (per year): Boys hostel: ₹65,000 (AC) / ₹45,000 (Non-AC) including mess charges. Girls hostel: ₹70,000 (AC) / ₹48,000 (Non-AC) including mess charges. Caution deposit: ₹5,000 (refundable)."),
        ("fees", "Can I pay fees in installments?",
         "Yes! Fees can be paid in 2 installments per semester. First installment at admission, second by November (odd sem) / April (even sem). EMI options available via education loan tie-ups with SBI, Canara Bank, and Indian Bank."),

        # Placements
        ("placements", "What is the placement record?",
         "2024 Placement Highlights: ✅ 95%+ placement rate ✅ 200+ companies visited ✅ Highest package: ₹22 LPA (Microsoft) ✅ Average package: ₹7.2 LPA ✅ 300+ students placed. Top recruiters: Amazon, Microsoft, TCS, Infosys, Wipro, Zoho, Freshworks, L&T."),
        ("placements", "Which companies recruit from this college?",
         "Top recruiters include: Tech Giants: Amazon, Microsoft, Google (via referrals), Zoho | IT Companies: TCS, Infosys, Wipro, HCL, Cognizant, Accenture | Core Companies: L&T, BHEL, Ashok Leyland | Startups: Freshworks, Chargebee, Kissflow | We have 200+ active MoUs with industry partners."),
        ("placements", "What is the average salary package?",
         "Average salary package for 2024 batch: CSE: ₹8.5 LPA | ECE: ₹6.8 LPA | Mechanical: ₹5.5 LPA | Overall average: ₹7.2 LPA. Highest: ₹22 LPA (Microsoft). Median: ₹6.5 LPA."),
        ("placements", "Is there placement training provided?",
         "Yes! Our Training & Placement (T&P) cell provides: 📚 Aptitude training from 2nd year | 💻 Coding bootcamps (DSA, System Design) | 🗣 Soft skills & communication | 🎯 Mock interviews with industry experts | 📝 Resume building workshops | 🔗 LinkedIn profile optimization."),

        # Campus
        ("campus", "What facilities are available on campus?",
         "Campus facilities: 🏛 Smart classrooms with digital boards | 💻 32 advanced computer labs (1200+ systems) | 📚 Central library (80,000+ books, 200+ journals) | 🏋 Sports complex (cricket, football, basketball, badminton, gym) | 🍽 Canteen & food court | 🏥 Medical center | 🚌 College bus service (25 routes) | ☀ Solar-powered campus | 📡 24/7 Wi-Fi."),
        ("campus", "Is there a hostel facility?",
         "Yes! Separate hostels for boys and girls: 🏠 Boys hostel: 500 capacity, AC & Non-AC rooms | 🏠 Girls hostel: 400 capacity, AC & Non-AC rooms | Features: 24/7 security, CCTV, RO water, laundry, Wi-Fi, indoor games, common TV room. Warden is available 24/7."),
        ("campus", "What sports facilities are available?",
         "Sports complex includes: 🏏 Cricket ground (floodlit) | ⚽ Football field | 🏀 Basketball court | 🏸 Badminton courts (6 indoor) | 🏊 Swimming pool | 🏋 Fully equipped gymnasium | Table tennis, Carrom, Chess | Annual sports meet 'KHELOTHSAV' held every February."),
        ("campus", "Is the campus Wi-Fi enabled?",
         "Yes! The entire campus has 24/7 high-speed Wi-Fi (1 Gbps leased line) powered by Cisco infrastructure. Each student gets 20 GB/day data. Labs have 10 Gbps intranet connectivity."),

        # Faculty
        ("faculty", "How is the faculty quality?",
         "Our faculty: 👨‍🏫 300+ faculty members | 60% with Ph.D. qualifications | Average teaching experience: 12 years | Many faculty are published researchers with 500+ international journal papers | Industry experts as visiting faculty from TCS, Infosys, and IITs | Faculty:Student ratio 1:15."),
        ("faculty", "How can I contact a faculty member?",
         "Faculty contacts are listed on bbc.edu.in/faculty. You can also email via the format firstname.dept@bbc.edu.in. During college hours, visit the respective department office."),

        # General
        ("general", "What are the college timings?",
         "College timings: Monday–Friday: 8:30 AM – 4:30 PM | Saturday: 8:30 AM – 1:00 PM | Office hours: 9:00 AM – 5:00 PM (Mon–Sat) | Library: 8:00 AM – 8:00 PM (Mon–Sat) | Labs: 24/7 access for final-year project students."),
        ("general", "What is the college address?",
         "Bharath Institute of Higher Education and Research, 173, Agaram Road, Selaiyur, Chennai – 600 073, Tamil Nadu, India. Landmarks: Near Tambaram, 2 km from Selaiyur Bus Stand. GPS: 12.9316° N, 80.1136° E."),
        ("general", "How to contact the college?",
         "📞 Phone: +91-44-2229-0742 | 📧 Email: info@bbc.edu.in | 🌐 Website: bbc.edu.in | 📍 Address: 173 Agaram Road, Selaiyur, Chennai - 600073 | Social: @BBCCollege on Instagram, Facebook, LinkedIn | Admissions helpline: +91-98765-43210 (9 AM – 6 PM)."),
        ("general", "What is the NAAC grade?",
         "BBC College is NAAC Accredited with 'A' Grade. We are also approved by AICTE and affiliated with Anna University. NBA accredited departments: CSE, ECE, and Mechanical Engineering."),
    ]
    c.executemany(
        "INSERT INTO faqs (category,question,answer) VALUES (?,?,?)",
        faqs
    )

    # ── Default admin user ──
    hashed = bcrypt.hashpw(b"admin@123", bcrypt.gensalt()).decode()
    c.execute("INSERT OR IGNORE INTO users (name,email,password,role) VALUES (?,?,?,?)",
              ("Admin", "admin@bbc.edu.in", hashed, "admin"))

    conn.commit()
    conn.close()
    print("[DB] Seeded successfully.")


# ─────────────────────────── USER QUERIES ────────────────────────────
def create_user(name, email, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        conn = get_conn()
        conn.execute("INSERT INTO users (name,email,password) VALUES (?,?,?)", (name, email, hashed))
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        return dict(row)
    except sqlite3.IntegrityError:
        return None


def get_user_by_email(email):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def verify_password(plain, hashed):
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ─────────────────────────── CHAT ────────────────────────────
def save_message(session_id, role, message, user_id=None, engine="rule"):
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO chat_history (session_id,user_id,role,message,engine_used) VALUES (?,?,?,?,?)",
        (session_id, user_id, role, message, engine)
    )
    msg_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return msg_id


def get_chat_history(session_id, limit=20):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM chat_history WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
        (session_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def get_all_chats_admin(limit=200):
    conn = get_conn()
    rows = conn.execute(
        """SELECT ch.*, u.name as user_name, u.email as user_email
           FROM chat_history ch LEFT JOIN users u ON ch.user_id = u.id
           ORDER BY ch.created_at DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────── FAQ ────────────────────────────
def get_all_faqs(category=None):
    conn = get_conn()
    if category:
        rows = conn.execute("SELECT * FROM faqs WHERE category=? ORDER BY id", (category,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM faqs ORDER BY category, id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_faq(category, question, answer):
    conn = get_conn()
    conn.execute("INSERT INTO faqs (category,question,answer) VALUES (?,?,?)", (category, question, answer))
    conn.commit()
    conn.close()


def update_faq(faq_id, category, question, answer):
    conn = get_conn()
    conn.execute("UPDATE faqs SET category=?,question=?,answer=? WHERE id=?",
                 (category, question, answer, faq_id))
    conn.commit()
    conn.close()


def delete_faq(faq_id):
    conn = get_conn()
    conn.execute("DELETE FROM faqs WHERE id=?", (faq_id,))
    conn.commit()
    conn.close()


def save_faq_embedding(faq_id, embedding_list):
    conn = get_conn()
    conn.execute("UPDATE faqs SET embedding=? WHERE id=?",
                 (json.dumps(embedding_list), faq_id))
    conn.commit()
    conn.close()


def get_faqs_with_embeddings():
    conn = get_conn()
    rows = conn.execute("SELECT id, question, answer, category, embedding FROM faqs WHERE embedding IS NOT NULL").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────── FEEDBACK ────────────────────────────
def save_feedback(chat_id, rating, session_id):
    conn = get_conn()
    conn.execute("INSERT INTO feedback (chat_id,rating,session_id) VALUES (?,?,?)",
                 (chat_id, rating, session_id))
    conn.commit()
    conn.close()


# ─────────────────────────── ANALYTICS ────────────────────────────
def track_query(query, category):
    conn = get_conn()
    existing = conn.execute("SELECT id,count FROM query_analytics WHERE query=?", (query,)).fetchone()
    if existing:
        conn.execute("UPDATE query_analytics SET count=count+1, last_asked=datetime('now') WHERE id=?",
                     (existing["id"],))
    else:
        conn.execute("INSERT INTO query_analytics (query,category) VALUES (?,?)", (query, category))
    conn.commit()
    conn.close()


def get_top_queries(limit=10):
    conn = get_conn()
    rows = conn.execute("SELECT query, category, count FROM query_analytics ORDER BY count DESC LIMIT ?",
                        (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_analytics_summary():
    conn = get_conn()
    total_chats = conn.execute("SELECT COUNT(*) FROM chat_history WHERE role='user'").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
    total_faqs = conn.execute("SELECT COUNT(*) FROM faqs").fetchone()[0]
    positive_feedback = conn.execute("SELECT COUNT(*) FROM feedback WHERE rating=1").fetchone()[0]
    negative_feedback = conn.execute("SELECT COUNT(*) FROM feedback WHERE rating=0").fetchone()[0]
    conn.close()
    return {
        "total_chats": total_chats,
        "total_users": total_users,
        "total_faqs": total_faqs,
        "positive_feedback": positive_feedback,
        "negative_feedback": negative_feedback,
    }


# ─────────────────────────── COURSES & PLACEMENTS ────────────────────────────
def get_courses():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM courses ORDER BY department, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_placements(year=None):
    conn = get_conn()
    if year:
        rows = conn.execute("SELECT * FROM placements WHERE year=? ORDER BY package_lpa DESC", (year,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM placements ORDER BY year DESC, package_lpa DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
