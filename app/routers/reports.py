from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Optional
import pandas as pd
from io import BytesIO

from ..database import get_db
from .. import models
from ..deps import require_role

router = APIRouter(prefix="/reports", tags=["reports"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/hr-leaves")
def hr_leave_report(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.RoleEnum.hr, models.RoleEnum.admin)),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    query = db.query(models.LeaveRequest).order_by(models.LeaveRequest.start_date.desc())

    if start_date:
        query = query.filter(models.LeaveRequest.start_date >= start_date)
    if end_date:
        query = query.filter(models.LeaveRequest.end_date <= end_date)

    leaves = query.all()

    total = len(leaves)
    pending = sum(1 for l in leaves if l.status == models.LeaveStatusEnum.pending)
    approved = sum(1 for l in leaves if l.status == models.LeaveStatusEnum.approved)
    rejected = sum(1 for l in leaves if l.status == models.LeaveStatusEnum.rejected)

    return templates.TemplateResponse("hr_leave_report.html", {
        "request": request,
        "user": user,
        "leaves": leaves,
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "generated_at": datetime.now().strftime("%d %B %Y, %I:%M %p"),
        "start_date": start_date,
        "end_date": end_date,
    })


@router.get("/hr-leaves/export")
def export_hr_report(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.RoleEnum.hr, models.RoleEnum.admin)),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    query = db.query(models.LeaveRequest).order_by(models.LeaveRequest.start_date.desc())

    if start_date:
        query = query.filter(models.LeaveRequest.start_date >= start_date)
    if end_date:
        query = query.filter(models.LeaveRequest.end_date <= end_date)

    leaves = query.all()

    data = []
    for l in leaves:
        data.append({
            "Employee": l.user.username if l.user else "Unknown",
            "Email": l.user.email if l.user else "",
            "Leave Type": l.leave_type.value.title() if hasattr(l.leave_type, 'value') else str(l.leave_type),
            "Start Date": l.start_date.strftime("%d/%m/%Y") if l.start_date else "",
            "End Date": l.end_date.strftime("%d/%m/%Y") if l.end_date else "",
            "Days": (l.end_date - l.start_date).days + 1 if l.end_date and l.start_date else 0,
            "Status": l.status.value.title() if hasattr(l.status, 'value') else str(l.status),
            "Reason": l.reason or "",
            "Applied On": l.created_at.strftime("%d/%m/%Y %H:%M") if hasattr(l, 'created_at') and l.created_at else ""
        })

    df = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Leave_Report")
        
        # === STRONGER FIX FOR ####### ===
        worksheet = writer.sheets['Leave_Report']
        
        # Force specific widths for date columns
        worksheet.column_dimensions['A'].width = 25   # Employee
        worksheet.column_dimensions['B'].width = 18   # Leave Type
        worksheet.column_dimensions['C'].width = 18   # Start Date
        worksheet.column_dimensions['D'].width = 18   # End Date
        worksheet.column_dimensions['E'].width = 10   # Days
        worksheet.column_dimensions['F'].width = 15   # Status
        worksheet.column_dimensions['G'].width = 50   # Reason
        worksheet.column_dimensions['H'].width = 22   # Applied On

    output.seek(0)

    filename = f"Leave_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )