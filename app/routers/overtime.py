from fastapi import APIRouter, Depends, Request, Form, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date, datetime

from ..database import get_db
from .. import models
from ..deps import get_current_user, require_role
from ..email import send_email_background

router = APIRouter(prefix="/overtime", tags=["overtime"])
templates = Jinja2Templates(directory="app/templates")

HOURS_PER_DAY = 8.0


@router.get("/")
def my_overtime(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    rows = db.query(models.OvertimeRequest).filter(models.OvertimeRequest.user_id == user.id).all()
    return templates.TemplateResponse("overtime_my.html", {"request": request, "user": user, "rows": rows})


@router.get("/request")
def overtime_request_form(
    request: Request,
    user: models.User = Depends(get_current_user),
):
    return templates.TemplateResponse("overtime_request.html", {
        "request": request, 
        "user": user,
        "replacement_balance": user.replacement_leave_balance or 0
    })


@router.post("/request")
def overtime_request_submit(
    date_str: str = Form(...),
    hours: float = Form(...),
    reason: str = Form(""),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    ot_date = date.fromisoformat(date_str)

    if hours <= 0 or hours > 12:
        return RedirectResponse(url="/overtime/request?error=Hours+must+be+between+0+and+12", status_code=303)

    if ot_date.weekday() >= 5 and not reason:   # Weekend or Public Holiday
        return RedirectResponse(url="/overtime/request?error=OT+on+weekend+requires+reason", status_code=303)

    ot = models.OvertimeRequest(
        user_id=user.id,
        date=ot_date,
        hours=hours,
        reason=reason,
        status=models.OvertimeStatusEnum.pending
    )
    db.add(ot)
    db.commit()

    # Notify Managers
    managers = db.query(models.User).filter(
        models.User.role.in_([models.RoleEnum.manager, models.RoleEnum.admin]),
        models.User.email.isnot(None)
    ).all()

    for m in managers:
        send_email_background(background_tasks, m.email,
            "New Overtime Claim",
            f"Employee {user.username} requested {hours} hours OT on {ot_date}.")

    return RedirectResponse(url="/overtime/", status_code=303)


@router.get("/manage")
def manage_overtime(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.RoleEnum.manager, models.RoleEnum.admin)),
):
    rows = db.query(models.OvertimeRequest)\
        .order_by(models.OvertimeRequest.date.desc())\
        .all()
    return templates.TemplateResponse("overtime_manage.html", {
        "request": request, 
        "user": user, 
        "rows": rows
    })


@router.post("/{ot_id}/approve")
def approve_overtime(
    ot_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.RoleEnum.manager, models.RoleEnum.admin)),
    background_tasks: BackgroundTasks = None,
):
    ot = db.query(models.OvertimeRequest).get(ot_id)
    if not ot:
        return RedirectResponse(url="/overtime/manage", status_code=303)

    ot.status = models.OvertimeStatusEnum.approved
    ot.approved_hours = ot.hours

    days = ot.hours / HOURS_PER_DAY
    employee = db.query(models.User).get(ot.user_id)
    if employee:
        employee.replacement_leave_balance = (employee.replacement_leave_balance or 0) + days

    db.commit()

    if employee and employee.email:
        send_email_background(background_tasks, employee.email,
            "Overtime Claim Approved",
            f"Your overtime claim of {ot.hours} hours on {ot.date} has been approved. {days:.2f} replacement day(s) added.")

    return RedirectResponse(url="/overtime/manage", status_code=303)


@router.post("/{ot_id}/reject")
def reject_overtime(
    ot_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.RoleEnum.manager, models.RoleEnum.admin)),
    background_tasks: BackgroundTasks = None,
):
    ot = db.query(models.OvertimeRequest).get(ot_id)
    if ot:
        ot.status = models.OvertimeStatusEnum.rejected
        db.commit()

        employee = db.query(models.User).get(ot.user_id)
        if employee and employee.email:
            send_email_background(background_tasks, employee.email,
                "Overtime Claim Rejected",
                f"Your overtime claim on {ot.date} was rejected.")

    return RedirectResponse(url="/overtime/manage", status_code=303)