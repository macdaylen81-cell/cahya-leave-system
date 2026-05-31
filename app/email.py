from fastapi import BackgroundTasks
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .config import settings

def send_email_background(background_tasks: BackgroundTasks, email_to: str, subject: str, html: str):
    background_tasks.add_task(send_email, email_to, subject, html)

def send_email(email_to: str, subject: str, html: str):
    try:
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_SENDER
        msg['To'] = email_to
        msg['Subject'] = subject
        msg.attach(MIMEText(html, 'html'))

        # Use Brevo SMTP
        smtp_host = getattr(settings, 'SMTP_HOST', 'smtp-relay.brevo.com')

        server = smtplib.SMTP(smtp_host, 587)
        server.starttls()
        server.login(settings.SMTP_SENDER, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Email sent successfully to {email_to}")
        return True
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        return False