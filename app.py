import os
from flask import Flask, jsonify, redirect, session

from database import get_db, init_db
from routes.candidate_routes import bp_candidate
from routes.hr_routes import bp_hr
from routes.interview_routes import bp_interview

# Read from Azure Environment Variables (safe defaults for local)
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")
app.config["BASE_URL"] = BASE_URL

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

init_db()

app.register_blueprint(bp_hr)
app.register_blueprint(bp_candidate)
app.register_blueprint(bp_interview)


@app.route("/")
def home():
    if not session.get("user_id"):
        return redirect("/login")
    if session.get("role") == "hr":
        return redirect("/hr/dashboard")
    return redirect("/candidate/home")


@app.route("/debug/db")
def debug_db():
    db = get_db()
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    db.close()
    return jsonify({"tables": tables})


@app.route("/debug/candidates_columns")
def debug_columns():
    db = get_db()
    cur = db.execute("PRAGMA table_info(candidates)")
    cols = cur.fetchall()
    db.close()
    return jsonify(cols)


@app.route("/debug/routes")
def debug_routes():
    return "<br>".join(sorted([str(r) for r in app.url_map.iter_rules()]))


if __name__ == "__main__":
    # local only
    app.run(host="0.0.0.0", port=5000, debug=True)
