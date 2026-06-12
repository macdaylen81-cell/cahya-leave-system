from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from . import models
from .deps import get_current_user
from .routers import auth, totp, leaves, users, overtime
from .security import get_password_hash

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Cahya Mata Intelligence Leave Management System")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include routers (without notifications)
app.include_router(auth.router)
app.include_router(totp.router)
app.include_router(leaves.router)
app.include_router(users.router)
app.include_router(overtime.router)


# ====================== ROOT ROUTE (FIXED) ======================
@app.get("/", response_model=None)
def dashboard(
    request: Request, 
    db: Session = Depends(get_db), 
    user: models.User = Depends(get_current_user)
):
    """Main dashboard - redirects to login if not authenticated"""
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # Dashboard data for logged-in users
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
    """Create default admin account"""
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
    return {"detail": "✅ Admin created successfully! Username: admin | Password: admin123"}