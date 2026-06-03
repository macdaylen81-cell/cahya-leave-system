from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import os

from .database import Base, engine, get_db
from . import models
from .deps import get_current_user_dep
from .security import get_current_user, get_password_hash

from .routers import auth, totp, leaves, users, overtime, notifications, reports, holidays

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Cahya Mata Intelligence Leave Management System")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router)
app.include_router(totp.router)
app.include_router(leaves.router)
app.include_router(users.router)
app.include_router(overtime.router)
app.include_router(notifications.router)
app.include_router(reports.router)
app.include_router(holidays.router)


@app.middleware("http")
async def force_password_change_middleware(request: Request, call_next):
    allowed_paths = [
        "/",
        "/login",
        "/change-password",
        "/totp/setup",
        "/totp/enable",
        "/init-admin",
        "/favicon.ico",
    ]

    if request.url.path in allowed_paths or request.url.path.startswith("/static"):
        return await call_next(request)

    if "session" in request.cookies:
        try:
            db = next(get_db())
            user = get_current_user(request=request, db=db)

            if user and getattr(user, "must_change_password", False):
                return RedirectResponse(url="/change-password", status_code=303)

            if user and not user.is_totp_enabled:
                return RedirectResponse(url="/totp/setup", status_code=303)

        except Exception:
            pass

    return await call_next(request)


@app.get("/")
def root():
    return RedirectResponse(url="/login", status_code=303)


@app.get("/dashboard")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user_dep),
):
    pending = None

    if user.role in (models.RoleEnum.manager, models.RoleEnum.admin):
        pending = db.query(models.LeaveRequest).filter(
            models.LeaveRequest.status == models.LeaveStatusEnum.pending
        ).count()

    my_pending = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.user_id == user.id,
        models.LeaveRequest.status == models.LeaveStatusEnum.pending,
    ).count()

    my_approved = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.user_id == user.id,
        models.LeaveRequest.status == models.LeaveStatusEnum.approved,
    ).count()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "pending": pending,
            "my_pending": my_pending,
            "my_approved": my_approved,
        },
    )


@app.get("/init-admin")
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

    seed_malaysia_holidays(db)

    return {"detail": "✅ Admin created + Malaysia Public Holidays seeded successfully!"}


def seed_malaysia_holidays(db: Session):
    from datetime import date

    holidays_2026 = [
        ("2026-01-01", "New Year's Day"),
        ("2026-02-17", "Chinese New Year"),
        ("2026-02-18", "Chinese New Year (Second Day)"),
        ("2026-03-31", "Hari Raya Aidilfitri"),
        ("2026-05-01", "Labour Day"),
        ("2026-05-27", "Hari Raya Haji"),
        ("2026-05-31", "Wesak Day"),
        ("2026-06-01", "Yang di-Pertuan Agong's Birthday"),
        ("2026-06-17", "Awal Muharram"),
        ("2026-08-31", "National Day"),
        ("2026-09-16", "Malaysia Day"),
        ("2026-11-09", "Deepavali"),
        ("2026-12-25", "Christmas Day"),
    ]

    for h_date, name in holidays_2026:
        existing = db.query(models.PublicHoliday).filter(
            models.PublicHoliday.date == date.fromisoformat(h_date)
        ).first()

        if not existing:
            db.add(
                models.PublicHoliday(
                    date=date.fromisoformat(h_date),
                    name=name,
                )
            )

    db.commit()
    print("✅ Malaysia Public Holidays for 2026 seeded successfully!")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
    )