import json
import os

from flask import Blueprint, render_template, request, session, redirect, send_file
from werkzeug.security import check_password_hash

from database import get_db
from jd_llm_extractor import JDKeywordExtractor
from question_engine import generate_questions
from routes.shared import (
    login_required,
    get_latest_jd_config,
    get_all_jd_configs,
    get_jd_config_by_id,
    extract_text,
    _normalize_questions,
    _parse_json_list,
    _parse_json_dict,
)

bp_hr = Blueprint("hr", __name__, url_prefix="/hr")


@bp_hr.route("/login", methods=["GET", "POST"])
def hr_login():
    if request.method == "POST":
        email = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()

        db = get_db()
        cur = db.execute(
            "SELECT id, password_hash FROM users WHERE email=? AND role='hr'",
            (email,),
        )
        row = cur.fetchone()
        db.close()

        if row and check_password_hash(row[1], password):
            session["user_id"] = row[0]
            session["email"] = email
            session["role"] = "hr"
            return redirect("/hr/dashboard")

        return render_template("hr_login.html", error="Invalid credentials")

    return render_template("hr_login.html")


@bp_hr.route("/logout")
def hr_logout():
    session.clear()
    return redirect("/hr/login")


@bp_hr.route("/dashboard", methods=["GET", "POST"])
@login_required(role="hr")
def hr_dashboard():
    selected_jd_id = request.args.get("jd_id", "").strip()
    if selected_jd_id.isdigit():
        config = get_jd_config_by_id(int(selected_jd_id)) or get_latest_jd_config()
    else:
        config = get_latest_jd_config()

    if request.method == "POST":
        action = request.form.get("action")
        title = request.form.get("title", "").strip()
        jd_text = request.form.get("jd_text", "").strip()
        min_acad = int(request.form.get("min_academic_percent", "60"))
        qualify_score = int(request.form.get("qualify_score", "60"))
        question_count = int(request.form.get("question_count", "10"))
        project_ratio = int(request.form.get("project_ratio", "80"))

        weights = {}
        for k, v in request.form.items():
            if k.startswith("weight_"):
                skill = k.replace("weight_", "").replace("__", " ")
                try:
                    weights[skill] = int(v)
                except:
                    weights[skill] = 0

        if action == "extract":
            extractor = JDKeywordExtractor()
            jd_dict = extractor.extract(jd_text)

            if not weights:
                all_skills = []
                for key in ["mandatory_programming", "domain_skills", "optional_domains", "tools", "soft_skills"]:
                    all_skills += jd_dict.get(key, [])

                per = max(1, int(100 / max(1, len(all_skills))))
                weights = {s: per for s in all_skills}

            return render_template(
                "hr_dashboard.html",
                config={
                    "jd_text": jd_text,
                    "title": title,
                    "jd_dict": jd_dict,
                    "weights": weights,
                    "min_academic_percent": min_acad,
                    "qualify_score": qualify_score,
                    "question_count": question_count,
                    "project_ratio": project_ratio,
                },
                msg="Skills extracted. Adjust weights and click Save.",
            )

        if action == "save":
            jd_dict_raw = request.form.get("jd_dict_json", "").strip()
            if jd_dict_raw:
                try:
                    jd_dict = json.loads(jd_dict_raw)
                except:
                    jd_dict = {}
            else:
                jd_dict = config["jd_dict"] if config else {}

            db = get_db()
            db.execute(
                """
                INSERT INTO jd_configs
                (title, jd_text, jd_dict_json, skill_weights_json, min_academic_percent, qualify_score, question_count, project_ratio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    jd_text,
                    json.dumps(jd_dict),
                    json.dumps(weights),
                    min_acad,
                    qualify_score,
                    question_count,
                    project_ratio,
                ),
            )
            db.commit()
            db.close()

            return redirect("/hr/dashboard")

    return render_template("hr_dashboard.html", config=config)


@bp_hr.route("/jds")
@login_required(role="hr")
def hr_jds():
    rows = get_all_jd_configs()
    return render_template("hr_jds.html", rows=rows)


@bp_hr.route("/candidates")
@login_required(role="hr")
def hr_candidates():
    db = get_db()
    rows = db.execute(
        """
        SELECT id, name, email, status, created_at
        FROM candidates
        ORDER BY id DESC
        """
    ).fetchall()
    db.close()

    return render_template("hr_candidates.html", rows=rows)


@bp_hr.route("/candidate/<int:candidate_id>/resume")
@login_required(role="hr")
def hr_candidate_resume(candidate_id):
    db = get_db()
    row = db.execute("SELECT resume_path FROM candidates WHERE id=?", (candidate_id,)).fetchone()
    db.close()

    if not row or not row[0]:
        return "Resume not found", 404

    resume_path = row[0]
    abs_upload = os.path.abspath("uploads")
    abs_path = os.path.abspath(resume_path)
    if not abs_path.startswith(abs_upload):
        return "Invalid resume path", 403

    if not os.path.exists(abs_path):
        return "File missing", 404

    return send_file(abs_path, as_attachment=False)


@bp_hr.route("/candidate/<int:candidate_id>")
@login_required(role="hr")
def hr_candidate_view(candidate_id):
    db = get_db()
    row = db.execute(
        """
        SELECT id, name, email, status, resume_path,
               jd_config_id, phase1_result_json, questions_json, answers_json,
               monitoring_json, interview_summary_json, created_at
        FROM candidates
        WHERE id=?
        """,
        (candidate_id,),
    ).fetchone()
    db.close()

    if not row:
        return "Candidate not found", 404

    phase1 = {}
    try:
        phase1 = json.loads(row[6]) if row[6] else {}
    except:
        phase1 = {"raw": row[6]}

    questions = _normalize_questions(_parse_json_list(row[7]))
    answers = [a for a in _parse_json_list(row[8]) if isinstance(a, dict)]
    monitoring = _parse_json_dict(row[9])
    summary = _parse_json_dict(row[10])

    jd_config = None
    if row[5]:
        jd_config = get_jd_config_by_id(int(row[5]))
    if not jd_config:
        jd_config = get_latest_jd_config()

    generated_questions = []
    resume_path = row[4]
    if resume_path and jd_config:
        try:
            resume_text = extract_text(resume_path)
        except:
            resume_text = ""
        generated_questions = generate_questions(
            resume_text=resume_text,
            jd_dict=jd_config.get("jd_dict", {}),
            weights=jd_config.get("weights", {}),
            question_count=jd_config.get("question_count", 10),
            project_ratio=jd_config.get("project_ratio", 80),
        )

    candidate = {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "status": row[3],
        "resume_path": row[4],
        "jd_config_id": row[5],
        "created_at": row[11],
    }

    return render_template(
        "hr_candidate_view.html",
        candidate=candidate,
        phase1=phase1,
        questions=questions,
        generated_questions=generated_questions,
        selected_jd=jd_config,
        answers=answers,
        monitoring=monitoring,
        summary=summary,
    )
