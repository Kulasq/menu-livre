/* frontend/admin/js/cupons.js
 * Gerenciamento de cupons de desconto.
 * Depende de: config.js, utils.js, auth.js
 */

const Cupons = (() => {
  let _cupons = []
  let _produtos = []
  let _editandoId = null
  let _dropdownAtivoId = null   // id do cupom com dropdown aberto
  let _confirmacaoCallback = null

  const TIPOS = {
    percentual: 'Percentual',
    valor_fixo: 'Valor fixo',
    frete_gratis: 'Frete grátis',
    brinde: 'Brinde',
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  function brl(v) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v)
  }

  function fmtData(iso) {
    if (!iso) return '—'
    return new Date(iso).toLocaleDateString('pt-BR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
    })
  }

  function fmtDesconto(cupom) {
    if (cupom.tipo === 'percentual') {
      const max = cupom.desconto_maximo ? ` (até ${brl(cupom.desconto_maximo)})` : ''
      return `${cupom.valor}%${max}`
    }
    if (cupom.tipo === 'valor_fixo') return brl(cupom.valor)
    if (cupom.tipo === 'frete_gratis') return 'Frete grátis'
    if (cupom.tipo === 'brinde') return cupom.produto_brinde?.nome ?? '(brinde)'
    return '—'
  }

  // ── API — usa o objeto global `api` do auth.js (token em memória + refresh automático) ──

  async function carregar() {
    try {
      _cupons = await api.get('/api/admin/cupons')
      renderizar()
    } catch {
      toast.erro('Erro ao carregar cupons')
    }
  }

  async function carregarProdutos() {
    try {
      _produtos = await api.get('/api/admin/produtos')
      const sel = document.getElementById('cupom-produto-brinde')
      sel.innerHTML = '<option value="">Selecione o produto...</option>' +
        _produtos.map(p => `<option value="${p.id}">${p.nome}</option>`).join('')
    } catch {
      // Silencioso — lista de brindes fica vazia se falhar
    }
  }

  async function salvar(dados) {
    try {
      if (_editandoId) {
        await api.put(`/api/admin/cupons/${_editandoId}`, dados)
      } else {
        await api.post('/api/admin/cupons', dados)
      }
      return true
    } catch (err) {
      toast.erro(err?.message || 'Erro ao salvar cupom')
      return false
    }
  }

  async function deletar(id) {
    try {
      await api.delete(`/api/admin/cupons/${id}`)
      return true
    } catch {
      toast.erro('Erro ao remover cupom')
      return false
    }
  }

  async function toggleAtivo(id) {
    const cupom = _cupons.find(c => c.id === id)
    if (!cupom) return
    try {
      await api.put(`/api/admin/cupons/${id}`, { ativo: !cupom.ativo })
      toast.sucesso(cupom.ativo ? 'Cupom desativado' : 'Cupom ativado')
      await carregar()
    } catch (err) {
      toast.erro(err?.message || 'Erro ao atualizar cupom')
    }
  }

  async function carregarUsos(id) {
    try {
      return await api.get(`/api/admin/cupons/${id}/usos`)
    } catch {
      toast.erro('Erro ao carregar usos')
      return []
    }
  }

  // ── Dropdown kebab ────────────────────────────────────────────────────────

  function _posicionarDropdown(menu, btnEl) {
    menu.style.visibility = 'hidden'
    menu.classList.remove('hidden')

    const rect  = btnEl.getBoundingClientRect()
    const menuH = menu.offsetHeight
    const viewH = window.innerHeight
    const GAP   = 4

    // Abre para baixo se couber, senão flip para cima
    const top = (viewH - rect.bottom - GAP) >= menuH
      ? rect.bottom + GAP
      : Math.max(GAP, rect.top - menuH - GAP)

    menu.style.top        = top + 'px'
    menu.style.right      = Math.max(GAP, window.innerWidth - rect.right) + 'px'
    menu.style.left       = 'auto'
    menu.style.visibility = ''
  }

  function _abrirDropdown(id, btnEl) {
    if (_dropdownAtivoId === id) { _fecharDropdown(); return }
    _fecharDropdown()
    _dropdownAtivoId = id
    _posicionarDropdown(document.getElementById('dropdown-acoes-cupom'), btnEl)
  }

  function _fecharDropdown() {
    document.getElementById('dropdown-acoes-cupom').classList.add('hidden')
    _dropdownAtivoId = null
  }

  // ── Renderização ─────────────────────────────────────────────────────────

  function renderizar() {
    const tbody = document.getElementById('cupons-tbody')
    if (!_cupons.length) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:40px;color:var(--texto-secundario)">
        Nenhum cupom cadastrado ainda.
      </td></tr>`
      return
    }

    tbody.innerHTML = _cupons.map(c => {
      const usosTxt = c.limite_total_usos
        ? `${c.usos_atuais} / ${c.limite_total_usos}`
        : `${c.usos_atuais}`

      // Badge clicável para toggle ativo/inativo
      const statusBadge = `<button
        class="badge ${c.ativo ? 'badge-sucesso' : 'badge-erro'}"
        data-id="${c.id}" data-action="toggle-ativo"
        type="button"
        title="Clique para ${c.ativo ? 'desativar' : 'ativar'}"
        style="cursor:pointer;border:none;font:inherit"
      >${c.ativo ? 'Ativo' : 'Inativo'}</button>`

      return `<tr>
        <td><code style="font-weight:700;font-size:.9rem">${c.codigo}</code></td>
        <td>${TIPOS[c.tipo] ?? c.tipo}</td>
        <td>${fmtDesconto(c)}</td>
        <td>
          <button class="btn-link" data-id="${c.id}" data-action="ver-usos" title="Ver pedidos que usaram esse cupom"
            style="color:inherit;background:none;border:none;cursor:pointer;padding:0;font:inherit">
            ${usosTxt}
          </button>
        </td>
        <td>${brl(c.faturamento_gerado ?? 0)}</td>
        <td>${fmtData(c.data_fim)}</td>
        <td>${statusBadge}</td>
        <td>
          <button class="btn-kebab btn-dd-cupom" data-id="${c.id}" type="button" aria-label="Ações" title="Ações">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="16" height="16" aria-hidden="true">
              <circle cx="12" cy="5"  r="2"/><circle cx="12" cy="12" r="2"/><circle cx="12" cy="19" r="2"/>
            </svg>
          </button>
        </td>
      </tr>`
    }).join('')
  }

  // ── Modal ────────────────────────────────────────────────────────────────

  function abrirModalNovo() {
    _editandoId = null
    document.getElementById('modal-cupom-titulo').textContent = 'Novo Cupom'
    document.getElementById('form-cupom').reset()
    document.getElementById('cupom-ativo').checked = true
    _sincronizarCamposTipo()
    document.getElementById('modal-cupom').classList.remove('hidden')
    document.getElementById('cupom-codigo').focus()
  }

  function abrirModalEditar(cupom) {
    _editandoId = cupom.id
    document.getElementById('modal-cupom-titulo').textContent = 'Editar Cupom'

    document.getElementById('cupom-codigo').value = cupom.codigo
    document.getElementById('cupom-tipo').value = cupom.tipo
    document.getElementById('cupom-valor').value = cupom.valor
    document.getElementById('cupom-desconto-maximo').value = cupom.desconto_maximo ?? ''
    document.getElementById('cupom-produto-brinde').value = cupom.produto_brinde_id ?? ''
    document.getElementById('cupom-valor-minimo').value = cupom.valor_minimo_pedido
    document.getElementById('cupom-limite-total').value = cupom.limite_total_usos ?? ''
    document.getElementById('cupom-limite-cliente').value = cupom.limite_por_cliente
    document.getElementById('cupom-primeira-compra').checked = cupom.somente_primeira_compra
    document.getElementById('cupom-ativo').checked = cupom.ativo

    document.getElementById('cupom-data-inicio').value = cupom.data_inicio
      ? cupom.data_inicio.slice(0, 16)
      : ''
    document.getElementById('cupom-data-fim').value = cupom.data_fim
      ? cupom.data_fim.slice(0, 16)
      : ''

    _sincronizarCamposTipo()
    document.getElementById('modal-cupom').classList.remove('hidden')
  }

  function fecharModal() {
    document.getElementById('modal-cupom').classList.add('hidden')
    _editandoId = null
  }

  function _sincronizarCamposTipo() {
    const tipo = document.getElementById('cupom-tipo').value
    const grupoValor = document.getElementById('grupo-valor')
    const grupoMax = document.getElementById('grupo-desconto-maximo')
    const grupoBrinde = document.getElementById('grupo-brinde')
    const labelValor = document.getElementById('label-valor')

    grupoValor.hidden = tipo === 'frete_gratis' || tipo === 'brinde'
    grupoMax.hidden = tipo !== 'percentual'
    grupoBrinde.hidden = tipo !== 'brinde'

    if (tipo === 'percentual') labelValor.firstChild.textContent = 'Percentual (%) '
    if (tipo === 'valor_fixo') labelValor.firstChild.textContent = 'Valor em R$ '
  }

  // ── Modal de confirmação ─────────────────────────────────────────────────

  function abrirConfirmacao(mensagem, callback) {
    _confirmacaoCallback = callback
    document.getElementById('modal-confirmar-msg').textContent = mensagem
    document.getElementById('modal-confirmar').classList.remove('hidden')
  }

  function fecharConfirmacao() {
    document.getElementById('modal-confirmar').classList.add('hidden')
    _confirmacaoCallback = null
  }

  // ── Modal de usos ────────────────────────────────────────────────────────

  async function abrirModalUsos(cupomId) {
    const cupom = _cupons.find(c => c.id === cupomId)
    document.getElementById('modal-usos-titulo').textContent =
      `Usos do cupom ${cupom?.codigo ?? ''}`
    document.getElementById('modal-usos').classList.remove('hidden')
    document.getElementById('usos-lista').innerHTML =
      '<p style="color:var(--texto-secundario);text-align:center;padding:24px">Carregando…</p>'

    const usos = await carregarUsos(cupomId)
    if (!usos.length) {
      document.getElementById('usos-lista').innerHTML =
        '<p style="color:var(--texto-secundario);text-align:center;padding:24px">Nenhum uso registrado ainda.</p>'
      return
    }

    document.getElementById('usos-lista').innerHTML = `
      <table class="tabela">
        <thead><tr><th>Pedido #</th><th>Cliente</th><th>Desconto</th><th>Subtotal</th><th>Data</th></tr></thead>
        <tbody>
          ${usos.map(u => `<tr>
            <td>${u.pedido_id}</td>
            <td>${u.cliente_telefone ?? '—'}</td>
            <td style="color:var(--sucesso)">${brl(u.desconto_aplicado)}</td>
            <td>${brl(u.subtotal_pedido)}</td>
            <td>${fmtData(u.criado_em)}</td>
          </tr>`).join('')}
        </tbody>
      </table>
    `
  }

  // ── Submit ────────────────────────────────────────────────────────────────

  async function onSubmit(e) {
    e.preventDefault()
    const tipo = document.getElementById('cupom-tipo').value
    const codigo = document.getElementById('cupom-codigo').value.trim().toUpperCase()

    if (!codigo) { toast.erro('Informe o código do cupom'); return }
    if ((tipo === 'percentual' || tipo === 'valor_fixo') && !document.getElementById('cupom-valor').value) {
      toast.erro('Informe o valor do desconto'); return
    }
    if (tipo === 'brinde' && !document.getElementById('cupom-produto-brinde').value) {
      toast.erro('Selecione o produto brinde'); return
    }

    const dados = {
      codigo,
      tipo,
      valor: parseFloat(document.getElementById('cupom-valor').value || '0'),
      desconto_maximo: document.getElementById('cupom-desconto-maximo').value
        ? parseFloat(document.getElementById('cupom-desconto-maximo').value)
        : null,
      produto_brinde_id: document.getElementById('cupom-produto-brinde').value
        ? parseInt(document.getElementById('cupom-produto-brinde').value)
        : null,
      valor_minimo_pedido: parseFloat(document.getElementById('cupom-valor-minimo').value || '0'),
      limite_total_usos: document.getElementById('cupom-limite-total').value
        ? parseInt(document.getElementById('cupom-limite-total').value)
        : null,
      limite_por_cliente: parseInt(document.getElementById('cupom-limite-cliente').value || '0'),
      somente_primeira_compra: document.getElementById('cupom-primeira-compra').checked,
      data_inicio: document.getElementById('cupom-data-inicio').value || null,
      data_fim: document.getElementById('cupom-data-fim').value || null,
      ativo: document.getElementById('cupom-ativo').checked,
    }

    const btn = document.getElementById('btn-salvar-cupom')
    btn.disabled = true
    btn.textContent = 'Salvando…'

    const ok = await salvar(dados)
    btn.disabled = false
    btn.textContent = 'Salvar'

    if (ok) {
      toast.sucesso(_editandoId ? 'Cupom atualizado!' : 'Cupom criado!')
      fecharModal()
      await carregar()
    }
  }

  // ── Eventos ──────────────────────────────────────────────────────────────

  function init() {
    if (!auth.proteger()) return

    carregarNomeLojaSidebar()

    // ── Modal cupom ──
    document.getElementById('btn-novo-cupom').addEventListener('click', abrirModalNovo)
    document.getElementById('modal-cupom-fechar').addEventListener('click', fecharModal)
    document.getElementById('modal-cupom-cancelar').addEventListener('click', fecharModal)
    document.getElementById('modal-cupom-overlay').addEventListener('click', fecharModal)
    document.getElementById('cupom-tipo').addEventListener('change', _sincronizarCamposTipo)
    document.getElementById('form-cupom').addEventListener('submit', onSubmit)

    // ── Modal usos ──
    const fecharUsos = () => document.getElementById('modal-usos').classList.add('hidden')
    document.getElementById('modal-usos-fechar').addEventListener('click', fecharUsos)
    document.getElementById('modal-usos-fechar-btn').addEventListener('click', fecharUsos)
    document.getElementById('modal-usos-overlay').addEventListener('click', fecharUsos)

    // ── Delegação de eventos na tabela (data-action) ──
    document.getElementById('tabela-cupons').addEventListener('click', async e => {
      // Kebab — abre/fecha dropdown
      const kebab = e.target.closest('.btn-dd-cupom')
      if (kebab) {
        _abrirDropdown(parseInt(kebab.dataset.id), kebab)
        return
      }

      const btn = e.target.closest('[data-action]')
      if (!btn) return
      const id = parseInt(btn.dataset.id)
      const action = btn.dataset.action

      if (action === 'toggle-ativo') {
        await toggleAtivo(id)
      }
      if (action === 'ver-usos') {
        await abrirModalUsos(id)
      }
    })

    // ── Kebab dropdown — itens ──
    document.getElementById('dd-cupom-editar').addEventListener('click', () => {
      const cupom = _cupons.find(c => c.id === _dropdownAtivoId)
      _fecharDropdown()
      if (cupom) abrirModalEditar(cupom)
    })

    document.getElementById('dd-cupom-deletar').addEventListener('click', () => {
      const id = _dropdownAtivoId
      const cupom = _cupons.find(c => c.id === id)
      _fecharDropdown()
      const msg = `Deletar o cupom "${cupom?.codigo}"?${cupom?.usos_atuais > 0 ? ` Ele tem ${cupom.usos_atuais} uso(s) registrado(s).` : ''}`
      abrirConfirmacao(msg, async () => {
        const ok = await deletar(id)
        if (ok) { toast.sucesso('Cupom removido'); await carregar() }
      })
    })

    document.getElementById('modal-confirmar-sim').addEventListener('click', () => {
      if (_confirmacaoCallback) _confirmacaoCallback()
      fecharConfirmacao()
    })
    document.getElementById('modal-confirmar-nao').addEventListener('click', fecharConfirmacao)
    document.getElementById('modal-confirmar-overlay').addEventListener('click', fecharConfirmacao)

    // ── Fechar dropdown ao clicar fora ou rolar ──
    document.addEventListener('click', e => {
      if (!e.target.closest('#dropdown-acoes-cupom') && !e.target.closest('.btn-dd-cupom')) {
        _fecharDropdown()
      }
    })
    window.addEventListener('scroll', _fecharDropdown, { passive: true, capture: true })

    // ── Normalizar código para maiúsculas enquanto digita ──
    document.getElementById('cupom-codigo').addEventListener('input', e => {
      const sel = e.target.selectionStart
      e.target.value = e.target.value.toUpperCase().replace(/\s/g, '')
      e.target.setSelectionRange(sel, sel)
    })

    carregarProdutos()
    carregar()
  }

  return { init }
})()

document.addEventListener('DOMContentLoaded', () => Cupons.init())
