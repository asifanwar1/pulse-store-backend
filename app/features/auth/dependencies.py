from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError
from app.dependencies import get_db
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.features.users.models import User, UserStatus

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def _extract_bearer_token(oauth_token: str | None, authorization: str | None) -> str:
    if oauth_token:
        return oauth_token

    if not authorization:
        raise UnauthorizedException()

    parts = authorization.strip().split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
        return parts[1].strip()

    # Some clients send the raw token in Authorization without the Bearer prefix.
    if authorization.strip():
        return authorization.strip()

    raise UnauthorizedException()


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    token = _extract_bearer_token(token, authorization)
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise UnauthorizedException()
        user_id = payload.get("sub")
        if user_id is None:
            raise UnauthorizedException()
    except JWTError:
        raise UnauthorizedException()
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        raise UnauthorizedException()
    user = db.query(User).filter(User.id == uid).first()
    if not user or not user.is_active or not user.is_verified or user.status != UserStatus.ACTIVE.value:
        raise UnauthorizedException()
    return user


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise ForbiddenException("Admin access required")
    return current_user
