import pytest
from unittest.mock import MagicMock, call
from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.invoices import (
    create_invoice,
    list_invoices,
    get_invoice,
    update_invoice,
    cancel_invoice,
    add_invoice_item,
    update_invoice_item,
    delete_invoice_item,
    get_invoice_or_404,
)
from app.models.business_member import BusinessRole
from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_item import InvoiceItem
from app.models.customer import Customer
from app.models.product import Product
from app.models.stock_adjustment import StockAdjustment
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceListResponse,
)
from app.schemas.invoice_item import (
    InvoiceItemCreate,
    InvoiceItemUpdate,
)


class TestInvoiceCreateSchema:
    def test_valid_invoice_create(self):
        item = InvoiceItemCreate(product_id=1, quantity=2, unit_price=Decimal("10.00"))
        invoice = InvoiceCreate(
            customer_id=5,
            tax=Decimal("1.50"),
            discount=Decimal("2.00"),
            notes="  Test Note  ",
            invoice_date=date(2026, 7, 15),
            due_date=date(2026, 8, 15),
            items=[item],
        )
        assert invoice.customer_id == 5
        assert invoice.tax == Decimal("1.50")
        assert invoice.discount == Decimal("2.00")
        assert invoice.notes == "Test Note"
        assert invoice.invoice_date == date(2026, 7, 15)
        assert invoice.due_date == date(2026, 8, 15)
        assert len(invoice.items) == 1

    def test_negative_tax_discount_rejected(self):
        with pytest.raises(ValidationError):
            InvoiceCreate(customer_id=1, tax=Decimal("-1.00"), items=[])
        with pytest.raises(ValidationError):
            InvoiceCreate(customer_id=1, discount=Decimal("-1.00"), items=[])

    def test_negative_quantity_rejected(self):
        with pytest.raises(ValidationError):
            InvoiceItemCreate(product_id=1, quantity=0)
        with pytest.raises(ValidationError):
            InvoiceItemCreate(product_id=1, quantity=-5)


class TestInvoiceUpdateSchema:
    def test_valid_invoice_update(self):
        update = InvoiceUpdate(
            tax=Decimal("5.00"),
            discount=Decimal("1.00"),
            notes="Updated notes",
        )
        assert update.tax == Decimal("5.00")
        assert update.discount == Decimal("1.00")
        assert update.notes == "Updated notes"

    def test_negative_tax_discount_rejected(self):
        with pytest.raises(ValidationError):
            InvoiceUpdate(tax=Decimal("-5.00"))


class TestInvoiceCalculationsAndCreation:
    def test_create_invoice_success(self):
        mock_db = MagicMock()
        mock_membership = MagicMock()
        mock_membership.role = BusinessRole.STAFF.value
        mock_membership.user_id = 12

        # Mock customer query
        mock_customer = MagicMock(spec=Customer)
        mock_customer.id = 5
        mock_customer.is_active = True
        mock_customer.business_id = 1

        # Mock product query
        mock_product = MagicMock(spec=Product)
        mock_product.id = 2
        mock_product.selling_price = Decimal("25.00")
        mock_product.is_active = True
        mock_product.business_id = 1

        # Mock db queries
        def db_query_side_effect(model):
            mock_query = MagicMock()
            if model == Customer:
                mock_query.filter.return_value.first.return_value = mock_customer
            elif model == Product:
                mock_query.filter.return_value.first.return_value = mock_product
            return mock_query

        mock_db.query.side_effect = db_query_side_effect

        invoice_in = InvoiceCreate(
            customer_id=5,
            tax=Decimal("5.00"),
            discount=Decimal("10.00"),
            items=[
                InvoiceItemCreate(product_id=2, quantity=3, unit_price=None)  # Use product selling_price
            ],
        )

        result = create_invoice(
            business_id=1,
            invoice_in=invoice_in,
            db=mock_db,
            membership=mock_membership,
        )

        assert result.subtotal == Decimal("75.00")
        assert result.tax == Decimal("5.00")
        assert result.discount == Decimal("10.00")
        assert result.total == Decimal("70.00")
        assert result.status == InvoiceStatus.UNPAID
        assert result.items[0].unit_price == Decimal("25.00")
        assert result.items[0].line_total == Decimal("75.00")
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_invoice_inactive_customer_raises_400(self):
        mock_db = MagicMock()
        mock_customer = MagicMock(spec=Customer)
        mock_customer.is_active = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_customer

        invoice_in = InvoiceCreate(
            customer_id=5,
            items=[InvoiceItemCreate(product_id=2, quantity=1)]
        )

        with pytest.raises(HTTPException) as exc_info:
            create_invoice(
                business_id=1,
                invoice_in=invoice_in,
                db=mock_db,
                membership=MagicMock(),
            )
        assert exc_info.value.status_code == 400
        assert "inactive customer" in exc_info.value.detail

    def test_create_invoice_negative_total_raises_400(self):
        mock_db = MagicMock()
        mock_customer = MagicMock(spec=Customer)
        mock_customer.is_active = True
        mock_product = MagicMock(spec=Product)
        mock_product.selling_price = Decimal("5.00")
        mock_product.is_active = True

        def db_query_side_effect(model):
            mock_query = MagicMock()
            if model == Customer:
                mock_query.filter.return_value.first.return_value = mock_customer
            elif model == Product:
                mock_query.filter.return_value.first.return_value = mock_product
            return mock_query

        mock_db.query.side_effect = db_query_side_effect

        invoice_in = InvoiceCreate(
            customer_id=5,
            tax=Decimal("0.00"),
            discount=Decimal("20.00"),  # total = 5 + 0 - 20 = -15
            items=[InvoiceItemCreate(product_id=2, quantity=1, unit_price=None)]
        )

        with pytest.raises(HTTPException) as exc_info:
            create_invoice(
                business_id=1,
                invoice_in=invoice_in,
                db=mock_db,
                membership=MagicMock(),
            )
        assert exc_info.value.status_code == 400
        assert "negative" in exc_info.value.detail


class TestInvoiceTenantIsolation:
    def test_get_invoice_or_404_success(self):
        mock_db = MagicMock()
        mock_invoice = MagicMock(spec=Invoice)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_invoice

        res = get_invoice_or_404(business_id=1, invoice_id=10, db=mock_db)
        assert res is mock_invoice

    def test_get_invoice_or_404_not_found(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            get_invoice_or_404(business_id=1, invoice_id=10, db=mock_db)
        assert exc_info.value.status_code == 404


class TestInvoicePagination:
    def test_build_total_pages(self):
        res = InvoiceListResponse.build(items=[], total=25, page=1, page_size=10)
        assert res.total_pages == 3


class TestInvoiceCreationRollback:
    def test_rollback_on_commit_error(self):
        mock_db = MagicMock()
        mock_customer = MagicMock(spec=Customer)
        mock_customer.is_active = True
        mock_product = MagicMock(spec=Product)
        mock_product.selling_price = Decimal("10.00")
        mock_product.is_active = True

        def db_query_side_effect(model):
            mock_query = MagicMock()
            if model == Customer:
                mock_query.filter.return_value.first.return_value = mock_customer
            elif model == Product:
                mock_query.filter.return_value.first.return_value = mock_product
            return mock_query

        mock_db.query.side_effect = db_query_side_effect
        mock_db.commit.side_effect = SQLAlchemyError("DB Error")

        invoice_in = InvoiceCreate(
            customer_id=5,
            items=[InvoiceItemCreate(product_id=2, quantity=1)]
        )

        with pytest.raises(HTTPException) as exc_info:
            create_invoice(
                business_id=1,
                invoice_in=invoice_in,
                db=mock_db,
                membership=MagicMock(),
            )
        assert exc_info.value.status_code == 500
        mock_db.rollback.assert_called_once()


class TestInvoiceCancellation:
    def test_cancel_paid_invoice_restores_stock(self):
        mock_db = MagicMock()
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.status = InvoiceStatus.PAID
        mock_invoice.invoice_number = "INV-1001"

        mock_item = MagicMock(spec=InvoiceItem)
        mock_item.product_id = 4
        mock_item.quantity = 5
        mock_invoice.items = [mock_item]

        mock_product = MagicMock(spec=Product)
        mock_product.id = 4
        mock_product.current_stock = 10

        # Mock fetching invoice and product
        def db_query_side_effect(model):
            mock_query = MagicMock()
            if model == Invoice:
                mock_query.filter.return_value.first.return_value = mock_invoice
            elif model == Product:
                mock_query.filter.return_value.first.return_value = mock_product
            return mock_query

        mock_db.query.side_effect = db_query_side_effect

        mock_membership = MagicMock()
        mock_membership.role = BusinessRole.MANAGER.value
        mock_membership.user_id = 9

        result = cancel_invoice(
            business_id=1,
            invoice_id=10,
            db=mock_db,
            membership=mock_membership,
        )

        assert result.status == InvoiceStatus.CANCELLED
        assert mock_product.current_stock == 15  # 10 + 5 restored
        mock_db.add.assert_called_once()  # For StockAdjustment
        added_adj = mock_db.add.call_args[0][0]
        assert isinstance(added_adj, StockAdjustment)
        assert added_adj.adjustment_type == "IN"
        assert added_adj.quantity == 5
        mock_db.commit.assert_called_once()


class TestInvoiceItemSubRoutes:
    def test_add_invoice_item_recalculates_totals(self):
        mock_db = MagicMock()
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.status = InvoiceStatus.UNPAID
        mock_invoice.subtotal = Decimal("50.00")
        mock_invoice.tax = Decimal("5.00")
        mock_invoice.discount = Decimal("10.00")

        mock_product = MagicMock(spec=Product)
        mock_product.selling_price = Decimal("20.00")
        mock_product.is_active = True

        def db_query_side_effect(model):
            mock_query = MagicMock()
            if model == Invoice:
                mock_query.filter.return_value.first.return_value = mock_invoice
            elif model == Product:
                mock_query.filter.return_value.first.return_value = mock_product
            return mock_query

        mock_db.query.side_effect = db_query_side_effect

        item_in = InvoiceItemCreate(product_id=2, quantity=2, unit_price=Decimal("15.00"))

        add_invoice_item(
            business_id=1,
            invoice_id=10,
            item_in=item_in,
            db=mock_db,
            membership=MagicMock(),
        )

        assert mock_invoice.subtotal == Decimal("80.00")  # 50 + 2*15
        assert mock_invoice.total == Decimal("75.00")  # 80 + 5 - 10
        mock_db.commit.assert_called_once()

    def test_add_item_to_paid_invoice_raises_400(self):
        mock_db = MagicMock()
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.status = InvoiceStatus.PAID
        mock_db.query.return_value.filter.return_value.first.return_value = mock_invoice

        with pytest.raises(HTTPException) as exc_info:
            add_invoice_item(
                business_id=1,
                invoice_id=10,
                item_in=InvoiceItemCreate(product_id=2, quantity=1),
                db=mock_db,
                membership=MagicMock(),
            )
        assert exc_info.value.status_code == 400
