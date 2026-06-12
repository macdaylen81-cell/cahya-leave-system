from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from . import models
from .deps import get_current_user_dep
from .routers import auth, totp, leaves, users, overtime, notifications
from .security import get_password_hash

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Cahya Mata Intelligence Leave Management System")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include all routers
app.include_router(auth.router)
app.include_router(totp.router)
app.include_router(leaves.router)
app.include_router(users.router)
app.include_router(overtime.router)
app.include_router(notifications.router)


# ====================== DASHBOARD ======================
@app.get("/")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user_dep),
):
    # Accurate balance calculation
    total_used = user.used_annual_leave or 0
    annual_remaining = user.annual_leave_quota - total_used

    first_half_remaining = 10 - (user.first_half_used or 0) + (user.carry_forward_days or 0)
    second_half_remaining = 10 - (user.second_half_used or 0)

    # Count requests
    my_pending = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.user_id == user.id,
        models.LeaveRequest.status == models.LeaveStatusEnum.pending
    ).count()

    my_approved = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.user_id == user.id,
        models.LeaveRequest.status == models.LeaveStatusEnum.approved
    ).count()

    pending_for_approval = None
    if user.role in (models.RoleEnum.manager, models.RoleEnum.admin):
        pending_for_approval = db.query(models.LeaveRequest).filter(
            models.LeaveRequest.status == models.LeaveStatusEnum.pending
        ).count()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "annual_remaining": max(0, annual_remaining),
            "first_half_remaining": max(0, first_half_remaining),
            "second_half_remaining": max(0, second_half_remaining),
            "carry_forward": user.carry_forward_days or 0,
            "pending": my_pending,
            "approved": my_approved,
            "pending_for_approval": pending_for_approval,
        },
    )


# ====================== INIT ADMIN ======================
@app.get("/init-admin")
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
        annual_leave_quota=20,
    )
    db.add(admin)
    db.commit()
    return {"detail": "✅ Admin created successfully! Username: admin | Password: admin123"}