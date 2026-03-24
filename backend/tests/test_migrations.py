import subprocess
import os
import tempfile
import pytest
from sqlalchemy import create_engine, inspect, text


def rodar_alembic(comando: list[str], db_url: str) -> subprocess.CompletedProcess:
    """Roda comando alembic com URL do banco sobrescrita via variável de ambiente."""
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    return subprocess.run(
        comando,
        capture_output=True,
        text=True,
        env=env,
    )


def test_migration_upgrade_e_downgrade():
    """Verifica que a migration sobe e desce sem erros."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    try:
        db_url = f"sqlite:///{db_path}"

        resultado_up = rodar_alembic(
            ["alembic", "upgrade", "head"], db_url
        )
        assert resultado_up.returncode == 0, (
            f"Falha no upgrade:\n{resultado_up.stderr}"
        )

        resultado_down = rodar_alembic(
            ["alembic", "downgrade", "base"], db_url
        )
        assert resultado_down.returncode == 0, (
            f"Falha no downgrade:\n{resultado_down.stderr}"
        )
    finally:
        os.unlink(db_path)


def test_migration_cria_tabelas_esperadas():
    """Verifica que as tabelas corretas são criadas após upgrade."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    try:
        db_url = f"sqlite:///{db_path}"

        resultado = rodar_alembic(["alembic", "upgrade", "head"], db_url)
        assert resultado.returncode == 0, (
            f"Migration falhou:\n{resultado.stderr}"
        )

        engine = create_engine(db_url)
        with engine.connect() as conn:
            tabelas = inspect(engine).get_table_names()

        engine.dispose()  # fecha conexão antes de deletar o arquivo

        tabelas_esperadas = {
            "usuarios",
            "clientes",
            "categorias",
            "produtos",
            "grupos_modificadores",
            "modificadores",
            "configuracoes",
            "alembic_version",
        }

        for tabela in tabelas_esperadas:
            assert tabela in tabelas, f"Tabela '{tabela}' não foi criada. Tabelas encontradas: {tabelas}"

    finally:
        os.unlink(db_path)