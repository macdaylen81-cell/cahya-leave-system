from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from .database import get_db
from .security import get_current_user_from_cookie
from . import models

def get_db_dep():
    return next(get_db())

def get_current_user(request: Request, db: Session = Depends(get_db)):
    data = get_current_user_from_cookie(request)
    if not data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = db.query(models.User).filter(models.User.id == data["user_id"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return user

def require_role(*roles: models.RoleEnum):
    def role_checker(user: models.User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return role_checker
