from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import re

from ..database import get_db
from .. import models
from ..deps import require_role
from ..security import get_password_hash

router = APIRouter(prefix="/users", tags=["users"])
templates = Jinja2Templates(directory="app/templates")


def is_strong_password(password: str) -> bool:
    """Strong Password Policy"""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):      # Uppercase
        return False
    if not re.search(r"[a-z]", password):      # Lowercase
        return False
    if not re.search(r"[0-9]", password):      # Number
        return False
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", password):  # Special char
        return False
    return True


@router.get("/")
def list_users(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.RoleEnum.admin)),
):
    users = db.query(models.User).all()
    summary = {}
    for u in users:
        summary[u.id] = {
            "quota": u.annual_leave_quota or 20,
            "used": 0,
            "remaining": u.annual_leave_quota or 20,
        }

    approved = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.status == models.LeaveStatusEnum.approved
    ).all()

    for l in approved:
        days = (l.end_date - l.start_date).days + 1
        if l.user_id in summary:
            summary[l.user_id]["used"] += days

    for s in summary.values():
        s["remaining"] = s["quota"] - s["used"]

    return templates.TemplateResponse(
        "admin_users.html",
        {"request": request, "users": users, "user": user, "summary": summary},
    )


@router.post("/create")
def create_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: models.RoleEnum = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.RoleEnum.admin)),
):
    if not email.lower().endswith("@gmail.com"):
        return RedirectResponse(url="/users/?error=Only+@gmail.com+emails+allowed", status_code=303)

    if db.query(models.User).filter(models.User.email == email.lower()).first():
        return RedirectResponse(url="/users/?error=Email+already+exists", status_code=303)

    # Strong Password Check
    if not is_strong_password(password):
        return RedirectResponse(
            url="/users/?error=Password+must+be+at+least+8+chars+with+uppercase,+lowercase,+number+and+special+character",
            status_code=303
        )

    new_user = models.User(
        username=username,
        email=email.lower(),
        password_hash=get_password_hash(password),
        role=role,
        is_active=True,
        must_change_password=True,
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/users/", status_code=303)


@router.get("/{user_id}/edit")
def edit_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.RoleEnum.admin)),
):
    u = db.query(models.User).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return templates.TemplateResponse(
        "admin_user_edit.html",
        {"request": request, "user": user, "edit_user": u},
    )


@router.post("/{user_id}/update")
def update_user(
    user_id: int,
    username: str = Form(...),
    email: str = Form(...),          
    role: models.RoleEnum = Form(...),
    is_active: bool = Form(False),
    password: str = Form(""),
    force_password_reset: bool = Form(False),   # ← New
    annual_leave_quota: int = Form(20),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.RoleEnum.admin)),
):
    u = db.query(models.User).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    if not email.lower().endswith("@gmail.com"):
        return RedirectResponse(url="/users/?error=Only+@gmail.com+allowed", status_code=303)

    u.username = username
    u.email = email.lower()
    u.role = role
    u.is_active = is_active
    u.annual_leave_quota = annual_leave_quota

    # If admin sets a new password
    if password and password.strip():
        if not is_strong_password(password):
            return RedirectResponse(
                url=f"/users/{user_id}/edit?error=Password+must+be+strong", 
                status_code=303
            )
        u.password_hash = get_password_hash(password)
        u.must_change_password = True   # Force change

    # If admin checks the force reset box
    elif force_password_reset:
        u.must_change_password = True

    db.commit()
    return RedirectResponse(url="/users/", status_code=303)