from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.dependencies import get_db
from app.api.deps import get_current_user, get_current_membership, require_roles
from app.models.user import User
from app.models.business import Business
from app.models.business_member import BusinessMember, BusinessRole
from app.models.customer import Customer
from app.schemas.business import (
    BusinessCreate,
    BusinessUpdate,
    BusinessResponse,
    BusinessWithRoleResponse,
)

router = APIRouter()


@router.post("", response_model=BusinessResponse)
def create_business(
    business_in: BusinessCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_business = Business(name=business_in.name)
    db.add(db_business)

    try:
        # Get the new business ID without committing yet.
        db.flush()

        # The user who creates the business becomes its OWNER.
        db_member = BusinessMember(
            business_id=db_business.id,
            user_id=current_user.id,
            role=BusinessRole.OWNER.value,
        )
        db.add(db_member)

        # Commit Business and BusinessMember together.
        db.commit()
        db.refresh(db_business)

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "A database error occurred while creating "
                "the business workspace."
            ),
        )

    except Exception:
        db.rollback()
        raise

    return db_business


@router.get("", response_model=list[BusinessWithRoleResponse])
def list_businesses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = (
        db.query(
            Business.id,
            Business.name,
            BusinessMember.role,
            Business.created_at,
            Business.updated_at,
        )
        .join(
            BusinessMember,
            Business.id == BusinessMember.business_id,
        )
        .filter(
            BusinessMember.user_id == current_user.id,
        )
        .all()
    )

    return [
        {
            "id": result.id,
            "name": result.name,
            "role": result.role,
            "created_at": result.created_at,
            "updated_at": result.updated_at,
        }
        for result in results
    ]


@router.get("/{business_id}", response_model=BusinessWithRoleResponse)
def get_business(
    business_id: int,
    membership: BusinessMember = Depends(get_current_membership),
):
    business = membership.business

    return {
        "id": business.id,
        "name": business.name,
        "role": membership.role,
        "created_at": business.created_at,
        "updated_at": business.updated_at,
    }


@router.put("/{business_id}", response_model=BusinessResponse)
def update_business(
    business_id: int,
    business_in: BusinessUpdate,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(require_roles(BusinessRole.OWNER, BusinessRole.MANAGER)),
):
    business = membership.business

    if business_in.name is not None:
        business.name = business_in.name

    try:
        db.commit()
        db.refresh(business)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update the business workspace.",
        )

    return business


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_business(
    business_id: int,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(require_roles(BusinessRole.OWNER)),
):
    business = membership.business
    try:
        db.delete(business)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete the business workspace.",
        )