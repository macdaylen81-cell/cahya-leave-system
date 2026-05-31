from sqlalchemy.orm import Session
from . import models

def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    link: str | None = None,
):
    n = models.Notification(
        user_id=user_id,
        title=title,
        message=message,
        link=link,
        is_read=False,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n
