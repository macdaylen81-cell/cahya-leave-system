from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import pyotp

from ..database import get_db
from .. import models
from ..deps import get_current_user

router = APIRouter(prefix="/totp", tags=["totp"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/setup")
def totp_setup(request: Request, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if not user.totp_secret:
        user.totp_secret = pyotp.random_base32()
        db.add(user)
        db.commit()
        db.refresh(user)
    totp = pyotp.TOTP(user.totp_secret)
    provisioning_uri = totp.provisioning_uri(name=user.username, issuer_name="LeaveSystem")
    return templates.TemplateResponse(
        "totp_setup.html",
        {"request": request, "provisioning_uri": provisioning_uri, "secret": user.totp_secret, "user": user},
    )

@router.post("/enable")
async def enable_totp(request: Request, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    form = await request.form()
    code = form.get("code")
    totp = pyotp.TOTP(user.totp_secret)
    if not code or not totp.verify(code, valid_window=1):
        return templates.TemplateResponse(
            "totp_setup.html",
            {
                "request": request,
                "provisioning_uri": totp.provisioning_uri(name=user.username, issuer_name="LeaveSystem"),
                "secret": user.totp_secret,
                "user": user,
                "error": "Invalid code",
            },
            status_code=400,
        )
    user.is_totp_enabled = True
    db.add(user)
    db.commit()
    return RedirectResponse(url="/", status_code=303)
