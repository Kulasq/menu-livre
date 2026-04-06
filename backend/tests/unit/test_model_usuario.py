from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.usuario import Usuario


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_criar_usuario():
    """Verifica que um usuário é salvo e recuperado corretamente."""
    db = setup_db()

    usuario = Usuario(
        nome="Kulas Dantas",
        email="kulas@paodeamao.com",
        senha_hash="hash_qualquer",
        role="superadmin",
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    assert usuario.id is not None
    assert usuario.nome == "Kulas Dantas"
    assert usuario.email == "kulas@paodeamao.com"
    assert usuario.role == "superadmin"
    assert usuario.ativo is True  # default
    assert usuario.ultimo_acesso is None  # default


def test_email_unico():
    """Verifica que dois usuários não podem ter o mesmo email."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    db = setup_db()

    db.add(Usuario(nome="A", email="mesmo@email.com", senha_hash="h1"))
    db.commit()

    db.add(Usuario(nome="B", email="mesmo@email.com", senha_hash="h2"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_role_default_admin():
    """Verifica que o role padrão é admin."""
    db = setup_db()

    usuario = Usuario(nome="Func", email="func@teste.com", senha_hash="h")
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    assert usuario.role == "admin"