"""create products table

Revision ID: 9d3411b2cbd0
Revises: 1bfa7795d62f
Create Date: 2026-07-14 11:41:50.712166

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9d3411b2cbd0"
down_revision: Union[str, Sequence[str], None] = "1bfa7795d62f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the products table."""

    op.create_table(
        "products",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "business_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "category",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "sku",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "barcode",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "cost_price",
            sa.Numeric(10, 2),
            nullable=False,
        ),
        sa.Column(
            "selling_price",
            sa.Numeric(10, 2),
            nullable=False,
        ),
        sa.Column(
            "current_stock",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "minimum_stock",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "image_url",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_products_business_id",
        "products",
        ["business_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the products table."""

    op.drop_index(
        "ix_products_business_id",
        table_name="products",
    )

    op.drop_table("products")