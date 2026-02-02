"""Alembic migration environment configuration.

This module configures the Alembic migration environment for FlowyML.
It reads the database URL from the FLOWYML_DATABASE_URL environment variable.
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from environment
database_url = os.getenv("FLOWYML_DATABASE_URL", "sqlite:///flowyml.db")
config.set_main_option("sqlalchemy.url", database_url)

# Import metadata for autogenerate support
from flowyml.storage.sql import SQLMetadataStore  # noqa: E402

# Create a temporary store to get metadata
_temp_store = SQLMetadataStore(db_url=database_url)
target_metadata = _temp_store.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
