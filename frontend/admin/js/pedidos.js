/**
 * Gestão de pedidos — listagem, filtros, status, pagamento.
 * A notificação sonora e o FAB de novos pedidos vivem em notificacao-pedidos.js (global).
 * Depende de: config.js, auth.js (api, auth), utils.js (toast, formatarPreco, $)
 */

/* ── Estado ─────────────────────────────────────────────── */

let pedidos = []
let pedidoSelecionado = null
let filtroStatus = ''
let filtroTipo = ''
let paginaAtual = 1
let autoRefreshTimer = null

const STATUS_LABELS = {
  pendente:   { label: 'Pendente',    classe: 'badge-aviso',   icon: () => icons.relogio },
  confirmado: { label: 'Confirmado',  classe: 'badge-info',    icon: () => icons.check },
  em_preparo: { label: 'Preparando',  classe: 'badge-preparo', icon: () => icons.fogo },
  pronto:     { label: 'Pronto',      classe: 'badge-sucesso', icon: () => icons.caixa },
  entregue:   { label: 'Entregue',    classe: 'badge-entregue',icon: () => icons.check_badge },
  cancelado:  { label: 'Cancelado',   classe: 'badge-erro',    icon: () => icons.x_circulo },
}

const FLUXO_STATUS = {
  pendente:   'confirmado',
  confirmado: 'em_preparo',
  em_preparo: 'pronto',
  pronto:     'entregue',
}

const TIPO_LABELS = {
  delivery:  'Delivery',
  retirada:  'Retirada',
}

const PAGAMENTO_LABELS = {
  pix:      'PIX',
  dinheiro: 'Dinheiro',
  cartao:   'Cartão',
}


/* ── Inicialização ──────────────────────────────────────── */

/* Nome da loja para o template de impressão (preenchido após auth) */
let _nomeLoja = ''

document.addEventListener('DOMContentLoaded', () => {
  if (!auth.proteger()) return

  setupUsuario()
  setupSidebar()
  carregarNomeLojaSidebar()
  setupEventos()
  carregarPedidos()

  /* Carrega nome_loja para o cupom térmico (usa cache de sessão se disponível) */
  api.get('/api/admin/configuracoes')
    .then(c => { if (c?.nome_loja) _nomeLoja = c.nome_loja })
    .catch(() => {})

  /* Polling a cada 5 segundos */
  autoRefreshTimer = setInterval(carregarPedidos, 5000)
})

function setupUsuario() {
  const usuario = auth.getUsuario()
  $('#header-usuario-nome').textContent = usuario.nome
  const iniciais = usuario.nome.split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase()
  $('#header-usuario-avatar').textContent = iniciais
}

function setupSidebar() {
  const sidebar = $('#sidebar')
  const overlay = $('#sidebar-overlay')
  $('#btn-menu').addEventListener('click', () => {
    sidebar.classList.add('aberto')
    overlay.classList.remove('hidden')
  })
  overlay.addEventListener('click', () => {
    sidebar.classList.remove('aberto')
    overlay.classList.add('hidden')
  })
}

function setupEventos() {
  /* Filtros */
  $('#filtro-status').addEventListener('change', (e) => {
    filtroStatus = e.target.value
    paginaAtual = 1
    carregarPedidos()
  })

  $('#filtro-tipo').addEventListener('change', (e) => {
    filtroTipo = e.target.value
    paginaAtual = 1
    carregarPedidos()
  })

  $('#btn-atualizar').addEventListener('click', carregarPedidos)

  /* Modal detalhe */
  $('#modal-pedido-fechar').addEventListener('click', fecharModalPedido)
  $('#modal-pedido-overlay').addEventListener('click', fecharModalPedido)

  /* Highlight de pedido disparado pelo FAB global (notificacao-pedidos.js) */
  window.addEventListener('pedido:highlight', (ev) => {
    destacarCard(ev.detail?.id)
  })
}

function destacarCard(id) {
  if (!id) return
  const card = document.querySelector(`.pedido-card[data-id="${id}"]`)
  if (!card) return
  card.scrollIntoView({ behavior: 'smooth', block: 'center' })
  card.classList.remove('highlight')
  void card.offsetWidth /* força reflow para reiniciar animação */
  card.classList.add('highlight')
  setTimeout(() => card.classList.remove('highlight'), 3500)
}


/* ══════════════════════════════════════════════════════════
   CARREGAR PEDIDOS
   ══════════════════════════════════════════════════════════ */

async function carregarPedidos() {
  try {
    let url = `/api/admin/pedidos?page=${paginaAtual}`
    if (filtroStatus) url += `&status=${filtroStatus}`
    if (filtroTipo) url += `&tipo=${filtroTipo}`

    const data = await api.get(url)
    pedidos = data
    renderPedidos()
  } catch (err) {
    console.error('Erro ao carregar pedidos:', err.message)
  }
}


/* ══════════════════════════════════════════════════════════
   RENDERIZAÇÃO
   ══════════════════════════════════════════════════════════ */

function renderPedidos() {
  const container = $('#pedidos-lista')
  const vazio = $('#pedidos-vazio')
  const loading = $('#pedidos-loading')

  loading.classList.add('hidden')

  if (pedidos.length === 0) {
    container.innerHTML = ''
    vazio.classList.remove('hidden')
    return
  }

  vazio.classList.add('hidden')
  container.innerHTML = pedidos.map(p => renderCardPedido(p)).join('')
  window.dispatchEvent(new CustomEvent('pedidos:renderizados'))
}

function renderCardPedido(pedido) {
  const statusInfo = STATUS_LABELS[pedido.status] || STATUS_LABELS.pendente
  const tipoLabel = TIPO_LABELS[pedido.tipo] || pedido.tipo
  const pagLabel = PAGAMENTO_LABELS[pedido.metodo_pagamento] || pedido.metodo_pagamento || '—'
  const horario = formatarHora(pedido.criado_em)
  const itensResumo = pedido.itens.map(i => `${i.quantidade}x ${esc(i.nome_snapshot)}`).join(', ')
  const proximoStatus = FLUXO_STATUS[pedido.status]

  const agendadoHtml = pedido.agendado_para
    ? `<span class="pedido-agendado">${formatarDataHora(pedido.agendado_para)}</span>`
    : ''

  const pagamentoClass = pedido.status_pagamento === 'pago' ? 'badge-sucesso' : 'badge-aviso'
  const pagamentoLabel = pedido.status_pagamento === 'pago' ? 'Pago' : 'Pendente'

  return `
    <div class="pedido-card" data-id="${pedido.id}" onclick="abrirDetalhe(${pedido.id})">
      <div class="pedido-card-top">
        <div class="pedido-card-info">
          <div class="pedido-card-numero">
            <strong>${esc(pedido.numero)}</strong>
            <span class="pedido-card-hora">${horario}</span>
          </div>
          <div class="pedido-card-cliente">${esc(pedido.cliente.nome)} · ${esc(pedido.cliente.telefone)}</div>
        </div>
        <span class="badge ${statusInfo.classe}">${statusInfo.icon()} ${statusInfo.label}</span>
      </div>

      <div class="pedido-card-meio">
        <span class="pedido-card-tipo">${tipoLabel}</span>
        <span class="pedido-card-itens">${esc(itensResumo)}</span>
        ${agendadoHtml}
      </div>

      <div class="pedido-card-bottom">
        <div class="pedido-card-valores">
          <span class="pedido-card-total">${formatarPreco(pedido.total)}</span>
          <span class="badge btn-sm ${pagamentoClass}" onclick="event.stopPropagation(); togglePagamento(${pedido.id})" title="Clique para alterar">${pagamentoLabel}</span>
          <span class="pedido-card-pagamento">${pagLabel}</span>
        </div>
        <div class="pedido-card-acoes" onclick="event.stopPropagation()">
          ${proximoStatus ? `
            <button class="btn btn-primary btn-sm" onclick="avancarStatus(${pedido.id})" title="Avançar para ${STATUS_LABELS[proximoStatus]?.label}">
              ${STATUS_LABELS[proximoStatus]?.icon()} ${STATUS_LABELS[proximoStatus]?.label}
            </button>
          ` : ''}
          ${pedido.status !== 'cancelado' && pedido.status !== 'entregue' ? `
            <button class="btn btn-danger btn-sm" onclick="cancelarPedido(${pedido.id})" title="Cancelar pedido">
              ${icons.x_circulo}
            </button>
          ` : ''}
        </div>
      </div>
    </div>
  `
}


/* ══════════════════════════════════════════════════════════
   MODAL DE DETALHE
   ══════════════════════════════════════════════════════════ */

function abrirDetalhe(id) {
  const pedido = pedidos.find(p => p.id === id)
  if (!pedido) return
  pedidoSelecionado = pedido

  const statusInfo = STATUS_LABELS[pedido.status] || STATUS_LABELS.pendente
  const tipoLabel = TIPO_LABELS[pedido.tipo] || pedido.tipo
  const pagLabel = PAGAMENTO_LABELS[pedido.metodo_pagamento] || pedido.metodo_pagamento || '—'
  const pagStatus = pedido.status_pagamento === 'pago' ? 'Pago' : 'Pagamento pendente'

  $('#detalhe-numero').textContent = pedido.numero
  $('#detalhe-status').innerHTML = `<span class="badge ${statusInfo.classe}">${statusInfo.icon()} ${statusInfo.label}</span>`
  $('#detalhe-cliente').textContent = `${pedido.cliente.nome} · ${pedido.cliente.telefone}`
  $('#detalhe-tipo').textContent = tipoLabel
  $('#detalhe-horario').textContent = formatarDataHora(pedido.criado_em)
  $('#detalhe-pagamento').textContent = `${pagLabel} — ${pagStatus}`

  const trocoRow = $('#detalhe-troco-row')
  if (pedido.metodo_pagamento === 'dinheiro') {
    if (pedido.troco_para) {
      const troco = pedido.troco_para - pedido.total
      $('#detalhe-troco').textContent = `${formatarPreco(pedido.troco_para)} → troco de ${formatarPreco(troco)}`
    } else {
      $('#detalhe-troco').textContent = 'Não precisa de troco'
    }
    trocoRow.classList.remove('hidden')
  } else {
    trocoRow.classList.add('hidden')
  }

  const enderecoEl = $('#detalhe-endereco')
  if (pedido.endereco_entrega) {
    enderecoEl.textContent = pedido.endereco_entrega
    enderecoEl.parentElement.classList.remove('hidden')
  } else {
    enderecoEl.parentElement.classList.add('hidden')
  }

  const agendaEl = $('#detalhe-agendado')
  if (pedido.agendado_para) {
    agendaEl.textContent = formatarDataHora(pedido.agendado_para)
    agendaEl.parentElement.classList.remove('hidden')
  } else {
    agendaEl.parentElement.classList.add('hidden')
  }

  const obsEl = $('#detalhe-obs')
  if (pedido.observacao) {
    obsEl.textContent = pedido.observacao
    obsEl.parentElement.classList.remove('hidden')
  } else {
    obsEl.parentElement.classList.add('hidden')
  }

  $('#detalhe-itens').innerHTML = pedido.itens.map(item => {
    const modsHtml = item.modificadores.length > 0
      ? `<div class="detalhe-item-mods">${item.modificadores.map(m => `${esc(m.nome_snapshot)} (+${formatarPreco(m.preco_snapshot)})`).join(', ')}</div>`
      : ''
    const obsHtml = item.observacao
      ? `<div class="detalhe-item-obs">${esc(item.observacao)}</div>`
      : ''

    return `
      <div class="detalhe-item">
        <div class="detalhe-item-info">
          <span class="detalhe-item-qty">${item.quantidade}x</span>
          <div>
            <strong>${esc(item.nome_snapshot)}</strong>
            ${modsHtml}
            ${obsHtml}
          </div>
        </div>
        <span class="detalhe-item-preco">${formatarPreco(item.subtotal)}</span>
      </div>
    `
  }).join('')

  $('#detalhe-subtotal').textContent = formatarPreco(pedido.subtotal)
  const taxaRow = $('#detalhe-taxa-row')
  if (pedido.taxa_entrega > 0) {
    $('#detalhe-taxa').textContent = formatarPreco(pedido.taxa_entrega)
    taxaRow.classList.remove('hidden')
  } else {
    taxaRow.classList.add('hidden')
  }
  $('#detalhe-total').textContent = formatarPreco(pedido.total)

  $('#modal-pedido').classList.remove('hidden')
}

function fecharModalPedido() {
  $('#modal-pedido').classList.add('hidden')
  pedidoSelecionado = null
}

function imprimirPedido() {
  const p = pedidoSelecionado
  if (!p) return

  /* ── Helpers de formatação ──────────────────────────── */
  const TIPO_TEXTO    = { delivery: 'Delivery', retirada: 'Retirada' }
  const PGTO_TEXTO    = { pix: 'PIX', dinheiro: 'Dinheiro', cartao: 'Cartao' }

  /* ── Largura de impressão (preferência local do dispositivo) ── */
  const largura = localStorage.getItem('impressao_largura') || '80mm'

  /* ── Monta os itens ─────────────────────────────────── */
  const itensHtml = p.itens.map(item => {
    const mods = item.modificadores.length
      ? item.modificadores.map(m =>
          `<div class="mod">  + ${m.nome_snapshot}</div>`
        ).join('')
      : ''
    const obs = item.observacao
      ? `<div class="obs">  Obs: ${item.observacao}</div>`
      : ''
    return `
      <div class="item">
        <div class="item-row">
          <span>${item.quantidade}x ${item.nome_snapshot}</span>
          <span>${formatarPreco(item.subtotal)}</span>
        </div>
        ${mods}${obs}
      </div>`
  }).join('')

  /* ── Monta taxa de entrega (se houver) ──────────────── */
  const taxaHtml = p.taxa_entrega > 0
    ? `<div class="subtotal-row"><span>Taxa de entrega</span><span>${formatarPreco(p.taxa_entrega)}</span></div>`
    : ''

  /* ── Endereço (delivery) ────────────────────────────── */
  const enderecoHtml = p.endereco_entrega
    ? `<div class="campo"><span class="rotulo">ENDERECO</span><span>${p.endereco_entrega}</span></div>`
    : ''

  /* ── Agendamento ────────────────────────────────────── */
  const agendadoHtml = p.agendado_para
    ? `<div class="campo"><span class="rotulo">AGENDADO</span><span>${formatarDataHora(p.agendado_para)}</span></div>`
    : ''

  /* ── Observação ─────────────────────────────────────── */
  const obsHtml = p.observacao
    ? `<div class="campo"><span class="rotulo">OBS</span><span>${p.observacao}</span></div>`
    : ''

  /* ── Troco ──────────────────────────────────────────── */
  const trocoHtml = p.metodo_pagamento === 'dinheiro' && p.troco_para
    ? `<div class="subtotal-row"><span>Troco para</span><span>${formatarPreco(p.troco_para)}</span></div>
       <div class="subtotal-row" style="font-weight:bold"><span>Troco</span><span>${formatarPreco(p.troco_para - p.total)}</span></div>`
    : ''

  /* ── Monta o HTML do cupom ──────────────────────────── */
  const html = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <title>Pedido ${p.numero}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
      font-family: Arial, Helvetica, sans-serif;
      font-variant-numeric: tabular-nums;
      font-size: 12pt;
      font-weight: 500;
      line-height: 1.35;
      width: ${largura};
      margin: 0 auto;
      padding: 4mm 2mm;
      color: #000;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
      -webkit-font-smoothing: none;
      font-smooth: never;
      text-rendering: geometricPrecision;
      font-synthesis: none;
    }

    .centro { text-align: center; }
    .sep { border-top: 1px dashed #000; margin: 6px 0; }

    h1 { font-size: 15pt; font-weight: 700; text-align: center; }
    .subtitulo { font-size: 10pt; text-align: center; margin-bottom: 2px; }

    .pedido-num { font-size: 13pt; font-weight: 700; text-align: center; margin: 4px 0; }
    .data { font-size: 10pt; text-align: center; margin-bottom: 4px; }

    .campo {
      display: flex;
      gap: 6px;
      font-size: 11pt;
      margin: 2px 0;
    }
    .rotulo {
      font-weight: 700;
      min-width: 70px;
    }

    .item { margin: 4px 0; font-size: 11pt; }
    .item-row { display: flex; justify-content: space-between; font-weight: 700; }
    .mod, .obs { font-size: 10pt; padding-left: 8px; }

    .subtotal-row {
      display: flex;
      justify-content: space-between;
      font-size: 11pt;
      margin: 2px 0;
    }
    .total-row {
      display: flex;
      justify-content: space-between;
      font-size: 13pt;
      font-weight: 700;
      margin-top: 4px;
    }

    .status { text-align: center; font-weight: 700; font-size: 12pt; margin: 4px 0; }
    .rodape { text-align: center; font-size: 10pt; margin-top: 8px; }

    @media print {
      body {
        width: ${largura};
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
        -webkit-font-smoothing: none;
        font-smooth: never;
      }
      @page { margin: 2mm; size: ${largura} auto; }
    }
  </style>
</head>
<body>

  <h1>${_nomeLoja || 'Cardápio Digital'}</h1>
  <div class="subtitulo">Cardapio Digital</div>

  <div class="sep"></div>

  <div class="pedido-num">Pedido ${p.numero}</div>
  <div class="data">${formatarDataHora(p.criado_em)}</div>

  <div class="sep"></div>

  <div class="campo"><span class="rotulo">CLIENTE</span><span>${p.cliente.nome}</span></div>
  <div class="campo"><span class="rotulo">FONE</span><span>${p.cliente.telefone}</span></div>
  <div class="campo"><span class="rotulo">TIPO</span><span>${TIPO_TEXTO[p.tipo] || p.tipo}</span></div>
  <div class="campo"><span class="rotulo">PGTO</span><span>${PGTO_TEXTO[p.metodo_pagamento] || p.metodo_pagamento}</span></div>
  ${enderecoHtml}${agendadoHtml}${obsHtml}

  <div class="sep"></div>

  <div style="font-weight:bold;font-size:10pt;margin-bottom:4px;">ITENS:</div>
  ${itensHtml}

  <div class="sep"></div>

  <div class="subtotal-row"><span>Subtotal</span><span>${formatarPreco(p.subtotal)}</span></div>
  ${taxaHtml}
  <div class="total-row"><span>TOTAL</span><span>${formatarPreco(p.total)}</span></div>
  ${trocoHtml}

  <div class="sep"></div>

  <div class="rodape">Documento sem valor fiscal.</div>
  <div class="rodape">${_nomeLoja || 'Menu Livre'}</div>

</body>
</html>`

  /* ── Abre janela, imprime e fecha ───────────────────── */
  const janela = window.open('', '_blank', 'width=400,height=600')
  janela.document.write(html)
  janela.document.close()
  janela.focus()
  janela.onload = () => {
    janela.print()
    janela.close()
  }
}


/* ══════════════════════════════════════════════════════════
   AÇÕES
   ══════════════════════════════════════════════════════════ */

async function avancarStatus(id) {
  const pedido = pedidos.find(p => p.id === id)
  if (!pedido) return

  const proximo = FLUXO_STATUS[pedido.status]
  if (!proximo) return

  try {
    await api.patch(`/api/admin/pedidos/${id}/status`, { status: proximo })
    toast.sucesso(`Pedido ${pedido.numero} → ${STATUS_LABELS[proximo].label}`)
    await carregarPedidos()
  } catch (err) {
    toast.erro(err.message)
  }
}

async function cancelarPedido(id) {
  const pedido = pedidos.find(p => p.id === id)
  if (!pedido) return

  if (!confirm(`Cancelar o pedido ${pedido.numero}?`)) return

  try {
    await api.patch(`/api/admin/pedidos/${id}/status`, { status: 'cancelado' })
    toast.sucesso(`Pedido ${pedido.numero} cancelado.`)
    await carregarPedidos()
  } catch (err) {
    toast.erro(err.message)
  }
}

async function togglePagamento(id) {
  const pedido = pedidos.find(p => p.id === id)
  if (!pedido) return

  const novoStatus = pedido.status_pagamento === 'pago' ? 'pendente' : 'pago'

  try {
    await api.patch(`/api/admin/pedidos/${id}/pagamento`, { status_pagamento: novoStatus })
    toast.sucesso(novoStatus === 'pago' ? 'Pagamento confirmado!' : 'Pagamento desmarcado.')
    await carregarPedidos()
  } catch (err) {
    toast.erro(err.message)
  }
}


/* ══════════════════════════════════════════════════════════
   HELPERS
   ══════════════════════════════════════════════════════════ */

function formatarHora(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('pt-BR', {
    timeZone: 'America/Recife',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatarDataHora(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('pt-BR', {
    timeZone: 'America/Recife',
    day: '2-digit', month: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

function esc(str) {
  if (!str) return ''
  const el = document.createElement('span')
  el.textContent = str
  return el.innerHTML
}