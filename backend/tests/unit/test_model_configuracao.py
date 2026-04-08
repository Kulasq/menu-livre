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

    assert config.nome_loja == "Minha Loja"
    assert config.taxa_entrega == 0.0
    assert config.fechado_manualmente is False
    assert config.tempo_entrega_min == 30
    assert config.tempo_entrega_max == 50


def test_campos_de_cores_tem_defaults():
    """Novos campos de cores devem ter os defaults da paleta Menu Livre."""
    db = setup_db()

    config = Configuracao(whatsapp="5581996008571")
    db.add(config)
    db.commit()
    db.refresh(config)

    assert config.cor_primaria   == "#f59e0b"
    assert config.cor_secundaria == "#d97706"
    assert config.cor_fundo      == "#f1f5f9"
    assert config.cor_fonte      == "#0f172a"
    assert config.cor_banner     == "#0f172a"


def test_campos_de_cores_aceitam_nulo_via_update():
    """Campos de cores aceitam NULL quando zerados via setattr (fluxo do service)."""
    db = setup_db()

    config = Configuracao(whatsapp="5581996008571")
    db.add(config)
    db.commit()

    # Simula o service zerando as cores após criação (não no construtor)
    config.cor_primaria = None
    config.cor_banner = None
    db.commit()
    db.refresh(config)

    assert config.cor_primaria is None
    assert config.cor_banner is None


def test_sempre_uma_linha():
    """Configuração deve ter sempre id=1 (linha única)."""
    db = setup_db()

    config = Configuracao(id=1, whatsapp="5581996008571")
    db.add(config)
    db.commit()

    assert config.id == 1