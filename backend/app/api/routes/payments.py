from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership, require_roles
from app.db.dependencies import get_db
from app.models.business_member import BusinessMember, BusinessRole
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentMethod
from app.models.product import Product
from app.models.stock_adjustment import StockAdjustment
from app.schemas.payment import (
    PaymentCreate,
    PaymentListResponse,
    PaymentResponse,
)

router = APIRouter()


@router.post(
    "/invoices/{invoice_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    business_id: int,
    invoice_id: int,
    payment_in: PaymentCreate,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(
        require_roles(
            BusinessRole.OWNER,
            BusinessRole.MANAGER,
            BusinessRole.STAFF,
        )
    ),
):
    # Fetch invoice
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

    # Reject cancelled invoices
    if invoice.status == InvoiceStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record payments for a cancelled invoice.",
        )

    # Reject already paid invoices
    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is already fully paid.",
        )

    # Calculate total of all previous payments
    prior_payments_sum = (
        db.query(Payment)
        .filter(Payment.invoice_id == invoice.id)
        .with_entities(Payment.amount)
        .all()
    )
    total_paid_so_far = sum(p.amount for p in prior_payments_sum)
    outstanding_balance = invoice.total - total_paid_so_far

    # Reject overpayment
    if payment_in.amount > outstanding_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment amount exceeds the outstanding balance of {outstanding_balance}.",
        )

    # Duplicate payment prevention (check within last 10 seconds)
    time_limit = datetime.utcnow() - timedelta(seconds=10)
    duplicate = db.query(Payment).filter(
        Payment.invoice_id == invoice.id,
        Payment.amount == payment_in.amount,
        Payment.payment_method == payment_in.payment_method,
        Payment.paid_at >= time_limit,
        Payment.reference == payment_in.reference,
    ).first()

    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate payment detected. Please wait before submitting again.",
        )

    # Add Payment
    payment = Payment(
        business_id=business_id,
        invoice_id=invoice.id,
        amount=payment_in.amount,
        payment_method=payment_in.payment_method,
        reference=payment_in.reference,
    )
    db.add(payment)

    # Calculate new status
    new_total_paid = total_paid_so_far + payment_in.amount
    if new_total_paid == invoice.total:
        invoice.status = InvoiceStatus.PAID

        # Reduce stock and create OUT StockAdjustment
        for item in invoice.items:
            product = (
                db.query(Product)
                .filter(
                    Product.id == item.product_id,
                    Product.business_id == business_id,
                )
                .first()
            )
            if product is None:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with ID {item.product_id} not found.",
                )
            if not product.is_active:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product '{product.name}' is inactive.",
                )
            if product.current_stock < item.quantity:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for product '{product.name}'.",
                )

            # Reduce stock
            product.current_stock -= item.quantity

            # Log OUT StockAdjustment
            adjustment = StockAdjustment(
                business_id=business_id,
                product_id=product.id,
                adjustment_type="OUT",
                quantity=-item.quantity,
                reason=f"Invoice {invoice.invoice_number} Payment",
                created_by=membership.user_id,
            )
            db.add(adjustment)
    else:
        invoice.status = InvoiceStatus.PARTIALLY_PAID

    try:
        db.commit()
        db.refresh(payment)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while creating the payment.",
        )

    return payment


@router.get(
    "/invoices/{invoice_id}/payments",
    response_model=list[PaymentResponse],
)
def list_invoice_payments(
    business_id: int,
    invoice_id: int,
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    # Ensure invoice exists
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

    payments = (
        db.query(Payment)
        .filter(
            Payment.invoice_id == invoice_id,
            Payment.business_id == business_id,
        )
        .order_by(Payment.paid_at.desc(), Payment.id.desc())
        .all()
    )

    return payments


@router.get(
    "/payments",
    response_model=PaymentListResponse,
)
def list_all_payments(
    business_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    membership: BusinessMember = Depends(get_current_membership),
):
    query = db.query(Payment).filter(Payment.business_id == business_id)

    total = query.count()

    payments = (
        query.order_by(Payment.paid_at.desc(), Payment.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaymentListResponse.build(
        items=payments,
        total=total,
        page=page,
        page_size=page_size,
    )
