from __future__ import annotations
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.services.whatsapp_service import gerar_url, formatar_mensagem, _formatar_fone


# ---------------------------------------------------------------------------
# gerar_url
# ---------------------------------------------------------------------------

class TestGerarUrl:
    def test_formato_base(self):
        """Deve usar api.whatsapp.com/send/ para evitar redirect que corrompe emojis."""
        url = gerar_url("Olá")
        assert url.startswith("https://api.whatsapp.com/send/")
        assert "?phone=" in url
        assert "text=" in url

    def test_formato_correto_api_direta(self):
        """Deve usar api.whatsapp.com/send/?phone=NUMERO&text=... (não wa.me)."""
        url = gerar_url("teste")
        assert "wa.me" not in url
        assert "api.whatsapp.com/send/" in url
        assert "?phone=" in url

    def test_emojis_sao_percent_encoded_utf8(self):
        """Emojis devem ser percent-encoded como UTF-8 (%F0%9F...), não Unicode bruto."""
        url = gerar_url("🍔 Pedido")
        assert "%F0%9F" in url       # 🍔 codificado como UTF-8
        assert "🍔" not in url        # não deve aparecer literal

    def test_espacos_como_porcento_20_nao_mais(self):
        """Espaços devem ser %20, não + (que é form-encoding, não URL-encoding)."""
        url = gerar_url("texto com espaço")
        assert "%20" in url
        assert "+" not in url.split("text=")[1]

    def test_acentos_sao_percent_encoded(self):
        url = gerar_url("Pão de Mão")
        assert "%C3%A3" in url   # 'ã' em UTF-8
        assert "ã" not in url

    def test_ampersand_e_igual_sao_encoded(self):
        """Caracteres & e = na mensagem não devem quebrar a query string."""
        url = gerar_url("a=1&b=2")
        assert "a=1&b=2" not in url
        assert "%3D" in url  # =
        assert "%26" in url  # &

    def test_newline_e_encoded(self):
        url = gerar_url("linha1\nlinha2")
        assert "\n" not in url
        assert "%0A" in url

    def test_url_contem_numero_whatsapp_no_phone_param(self):
        """Número deve estar no parâmetro phone= da query string."""
        with patch("app.services.whatsapp_service.settings") as mock_settings:
            mock_settings.WHATSAPP_NUMBER = "5581999990000"
            url = gerar_url("teste")
        assert "phone=5581999990000" in url


# ---------------------------------------------------------------------------
# _formatar_fone
# ---------------------------------------------------------------------------

class TestFormatarFone:
    def test_celular_11_digitos(self):
        assert _formatar_fone("81996008571") == "81 99600-8571"

    def test_fixo_10_digitos(self):
        assert _formatar_fone("8133330000") == "81 3333-0000"

    def test_com_caracteres_especiais(self):
        # Remove não-dígitos antes de formatar
        assert _formatar_fone("(81) 9 9600-8571") == "81 99600-8571"

    def test_formato_inesperado_retorna_original(self):
        assert _formatar_fone("123") == "123"


# ---------------------------------------------------------------------------
# formatar_mensagem — testa a estrutura geral da mensagem
# ---------------------------------------------------------------------------

def _mock_pedido(tipo="delivery", metodo="pix", com_modificador=False, com_obs=True):
    """Cria um pedido fake com MagicMock para testar formatar_mensagem."""
    pedido = MagicMock()
    pedido.numero = "001"
    pedido.criado_em = datetime(2025, 1, 10, 14, 30, tzinfo=timezone.utc)
    pedido.tipo = tipo
    pedido.endereco_entrega = "Rua A, 123" if tipo == "delivery" else None
    pedido.agendado_para = None
    pedido.subtotal = 30.00
    pedido.taxa_entrega = 5.00 if tipo == "delivery" else 0.00
    pedido.total = 35.00
    pedido.metodo_pagamento = metodo
    pedido.observacao = "Sem cebola" if com_obs else None

    pedido.cliente.nome = "João"
    pedido.cliente.telefone = "81996008571"

    item = MagicMock()
    item.quantidade = 1
    item.nome_snapshot = "X-Burguer"
    item.subtotal = 30.00
    item.observacao = None
    item.modificadores = []

    if com_modificador:
        mod = MagicMock()
        mod.nome_snapshot = "Bacon extra"
        mod.preco_snapshot = 3.00
        item.modificadores = [mod]

    pedido.itens = [item]
    return pedido


class TestFormatarMensagem:
    def test_contem_numero_pedido(self):
        msg = formatar_mensagem(_mock_pedido())
        assert "001" in msg

    def test_contem_nome_cliente(self):
        msg = formatar_mensagem(_mock_pedido())
        assert "João" in msg

    def test_delivery_contem_endereco(self):
        msg = formatar_mensagem(_mock_pedido(tipo="delivery"))
        assert "Rua A, 123" in msg

    def test_retirada_nao_contem_endereco(self):
        msg = formatar_mensagem(_mock_pedido(tipo="retirada"))
        assert "Rua A, 123" not in msg

    def test_contem_total_formatado(self):
        msg = formatar_mensagem(_mock_pedido())
        assert "R$ 35,00" in msg

    def test_contem_taxa_entrega_quando_delivery(self):
        msg = formatar_mensagem(_mock_pedido(tipo="delivery"))
        assert "R$ 5,00" in msg

    def test_modificador_aparece_na_mensagem(self):
        msg = formatar_mensagem(_mock_pedido(com_modificador=True))
        assert "Bacon extra" in msg
        assert "R$ 3,00" in msg

    def test_observacao_aparece_na_mensagem(self):
        msg = formatar_mensagem(_mock_pedido(com_obs=True))
        assert "Sem cebola" in msg

    def test_metodo_pix_mostra_chave(self):
        msg = formatar_mensagem(_mock_pedido(metodo="pix"))
        assert "Chave" in msg

    def test_metodo_cartao_nao_mostra_chave(self):
        msg = formatar_mensagem(_mock_pedido(metodo="cartao"))
        assert "Chave" not in msg
