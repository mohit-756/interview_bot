import json
import os
import uuid

from flask import Blueprint, current_app, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db
from resume_logic import resume_analysis
from routes.shared import (
    login_required,
    extract_text,
    get_all_jd_configs,
    get_jd_config_by_id,
    _send_schedule_mail,
    build_interview_link,
)

bp_candidate = Blueprint("candidate", __name__)


@bp_candidate.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not name or not email or not password:
            return "All fields required", 400

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)",
                (email, generate_password_hash(password), "candidate"),
            )
            db.execute(
                "INSERT OR IGNORE INTO candidates (name, email, status) VALUES (?, ?, ?)",
                (name, email, "new"),
            )
            db.commit()
        except Exception as e:
            db.close()
            return f"User already exists / DB error: {e}", 400
        db.close()

        return redirect("/login")

    html = """
    <h2>Candidate Register</h2>
    <form method="POST">
      Name: <input name="name"><br><br>
      Email: <input name="email"><br><br>
      Password: <input type="password" name="password"><br><br>
      <button type="submit">Register</button>
    </form>
    <br><a href="/login">Already registered? Login</a>
    """
    return html


@bp_candidate.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        db = get_db()
        user = db.execute(
            "SELECT id, password_hash, role FROM users WHERE email=?",
            (email,),
        ).fetchone()
        db.close()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            session["email"] = email
            session["role"] = user[2]

            if user[2] == "hr":
                return redirect("/hr/dashboard")
            return redirect("/candidate/home")

        return "Invalid credentials", 401

    html = """
    <h2>Login</h2>
    <form method="POST">
      Email: <input name="email"><br><br>
      Password: <input type="password" name="password"><br><br>
      <button type="submit">Login</button>
    </form>
    <br><a href="/register">New candidate? Register</a>
    <br><a href="/hr/login">HR Login</a>
    """
    return html


@bp_candidate.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@bp_candidate.route("/candidate/home")
@login_required(role="candidate")
def candidate_home():
    email = session["email"]
    db = get_db()
    row = db.execute(
        "SELECT name, status, resume_path FROM candidates WHERE email=?",
        (email,),
    ).fetchone()
    db.close()

    if not row:
        return "Candidate record not found"

    html = f"""
    <h2>Candidate Home</h2>
    <p><b>Name:</b> {row[0]}</p>
    <p><b>Status:</b> {row[1]}</p>
    <p><b>Resume:</b> {row[2] if row[2] else "Not uploaded"}</p>
    <a href="/candidate/upload">Upload Resume</a> |
    <a href="/logout">Logout</a>
    """
    return html


@bp_candidate.route("/candidate/upload", methods=["GET", "POST"])
@login_required(role="candidate")
def candidate_upload():
    if request.method == "GET":
        jd_rows = get_all_jd_configs()
        return render_template("candidate_upload.html", jd_rows=jd_rows)

    resume = request.files.get("resume")
    if not resume:
        return "Resume required", 400

    selected_jd = request.form.get("jd_config_id", "").strip()
    if not selected_jd.isdigit():
        return "Please select a valid JD", 400

    selected_jd_id = int(selected_jd)

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    path = os.path.join(upload_folder, resume.filename)
    resume.save(path)

    resume_text = extract_text(path)

    config = get_jd_config_by_id(selected_jd_id)
    if not config:
        return "Selected JD config missing.", 400

    jd_dict = config["jd_dict"]
    qualify_score = int(config.get("qualify_score", 60))

    result = resume_analysis(
        resume_text,
        jd_dict,
        qualify_score=qualify_score,
    )

    status = "rejected"
    if result.get("decision") == "Shortlisted":
        status = "shortlisted"

    email = session["email"]
    db = get_db()
    db.execute(
        """
        UPDATE candidates
        SET resume_path=?, jd_config_id=?, status=?, phase1_result_json=?, questions_json=?, interview_date=?, interview_link=?, interview_token=?
        WHERE email=?
        """,
        (
            path,
            selected_jd_id,
            status,
            json.dumps(result),
            None,
            None,
            None,
            None,
            email,
        ),
    )
    db.commit()
    db.close()

    return render_template(
        "candidate_result.html",
        result=result,
        selected_jd=config,
        qualify_score=qualify_score,
        can_schedule=status == "shortlisted",
    )


@bp_candidate.route("/candidate/schedule", methods=["GET", "POST"])
@login_required(role="candidate")
def candidate_schedule():
    email = session["email"]
    db = get_db()
    row = db.execute(
        "SELECT id, name, status FROM candidates WHERE email=?",
        (email,),
    ).fetchone()
    db.close()

    if not row:
        return "Candidate record not found", 404

    if row[2] != "shortlisted":
        return "Only shortlisted candidates can schedule interviews.", 403

    if request.method == "GET":
        return render_template("candidate_schedule.html")

    interview_date = request.form.get("interview_date", "").strip()
    if not interview_date:
        return "Interview date is required", 400

    interview_token = str(uuid.uuid4())
    interview_link = build_interview_link(interview_token)

    db = get_db()
    db.execute(
        """
        UPDATE candidates
        SET interview_date=?, interview_link=?, interview_token=?, status=?
        WHERE email=?
        """,
        (interview_date, interview_link, interview_token, "scheduled", email),
    )
    db.commit()
    db.close()

    _send_schedule_mail(email, interview_date, interview_link)

    return render_template(
        "candidate_schedule_success.html",
        interview_date=interview_date,
        interview_link=interview_link,
    )
