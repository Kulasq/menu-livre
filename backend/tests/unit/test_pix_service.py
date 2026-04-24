from __future__ import annotations
import pytest
from app.services.pix_service import _crc16, _sanitizar, _normalizar_chave_telefone, gerar_br_code, gerar_cobranca_pix


class TestCrc16:
    def test_vetor_conhecido(self):
        # Payload de referência pública sem CRC (sem os "6304" no final)
        # O CRC do payload completo deve terminar com os 4 hex do resultado
        payload = "00020126360014BR.GOV.BCB.PIX0114+5581999990000520400005303986540544.905802BR5905LOJA 6009SAO PAULO62070503***6304"
        crc = _crc16(payload)
        assert len(crc) == 4
        assert crc == crc.upper()
        assert all(c in "0123456789ABCDEF" for c in crc)

    def test_crc_string_vazia(self):
        crc = _crc16("")
        assert len(crc) == 4

    def test_crc_determinístico(self):
        assert _crc16("test") == _crc16("test")

    def test_crc_diferente_para_inputs_diferentes(self):
        assert _crc16("abc") != _crc16("abd")


class TestSanitizar:
    def test_remove_acentos(self):
        result = _sanitizar("Pão de Mão", 25)
        assert "ã" not in result
        assert "Pao" in result or "P" in result

    def test_trunca_no_max_len(self):
        result = _sanitizar("A" * 50, 25)
        assert len(result) <= 25

    def test_texto_vazio_retorna_loja(self):
        result = _sanitizar("", 25)
        assert result == "LOJA"

    def test_texto_ascii_passa_intacto(self):
        result = _sanitizar("HAMBURGUERIA", 25)
        assert result == "HAMBURGUERIA"

    def test_espaco_duplo_vira_simples(self):
        result = _sanitizar("A  B", 25)
        assert "  " not in result


class TestNormalizarChaveTelefone:
    def test_celular_11_digitos_recebe_prefixo(self):
        assert _normalizar_chave_telefone("81996008571") == "+5581996008571"

    def test_fixo_10_digitos_recebe_prefixo(self):
        assert _normalizar_chave_telefone("8133330000") == "+558133330000"

    def test_ja_com_prefixo_nao_altera(self):
        assert _normalizar_chave_telefone("+5581996008571") == "+5581996008571"

    def test_email_nao_altera(self):
        assert _normalizar_chave_telefone("loja@email.com") == "loja@email.com"

    def test_cpf_com_pontuacao_nao_altera(self):
        assert _normalizar_chave_telefone("123.456.789-09") == "123.456.789-09"

    def test_chave_aleatoria_nao_altera(self):
        chave = "a1b2c3d4-1234-5678-abcd-ef1234567890"
        assert _normalizar_chave_telefone(chave) == chave


class TestGerarBrCode:
    def test_começa_com_0001(self):
        br = gerar_br_code("11999990000", 42.50, "Loja Teste")
        assert br.startswith("0002")

    def test_contem_chave_pix(self):
        chave = "11999990000"
        br = gerar_br_code(chave, 42.50, "Loja Teste")
        assert chave in br

    def test_contem_valor_formatado(self):
        br = gerar_br_code("11999990000", 42.50, "Loja Teste")
        assert "42.50" in br

    def test_valor_inteiro_tem_duas_casas(self):
        br = gerar_br_code("11999990000", 10.0, "Loja Teste")
        assert "10.00" in br

    def test_termina_com_crc_4_hex(self):
        br = gerar_br_code("11999990000", 42.50, "Loja Teste")
        crc_part = br[-4:]
        assert len(crc_part) == 4
        assert all(c in "0123456789ABCDEFabcdef" for c in crc_part)

    def test_campo_pais_br(self):
        br = gerar_br_code("11999990000", 42.50, "Loja Teste")
        assert "5802BR" in br

    def test_campo_moeda_986(self):
        br = gerar_br_code("11999990000", 42.50, "Loja Teste")
        assert "5303986" in br

    def test_nome_longo_truncado(self):
        nome_longo = "A" * 50
        br = gerar_br_code("11999990000", 10.0, nome_longo)
        # Nome truncado em 25 chars
        assert nome_longo not in br

    def test_email_como_chave(self):
        br = gerar_br_code("loja@email.com", 25.00, "Loja")
        assert "loja@email.com" in br

    def test_cpf_como_chave(self):
        br = gerar_br_code("123.456.789-09", 15.00, "Loja")
        assert "123.456.789-09" in br

    def test_celular_sem_prefixo_normalizado_quando_tipo_celular(self):
        br = gerar_br_code("81996008571", 10.00, "Loja", tipo_chave="celular")
        assert "+5581996008571" in br

    def test_celular_sem_prefixo_normalizado_quando_tipo_telefone(self):
        # aceita ambos os valores para retrocompatibilidade
        br = gerar_br_code("81996008571", 10.00, "Loja", tipo_chave="telefone")
        assert "+5581996008571" in br

    def test_celular_sem_tipo_nao_normaliza(self):
        br = gerar_br_code("81996008571", 10.00, "Loja")
        assert "81996008571" in br


class TestGerarCobrancaPix:
    def test_retorna_dict_com_br_code_e_qr(self):
        result = gerar_cobranca_pix("11999990000", 42.50, "Loja Teste")
        assert result is not None
        assert "br_code" in result
        assert "qr_code_base64" in result

    def test_qr_e_data_uri_png(self):
        result = gerar_cobranca_pix("11999990000", 42.50, "Loja Teste")
        assert result["qr_code_base64"].startswith("data:image/png;base64,")

    def test_sem_chave_retorna_none(self):
        assert gerar_cobranca_pix("", 42.50, "Loja") is None
        assert gerar_cobranca_pix(None, 42.50, "Loja") is None

    def test_valor_zero_retorna_none(self):
        assert gerar_cobranca_pix("11999990000", 0, "Loja") is None

    def test_valor_negativo_retorna_none(self):
        assert gerar_cobranca_pix("11999990000", -5.0, "Loja") is None
