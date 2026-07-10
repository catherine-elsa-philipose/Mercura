from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.dependencies import get_db
from app.models.user import User
from app.models.business_member import BusinessMember, BusinessRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    if not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not configured on the server.")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        user_id_int = int(user_id)
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise credentials_exception
        
    user = db.query(User).filter(User.id == user_id_int).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

def get_current_membership(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> BusinessMember:
    membership = db.query(BusinessMember).filter(
        BusinessMember.business_id == business_id,
        BusinessMember.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    return membership

def require_roles(*allowed_roles: BusinessRole):
    def dependency(
        membership: BusinessMember = Depends(get_current_membership)
    ) -> BusinessMember:
        allowed_strings = {role.value for role in allowed_roles}
        if membership.role not in allowed_strings:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        return membership
    return dependency

