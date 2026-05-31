from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date

from ..database import get_db
from .. import models
from ..deps import require_role

router = APIRouter(prefix="/holidays", tags=["holidays"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def holiday_list(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.RoleEnum.hr, models.RoleEnum.admin)),
):
    holidays = db.query(models.PublicHoliday).order_by(models.PublicHoliday.date).all()
    return templates.TemplateResponse("holiday_list.html", {
        "request": request,
        "user": user,
        "holidays": holidays
    })


@router.post("/add")
def add_holiday(
    holiday_date: date = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.RoleEnum.hr, models.RoleEnum.admin)),
):
    if db.query(models.PublicHoliday).filter(models.PublicHoliday.date == holiday_date).first():
        return RedirectResponse(url="/holidays/?error=Date+already+exists", status_code=303)

    new_holiday = models.PublicHoliday(date=holiday_date, name=name.strip())
    db.add(new_holiday)
    db.commit()
    return RedirectResponse(url="/holidays/", status_code=303)


@router.post("/seed-default")
def seed_default_holidays(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.RoleEnum.hr, models.RoleEnum.admin)),
):
    default_holidays = [
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

    added = 0
    for h_date, name in default_holidays:
        if not db.query(models.PublicHoliday).filter(models.PublicHoliday.date == date.fromisoformat(h_date)).first():
            db.add(models.PublicHoliday(date=date.fromisoformat(h_date), name=name))
            added += 1

    db.commit()
    return RedirectResponse(url="/holidays/?success=Added+" + str(added) + "+holidays", status_code=303)


@router.post("/{holiday_id}/delete")
def delete_holiday(
    holiday_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_role(models.RoleEnum.hr, models.RoleEnum.admin)),
):
    holiday = db.query(models.PublicHoliday).get(holiday_id)
    if holiday:
        db.delete(holiday)
        db.commit()
    return RedirectResponse(url="/holidays/", status_code=303)