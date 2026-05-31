from fastapi import BackgroundTasks
from .config import settings
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


def send_email_background(background_tasks: BackgroundTasks, email_to: str, subject: str, html: str):
    background_tasks.add_task(send_email, email_to, subject, html)


def send_email(email_to: str, subject: str, html: str):
    try:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = settings.BREVO_API_KEY

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        email = sib_api_v3_sdk.SendSmtpEmail(
            sender={
                "name": settings.SMTP_FROM_NAME,
                "email": settings.SMTP_FROM_EMAIL,
            },
            to=[{"email": email_to}],
            subject=subject,
            html_content=html,
        )

        api_instance.send_transac_email(email)

        print(f"✅ SUCCESS: Email sent to {email_to}")
        return True

    except ApiException as e:
        print(f"❌ BREVO API ERROR: {e}")
        return False

    except Exception as e:
        print(f"❌ EMAIL FAILED to {email_to}")
        print(f"❌ Error Type: {type(e).__name__}")
        print(f"❌ Error Message: {e}")
        return False