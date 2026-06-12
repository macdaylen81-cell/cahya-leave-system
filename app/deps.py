from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .security import get_current_user_from_cookie   # ← Make sure this function exists
from . import models


# Main dependency to get current user
def get_current_user_dep(
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user_from_cookie(request=request, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return user


# Role-based permission checker
def require_role(*roles: models.RoleEnum):
    def role_checker(
        user: models.User = Depends(get_current_user_dep),
    ):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_checker