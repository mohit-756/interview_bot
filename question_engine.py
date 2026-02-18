import re
from typing import List

SYSTEM_PROMPT = """You are an experienced technical interviewer.

Generate dynamic and project-specific interview questions based on the candidate's resume and selected JD.

Rules:
1. 80% questions must be project-based.
2. 20% questions must be theory + self introduction.
3. Avoid generic phrases like "Explain your project".
4. Ask deep and specific questions about:
   - Architecture decisions
   - Tools and technologies used
   - Challenges faced
   - Design patterns
   - Deployment process
   - Database schema design
   - APIs and integration
   - Performance optimization
   - Security measures
5. If project involves Java or Spring Boot, ask about:
   - Dependency Injection
   - REST API design
   - Exception handling
   - JPA/Hibernate usage
6. If project involves Angular, ask about:
   - Component communication
   - Services
   - Routing
   - State management
7. Include behavioral question about teamwork and impact.
8. Include 1 self-introduction question.
9. Keep questions concise but technically deep.

Return only the list of questions.
"""


def build_user_prompt(resume_text: str, jd_text: str, question_count: int = 10) -> str:
    return f"""
Selected JD:
{jd_text}

Candidate Resume:
{resume_text}

Generate exactly {int(question_count)} interview questions following all rules above.
""".strip()


def _extract_resume_skills(resume_text: str) -> List[str]:
    known_skills = [
        "Python",
        "Java",
        "Flask",
        "Django",
        "Machine Learning",
        "ML",
        "Deep Learning",
        "SQL",
        "MySQL",
        "PostgreSQL",
        "MongoDB",
        "Pandas",
        "NumPy",
        "Scikit-learn",
        "TensorFlow",
        "PyTorch",
        "AWS",
        "Docker",
        "Kubernetes",
        "JavaScript",
        "React",
        "Node.js",
        "Git",
    ]

    extracted = []
    lowered_resume = resume_text.lower()

    for skill in known_skills:
        pattern = r"\\b" + re.escape(skill.lower()) + r"\\b"
        if re.search(pattern, lowered_resume):
            extracted.append(skill)

    return extracted


def _extract_project_names(resume_text: str) -> List[str]:
    projects = []
    for line in resume_text.splitlines():
        cleaned_line = line.strip()
        if not cleaned_line:
            continue

        if "project" in cleaned_line.lower():
            match = re.search(
                r"(?i)(?:project\\s*[:\\-]?\\s*)(.+)$",
                cleaned_line,
            )
            project_name = match.group(1).strip() if match else cleaned_line
            if project_name and project_name not in projects:
                projects.append(project_name)

    return projects


def _collect_jd_skills(jd_dict: dict) -> List[str]:
    jd_dict = jd_dict or {}
    skills = []
    for key in ["mandatory_programming", "domain_skills", "optional_domains", "tools", "soft_skills"]:
        for item in jd_dict.get(key, []) or []:
            clean = str(item).strip()
            if clean:
                skills.append(clean)
    return skills


def _pick_weighted_skills(weights: dict, jd_dict: dict) -> List[str]:
    if not isinstance(weights, dict):
        weights = {}

    available = _collect_jd_skills(jd_dict)
    available_map = {s.lower(): s for s in available}
    picked = []

    for raw_skill, raw_weight in weights.items():
        skill = str(raw_skill).strip()
        if not skill:
            continue
        try:
            weight = int(raw_weight)
        except:
            weight = 0
        if weight <= 0:
            continue
        canonical = available_map.get(skill.lower(), skill)
        picked.append((canonical, weight))

    if not picked:
        fallback = []
        for s in available:
            if s.lower() not in {x[0].lower() for x in fallback}:
                fallback.append((s, 1))
        return [x[0] for x in fallback]

    picked.sort(key=lambda x: x[1], reverse=True)
    out = []
    seen = set()
    for skill, _weight in picked:
        key = skill.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(skill)
    return out


def _extract_projects_for_questions(resume_text: str) -> List[str]:
    text = resume_text or ""
    lines = [line.strip(" -\t\r") for line in text.splitlines() if line.strip()]
    projects = []
    in_projects_section = False

    for line in lines:
        lower = line.lower()
        if re.search(r"^\s*projects?\s*[:\-]?\s*$", lower):
            in_projects_section = True
            continue

        if in_projects_section and re.match(r"^[a-z][a-z\s]{0,30}\s*[:\-]?$", lower) and "project" not in lower:
            in_projects_section = False

        if in_projects_section or "project" in lower:
            cleaned = re.sub(r"(?i)^projects?\s*[:\-]?\s*", "", line).strip()
            if cleaned and cleaned.lower() not in {p.lower() for p in projects}:
                projects.append(cleaned)

    if not projects:
        projects = _extract_project_names(text)

    return projects


def generate_questions(resume_text, jd_dict, weights, question_count, project_ratio):
    try:
        total_questions = max(1, int(question_count))
    except:
        total_questions = 10

    try:
        ratio = int(project_ratio)
    except:
        ratio = 80
    ratio = min(100, max(0, ratio))

    project_questions_count = round(total_questions * (ratio / 100.0))
    theory_questions_count = total_questions - project_questions_count

    questions = []
    projects = _extract_projects_for_questions(resume_text)

    for idx in range(project_questions_count):
        if projects:
            project_name = projects[idx % len(projects)]
            questions.append(f"Explain your project: {project_name}. What problem did it solve and what was your contribution?")
        else:
            questions.append("Describe one project you built. Explain architecture, tradeoffs, and outcomes.")

    if theory_questions_count > 0:
        questions.append("Introduce yourself and summarize your relevant experience in 1-2 minutes.")
        remaining_theory = theory_questions_count - 1
    else:
        remaining_theory = 0

    weighted_skills = _pick_weighted_skills(weights, jd_dict)
    if not weighted_skills:
        weighted_skills = _collect_jd_skills(jd_dict)

    for idx in range(max(0, remaining_theory)):
        if weighted_skills:
            skill = weighted_skills[idx % len(weighted_skills)]
            questions.append(f"Explain key concepts of {skill} and where you applied it.")
        else:
            questions.append("Walk through a technical challenge you solved recently.")

    return questions[:total_questions]


def generate_dynamic_questions(resume_text: str, jd_dict: dict, num_questions=10):
    resume_skills = _extract_resume_skills(resume_text)
    default_weights = {skill: 1 for skill in resume_skills}
    return generate_questions(
        resume_text=resume_text,
        jd_dict=jd_dict,
        weights=default_weights,
        question_count=num_questions,
        project_ratio=80,
    )
