from datetime import date, datetime
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership, require_roles
from app.db.dependencies import get_db
from app.models.business_member import BusinessMember, BusinessRole
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_item import InvoiceItem
from app.models.product import Product
from app.models.stock_adjustment import StockAdjustment
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
)
from app.schemas.invoice_item import (
    InvoiceItemCreate,
    InvoiceItemUpdate,
    InvoiceItemResponse,
)

router = APIRouter()


def get_invoice_or_404(
    business_id: int,
    invoice_id: int,
    db: Session,
) -> Invoice:
    invoice = (
        db.query(Invoice)
        .filter(
            Invoice.id == invoice_id,
            Invoice.business_id == business_id,
        )
        .first()
    )

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    return invoice


@router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invoice(
    business_id: int,
    invoice_in: InvoiceCreate,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(
        require_roles(
            BusinessRole.OWNER,
            BusinessRole.MANAGER,
            BusinessRole.STAFF,
        )
    ),
):
    # Verify customer exists and is active
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == invoice_in.customer_id,
            Customer.business_id == business_id,
        )
        .first()
    )
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )
    if not customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot invoice an inactive customer.",
        )

    # Verify we have items
    if not invoice_in.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice must contain at least one item.",
        )

    # Calculate item line totals and subtotal
    invoice_items = []
    subtotal = Decimal("0.00")

    for item_in in invoice_in.items:
        product = (
            db.query(Product)
            .filter(
                Product.id == item_in.product_id,
                Product.business_id == business_id,
            )
            .first()
        )
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {item_in.product_id} not found.",
            )
        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{product.name}' is inactive.",
            )

        unit_price = (
            item_in.unit_price
            if item_in.unit_price is not None
            else product.selling_price
        )
        line_total = Decimal(str(item_in.quantity)) * unit_price
        subtotal += line_total

        invoice_item = InvoiceItem(
            product_id=product.id,
            quantity=item_in.quantity,
            unit_price=unit_price,
            line_total=line_total,
        )
        invoice_items.append(invoice_item)

    total = subtotal + invoice_in.tax - invoice_in.discount
    if total < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice total cannot be negative.",
        )

    # Generate a unique invoice number
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_suffix = uuid.uuid4().hex[:6].upper()
    invoice_number = f"INV-{business_id}-{timestamp}-{random_suffix}"

    # Create Invoice
    invoice = Invoice(
        business_id=business_id,
        customer_id=invoice_in.customer_id,
        invoice_number=invoice_number,
        status=InvoiceStatus.UNPAID,
        subtotal=subtotal,
        tax=invoice_in.tax,
        discount=invoice_in.discount,
        total=total,
        notes=invoice_in.notes,
        invoice_date=invoice_in.invoice_date,
        due_date=invoice_in.due_date,
        items=invoice_items,
    )

    db.add(invoice)

    try:
        db.commit()
        db.refresh(invoice)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while creating the invoice.",
        )

    return invoice


@router.get(
    "",
    response_model=InvoiceListResponse,
)
def list_invoices(
    business_id: int,
    customer_id: int | None = Query(default=None),
    status_filter: InvoiceStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    query = db.query(Invoice).filter(Invoice.business_id == business_id)

    if customer_id is not None:
        query = query.filter(Invoice.customer_id == customer_id)

    if status_filter is not None:
        query = query.filter(Invoice.status == status_filter)

    if search is not None and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(Invoice.invoice_number.ilike(term))

    if start_date is not None:
        query = query.filter(Invoice.invoice_date >= start_date)

    if end_date is not None:
        query = query.filter(Invoice.invoice_date <= end_date)

    total = query.count()

    invoices = (
        query.order_by(Invoice.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return InvoiceListResponse.build(
        items=invoices,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
)
def get_invoice(
    business_id: int,
    invoice_id: int,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    return get_invoice_or_404(
        business_id=business_id,
        invoice_id=invoice_id,
        db=db,
    )


@router.patch(
    "/{invoice_id}",
    response_model=InvoiceResponse,
)
def update_invoice(
    business_id: int,
    invoice_id: int,
    invoice_in: InvoiceUpdate,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(
        require_roles(
            BusinessRole.OWNER,
            BusinessRole.MANAGER,
            BusinessRole.STAFF,
        )
    ),
):
    invoice = get_invoice_or_404(
        business_id=business_id,
        invoice_id=invoice_id,
        db=db,
    )

    if invoice.status in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a paid or cancelled invoice.",
        )

    update_data = invoice_in.model_dump(exclude_unset=True)

    if "customer_id" in update_data and update_data["customer_id"] is not None:
        customer = (
            db.query(Customer)
            .filter(
                Customer.id == update_data["customer_id"],
                Customer.business_id == business_id,
            )
            .first()
        )
        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )
        if not customer.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign an inactive customer.",
            )

    for field, value in update_data.items():
        setattr(invoice, field, value)

    # Recalculate totals
    invoice.total = invoice.subtotal + invoice.tax - invoice.discount
    if invoice.total < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice total cannot be negative.",
        )

    try:
        db.commit()
        db.refresh(invoice)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while updating the invoice.",
        )

    return invoice


@router.patch(
    "/{invoice_id}/cancel",
    response_model=InvoiceResponse,
)
def cancel_invoice(
    business_id: int,
    invoice_id: int,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(
        require_roles(
            BusinessRole.OWNER,
            BusinessRole.MANAGER,
        )
    ),
):
    invoice = get_invoice_or_404(
        business_id=business_id,
        invoice_id=invoice_id,
        db=db,
    )

    if invoice.status == InvoiceStatus.CANCELLED:
        return invoice

    # If the invoice was PAID, we must restore the stock levels and create IN adjustments
    if invoice.status == InvoiceStatus.PAID:
        for item in invoice.items:
            product = (
                db.query(Product)
                .filter(
                    Product.id == item.product_id,
                    Product.business_id == business_id,
                )
                .first()
            )
            if product is not None:
                product.current_stock += item.quantity
                # Create IN stock adjustment
                adjustment = StockAdjustment(
                    business_id=business_id,
                    product_id=product.id,
                    adjustment_type="IN",
                    quantity=item.quantity,
                    reason=f"Cancelled Invoice {invoice.invoice_number}",
                    created_by=membership.user_id,
                )
                db.add(adjustment)

    invoice.status = InvoiceStatus.CANCELLED

    try:
        db.commit()
        db.refresh(invoice)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while cancelling the invoice.",
        )

    return invoice


# ---------------------------------------------------------------------------
# Invoice Items Sub-router Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/{invoice_id}/items",
    response_model=InvoiceItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_invoice_item(
    business_id: int,
    invoice_id: int,
    item_in: InvoiceItemCreate,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(
        require_roles(
            BusinessRole.OWNER,
            BusinessRole.MANAGER,
            BusinessRole.STAFF,
        )
    ),
):
    invoice = get_invoice_or_404(
        business_id=business_id,
        invoice_id=invoice_id,
        db=db,
    )

    if invoice.status not in (InvoiceStatus.DRAFT, InvoiceStatus.UNPAID):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add items to a paid, partially paid, or cancelled invoice.",
        )

    product = (
        db.query(Product)
        .filter(
            Product.id == item_in.product_id,
            Product.business_id == business_id,
        )
        .first()
    )
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product '{product.name}' is inactive.",
        )

    unit_price = (
        item_in.unit_price
        if item_in.unit_price is not None
        else product.selling_price
    )
    line_total = Decimal(str(item_in.quantity)) * unit_price

    invoice_item = InvoiceItem(
        invoice_id=invoice.id,
        product_id=product.id,
        quantity=item_in.quantity,
        unit_price=unit_price,
        line_total=line_total,
    )

    db.add(invoice_item)

    # Recalculate totals
    invoice.subtotal += line_total
    invoice.total = invoice.subtotal + invoice.tax - invoice.discount
    if invoice.total < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice total cannot be negative.",
        )

    try:
        db.commit()
        db.refresh(invoice_item)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while adding the invoice item.",
        )

    return invoice_item


@router.patch(
    "/{invoice_id}/items/{item_id}",
    response_model=InvoiceItemResponse,
)
def update_invoice_item(
    business_id: int,
    invoice_id: int,
    item_id: int,
    item_in: InvoiceItemUpdate,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(
        require_roles(
            BusinessRole.OWNER,
            BusinessRole.MANAGER,
            BusinessRole.STAFF,
        )
    ),
):
    invoice = get_invoice_or_404(
        business_id=business_id,
        invoice_id=invoice_id,
        db=db,
    )

    if invoice.status not in (InvoiceStatus.DRAFT, InvoiceStatus.UNPAID):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update items of a paid, partially paid, or cancelled invoice.",
        )

    item = (
        db.query(InvoiceItem)
        .filter(
            InvoiceItem.id == item_id,
            InvoiceItem.invoice_id == invoice.id,
        )
        .first()
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice item not found.",
        )

    old_line_total = item.line_total
    quantity = item_in.quantity if item_in.quantity is not None else item.quantity
    unit_price = (
        item_in.unit_price if item_in.unit_price is not None else item.unit_price
    )
    line_total = Decimal(str(quantity)) * unit_price

    item.quantity = quantity
    item.unit_price = unit_price
    item.line_total = line_total

    # Update invoice subtotal and total
    invoice.subtotal = invoice.subtotal - old_line_total + line_total
    invoice.total = invoice.subtotal + invoice.tax - invoice.discount
    if invoice.total < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice total cannot be negative.",
        )

    try:
        db.commit()
        db.refresh(item)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while updating the invoice item.",
        )

    return item


@router.delete(
    "/{invoice_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_invoice_item(
    business_id: int,
    invoice_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(
        require_roles(
            BusinessRole.OWNER,
            BusinessRole.MANAGER,
            BusinessRole.STAFF,
        )
    ),
):
    invoice = get_invoice_or_404(
        business_id=business_id,
        invoice_id=invoice_id,
        db=db,
    )

    if invoice.status not in (InvoiceStatus.DRAFT, InvoiceStatus.UNPAID):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete items of a paid, partially paid, or cancelled invoice.",
        )

    item = (
        db.query(InvoiceItem)
        .filter(
            InvoiceItem.id == item_id,
            InvoiceItem.invoice_id == invoice.id,
        )
        .first()
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice item not found.",
        )

    line_total = item.line_total
    db.delete(item)

    # Recalculate totals
    invoice.subtotal -= line_total
    invoice.total = invoice.subtotal + invoice.tax - invoice.discount
    if invoice.total < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice total cannot be negative.",
        )

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while deleting the invoice item.",
        )
