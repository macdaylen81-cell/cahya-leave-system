from fastapi import BackgroundTasks
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .config import settings

def send_email_background(background_tasks: BackgroundTasks, email_to: str, subject: str, html: str):
    background_tasks.add_task(send_email, email_to, subject, html)

def send_email(email_to: str, subject: str, html: str):
    try:
        print(f"📧 Attempting to send email to: {email_to}")
        print(f"📧 Subject: {subject}")

        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_SENDER
        msg['To'] = email_to
        msg['Subject'] = subject
        msg.attach(MIMEText(html, 'html'))

        smtp_host = getattr(settings, 'SMTP_HOST', 'smtp-relay.brevo.com')

        print(f"📧 Connecting to SMTP server: {smtp_host}")

        server = smtplib.SMTP(smtp_host, 587)
        server.starttls()
        server.login(settings.SMTP_SENDER, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"✅ SUCCESS: Email sent to {email_to}")
        return True

    except Exception as e:
        print(f"❌ EMAIL FAILED to {email_to}")
        print(f"❌ Error Type: {type(e).__name__}")
        print(f"❌ Error Message: {e}")
        return False