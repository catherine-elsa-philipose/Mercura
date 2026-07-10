"""
Phase 4 isolated tests.

All tests are non-destructive and do not connect to or mutate the Neon database.
DB integration tests remain skipped until an isolated PostgreSQL test environment exists.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.schemas.business import BusinessCreate
from app.models.business_member import BusinessRole, BusinessMember
from app.api.deps import get_current_membership, require_roles


# ---------------------------------------------------------------------------
# BusinessCreate schema tests
# ---------------------------------------------------------------------------

class TestBusinessCreateSchema:

    def test_valid_name_accepted(self):
        b = BusinessCreate(name="Fresh Mart")
        assert b.name == "Fresh Mart"

    def test_leading_trailing_whitespace_trimmed(self):
        b = BusinessCreate(name="   Fresh Mart   ")
        assert b.name == "Fresh Mart"

    def test_whitespace_only_name_rejected(self):
        with pytest.raises(ValueError):
            BusinessCreate(name="     ")

    def test_empty_string_rejected(self):
        with pytest.raises(ValueError):
            BusinessCreate(name="")

    def test_name_at_exactly_100_chars_accepted(self):
        name = "A" * 100
        b = BusinessCreate(name=name)
        assert len(b.name) == 100

    def test_name_over_100_chars_rejected(self):
        with pytest.raises(ValueError):
            BusinessCreate(name="A" * 101)

    def test_trimmed_name_at_100_chars_accepted(self):
        # raw input is 104 chars but trimmed result is exactly 100 — must pass
        b = BusinessCreate(name="  " + "A" * 100 + "  ")
        assert len(b.name) == 100

    def test_trimmed_name_over_100_chars_rejected(self):
        # raw input is padded with spaces, trimmed result is 101 chars — must fail
        with pytest.raises(ValueError):
            BusinessCreate(name="  " + "A" * 101 + "  ")


# ---------------------------------------------------------------------------
# BusinessRole enum tests
# ---------------------------------------------------------------------------

class TestBusinessRole:

    def test_owner_value(self):
        assert BusinessRole.OWNER.value == "OWNER"

    def test_manager_value(self):
        assert BusinessRole.MANAGER.value == "MANAGER"

    def test_staff_value(self):
        assert BusinessRole.STAFF.value == "STAFF"

    def test_role_is_string_enum(self):
        assert isinstance(BusinessRole.OWNER, str)

    def test_invalid_role_not_in_enum(self):
        with pytest.raises(ValueError):
            BusinessRole("ADMIN")

    def test_invalid_role_superuser_not_in_enum(self):
        with pytest.raises(ValueError):
            BusinessRole("SUPERUSER")


# ---------------------------------------------------------------------------
# get_current_membership dependency tests (no DB)
# ---------------------------------------------------------------------------

class TestGetCurrentMembership:

    def _make_mock_membership(self, business_id: int, user_id: int, role: str) -> MagicMock:
        m = MagicMock(spec=BusinessMember)
        m.business_id = business_id
        m.user_id = user_id
        m.role = role
        return m

    def test_membership_found_returns_membership(self):
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_membership = self._make_mock_membership(10, 1, BusinessRole.OWNER.value)

        # chain: db.query(...).filter(...).first()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_membership

        result = get_current_membership(business_id=10, db=mock_db, current_user=mock_user)
        assert result is mock_membership

    def test_no_membership_raises_404(self):
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1

        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            get_current_membership(business_id=99, db=mock_db, current_user=mock_user)
        assert exc_info.value.status_code == 404
        assert "Business not found" in exc_info.value.detail


# ---------------------------------------------------------------------------
# require_roles dependency tests (no DB)
# ---------------------------------------------------------------------------

class TestRequireRoles:

    def _make_mock_membership(self, role: str) -> MagicMock:
        m = MagicMock(spec=BusinessMember)
        m.role = role
        return m

    def test_owner_allowed_when_owner_required(self):
        mock_membership = self._make_mock_membership(BusinessRole.OWNER.value)
        dep_fn = require_roles(BusinessRole.OWNER)
        result = dep_fn(membership=mock_membership)
        assert result is mock_membership

    def test_manager_allowed_when_manager_required(self):
        mock_membership = self._make_mock_membership(BusinessRole.MANAGER.value)
        dep_fn = require_roles(BusinessRole.MANAGER)
        result = dep_fn(membership=mock_membership)
        assert result is mock_membership

    def test_staff_allowed_when_owner_or_staff_required(self):
        mock_membership = self._make_mock_membership(BusinessRole.STAFF.value)
        dep_fn = require_roles(BusinessRole.OWNER, BusinessRole.STAFF)
        result = dep_fn(membership=mock_membership)
        assert result is mock_membership

    def test_staff_denied_when_only_owner_required(self):
        mock_membership = self._make_mock_membership(BusinessRole.STAFF.value)
        dep_fn = require_roles(BusinessRole.OWNER)
        with pytest.raises(HTTPException) as exc_info:
            dep_fn(membership=mock_membership)
        assert exc_info.value.status_code == 403
        assert "Permission denied" in exc_info.value.detail

    def test_manager_denied_when_only_staff_required(self):
        mock_membership = self._make_mock_membership(BusinessRole.MANAGER.value)
        dep_fn = require_roles(BusinessRole.STAFF)
        with pytest.raises(HTTPException) as exc_info:
            dep_fn(membership=mock_membership)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Business creation transaction rollback test (application logic only)
# ---------------------------------------------------------------------------

class TestBusinessCreationRollback:
    """
    Tests that application-level rollback is invoked when a database error occurs
    during business creation.

    NOTE: This test validates that the application calls db.rollback() on
    SQLAlchemyError. It does NOT test PostgreSQL ACID rollback semantics —
    that would require a real database and integration-level testing.
    """

    def test_rollback_called_on_sqlalchemy_error(self):
        from sqlalchemy.exc import SQLAlchemyError
        from app.api.routes.businesses import create_business
        from app.schemas.business import BusinessCreate

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1

        # Simulate flush raising a database error
        mock_db.flush.side_effect = SQLAlchemyError("simulated db error")

        business_in = BusinessCreate(name="Test Business")

        with pytest.raises(HTTPException) as exc_info:
            create_business(business_in=business_in, db=mock_db, current_user=mock_user)

        mock_db.rollback.assert_called_once()
        assert exc_info.value.status_code == 500

    def test_creator_role_is_owner(self):
        """
        Verify that the creation logic assigns OWNER role to the creator.
        Inspects the BusinessMember call args without DB mutation.
        """
        from app.models.business_member import BusinessRole
        from app.api.routes.businesses import create_business
        from app.schemas.business import BusinessCreate

        created_members = []

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 42

        # Simulate flush successfully setting the id
        def fake_flush():
            mock_db.add.call_args_list[0][0][0].id = 99

        mock_db.flush.side_effect = fake_flush

        original_add = mock_db.add

        def capture_add(obj):
            if isinstance(obj, BusinessMember):
                created_members.append(obj)

        mock_db.add.side_effect = capture_add
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        business_in = BusinessCreate(name="Owner Test Business")
        create_business(business_in=business_in, db=mock_db, current_user=mock_user)

        assert len(created_members) == 1
        assert created_members[0].role == BusinessRole.OWNER.value
        assert created_members[0].user_id == 42


# ---------------------------------------------------------------------------
# DB integration — blocked
# ---------------------------------------------------------------------------

@pytest.mark.skip(
    reason="BLOCKED: DB integration tests cannot be run against the default Neon "
           "development database safely without isolated schemas."
)
def test_db_integration_blocked():
    pass
