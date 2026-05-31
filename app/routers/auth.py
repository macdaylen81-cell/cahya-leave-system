from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import httpx
import pyotp
import re

from ..database import get_db
from .. import models
from ..security import verify_password, get_password_hash, create_session_token
from ..config import settings
from ..deps import get_current_user

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


def is_strong_password(password: str) -> bool:
    if len(password) < 8: 
        return False
    if not re.search(r"[A-Z]", password): 
        return False
    if not re.search(r"[a-z]", password): 
        return False
    if not re.search(r"[0-9]", password): 
        return False
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", password): 
        return False
    return True


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html", 
        {"request": request, "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY}
    )


async def verify_recaptcha(response_token: str) -> bool:
    if not settings.RECAPTCHA_SECRET_KEY:
        return True  # DEV mode
    data = {
        "secret": settings.RECAPTCHA_SECRET_KEY,
        "response": response_token,
    }
    async with httpx.AsyncClient() as client:
        r = await client.post("https://www.google.com/recaptcha/api/siteverify", data=data)
        j = r.json()
        return j.get("success", False)


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    totp_code: str = Form(None),
    g_recaptcha_response: str = Form("", alias="g-recaptcha-response"),
    db: Session = Depends(get_db),
):
    # reCAPTCHA Check
    if not g_recaptcha_response or not await verify_recaptcha(g_recaptcha_response):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Please complete the reCAPTCHA verification",
                "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid username or password",
                "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if user.is_totp_enabled:
        if not totp_code:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "TOTP code required",
                "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
            }, status_code=400)
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code, valid_window=1):
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Invalid TOTP code",
                "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
            }, status_code=400)

    # === FORCE PASSWORD CHANGE ON FIRST LOGIN ===
    if user.must_change_password:
        token = create_session_token(user.id)
        response = RedirectResponse(url="/change-password", status_code=302)
        response.set_cookie("session", token, httponly=True, samesite="lax")
        return response

    # Normal successful login
    token = create_session_token(user.id)
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie("session", token, httponly=True, samesite="lax")
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session")
    return response


@router.get("/init-admin")
def init_admin(db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.role == models.RoleEnum.admin).first()
    if existing:
        return {"detail": "Admin already exists"}

    admin = models.User(
        username="admin",
        email="admin@gmail.com",
        password_hash=get_password_hash("admin123"),
        role=models.RoleEnum.admin,
        is_active=True,
        must_change_password=False,
    )
    db.add(admin)
    db.commit()
    return {"detail": "✅ Admin created successfully!"}


# ==================== CHANGE PASSWORD ROUTES ====================
@router.get("/change-password")
def change_password_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = get_current_user(request=request, db=db)
        if not user.must_change_password:
            return RedirectResponse(url="/", status_code=303)
    except:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse("change_password.html", {"request": request, "user": user})


@router.post("/change-password")
def change_password(
    request: Request,
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        user = get_current_user(request=request, db=db)
    except:
        return RedirectResponse(url="/login", status_code=303)

    if new_password != confirm_password:
        return templates.TemplateResponse("change_password.html", {
            "request": request, 
            "user": user, 
            "error": "Passwords do not match"
        })

    if not is_strong_password(new_password):
        return templates.TemplateResponse("change_password.html", {
            "request": request, 
            "user": user, 
            "error": "Password must be at least 8 characters and include uppercase, lowercase, number & special character."
        })

    user.password_hash = get_password_hash(new_password)
    user.must_change_password = False
    db.commit()

    return RedirectResponse(url="/", status_code=303)