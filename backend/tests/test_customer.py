import pytest
from unittest.mock import MagicMock

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes.customers import (
    create_customer,
    deactivate_customer,
    get_customer_or_404,
)
from app.models.business import Business
from app.models.business_member import BusinessRole
from app.models.customer import Customer
from app.schemas.customer import (
    CustomerCreate,
    CustomerListResponse,
    CustomerUpdate,
)


class TestCustomerCreateSchema:
    def test_valid_customer_accepted(self):
        customer = CustomerCreate(
            name="Alice Johnson",
            phone="9876543210",
            email="ALICE@EXAMPLE.COM",
        )

        assert customer.name == "Alice Johnson"
        assert customer.phone == "9876543210"
        assert str(customer.email) == "alice@example.com"

    def test_name_whitespace_trimmed(self):
        customer = CustomerCreate(name="  Alice Johnson  ")

        assert customer.name == "Alice Johnson"

    def test_whitespace_only_name_rejected(self):
        with pytest.raises(ValidationError):
            CustomerCreate(name="   ")

    def test_name_at_100_chars_accepted(self):
        customer = CustomerCreate(name="A" * 100)

        assert len(customer.name) == 100

    def test_name_over_100_chars_rejected(self):
        with pytest.raises(ValidationError):
            CustomerCreate(name="A" * 101)

    def test_empty_phone_becomes_none(self):
        customer = CustomerCreate(
            name="Alice",
            phone="   ",
        )

        assert customer.phone is None

    def test_phone_whitespace_trimmed(self):
        customer = CustomerCreate(
            name="Alice",
            phone="  9876543210  ",
        )

        assert customer.phone == "9876543210"

    def test_empty_email_becomes_none(self):
        customer = CustomerCreate(
            name="Alice",
            email="   ",
        )

        assert customer.email is None

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            CustomerCreate(
                name="Alice",
                email="not-an-email",
            )


class TestCustomerUpdateSchema:
    def test_omitted_field_not_in_model_fields_set(self):
        update = CustomerUpdate(name="Updated Name")

        assert "name" in update.model_fields_set
        assert "phone" not in update.model_fields_set
        assert "email" not in update.model_fields_set

    def test_explicit_null_is_in_model_fields_set(self):
        update = CustomerUpdate(phone=None)

        assert "phone" in update.model_fields_set
        assert update.phone is None

    def test_update_name_trimmed(self):
        update = CustomerUpdate(name="  Updated Name  ")

        assert update.name == "Updated Name"

    def test_update_whitespace_name_rejected(self):
        with pytest.raises(ValidationError):
            CustomerUpdate(name="   ")


class TestCustomerTenantIsolation:
    def test_customer_lookup_filters_by_customer_and_business(self):
        mock_db = MagicMock()
        mock_customer = MagicMock(spec=Customer)

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_customer
        )

        result = get_customer_or_404(
            business_id=10,
            customer_id=20,
            db=mock_db,
        )

        assert result is mock_customer

        filter_args = (
            mock_db.query.return_value
            .filter.call_args.args
        )

        assert len(filter_args) == 2

    def test_wrong_business_or_missing_customer_raises_404(self):
        mock_db = MagicMock()

        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            get_customer_or_404(
                business_id=999,
                customer_id=20,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Customer not found"


class TestCustomerPagination:
    def test_total_pages_calculation(self):
        response = CustomerListResponse.build(
            items=[],
            total=45,
            page=1,
            page_size=20,
        )

        assert response.total_pages == 3

    def test_zero_total_has_zero_pages(self):
        response = CustomerListResponse.build(
            items=[],
            total=0,
            page=1,
            page_size=20,
        )

        assert response.total_pages == 0


class TestCustomerCreationRollback:
    def test_rollback_called_on_commit_error(self):
        mock_db = MagicMock()
        mock_membership = MagicMock()
        mock_membership.role = BusinessRole.OWNER.value

        mock_db.commit.side_effect = SQLAlchemyError(
            "simulated database error"
        )

        customer_in = CustomerCreate(
            name="Rollback Customer"
        )

        with pytest.raises(HTTPException) as exc_info:
            create_customer(
                business_id=1,
                customer_in=customer_in,
                db=mock_db,
                membership=mock_membership,
            )

        assert exc_info.value.status_code == 500
        mock_db.rollback.assert_called_once()


class TestCustomerDeactivation:
    def test_owner_can_deactivate_customer_logic(self):
        mock_db = MagicMock()
        mock_membership = MagicMock()
        mock_membership.role = BusinessRole.OWNER.value

        mock_customer = MagicMock(spec=Customer)
        mock_customer.is_active = True

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_customer
        )

        result = deactivate_customer(
            business_id=1,
            customer_id=10,
            db=mock_db,
            membership=mock_membership,
        )

        assert result is mock_customer
        assert mock_customer.is_active is False
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_customer)

    def test_rollback_called_on_deactivation_error(self):
        mock_db = MagicMock()
        mock_membership = MagicMock()
        mock_membership.role = BusinessRole.OWNER.value

        mock_customer = MagicMock(spec=Customer)
        mock_customer.is_active = True

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_customer
        )

        mock_db.commit.side_effect = SQLAlchemyError(
            "simulated database error"
        )

        with pytest.raises(HTTPException) as exc_info:
            deactivate_customer(
                business_id=1,
                customer_id=10,
                db=mock_db,
                membership=mock_membership,
            )

        assert exc_info.value.status_code == 500
        mock_db.rollback.assert_called_once()


@pytest.mark.skip(
    reason=(
        "BLOCKED: DB integration tests cannot run against the default "
        "Neon development database safely without an isolated PostgreSQL "
        "test environment."
    )
)
def test_db_integration_blocked():
    pass