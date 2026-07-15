import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.products import (
    create_product,
    deactivate_product,
    get_product_or_404,
    get_low_stock_products,
    create_stock_adjustment,
    list_stock_adjustments,
)
from app.models.business_member import BusinessRole
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
    StockAdjustmentListResponse,
)


class TestProductCreateSchema:
    def test_valid_product_accepted(self):
        product = ProductCreate(
            name="Chocolate Cake",
            category="Bakery",
            sku="CAKE001",
            barcode="123456789",
            cost_price=Decimal("100.00"),
            selling_price=Decimal("150.00"),
            current_stock=10,
            minimum_stock=2,
            image_url="https://example.com/cake.jpg",
        )

        assert product.name == "Chocolate Cake"
        assert product.category == "Bakery"
        assert product.sku == "CAKE001"

    def test_name_whitespace_trimmed(self):
        product = ProductCreate(
            name="   Chocolate Cake   ",
            sku="CAKE001",
            cost_price=Decimal("100"),
            selling_price=Decimal("150"),
        )

        assert product.name == "Chocolate Cake"

    def test_whitespace_only_name_rejected(self):
        with pytest.raises(ValidationError):
            ProductCreate(
                name="   ",
                sku="CAKE001",
                cost_price=Decimal("100"),
                selling_price=Decimal("150"),
            )

    def test_name_at_100_chars_accepted(self):
        product = ProductCreate(
            name="A" * 100,
            sku="SKU100",
            cost_price=Decimal("1"),
            selling_price=Decimal("2"),
        )

        assert len(product.name) == 100

    def test_name_over_100_chars_rejected(self):
        with pytest.raises(ValidationError):
            ProductCreate(
                name="A" * 101,
                sku="SKU101",
                cost_price=Decimal("1"),
                selling_price=Decimal("2"),
            )

    def test_category_whitespace_becomes_none(self):
        product = ProductCreate(
            name="Milk",
            category="   ",
            sku="MILK001",
            cost_price=Decimal("20"),
            selling_price=Decimal("30"),
        )

        assert product.category is None
class TestProductUpdateSchema:
    def test_omitted_field_not_in_model_fields_set(self):
        update = ProductUpdate(name="Updated Product")

        assert "name" in update.model_fields_set
        assert "category" not in update.model_fields_set
        assert "sku" not in update.model_fields_set

    def test_explicit_null_is_in_model_fields_set(self):
        update = ProductUpdate(category=None)

        assert "category" in update.model_fields_set
        assert update.category is None

    def test_update_name_trimmed(self):
        update = ProductUpdate(name="  Updated Product  ")

        assert update.name == "Updated Product"

    def test_update_whitespace_name_rejected(self):
        with pytest.raises(ValidationError):
            ProductUpdate(name="   ")


class TestProductTenantIsolation:
    def test_product_lookup_filters_by_product_and_business(self):
        mock_db = MagicMock()
        mock_product = MagicMock(spec=Product)

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_product
        )

        result = get_product_or_404(
            business_id=10,
            product_id=20,
            db=mock_db,
        )

        assert result is mock_product

        filter_args = (
            mock_db.query.return_value
            .filter.call_args.args
        )

        assert len(filter_args) == 2

    def test_wrong_business_or_missing_product_raises_404(self):
        mock_db = MagicMock()

        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            get_product_or_404(
                business_id=999,
                product_id=20,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Product not found"


class TestProductPagination:
    def test_total_pages_calculation(self):
        response = ProductListResponse.build(
            items=[],
            total=45,
            page=1,
            page_size=20,
        )

        assert response.total_pages == 3

    def test_zero_total_has_zero_pages(self):
        response = ProductListResponse.build(
            items=[],
            total=0,
            page=1,
            page_size=20,
        )

        assert response.total_pages == 0


class TestProductCreationRollback:
    def test_rollback_called_on_commit_error(self):
        mock_db = MagicMock()
        mock_membership = MagicMock()
        mock_membership.role = BusinessRole.OWNER.value

        mock_db.commit.side_effect = SQLAlchemyError(
            "simulated database error"
        )

        product_in = ProductCreate(
            name="Rollback Product",
            sku="ROLL001",
            cost_price=Decimal("100"),
            selling_price=Decimal("150"),
        )

        with pytest.raises(HTTPException) as exc_info:
            create_product(
                business_id=1,
                product_in=product_in,
                db=mock_db,
                membership=mock_membership,
            )

        assert exc_info.value.status_code == 500
        mock_db.rollback.assert_called_once()


class TestProductDeactivation:
    def test_owner_can_deactivate_product_logic(self):
        mock_db = MagicMock()
        mock_membership = MagicMock()
        mock_membership.role = BusinessRole.OWNER.value

        mock_product = MagicMock(spec=Product)
        mock_product.is_active = True

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_product
        )

        result = deactivate_product(
            business_id=1,
            product_id=10,
            db=mock_db,
            membership=mock_membership,
        )

        assert result is mock_product
        assert mock_product.is_active is False
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_product)

    def test_rollback_called_on_deactivation_error(self):
        mock_db = MagicMock()
        mock_membership = MagicMock()
        mock_membership.role = BusinessRole.OWNER.value

        mock_product = MagicMock(spec=Product)
        mock_product.is_active = True

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_product
        )

        mock_db.commit.side_effect = SQLAlchemyError(
            "simulated database error"
        )

        with pytest.raises(HTTPException) as exc_info:
            deactivate_product(
                business_id=1,
                product_id=10,
                db=mock_db,
                membership=mock_membership,
            )

        assert exc_info.value.status_code == 500
        mock_db.rollback.assert_called_once()


class TestStockAdjustmentCreateSchema:
    def test_valid_in_adjustment_accepted(self):
        adj = StockAdjustmentCreate(
            adjustment_type="IN",
            quantity=10,
            reason="Supplier shipment",
        )
        assert adj.adjustment_type == "IN"
        assert adj.quantity == 10
        assert adj.reason == "Supplier shipment"

    def test_valid_out_adjustment_accepted(self):
        adj = StockAdjustmentCreate(
            adjustment_type="OUT",
            quantity=-5,
            reason="Customer sale",
        )
        assert adj.adjustment_type == "OUT"
        assert adj.quantity == -5

    def test_valid_adjustment_type_accepted(self):
        adj1 = StockAdjustmentCreate(adjustment_type="ADJUSTMENT", quantity=3)
        adj2 = StockAdjustmentCreate(adjustment_type="ADJUSTMENT", quantity=-2)
        assert adj1.quantity == 3
        assert adj2.quantity == -2

    def test_zero_quantity_rejected(self):
        with pytest.raises(ValidationError):
            StockAdjustmentCreate(adjustment_type="IN", quantity=0)

    def test_negative_quantity_for_in_rejected(self):
        with pytest.raises(ValidationError):
            StockAdjustmentCreate(adjustment_type="IN", quantity=-5)

    def test_positive_quantity_for_out_rejected(self):
        with pytest.raises(ValidationError):
            StockAdjustmentCreate(adjustment_type="OUT", quantity=5)

    def test_reason_whitespace_trimmed_and_stripped(self):
        adj = StockAdjustmentCreate(
            adjustment_type="IN",
            quantity=10,
            reason="   Lots of items   ",
        )
        assert adj.reason == "Lots of items"

        adj_empty = StockAdjustmentCreate(
            adjustment_type="IN",
            quantity=10,
            reason="   ",
        )
        assert adj_empty.reason is None


class TestProductLowStock:
    def test_low_stock_filters_and_paginates(self):
        mock_db = MagicMock()
        mock_membership = MagicMock()

        # Setup mock products
        mock_query = mock_db.query.return_value.filter.return_value
        mock_query.count.return_value = 1

        real_product = Product(
            id=1,
            business_id=1,
            name="Low Stock Product",
            category="Test",
            sku="LS001",
            barcode=None,
            cost_price=Decimal("10"),
            selling_price=Decimal("15"),
            current_stock=2,
            minimum_stock=5,
            image_url=None,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
            real_product
        ]

        result = get_low_stock_products(
            business_id=1,
            page=1,
            page_size=20,
            db=mock_db,
            membership=mock_membership,
        )

        assert isinstance(result, ProductListResponse)
        assert result.total == 1
        assert len(result.items) == 1


class TestStockAdjustmentCreation:
    def test_successful_stock_adjustment_adds_qty_to_current_stock(self):
        mock_db = MagicMock()
        mock_membership = MagicMock()
        mock_membership.user_id = 5

        mock_product = MagicMock(spec=Product)
        mock_product.is_active = True
        mock_product.current_stock = 15

        mock_db.query.return_value.filter.return_value.first.return_value = mock_product

        adj_in = StockAdjustmentCreate(
            adjustment_type="IN",
            quantity=5,
            reason="Stock count correction",
        )

        result = create_stock_adjustment(
            business_id=1,
            product_id=10,
            adjustment_in=adj_in,
            db=mock_db,
            membership=mock_membership,
        )

        assert result.adjustment_type == "IN"
        assert result.quantity == 5
        assert result.created_by == 5
        assert mock_product.current_stock == 20
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_adjust_stock_for_inactive_product_raises_400(self):
        mock_db = MagicMock()
        mock_membership = MagicMock()

        mock_product = MagicMock(spec=Product)
        mock_product.is_active = False

        mock_db.query.return_value.filter.return_value.first.return_value = mock_product

        adj_in = StockAdjustmentCreate(adjustment_type="IN", quantity=5)

        with pytest.raises(HTTPException) as exc_info:
            create_stock_adjustment(
                business_id=1,
                product_id=10,
                adjustment_in=adj_in,
                db=mock_db,
                membership=mock_membership,
            )

        assert exc_info.value.status_code == 400
        assert "inactive product" in exc_info.value.detail

    def test_insufficient_stock_for_adjustment_raises_400(self):
        mock_db = MagicMock()
        mock_membership = MagicMock()

        mock_product = MagicMock(spec=Product)
        mock_product.is_active = True
        mock_product.current_stock = 3

        mock_db.query.return_value.filter.return_value.first.return_value = mock_product

        adj_out = StockAdjustmentCreate(adjustment_type="OUT", quantity=-5)

        with pytest.raises(HTTPException) as exc_info:
            create_stock_adjustment(
                business_id=1,
                product_id=10,
                adjustment_in=adj_out,
                db=mock_db,
                membership=mock_membership,
            )

        assert exc_info.value.status_code == 400
        assert "Insufficient stock" in exc_info.value.detail

    def test_db_error_causes_rollback_on_stock_adjustment(self):
        mock_db = MagicMock()
        mock_membership = MagicMock()
        mock_membership.user_id = 5

        mock_product = MagicMock(spec=Product)
        mock_product.is_active = True
        mock_product.current_stock = 10

        mock_db.query.return_value.filter.return_value.first.return_value = mock_product
        mock_db.commit.side_effect = SQLAlchemyError("DB Error")

        adj_in = StockAdjustmentCreate(adjustment_type="IN", quantity=5)

        with pytest.raises(HTTPException) as exc_info:
            create_stock_adjustment(
                business_id=1,
                product_id=10,
                adjustment_in=adj_in,
                db=mock_db,
                membership=mock_membership,
            )

        assert exc_info.value.status_code == 500
        mock_db.rollback.assert_called_once()


class TestStockAdjustmentHistoryList:
    def test_list_stock_adjustments_returns_paginated_history(self):
        mock_db = MagicMock()
        mock_membership = MagicMock()

        # Product exists check
        mock_product = MagicMock(spec=Product)
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_product,  # get_product_or_404
        ]

        real_adj_1 = StockAdjustment(
            id=1,
            business_id=1,
            product_id=10,
            adjustment_type="IN",
            quantity=10,
            reason="Supplier delivery",
            created_by=5,
            created_at=datetime.now(),
        )
        real_adj_2 = StockAdjustment(
            id=2,
            business_id=1,
            product_id=10,
            adjustment_type="OUT",
            quantity=-2,
            reason="Customer sale",
            created_by=5,
            created_at=datetime.now(),
        )

        # StockAdjustment query mock
        mock_query = mock_db.query.return_value.filter.return_value
        mock_query.count.return_value = 2
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
            real_adj_1,
            real_adj_2,
        ]

        result = list_stock_adjustments(
            business_id=1,
            product_id=10,
            page=1,
            page_size=20,
            db=mock_db,
            membership=mock_membership,
        )

        assert isinstance(result, StockAdjustmentListResponse)
        assert result.total == 2
        assert len(result.items) == 2


@pytest.mark.skip(
    reason=(
        "BLOCKED: DB integration tests cannot run against the default "
        "Neon development database safely without an isolated PostgreSQL "
        "test environment."
    )
)
def test_db_integration_blocked():
    pass