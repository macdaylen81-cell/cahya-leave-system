import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fastapi import BackgroundTasks
from dotenv import load_dotenv

load_dotenv()

def send_email(to_email: str, subject: str, html_body: str) -> bool:
    sender = os.getenv("SMTP_SENDER")
    password = os.getenv("SMTP_PASSWORD")
    
    if not sender or not password:
        print("⚠️ Email not configured! Check .env file")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, to_email, msg.as_string())
        print(f"✅ Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False


def send_email_background(bg_tasks: BackgroundTasks, to_email: str, subject: str, html_body: str):
    bg_tasks.add_task(send_email, to_email, subject, html_body)