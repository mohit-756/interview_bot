import sqlite3

def log_behavior(candidate, event, confidence):

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO behavior_logs(candidate_name, suspicious_event, confidence, timestamp)
        VALUES (?, ?, ?, datetime('now'))
    """, (candidate, event, confidence))

    conn.commit()
    conn.close()
def save_transcript(candidate, question, answer):

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO interview_transcripts(candidate_name, question, answer, timestamp)
        VALUES (?, ?, ?, datetime('now'))
    """, (candidate, question, answer))

    conn.commit()
    conn.close()
