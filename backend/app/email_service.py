import smtplib
import os
from email.mime.text import MIMEText


def send_email(to_email, message, subject="Medicine Refill Reminder"):
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM") or smtp_username

    if not smtp_username or not smtp_password or not smtp_from:
        return {
            "success": False,
            "error": "Missing SMTP_USERNAME/SMTP_PASSWORD/SMTP_FROM configuration",
        }

    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = to_email

    try:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
