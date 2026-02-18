# resume_logic.py
import re

# --------- Tunables / Defaults ----------
# NOTE: HR dashboard will override qualify_score (and optionally min_domain_score) via app.py
DEFAULT_MIN_DOMAIN_SCORE_FRESHER = 30      # was 60 hard reject → now 30 (demo-friendly)
DEFAULT_QUALIFY_SCORE = 40                 # fallback if HR doesn't pass anything

ACTION_WORDS = [
    "implemented", "developed", "designed",
    "built", "trained", "analyzed",
    "created", "deployed"
]

FRESHER_KEYWORDS = [
    "currently studying", "pursuing", "student",
    "final year", "undergraduate", "bachelor",
    "b.tech", "be"
]

PROGRAMMING_LANGUAGES = [
    "python", "java", "c++", "c", "javascript"
]

DOMAIN_KEYWORDS = [
    "machine learning", "ai", "web", "flask",
    "data analysis", "ml", "html", "css"
]


# ---------------- CANDIDATE TYPE ----------------
def detect_candidate_type(text: str):
    text = (text or "").lower()

    for kw in FRESHER_KEYWORDS:
        if kw in text:
            return "fresher", 0

    years = re.findall(r'(\d+)\+?\s*years?', text)
    if years:
        return "experienced", max(map(int, years))

    return "fresher", 0


# ---------------- ACADEMIC EXTRACTION ----------------
def extract_percentages(text: str):
    percentages = re.findall(r'(\d{2})\s*%', (text or ""))
    return list(map(int, percentages)) if percentages else []


def extract_cgpa(text: str):
    match = re.findall(r'cgpa[:\s]*([\d.]+)', (text or "").lower())
    if match:
        try:
            return float(match[0])
        except:
            return None
    return None


def cgpa_to_percentage(cgpa: float):
    return cgpa * 10


# ---------------- FRESHER ELIGIBILITY ----------------
def fresher_eligibility(text: str):
    text = (text or "").lower()
    percentages = extract_percentages(text)
    cgpa = extract_cgpa(text)

    marks = percentages.copy()
    if cgpa:
        marks.append(cgpa_to_percentage(cgpa))

    # keep basic filter (avoid super low marks)
    if not marks or any(m < 40 for m in marks):
        return False, "Academic score below 40%"

    if not any(lang in text for lang in PROGRAMMING_LANGUAGES):
        return False, "No minimum programming language found"

    if not any(dom in text for dom in DOMAIN_KEYWORDS):
        return False, "No basic domain knowledge found"

    return True, "Eligible fresher"


# ---------------- SCORING FUNCTIONS ----------------
def score_programming(text: str, jd_dict: dict):
    text = (text or "").lower()
    jd_dict = jd_dict or {}

    mandatory = jd_dict.get("mandatory_programming", []) or []
    matched = [s for s in mandatory if (s or "").lower() in text]

    if not mandatory:
        return 0, []

    score = int((len(matched) / len(mandatory)) * 100)
    return score, matched


def score_domain_skills(text: str, jd_dict: dict):
    text = (text or "").lower()
    jd_dict = jd_dict or {}

    domains = jd_dict.get("domain_skills", []) or []
    matched = [s for s in domains if (s or "").lower() in text]

    if not domains:
        return 0, []

    # simple scoring: each match gives 25 (cap 100)
    score = min(100, len(matched) * 25)
    return score, matched


def score_projects(text: str):
    text = (text or "").lower()

    if "project" not in text:
        return 30

    tech = ["python", "ml", "flask", "sql", "api"]
    depth = sum(1 for t in tech if t in text)

    if depth >= 3:
        return 90
    elif depth == 2:
        return 75
    return 55


def score_knowledge_confidence(text: str):
    text = (text or "").lower()
    hits = sum(1 for w in ACTION_WORDS if w in text)

    if hits >= 4:
        return 90
    elif hits >= 2:
        return 70
    return 45


def score_jd_domain_match(text: str, jd_dict: dict):
    text = (text or "").lower()
    jd_dict = jd_dict or {}

    mandatory = jd_dict.get("mandatory_programming", []) or []
    domains = jd_dict.get("domain_skills", []) or []
    optional = jd_dict.get("optional_domains", []) or []

    matched = []
    score = 0
    max_score = (len(mandatory) * 5) + (len(domains) * 3) + (len(optional) * 2)

    for skill in mandatory:
        if (skill or "").lower() in text:
            score += 5
            matched.append(skill)

    for domain in domains:
        if (domain or "").lower() in text:
            score += 3
            matched.append(domain)

    for domain in optional:
        if (domain or "").lower() in text:
            score += 2
            matched.append(domain)

    if max_score == 0:
        return 0, []

    final_score = int((score / max_score) * 100)
    return final_score, matched


# ---------------- RESUME ANALYSIS ----------------
def resume_analysis(
    resume_text: str,
    jd_dict: dict,
    qualify_score: int = DEFAULT_QUALIFY_SCORE,
    min_domain_score_fresher: int = DEFAULT_MIN_DOMAIN_SCORE_FRESHER,
    strict_fresher_gate: bool = False
):
    """
    ✅ IMPORTANT (your requirement):
    - qualify_score is passed from HR dashboard (app.py) and used as final cutoff.

    Options:
    - strict_fresher_gate=False (recommended): no hard rejection on low domain scores.
    - strict_fresher_gate=True: fresher will be rejected if any domain score < min_domain_score_fresher.
    """
    text = (resume_text or "").lower()
    jd_dict = jd_dict or {}

    candidate_type, years = detect_candidate_type(text)

    # Fresher basic eligibility filter (keep it)
    if candidate_type == "fresher":
        eligible, reason = fresher_eligibility(text)
        if not eligible:
            return {
                "candidate_type": "fresher",
                "final_score": 0,
                "decision": "Rejected",
                "domain_scores": {},
                "matched_details": {},
                "strength": None,
                "weakness": reason
            }

    # Scores
    prog_score, prog_matched = score_programming(text, jd_dict)
    domain_score, domain_matched = score_domain_skills(text, jd_dict)
    jd_score, jd_matched = score_jd_domain_match(text, jd_dict)

    scores = {
        "programming": prog_score,
        "domain_skills": domain_score,
        "projects": score_projects(text),
        "knowledge_confidence": score_knowledge_confidence(text),
        "jd_domain_match": jd_score
    }

    matched_details = {
        "programming": prog_matched,
        "domain_skills": domain_matched,
        "jd_domain_match": jd_matched
    }

    # OPTIONAL hard gate (OFF by default)
    if candidate_type == "fresher" and strict_fresher_gate:
        for domain, score in scores.items():
            if score < min_domain_score_fresher:
                return {
                    "candidate_type": "fresher",
                    "final_score": 0,
                    "decision": "Rejected",
                    "domain_scores": scores,
                    "matched_details": matched_details,
                    "strength": max(scores, key=scores.get),
                    "weakness": f"{domain} below minimum {min_domain_score_fresher}%"
                }

    # Final weighted score
    if candidate_type == "experienced":
        scores["experience"] = min(100, years * 20)
        final_score = (
            0.20 * scores["programming"] +
            0.15 * scores["domain_skills"] +
            0.20 * scores["projects"] +
            0.15 * scores["knowledge_confidence"] +
            0.15 * scores["jd_domain_match"] +
            0.15 * scores["experience"]
        )
    else:
        final_score = (
            0.25 * scores["programming"] +
            0.20 * scores["domain_skills"] +
            0.20 * scores["projects"] +
            0.15 * scores["knowledge_confidence"] +
            0.20 * scores["jd_domain_match"]
        )

    # ✅ HR Dashboard cutoff is used here
    decision = "Shortlisted" if final_score >= int(qualify_score or DEFAULT_QUALIFY_SCORE) else "Rejected"

    strength = max(scores, key=scores.get) if scores else None
    weak_domains = [k for k, v in scores.items() if v < min_domain_score_fresher]
    weakness = weak_domains[0] if weak_domains else None

    return {
        "candidate_type": candidate_type,
        "final_score": round(float(final_score), 2),
        "decision": decision,
        "domain_scores": scores,
        "matched_details": matched_details,
        "strength": strength,
        "weakness": weakness
    }
