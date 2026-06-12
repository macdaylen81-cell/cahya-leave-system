from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os

from .database import Base, engine, get_db
from . import models
from .deps import get_current_user_dep
from .security import get_current_user, get_password_hash
from .routers import auth, totp, leaves, users, overtime, reports, holidays

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Cahya Mata Intelligence Leave Management System")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router)
app.include_router(totp.router)
app.include_router(leaves.router)
app.include_router(users.router)
app.include_router(overtime.router)
app.include_router(reports.router)
app.include_router(holidays.router)


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


@app.middleware("http")
async def force_password_change_middleware(request: Request, call_next):
    skip_paths = [
        "/",
        "/login",
        "/change-password",
        "/totp/setup",
        "/totp/enable",
        "/init-admin",
        "/favicon.ico",
    ]

    if request.url.path in skip_paths or request.url.path.startswith("/static"):
        return await call_next(request)

    if "session" in request.cookies:
        try:
            db = next(get_db())
            user = get_current_user(request=request, db=db)

            if user and getattr(user, "must_change_password", False):
                return RedirectResponse(url="/change-password", status_code=303)

            if user and not getattr(user, "is_totp_enabled", False):
                return RedirectResponse(url="/totp/setup", status_code=303)

        except Exception:
            pass

    return await call_next(request)


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

    return {
        "detail": "✅ Admin created successfully! Username: admin | Password: admin123"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
    )