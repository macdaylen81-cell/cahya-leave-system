from passlib.context import CryptContext
from itsdangerous import URLSafeSerializer, BadSignature
from fastapi import Request, HTTPException, status
from .config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
serializer = URLSafeSerializer(settings.SECRET_KEY, salt="session")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_session_token(user_id: int) -> str:
    return serializer.dumps({"user_id": user_id})

def get_session_data(token: str):
    try:
        return serializer.loads(token)
    except BadSignature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

def get_current_user_from_cookie(request: Request):
    token = request.cookies.get("session")
    if not token:
        return None
    try:
        data = get_session_data(token)
        return data
    except HTTPException:
        return None
