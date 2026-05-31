from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from ..database import get_db
from ..deps import get_current_user
from .. import models

router = APIRouter(prefix="/notifications", tags=["notifications"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def notifications_page(
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    items = (
        db.query(models.Notification)
        .filter(models.Notification.user_id == user.id)
        .order_by(models.Notification.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "notifications.html",
        {"request": request, "user": user, "items": items, "title": "Notifications"},
    )


@router.post("/{notif_id}/read")
def mark_read(
    notif_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    n = (
        db.query(models.Notification)
        .filter(models.Notification.id == notif_id, models.Notification.user_id == user.id)
        .first()
    )
    if n:
        n.is_read = True
        db.commit()
    return RedirectResponse(url="/notifications", status_code=303)


@router.post("/read-all")
def read_all(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    db.query(models.Notification).filter(
        models.Notification.user_id == user.id,
        models.Notification.is_read == False,  # noqa: E712
    ).update({"is_read": True})
    db.commit()
    return RedirectResponse(url="/notifications", status_code=303)

