import smtplib
from email.mime.text import MIMEText

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# 🔴 CHANGE THESE
SENDER_EMAIL = "mohitcheedala@gmail.com"
APP_PASSWORD = "djqlsluigjzekhan"


def send_mail(receiver_email, candidate_name, interview_link, interview_date):

    # Make name look clean
    candidate_name = candidate_name.title()

    body = f"""
Hello {candidate_name},

Your interview has been scheduled successfully.

📅 Interview Date: {interview_date}

🔗 Interview Link:
{interview_link}

Please join on time.

Best regards,
HR Team
"""

    msg = MIMEText(body)
    msg["Subject"] = "Interview Scheduled"
    msg["From"] = SENDER_EMAIL
    msg["To"] = receiver_email

    server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
    server.login(SENDER_EMAIL, APP_PASSWORD)
    server.send_message(msg)
    server.quit()
