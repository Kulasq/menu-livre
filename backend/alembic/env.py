import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Importar Base e todos os models para o Alembic detectar
from app.database import Base
import app.models  # noqa: F401 — garante que todos os models são registrados

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
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
    # Permite sobrescrever a URL via variável de ambiente (útil em testes)
    url_override = os.environ.get("DATABASE_URL")
    
    cfg = config.get_section(config.config_ini_section, {})
    if url_override:
        cfg["sqlalchemy.url"] = url_override

    connectable = engine_from_config(
        cfg,
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