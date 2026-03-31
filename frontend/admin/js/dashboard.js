/* frontend/admin/js/dashboard.js */

/**
 * Dashboard — resumo do dia.
 * Depende de: config.js, auth.js (api, auth), utils.js (toast, formatarPreco, $)
 */

let refreshTimer = null

document.addEventListener('DOMContentLoaded', () => {
  if (!auth.proteger()) return

  setupUsuario()
  setupSidebar()
  carregarResumo()

  /* Atualiza a cada 30 segundos */
  refreshTimer = setInterval(carregarResumo, 30000)
})

function setupUsuario() {
  const usuario = auth.getUsuario()
  $('#header-usuario-nome').textContent = usuario.nome
  const iniciais = usuario.nome.split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase()
  $('#header-usuario-avatar').textContent = iniciais
  $('#welcome-nome').textContent = usuario.nome
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

async function carregarResumo() {
  try {
    const data = await api.get('/api/admin/dashboard/resumo')
    renderResumo(data)
  } catch (err) {
    console.error('Erro ao carregar resumo:', err.message)
  }
}

function renderResumo(data) {
  /* Cards principais */
  $('#stat-pedidos').textContent = data.total_pedidos
  $('#stat-vendas').textContent = formatarPreco(data.total_vendas)
  $('#stat-ticket').textContent = formatarPreco(data.ticket_medio)
  $('#stat-andamento').textContent = data.em_andamento

  /* Por status */
  const statusContainer = $('#resumo-status')
  const statusLabels = {
    pendente:   { label: 'Pendente',   icon: '🕐', classe: 'stat-pendente' },
    confirmado: { label: 'Confirmado', icon: '✅', classe: 'stat-confirmado' },
    em_preparo: { label: 'Preparando', icon: '🔥', classe: 'stat-preparo' },
    pronto:     { label: 'Pronto',     icon: '📦', classe: 'stat-pronto' },
    entregue:   { label: 'Entregue',   icon: '🎉', classe: 'stat-entregue' },
    cancelado:  { label: 'Cancelado',  icon: '❌', classe: 'stat-cancelado' },
  }

  statusContainer.innerHTML = Object.entries(statusLabels).map(([key, info]) => {
    const count = data.por_status[key] || 0
    return `
      <div class="stat-status-item ${info.classe}">
        <span class="stat-status-icon">${info.icon}</span>
        <span class="stat-status-count">${count}</span>
        <span class="stat-status-label">${info.label}</span>
      </div>
    `
  }).join('')

  /* Por tipo */
  const deliveryCount = data.por_tipo?.delivery || 0
  const retiradaCount = data.por_tipo?.retirada || 0
  $('#stat-delivery').textContent = deliveryCount
  $('#stat-retirada').textContent = retiradaCount

  /* Pagamento */
  $('#stat-pagos').textContent = data.pagos
  $('#stat-pendentes-pgto').textContent = data.pendentes_pagamento

  /* Esconder loading */
  $('#dashboard-loading').classList.add('hidden')
  $('#dashboard-conteudo').classList.remove('hidden')
}