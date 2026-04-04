from __future__ import annotations
from urllib.parse import quote
from app.config import settings


def formatar_mensagem(pedido) -> str:
    from datetime import timezone, timedelta
    BRT = timezone(timedelta(hours=-3))
    horario = pedido.criado_em.replace(tzinfo=timezone.utc).astimezone(BRT)
    horario_str = horario.strftime("%H:%M")

    def brl(valor: float) -> str:
        return f"R$ {valor:.2f}".replace(".", ",")

    lines = [
        "🍔 *Pão de Mão* — Novo Pedido!",
        "",
        f"📋 Pedido: {pedido.numero}",
        f"👤 Cliente: {pedido.cliente.nome}",
        f"📱 Telefone: {_formatar_fone(pedido.cliente.telefone)}",
        "",
    ]

    tipo_label = {"delivery": "Delivery", "retirada": "Retirada"}.get(pedido.tipo, pedido.tipo)
    lines.append(f"🚚 *Tipo:* {tipo_label}")

    if pedido.tipo == "delivery" and pedido.endereco_entrega:
        lines.append(f"📍 *Endereço:* {pedido.endereco_entrega}")

    if pedido.agendado_para:
        agendado_brt = pedido.agendado_para.replace(tzinfo=timezone.utc).astimezone(BRT)
        agendado_str = agendado_brt.strftime("%d/%m/%Y às %H:%M")
        lines.append(f"📅 *Agendado para:* {agendado_str}")

    lines += ["", "🛍️ *Produtos:*"]

    for item in pedido.itens:
        lines.append(f"• {item.quantidade}x {item.nome_snapshot} — {brl(item.subtotal)}")
        for mod in item.modificadores:
            extra = f" (+{brl(mod.preco_snapshot)})" if mod.preco_snapshot > 0 else ""
            lines.append(f"  └ {mod.nome_snapshot}{extra}")
        if item.observacao:
            lines.append(f"  └ Obs: {item.observacao}")

    lines += [
        "",
        "💰 *Resumo:*",
        f"Subtotal: {brl(pedido.subtotal)}",
    ]

    if pedido.taxa_entrega > 0:
        lines.append(f"Entrega: {brl(pedido.taxa_entrega)}")

    lines.append(f"*Total: {brl(pedido.total)}*")

    metodo = {"pix": "PIX", "dinheiro": "Dinheiro", "cartao": "Cartão"}.get(
        pedido.metodo_pagamento or "", pedido.metodo_pagamento or ""
    )
    lines += ["", f"💳 *Pagamento:* {metodo}"]

    if pedido.metodo_pagamento == "pix":
        lines.append(f"🔑 Chave: {settings.WHATSAPP_NUMBER}")

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