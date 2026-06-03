from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import pyotp

from ..database import get_db
from .. import models
from ..deps import get_current_user_dep

router = APIRouter(prefix="/totp", tags=["totp"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/setup")
def totp_setup_page(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user_dep),
):
    if user.is_totp_enabled:
        return RedirectResponse(url="/dashboard", status_code=303)

    if not user.totp_secret:
        user.totp_secret = pyotp.random_base32()
        db.commit()
        db.refresh(user)

    totp = pyotp.TOTP(user.totp_secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name="Cahya Mata Intelligence"
    )

    return templates.TemplateResponse(
        "totp_setup.html",
        {
            "request": request,
            "user": user,
            "secret": user.totp_secret,
            "provisioning_uri": provisioning_uri,
        },
    )


@router.post("/enable")
def enable_totp(
    request: Request,
    code: str = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user_dep),
):
    if user.is_totp_enabled:
        return RedirectResponse(url="/dashboard", status_code=303)

    if not user.totp_secret:
        user.totp_secret = pyotp.random_base32()
        db.commit()
        db.refresh(user)

    totp = pyotp.TOTP(user.totp_secret)

    if not totp.verify(code, valid_window=1):
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="Cahya Mata Intelligence"
        )

        return templates.TemplateResponse(
            "totp_setup.html",
            {
                "request": request,
                "user": user,
                "secret": user.totp_secret,
                "provisioning_uri": provisioning_uri,
                "error": "Invalid verification code. Please try again.",
            },
            status_code=400,
        )

    user.is_totp_enabled = True
    db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)