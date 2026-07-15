import pytest
from unittest.mock import MagicMock, call
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.payments import (
    create_payment,
    list_invoice_payments,
    list_all_payments,
)
from app.models.business_member import BusinessRole
from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_item import InvoiceItem
from app.models.payment import Payment, PaymentMethod
from app.models.product import Product
from app.models.stock_adjustment import StockAdjustment
from app.schemas.payment import PaymentCreate, PaymentListResponse


class TestPaymentCreateSchema:
    def test_valid_payment_create(self):
        payment = PaymentCreate(
            amount=Decimal("150.00"),
            payment_method=PaymentMethod.UPI,
            reference="  REF123456  ",
        )
        assert payment.amount == Decimal("150.00")
        assert payment.payment_method == PaymentMethod.UPI
        assert payment.reference == "REF123456"

    def test_zero_or_negative_amount_rejected(self):
        with pytest.raises(ValidationError):
            PaymentCreate(amount=Decimal("0.00"), payment_method=PaymentMethod.CASH)
        with pytest.raises(ValidationError):
            PaymentCreate(amount=Decimal("-10.00"), payment_method=PaymentMethod.CASH)


class TestPaymentCreation:
    def test_partial_payment_does_not_deduct_stock(self):
        mock_db = MagicMock()
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.id = 10
        mock_invoice.total = Decimal("100.00")
        mock_invoice.status = InvoiceStatus.UNPAID
        mock_invoice.invoice_number = "INV-123"

        # Mock database query routes
        def db_query_side_effect(model):
            mock_query = MagicMock()
            if model == Invoice:
                mock_query.filter.return_value.first.return_value = mock_invoice
            elif model == Payment:
                # Prior payments sum to empty list
                mock_query.filter.return_value.with_entities.return_value.all.return_value = []
                # Duplicate check returns None
                mock_query.filter.return_value.first.return_value = None
            return mock_query

        mock_db.query.side_effect = db_query_side_effect

        mock_membership = MagicMock()
        mock_membership.role = BusinessRole.STAFF.value
        mock_membership.user_id = 5

        payment_in = PaymentCreate(
            amount=Decimal("40.00"),
            payment_method=PaymentMethod.CASH,
        )

        result = create_payment(
            business_id=1,
            invoice_id=10,
            payment_in=payment_in,
            db=mock_db,
            membership=mock_membership,
        )

        assert mock_invoice.status == InvoiceStatus.PARTIALLY_PAID
        assert result.amount == Decimal("40.00")
        # Ensure stock reduction was NOT called
        mock_db.commit.assert_called_once()

    def test_full_payment_deducts_stock_and_creates_stock_adjustments(self):
        mock_db = MagicMock()
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.id = 10
        mock_invoice.total = Decimal("100.00")
        mock_invoice.status = InvoiceStatus.PARTIALLY_PAID
        mock_invoice.invoice_number = "INV-123"

        # Prior payments sum to 60.00
        prior_payment = MagicMock()
        prior_payment.amount = Decimal("60.00")
        
        # Mock items
        mock_item = MagicMock(spec=InvoiceItem)
        mock_item.product_id = 3
        mock_item.quantity = 2
        mock_invoice.items = [mock_item]

        # Mock product
        mock_product = MagicMock(spec=Product)
        mock_product.id = 3
        mock_product.current_stock = 10
        mock_product.is_active = True

        # Mock database query routes
        def db_query_side_effect(model):
            mock_query = MagicMock()
            if model == Invoice:
                mock_query.filter.return_value.first.return_value = mock_invoice
            elif model == Payment:
                # Prior payments sum
                mock_query.filter.return_value.with_entities.return_value.all.return_value = [prior_payment]
                # Duplicate check
                mock_query.filter.return_value.first.return_value = None
            elif model == Product:
                mock_query.filter.return_value.first.return_value = mock_product
            return mock_query

        mock_db.query.side_effect = db_query_side_effect

        mock_membership = MagicMock()
        mock_membership.role = BusinessRole.STAFF.value
        mock_membership.user_id = 5

        payment_in = PaymentCreate(
            amount=Decimal("40.00"),
            payment_method=PaymentMethod.CARD,
        )

        result = create_payment(
            business_id=1,
            invoice_id=10,
            payment_in=payment_in,
            db=mock_db,
            membership=mock_membership,
        )

        assert mock_invoice.status == InvoiceStatus.PAID
        assert mock_product.current_stock == 8  # 10 - 2 reduced
        
        # Check stock adjustment was logged
        added_objs = [call_arg[0][0] for call_arg in mock_db.add.call_args_list]
        adjustments = [obj for obj in added_objs if isinstance(obj, StockAdjustment)]
        assert len(adjustments) == 1
        assert adjustments[0].adjustment_type == "OUT"
        assert adjustments[0].quantity == -2
        assert adjustments[0].product_id == 3

        mock_db.commit.assert_called_once()

    def test_overpayment_raises_400(self):
        mock_db = MagicMock()
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.total = Decimal("100.00")
        mock_invoice.status = InvoiceStatus.UNPAID

        # Mock queries
        def db_query_side_effect(model):
            mock_query = MagicMock()
            if model == Invoice:
                mock_query.filter.return_value.first.return_value = mock_invoice
            elif model == Payment:
                # Prior payments sum
                mock_query.filter.return_value.with_entities.return_value.all.return_value = []
                # Duplicate check
                mock_query.filter.return_value.first.return_value = None
            return mock_query

        mock_db.query.side_effect = db_query_side_effect

        payment_in = PaymentCreate(
            amount=Decimal("120.00"),  # > 100.00
            payment_method=PaymentMethod.CASH,
        )

        with pytest.raises(HTTPException) as exc_info:
            create_payment(
                business_id=1,
                invoice_id=10,
                payment_in=payment_in,
                db=mock_db,
                membership=MagicMock(),
            )
        assert exc_info.value.status_code == 400
        assert "exceeds" in exc_info.value.detail

    def test_payment_on_cancelled_invoice_raises_400(self):
        mock_db = MagicMock()
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.status = InvoiceStatus.CANCELLED

        mock_db.query.return_value.filter.return_value.first.return_value = mock_invoice

        payment_in = PaymentCreate(amount=Decimal("10.00"), payment_method=PaymentMethod.CASH)

        with pytest.raises(HTTPException) as exc_info:
            create_payment(
                business_id=1,
                invoice_id=10,
                payment_in=payment_in,
                db=mock_db,
                membership=MagicMock(),
            )
        assert exc_info.value.status_code == 400
        assert "cancelled" in exc_info.value.detail

    def test_duplicate_payment_prevention_raises_400(self):
        mock_db = MagicMock()
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.total = Decimal("100.00")
        mock_invoice.status = InvoiceStatus.UNPAID

        # Mock duplicate check (returns a duplicate payment object)
        mock_duplicate = MagicMock(spec=Payment)
        
        def db_query_side_effect(model):
            mock_query = MagicMock()
            if model == Invoice:
                mock_query.filter.return_value.first.return_value = mock_invoice
            elif model == Payment:
                # Prior payments sum
                mock_query.filter.return_value.with_entities.return_value.all.return_value = []
                # Duplicate check returns mock_duplicate
                mock_query.filter.return_value.first.return_value = mock_duplicate
            return mock_query

        mock_db.query.side_effect = db_query_side_effect

        payment_in = PaymentCreate(amount=Decimal("10.00"), payment_method=PaymentMethod.CASH)

        with pytest.raises(HTTPException) as exc_info:
            create_payment(
                business_id=1,
                invoice_id=10,
                payment_in=payment_in,
                db=mock_db,
                membership=MagicMock(),
            )
        assert exc_info.value.status_code == 400
        assert "Duplicate payment detected" in exc_info.value.detail


class TestPaymentRollback:
    def test_rollback_on_commit_error(self):
        mock_db = MagicMock()
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.total = Decimal("100.00")
        mock_invoice.status = InvoiceStatus.UNPAID

        def db_query_side_effect(model):
            mock_query = MagicMock()
            if model == Invoice:
                mock_query.filter.return_value.first.return_value = mock_invoice
            elif model == Payment:
                # Prior payments sum
                mock_query.filter.return_value.with_entities.return_value.all.return_value = []
                # Duplicate check returns None
                mock_query.filter.return_value.first.return_value = None
            return mock_query

        mock_db.query.side_effect = db_query_side_effect
        mock_db.commit.side_effect = SQLAlchemyError("DB Commit Error")

        payment_in = PaymentCreate(amount=Decimal("10.00"), payment_method=PaymentMethod.CASH)

        with pytest.raises(HTTPException) as exc_info:
            create_payment(
                business_id=1,
                invoice_id=10,
                payment_in=payment_in,
                db=mock_db,
                membership=MagicMock(),
            )
        assert exc_info.value.status_code == 500
        mock_db.rollback.assert_called_once()
