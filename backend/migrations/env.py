"""Alembic environment configuration"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import models
from app.database import Base
from app.models import user

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# set the target metadata for 'autogenerate' support
target_metadata = Base.metadata

# Get database URL from environment
database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://testtrack:testtrack123@localhost:5432/testtrack_pro"
)
config.set_main_option("sqlalchemy.url", database_url)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode - generates SQL scripts without DB connection"""

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode - requires DB connection"""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
