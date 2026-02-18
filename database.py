import os
import sqlite3

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


def get_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    db = get_db()

    db.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password_hash TEXT,
        role TEXT CHECK(role IN ('hr','candidate')) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    db.execute(
        """
    INSERT OR IGNORE INTO users (email, password_hash, role)
    VALUES (?, ?, ?)
    """,
        ("hr", generate_password_hash("hr@123"), "hr"),
    )

    db.execute(
        """
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        resume_path TEXT,
        jd_config_id INTEGER,
        status TEXT,
        phase1_result_json TEXT,
        interview_date TEXT,
        interview_link TEXT,
        interview_token TEXT,
        questions_json TEXT,
        proctoring_json TEXT,
        answers_json TEXT,
        monitoring_json TEXT,
        interview_summary_json TEXT,
        evaluation_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    try:
        db.execute("ALTER TABLE candidates ADD COLUMN phase1_result_json TEXT")
    except:
        pass

    try:
        db.execute("ALTER TABLE candidates ADD COLUMN jd_config_id INTEGER")
    except:
        pass

    try:
        db.execute("ALTER TABLE candidates ADD COLUMN questions_json TEXT")
    except:
        pass

    try:
        db.execute("ALTER TABLE candidates ADD COLUMN proctoring_json TEXT")
    except:
        pass

    try:
        db.execute("ALTER TABLE candidates ADD COLUMN evaluation_json TEXT")
    except:
        pass

    try:
        db.execute("ALTER TABLE candidates ADD COLUMN monitoring_json TEXT")
    except:
        pass

    try:
        db.execute("ALTER TABLE candidates ADD COLUMN interview_summary_json TEXT")
    except:
        pass

    db.execute(
        """
    CREATE TABLE IF NOT EXISTS jd_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        jd_text TEXT,
        jd_dict_json TEXT,
        skill_weights_json TEXT,
        min_academic_percent INTEGER DEFAULT 60,
        qualify_score INTEGER DEFAULT 60,
        question_count INTEGER DEFAULT 10,
        project_ratio INTEGER DEFAULT 80,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    try:
        db.execute("ALTER TABLE jd_configs ADD COLUMN title TEXT")
    except:
        pass

    try:
        db.execute("ALTER TABLE jd_configs ADD COLUMN question_count INTEGER DEFAULT 10")
    except:
        pass

    try:
        db.execute("ALTER TABLE jd_configs ADD COLUMN project_ratio INTEGER DEFAULT 80")
    except:
        pass

    db.commit()
    db.close()

    print("DB initialized. HR login: hr / hr@123")
    print("DB PATH =>", DB_PATH)
