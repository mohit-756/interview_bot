import json
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from database import get_db
from question_engine import generate_questions
from routes.shared import (
    _fallback_questions_from_jd,
    _normalize_questions,
    _parse_json_dict,
    _parse_json_list,
    extract_text,
    get_latest_jd_config,
    get_jd_config_by_id,
)

bp_interview = Blueprint("interview", __name__, url_prefix="/interview")


@bp_interview.route("/<token>")
def interview(token):
    db = get_db()
    row = db.execute(
        """
        SELECT id, name, interview_date, questions_json, answers_json, monitoring_json, jd_config_id, resume_path
        FROM candidates
        WHERE interview_token=?
        """,
        (token,),
    ).fetchone()
    db.close()

    if not row:
        return "Invalid interview link", 404

    questions = _normalize_questions(_parse_json_list(row[3]))
    if not questions:
        config = get_jd_config_by_id(int(row[6])) if row[6] else None
        if not config:
            config = get_latest_jd_config() or {}
        resume_text = ""
        if row[7]:
            try:
                resume_text = extract_text(row[7])
            except:
                resume_text = ""

        questions = generate_questions(
            resume_text=resume_text,
            jd_dict=config.get("jd_dict", {}),
            weights=config.get("weights", {}),
            question_count=config.get("question_count", 10),
            project_ratio=config.get("project_ratio", 80),
        )
        if not questions:
            questions = _fallback_questions_from_jd(config.get("jd_dict", {}))

    existing_answers = _parse_json_list(row[4])
    monitoring = _parse_json_dict(row[5])

    return render_template(
        "interview_start.html",
        token=token,
        name=row[1],
        interview_date=row[2],
        questions=questions,
        existing_answers=existing_answers,
        monitoring=monitoring,
    )


@bp_interview.route("/<token>/save_answer", methods=["POST"])
def interview_save_answer(token):
    payload = request.get_json(silent=True) or {}
    question_index = int(payload.get("question_index", 0))
    answer = str(payload.get("answer", "")).strip()
    question_text = str(payload.get("question_text", "")).strip()
    try:
        time_taken = float(payload.get("time_taken_seconds", 0))
    except:
        time_taken = 0

    db = get_db()
    row = db.execute(
        "SELECT id, answers_json FROM candidates WHERE interview_token=?",
        (token,),
    ).fetchone()
    if not row:
        db.close()
        return jsonify({"ok": False, "error": "Invalid token"}), 404

    answers = _parse_json_list(row[1])
    updated = False
    for item in answers:
        if isinstance(item, dict) and int(item.get("question_index", -1)) == question_index:
            item["question_text"] = question_text
            item["answer"] = answer
            item["time_taken_seconds"] = round(max(0, time_taken), 2)
            item["submitted_at"] = datetime.utcnow().isoformat()
            updated = True
            break

    if not updated:
        answers.append(
            {
                "question_index": question_index,
                "question_text": question_text,
                "answer": answer,
                "time_taken_seconds": round(max(0, time_taken), 2),
                "submitted_at": datetime.utcnow().isoformat(),
            }
        )

    answers = sorted(
        [a for a in answers if isinstance(a, dict)],
        key=lambda x: int(x.get("question_index", 0)),
    )

    db.execute(
        "UPDATE candidates SET answers_json=? WHERE id=?",
        (json.dumps(answers), row[0]),
    )
    db.commit()
    db.close()
    return jsonify({"ok": True, "saved_count": len(answers)})


@bp_interview.route("/<token>/monitoring", methods=["POST"])
def interview_monitoring(token):
    payload = request.get_json(silent=True) or {}
    db = get_db()
    row = db.execute(
        "SELECT id, monitoring_json FROM candidates WHERE interview_token=?",
        (token,),
    ).fetchone()
    if not row:
        db.close()
        return jsonify({"ok": False, "error": "Invalid token"}), 404

    monitoring = _parse_json_dict(row[1])
    monitoring["camera_granted"] = bool(payload.get("camera_granted", monitoring.get("camera_granted", False)))
    monitoring["mic_granted"] = bool(payload.get("mic_granted", monitoring.get("mic_granted", False)))

    try:
        tab_switch_count = int(payload.get("tab_switch_count", monitoring.get("tab_switch_count", 0)))
    except:
        tab_switch_count = int(monitoring.get("tab_switch_count", 0))
    monitoring["tab_switch_count"] = max(int(monitoring.get("tab_switch_count", 0)), tab_switch_count)
    monitoring["last_updated_at"] = datetime.utcnow().isoformat()

    db.execute(
        "UPDATE candidates SET monitoring_json=? WHERE id=?",
        (json.dumps(monitoring), row[0]),
    )
    db.commit()
    db.close()
    return jsonify({"ok": True})


@bp_interview.route("/<token>/complete", methods=["POST"])
def interview_complete(token):
    payload = request.get_json(silent=True) or {}
    db = get_db()
    row = db.execute(
        """
        SELECT id, questions_json, answers_json, monitoring_json, jd_config_id, resume_path
        FROM candidates
        WHERE interview_token=?
        """,
        (token,),
    ).fetchone()
    if not row:
        db.close()
        return jsonify({"ok": False, "error": "Invalid token"}), 404

    questions = _normalize_questions(_parse_json_list(row[1]))
    if not questions:
        config = get_jd_config_by_id(int(row[4])) if row[4] else None
        if not config:
            config = get_latest_jd_config() or {}
        resume_text = ""
        if row[5]:
            try:
                resume_text = extract_text(row[5])
            except:
                resume_text = ""
        questions = generate_questions(
            resume_text=resume_text,
            jd_dict=config.get("jd_dict", {}),
            weights=config.get("weights", {}),
            question_count=config.get("question_count", 10),
            project_ratio=config.get("project_ratio", 80),
        )
        if not questions:
            questions = _fallback_questions_from_jd(config.get("jd_dict", {}))

    answers = [a for a in _parse_json_list(row[2]) if isinstance(a, dict)]
    monitoring = _parse_json_dict(row[3])

    monitoring["camera_granted"] = bool(payload.get("camera_granted", monitoring.get("camera_granted", False)))
    monitoring["mic_granted"] = bool(payload.get("mic_granted", monitoring.get("mic_granted", False)))
    try:
        monitoring["tab_switch_count"] = int(payload.get("tab_switch_count", monitoring.get("tab_switch_count", 0)))
    except:
        monitoring["tab_switch_count"] = int(monitoring.get("tab_switch_count", 0))
    monitoring["completed_at"] = datetime.utcnow().isoformat()

    answered = [a for a in answers if str(a.get("answer", "")).strip()]
    answer_lengths = [len(str(a.get("answer", "")).split()) for a in answered]
    avg_answer_length = round(sum(answer_lengths) / len(answer_lengths), 2) if answer_lengths else 0

    total_time_seconds = 0.0
    for a in answered:
        try:
            total_time_seconds += float(a.get("time_taken_seconds", 0))
        except:
            pass
    total_time_seconds = round(total_time_seconds, 2)

    total_questions = len(questions)
    answered_count = len(answered)
    coverage = answered_count / max(1, total_questions)
    length_factor = min(1.0, avg_answer_length / 30.0)
    communication_score = int(round(min(10.0, (coverage * 6.0) + (length_factor * 4.0))))

    summary = {
        "total_questions": total_questions,
        "answered_count": answered_count,
        "avg_answer_length": avg_answer_length,
        "total_time_seconds": total_time_seconds,
        "tab_switch_count": int(monitoring.get("tab_switch_count", 0)),
        "camera_granted": bool(monitoring.get("camera_granted", False)),
        "mic_granted": bool(monitoring.get("mic_granted", False)),
        "communication_score": communication_score,
    }

    db.execute(
        """
        UPDATE candidates
        SET monitoring_json=?, interview_summary_json=?, status=?
        WHERE id=?
        """,
        (json.dumps(monitoring), json.dumps(summary), "interview_completed", row[0]),
    )
    db.commit()
    db.close()
    return jsonify({"ok": True, "done_url": f"/interview/{token}/done"})


@bp_interview.route("/<token>/done")
def interview_done(token):
    db = get_db()
    row = db.execute(
        "SELECT name, interview_summary_json FROM candidates WHERE interview_token=?",
        (token,),
    ).fetchone()
    db.close()
    if not row:
        return "Invalid interview link", 404

    summary = _parse_json_dict(row[1])
    return render_template("interview_done.html", name=row[0], summary=summary)
