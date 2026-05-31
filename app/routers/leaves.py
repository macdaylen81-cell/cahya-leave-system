from fastapi import APIRouter, Depends, Request, Form, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta

from ..database import get_db
from .. import models
from ..deps import get_current_user, require_role
from ..email import send_email_background

router = APIRouter(prefix="/leave", tags=["leave"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
def list_my_leaves(request: Request, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    leaves = db.query(models.LeaveRequest).filter(models.LeaveRequest.user_id == user.id).all()
    
    # Calculate working days for display
    for leave in leaves:
        current = leave.start_date
        working_days = 0
        while current <= leave.end_date:
            if current.weekday() < 5:  # Monday to Friday
                # Optional: exclude public holidays too
                holiday = db.query(models.PublicHoliday).filter(models.PublicHoliday.date == current).first()
                if not holiday:
                    working_days += 1
            current += timedelta(days=1)
        
        leave.display_days = working_days   # Add temporary attribute for template

    return templates.TemplateResponse("leave_list.html", {
        "request": request, 
        "leaves": leaves, 
        "user": user
    })

@router.get("/request")
def request_leave_page(request: Request, user: models.User = Depends(get_current_user)):
    return templates.TemplateResponse("leave_request.html", {"request": request, "user": user})


@router.post("/request")
def request_leave(
    request: Request,
    start_date: str = Form(...),
    end_date: str = Form(...),
    reason: str = Form(...),
    leave_type: str = Form("annual"),
    days: int = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    s = date.fromisoformat(start_date)
    e = date.fromisoformat(end_date)

    if days <= 0:
        return RedirectResponse(url="/leave/request?error=Invalid+date+range", status_code=303)

    # === 1. First, check half-year limit for Annual Leave ===
    if leave_type == "annual":
        current_year = datetime.today().year

        if user.leave_year != current_year:
            if not (user.carry_forward_days and user.carry_forward_expiry and user.carry_forward_expiry >= date.today()):
                user.carry_forward_days = 0
                user.carry_forward_expiry = None
            user.leave_year = current_year
            user.first_half_used = 0
            user.second_half_used = 0
            db.commit()

        is_first_half = s.month <= 6
        if is_first_half:
            remaining = 10 - (user.first_half_used or 0) + (user.carry_forward_days or 0)
            if days > remaining:
                return RedirectResponse(
                    url=f"/leave/request?error=First+half+limit+reached.+Only+{remaining}+days+left", 
                    status_code=303
                )
        else:
            remaining = 10 - (user.second_half_used or 0)
            if days > remaining:
                return RedirectResponse(
                    url=f"/leave/request?error=Second+half+limit+reached.+Only+{remaining}+days+left", 
                    status_code=303
                )

    # === 2. Then validate working days (exclude weekends + holidays) ===
    calculated_working_days = 0
    current = s
    while current <= e:
        if current.weekday() < 5:  # Monday to Friday
            holiday = db.query(models.PublicHoliday).filter(models.PublicHoliday.date == current).first()
            if not holiday:
                calculated_working_days += 1
        current += timedelta(days=1)

    if calculated_working_days != days:
        return RedirectResponse(
            url="/leave/request?error=Date+range+contains+holidays+or+weekends.+Please+reselect+dates", 
            status_code=303
        )

    # Create the leave request
    leave = models.LeaveRequest(
        user_id=user.id,
        start_date=s,
        end_date=e,
        reason=reason,
        leave_type=leave_type,
        status=models.LeaveStatusEnum.pending
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)

    # Notify Managers
    managers = db.query(models.User).filter(
        models.User.role.in_([models.RoleEnum.manager, models.RoleEnum.admin]),
        models.User.email.isnot(None)
    ).all()

    for manager in managers:
        send_email_background(background_tasks, manager.email,
            "New Leave Request",
            f"Employee {user.username} requested {days} working days {leave_type} leave from {s} to {e}.")

    return RedirectResponse(url="/leave/", status_code=303)

@router.get("/manage")
def manage_leaves(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.RoleEnum.manager, models.RoleEnum.admin)),
):
    pending = db.query(models.LeaveRequest)\
        .filter(models.LeaveRequest.status == models.LeaveStatusEnum.pending)\
        .order_by(models.LeaveRequest.start_date.desc())\
        .all()

    history = db.query(models.LeaveRequest)\
        .order_by(models.LeaveRequest.start_date.desc())\
        .all()

    return templates.TemplateResponse("leave_manage.html", {
        "request": request, 
        "pending": pending, 
        "history": history, 
        "user": user
    })


@router.post("/approve/{leave_id}")
def approve_leave(
    leave_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.RoleEnum.manager, models.RoleEnum.admin)),
    background_tasks: BackgroundTasks = None,
):
    leave = db.query(models.LeaveRequest).get(leave_id)
    if leave and leave.leave_type == models.LeaveTypeEnum.annual:
        # Count only working days
        days = 0
        current = leave.start_date
        while current <= leave.end_date:
            if current.weekday() < 5:   # Monday to Friday
                days += 1
            current += timedelta(days=1)

        if leave.user:
            # Deduct from carry forward first, then normal quota
            if leave.user.carry_forward_days and leave.user.carry_forward_days >= days:
                leave.user.carry_forward_days -= days
            else:
                if leave.user.carry_forward_days:
                    days -= leave.user.carry_forward_days
                    leave.user.carry_forward_days = 0

                leave.user.used_annual_leave = (leave.user.used_annual_leave or 0) + days

                if leave.start_date.month <= 6:
                    leave.user.first_half_used = (leave.user.first_half_used or 0) + days
                else:
                    leave.user.second_half_used = (leave.user.second_half_used or 0) + days

        leave.status = models.LeaveStatusEnum.approved
        db.commit()

        if leave.user and leave.user.email:
            send_email_background(background_tasks, leave.user.email, 
                "Leave Request Approved", 
                f"Your {leave.leave_type.value} leave ({days} working days) has been approved.")

    return RedirectResponse(url="/leave/manage", status_code=303)

@router.post("/reject/{leave_id}")
def reject_leave(
    leave_id: int,
    reason: str = Form(""),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.RoleEnum.manager, models.RoleEnum.admin)),
    background_tasks: BackgroundTasks = None,
):
    leave = db.query(models.LeaveRequest).get(leave_id)
    if leave:
        leave.status = models.LeaveStatusEnum.rejected
        db.commit()

        if leave.user and leave.user.email:
            send_email_background(background_tasks, leave.user.email, 
                "Leave Request Rejected", 
                f"Your {leave.leave_type.value} leave request was rejected.<br>Manager comment: {reason or 'No comment.'}")

    return RedirectResponse(url="/leave/manage", status_code=303)


@router.get("/employee/{user_id}/history")
def employee_leave_history(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.RoleEnum.manager, models.RoleEnum.admin)),
):
    employee = db.query(models.User).get(user_id)
    if not employee:
        return RedirectResponse(url="/leave/manage", status_code=303)

    history = db.query(models.LeaveRequest)\
        .filter(models.LeaveRequest.user_id == user_id)\
        .order_by(models.LeaveRequest.start_date.desc())\
        .all()

    return templates.TemplateResponse("employee_leave_history.html", {
        "request": request,
        "employee": employee,
        "history": history,
        "user": user
    })