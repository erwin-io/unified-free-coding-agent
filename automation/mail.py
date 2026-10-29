"""Optional owner status email. No prompts, code or secrets are included."""
import os
import smtplib
from email.message import EmailMessage
from . import util


def notify(subject, body):
    if not util.flag("EMAIL_ENABLED", False):
        return False
    owner = os.getenv("OWNER_EMAIL", "").strip()
    sender = os.getenv("EMAIL_FROM", "").strip() or os.getenv("SMTP_USERNAME", "").strip()
    user = os.getenv("SMTP_USERNAME", "").strip()
    pwd = os.getenv("SMTP_APP_PASSWORD", "").strip()
    if not all((owner, sender, user, pwd)):
        print("Owner email requested but SMTP variables are incomplete.")
        return False
    mail = EmailMessage()
    mail["From"], mail["To"], mail["Subject"] = sender, owner, subject[:180]
    mail.set_content(body[:20000])
    try:
        with smtplib.SMTP_SSL(os.getenv("SMTP_HOST", "smtp.gmail.com"),
                              int(os.getenv("SMTP_PORT", "465")), timeout=25) as smtp:
            smtp.login(user, pwd)
            smtp.send_message(mail)
        return True
    except (OSError, smtplib.SMTPException) as error:
        print("Owner email delivery failed:", type(error).__name__)
        return False
