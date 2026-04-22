from __future__ import annotations
from urllib.parse import quote
from app.config import settings


def formatar_mensagem(pedido, nome_loja: str = "Menu Livre", chave_pix: str | None = None) -> str:
    from datetime import timezone, timedelta
    BRT = timezone(timedelta(hours=-3))
    horario = pedido.criado_em.replace(tzinfo=timezone.utc).astimezone(BRT)
    horario_str = horario.strftime("%H:%M")

    def brl(valor: float) -> str:
        return f"R$ {valor:.2f}".replace(".", ",")

    lines = []
    if settings.CARDAPIO_URL:
        lines.append(f"🌐 {settings.CARDAPIO_URL}")

    lines += [
        f"🍔 *{nome_loja}* — Novo Pedido!",
        "",
        f"📋 Pedido: {pedido.numero}",
    ]

    if pedido.agendado_para:
        agendado_brt = pedido.agendado_para.replace(tzinfo=timezone.utc).astimezone(BRT)
        agendado_str = agendado_brt.strftime("%d/%m/%Y às %H:%M")
        lines += [
            "",
            "⚠️ *PEDIDO AGENDADO*",
            f"📅 *Agendado para:* {agendado_str}",
            "",
        ]

    lines += [
        f"👤 Cliente: {pedido.cliente.nome}",
        f"📱 Telefone: {_formatar_fone(pedido.cliente.telefone)}",
        "",
    ]

    tipo_label = {"delivery": "Delivery", "retirada": "Retirada"}.get(pedido.tipo, pedido.tipo)
    lines.append(f"🏍️ *Tipo:* {tipo_label}" if pedido.tipo == "delivery" else f"🛍️ *Tipo:* {tipo_label}")

    if pedido.tipo == "delivery" and pedido.endereco_entrega:
        lines.append(f"📍 *Endereço:* {pedido.endereco_entrega}")

    lines += ["", "🛍️ *Produtos:*"]

    for item in pedido.itens:
        lines.append(f"• {item.quantidade}x {item.nome_snapshot} — {brl(item.subtotal)}")
        for mod in item.modificadores:
            extra = f" (+{brl(mod.preco_snapshot)})" if mod.preco_snapshot > 0 else ""
            lines.append(f"  └ {mod.nome_snapshot}{extra}")
        if item.observacao:
            lines.append(f"  └ Obs: {item.observacao}")

    metodo = {"pix": "PIX", "dinheiro": "Dinheiro", "cartao": "Cartão"}.get(
        pedido.metodo_pagamento or "", pedido.metodo_pagamento or ""
    )
    lines += ["", f"💳 *Pagamento:* {metodo}"]

    if pedido.metodo_pagamento == "pix" and chave_pix:
        lines.append(f"🔑 Chave: {chave_pix}")

    lines += [
        "",
        "💰 *Resumo:*",
        f"Subtotal: {brl(pedido.subtotal)}",
    ]

    if pedido.taxa_entrega > 0:
        lines.append(f"Entrega: {brl(pedido.taxa_entrega)}")

    lines.append(f"*Total: {brl(pedido.total)}*")

    if pedido.metodo_pagamento == "dinheiro":
        if pedido.troco_para:
            lines.append(f"💵 Valor recebido: {brl(pedido.troco_para)}")
            lines.append(f"💵 *Troco: {brl(pedido.troco_para - pedido.total)}*")
        else:
            lines.append("💵 Não precisa de troco")

    if pedido.observacao:
        lines += ["", f"📝 *Observação:* {pedido.observacao}"]

    lines.append(f"\n⏰ Pedido às {horario_str}")
    return "\n".join(lines)


def gerar_url(mensagem: str) -> str:
    encoded = quote(mensagem, safe='')
    return f"https://api.whatsapp.com/send/?phone={settings.WHATSAPP_NUMBER}&text={encoded}"


def _formatar_fone(telefone: str) -> str:
    d = "".join(c for c in telefone if c.isdigit())
    if len(d) == 11:
        return f"{d[:2]} {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"{d[:2]} {d[2:6]}-{d[6:]}"
    return telefone