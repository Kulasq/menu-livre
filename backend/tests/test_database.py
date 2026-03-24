import tempfile
import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from app.database import Base


def criar_engine_memoria():
    """Engine em memória — para testes de estrutura (rápido)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def configurar(conn, rec):
        conn.execute("PRAGMA foreign_keys=ON")

    return engine


def criar_engine_disco():
    """Engine em arquivo temporário — para testar PRAGMAs de disco (WAL)."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()

    engine = create_engine(
        f"sqlite:///{tmp.name}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def configurar(conn, rec):
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

    return engine, tmp.name


def test_banco_cria_tabelas():
    """Verifica que o banco inicializa sem erros."""
    engine = criar_engine_memoria()
    Base.metadata.create_all(engine)
    Base.metadata.drop_all(engine)


def test_pragma_foreign_keys_ativo():
    """Verifica que foreign keys estão habilitadas."""
    engine = criar_engine_memoria()
    Session = sessionmaker(bind=engine)
    db = Session()

    result = db.execute(text("PRAGMA foreign_keys")).fetchone()
    assert result[0] == 1, "PRAGMA foreign_keys deve estar ON (1)"

    db.close()


def test_pragma_wal_ativo():
    """WAL mode só funciona em banco de arquivo — não em memória."""
    engine, tmp_path = criar_engine_disco()
    Session = sessionmaker(bind=engine)
    db = Session()

    result = db.execute(text("PRAGMA journal_mode")).fetchone()
    assert result[0] == "wal", "journal_mode deve ser WAL em banco de arquivo"

    db.close()
    engine.dispose()

    # Limpar arquivos temporários
    for ext in ("", "-wal", "-shm"):
        path = tmp_path + ext
        if os.path.exists(path):
            os.remove(path)