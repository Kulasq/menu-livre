from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.configuracao import Configuracao


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_criar_configuracao():
    """Verifica que a configuração é salva com defaults corretos."""
    db = setup_db()

    config = Configuracao(whatsapp="5581996008571")
    db.add(config)
    db.commit()
    db.refresh(config)

    assert config.nome_loja == "Pão de Mão"
    assert config.taxa_entrega == 0.0
    assert config.aceitar_pedidos is True
    assert config.tempo_entrega_min == 30
    assert config.tempo_entrega_max == 50


def test_sempre_uma_linha():
    """Configuração deve ter sempre id=1 (linha única)."""
    db = setup_db()

    config = Configuracao(id=1, whatsapp="5581996008571")
    db.add(config)
    db.commit()

    assert config.id == 1