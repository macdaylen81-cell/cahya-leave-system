from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from .database import get_db
from .security import get_current_user   # ← Updated import
from . import models


def get_db_dep():
    return next(get_db())


# Main dependency to get current user from JWT token
def get_current_user_dependency(
    request: Request, 
    db: Session = Depends(get_db)
):
    return get_current_user(request, db)


# Role-based permission checker
def require_role(*roles: models.RoleEnum):
    def role_checker(user: models.User = Depends(get_current_user_dependency)):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Insufficient permissions"
            )
        return user
    return role_checker