from pyresparser import ResumeParser
import spacy

# Load spaCy model once
nlp = spacy.load("en_core_web_sm")


def extract_name_from_resume(resume_path):
    """
    Extract candidate name using pyresparser
    fallback to spaCy if needed
    """

    try:
        # Method 1: Using pyresparser
        data = ResumeParser(resume_path).get_extracted_data()

        if data and data.get("name"):
            return data["name"]

    except Exception as e:
        print("PyResParser failed:", e)

    # Method 2: Fallback using spaCy
    try:
        with open(resume_path, "r", encoding="utf-8") as f:
            text = f.read()

        doc = nlp(text)

        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text

    except Exception as e:
        print("SpaCy fallback failed:", e)

    return None
