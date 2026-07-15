from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import os
import sys

sys.path.insert(
    0,
    os.path.realpath(
        os.path.join(os.path.dirname(__file__), "..")
    )
)

from app.core.config import settings
from app.db.base import Base
from app.models.user import User
from app.models.business import Business
from app.models.business_member import BusinessMember
from app.models.customer import Customer
from app.models.product import Product
from app.models.stock_adjustment import StockAdjustment

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLAlchemy metadata used by Alembic autogenerate.
target_metadata = Base.metadata

assert "users" in target_metadata.tables, (
    "User model not discovered by Alembic!"
)
assert "businesses" in target_metadata.tables, (
    "Business model not discovered by Alembic!"
)
assert "business_members" in target_metadata.tables, (
    "BusinessMember model not discovered by Alembic!"
)
assert "customers" in target_metadata.tables, (
    "Customer model not discovered by Alembic!"
)


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""

    if not settings.DATABASE_URL:
        raise ValueError(
            "DATABASE_URL is not configured. "
            "Alembic cannot run migrations."
        )

    url = settings.DATABASE_URL

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode."""

    if not settings.DATABASE_URL:
        raise ValueError(
            "DATABASE_URL is not configured. "
            "Alembic cannot run migrations."
        )

    configuration = config.get_section(
        config.config_ini_section,
        {}
    )
    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()