import re
from jd_config import JD
from resume_name_extractor import extract_name_from_resume

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
def detect_candidate_type(text):
    text = text.lower()

    for kw in FRESHER_KEYWORDS:
        if kw in text:
            return "fresher", 0

    years = re.findall(r'(\d+)\+?\s*years?', text)
    if years:
        return "experienced", max(map(int, years))

    return "fresher", 0


# ---------------- ACADEMIC EXTRACTION ----------------
def extract_percentages(text):
    percentages = re.findall(r'(\d{2})\s*%', text)
    return list(map(int, percentages))


def extract_cgpa(text):
    match = re.findall(r'cgpa[:\s]*([\d.]+)', text)
    if match:
        return float(match[0])
    return None


def cgpa_to_percentage(cgpa):
    return cgpa * 10


# ---------------- FRESHER ELIGIBILITY ----------------
def fresher_eligibility(text):
    percentages = extract_percentages(text)
    cgpa = extract_cgpa(text)

    marks = percentages.copy()
    if cgpa:
        marks.append(cgpa_to_percentage(cgpa))

    if not marks or any(m < 60 for m in marks):
        return False, "Academic score below 60%"

    if not any(lang in text for lang in PROGRAMMING_LANGUAGES):
        return False, "No minimum programming language found"

    if not any(dom in text for dom in DOMAIN_KEYWORDS):
        return False, "No basic domain knowledge found"

    return True, "Eligible fresher"


# ---------------- SCORING FUNCTIONS ----------------
def score_programming(text):
    mandatory = JD.get("mandatory_programming", [])
    matched = [s for s in mandatory if s.lower() in text]

    if not mandatory:
        return 0, []

    score = int((len(matched) / len(mandatory)) * 100)
    return score, matched


def score_domain_skills(text):
    domains = JD.get("domain_skills", [])
    matched = [s for s in domains if s.lower() in text]

    if not domains:
        return 0, []

    score = min(100, len(matched) * 25)
    return score, matched


def score_projects(text):
    if "project" not in text:
        return 30

    tech = ["python", "ml", "flask", "sql", "api"]
    depth = sum(1 for t in tech if t in text)

    if depth >= 3:
        return 90
    elif depth == 2:
        return 75
    return 55


def score_knowledge_confidence(text):
    hits = sum(1 for w in ACTION_WORDS if w in text)
    if hits >= 4:
        return 90
    elif hits >= 2:
        return 70
    return 45


def score_jd_domain_match(text):
    text = text.lower()

    mandatory = JD.get("mandatory_programming", [])
    domains = JD.get("domain_skills", [])
    optional = JD.get("optional_domains", [])

    matched = []
    score = 0
    max_score = (len(mandatory) * 5) + (len(domains) * 3) + (len(optional) * 2)

    for skill in mandatory:
        if skill.lower() in text:
            score += 5
            matched.append(skill)

    for domain in domains:
        if domain.lower() in text:
            score += 3
            matched.append(domain)

    for domain in optional:
        if domain.lower() in text:
            score += 2
            matched.append(domain)

    if max_score == 0:
        return 0, []

    final_score = int((score / max_score) * 100)
    return final_score, matched


# ---------------- RESUME ANALYSIS ----------------
def resume_analysis(resume_text, resume_path=None):
    text = resume_text.lower()
    candidate_type, years = detect_candidate_type(text)
     # -------- NAME EXTRACTION --------
    candidate_name = None

    if resume_path:
        try:
            candidate_name = extract_name_from_resume(resume_path)
        except Exception as e:
            print("Name extraction failed:", e)

    if not candidate_name:
        candidate_name = "Candidate"
        
    # Fresher eligibility
    if candidate_type == "fresher":
        eligible, reason = fresher_eligibility(text)
        if not eligible:
            result= {
                "candidate_type": "fresher",
                "final_score": 0,
                "decision": "Rejected",
                "domain_scores": {},
                "matched_details": {},
                "strength": None,
                "weakness": reason
            }
            result["candidate_name"] = candidate_name
            return result

    # Get scores + matched details
    prog_score, prog_matched = score_programming(text)
    domain_score, domain_matched = score_domain_skills(text)
    jd_score, jd_matched = score_jd_domain_match(text)

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

    # Fresher minimum threshold
    if candidate_type == "fresher":
        for domain, score in scores.items():
            if score < 60:
                result= {
                    "candidate_type": "fresher",
                    "final_score": 0,
                    "decision": "Rejected",
                    "domain_scores": scores,
                    "matched_details": matched_details,
                    "strength": max(scores, key=scores.get),
                    "weakness": f"{domain} below minimum 60%"
                }
                result["candidate_name"] = candidate_name
                return result
                

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

    decision = "Shortlisted" if final_score >= 75 else "Rejected"

    strength = max(scores, key=scores.get)
    weak_domains = [k for k, v in scores.items() if v < 60]
    weakness = weak_domains[0] if weak_domains else None

    result= {
        "candidate_type": candidate_type,
        "final_score": round(final_score, 2),
        "decision": decision,
        "domain_scores": scores,
        "matched_details": matched_details,
        "strength": strength,
        "weakness": weakness
    }
    result["candidate_name"] = candidate_name
    return result
