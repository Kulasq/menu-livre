from __future__ import annotations
import base64
import io
import unicodedata

import qrcode


def _crc16(data: str) -> str:
    crc = 0xFFFF
    for byte in data.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return f"{crc:04X}"


def _campo(id_: str, valor: str) -> str:
    return f"{id_}{len(valor):02d}{valor}"


def _sanitizar(texto: str, max_len: int) -> str:
    normalizado = unicodedata.normalize("NFKD", texto)
    sem_acentos = "".join(c for c in normalizado if not unicodedata.combining(c))
    ascii_only = "".join(c if ord(c) < 128 else " " for c in sem_acentos)
    limpo = " ".join(ascii_only.split())
    return limpo[:max_len].strip() or "LOJA"


def _normalizar_chave_telefone(chave: str) -> str:
    """Telefone PIX deve estar no formato E.164: +5511999990000.
    Se a chave for só dígitos (10–11 chars), adiciona o prefixo +55."""
    digitos = ''.join(c for c in chave if c.isdigit())
    if len(digitos) in (10, 11) and chave == digitos:
        return f"+55{digitos}"
    return chave


def gerar_br_code(
    chave_pix: str,
    valor: float,
    nome_beneficiario: str,
    cidade: str = "SAO PAULO",
    txid: str = "***",
    tipo_chave: str | None = None,
) -> str:
    if tipo_chave in ("celular", "telefone"):
        chave_pix = _normalizar_chave_telefone(chave_pix)

    nome = _sanitizar(nome_beneficiario, 25)
    cidade_san = _sanitizar(cidade, 15)
    valor_str = f"{valor:.2f}"

    merchant_account = _campo("26", _campo("00", "BR.GOV.BCB.PIX") + _campo("01", chave_pix))
    additional_data = _campo("62", _campo("05", txid))

    payload = (
        _campo("00", "01")
        + merchant_account
        + _campo("52", "0000")
        + _campo("53", "986")
        + _campo("54", valor_str)
        + _campo("58", "BR")
        + _campo("59", nome)
        + _campo("60", cidade_san)
        + additional_data
        + "6304"
    )
    return payload + _crc16(payload)


def gerar_qr_base64(br_code: str) -> str:
    img = qrcode.make(br_code)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def gerar_cobranca_pix(
    chave_pix: str,
    valor: float,
    nome_loja: str,
    tipo_chave: str | None = None,
) -> dict | None:
    if not chave_pix or valor <= 0:
        return None
    try:
        br_code = gerar_br_code(chave_pix, valor, nome_loja, tipo_chave=tipo_chave)
        qr_base64 = gerar_qr_base64(br_code)
        return {"br_code": br_code, "qr_code_base64": qr_base64}
    except Exception:
        return None
