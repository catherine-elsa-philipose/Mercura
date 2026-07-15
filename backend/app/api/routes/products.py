from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership, require_roles
from app.db.dependencies import get_db
from app.models.business_member import BusinessMember, BusinessRole
from app.models.product import Product
from app.models.stock_adjustment import StockAdjustment
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.schemas.stock_adjustment import (
    StockAdjustmentCreate,
    StockAdjustmentResponse,
    StockAdjustmentListResponse,
)

router = APIRouter()


def get_product_or_404(
    business_id: int,
    product_id: int,
    db: Session,
) -> Product:
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.business_id == business_id,
        )
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return product


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    business_id: int,
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(
        require_roles(
            BusinessRole.OWNER,
            BusinessRole.MANAGER,
            BusinessRole.STAFF,
        )
    ),
):
    product = Product(
        business_id=business_id,
        name=product_in.name,
        category=product_in.category,
        sku=product_in.sku,
        barcode=product_in.barcode,
        cost_price=product_in.cost_price,
        selling_price=product_in.selling_price,
        current_stock=product_in.current_stock,
        minimum_stock=product_in.minimum_stock,
        image_url=product_in.image_url,
    )

    db.add(product)

    try:
        db.commit()
        db.refresh(product)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while creating the product.",
        )

    return product


@router.get(
    "",
    response_model=ProductListResponse,
)
def list_products(
    business_id: int,
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    query = db.query(Product).filter(
        Product.business_id == business_id
    )

    if search is not None and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Product.name.ilike(term),
                Product.category.ilike(term),
                Product.sku.ilike(term),
                Product.barcode.ilike(term),
            )
        )

    total = query.count()

    products = (
        query.order_by(Product.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ProductListResponse.build(
        items=products,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/low-stock",
    response_model=ProductListResponse,
)
def get_low_stock_products(
    business_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    query = db.query(Product).filter(
        Product.business_id == business_id,
        Product.current_stock < Product.minimum_stock,
        Product.is_active == True,
    )

    total = query.count()

    products = (
        query.order_by(Product.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ProductListResponse.build(
        items=products,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
def get_product(
    business_id: int,
    product_id: int,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    return get_product_or_404(
        business_id=business_id,
        product_id=product_id,
        db=db,
    )


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
)
def update_product(
    business_id: int,
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(
        require_roles(
            BusinessRole.OWNER,
            BusinessRole.MANAGER,
            BusinessRole.STAFF,
        )
    ),
):
    product = get_product_or_404(
        business_id=business_id,
        product_id=product_id,
        db=db,
    )

    update_data = product_in.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(product, field, value)

    try:
        db.commit()
        db.refresh(product)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while updating the product.",
        )

    return product
@router.patch(
    "/{product_id}/deactivate",
    response_model=ProductResponse,
)
def deactivate_product(
    business_id: int,
    product_id: int,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(
        require_roles(
            BusinessRole.OWNER,
            BusinessRole.MANAGER,
        )
    ),
):
    product = get_product_or_404(
        business_id=business_id,
        product_id=product_id,
        db=db,
    )

    product.is_active = False

    try:
        db.commit()
        db.refresh(product)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while deactivating the product.",
        )

    return product


@router.post(
    "/{product_id}/stock",
    response_model=StockAdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_stock_adjustment(
    business_id: int,
    product_id: int,
    adjustment_in: StockAdjustmentCreate,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(
        require_roles(
            BusinessRole.OWNER,
            BusinessRole.MANAGER,
            BusinessRole.STAFF,
        )
    ),
):
    product = get_product_or_404(
        business_id=business_id,
        product_id=product_id,
        db=db,
    )

    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot adjust stock for an inactive product.",
        )

    new_stock = product.current_stock + adjustment_in.quantity
    if new_stock < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient stock for this adjustment.",
        )

    product.current_stock = new_stock

    adjustment = StockAdjustment(
        business_id=business_id,
        product_id=product_id,
        adjustment_type=adjustment_in.adjustment_type,
        quantity=adjustment_in.quantity,
        reason=adjustment_in.reason,
        created_by=membership.user_id,
    )

    db.add(adjustment)

    try:
        db.commit()
        db.refresh(adjustment)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while creating the stock adjustment.",
        )

    return adjustment


@router.get(
    "/{product_id}/stock",
    response_model=StockAdjustmentListResponse,
)
def list_stock_adjustments(
    business_id: int,
    product_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    # Ensure product exists and belongs to business
    get_product_or_404(
        business_id=business_id,
        product_id=product_id,
        db=db,
    )

    query = db.query(StockAdjustment).filter(
        StockAdjustment.business_id == business_id,
        StockAdjustment.product_id == product_id,
    )

    total = query.count()

    adjustments = (
        query.order_by(StockAdjustment.created_at.desc(), StockAdjustment.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return StockAdjustmentListResponse.build(
        items=adjustments,
        total=total,
        page=page,
        page_size=page_size,
    )