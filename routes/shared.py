import json
from functools import wraps

import PyPDF2
import docx
from flask import current_app, redirect, session

from database import get_db
from mailer import send_mail


def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                return redirect("/login")
            if role == "hr" and session.get("role") != "hr":
                return "Unauthorized", 403
            if role == "candidate" and session.get("role") != "candidate":
                return "Unauthorized", 403
            return f(*args, **kwargs)

        return wrapper

    return decorator


def extract_text(path):
    text = ""
    if path.lower().endswith(".pdf"):
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    elif path.lower().endswith(".docx"):
        doc = docx.Document(path)
        for para in doc.paragraphs:
            text += para.text + " "
    return text


def get_latest_jd_config():
    db = get_db()
    cur = db.execute(
        """
        SELECT id, COALESCE(title, ''), jd_text, jd_dict_json, skill_weights_json,
               min_academic_percent, qualify_score, question_count, project_ratio, created_at
        FROM jd_configs
        ORDER BY id DESC LIMIT 1
    """
    )
    row = cur.fetchone()
    db.close()

    if not row:
        return None

    return {
        "id": row[0],
        "title": row[1] or "",
        "jd_text": row[2] or "",
        "jd_dict": json.loads(row[3] or "{}"),
        "weights": json.loads(row[4] or "{}"),
        "min_academic_percent": int(row[5] or 60),
        "qualify_score": int(row[6] or 60),
        "question_count": int(row[7] or 10),
        "project_ratio": int(row[8] or 80),
        "created_at": row[9],
    }


def get_all_jd_configs():
    db = get_db()
    rows = db.execute(
        """
        SELECT id, COALESCE(title, ''), created_at, qualify_score, question_count, project_ratio
        FROM jd_configs
        ORDER BY id DESC
        """
    ).fetchall()
    db.close()
    return rows


def get_jd_config_by_id(jd_id):
    db = get_db()
    row = db.execute(
        """
        SELECT id, COALESCE(title, ''), jd_text, jd_dict_json, skill_weights_json,
               min_academic_percent, qualify_score, question_count, project_ratio, created_at
        FROM jd_configs
        WHERE id=?
        """,
        (jd_id,),
    ).fetchone()
    db.close()

    if not row:
        return None

    return {
        "id": row[0],
        "title": row[1] or "",
        "jd_text": row[2] or "",
        "jd_dict": json.loads(row[3] or "{}"),
        "weights": json.loads(row[4] or "{}"),
        "min_academic_percent": int(row[5] or 60),
        "qualify_score": int(row[6] or 60),
        "question_count": int(row[7] or 10),
        "project_ratio": int(row[8] or 80),
        "created_at": row[9],
    }


def _send_schedule_mail(to_email, interview_date, interview_link):
    subject = "Interview scheduled successfully"
    body = (
        "Your interview has been scheduled.\n\n"
        f"Date and time: {interview_date}\n"
        f"Interview link: {interview_link}\n"
    )
    ok = send_mail(to_email, subject, body)
    if not ok:
        print(f"[MAIL_FALLBACK] Could not send interview email to {to_email}. Link: {interview_link}")


def _parse_json_list(raw):
    if not raw:
        return []
    try:
        value = json.loads(raw)
        return value if isinstance(value, list) else []
    except:
        return []


def _parse_json_dict(raw):
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except:
        return {}


def _fallback_questions_from_jd(jd_dict):
    jd_dict = jd_dict or {}
    skills = []
    for key in ["mandatory_programming", "domain_skills", "tools", "optional_domains"]:
        skills.extend(jd_dict.get(key, []) or [])

    seen = set()
    uniq = []
    for skill in skills:
        clean = str(skill).strip()
        if clean and clean.lower() not in seen:
            uniq.append(clean)
            seen.add(clean.lower())

    if uniq:
        return [f"Explain your understanding of {s}." for s in uniq[:5]]

    return [
        "Introduce yourself and your background.",
        "Explain one project you are proud of.",
        "What challenges did you solve in your recent work?",
        "How do you approach debugging a difficult issue?",
        "Why do you think you are a fit for this role?",
    ]


def _normalize_questions(raw_questions):
    out = []
    for q in raw_questions or []:
        if isinstance(q, dict):
            text = str(q.get("question", "")).strip()
        else:
            text = str(q).strip()
        if text:
            out.append(text)
    return out


def build_interview_link(token):
    base_url = current_app.config.get("BASE_URL", "http://127.0.0.1:5000")
    return f"{base_url}/interview/{token}"
