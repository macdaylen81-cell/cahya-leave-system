from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import httpx
import pyotp

from ..database import get_db
from .. import models
from ..security import verify_password, get_password_hash, create_session_token
from ..config import settings
from ..deps import get_current_user

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


def get_logged_in_user(
    request: Request,
    db: Session = Depends(get_db)
):
    return get_current_user(request=request, db=db)


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
        },
    )


async def verify_recaptcha(response_token: str) -> bool:
    if not settings.RECAPTCHA_SECRET_KEY:
        return True

    data = {
        "secret": settings.RECAPTCHA_SECRET_KEY,
        "response": response_token,
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data=data,
        )
        j = r.json()
        return j.get("success", False)


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    totp_code: str = Form(None),
    g_recaptcha_response: str = Form(alias="g-recaptcha-response", default=""),
    db: Session = Depends(get_db),
):
    if not await verify_recaptcha(g_recaptcha_response):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "reCAPTCHA failed",
                "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
            },
            status_code=400,
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
            status_code=400,
        )

    if not user.is_active:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Account is inactive",
                "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
            },
            status_code=400,
        )

    if user.is_totp_enabled:
        if not totp_code:
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error": "Please enter your TOTP code",
                    "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
                },
                status_code=400,
            )

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code, valid_window=1):
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error": "Invalid TOTP code",
                    "recaptcha_site_key": settings.RECAPTCHA_SITE_KEY,
                },
                status_code=400,
            )

    token = create_session_token(user.id)

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        "session",
        token,
        httponly=True,
        samesite="lax",
        max_age=180,  
    )

    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session")
    return response


@router.get("/change-password")
def change_password_page(
    request: Request,
    user: models.User = Depends(get_logged_in_user),
):
    return templates.TemplateResponse(
        "change_password.html",
        {
            "request": request,
            "user": user,
        },
    )


@router.post("/change-password")
def change_password(
    request: Request,
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_logged_in_user),
):
    if new_password != confirm_password:
        return templates.TemplateResponse(
            "change_password.html",
            {
                "request": request,
                "user": user,
                "error": "Passwords do not match",
            },
            status_code=400,
        )

    if len(new_password) < 8:
        return templates.TemplateResponse(
            "change_password.html",
            {
                "request": request,
                "user": user,
                "error": "Password must be at least 8 characters",
            },
            status_code=400,
        )

    user.password_hash = get_password_hash(new_password)
    user.must_change_password = False
    db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/init-admin")
def init_admin(db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(
        models.User.role == models.RoleEnum.admin
    ).first()

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

    return {"detail": "✅ Admin created!"}