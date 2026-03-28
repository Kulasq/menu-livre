/* frontend/admin/js/pedidos.js */

/**
 * Gestão de pedidos — listagem, filtros, status, pagamento.
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
  pendente:   { label: 'Pendente',    classe: 'badge-aviso',   icon: '🕐' },
  confirmado: { label: 'Confirmado',  classe: 'badge-info',    icon: '✅' },
  em_preparo: { label: 'Preparando',  classe: 'badge-preparo', icon: '🔥' },
  pronto:     { label: 'Pronto',      classe: 'badge-sucesso', icon: '📦' },
  entregue:   { label: 'Entregue',    classe: 'badge-entregue',icon: '🎉' },
  cancelado:  { label: 'Cancelado',   classe: 'badge-erro',    icon: '❌' },
}

const FLUXO_STATUS = {
  pendente:   'confirmado',
  confirmado: 'em_preparo',
  em_preparo: 'pronto',
  pronto:     'entregue',
}

const TIPO_LABELS = {
  delivery:  '🛵 Delivery',
  retirada:  '🏪 Retirada',
}

const PAGAMENTO_LABELS = {
  pix:      '💳 PIX',
  dinheiro: '💵 Dinheiro',
  cartao:   '💳 Cartão',
}


/* ── Inicialização ──────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {
  if (!auth.proteger()) return

  setupUsuario()
  setupSidebar()
  setupEventos()
  carregarPedidos()

  /* Auto-refresh a cada 30 segundos */
  autoRefreshTimer = setInterval(carregarPedidos, 30000)
})

function setupUsuario() {
  const usuario = auth.getUsuario()
  $('#header-usuario-nome').textContent = usuario.nome
  const iniciais = usuario.nome.split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase()
  $('#header-usuario-avatar').textContent = iniciais
}

function setupSidebar() {
  $('#btn-logout').addEventListener('click', () => auth.logout())

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
}


/* ── Carregar pedidos ───────────────────────────────────── */

async function carregarPedidos() {
  try {
    let url = `/api/admin/pedidos?page=${paginaAtual}`
    if (filtroStatus) url += `&status=${filtroStatus}`
    if (filtroTipo) url += `&tipo=${filtroTipo}`

    const data = await api.get(url)
    pedidos = data
    renderPedidos()
  } catch (err) {
    toast.erro('Erro ao carregar pedidos: ' + err.message)
  }
}


/* ── Renderização ───────────────────────────────────────── */

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
}

function renderCardPedido(pedido) {
  const statusInfo = STATUS_LABELS[pedido.status] || STATUS_LABELS.pendente
  const tipoLabel = TIPO_LABELS[pedido.tipo] || pedido.tipo
  const pagLabel = PAGAMENTO_LABELS[pedido.metodo_pagamento] || pedido.metodo_pagamento || '—'
  const horario = formatarHora(pedido.criado_em)
  const itensResumo = pedido.itens.map(i => `${i.quantidade}x ${esc(i.nome_snapshot)}`).join(', ')
  const proximoStatus = FLUXO_STATUS[pedido.status]

  const agendadoHtml = pedido.agendado_para
    ? `<span class="pedido-agendado">📅 ${formatarDataHora(pedido.agendado_para)}</span>`
    : ''

  const pagamentoClass = pedido.status_pagamento === 'pago' ? 'badge-sucesso' : 'badge-aviso'
  const pagamentoLabel = pedido.status_pagamento === 'pago' ? '💰 Pago' : '⏳ Pendente'

  return `
    <div class="pedido-card" onclick="abrirDetalhe(${pedido.id})">
      <div class="pedido-card-top">
        <div class="pedido-card-info">
          <div class="pedido-card-numero">
            <strong>${esc(pedido.numero)}</strong>
            <span class="pedido-card-hora">${horario}</span>
          </div>
          <div class="pedido-card-cliente">${esc(pedido.cliente.nome)} · ${esc(pedido.cliente.telefone)}</div>
        </div>
        <span class="badge ${statusInfo.classe}">${statusInfo.icon} ${statusInfo.label}</span>
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
              ${STATUS_LABELS[proximoStatus]?.icon} ${STATUS_LABELS[proximoStatus]?.label}
            </button>
          ` : ''}
          ${pedido.status !== 'cancelado' && pedido.status !== 'entregue' ? `
            <button class="btn btn-danger btn-sm" onclick="cancelarPedido(${pedido.id})" title="Cancelar pedido">
              ❌
            </button>
          ` : ''}
        </div>
      </div>
    </div>
  `
}


/* ── Modal de detalhe ───────────────────────────────────── */

function abrirDetalhe(id) {
  const pedido = pedidos.find(p => p.id === id)
  if (!pedido) return
  pedidoSelecionado = pedido

  const statusInfo = STATUS_LABELS[pedido.status] || STATUS_LABELS.pendente
  const tipoLabel = TIPO_LABELS[pedido.tipo] || pedido.tipo
  const pagLabel = PAGAMENTO_LABELS[pedido.metodo_pagamento] || pedido.metodo_pagamento || '—'
  const pagStatus = pedido.status_pagamento === 'pago' ? '💰 Pago' : '⏳ Pagamento pendente'

  $('#detalhe-numero').textContent = pedido.numero
  $('#detalhe-status').innerHTML = `<span class="badge ${statusInfo.classe}">${statusInfo.icon} ${statusInfo.label}</span>`
  $('#detalhe-cliente').textContent = `${pedido.cliente.nome} · ${pedido.cliente.telefone}`
  $('#detalhe-tipo').textContent = tipoLabel
  $('#detalhe-horario').textContent = formatarDataHora(pedido.criado_em)
  $('#detalhe-pagamento').textContent = `${pagLabel} — ${pagStatus}`

  /* Endereço */
  const enderecoEl = $('#detalhe-endereco')
  if (pedido.endereco_entrega) {
    enderecoEl.textContent = pedido.endereco_entrega
    enderecoEl.parentElement.classList.remove('hidden')
  } else {
    enderecoEl.parentElement.classList.add('hidden')
  }

  /* Agendamento */
  const agendaEl = $('#detalhe-agendado')
  if (pedido.agendado_para) {
    agendaEl.textContent = formatarDataHora(pedido.agendado_para)
    agendaEl.parentElement.classList.remove('hidden')
  } else {
    agendaEl.parentElement.classList.add('hidden')
  }

  /* Observação */
  const obsEl = $('#detalhe-obs')
  if (pedido.observacao) {
    obsEl.textContent = pedido.observacao
    obsEl.parentElement.classList.remove('hidden')
  } else {
    obsEl.parentElement.classList.add('hidden')
  }

  /* Itens */
  $('#detalhe-itens').innerHTML = pedido.itens.map(item => {
    const modsHtml = item.modificadores.length > 0
      ? `<div class="detalhe-item-mods">${item.modificadores.map(m => `${esc(m.nome_snapshot)} (+${formatarPreco(m.preco_snapshot)})`).join(', ')}</div>`
      : ''
    const obsHtml = item.observacao
      ? `<div class="detalhe-item-obs">💬 ${esc(item.observacao)}</div>`
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

  /* Totais */
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


/* ── Ações ──────────────────────────────────────────────── */

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


/* ── Helpers ────────────────────────────────────────────── */

function formatarHora(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

function formatarDataHora(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('pt-BR', {
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