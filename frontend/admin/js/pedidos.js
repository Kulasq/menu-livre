/**
 * Gestão de pedidos — listagem, filtros, status, pagamento, histórico, criação admin.
 * A notificação sonora e o FAB de novos pedidos vivem em notificacao-pedidos.js (global).
 * Depende de: config.js, auth.js (api, auth), utils.js (toast, formatarPreco, $)
 */

/* ── Estado ─────────────────────────────────────────────── */

let pedidos = []
let pedidoSelecionado = null
let filtroTipo = ''
let paginaAtual = 1
let autoRefreshTimer = null
let abaAtiva = 'hoje'

// Histórico
let histPagina = 1
const HIST_PAGE_SIZE = 20
let histTotal = 0
let histPedidos = []
let histSelecionados = new Set()   // IDs selecionados com checkbox

// Novo pedido
let cardapioCache = null
let npItens = []        // [{produto, quantidade, modificadores: [], subtotal}]
let npClienteId = null
let npConfigCache = null

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
  delivery: 'Delivery',
  retirada: 'Retirada',
  balcao:   'Balcão',
}

const PAGAMENTO_LABELS = {
  pix:      'PIX',
  dinheiro: 'Dinheiro',
  cartao:   'Cartão',
}


/* ── Inicialização ──────────────────────────────────────── */

let _nomeLoja = ''

document.addEventListener('DOMContentLoaded', () => {
  if (!auth.proteger()) return

  setupUsuario()
  setupSidebar()
  carregarNomeLojaSidebar()
  setupEventos()
  carregarPedidosHoje()

  api.get('/api/admin/configuracoes')
    .then(c => {
      if (c?.nome_loja) _nomeLoja = c.nome_loja
      npConfigCache = c
    })
    .catch(() => {})

  // Polling a cada 5 segundos (apenas na aba Hoje)
  autoRefreshTimer = setInterval(() => {
    if (abaAtiva === 'hoje') carregarPedidosHoje(true)
  }, 5000)
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
  // Abas
  $('#aba-hoje').addEventListener('click', () => mudarAba('hoje'))
  $('#aba-historico').addEventListener('click', () => mudarAba('historico'))

  // Filtro tipo (aba hoje)
  $('#filtro-tipo').addEventListener('change', (e) => {
    filtroTipo = e.target.value
    paginaAtual = 1
    carregarPedidosHoje()
  })

  // Modal detalhe
  $('#modal-pedido-fechar').addEventListener('click', fecharModalPedido)
  $('#modal-pedido-overlay').addEventListener('click', fecharModalPedido)
  $('#btn-deletar-pedido').addEventListener('click', () => {
    if (!pedidoSelecionado) return
    confirmarExcluirPedido(pedidoSelecionado)
  })

  // Modal confirmação
  $('#modal-confirmacao-overlay').addEventListener('click', fecharConfirmacao)
  $('#btn-confirmacao-cancelar').addEventListener('click', fecharConfirmacao)

  // Histórico — dropdown período
  const hoje = dataHoje()
  $('#hist-data-inicio').max = hoje
  $('#hist-data-fim').max = hoje

  $('#hist-periodo').addEventListener('change', () => {
    const periodo = $('#hist-periodo').value
    $('#hist-datas-custom').classList.toggle('hidden', periodo !== 'personalizado')
    if (periodo !== 'personalizado') {
      histPagina = 1
      carregarHistorico()
    }
  })

  // Auto-busca ao mudar tipo no histórico
  $('#hist-filtro-tipo').addEventListener('change', () => {
    histPagina = 1
    carregarHistorico()
  })

  // Datas personalizadas — validação e auto-busca
  $('#hist-data-inicio').addEventListener('change', () => {
    const inicio = $('#hist-data-inicio').value
    const fim = $('#hist-data-fim').value
    // fim não pode ser anterior ao início
    $('#hist-data-fim').min = inicio || ''
    if (fim && inicio && fim < inicio) $('#hist-data-fim').value = inicio
    if (inicio && fim) { histPagina = 1; carregarHistorico() }
  })
  $('#hist-data-fim').addEventListener('change', () => {
    const inicio = $('#hist-data-inicio').value
    const fim = $('#hist-data-fim').value
    // início não pode ser posterior ao fim
    $('#hist-data-inicio').max = fim || hoje
    if (inicio && fim) { histPagina = 1; carregarHistorico() }
  })

  $('#btn-excluir-selecionados').addEventListener('click', excluirSelecionados)
  $('#hist-selecionar-todos').addEventListener('change', (e) => selecionarTodosHist(e.target.checked))
  $('#hist-btn-anterior').addEventListener('click', () => {
    if (histPagina > 1) { histPagina--; carregarHistorico() }
  })
  $('#hist-btn-proxima').addEventListener('click', () => {
    const totalPaginas = Math.ceil(histTotal / HIST_PAGE_SIZE)
    if (histPagina < totalPaginas) { histPagina++; carregarHistorico() }
  })

  // Highlight de pedido disparado pelo FAB global
  window.addEventListener('pedido:highlight', (ev) => destacarCard(ev.detail?.id))

  // Novo pedido — eventos internos
  setupEventosNovoPedido()
}

function mudarAba(aba) {
  abaAtiva = aba
  $('#aba-hoje').classList.toggle('ativa', aba === 'hoje')
  $('#aba-historico').classList.toggle('ativa', aba === 'historico')
  $('#painel-hoje').classList.toggle('hidden', aba !== 'hoje')
  $('#painel-historico').classList.toggle('hidden', aba !== 'historico')

  if (aba === 'historico') {
    if (histPedidos.length === 0) carregarHistorico()
  }
}

function destacarCard(id) {
  if (!id) return
  const card = document.querySelector(`.pedido-card[data-id="${id}"]`)
  if (!card) return
  card.scrollIntoView({ behavior: 'smooth', block: 'center' })
  card.classList.remove('highlight')
  void card.offsetWidth
  card.classList.add('highlight')
  setTimeout(() => card.classList.remove('highlight'), 3500)
}


/* ══════════════════════════════════════════════════════════
   CARREGAR PEDIDOS — HOJE
   ══════════════════════════════════════════════════════════ */

function dataHoje() {
  return new Date().toISOString().slice(0, 10)
}

async function carregarPedidosHoje(silencioso = false) {
  try {
    const hoje = dataHoje()
    let url = `/api/admin/pedidos?data_inicio=${hoje}&data_fim=${hoje}&page=${paginaAtual}`
    if (filtroTipo) url += `&tipo=${filtroTipo}`

    const data = await api.get(url)
    pedidos = data
    renderPedidos()
  } catch (err) {
    if (!silencioso) console.error('Erro ao carregar pedidos:', err.message)
  }
}


/* ══════════════════════════════════════════════════════════
   CARREGAR HISTÓRICO
   ══════════════════════════════════════════════════════════ */

function calcularDatasHistorico() {
  const periodo = $('#hist-periodo').value
  const hoje = new Date()
  const fmt = d => d.toISOString().slice(0, 10)

  if (periodo === 'hoje') {
    return { inicio: fmt(hoje), fim: fmt(hoje) }
  } else if (periodo === 'ontem') {
    const ontem = new Date(hoje); ontem.setDate(hoje.getDate() - 1)
    return { inicio: fmt(ontem), fim: fmt(ontem) }
  } else if (periodo === '7dias') {
    const d = new Date(hoje); d.setDate(hoje.getDate() - 6)
    return { inicio: fmt(d), fim: fmt(hoje) }
  } else if (periodo === '14dias') {
    const d = new Date(hoje); d.setDate(hoje.getDate() - 13)
    return { inicio: fmt(d), fim: fmt(hoje) }
  } else if (periodo === '30dias') {
    const d = new Date(hoje); d.setDate(hoje.getDate() - 29)
    return { inicio: fmt(d), fim: fmt(hoje) }
  } else {
    // personalizado
    return { inicio: $('#hist-data-inicio').value, fim: $('#hist-data-fim').value }
  }
}

async function carregarHistorico() {
  const { inicio: dataInicio, fim: dataFim } = calcularDatasHistorico()
  const tipo = $('#hist-filtro-tipo').value

  if (!dataInicio || !dataFim) {
    toast.aviso('Selecione as datas de início e fim.')
    return
  }

  // Limpa seleção ao recarregar
  histSelecionados.clear()
  atualizarBtnExcluirSelecionados()
  $('#hist-barra-selecao').classList.add('hidden')
  $('#hist-selecionar-todos').checked = false

  $('#hist-loading').classList.remove('hidden')
  $('#hist-lista').innerHTML = ''
  $('#hist-vazio').classList.add('hidden')
  $('#hist-paginacao').classList.add('hidden')

  try {
    let url = `/api/admin/pedidos?data_inicio=${dataInicio}&data_fim=${dataFim}&page=${histPagina}&page_size=${HIST_PAGE_SIZE}`
    if (tipo) url += `&tipo=${tipo}`

    let urlCount = `/api/admin/pedidos/contagem?data_inicio=${dataInicio}&data_fim=${dataFim}`
    if (tipo) urlCount += `&tipo=${tipo}`

    const [data, countData] = await Promise.all([api.get(url), api.get(urlCount)])
    histPedidos = data
    histTotal = countData.total

    $('#hist-loading').classList.add('hidden')

    if (histPedidos.length === 0) {
      $('#hist-vazio').classList.remove('hidden')
      return
    }

    $('#hist-lista').innerHTML = histPedidos.map(p => renderCardPedido(p, true)).join('')
    $('#hist-barra-selecao').classList.remove('hidden')

    // Paginação
    const totalPaginas = Math.ceil(histTotal / HIST_PAGE_SIZE)
    $('#hist-paginacao').classList.toggle('hidden', totalPaginas <= 1)
    if (totalPaginas > 1) {
      $('#hist-pagina-info').textContent = `Página ${histPagina} de ${totalPaginas} (${histTotal} pedidos)`
      $('#hist-btn-anterior').disabled = histPagina === 1
      $('#hist-btn-proxima').disabled = histPagina === totalPaginas
    }
  } catch (err) {
    $('#hist-loading').classList.add('hidden')
    toast.erro('Erro ao carregar histórico: ' + err.message)
  }
}


/* ── Seleção múltipla no histórico ──────────────────────── */

function toggleSelecaoHist(id, checked) {
  if (checked) histSelecionados.add(id)
  else histSelecionados.delete(id)
  // Atualiza o estado do "selecionar todos"
  const total = histPedidos.length
  $('#hist-selecionar-todos').checked = histSelecionados.size === total && total > 0
  $('#hist-selecionar-todos').indeterminate = histSelecionados.size > 0 && histSelecionados.size < total
  atualizarBtnExcluirSelecionados()
}

function selecionarTodosHist(checked) {
  histPedidos.forEach(p => {
    if (checked) histSelecionados.add(p.id)
    else histSelecionados.delete(p.id)
  })
  // Atualiza todos os checkboxes da lista
  document.querySelectorAll('.hist-checkbox[data-id]').forEach(cb => {
    cb.checked = checked
  })
  atualizarBtnExcluirSelecionados()
}

function atualizarBtnExcluirSelecionados() {
  const btn = $('#btn-excluir-selecionados')
  if (!btn) return
  const n = histSelecionados.size
  btn.classList.toggle('hidden', n === 0)
  btn.textContent = `Excluir selecionados (${n})`
}

async function excluirSelecionados() {
  if (!histSelecionados.size) return
  const n = histSelecionados.size
  abrirConfirmacao(
    'Excluir selecionados',
    `Deseja excluir ${n} pedido(s) selecionado(s)? Esta ação não pode ser desfeita.`,
    async () => {
      try {
        await Promise.all([...histSelecionados].map(id =>
          api.delete(`/api/admin/pedidos/${id}`)
        ))
        histSelecionados.clear()
        atualizarBtnExcluirSelecionados()
        await carregarHistorico()
        toast.sucesso(`${n} pedido(s) excluído(s).`)
      } catch {
        toast.erro('Erro ao excluir pedidos selecionados.')
      }
    }
  )
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

function renderCardPedido(pedido, isHistorico = false) {
  const statusInfo = STATUS_LABELS[pedido.status] || STATUS_LABELS.pendente
  const tipoLabel = TIPO_LABELS[pedido.tipo] || pedido.tipo
  const pagLabel = PAGAMENTO_LABELS[pedido.metodo_pagamento] || pedido.metodo_pagamento || '—'
  const horario = isHistorico ? formatarDataHora(pedido.criado_em) : formatarHora(pedido.criado_em)
  const itensResumo = pedido.itens.map(i => `${i.quantidade}x ${esc(i.nome_snapshot)}`).join(', ')
  const proximoStatus = FLUXO_STATUS[pedido.status]

  const agendadoHtml = pedido.agendado_para
    ? `<span class="pedido-agendado">${formatarDataHora(pedido.agendado_para)}</span>`
    : ''

  const pagamentoClass = pedido.status_pagamento === 'pago' ? 'badge-sucesso' : 'badge-aviso'
  const pagamentoLabel = pedido.status_pagamento === 'pago' ? 'Pago' : 'Pendente'

  // Linha de cliente no card
  // Com cliente vinculado → "Nome · telefone" (qualquer tipo)
  // Balcão sem cliente, mas com nome manual → nome simples
  // Sem cliente → tipo do pedido como fallback
  let linhaCliente
  if (pedido.cliente) {
    linhaCliente = pedido.cliente.telefone
      ? `${esc(pedido.cliente.nome)} · ${esc(pedido.cliente.telefone)}`
      : esc(pedido.cliente.nome)
  } else if (pedido.tipo === 'balcao' && pedido.nome_cliente_balcao) {
    linhaCliente = esc(pedido.nome_cliente_balcao)
  } else {
    linhaCliente = tipoLabel
  }

  const cardHtml = `
    <div class="pedido-card" data-id="${pedido.id}" onclick="abrirDetalhe(${pedido.id}, ${isHistorico})">
      <div class="pedido-card-top">
        <div class="pedido-card-info">
          <div class="pedido-card-cliente">${linhaCliente}</div>
          <div class="pedido-card-numero">
            <span>${esc(pedido.numero)}</span>
            <span class="pedido-card-hora">${horario}</span>
          </div>
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

  if (!isHistorico) return cardHtml

  return `
    <div class="hist-card-wrapper">
      <input type="checkbox" class="hist-checkbox" data-id="${pedido.id}"
        onclick="event.stopPropagation()"
        onchange="toggleSelecaoHist(${pedido.id}, this.checked)"
        ${histSelecionados.has(pedido.id) ? 'checked' : ''}
      />
      ${cardHtml}
    </div>
  `
}


/* ══════════════════════════════════════════════════════════
   MODAL DE DETALHE
   ══════════════════════════════════════════════════════════ */

function abrirDetalhe(id, isHistorico = false) {
  const lista = isHistorico ? histPedidos : pedidos
  const pedido = lista.find(p => p.id === id)
  if (!pedido) return
  pedidoSelecionado = pedido

  const statusInfo = STATUS_LABELS[pedido.status] || STATUS_LABELS.pendente
  const tipoLabel = TIPO_LABELS[pedido.tipo] || pedido.tipo
  const pagLabel = PAGAMENTO_LABELS[pedido.metodo_pagamento] || pedido.metodo_pagamento || '—'
  const pagStatus = pedido.status_pagamento === 'pago' ? 'Pago' : 'Pagamento pendente'

  $('#detalhe-numero').textContent = pedido.numero
  $('#detalhe-status').innerHTML = `<span class="badge ${statusInfo.classe}">${statusInfo.icon()} ${statusInfo.label}</span>`
  $('#detalhe-cliente').textContent = pedido.cliente
    ? (pedido.cliente.telefone ? `${pedido.cliente.nome} · ${pedido.cliente.telefone}` : pedido.cliente.nome)
    : '—'
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


/* ══════════════════════════════════════════════════════════
   MODAL CONFIRMAÇÃO
   ══════════════════════════════════════════════════════════ */

let _confirmacaoCallback = null

function abrirConfirmacao(titulo, texto, callback) {
  $('#confirmacao-titulo').textContent = titulo
  $('#confirmacao-texto').textContent = texto
  _confirmacaoCallback = callback
  $('#modal-confirmacao').classList.remove('hidden')
  $('#btn-confirmacao-ok').onclick = async () => {
    fecharConfirmacao()
    await callback()
  }
}

function fecharConfirmacao() {
  $('#modal-confirmacao').classList.add('hidden')
  _confirmacaoCallback = null
}


/* ══════════════════════════════════════════════════════════
   AÇÕES: STATUS, PAGAMENTO, DELETAR
   ══════════════════════════════════════════════════════════ */

async function avancarStatus(id) {
  const pedido = pedidos.find(p => p.id === id)
  if (!pedido) return
  const proximo = FLUXO_STATUS[pedido.status]
  if (!proximo) return
  try {
    await api.patch(`/api/admin/pedidos/${id}/status`, { status: proximo })
    toast.sucesso(`Pedido ${pedido.numero} → ${STATUS_LABELS[proximo].label}`)
    await carregarPedidosHoje()
  } catch (err) {
    toast.erro(err.message)
  }
}

async function cancelarPedido(id) {
  const pedido = pedidos.find(p => p.id === id)
  if (!pedido) return
  abrirConfirmacao(
    'Cancelar pedido',
    `Cancelar o pedido ${pedido.numero}? Esta ação não pode ser desfeita.`,
    async () => {
      try {
        await api.patch(`/api/admin/pedidos/${id}/status`, { status: 'cancelado' })
        toast.sucesso(`Pedido ${pedido.numero} cancelado.`)
        await carregarPedidosHoje()
      } catch (err) {
        toast.erro(err.message)
      }
    }
  )
}

async function togglePagamento(id) {
  const pedido = pedidos.find(p => p.id === id) || histPedidos.find(p => p.id === id)
  if (!pedido) return
  const novoStatus = pedido.status_pagamento === 'pago' ? 'pendente' : 'pago'
  try {
    await api.patch(`/api/admin/pedidos/${id}/pagamento`, { status_pagamento: novoStatus })
    toast.sucesso(novoStatus === 'pago' ? 'Pagamento confirmado!' : 'Pagamento desmarcado.')
    if (abaAtiva === 'hoje') await carregarPedidosHoje()
    else await carregarHistorico()
  } catch (err) {
    toast.erro(err.message)
  }
}

function confirmarExcluirPedido(pedido) {
  abrirConfirmacao(
    'Excluir pedido',
    `Excluir permanentemente o pedido ${pedido.numero}? Esta ação não pode ser desfeita.`,
    async () => {
      try {
        await api.delete(`/api/admin/pedidos/${pedido.id}`)
        toast.sucesso(`Pedido ${pedido.numero} excluído.`)
        fecharModalPedido()
        if (abaAtiva === 'hoje') await carregarPedidosHoje()
        else await carregarHistorico()
      } catch (err) {
        toast.erro(err.message)
      }
    }
  )
}

function confirmarLimpar(periodo) {
  const textos = {
    hoje: 'Excluir TODOS os pedidos de hoje? Esta ação é irreversível.',
    semana: 'Excluir TODOS os pedidos da semana atual? Esta ação é irreversível.',
  }
  const titulos = { hoje: 'Limpar pedidos de hoje', semana: 'Limpar pedidos da semana' }
  abrirConfirmacao(titulos[periodo], textos[periodo], async () => {
    try {
      const res = await api.delete(`/api/admin/pedidos?periodo=${periodo}`)
      toast.sucesso(`${res.deletados} pedido(s) excluído(s).`)
      await carregarPedidosHoje()
    } catch (err) {
      toast.erro(err.message)
    }
  })
}


/* ══════════════════════════════════════════════════════════
   IMPRESSÃO
   ══════════════════════════════════════════════════════════ */

function imprimirPedido() {
  const p = pedidoSelecionado
  if (!p) return

  const TIPO_TEXTO    = { delivery: 'Delivery', retirada: 'Retirada', balcao: 'Balcão' }
  const PGTO_TEXTO    = { pix: 'PIX', dinheiro: 'Dinheiro', cartao: 'Cartao' }
  const largura = localStorage.getItem('impressao_largura') || '80mm'

  const itensHtml = p.itens.map(item => {
    const mods = item.modificadores.length
      ? item.modificadores.map(m => `<div class="mod">+ ${m.nome_snapshot}</div>`).join('')
      : ''
    const obs = item.observacao ? `<div class="obs">Obs: ${item.observacao}</div>` : ''
    return `
      <div class="item">
        <div class="item-row">
          <span class="item-nome">${item.quantidade}x ${item.nome_snapshot}</span>
          <span class="item-preco">${formatarPreco(item.subtotal)}</span>
        </div>
        ${mods}${obs}
      </div>`
  }).join('')

  const taxaHtml = p.taxa_entrega > 0
    ? `<div class="subtotal-row"><span>Taxa de entrega</span><span>${formatarPreco(p.taxa_entrega)}</span></div>`
    : ''
  const enderecoHtml = p.endereco_entrega
    ? `<div class="campo"><span class="rotulo">ENDERECO</span><span>${p.endereco_entrega}</span></div>`
    : ''
  const agendadoHtml = p.agendado_para
    ? `<div class="campo"><span class="rotulo">AGENDADO</span><span>${formatarDataHora(p.agendado_para)}</span></div>`
    : ''
  const obsHtml = p.observacao
    ? `<div class="campo"><span class="rotulo">OBS</span><span>${p.observacao}</span></div>`
    : ''
  const trocoHtml = p.metodo_pagamento === 'dinheiro' && p.troco_para
    ? `<div class="subtotal-row"><span>Troco para</span><span>${formatarPreco(p.troco_para)}</span></div>
       <div class="subtotal-row" style="font-weight:bold"><span>Troco</span><span>${formatarPreco(p.troco_para - p.total)}</span></div>`
    : ''

  // Cliente vinculado tem prioridade; balcão sem cliente usa nome_cliente_balcao ou fallback
  const nomeImpressao = p.cliente?.nome
    ?? (p.tipo === 'balcao' ? (p.nome_cliente_balcao || 'Balcão') : '—')
  const foneImpressao = p.cliente?.telefone ?? null
  const foneHtml = foneImpressao
    ? `<div class="campo"><span class="rotulo">FONE</span><span>${foneImpressao}</span></div>`
    : ''

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
    .sep { border-top: 1px dashed #000; margin: 5px 0; }
    h1 { font-size: 15pt; font-weight: 700; text-align: center; }
    .subtitulo { font-size: 10pt; text-align: center; margin-bottom: 2px; }
    .pedido-num { font-size: 13pt; font-weight: 700; text-align: center; margin: 4px 0; }
    .data { font-size: 10pt; text-align: center; margin-bottom: 4px; }
    .campo { display: flex; gap: 4px; font-size: 11pt; margin: 2px 0; word-break: break-word; }
    .rotulo { font-weight: 700; min-width: 65px; flex-shrink: 0; }
    .campo span:last-child { flex: 1; }
    .item { margin: 4px 0; font-size: 11pt; }
    .item-row { display: flex; gap: 6px; align-items: baseline; }
    .item-nome { flex: 1; word-break: break-word; font-weight: 700; }
    .item-preco { white-space: nowrap; font-weight: 700; }
    .mod, .obs { font-size: 10pt; padding-left: 4px; }
    .subtotal-row { display: flex; justify-content: space-between; font-size: 11pt; margin: 2px 0; }
    .total-row { display: flex; justify-content: space-between; font-size: 13pt; font-weight: 700; margin-top: 4px; }
    .rodape { text-align: center; font-size: 10pt; margin-top: 8px; }
    @media print {
      body { width: ${largura}; -webkit-print-color-adjust: exact; print-color-adjust: exact; -webkit-font-smoothing: none; font-smooth: never; }
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
  <div class="campo"><span class="rotulo">CLIENTE</span><span>${nomeImpressao}</span></div>
  ${foneHtml}
  <div class="campo"><span class="rotulo">TIPO</span><span>${TIPO_TEXTO[p.tipo] || p.tipo}</span></div>
  <div class="campo"><span class="rotulo">PGTO</span><span>${PGTO_TEXTO[p.metodo_pagamento] || '—'}</span></div>
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

  const janela = window.open('', '_blank', 'width=400,height=600')
  janela.document.write(html)
  janela.document.close()
  janela.focus()
  janela.onload = () => { janela.print(); janela.close() }
}


/* ══════════════════════════════════════════════════════════
   PDV — SPLIT-SCREEN NOVO PEDIDO
   ══════════════════════════════════════════════════════════ */

let pdvTipo = 'balcao'       // tipo ativo no PDV
let pdvProdutoAtual = null   // produto sendo configurado no modal

function setupEventosNovoPedido() {
  // Dropdown "+ Novo pedido"
  $('#btn-novo-pedido').addEventListener('click', (e) => {
    e.stopPropagation()
    $('#pdv-tipo-menu').classList.toggle('hidden')
  })
  document.addEventListener('click', () => $('#pdv-tipo-menu').classList.add('hidden'))

  // PDV — fechar
  $('#pdv-fechar').addEventListener('click', fecharPdv)

  // PDV — busca de cliente (debounce no campo nome)
  let _pdvDebounceNome
  $('#pdv-busca-nome').addEventListener('input', () => {
    clearTimeout(_pdvDebounceNome)
    _pdvDebounceNome = setTimeout(() => pdvBuscarCliente(), 300)
  })
  $('#pdv-btn-limpar-cliente').addEventListener('click', pdvLimparCliente)
  // Fechar sugestões ao clicar fora
  document.addEventListener('click', (e) => {
    if (!e.target.closest('#pdv-cliente-section')) pdvFecharSugestoes()
  })

  // PDV — pagamento → troco
  $('#pdv-pagamento').addEventListener('change', () => {
    $('#pdv-troco-grupo').classList.toggle('hidden', $('#pdv-pagamento').value !== 'dinheiro')
  })

  // PDV — criar pedido
  $('#pdv-btn-criar').addEventListener('click', pdvCriarPedido)

  // PDV — busca de produto
  $('#pdv-busca').addEventListener('input', () => pdvRenderProdutos($('#pdv-busca').value))

  // Modal de produto (modificadores)
  $('#pdv-modal-produto-fechar').addEventListener('click', fecharModalProduto)
  $('#pdv-modal-produto-overlay').addEventListener('click', fecharModalProduto)
  $('#pdv-prod-menos').addEventListener('click', () => pdvAjustarQtdProd(-1))
  $('#pdv-prod-mais').addEventListener('click', () => pdvAjustarQtdProd(1))
  $('#pdv-prod-adicionar').addEventListener('click', pdvAdicionarProduto)
}

/* ── Abertura do PDV ───────────────────────────────────── */

async function abrirPdv(tipo) {
  pdvTipo = tipo
  npItens = []
  npClienteId = null

  // Configura badge de tipo
  const labels = { balcao: 'Balcão', retirada: 'Retirada', delivery: 'Delivery' }
  $('#pdv-badge-tipo').textContent = labels[tipo] || tipo

  // Reset campos
  pdvLimparCliente()
  $('#pdv-busca-nome').value = ''
  $('#pdv-endereco').value = ''
  $('#pdv-enderecos-salvos-container')?.remove()
  $('#pdv-endereco-grupo').classList.toggle('hidden', tipo !== 'delivery')
  $('#pdv-pagamento').value = ''
  $('#pdv-troco').value = ''
  $('#pdv-obs').value = ''
  $('#pdv-troco-grupo').classList.add('hidden')

  pdvRenderCarrinho()
  pdvAtualizarTotal()
  $('#pdv-btn-criar').disabled = true

  $('#pdv-overlay').classList.remove('hidden')
  document.body.style.overflow = 'hidden'

  // Carrega cardápio se necessário
  if (!cardapioCache) {
    $('#pdv-categorias').innerHTML = '<div class="pdv-categorias-loading">Carregando...</div>'
    try {
      cardapioCache = await api.get('/api/cardapio')
    } catch (err) {
      toast.erro('Erro ao carregar cardápio: ' + err.message)
      return
    }
  }

  pdvRenderCategorias()
  pdvRenderProdutos('')
}

function fecharPdv() {
  $('#pdv-overlay').classList.add('hidden')
  document.body.style.overflow = ''
}

/* ── Categorias ────────────────────────────────────────── */

function pdvRenderCategorias() {
  const categorias = cardapioCache?.categorias || []
  if (!categorias.length) {
    $('#pdv-categorias').innerHTML = '<div class="pdv-categorias-loading">Sem categorias.</div>'
    return
  }
  $('#pdv-categorias').innerHTML = categorias.map((cat, i) => `
    <button class="pdv-cat-btn ${i === 0 ? 'ativa' : ''}"
      onclick="pdvSelecionarCat(${cat.id}, this)">
      ${esc(cat.nome)}
    </button>
  `).join('')
}

function pdvSelecionarCat(catId, btn) {
  document.querySelectorAll('.pdv-cat-btn').forEach(b => b.classList.remove('ativa'))
  btn.classList.add('ativa')
  // Scroll até a seção da categoria no grid
  const secao = document.querySelector(`.pdv-categoria-titulo[data-cat="${catId}"]`)
  if (secao) secao.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

/* ── Produtos ──────────────────────────────────────────── */

function pdvRenderProdutos(busca = '') {
  const categorias = cardapioCache?.categorias || []
  const q = busca.toLowerCase()
  let html = ''

  for (const cat of categorias) {
    const prods = (cat.produtos || []).filter(p =>
      p.disponivel && (!q || p.nome.toLowerCase().includes(q) || (p.descricao || '').toLowerCase().includes(q))
    )
    if (!prods.length) continue

    html += `<div class="pdv-categoria-titulo" data-cat="${cat.id}">${esc(cat.nome)}</div>`
    for (const prod of prods) {
      const imgHtml = prod.foto_url
        ? `<img src="${CONFIG.API_URL}${esc(prod.foto_url)}" alt="${esc(prod.nome)}" class="pdv-produto-card-img" loading="lazy" />`
        : `<div class="pdv-produto-card-img-placeholder"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width:32px;height:32px"><path stroke-linecap="round" stroke-linejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Zm10.5-11.25h.008v.008h-.008V8.25Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" /></svg></div>`
      html += `
        <div class="pdv-produto-card" onclick="abrirModalProduto(${prod.id})">
          ${imgHtml}
          <div class="pdv-produto-card-body">
            <div class="pdv-produto-card-nome">${esc(prod.nome)}</div>
            <div class="pdv-produto-card-preco">${formatarPreco(prod.preco)}</div>
          </div>
        </div>`
    }
  }

  if (!html) html = '<p style="grid-column:1/-1;color:var(--texto-terc);text-align:center;padding:32px 0">Nenhum produto encontrado.</p>'
  $('#pdv-produtos').innerHTML = html
}

/* ── Modal de produto (modificadores) ─────────────────── */

function abrirModalProduto(produtoId) {
  const categorias = cardapioCache?.categorias || []
  let produto = null
  for (const cat of categorias) {
    produto = (cat.produtos || []).find(p => p.id === produtoId)
    if (produto) break
  }
  if (!produto) return

  pdvProdutoAtual = { ...produto, _qtd: 1, _mods: {} }

  // Imagem
  const img = $('#pdv-prod-img')
  if (produto.foto_url) {
    img.src = CONFIG.API_URL + produto.foto_url
    img.alt = produto.nome
    img.classList.remove('hidden')
  } else {
    img.classList.add('hidden')
  }

  $('#pdv-prod-nome').textContent = produto.nome
  $('#pdv-prod-desc').textContent = produto.descricao || ''
  $('#pdv-prod-desc').classList.toggle('hidden', !produto.descricao)
  $('#pdv-prod-preco').textContent = formatarPreco(produto.preco)
  $('#pdv-prod-qtd').textContent = '1'
  $('#pdv-prod-obs').value = ''

  // Modificadores
  const grupos = produto.grupos_modificadores || []
  let modsHtml = ''
  for (const grupo of grupos) {
    const isRadio = grupo.selecao_maxima === 1
    const tipo = isRadio ? 'radio' : 'checkbox'
    const grupoId = `grp_${grupo.id}`

    let subtitulo = ''
    if (grupo.selecao_minima > 0) subtitulo = `Obrigatório · selecione ${grupo.selecao_minima === grupo.selecao_maxima ? grupo.selecao_minima : `até ${grupo.selecao_maxima}`}`
    else subtitulo = `Opcional · selecione até ${grupo.selecao_maxima}`

    const opcoesHtml = (grupo.modificadores || []).filter(m => m.disponivel).map(mod => `
      <label class="pdv-mod-opcao" onclick="pdvToggleMod(this)">
        <div class="pdv-mod-opcao-info">
          <div class="pdv-mod-opcao-nome">${esc(mod.nome)}</div>
          ${mod.preco_adicional > 0 ? `<div class="pdv-mod-opcao-preco">+ ${formatarPreco(mod.preco_adicional)}</div>` : ''}
        </div>
        <input type="${tipo}" name="${grupoId}" value="${mod.id}"
          data-preco="${mod.preco_adicional}" data-nome="${esc(mod.nome)}"
          data-grupo="${grupo.id}" data-max="${grupo.selecao_maxima}"
          onchange="pdvAtualizarPrecoBtn()" />
      </label>`).join('')

    modsHtml += `
      <div class="pdv-mod-grupo">
        <div class="pdv-mod-grupo-titulo">${esc(grupo.nome)}</div>
        <div class="pdv-mod-grupo-subtitulo">${subtitulo}</div>
        ${opcoesHtml}
      </div>`
  }
  $('#pdv-prod-modificadores').innerHTML = modsHtml

  pdvAtualizarPrecoBtn()
  $('#pdv-modal-produto').classList.remove('hidden')
}

function fecharModalProduto() {
  $('#pdv-modal-produto').classList.add('hidden')
  pdvProdutoAtual = null
}

function pdvToggleMod(label) {
  label.classList.toggle('selecionada', label.querySelector('input')?.checked)
}

function pdvAjustarQtdProd(delta) {
  if (!pdvProdutoAtual) return
  pdvProdutoAtual._qtd = Math.max(1, pdvProdutoAtual._qtd + delta)
  $('#pdv-prod-qtd').textContent = pdvProdutoAtual._qtd
  pdvAtualizarPrecoBtn()
}

function pdvAtualizarPrecoBtn() {
  if (!pdvProdutoAtual) return
  let preco = pdvProdutoAtual.preco
  document.querySelectorAll('#pdv-prod-modificadores input:checked').forEach(inp => {
    preco += parseFloat(inp.dataset.preco || 0)
  })
  preco *= (pdvProdutoAtual._qtd || 1)
  $('#pdv-prod-preco-btn').textContent = formatarPreco(preco)
}

function pdvAdicionarProduto() {
  if (!pdvProdutoAtual) return

  const mods = []
  document.querySelectorAll('#pdv-prod-modificadores input:checked').forEach(inp => {
    mods.push({
      modificador_id: parseInt(inp.value),
      nome_snapshot: inp.dataset.nome,
      preco_snapshot: parseFloat(inp.dataset.preco || 0),
    })
  })

  let precoUni = pdvProdutoAtual.preco + mods.reduce((s, m) => s + m.preco_snapshot, 0)
  const obs = $('#pdv-prod-obs').value.trim() || null

  npItens.push({
    produto: pdvProdutoAtual,
    quantidade: pdvProdutoAtual._qtd,
    modificadores: mods,
    observacao: obs,
    subtotal: precoUni * pdvProdutoAtual._qtd,
  })

  fecharModalProduto()
  pdvRenderCarrinho()
  pdvAtualizarTotal()
}

/* ── Carrinho ──────────────────────────────────────────── */

function pdvRenderCarrinho() {
  const lista = $('#pdv-itens-lista')
  if (npItens.length === 0) {
    lista.innerHTML = '<p class="pdv-vazio-itens">Nenhum item adicionado.</p>'
    $('#pdv-btn-criar').disabled = true
    return
  }

  lista.innerHTML = npItens.map((item, i) => {
    const modsHtml = item.modificadores.length
      ? `<div class="pdv-item-mods">${item.modificadores.map(m => esc(m.nome_snapshot)).join(', ')}</div>`
      : ''
    const obsHtml = item.observacao ? `<div class="pdv-item-mods" style="font-style:italic">Obs: ${esc(item.observacao)}</div>` : ''
    return `
      <div class="pdv-item-linha">
        <div class="pdv-item-info">
          <div class="pdv-item-nome">${esc(item.produto.nome)}</div>
          ${modsHtml}${obsHtml}
          <div class="pdv-item-preco">${formatarPreco(item.subtotal)}</div>
        </div>
        <div class="pdv-item-controles">
          <button type="button" class="pdv-qtd-btn" onclick="pdvAlterarQtd(${i}, -1)">−</button>
          <span class="pdv-item-qtd">${item.quantidade}</span>
          <button type="button" class="pdv-qtd-btn" onclick="pdvAlterarQtd(${i}, 1)">+</button>
          <button type="button" class="pdv-qtd-btn" style="border-color:transparent;color:var(--erro,#ef4444)" onclick="pdvRemoverItem(${i})" title="Remover">${icons.x_circulo}</button>
        </div>
      </div>`
  }).join('')

  $('#pdv-btn-criar').disabled = false
}

function pdvAlterarQtd(i, delta) {
  npItens[i].quantidade = Math.max(1, npItens[i].quantidade + delta)
  const precoUni = npItens[i].subtotal / (npItens[i].quantidade - delta)
  npItens[i].subtotal = precoUni * npItens[i].quantidade
  pdvRenderCarrinho()
  pdvAtualizarTotal()
}

function pdvRemoverItem(i) {
  npItens.splice(i, 1)
  pdvRenderCarrinho()
  pdvAtualizarTotal()
}

function pdvAtualizarTotal() {
  const subtotal = npItens.reduce((s, i) => s + i.subtotal, 0)
  const taxa = (pdvTipo === 'delivery' && npConfigCache?.taxa_entrega) ? npConfigCache.taxa_entrega : 0
  const total = subtotal + taxa
  $('#pdv-taxa-linha').classList.toggle('hidden', taxa === 0)
  $('#pdv-taxa').textContent = formatarPreco(taxa)
  $('#pdv-total').textContent = formatarPreco(total)
}

/* ── Buscar cliente no PDV ─────────────────────────────── */

function pdvFecharSugestoes() {
  $('#pdv-sugestoes').classList.add('hidden')
  $('#pdv-sugestoes').innerHTML = ''
}

function pdvLimparCliente() {
  npClienteId = null
  $('#pdv-cliente-selecionado').classList.add('hidden')
  $('#pdv-novo-cliente-campos').classList.add('hidden')
  document.getElementById('pdv-enderecos-salvos-container')?.remove()
  pdvFecharSugestoes()
}

function pdvSelecionarCliente(cliente) {
  npClienteId = cliente.id
  $('#pdv-busca-nome').value = cliente.nome
  const info = cliente.telefone ? `✓ ${cliente.nome} — ${cliente.telefone}` : `✓ ${cliente.nome}`
  $('#pdv-cliente-selecionado-info').textContent = info
  $('#pdv-cliente-selecionado').classList.remove('hidden')
  $('#pdv-novo-cliente-campos').classList.add('hidden')
  pdvFecharSugestoes()
  if (pdvTipo === 'delivery') pdvCarregarEnderecos(cliente.id)
}

async function pdvCarregarEnderecos(clienteId) {
  document.getElementById('pdv-enderecos-salvos-container')?.remove()
  try {
    const enderecos = await api.get(`/api/admin/clientes/${clienteId}/enderecos`)
    if (!enderecos || enderecos.length === 0) return

    const grupoEndereco = $('#pdv-endereco-grupo')
    const container = document.createElement('div')
    container.id = 'pdv-enderecos-salvos-container'
    container.className = 'pdv-enderecos-salvos'

    const titulo = document.createElement('p')
    titulo.className = 'pdv-enderecos-titulo'
    titulo.textContent = 'Endereços salvos:'
    container.appendChild(titulo)

    enderecos.forEach((e, idx) => {
      const radioId = `pdv-end-${idx}`
      const item = document.createElement('div')
      item.className = 'pdv-endereco-item'

      const radio = document.createElement('input')
      radio.type = 'radio'
      radio.name = 'pdv-endereco-salvo'
      radio.id = radioId
      radio.className = 'pdv-endereco-radio'
      radio.value = e.endereco
      radio.addEventListener('change', () => { $('#pdv-endereco').value = e.endereco })

      const label = document.createElement('label')
      label.htmlFor = radioId
      label.className = 'pdv-endereco-texto'
      label.textContent = e.endereco

      const del = document.createElement('button')
      del.type = 'button'
      del.className = 'pdv-endereco-del'
      del.setAttribute('aria-label', 'Remover endereço')
      del.textContent = '✕'
      del.addEventListener('click', async () => {
        try {
          await api.delete(`/api/admin/clientes/${clienteId}/enderecos/${e.id}`)
          if (radio.checked) $('#pdv-endereco').value = ''
          item.remove()
          if (!container.querySelector('.pdv-endereco-item')) container.remove()
        } catch { toast.erro('Erro ao remover endereço.') }
      })

      item.append(radio, label, del)
      container.appendChild(item)
    })

    grupoEndereco.insertBefore(container, grupoEndereco.firstChild)
  } catch { /* silencioso */ }
}

async function pdvBuscarCliente() {
  const q = $('#pdv-busca-nome').value.trim()
  if (!q) { pdvFecharSugestoes(); return }

  try {
    const res = await api.get(`/api/admin/clientes/lista?q=${encodeURIComponent(q)}&page_size=5`)
    const lista = res?.clientes ?? []
    const sug = $('#pdv-sugestoes')

    if (lista.length === 0) {
      sug.innerHTML = `<div class="pdv-sugestao-vazio">Nenhum cliente encontrado — será cadastrado com este nome.</div>`
      sug.classList.remove('hidden')
      npClienteId = null
      $('#pdv-cliente-selecionado').classList.add('hidden')
      $('#pdv-novo-cliente-campos').classList.remove('hidden')
      return
    }

    sug.innerHTML = lista.map(c =>
      `<div class="pdv-sugestao-item" data-id="${c.id}" data-nome="${esc(c.nome)}" data-tel="${esc(c.telefone ?? '')}">
        <span class="pdv-sugestao-nome">${esc(c.nome)}</span>
        <span class="pdv-sugestao-tel">${esc(c.telefone ?? '—')}</span>
      </div>`
    ).join('')
    sug.classList.remove('hidden')

    sug.querySelectorAll('.pdv-sugestao-item').forEach(item => {
      item.addEventListener('click', () => {
        pdvSelecionarCliente({ id: +item.dataset.id, nome: item.dataset.nome, telefone: item.dataset.tel || null })
      })
    })
  } catch { pdvFecharSugestoes() }
}

/* ── Criar pedido ─────────────────────────────────────── */

async function pdvCriarPedido() {
  if (npItens.length === 0) { toast.aviso('Adicione pelo menos um item.'); return }

  const endereco = $('#pdv-endereco').value.trim()
  if (pdvTipo === 'delivery' && !endereco) { toast.aviso('Informe o endereço de entrega.'); return }

  const pagamento = $('#pdv-pagamento').value
  const troco = $('#pdv-troco').value ? parseFloat($('#pdv-troco').value) : null
  const obs = $('#pdv-obs').value.trim()
  const nomeBusca = $('#pdv-busca-nome').value.trim()

  const itens = npItens.map(i => ({
    produto_id: i.produto.id,
    quantidade: i.quantidade,
    modificadores: i.modificadores.map(m => ({ modificador_id: m.modificador_id })),
    observacao: i.observacao || null,
  }))

  const payload = {
    tipo: pdvTipo,
    endereco_entrega: pdvTipo === 'delivery' ? endereco : null,
    metodo_pagamento: pagamento || null,
    troco_para: pagamento === 'dinheiro' ? troco : null,
    observacao: obs || null,
    itens,
    cliente_id:   npClienteId || null,
    cliente_nome: (!npClienteId && nomeBusca) ? nomeBusca : null,
  }

  const btn = $('#pdv-btn-criar')
  btn.disabled = true
  btn.textContent = 'Criando...'

  try {
    const res = await api.post('/api/admin/pedidos', payload)
    // Auto-confirmar: pedido criado pelo admin já está ciente, não precisa notificar
    await api.patch(`/api/admin/pedidos/${res.pedido.id}/status`, { status: 'confirmado' })
    toast.sucesso(`Pedido ${res.pedido.numero} criado!`)
    fecharPdv()
    await carregarPedidosHoje()
  } catch (err) {
    toast.erro(err.message || 'Erro ao criar pedido.')
    btn.disabled = false
  } finally {
    btn.textContent = 'Criar pedido'
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
