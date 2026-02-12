import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

# ✅ Candidates Table
cur.execute("""
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT UNIQUE,
    resume_path TEXT,
    resume_score REAL,
    status TEXT,
    interview_date TEXT,
    interview_link TEXT,
    interview_token TEXT
)
""")


# ✅ Behavior / Suspicious Monitoring Table  (STEP 5 ADD THIS)
cur.execute("""
CREATE TABLE IF NOT EXISTS behavior_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_name TEXT,
    suspicious_event TEXT,
    confidence REAL,
    timestamp TEXT
)
""")


# ✅ Interview Transcript Table (VERY USEFUL FOR FINAL REPORT)
cur.execute("""
CREATE TABLE IF NOT EXISTS interview_transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_name TEXT,
    question TEXT,
    answer TEXT,
    timestamp TEXT
)
""")

conn.commit()
conn.close()
