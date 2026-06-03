from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from .database import get_db
from .security import get_current_user   # JWT version
from . import models


# Database dependency
def get_db_dep():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


# Current user dependency (JWT)
def get_current_user_dep(
    request: Request, 
    db: Session = Depends(get_db_dep)
):
    return get_current_user(request, db)


# Role checker
def require_role(*roles: models.RoleEnum):
    def role_checker(user: models.User = Depends(get_current_user_dep)):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Insufficient permissions"
            )
        return user
    return role_checker