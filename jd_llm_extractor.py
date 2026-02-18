import requests
import json
import re

class JDKeywordExtractor:
    def __init__(self, model="llama3.2:3b", base_url="http://localhost:11434", timeout=60):
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    def _extract_json_obj(self, text: str):
        """
        Try to find the first JSON object {...} from a messy LLM response.
        Supports responses with markdown fences and extra text.
        """
        if not text:
            return None

        # remove markdown fences if present
        text = text.strip()
        text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = text.replace("```", "").strip()

        # Find a JSON object by scanning braces
        start = text.find("{")
        if start == -1:
            return None

        # brace matching
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:i+1]
                    try:
                        return json.loads(candidate)
                    except:
                        return None
        return None

    def extract(self, jd_text: str) -> dict:
        prompt = f"""
Return ONLY valid JSON (no explanations, no markdown).
JSON keys:
mandatory_programming, domain_skills, optional_domains, tools, soft_skills

Each value must be a list of strings.

JD:
{jd_text}
""".strip()

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        try:
            r = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print("❌ Ollama request failed:", e)
            return self._fallback_extract(jd_text)

        raw = (data.get("response") or "").strip()
        print("🔎 LLM RAW RESPONSE (first 200 chars):", raw[:200])

        obj = self._extract_json_obj(raw)
        if obj and isinstance(obj, dict):
            # Ensure all keys exist
            for k in ["mandatory_programming", "domain_skills", "optional_domains", "tools", "soft_skills"]:
                if k not in obj or not isinstance(obj[k], list):
                    obj[k] = []
            # clean strings
            for k in obj:
                obj[k] = [str(x).strip() for x in obj[k] if str(x).strip()]
            return obj

        print("⚠️ Could not parse JSON from LLM. Using fallback.")
        return self._fallback_extract(jd_text)

    def _fallback_extract(self, jd_text: str) -> dict:
        """
        Fast non-LLM fallback extraction using keyword matching.
        (Demo-safe: never crashes)
        """
        known = {
            "mandatory_programming": ["python", "java", "c", "c++", "javascript", "sql"],
            "domain_skills": ["ai/ml", "machine learning", "deep learning", "nlp", "cloud", "aws", "azure", "gcp"],
            "optional_domains": ["sap", "devops", "data engineering", "data analyst"],
            "tools": ["numpy", "pandas", "docker", "kubernetes", "git", "linux", "flask", "django"],
            "soft_skills": ["communication", "problem solving", "teamwork", "leadership"]
        }

        text = (jd_text or "").lower()
        out = {k: [] for k in known.keys()}

        for group, skills in known.items():
            for s in skills:
                if s.lower() in text:
                    out[group].append(s)

        return out
