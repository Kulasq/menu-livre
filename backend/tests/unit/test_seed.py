from __future__ import annotations

import pytest
from app.models.usuario import Usuario
from app.models.configuracao import Configuracao
from app.services.auth_service import verificar_senha


def executar_seed(db) -> None:
    """Executa a lógica do seed diretamente, sem subprocess."""
    from scripts.seed import seed_usuario, seed_configuracao
    seed_usuario(db)
    seed_configuracao(db)


class TestSeedUsuario:
    def test_cria_superadmin(self, db_teste):
        executar_seed(db_teste)

        usuario = db_teste.query(Usuario).filter_by(email="sara@paodemao.com.br").first()
        assert usuario is not None

    def test_superadmin_tem_campos_corretos(self, db_teste):
        executar_seed(db_teste)

        usuario = db_teste.query(Usuario).filter_by(email="sara@paodemao.com.br").first()
        assert usuario.nome == "Sara"
        assert usuario.role == "superadmin"
        assert usuario.ativo is True

    def test_superadmin_senha_valida(self, db_teste):
        executar_seed(db_teste)

        usuario = db_teste.query(Usuario).filter_by(email="sara@paodemao.com.br").first()
        assert verificar_senha("paodemao2026", usuario.senha_hash) is True

    def test_seed_idempotente_usuario(self, db_teste):
        """Rodar o seed duas vezes não duplica o usuário."""
        executar_seed(db_teste)
        executar_seed(db_teste)

        total = db_teste.query(Usuario).filter_by(email="sara@paodemao.com.br").count()
        assert total == 1


class TestSeedConfiguracao:
    def test_cria_configuracao(self, db_teste):
        executar_seed(db_teste)

        config = db_teste.query(Configuracao).filter_by(id=1).first()
        assert config is not None

    def test_configuracao_tem_campos_corretos(self, db_teste):
        executar_seed(db_teste)

        config = db_teste.query(Configuracao).filter_by(id=1).first()
        assert config.nome_loja == "Pão de Mão"
        assert config.whatsapp == "5581996008571"
        assert config.instagram_url == "https://instagram.com/paodemao"
        assert config.aceitar_pedidos is True

    def test_configuracao_valores_padrao(self, db_teste):
        executar_seed(db_teste)

        config = db_teste.query(Configuracao).filter_by(id=1).first()
        assert config.taxa_entrega == 0.0
        assert config.pedido_minimo == 0.0
        assert config.tempo_entrega_min == 30
        assert config.tempo_entrega_max == 50

    def test_seed_idempotente_configuracao(self, db_teste):
        """Rodar o seed duas vezes não duplica a configuração."""
        executar_seed(db_teste)
        executar_seed(db_teste)

        total = db_teste.query(Configuracao).filter_by(id=1).count()
        assert total == 1