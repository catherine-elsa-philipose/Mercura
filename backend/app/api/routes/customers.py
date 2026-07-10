from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership, require_roles
from app.db.dependencies import get_db
from app.models.business_member import BusinessMember, BusinessRole
from app.models.customer import Customer
from app.schemas.customer import (
    CustomerCreate,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
)

router = APIRouter()


def get_customer_or_404(
    business_id: int,
    customer_id: int,
    db: Session,
) -> Customer:
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.business_id == business_id,
        )
        .first()
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    return customer


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(
    business_id: int,
    customer_in: CustomerCreate,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(
        require_roles(
            BusinessRole.OWNER,
            BusinessRole.MANAGER,
            BusinessRole.STAFF,
        )
    ),
):
    customer = Customer(
        business_id=business_id,
        name=customer_in.name,
        phone=customer_in.phone,
        email=str(customer_in.email) if customer_in.email is not None else None,
    )

    db.add(customer)

    try:
        db.commit()
        db.refresh(customer)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while creating the customer.",
        )

    return customer


@router.get(
    "",
    response_model=CustomerListResponse,
)
def list_customers(
    business_id: int,
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    query = db.query(Customer).filter(
        Customer.business_id == business_id
    )

    if search is not None and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Customer.name.ilike(term),
                Customer.phone.ilike(term),
                Customer.email.ilike(term),
            )
        )

    total = query.count()

    customers = (
        query.order_by(Customer.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return CustomerListResponse.build(
        items=customers,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
)
def get_customer(
    business_id: int,
    customer_id: int,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    return get_customer_or_404(
        business_id=business_id,
        customer_id=customer_id,
        db=db,
    )


@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
)
def update_customer(
    business_id: int,
    customer_id: int,
    customer_in: CustomerUpdate,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(
        require_roles(
            BusinessRole.OWNER,
            BusinessRole.MANAGER,
            BusinessRole.STAFF,
        )
    ),
):
    customer = get_customer_or_404(
        business_id=business_id,
        customer_id=customer_id,
        db=db,
    )

    update_data = customer_in.model_dump(
        exclude_unset=True
    )

    if "email" in update_data and update_data["email"] is not None:
        update_data["email"] = str(update_data["email"])

    for field, value in update_data.items():
        setattr(customer, field, value)

    try:
        db.commit()
        db.refresh(customer)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while updating the customer.",
        )

    return customer


@router.patch(
    "/{customer_id}/deactivate",
    response_model=CustomerResponse,
)
def deactivate_customer(
    business_id: int,
    customer_id: int,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(
        require_roles(
            BusinessRole.OWNER,
            BusinessRole.MANAGER,
        )
    ),
):
    customer = get_customer_or_404(
        business_id=business_id,
        customer_id=customer_id,
        db=db,
    )

    customer.is_active = False

    try:
        db.commit()
        db.refresh(customer)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while deactivating the customer.",
        )

    return customer