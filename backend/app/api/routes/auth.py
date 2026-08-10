from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.dependencies import get_db
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse
from app.models.user import User
from app.models.business import Business
from app.models.business_member import BusinessMember, BusinessRole
from app.core.security import hash_password, verify_password, create_access_token
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    normalized_email = user_in.email.strip().lower()

    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system."
        )

    user = User(
        email=normalized_email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
    )

    db.add(user)
    db.flush() # Flush to get the user ID for the member record

    # Create business with user-provided name or fallback
    if user_in.business_name and user_in.business_name.strip():
        business_name = user_in.business_name.strip()
    else:
        business_name = f"{user.full_name}'s Business" if user.full_name else f"{user.email}'s Business"
    business = Business(name=business_name)
    db.add(business)
    db.flush() # Flush to get business ID

    # Assign owner role
    business_member = BusinessMember(
        business_id=business.id,
        user_id=user.id,
        role=BusinessRole.OWNER.value
    )
    db.add(business_member)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Registration failed due to a duplicate or invalid entry."
        )

    return user


@router.post("/login", response_model=TokenResponse)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    normalized_email = user_in.email.strip().lower()

    user = db.query(User).filter(User.email == normalized_email).first()

    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Inactive user"
        )

    return {
        "access_token": create_access_token(user.id)
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user