/* ── Estado ─────────────────────────────────────────────── */

let categorias = []
let produtos = []
let gruposGlobais = []        // lista de grupos autônomos
let categoriaEditando = null
let produtoEditando = null
let fotoParaUpload = null
let filtroCategoria = ''
let confirmacaoCallback = null

/* Estado dos modificadores (modal por produto) */
let modProdutoId = null
let grupoEditando = null
let opcaoEditando = null
let opcaoGrupoId = null

/* Estado dos grupos globais */
let grupoGlobalEditando = null   // null = criando, obj = editando
let grupoOpcoesSelecionado = null // grupo cujas opções estão abertas
let opcaoGlobalEditando = null
let grupoVincularId = null       // grupo que está sendo vinculado

/* Estado dos dropdowns de ações */
let dropdownCategoriaId = null
let dropdownGrupoId = null
let dropdownProdutoId = null

/* Estado do modal de vínculos */
let vinculadosIniciais = new Set()   // IDs de produtos vinculados ao abrir o modal


/* ── Inicialização ──────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {
  if (!auth.proteger()) return

  setupUsuario()
  setupSidebar()
  carregarNomeLojaSidebar()
  setupEventos()
  carregarDados()
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
  /* Categorias */
  $('#btn-nova-categoria').addEventListener('click', () => abrirModalCategoria())
  $('#form-categoria').addEventListener('submit', handleSubmitCategoria)
  $('#modal-categoria-fechar').addEventListener('click', fecharModalCategoria)
  $('#modal-categoria-overlay').addEventListener('click', fecharModalCategoria)
  $('#modal-categoria-cancelar').addEventListener('click', fecharModalCategoria)

  /* Produtos */
  $('#btn-novo-produto').addEventListener('click', () => abrirModalProduto())
  $('#form-produto').addEventListener('submit', handleSubmitProduto)
  $('#modal-produto-fechar').addEventListener('click', fecharModalProduto)
  $('#modal-produto-overlay').addEventListener('click', fecharModalProduto)
  $('#modal-produto-cancelar').addEventListener('click', fecharModalProduto)

  /* Upload de foto */
  $('#produto-foto-input').addEventListener('change', handleFotoChange)
  $('#produto-foto-btn').addEventListener('click', () => $('#produto-foto-input').click())
  $('#produto-foto-remover').addEventListener('click', removerFoto)

  /* Toggle de controle de estoque */
  $('#produto-controle-estoque').addEventListener('change', e => _togglePainelEstoqueProduto(e.target.checked))
  $('#opcao-controle-estoque').addEventListener('change', e => _togglePainelEstoqueOpcao(e.target.checked))

  /* Filtro */
  $('#filtro-categoria').addEventListener('change', (e) => {
    filtroCategoria = e.target.value
    renderProdutos()
  })

  /* Modificadores (modal por produto) */
  $('#modal-modificadores-fechar').addEventListener('click', fecharModalModificadores)
  $('#modal-modificadores-overlay').addEventListener('click', fecharModalModificadores)
  $('#btn-novo-grupo').addEventListener('click', () => abrirModalGrupo())
  $('#form-grupo').addEventListener('submit', handleSubmitGrupo)
  $('#modal-grupo-fechar').addEventListener('click', fecharModalGrupo)
  $('#modal-grupo-overlay').addEventListener('click', fecharModalGrupo)
  $('#modal-grupo-cancelar').addEventListener('click', fecharModalGrupo)
  $('#form-opcao').addEventListener('submit', handleSubmitOpcaoUnificado)
  $('#modal-opcao-fechar').addEventListener('click', fecharModalOpcao)
  $('#modal-opcao-overlay').addEventListener('click', fecharModalOpcao)
  $('#modal-opcao-cancelar').addEventListener('click', fecharModalOpcao)

  /* Grupos globais */
  $('#btn-novo-grupo-global').addEventListener('click', () => abrirModalGrupoGlobal())
  $('#form-grupo-global').addEventListener('submit', handleSubmitGrupoGlobal)
  $('#modal-grupo-global-fechar').addEventListener('click', fecharModalGrupoGlobal)
  $('#modal-grupo-global-overlay').addEventListener('click', fecharModalGrupoGlobal)
  $('#modal-grupo-global-cancelar').addEventListener('click', fecharModalGrupoGlobal)

  /* Opções do grupo global */
  $('#modal-opcoes-grupo-fechar').addEventListener('click', fecharModalOpcoesGrupo)
  $('#modal-opcoes-grupo-overlay').addEventListener('click', fecharModalOpcoesGrupo)
  $('#btn-nova-opcao-grupo').addEventListener('click', () => abrirModalOpcaoGlobal())

  /* Vincular */
  $('#modal-vincular-fechar').addEventListener('click', fecharModalVincular)
  $('#modal-vincular-overlay').addEventListener('click', fecharModalVincular)
  $('#modal-vincular-cancelar').addEventListener('click', fecharModalVincular)
  $('#btn-confirmar-vincular').addEventListener('click', handleConfirmarVincular)

  /* Ações rápidas da lista hierárquica */
  $('#v-btn-todos').addEventListener('click', () => {
    $('#v-lista-hierarquica').querySelectorAll('.vp-produto').forEach(cb => { cb.checked = true })
    $('#v-lista-hierarquica').querySelectorAll('.vp-categoria').forEach(cb => { cb.checked = true; cb.indeterminate = false })
  })
  $('#v-btn-nenhum').addEventListener('click', () => {
    $('#v-lista-hierarquica').querySelectorAll('input[type=checkbox]').forEach(cb => { cb.checked = false; cb.indeterminate = false })
  })

  /* Delegação de eventos na lista hierárquica — categoria e produto */
  $('#v-lista-hierarquica').addEventListener('change', (e) => {
    if (e.target.matches('.vp-categoria')) _vCatChange(e.target)
    else if (e.target.matches('.vp-produto')) _vProdChange(e.target)
  })

  /* Dropdown — categorias */
  $('#dd-cat-editar').addEventListener('click', () => { const id = dropdownCategoriaId; fecharDropdowns(); if (id) abrirModalCategoria(id) })
  $('#dd-cat-excluir').addEventListener('click', () => {
    const cat = categorias.find(c => c.id === dropdownCategoriaId)
    fecharDropdowns()
    if (cat) confirmarExcluirCategoria(cat.id, cat.nome)
  })

  /* Dropdown — grupos globais */
  $('#dd-grupo-opcoes').addEventListener('click', () => { const id = dropdownGrupoId; fecharDropdowns(); if (id) abrirModalOpcoesGrupo(id) })
  $('#dd-grupo-vincular').addEventListener('click', () => { const id = dropdownGrupoId; fecharDropdowns(); if (id) abrirModalVincular(id) })
  $('#dd-grupo-editar').addEventListener('click', () => { const id = dropdownGrupoId; fecharDropdowns(); if (id) abrirModalGrupoGlobal(id) })
  $('#dd-grupo-excluir').addEventListener('click', () => {
    const grupo = gruposGlobais.find(g => g.id === dropdownGrupoId)
    fecharDropdowns()
    if (grupo) confirmarExcluirGrupoGlobal(grupo.id, grupo.nome, grupo.total_produtos || 0)
  })

  /* Dropdown — produtos */
  $('#dd-prod-editar').addEventListener('click', () => { const id = dropdownProdutoId; fecharDropdowns(); if (id) abrirModalProduto(id) })
  $('#dd-prod-excluir').addEventListener('click', () => {
    const prod = produtos.find(p => p.id === dropdownProdutoId)
    fecharDropdowns()
    if (prod) confirmarExcluirProduto(prod.id, prod.nome)
  })

  /* Fecha dropdowns ao clicar fora */
  document.addEventListener('click', (e) => {
    if (!e.target.closest('#dropdown-acoes-categoria') && !e.target.closest('.btn-dd-categoria')) fecharDropdownCategoria()
    if (!e.target.closest('#dropdown-acoes-grupo') && !e.target.closest('.btn-dd-grupo')) fecharDropdownGrupo()
    if (!e.target.closest('#dropdown-acoes-produto') && !e.target.closest('.btn-dd-produto')) fecharDropdownProduto()
  })

  /* Fecha dropdowns ao rolar (qualquer elemento scrollável) */
  window.addEventListener('scroll', fecharDropdowns, { passive: true, capture: true })

  /* Confirmação */
  $('#modal-confirmar-sim').addEventListener('click', () => {
    if (confirmacaoCallback) confirmacaoCallback()
    fecharConfirmacao()
  })
  $('#modal-confirmar-nao').addEventListener('click', fecharConfirmacao)
  $('#modal-confirmar-overlay').addEventListener('click', fecharConfirmacao)
}

async function carregarDados() {
  try {
    $('#categorias-loading').classList.remove('hidden')
    $('#produtos-loading').classList.remove('hidden')
    $('#grupos-loading').classList.remove('hidden')

    const [cats, prods, grupos] = await Promise.all([
      api.get('/api/admin/categorias'),
      api.get('/api/admin/produtos'),
      api.get('/api/admin/grupos-modificadores'),
    ])

    categorias = cats
    produtos = prods
    gruposGlobais = grupos

    renderCategorias()
    renderProdutos()
    renderGruposGlobais()
    atualizarFiltroCategorias()
    atualizarSelectCategoria()
  } catch (err) {
    toast.erro('Erro ao carregar cardápio: ' + err.message)
  } finally {
    $('#categorias-loading').classList.add('hidden')
    $('#produtos-loading').classList.add('hidden')
    $('#grupos-loading').classList.add('hidden')
  }
}


/* ══════════════════════════════════════════════════════════
   CATEGORIAS
   ══════════════════════════════════════════════════════════ */

function renderCategorias() {
  const tbody = $('#categorias-tbody')
  const vazio = $('#categorias-vazio')

  if (categorias.length === 0) {
    tbody.innerHTML = ''
    vazio.classList.remove('hidden')
    return
  }

  vazio.classList.add('hidden')
  tbody.innerHTML = categorias.map(cat => `
    <tr style="will-change:opacity;${cat.ativo ? '' : 'opacity:.55'}">
      <td>
        <strong>${esc(cat.nome)}</strong>
      </td>
      <td>${cat.ordem}</td>
      <td>
        <button class="btn btn-sm ${cat.ativo ? 'btn-secondary' : 'btn-danger'}"
                onclick="toggleAtivoCategoria(${cat.id})"
                title="${cat.ativo ? 'Ativa — clique para desativar' : 'Inativa — clique para ativar'}">
          ${cat.ativo ? icons.check : icons.x_circulo}
        </button>
      </td>
      <td style="position:relative">
        <button class="btn btn-secondary btn-sm btn-dd-categoria" onclick="abrirDropdownCategoria(${cat.id}, this)" title="Ações" style="padding:6px 8px">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width:16px;height:16px;vertical-align:middle"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.75a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5ZM12 12.75a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5ZM12 18.75a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5Z" /></svg>
        </button>
      </td>
    </tr>
  `).join('')
}

function abrirModalCategoria(id = null) {
  categoriaEditando = id ? categorias.find(c => c.id === id) : null
  $('#modal-categoria-titulo').textContent = categoriaEditando ? 'Editar categoria' : 'Nova categoria'
  $('#categoria-nome').value = categoriaEditando?.nome || ''
  $('#categoria-ordem').value = categoriaEditando?.ordem ?? 0

  $('#modal-categoria').classList.remove('hidden')
  $('#categoria-nome').focus()
}

function fecharModalCategoria() {
  $('#modal-categoria').classList.add('hidden')
  categoriaEditando = null
}

async function handleSubmitCategoria(e) {
  e.preventDefault()
  const btn = $('#btn-salvar-categoria')
  btn.disabled = true
  btn.textContent = 'Salvando…'

  const dados = {
    nome: $('#categoria-nome').value.trim(),
    ordem: parseInt($('#categoria-ordem').value) || 0,
  }
  // ativo é controlado pelo botão inline na tabela, não pelo modal

  try {
    if (categoriaEditando) {
      await api.put(`/api/admin/categorias/${categoriaEditando.id}`, dados)
      toast.sucesso('Categoria atualizada!')
    } else {
      await api.post('/api/admin/categorias', dados)
      toast.sucesso('Categoria criada!')
    }
    fecharModalCategoria()
    await carregarDados()
  } catch (err) {
    toast.erro(err.message)
  } finally {
    btn.disabled = false
    btn.textContent = 'Salvar'
  }
}

function confirmarExcluirCategoria(id, nome) {
  abrirConfirmacao(`Excluir a categoria "${nome}"?`, async () => {
    try {
      await api.delete(`/api/admin/categorias/${id}`)
      toast.sucesso('Categoria excluída!')
      await carregarDados()
    } catch (err) { toast.erro(err.message) }
  })
}

async function toggleAtivoCategoria(id) {
  const cat = categorias.find(c => c.id === id)
  if (!cat) return
  const novoAtivo = !cat.ativo
  try {
    await api.put(`/api/admin/categorias/${id}`, { ativo: novoAtivo })
    cat.ativo = novoAtivo          // atualiza local — sem re-fetch, sem flicker
    renderCategorias()
    toast.sucesso(novoAtivo ? 'Categoria ativada!' : 'Categoria desativada!')
  } catch (err) { toast.erro(err.message) }
}


/* ══════════════════════════════════════════════════════════
   PRODUTOS
   ══════════════════════════════════════════════════════════ */

function _badgeEstoqueProduto(prod) {
  if (!prod.controle_estoque) return ''
  if (prod.estoque_atual === 0)
    return `<span class="badge-estoque badge-estoque-zero">Esgotado</span>`
  return `<span class="badge-estoque badge-estoque-ok">Estoque: ${prod.estoque_atual}</span>`
}

function renderProdutos() {
  const tbody = $('#produtos-tbody')
  const vazio = $('#produtos-vazio')

  let lista = produtos
  if (filtroCategoria) lista = lista.filter(p => p.categoria_id === Number(filtroCategoria))

  if (lista.length === 0) {
    tbody.innerHTML = ''
    vazio.classList.remove('hidden')
    return
  }

  vazio.classList.add('hidden')
  tbody.innerHTML = lista.map(prod => {
    const cat = categorias.find(c => c.id === prod.categoria_id)
    const fotoHtml = prod.foto_url
      ? `<img src="${CONFIG.API_URL}${prod.foto_url}" alt="${esc(prod.nome)}" style="width:48px;height:48px;object-fit:cover;border-radius:6px">`
      : `<div style="width:48px;height:48px;border-radius:6px;background:var(--borda);display:flex;align-items:center;justify-content:center;color:var(--texto-terc)"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width:22px;height:22px"><path stroke-linecap="round" stroke-linejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" /><path stroke-linecap="round" stroke-linejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 10.5h.008v.008h-.008V10.5Z" /></svg></div>`

    const badgeEstoque = _badgeEstoqueProduto(prod)

    return `
      <tr style="${prod.disponivel ? '' : 'opacity:.55'}">
        <td>${fotoHtml}</td>
        <td>
          <strong>${esc(prod.nome)}</strong>${badgeEstoque}
          ${prod.descricao ? `<br><span class="text-terc" style="font-size:.82rem">${esc(prod.descricao).substring(0, 60)}${prod.descricao.length > 60 ? '…' : ''}</span>` : ''}
        </td>
        <td>${formatarPreco(prod.preco)}</td>
        <td><span class="badge badge-aviso" style="white-space:nowrap;max-width:130px;overflow:hidden;text-overflow:ellipsis;display:inline-block;vertical-align:middle" title="${cat ? esc(cat.nome) : ''}">${cat ? esc(cat.nome) : '—'}</span></td>
        <td>
          <button class="btn btn-sm ${prod.disponivel ? 'btn-secondary' : 'btn-danger'}" onclick="toggleDisponivel(${prod.id})" title="${prod.disponivel ? 'Disponível' : 'Indisponível'}">
            ${prod.disponivel ? icons.check : icons.x_circulo}
          </button>
        </td>
        <td>
          <button class="btn btn-sm ${prod.destaque ? 'btn-primary' : 'btn-secondary'}" onclick="toggleDestaque(${prod.id})" title="${prod.destaque ? 'Destaque ativo' : 'Sem destaque'}">
            ${prod.destaque ? icons.estrela : icons.estrela_vazia}
          </button>
        </td>
        <td style="position:relative">
          <button class="btn btn-secondary btn-sm btn-dd-produto" onclick="abrirDropdownProduto(${prod.id}, this)" title="Ações" style="padding:6px 8px">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width:16px;height:16px;vertical-align:middle"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.75a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5ZM12 12.75a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5ZM12 18.75a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5Z" /></svg>
          </button>
        </td>
      </tr>
    `
  }).join('')
}

function atualizarFiltroCategorias() {
  const select = $('#filtro-categoria')
  select.innerHTML = '<option value="">Todas as categorias</option>'
    + categorias.map(c => `<option value="${c.id}">${esc(c.nome)}</option>`).join('')
}

function atualizarSelectCategoria() {
  const select = $('#produto-categoria')
  select.innerHTML = '<option value="">Selecione…</option>'
    + categorias.filter(c => c.ativo).map(c => `<option value="${c.id}">${esc(c.nome)}</option>`).join('')
}

/* Modal Produto */
function abrirModalProduto(id = null) {
  produtoEditando = id ? produtos.find(p => p.id === id) : null
  fotoParaUpload = null

  $('#modal-produto-titulo').textContent = produtoEditando ? 'Editar produto' : 'Novo produto'
  $('#produto-categoria').value = produtoEditando?.categoria_id || ''
  $('#produto-nome').value = produtoEditando?.nome || ''
  $('#produto-descricao').value = produtoEditando?.descricao || ''
  $('#produto-preco').value = produtoEditando?.preco || ''
  $('#produto-ordem').value = produtoEditando?.ordem ?? 0
  $('#produto-disponivel').checked = produtoEditando?.disponivel ?? true
  $('#produto-destaque').checked = produtoEditando?.destaque ?? false

  // Estoque
  const controleOn = produtoEditando?.controle_estoque ?? false
  $('#produto-controle-estoque').checked = controleOn
  $('#produto-estoque-atual').value = produtoEditando?.estoque_atual ?? 0
  _togglePainelEstoqueProduto(controleOn)
  // Os botões rápidos só funcionam ao editar (produto já tem ID)
  $('#estoque-botoes-produto').style.display = produtoEditando ? '' : 'none'

  atualizarPreviewFoto(produtoEditando?.foto_url || null)
  $('#produto-foto-input').value = ''

  $('#modal-produto').classList.remove('hidden')
  $('#produto-nome').focus()
}

function _togglePainelEstoqueProduto(on) {
  $('#painel-estoque-produto').classList.toggle('hidden', !on)
}

function fecharModalProduto() {
  $('#modal-produto').classList.add('hidden')
  produtoEditando = null
  fotoParaUpload = null
}

function atualizarPreviewFoto(url) {
  const preview = $('#produto-foto-preview')
  const btnRemover = $('#produto-foto-remover')
  const placeholder = $('#produto-foto-placeholder')

  if (url) {
    preview.src = url.startsWith('blob:') ? url : `${CONFIG.API_URL}${url}`
    preview.classList.remove('hidden')
    btnRemover.classList.remove('hidden')
    placeholder.classList.add('hidden')
  } else {
    preview.classList.add('hidden')
    btnRemover.classList.add('hidden')
    placeholder.classList.remove('hidden')
  }
}

function handleFotoChange(e) {
  const file = e.target.files[0]
  if (!file) return
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    toast.erro('Use JPEG, PNG ou WebP.')
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    toast.erro('Imagem muito grande. Máximo: 5MB.')
    return
  }
  fotoParaUpload = file
  atualizarPreviewFoto(URL.createObjectURL(file))
}

function removerFoto() {
  fotoParaUpload = null
  $('#produto-foto-input').value = ''
  atualizarPreviewFoto(null)
  if (produtoEditando?.foto_url) produtoEditando._removerFoto = true
}

async function uploadImagem(file) {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${CONFIG.API_URL}/api/admin/upload`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${api._accessToken}` },
    body: formData,
  })
  if (!res.ok) {
    const erro = await res.json().catch(() => null)
    throw new Error(erro?.detail || 'Erro no upload da imagem')
  }
  return (await res.json()).url
}

async function handleSubmitProduto(e) {
  e.preventDefault()
  const btn = $('#btn-salvar-produto')
  btn.disabled = true
  btn.textContent = 'Salvando…'

  try {
    let fotoUrl = produtoEditando?.foto_url || null
    if (fotoParaUpload) fotoUrl = await uploadImagem(fotoParaUpload)
    else if (produtoEditando?._removerFoto) fotoUrl = null

    const dados = {
      categoria_id: parseInt($('#produto-categoria').value),
      nome: $('#produto-nome').value.trim(),
      descricao: $('#produto-descricao').value.trim() || null,
      preco: parseFloat($('#produto-preco').value),
      disponivel: $('#produto-disponivel').checked,
      destaque: $('#produto-destaque').checked,
      controle_estoque: $('#produto-controle-estoque').checked,
      estoque_atual: parseInt($('#produto-estoque-atual').value) || 0,
      ordem: parseInt($('#produto-ordem').value) || 0,
      foto_url: fotoUrl,
    }

    if (!dados.categoria_id) { toast.erro('Selecione uma categoria.'); return }

    if (produtoEditando) {
      await api.put(`/api/admin/produtos/${produtoEditando.id}`, dados)
      toast.sucesso('Produto atualizado!')
    } else {
      await api.post('/api/admin/produtos', dados)
      toast.sucesso('Produto criado!')
    }
    fecharModalProduto()
    await carregarDados()
  } catch (err) {
    toast.erro(err.message)
  } finally {
    btn.disabled = false
    btn.textContent = 'Salvar'
  }
}

async function toggleDisponivel(id) {
  const prod = produtos.find(p => p.id === id)
  if (!prod) return
  try {
    await api.put(`/api/admin/produtos/${id}`, { disponivel: !prod.disponivel })
    prod.disponivel = !prod.disponivel
    renderProdutos()
    toast.sucesso(prod.disponivel ? 'Produto ativado!' : 'Produto desativado!')
  } catch (err) { toast.erro(err.message) }
}

async function toggleDestaque(id) {
  const prod = produtos.find(p => p.id === id)
  if (!prod) return
  try {
    await api.put(`/api/admin/produtos/${id}`, { destaque: !prod.destaque })
    prod.destaque = !prod.destaque
    renderProdutos()
    toast.sucesso(prod.destaque ? 'Produto destacado!' : 'Destaque removido!')
  } catch (err) { toast.erro(err.message) }
}

// ── Ajuste rápido de estoque ──────────────────────────────────────────────────

async function ajustarEstoqueProdutoRapido(operacao, valor) {
  if (!produtoEditando) return
  try {
    const atualizado = await api.patch(
      `/api/admin/produtos/${produtoEditando.id}/estoque`,
      { operacao, valor }
    )
    // Atualiza display e estado local sem recarregar tudo
    $('#produto-estoque-atual').value = atualizado.estoque_atual
    produtoEditando.estoque_atual = atualizado.estoque_atual
    // Atualiza na lista em memória também
    const idx = produtos.findIndex(p => p.id === produtoEditando.id)
    if (idx !== -1) produtos[idx].estoque_atual = atualizado.estoque_atual
    renderProdutos()
    toast.sucesso(`Estoque: ${atualizado.estoque_atual}`)
  } catch (err) { toast.erro(err.message) }
}

async function ajustarEstoqueOpcaoRapido(operacao, valor) {
  if (!opcaoEditando) return
  try {
    const atualizado = await api.patch(
      `/api/admin/modificadores/opcoes/${opcaoEditando.id}/estoque`,
      { operacao, valor }
    )
    $('#opcao-estoque-atual').value = atualizado.estoque_atual
    opcaoEditando.estoque_atual = atualizado.estoque_atual
    toast.sucesso(`Estoque: ${atualizado.estoque_atual}`)
  } catch (err) { toast.erro(err.message) }
}

function confirmarExcluirProduto(id, nome) {
  abrirConfirmacao(`Excluir o produto "${nome}"?`, async () => {
    try {
      await api.delete(`/api/admin/produtos/${id}`)
      toast.sucesso('Produto excluído!')
      await carregarDados()
    } catch (err) { toast.erro(err.message) }
  })
}


/* ══════════════════════════════════════════════════════════
   MODIFICADORES (modal por produto — fluxo legado)
   ══════════════════════════════════════════════════════════ */

function getProdutoAtual() {
  return produtos.find(p => p.id === modProdutoId)
}

function abrirModalModificadores(produtoId) {
  modProdutoId = produtoId
  const prod = getProdutoAtual()
  if (!prod) return

  $('#modal-modificadores-titulo').textContent = `Modificadores — ${prod.nome}`
  renderModificadores()
  $('#modal-modificadores').classList.remove('hidden')
}

function fecharModalModificadores() {
  $('#modal-modificadores').classList.add('hidden')
  modProdutoId = null
}

function renderModificadores() {
  const prod = getProdutoAtual()
  if (!prod) return

  const grupos = prod.grupos_modificadores || []
  const lista = $('#modificadores-lista')
  const vazio = $('#modificadores-vazio')

  if (grupos.length === 0) {
    lista.innerHTML = ''
    vazio.classList.remove('hidden')
    return
  }

  vazio.classList.add('hidden')
  lista.innerHTML = grupos.map(grupo => {
    const obrigTag = grupo.obrigatorio
      ? '<span class="badge badge-erro" style="font-size:.7rem">Obrigatório</span>'
      : '<span class="badge badge-aviso" style="font-size:.7rem">Opcional</span>'

    const selecaoInfo = `Selecionar ${grupo.selecao_minima}–${grupo.selecao_maxima}`

    const opcoesHtml = (grupo.modificadores || []).map(mod => `
      <div class="mod-opcao">
        <div class="mod-opcao-info">
          <span class="${mod.disponivel ? '' : 'text-terc'}">${esc(mod.nome)}</span>
          ${mod.preco_adicional > 0 ? `<span class="mod-opcao-preco">+${formatarPreco(mod.preco_adicional)}</span>` : ''}
          ${!mod.disponivel ? '<span class="badge badge-erro" style="font-size:.65rem">Indisponível</span>' : ''}
        </div>
        <div class="mod-opcao-acoes">
          <button class="btn btn-secondary btn-sm" onclick="abrirModalOpcao(${grupo.id}, ${mod.id})" title="Editar">${icons.editar}</button>
          <button class="btn btn-danger btn-sm" onclick="confirmarExcluirOpcao(${mod.id}, '${esc(mod.nome)}')" title="Excluir">${icons.excluir}</button>
        </div>
      </div>
    `).join('')

    return `
      <div class="mod-grupo">
        <div class="mod-grupo-header">
          <div class="mod-grupo-info">
            <strong>${esc(grupo.nome)}</strong>
            ${obrigTag}
            <span class="text-terc" style="font-size:.78rem">${selecaoInfo}</span>
          </div>
          <div class="mod-grupo-acoes">
            <button class="btn btn-secondary btn-sm" onclick="abrirModalOpcao(${grupo.id})" title="Nova opção">+ Opção</button>
            <button class="btn btn-secondary btn-sm" onclick="abrirModalGrupo(${grupo.id})" title="Editar grupo">${icons.editar}</button>
            <button class="btn btn-danger btn-sm" onclick="confirmarDesvincularGrupo(${grupo.id}, '${esc(grupo.nome)}')" title="Remover do produto">${icons.excluir}</button>
          </div>
        </div>
        <div class="mod-opcoes">
          ${opcoesHtml || '<p class="text-terc" style="padding:8px 0;font-size:.85rem">Nenhuma opção adicionada.</p>'}
        </div>
      </div>
    `
  }).join('')
}


/* ── Modal Grupo (por produto) ── */

function abrirModalGrupo(grupoId = null) {
  const prod = getProdutoAtual()
  if (!prod) return

  grupoEditando = grupoId
    ? (prod.grupos_modificadores || []).find(g => g.id === grupoId)
    : null

  $('#modal-grupo-titulo').textContent = grupoEditando ? 'Editar grupo' : 'Novo grupo'
  $('#grupo-nome').value = grupoEditando?.nome || ''
  $('#grupo-selecao-min').value = grupoEditando?.selecao_minima ?? 0
  $('#grupo-selecao-max').value = grupoEditando?.selecao_maxima ?? 1
  $('#grupo-ordem').value = 0
  $('#grupo-obrigatorio').checked = grupoEditando?.obrigatorio ?? false

  $('#modal-grupo').classList.remove('hidden')
  $('#grupo-nome').focus()
}

function fecharModalGrupo() {
  $('#modal-grupo').classList.add('hidden')
  grupoEditando = null
}

async function handleSubmitGrupo(e) {
  e.preventDefault()
  const btn = $('#btn-salvar-grupo')
  btn.disabled = true
  btn.textContent = 'Salvando…'

  const dados = {
    nome: $('#grupo-nome').value.trim(),
    obrigatorio: $('#grupo-obrigatorio').checked,
    selecao_minima: parseInt($('#grupo-selecao-min').value) || 0,
    selecao_maxima: parseInt($('#grupo-selecao-max').value) || 1,
  }

  try {
    if (grupoEditando) {
      await api.put(`/api/admin/grupos-modificadores/${grupoEditando.id}`, dados)
      toast.sucesso('Grupo atualizado!')
    } else {
      // Cria e vincula ao produto atual via rota legada
      await api.post(`/api/admin/produtos/${modProdutoId}/modificadores`, dados)
      toast.sucesso('Grupo criado!')
    }
    fecharModalGrupo()
    await recarregarModificadores()
  } catch (err) {
    toast.erro(err.message)
  } finally {
    btn.disabled = false
    btn.textContent = 'Salvar'
  }
}

function confirmarDesvincularGrupo(grupoId, nome) {
  const totalProdutos = (gruposGlobais.find(g => g.id === grupoId)?.total_produtos) || 0
  const aviso = totalProdutos > 1
    ? ` Este grupo está em ${totalProdutos} produtos — será removido apenas deste.`
    : ''
  abrirConfirmacao(`Remover o grupo "${nome}" deste produto?${aviso}`, async () => {
    try {
      await api.delete(`/api/admin/grupos-modificadores/${grupoId}/vinculos/${modProdutoId}`)
      toast.sucesso('Grupo removido do produto!')
      await recarregarModificadores()
    } catch (err) { toast.erro(err.message) }
  })
}


/* ── Modal Opção (por produto) ── */

function abrirModalOpcao(grupoId, opcaoId = null) {
  opcaoGrupoId = grupoId

  if (opcaoId) {
    const prod = getProdutoAtual()
    const grupo = (prod?.grupos_modificadores || []).find(g => g.id === grupoId)
    opcaoEditando = (grupo?.modificadores || []).find(m => m.id === opcaoId)
  } else {
    opcaoEditando = null
  }

  $('#modal-opcao-titulo').textContent = opcaoEditando ? 'Editar opção' : 'Nova opção'
  $('#opcao-nome').value = opcaoEditando?.nome || ''
  $('#opcao-preco').value = opcaoEditando?.preco_adicional ?? 0
  $('#opcao-disponivel').checked = opcaoEditando?.disponivel ?? true

  // Estoque da opção
  const controleOn = opcaoEditando?.controle_estoque ?? false
  $('#opcao-controle-estoque').checked = controleOn
  $('#opcao-estoque-atual').value = opcaoEditando?.estoque_atual ?? 0
  _togglePainelEstoqueOpcao(controleOn)
  $('#estoque-botoes-opcao').style.display = opcaoEditando ? '' : 'none'

  $('#modal-opcao').classList.remove('hidden')
  $('#opcao-nome').focus()
}

function fecharModalOpcao() {
  $('#modal-opcao').classList.add('hidden')
  opcaoEditando = null
  opcaoGrupoId = null
}

function _togglePainelEstoqueOpcao(on) {
  $('#painel-estoque-opcao').classList.toggle('hidden', !on)
}

async function handleSubmitOpcao(e) {
  e.preventDefault()
  const btn = $('#btn-salvar-opcao')
  btn.disabled = true
  btn.textContent = 'Salvando…'

  const dados = {
    nome: $('#opcao-nome').value.trim(),
    preco_adicional: parseFloat($('#opcao-preco').value) || 0,
    disponivel: $('#opcao-disponivel').checked,
  }

  try {
    if (opcaoEditando) {
      await api.put(`/api/admin/modificadores/opcoes/${opcaoEditando.id}`, dados)
      toast.sucesso('Opção atualizada!')
    } else {
      await api.post(`/api/admin/grupos-modificadores/${opcaoGrupoId}/opcoes`, dados)
      toast.sucesso('Opção adicionada!')
    }
    fecharModalOpcao()
    await recarregarModificadores()
  } catch (err) {
    toast.erro(err.message)
  } finally {
    btn.disabled = false
    btn.textContent = 'Salvar'
  }
}

function confirmarExcluirOpcao(opcaoId, nome) {
  abrirConfirmacao(`Excluir a opção "${nome}"?`, async () => {
    try {
      await api.delete(`/api/admin/modificadores/opcoes/${opcaoId}`)
      toast.sucesso('Opção excluída!')
      await recarregarModificadores()
    } catch (err) { toast.erro(err.message) }
  })
}

async function recarregarModificadores() {
  try {
    const [produtosAtualizados, gruposAtualizados] = await Promise.all([
      api.get('/api/admin/produtos'),
      api.get('/api/admin/grupos-modificadores'),
    ])
    produtos = produtosAtualizados
    gruposGlobais = gruposAtualizados
    renderProdutos()
    renderModificadores()
    renderGruposGlobais()
  } catch (err) {
    toast.erro('Erro ao recarregar: ' + err.message)
  }
}


/* ══════════════════════════════════════════════════════════
   GRUPOS GLOBAIS (3ª seção)
   ══════════════════════════════════════════════════════════ */

function renderGruposGlobais() {
  const tbody = $('#grupos-tbody')
  const vazio = $('#grupos-vazio')

  if (gruposGlobais.length === 0) {
    tbody.innerHTML = ''
    vazio.classList.remove('hidden')
    return
  }

  vazio.classList.add('hidden')
  tbody.innerHTML = gruposGlobais.map(grupo => {
    const totalOpcoes = grupo.modificadores?.length || 0
    const totalProdutos = grupo.total_produtos || 0
    const ativo = grupo.ativo !== false  // default true se campo ausente (migração pendente)
    const obrigTag = grupo.obrigatorio
      ? '<span class="badge badge-erro" style="font-size:.7rem">Sim</span>'
      : '<span class="badge badge-sucesso" style="font-size:.7rem">Não</span>'

    // Mini-badges de estoque por opção — visíveis direto na linha sem abrir o modal
    const opcoesComEstoque = (grupo.modificadores || []).filter(m => m.controle_estoque)
    const badgesOpcoes = opcoesComEstoque.length > 0
      ? `<br><span style="display:inline-flex;flex-wrap:wrap;gap:3px;margin-top:3px">${
          opcoesComEstoque.map(m =>
            m.estoque_atual <= 0
              ? `<span class="badge-estoque badge-estoque-zero" style="font-size:.62rem;margin-left:0">${esc(m.nome)}: 0</span>`
              : `<span class="badge-estoque badge-estoque-ok"  style="font-size:.62rem;margin-left:0">${esc(m.nome)}: ${m.estoque_atual}</span>`
          ).join('')
        }</span>`
      : ''

    return `
      <tr style="${ativo ? '' : 'opacity:.55'}">
        <td>
          <strong>${esc(grupo.nome)}</strong>
          ${badgesOpcoes}
        </td>
        <td>
          <span class="badge badge-aviso">${totalOpcoes}</span>
        </td>
        <td>
          <span class="${totalProdutos > 0 ? 'badge badge-sucesso' : 'text-terc'}" style="font-size:.8rem">
            ${totalProdutos > 0 ? `${totalProdutos} produto${totalProdutos > 1 ? 's' : ''}` : '—'}
          </span>
        </td>
        <td>${obrigTag}</td>
        <td>
          <button class="btn btn-sm ${ativo ? 'btn-secondary' : 'btn-danger'}"
                  onclick="toggleAtivoGrupo(${grupo.id})"
                  title="${ativo ? 'Desativar grupo' : 'Ativar grupo'}">
            ${ativo ? icons.check : icons.x_circulo}
          </button>
        </td>
        <td style="position:relative">
          <button class="btn btn-secondary btn-sm btn-dd-grupo" onclick="abrirDropdownGrupo(${grupo.id}, this)" title="Ações" style="padding:6px 8px">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width:16px;height:16px;vertical-align:middle"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.75a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5ZM12 12.75a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5ZM12 18.75a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5Z" /></svg>
          </button>
        </td>
      </tr>
    `
  }).join('')
}


/* ── Modal Grupo Global (criar/editar) ── */

function abrirModalGrupoGlobal(grupoId = null) {
  grupoGlobalEditando = grupoId ? gruposGlobais.find(g => g.id === grupoId) : null

  $('#modal-grupo-global-titulo').textContent = grupoGlobalEditando ? 'Editar grupo' : 'Novo grupo'
  $('#gg-nome').value = grupoGlobalEditando?.nome || ''
  $('#gg-selecao-max').value = grupoGlobalEditando?.selecao_maxima ?? 1
  $('#gg-obrigatorio').checked = grupoGlobalEditando?.obrigatorio ?? false

  $('#modal-grupo-global').classList.remove('hidden')
  $('#gg-nome').focus()
}

function fecharModalGrupoGlobal() {
  $('#modal-grupo-global').classList.add('hidden')
  grupoGlobalEditando = null
}

async function handleSubmitGrupoGlobal(e) {
  e.preventDefault()
  const btn = $('#btn-salvar-grupo-global')
  btn.disabled = true
  btn.textContent = 'Salvando…'

  const dados = {
    nome: $('#gg-nome').value.trim(),
    obrigatorio: $('#gg-obrigatorio').checked,
    selecao_minima: 0,
    selecao_maxima: Math.max(1, parseInt($('#gg-selecao-max').value) || 1),
  }

  try {
    if (grupoGlobalEditando) {
      await api.put(`/api/admin/grupos-modificadores/${grupoGlobalEditando.id}`, dados)
      toast.sucesso('Grupo atualizado!')
    } else {
      await api.post('/api/admin/grupos-modificadores', dados)
      toast.sucesso('Grupo criado!')
    }
    fecharModalGrupoGlobal()
    await recarregarGruposGlobais()
  } catch (err) {
    toast.erro(err.message)
  } finally {
    btn.disabled = false
    btn.textContent = 'Salvar'
  }
}

async function toggleAtivoGrupo(grupoId) {
  const grupo = gruposGlobais.find(g => g.id === grupoId)
  if (!grupo) return
  const novoAtivo = !grupo.ativo
  try {
    await api.put(`/api/admin/grupos-modificadores/${grupoId}`, { ativo: novoAtivo })
    grupo.ativo = novoAtivo        // atualiza local — sem re-fetch, sem flicker
    renderGruposGlobais()
    toast.sucesso(novoAtivo ? 'Grupo ativado!' : 'Grupo desativado!')
  } catch (err) { toast.erro(err.message) }
}

function confirmarExcluirGrupoGlobal(grupoId, nome, totalProdutos) {
  const aviso = totalProdutos > 0
    ? ` Ele está vinculado a ${totalProdutos} produto${totalProdutos > 1 ? 's' : ''} e será removido de todos.`
    : ''
  abrirConfirmacao(`Excluir o grupo "${nome}" e todas suas opções?${aviso}`, async () => {
    try {
      await api.delete(`/api/admin/grupos-modificadores/${grupoId}`)
      toast.sucesso('Grupo excluído!')
      await recarregarGruposGlobais()
    } catch (err) { toast.erro(err.message) }
  })
}


/* ── Modal Opções do Grupo Global ── */

function abrirModalOpcoesGrupo(grupoId) {
  grupoOpcoesSelecionado = gruposGlobais.find(g => g.id === grupoId)
  if (!grupoOpcoesSelecionado) return

  $('#modal-opcoes-grupo-titulo').textContent = `Opções — ${grupoOpcoesSelecionado.nome}`
  renderOpcoesGrupoGlobal()
  $('#modal-opcoes-grupo').classList.remove('hidden')
}

function fecharModalOpcoesGrupo() {
  $('#modal-opcoes-grupo').classList.add('hidden')
  grupoOpcoesSelecionado = null
  opcaoGlobalEditando = null
  renderGruposGlobais()  // atualiza badges de estoque na tabela sem re-fetch
}

function renderOpcoesGrupoGlobal() {
  const grupo = grupoOpcoesSelecionado
  if (!grupo) return

  const opcoes = grupo.modificadores || []
  const lista = $('#opcoes-grupo-lista')
  const vazio = $('#opcoes-grupo-vazio')

  if (opcoes.length === 0) {
    lista.innerHTML = ''
    vazio.classList.remove('hidden')
    return
  }

  vazio.classList.add('hidden')
  lista.innerHTML = opcoes.map(mod => {
    const esgotadoPorEstoque = mod.controle_estoque && mod.estoque_atual <= 0
    const esgotado = !mod.disponivel || esgotadoPorEstoque
    let badgeOpcao = ''
    if (!mod.disponivel || esgotadoPorEstoque) {
      badgeOpcao = '<span class="badge badge-erro" style="font-size:.65rem">Esgotado</span>'
    } else if (mod.controle_estoque) {
      badgeOpcao = `<span class="badge-estoque badge-estoque-ok" style="font-size:.65rem">Est. ${mod.estoque_atual}</span>`
    }

    return `
    <div class="mod-opcao" style="will-change:opacity;${esgotado ? 'opacity:.5' : ''}">
      <div class="mod-opcao-info">
        <span>${esc(mod.nome)}</span>
        ${mod.preco_adicional > 0 ? `<span class="mod-opcao-preco">+${formatarPreco(mod.preco_adicional)}</span>` : ''}
        ${badgeOpcao}
      </div>
      <div class="mod-opcao-acoes">
        <button class="btn btn-sm ${mod.disponivel ? 'btn-secondary' : 'btn-danger'}"
                onclick="toggleDisponivelOpcao(${mod.id})"
                title="${mod.disponivel ? 'Disponível — clique para esgotar' : 'Esgotado — clique para reativar'}">
          ${mod.disponivel ? icons.check : icons.x_circulo}
        </button>
        <button class="btn btn-secondary btn-sm" onclick="abrirModalOpcaoGlobal(${mod.id})" title="Editar">${icons.editar}</button>
        <button class="btn btn-danger btn-sm" onclick="confirmarExcluirOpcaoGlobal(${mod.id}, '${esc(mod.nome)}')" title="Excluir">${icons.excluir}</button>
      </div>
    </div>
  `}).join('')
}

function abrirModalOpcaoGlobal(opcaoId = null) {
  if (!grupoOpcoesSelecionado) return
  opcaoGlobalEditando = opcaoId
    ? (grupoOpcoesSelecionado.modificadores || []).find(m => m.id === opcaoId)
    : null

  // Usa os mesmos campos do modal de opção compartilhado
  $('#modal-opcao-titulo').textContent = opcaoGlobalEditando ? 'Editar opção' : 'Nova opção'
  $('#opcao-nome').value = opcaoGlobalEditando?.nome || ''
  $('#opcao-preco').value = opcaoGlobalEditando?.preco_adicional ?? 0
  $('#opcao-disponivel').checked = opcaoGlobalEditando?.disponivel ?? true

  // Estoque da opção global
  const controleOnG = opcaoGlobalEditando?.controle_estoque ?? false
  $('#opcao-controle-estoque').checked = controleOnG
  $('#opcao-estoque-atual').value = opcaoGlobalEditando?.estoque_atual ?? 0
  _togglePainelEstoqueOpcao(controleOnG)
  $('#estoque-botoes-opcao').style.display = opcaoGlobalEditando ? '' : 'none'
  // ajustarEstoqueOpcaoRapido usa opcaoEditando — aqui é o contexto global
  opcaoEditando = opcaoGlobalEditando

  $('#modal-opcao').classList.remove('hidden')
  $('#opcao-nome').focus()
}

async function handleSubmitOpcaoUnificado(e) {
  e.preventDefault()
  const btn = $('#btn-salvar-opcao')
  btn.disabled = true
  btn.textContent = 'Salvando…'

  const dados = {
    nome: $('#opcao-nome').value.trim(),
    preco_adicional: parseFloat($('#opcao-preco').value) || 0,
    disponivel: $('#opcao-disponivel').checked,
    controle_estoque: $('#opcao-controle-estoque').checked,
    estoque_atual: parseInt($('#opcao-estoque-atual').value) || 0,
  }

  // Contexto: modal de opções do grupo global está aberto
  const contextoGlobal = !$('#modal-opcoes-grupo').classList.contains('hidden') && grupoOpcoesSelecionado

  try {
    if (contextoGlobal) {
      if (opcaoGlobalEditando) {
        await api.put(`/api/admin/modificadores/opcoes/${opcaoGlobalEditando.id}`, dados)
        toast.sucesso('Opção atualizada!')
      } else {
        await api.post(`/api/admin/grupos-modificadores/${grupoOpcoesSelecionado.id}/opcoes`, dados)
        toast.sucesso('Opção adicionada!')
      }
      fecharModalOpcao()
      await recarregarGruposGlobais()
      // Reabre modal de opções com dados frescos
      const grupoAtualizado = gruposGlobais.find(g => g.id === grupoOpcoesSelecionado?.id)
      if (grupoAtualizado) {
        grupoOpcoesSelecionado = grupoAtualizado
        renderOpcoesGrupoGlobal()
        $('#modal-opcoes-grupo').classList.remove('hidden')
      }
    } else {
      // Contexto: modificador por produto
      if (opcaoEditando) {
        await api.put(`/api/admin/modificadores/opcoes/${opcaoEditando.id}`, dados)
        toast.sucesso('Opção atualizada!')
      } else {
        await api.post(`/api/admin/grupos-modificadores/${opcaoGrupoId}/opcoes`, dados)
        toast.sucesso('Opção adicionada!')
      }
      fecharModalOpcao()
      await recarregarModificadores()
    }
  } catch (err) {
    toast.erro(err.message)
  } finally {
    btn.disabled = false
    btn.textContent = 'Salvar'
  }
}

function confirmarExcluirOpcaoGlobal(opcaoId, nome) {
  abrirConfirmacao(`Excluir a opção "${nome}"?`, async () => {
    try {
      await api.delete(`/api/admin/modificadores/opcoes/${opcaoId}`)
      toast.sucesso('Opção excluída!')
      await recarregarGruposGlobais()
      const grupoAtualizado = gruposGlobais.find(g => g.id === grupoOpcoesSelecionado?.id)
      if (grupoAtualizado && !$('#modal-opcoes-grupo').classList.contains('hidden')) {
        grupoOpcoesSelecionado = grupoAtualizado
        renderOpcoesGrupoGlobal()
      }
    } catch (err) { toast.erro(err.message) }
  })
}

async function toggleDisponivelOpcao(opcaoId) {
  if (!grupoOpcoesSelecionado) return
  const mod = (grupoOpcoesSelecionado.modificadores || []).find(m => m.id === opcaoId)
  if (!mod) return

  try {
    await api.put(`/api/admin/modificadores/opcoes/${opcaoId}`, { disponivel: !mod.disponivel })
    mod.disponivel = !mod.disponivel
    renderOpcoesGrupoGlobal()
  } catch (err) {
    toast.erro(err.message)
  }
}


/* ── Modal Vincular ── */

function abrirModalVincular(grupoId) {
  grupoVincularId = grupoId
  const grupo = gruposGlobais.find(g => g.id === grupoId)
  if (!grupo) return

  $('#vincular-nome-grupo').textContent = `"${grupo.nome}"`

  // Captura estado inicial de vínculos (para diff no save)
  vinculadosIniciais = new Set(
    produtos.filter(p => p.grupos_modificadores?.some(g => g.id === grupoId)).map(p => p.id)
  )

  // Monta lista hierárquica: categoria → produtos
  const listEl = $('#v-lista-hierarquica')
  if (categorias.length === 0) {
    listEl.innerHTML = '<p class="text-terc" style="font-size:.85rem;padding:8px 0">Nenhuma categoria cadastrada.</p>'
  } else {
    let html = ''
    for (const cat of categorias) {
      const prodsCat = produtos.filter(p => p.categoria_id === cat.id)
      if (prodsCat.length === 0) continue   // pula categorias sem produtos

      const vinculadosNaCat = prodsCat.filter(p => vinculadosIniciais.has(p.id)).length
      const catChecked      = vinculadosNaCat === prodsCat.length ? 'checked' : ''
      const catIndet        = vinculadosNaCat > 0 && vinculadosNaCat < prodsCat.length

      html += `<div class="v-cat-grupo" style="padding:6px 0 2px">
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer;padding:3px 0;user-select:none">
          <input type="checkbox" class="vp-categoria" data-cat="${cat.id}" ${catChecked} />
          <span style="font-weight:600;font-size:.88rem">${esc(cat.nome)}</span>
          <span class="text-terc" style="font-size:.74rem;font-weight:normal">${prodsCat.length} produto${prodsCat.length !== 1 ? 's' : ''}</span>
        </label>`

      for (const p of prodsCat) {
        const checked = vinculadosIniciais.has(p.id)
        html += `
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer;padding:2px 0 2px 22px;user-select:none">
          <input type="checkbox" class="vp-produto" data-cat="${cat.id}" value="${p.id}" ${checked ? 'checked' : ''} />
          <span style="font-size:.85rem">${esc(p.nome)}</span>
          ${checked ? '<span class="badge badge-sucesso" style="font-size:.62rem;flex-shrink:0">vinculado</span>' : ''}
        </label>`
      }

      html += '</div>'
      // Separador sutil entre categorias
      html += '<div style="border-top:1px solid var(--borda);margin:2px 0;opacity:.4"></div>'
    }
    listEl.innerHTML = html || '<p class="text-terc" style="font-size:.85rem;padding:8px 0">Nenhum produto cadastrado.</p>'

    // Aplica estado indeterminado (só via JS)
    listEl.querySelectorAll('.vp-categoria').forEach(cb => {
      const catId = cb.dataset.cat
      const prods = listEl.querySelectorAll(`.vp-produto[data-cat="${catId}"]`)
      const total   = prods.length
      const marcados = Array.from(prods).filter(c => c.checked).length
      cb.indeterminate = marcados > 0 && marcados < total
    })
  }

  $('#modal-vincular').classList.remove('hidden')
}

/* Checkbox de categoria: marca/desmarca todos os filhos */
function _vCatChange(catCb) {
  const catId  = catCb.dataset.cat
  const checked = catCb.checked
  catCb.indeterminate = false
  $('#v-lista-hierarquica').querySelectorAll(`.vp-produto[data-cat="${catId}"]`).forEach(cb => {
    cb.checked = checked
  })
}

/* Checkbox de produto: atualiza estado da categoria pai */
function _vProdChange(prodCb) {
  const catId  = prodCb.dataset.cat
  const lista  = $('#v-lista-hierarquica')
  const prods  = lista.querySelectorAll(`.vp-produto[data-cat="${catId}"]`)
  const total   = prods.length
  const marcados = Array.from(prods).filter(c => c.checked).length
  const catCb  = lista.querySelector(`.vp-categoria[data-cat="${catId}"]`)
  if (!catCb) return
  catCb.checked      = marcados === total
  catCb.indeterminate = marcados > 0 && marcados < total
}

function fecharModalVincular() {
  $('#modal-vincular').classList.add('hidden')
  grupoVincularId = null
  vinculadosIniciais = new Set()
}

async function handleConfirmarVincular() {
  // Coleta IDs marcados na lista hierárquica
  const checks   = $('#v-lista-hierarquica').querySelectorAll('.vp-produto:checked')
  const idsDepois = new Set(Array.from(checks).map(c => parseInt(c.value)))

  const adicionar = [...idsDepois].filter(id => !vinculadosIniciais.has(id))
  const remover   = [...vinculadosIniciais].filter(id => !idsDepois.has(id))

  if (adicionar.length === 0 && remover.length === 0) {
    toast.sucesso('Nenhuma alteração nos vínculos.')
    fecharModalVincular()
    return
  }

  const btn = $('#btn-confirmar-vincular')
  btn.disabled = true
  btn.textContent = 'Salvando…'

  try {
    let totalVinculados = 0
    let totalDesvinculados = 0

    // Vincula novos em batch
    if (adicionar.length > 0) {
      const res = await api.post(
        `/api/admin/grupos-modificadores/${grupoVincularId}/vincular`,
        { modo: 'produtos', produtos_ids: adicionar }
      )
      totalVinculados = res.vinculados
    }

    // Desvincula removidos (um por um — backend aceita individual)
    for (const prodId of remover) {
      await api.delete(`/api/admin/grupos-modificadores/${grupoVincularId}/vinculos/${prodId}`)
      totalDesvinculados++
    }

    const partes = []
    if (totalVinculados   > 0) partes.push(`${totalVinculados} vinculado${totalVinculados !== 1 ? 's' : ''}`)
    if (totalDesvinculados > 0) partes.push(`${totalDesvinculados} desvinculado${totalDesvinculados !== 1 ? 's' : ''}`)
    toast.sucesso(partes.length ? partes.join(', ') + '.' : 'Salvo!')

    fecharModalVincular()
    await carregarDados()
  } catch (err) {
    toast.erro(err.message)
  } finally {
    btn.disabled = false
    btn.textContent = 'Salvar'
  }
}

/* ── Dropdowns de ações ── */

function abrirDropdownCategoria(catId, btnEl) {
  if (dropdownCategoriaId === catId) { fecharDropdownCategoria(); return }
  fecharDropdowns()
  dropdownCategoriaId = catId
  _posicionarDropdown($('#dropdown-acoes-categoria'), btnEl)
}

function fecharDropdownCategoria() {
  $('#dropdown-acoes-categoria').classList.add('hidden')
  dropdownCategoriaId = null
}

function abrirDropdownGrupo(grupoId, btnEl) {
  if (dropdownGrupoId === grupoId) { fecharDropdownGrupo(); return }
  fecharDropdowns()
  dropdownGrupoId = grupoId
  _posicionarDropdown($('#dropdown-acoes-grupo'), btnEl)
}

function fecharDropdownGrupo() {
  $('#dropdown-acoes-grupo').classList.add('hidden')
  dropdownGrupoId = null
}

function abrirDropdownProduto(produtoId, btnEl) {
  if (dropdownProdutoId === produtoId) { fecharDropdownProduto(); return }
  fecharDropdowns()
  dropdownProdutoId = produtoId
  _posicionarDropdown($('#dropdown-acoes-produto'), btnEl)
}

function fecharDropdownProduto() {
  $('#dropdown-acoes-produto').classList.add('hidden')
  dropdownProdutoId = null
}

function fecharDropdowns() {
  fecharDropdownCategoria()
  fecharDropdownGrupo()
  fecharDropdownProduto()
}

function _posicionarDropdown(menu, btnEl) {
  // Mostra off-screen para medir altura real antes de posicionar
  menu.style.visibility = 'hidden'
  menu.classList.remove('hidden')

  const rect  = btnEl.getBoundingClientRect()
  const menuH = menu.offsetHeight
  const viewH = window.innerHeight
  const GAP   = 4

  // Vertical: abre para baixo se couber, senão flip para cima
  const top = (viewH - rect.bottom - GAP) >= menuH
    ? rect.bottom + GAP                     // padrão: abaixo do botão
    : Math.max(GAP, rect.top - menuH - GAP) // flip: acima do botão

  menu.style.top   = top + 'px'
  menu.style.right = Math.max(GAP, window.innerWidth - rect.right) + 'px'
  menu.style.left  = 'auto'
  menu.style.visibility = ''
}

async function recarregarGruposGlobais() {
  try {
    gruposGlobais = await api.get('/api/admin/grupos-modificadores')
    renderGruposGlobais()
  } catch (err) {
    toast.erro('Erro ao recarregar grupos: ' + err.message)
  }
}


/* ══════════════════════════════════════════════════════════
   CONFIRMAÇÃO & HELPERS
   ══════════════════════════════════════════════════════════ */

function abrirConfirmacao(mensagem, callback) {
  confirmacaoCallback = callback
  $('#modal-confirmar-msg').textContent = mensagem
  $('#modal-confirmar').classList.remove('hidden')
}

function fecharConfirmacao() {
  $('#modal-confirmar').classList.add('hidden')
  confirmacaoCallback = null
}

function esc(str) {
  if (!str) return ''
  const el = document.createElement('span')
  el.textContent = str
  return el.innerHTML
}


/* ── ESC fecha o modal de topo ──────────────────────────── */

document.addEventListener('keydown', e => {
  if (e.key !== 'Escape') return
  // Fecha dropdowns antes de qualquer modal
  if (dropdownCategoriaId !== null || dropdownGrupoId !== null || dropdownProdutoId !== null) { fecharDropdowns(); return }
  // Ordem decrescente de z-index: 350 → 340 → 330 → 320 → 310 → ...
  if (!$('#modal-confirmar').classList.contains('hidden')) return fecharConfirmacao()
  if (!$('#modal-vincular').classList.contains('hidden')) return fecharModalVincular()
  if (!$('#modal-opcao').classList.contains('hidden')) return fecharModalOpcao()
  if (!$('#modal-opcoes-grupo').classList.contains('hidden')) return fecharModalOpcoesGrupo()
  if (!$('#modal-grupo-global').classList.contains('hidden')) return fecharModalGrupoGlobal()
  if (!$('#modal-grupo').classList.contains('hidden')) return fecharModalGrupo()
  if (!$('#modal-modificadores').classList.contains('hidden')) return fecharModalModificadores()
  if (!$('#modal-produto').classList.contains('hidden')) return fecharModalProduto()
  if (!$('#modal-categoria').classList.contains('hidden')) return fecharModalCategoria()
})
