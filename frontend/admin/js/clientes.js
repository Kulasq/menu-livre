/* frontend/admin/js/clientes.js */
;(function () {
  'use strict'

  // ── Estado ────────────────────────────────────────────────────────────────

  const estado = {
    q: '',
    segmento: '',
    ordenar: 'ultimo_pedido',
    page: 1,
    pageSize: 30,
    total: 0,
    drawerClienteId: null,
    drawerAba: 'pedidos',
    debounceTimer: null,
  }

  // id do cliente aguardando confirmação de exclusão
  let _excluirClienteId = null

  // ── Segmentos: labels e cores ─────────────────────────────────────────────

  const SEGMENTOS = {
    campeao:  { label: 'Campeão',  cls: 'seg-campeao'  },
    leal:     { label: 'Leal',     cls: 'seg-leal'     },
    novo:     { label: 'Novo',     cls: 'seg-novo'     },
    comum:    { label: 'Comum',    cls: 'seg-comum'    },
    em_risco: { label: 'Em risco', cls: 'seg-em-risco' },
    inativo:  { label: 'Inativo',  cls: 'seg-inativo'  },
  }

  function badgeSegmento(seg) {
    const s = SEGMENTOS[seg] || { label: seg, cls: 'seg-comum' }
    return `<span class="clientes-badge ${s.cls}">${s.label}</span>`
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  function inicialAvatar(nome) {
    return (nome || '?').charAt(0).toUpperCase()
  }

  function formatarTelefoneExibicao(tel) {
    if (!tel) return '—'
    const d = tel.replace(/\D/g, '')
    if (!d || /^0+$/.test(d)) return '—'
    if (d.length === 11) return `(${d.slice(0,2)}) ${d.slice(2,7)}-${d.slice(7)}`
    if (d.length === 10) return `(${d.slice(0,2)}) ${d.slice(2,6)}-${d.slice(6)}`
    return tel
  }

  function urlWhatsApp(telefone) {
    if (!telefone) return null
    const num = telefone.replace(/\D/g, '')
    const completo = num.startsWith('55') ? num : `55${num}`
    return `https://api.whatsapp.com/send/?phone=${completo}`
  }

  function formatarDataHora(iso) {
    if (!iso) return '—'
    const d = new Date(iso)
    return d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  function statusPedidoLabel(status) {
    const mapa = {
      pendente: 'Pendente', preparando: 'Preparando', pronto: 'Pronto',
      entregue: 'Entregue', cancelado: 'Cancelado', agendado: 'Agendado',
    }
    return mapa[status] || status
  }

  function statusPedidoCls(status) {
    const mapa = {
      pendente: 'status-pendente', preparando: 'status-preparando', pronto: 'status-pronto',
      entregue: 'status-entregue', cancelado: 'status-cancelado', agendado: 'status-agendado',
    }
    return mapa[status] || ''
  }

  // ── Listagem ──────────────────────────────────────────────────────────────

  async function carregarLista() {
    const tbody = document.getElementById('clientes-tbody')
    tbody.innerHTML = '<tr><td colspan="7" class="clientes-estado">Carregando…</td></tr>'

    const params = new URLSearchParams({
      page: estado.page,
      page_size: estado.pageSize,
      ordenar: estado.ordenar,
    })
    if (estado.q)        params.set('q', estado.q)
    if (estado.segmento) params.set('segmento', estado.segmento)

    try {
      const data = await api.get(`/api/admin/clientes/lista?${params}`)
      estado.total = data.total
      renderTabela(data.clientes)
      renderPaginacao()
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" class="clientes-estado clientes-estado-erro">Erro ao carregar clientes. Tente novamente.</td></tr>`
      console.error(err)
    }
  }

  const SVG_TRES_PONTOS = `<svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M12 6a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Zm0 4.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Zm1.5 7.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Z"/></svg>`
  const SVG_WHATSAPP = `<svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14" aria-hidden="true"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413Z"/></svg>`
  const SVG_LAPIZ = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="14" height="14" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125" /></svg>`
  const SVG_LIXO = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="14" height="14" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" /></svg>`
  const SVG_X_MINI = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" width="14" height="14" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>`

  function renderTabela(clientes) {
    const tbody = document.getElementById('clientes-tbody')

    if (!clientes.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="clientes-estado">Nenhum cliente encontrado.</td></tr>'
      return
    }

    tbody.innerHTML = clientes.map(c => `
      <tr class="clientes-linha" data-id="${c.id}" data-nome="${c.nome.replace(/"/g, '&quot;')}" data-telefone="${c.telefone}" tabindex="0" role="button" aria-label="Ver detalhes de ${c.nome}">
        <td class="clientes-td-nome">
          <div class="clientes-avatar-mini">${inicialAvatar(c.nome)}</div>
          <span>${c.nome}</span>
        </td>
        <td>${formatarTelefoneExibicao(c.telefone)}</td>
        <td class="clientes-td-num">${c.total_pedidos}</td>
        <td class="clientes-td-num">${formatarPreco(c.total_gasto)}</td>
        <td>${formatarData(c.ultimo_pedido)}</td>
        <td>${badgeSegmento(c.segmento)}</td>
        <td class="clientes-td-acoes">
          <div class="kebab-wrap">
            <button class="btn-kebab" type="button" title="Opções" aria-label="Opções de ${c.nome}" aria-haspopup="true" aria-expanded="false">
              ${SVG_TRES_PONTOS}
            </button>
            <div class="kebab-dropdown" hidden role="menu">
              ${c.telefone ? `<a class="kebab-item" href="${urlWhatsApp(c.telefone)}" target="_blank" rel="noopener noreferrer" role="menuitem">${SVG_WHATSAPP} WhatsApp</a>` : ''}
              <button class="kebab-item" type="button" data-action="editar" role="menuitem">
                ${SVG_LAPIZ} Editar contato
              </button>
              <button class="kebab-item kebab-item-perigo" type="button" data-action="excluir" role="menuitem">
                ${SVG_LIXO} Excluir contato
              </button>
            </div>
          </div>
        </td>
      </tr>
    `).join('')

    tbody.querySelectorAll('.clientes-linha').forEach(tr => {
      const id = Number(tr.dataset.id)
      const nome = tr.dataset.nome
      const kebabBtn = tr.querySelector('.btn-kebab')
      const kebabDrop = tr.querySelector('.kebab-dropdown')

      // Clique na linha abre drawer (exceto na coluna de ações)
      tr.addEventListener('click', e => {
        if (e.target.closest('.clientes-td-acoes')) return
        abrirDrawer(id)
      })
      tr.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') {
          if (!e.target.closest('.clientes-td-acoes')) abrirDrawer(id)
        }
      })

      // Kebab: abre/fecha dropdown com posição calculada (evita corte por overflow)
      kebabBtn.addEventListener('click', e => {
        e.stopPropagation()
        const estaAberto = !kebabDrop.hidden
        _fecharTodosDropdowns()
        if (!estaAberto) {
          const rect = kebabBtn.getBoundingClientRect()
          kebabDrop.style.top  = (rect.bottom + 4) + 'px'
          kebabDrop.style.right = (window.innerWidth - rect.right) + 'px'
          kebabDrop.style.left = 'auto'
          kebabDrop.hidden = false
          kebabBtn.setAttribute('aria-expanded', 'true')
        }
      })

      // Itens do dropdown
      tr.querySelector('[data-action="editar"]').addEventListener('click', e => {
        e.stopPropagation()
        _fecharTodosDropdowns()
        abrirEdicao(id)
      })

      tr.querySelector('[data-action="excluir"]').addEventListener('click', e => {
        e.stopPropagation()
        _fecharTodosDropdowns()
        abrirModalExcluir(id, nome)
      })
    })
  }

  function _fecharTodosDropdowns() {
    document.querySelectorAll('.kebab-dropdown:not([hidden])').forEach(d => {
      d.hidden = true
      const btn = d.previousElementSibling
      if (btn) btn.setAttribute('aria-expanded', 'false')
    })
  }

  function renderPaginacao() {
    const totalPags = Math.ceil(estado.total / estado.pageSize) || 1
    const paginacao = document.getElementById('clientes-paginacao')
    const info = document.getElementById('clientes-pag-info')
    const btnAnterior = document.getElementById('clientes-pag-anterior')
    const btnProxima = document.getElementById('clientes-pag-proxima')

    paginacao.hidden = estado.total <= estado.pageSize

    info.textContent = `Página ${estado.page} de ${totalPags} · ${estado.total} cliente${estado.total !== 1 ? 's' : ''}`
    btnAnterior.disabled = estado.page <= 1
    btnProxima.disabled = estado.page >= totalPags
  }

  // ── Drawer ────────────────────────────────────────────────────────────────

  function _setModoDrawer(modo) {
    document.getElementById('drawer-header-view').hidden = (modo !== 'view')
    document.getElementById('drawer-view-area').hidden   = (modo !== 'view')
    document.getElementById('drawer-header-edit').hidden = (modo !== 'edit')
    document.getElementById('drawer-edit-area').hidden   = (modo !== 'edit')
  }

  function _abrirDrawerContainer() {
    const drawer = document.getElementById('clientes-drawer')
    const overlay = document.getElementById('drawer-overlay')
    drawer.hidden = false
    overlay.hidden = false
    drawer.removeAttribute('aria-hidden')
    overlay.removeAttribute('aria-hidden')
    drawer.classList.add('aberto')
  }

  async function abrirDrawer(clienteId) {
    estado.drawerClienteId = clienteId
    estado.drawerAba = 'pedidos'

    document.getElementById('drawer-nome').textContent = '…'
    document.getElementById('drawer-telefone').textContent = ''
    document.getElementById('drawer-avatar').textContent = '…'
    document.getElementById('drawer-stats').innerHTML = ''
    document.getElementById('drawer-conteudo').innerHTML = '<div class="clientes-estado">Carregando…</div>'
    _setAbaAtiva('pedidos')
    _setModoDrawer('view')
    _abrirDrawerContainer()

    try {
      const [cliente, pedidos, enderecos] = await Promise.all([
        api.get(`/api/admin/clientes/${clienteId}`),
        api.get(`/api/admin/clientes/${clienteId}/pedidos?limite=50`),
        api.get(`/api/admin/clientes/${clienteId}/enderecos`),
      ])

      preencherDrawerHeader(cliente)
      preencherStats(cliente)
      _dadosDrawer.pedidos = pedidos
      _dadosDrawer.enderecos = enderecos
      _renderizarAba('pedidos', pedidos, enderecos)
    } catch (err) {
      document.getElementById('drawer-conteudo').innerHTML =
        '<div class="clientes-estado clientes-estado-erro">Erro ao carregar detalhes.</div>'
      console.error(err)
    }
  }

  // Abre o drawer em modo edição para um cliente existente
  async function abrirEdicao(clienteId) {
    estado.drawerClienteId = clienteId

    document.getElementById('drawer-edit-titulo').textContent = 'Editar contato'
    document.getElementById('drawer-avatar-edit').textContent = '…'
    document.getElementById('edit-nome').value = ''
    document.getElementById('edit-telefone').value = ''
    document.getElementById('edit-enderecos-lista').innerHTML = '<div class="clientes-estado" style="font-size:.85rem">Carregando…</div>'
    document.getElementById('drawer-edit-enderecos-section').hidden = false
    _setModoDrawer('edit')
    _abrirDrawerContainer()

    try {
      const [cliente, enderecos] = await Promise.all([
        api.get(`/api/admin/clientes/${clienteId}`),
        api.get(`/api/admin/clientes/${clienteId}/enderecos`),
      ])

      // Popula cabeçalho de visualização (para o cancelar funcionar)
      preencherDrawerHeader(cliente)
      preencherStats(cliente)
      _dadosDrawer.enderecos = enderecos
      _dadosDrawer.pedidos = null

      // Popula formulário
      document.getElementById('drawer-avatar-edit').textContent = inicialAvatar(cliente.nome)
      document.getElementById('edit-nome').value = cliente.nome
      document.getElementById('edit-telefone').value = formatarTelefoneExibicao(cliente.telefone)
      renderEditEnderecos(enderecos)
    } catch (err) {
      document.getElementById('edit-enderecos-lista').innerHTML =
        '<div class="clientes-estado clientes-estado-erro" style="font-size:.85rem">Erro ao carregar dados.</div>'
      console.error(err)
    }
  }

  // Abre o drawer em modo criação (campos vazios, sem endereços)
  function abrirNovoCliente() {
    estado.drawerClienteId = null
    _dadosDrawer.pedidos = null
    _dadosDrawer.enderecos = null

    document.getElementById('drawer-edit-titulo').textContent = 'Novo cliente'
    document.getElementById('drawer-avatar-edit').textContent = '+'
    document.getElementById('edit-nome').value = ''
    document.getElementById('edit-telefone').value = ''
    document.getElementById('drawer-edit-enderecos-section').hidden = true

    _setModoDrawer('edit')
    _abrirDrawerContainer()
    setTimeout(() => document.getElementById('edit-nome').focus(), 80)
  }

  function fecharDrawer() {
    const drawer = document.getElementById('clientes-drawer')
    const overlay = document.getElementById('drawer-overlay')
    drawer.classList.remove('aberto')
    setTimeout(() => {
      drawer.hidden = true
      overlay.hidden = true
      drawer.setAttribute('aria-hidden', 'true')
      overlay.setAttribute('aria-hidden', 'true')
      estado.drawerClienteId = null
    }, 250)
  }

  function preencherDrawerHeader(cliente) {
    document.getElementById('drawer-nome').textContent = cliente.nome
    document.getElementById('drawer-telefone').textContent = formatarTelefoneExibicao(cliente.telefone)
    document.getElementById('drawer-avatar').textContent = inicialAvatar(cliente.nome)
  }

  function preencherStats(cliente) {
    const el = document.getElementById('drawer-stats')
    el.innerHTML = `
      <div class="drawer-stat">
        <span class="drawer-stat-valor">${cliente.total_pedidos}</span>
        <span class="drawer-stat-label">Pedidos</span>
      </div>
      <div class="drawer-stat">
        <span class="drawer-stat-valor">${formatarPreco(cliente.total_gasto)}</span>
        <span class="drawer-stat-label">Total gasto</span>
      </div>
      <div class="drawer-stat">
        <span class="drawer-stat-valor">${badgeSegmento(cliente.segmento)}</span>
        <span class="drawer-stat-label">Segmento</span>
      </div>
      <div class="drawer-stat">
        <span class="drawer-stat-valor">${formatarData(cliente.ultimo_pedido)}</span>
        <span class="drawer-stat-label">Último pedido</span>
      </div>
    `
  }

  function _setAbaAtiva(aba) {
    document.querySelectorAll('.clientes-drawer-aba').forEach(btn => {
      btn.classList.toggle('ativa', btn.dataset.aba === aba)
    })
  }

  // Guarda os dados do drawer para trocar de aba sem novo fetch
  let _dadosDrawer = { pedidos: null, enderecos: null }

  function _renderizarAba(aba, pedidos, enderecos) {
    if (pedidos !== undefined) _dadosDrawer.pedidos = pedidos
    if (enderecos !== undefined) _dadosDrawer.enderecos = enderecos

    const conteudo = document.getElementById('drawer-conteudo')
    _setAbaAtiva(aba)

    if (aba === 'pedidos') {
      const lista = _dadosDrawer.pedidos || []
      if (!lista.length) {
        conteudo.innerHTML = '<div class="clientes-estado">Nenhum pedido registrado.</div>'
        return
      }
      conteudo.innerHTML = lista.map(p => `
        <div class="drawer-pedido">
          <div class="drawer-pedido-cabecalho">
            <span class="drawer-pedido-numero">#${p.numero}</span>
            <span class="clientes-badge ${statusPedidoCls(p.status)}">${statusPedidoLabel(p.status)}</span>
            <span class="drawer-pedido-data">${formatarDataHora(p.criado_em)}</span>
          </div>
          <div class="drawer-pedido-itens">
            ${(p.itens || []).map(i => `<span class="drawer-pedido-item">${i.quantidade}× ${i.nome_snapshot}</span>`).join('')}
          </div>
          <div class="drawer-pedido-rodape">
            <span class="drawer-pedido-tipo">${p.tipo === 'delivery' ? '🛵 Delivery' : p.tipo === 'retirada' ? '🏪 Retirada' : '🧾 Balcão'}</span>
            <span class="drawer-pedido-total">${formatarPreco(p.total)}</span>
          </div>
        </div>
      `).join('')
    } else {
      const lista = _dadosDrawer.enderecos || []
      if (!lista.length) {
        conteudo.innerHTML = '<div class="clientes-estado">Nenhum endereço salvo.</div>'
        return
      }
      conteudo.innerHTML = `<div class="drawer-enderecos">${
        lista.map(e => `<div class="drawer-endereco-chip">${e.endereco}</div>`).join('')
      }</div>`
    }
  }

  // ── Modo edição ───────────────────────────────────────────────────────────

  function renderEditEnderecos(enderecos) {
    const lista = document.getElementById('edit-enderecos-lista')
    if (!enderecos.length) {
      lista.innerHTML = '<p class="edit-enderecos-vazio">Nenhum endereço salvo.</p>'
      return
    }
    lista.innerHTML = enderecos.map(e => `
      <div class="edit-endereco-row">
        <span class="edit-endereco-texto">${e.endereco}</span>
        <button class="btn-icone-remover" type="button" data-endereco-id="${e.id}" aria-label="Remover endereço">
          ${SVG_X_MINI}
        </button>
      </div>
    `).join('')

    lista.querySelectorAll('.btn-icone-remover').forEach(btn => {
      btn.addEventListener('click', async () => {
        const enderecoId = Number(btn.dataset.enderecoId)
        const clienteId = estado.drawerClienteId
        btn.disabled = true
        try {
          await api.delete(`/api/admin/clientes/${clienteId}/enderecos/${enderecoId}`)
          const atualizados = await api.get(`/api/admin/clientes/${clienteId}/enderecos`)
          _dadosDrawer.enderecos = atualizados
          renderEditEnderecos(atualizados)
        } catch (err) {
          toast.erro(err.message || 'Erro ao remover endereço')
          btn.disabled = false
        }
      })
    })
  }

  async function salvarEdicao() {
    const clienteId = estado.drawerClienteId
    const nome = document.getElementById('edit-nome').value.trim()
    const telefone = document.getElementById('edit-telefone').value.replace(/\D/g, '')

    if (!nome) { toast.erro('Nome é obrigatório'); return }
    if (!telefone) { toast.erro('Telefone é obrigatório'); return }

    const btn = document.getElementById('btn-salvar-edicao')
    btn.disabled = true

    try {
      if (clienteId === null) {
        // ── Criação ──
        const novo = await api.post('/api/admin/clientes', { nome, telefone })
        toast.sucesso('Cliente criado com sucesso')
        carregarLista()
        await abrirDrawer(novo.id)
      } else {
        // ── Edição ──
        await api.put(`/api/admin/clientes/${clienteId}`, { nome, telefone })
        toast.sucesso('Cliente atualizado')
        carregarLista()
        await abrirDrawer(clienteId)
      }
    } catch (err) {
      toast.erro(err.message || 'Erro ao salvar')
    } finally {
      btn.disabled = false
    }
  }

  function cancelarEdicao() {
    const clienteId = estado.drawerClienteId
    if (clienteId === null) {
      // Criação cancelada: fecha o drawer
      fecharDrawer()
    } else if (_dadosDrawer.pedidos !== null) {
      // Edição cancelada com dados em cache: volta à visualização
      _setModoDrawer('view')
      _renderizarAba('pedidos')
    } else {
      // Edição cancelada sem cache: recarrega no modo visualização
      abrirDrawer(clienteId)
    }
  }

  // ── Modal de exclusão ─────────────────────────────────────────────────────

  function abrirModalExcluir(clienteId, nome) {
    _excluirClienteId = clienteId
    document.getElementById('modal-excluir-nome').textContent = nome
    document.getElementById('modal-excluir').hidden = false
  }

  function fecharModalExcluir() {
    document.getElementById('modal-excluir').hidden = true
    _excluirClienteId = null
  }

  async function confirmarExclusao() {
    if (!_excluirClienteId) return
    const clienteId = _excluirClienteId
    const btn = document.getElementById('btn-excluir-confirmar')
    btn.disabled = true

    try {
      await api.delete(`/api/admin/clientes/${clienteId}`)
      fecharModalExcluir()
      if (estado.drawerClienteId === clienteId) fecharDrawer()
      carregarLista()
      toast.sucesso('Cliente excluído')
    } catch (err) {
      toast.erro(err.message || 'Erro ao excluir cliente')
    } finally {
      btn.disabled = false
    }
  }

  // ── Máscara de telefone ───────────────────────────────────────────────────

  function aplicarMascaraTelefone(input) {
    input.addEventListener('input', e => {
      let v = e.target.value.replace(/\D/g, '').slice(0, 11)
      if (v.length > 7) {
        v = `(${v.slice(0,2)}) ${v.slice(2,7)}-${v.slice(7)}`
      } else if (v.length > 6) {
        v = `(${v.slice(0,2)}) ${v.slice(2,6)}-${v.slice(6)}`
      } else if (v.length > 2) {
        v = `(${v.slice(0,2)}) ${v.slice(2)}`
      } else if (v.length > 0) {
        v = `(${v}`
      }
      e.target.value = v
    })
  }

  // ── Filtros e eventos ─────────────────────────────────────────────────────

  function inicializar() {
    if (!auth.proteger()) return

    carregarNomeLojaSidebar()

    const usuario = auth.getUsuario()
    const nomeEl = document.getElementById('header-usuario-nome')
    const avatarEl = document.getElementById('header-usuario-avatar')
    if (nomeEl) nomeEl.textContent = usuario.nome
    if (avatarEl) avatarEl.textContent = inicialAvatar(usuario.nome)

    // Mobile sidebar
    document.getElementById('btn-menu')?.addEventListener('click', () => {
      document.getElementById('sidebar').classList.toggle('aberta')
    })

    // Busca com debounce + botão X customizado
    const buscaInput = document.getElementById('clientes-busca')
    const btnLimparBusca = document.getElementById('clientes-busca-limpar')

    buscaInput.addEventListener('input', e => {
      btnLimparBusca.hidden = !e.target.value
      clearTimeout(estado.debounceTimer)
      estado.debounceTimer = setTimeout(() => {
        estado.q = e.target.value.trim()
        estado.page = 1
        carregarLista()
      }, 300)
    })

    btnLimparBusca.addEventListener('click', () => {
      buscaInput.value = ''
      btnLimparBusca.hidden = true
      estado.q = ''
      estado.page = 1
      carregarLista()
      buscaInput.focus()
    })

    // Ordenação
    document.getElementById('clientes-ordenar').addEventListener('change', e => {
      estado.ordenar = e.target.value
      estado.page = 1
      carregarLista()
    })

    // Chips de segmento
    document.querySelectorAll('.clientes-segmento-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.clientes-segmento-chip').forEach(b => b.classList.remove('ativo'))
        btn.classList.add('ativo')
        estado.segmento = btn.dataset.segmento
        estado.page = 1
        carregarLista()
      })
    })

    // Paginação
    document.getElementById('clientes-pag-anterior').addEventListener('click', () => {
      if (estado.page > 1) { estado.page--; carregarLista() }
    })
    document.getElementById('clientes-pag-proxima').addEventListener('click', () => {
      const totalPags = Math.ceil(estado.total / estado.pageSize)
      if (estado.page < totalPags) { estado.page++; carregarLista() }
    })

    // Fechar drawer
    document.getElementById('drawer-fechar').addEventListener('click', fecharDrawer)
    document.getElementById('drawer-overlay').addEventListener('click', fecharDrawer)
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') {
        _fecharTodosDropdowns()
        fecharDrawer()
        fecharModalExcluir()
        fecharModalNovoCliente()
      }
    })

    // Abas do drawer
    document.querySelectorAll('.clientes-drawer-aba').forEach(btn => {
      btn.addEventListener('click', () => {
        if (estado.drawerClienteId !== null) {
          estado.drawerAba = btn.dataset.aba
          _renderizarAba(btn.dataset.aba)
        }
      })
    })

    // Máscara de telefone no drawer
    aplicarMascaraTelefone(document.getElementById('edit-telefone'))

    // Edição: salvar e cancelar
    document.getElementById('btn-salvar-edicao').addEventListener('click', salvarEdicao)
    document.getElementById('btn-cancelar-edicao').addEventListener('click', cancelarEdicao)

    // Endereço: adicionar
    document.getElementById('btn-add-endereco').addEventListener('click', async () => {
      const input = document.getElementById('edit-novo-endereco')
      const texto = input.value.trim()
      if (!texto) return
      const clienteId = estado.drawerClienteId
      const btn = document.getElementById('btn-add-endereco')
      btn.disabled = true
      try {
        await api.post(`/api/admin/clientes/${clienteId}/enderecos`, { endereco: texto })
        input.value = ''
        const atualizados = await api.get(`/api/admin/clientes/${clienteId}/enderecos`)
        _dadosDrawer.enderecos = atualizados
        renderEditEnderecos(atualizados)
      } catch (err) {
        toast.erro(err.message || 'Erro ao adicionar endereço')
      } finally {
        btn.disabled = false
      }
    })

    // Enter no campo de novo endereço
    document.getElementById('edit-novo-endereco').addEventListener('keydown', e => {
      if (e.key === 'Enter') document.getElementById('btn-add-endereco').click()
    })

    // Modal de exclusão
    document.getElementById('btn-excluir-cancelar').addEventListener('click', fecharModalExcluir)
    document.getElementById('modal-excluir-overlay').addEventListener('click', fecharModalExcluir)
    document.getElementById('btn-excluir-confirmar').addEventListener('click', confirmarExclusao)

    // Novo cliente — abre o drawer diretamente
    document.getElementById('btn-novo-cliente').addEventListener('click', abrirNovoCliente)

    // Fechar dropdowns ao clicar fora
    document.addEventListener('click', () => _fecharTodosDropdowns())

    carregarLista()
  }

  document.addEventListener('DOMContentLoaded', inicializar)

})()
