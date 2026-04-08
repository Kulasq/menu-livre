/* ── Estado ─────────────────────────────────────────────── */

let categorias = []
let produtos = []
let categoriaEditando = null
let produtoEditando = null
let fotoParaUpload = null
let filtroCategoria = ''
let confirmacaoCallback = null

/* Estado dos modificadores */
let modProdutoId = null        // produto cujos modificadores estão abertos
let grupoEditando = null       // null = criando, obj = editando
let opcaoEditando = null       // null = criando, obj = editando
let opcaoGrupoId = null        // grupo ao qual a opção pertence


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

  /* Filtro */
  $('#filtro-categoria').addEventListener('change', (e) => {
    filtroCategoria = e.target.value
    renderProdutos()
  })

  /* Modificadores */
  $('#modal-modificadores-fechar').addEventListener('click', fecharModalModificadores)
  $('#modal-modificadores-overlay').addEventListener('click', fecharModalModificadores)
  $('#btn-novo-grupo').addEventListener('click', () => abrirModalGrupo())

  /* Grupo */
  $('#form-grupo').addEventListener('submit', handleSubmitGrupo)
  $('#modal-grupo-fechar').addEventListener('click', fecharModalGrupo)
  $('#modal-grupo-overlay').addEventListener('click', fecharModalGrupo)
  $('#modal-grupo-cancelar').addEventListener('click', fecharModalGrupo)

  /* Opção */
  $('#form-opcao').addEventListener('submit', handleSubmitOpcao)
  $('#modal-opcao-fechar').addEventListener('click', fecharModalOpcao)
  $('#modal-opcao-overlay').addEventListener('click', fecharModalOpcao)
  $('#modal-opcao-cancelar').addEventListener('click', fecharModalOpcao)

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

    const [cats, prods] = await Promise.all([
      api.get('/api/admin/categorias'),
      api.get('/api/admin/produtos'),
    ])

    categorias = cats
    produtos = prods

    renderCategorias()
    renderProdutos()
    atualizarFiltroCategorias()
    atualizarSelectCategoria()
  } catch (err) {
    toast.erro('Erro ao carregar cardápio: ' + err.message)
  } finally {
    $('#categorias-loading').classList.add('hidden')
    $('#produtos-loading').classList.add('hidden')
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
    <tr>
      <td>
        <strong>${esc(cat.nome)}</strong>
        ${cat.descricao ? `<br><span class="text-terc" style="font-size:.82rem">${esc(cat.descricao)}</span>` : ''}
      </td>
      <td>${cat.ordem}</td>
      <td>
        <span class="badge ${cat.ativo ? 'badge-sucesso' : 'badge-erro'}">
          ${cat.ativo ? 'Ativa' : 'Inativa'}
        </span>
      </td>
      <td>
        <div style="display:flex;gap:6px">
          <button class="btn btn-secondary btn-sm" onclick="abrirModalCategoria(${cat.id})" title="Editar">${icons.editar}</button>
          <button class="btn btn-danger btn-sm" onclick="confirmarExcluirCategoria(${cat.id}, '${esc(cat.nome)}')" title="Excluir">${icons.excluir}</button>
        </div>
      </td>
    </tr>
  `).join('')
}

function abrirModalCategoria(id = null) {
  categoriaEditando = id ? categorias.find(c => c.id === id) : null
  $('#modal-categoria-titulo').textContent = categoriaEditando ? 'Editar categoria' : 'Nova categoria'
  $('#categoria-nome').value = categoriaEditando?.nome || ''
  $('#categoria-descricao').value = categoriaEditando?.descricao || ''
  $('#categoria-ordem').value = categoriaEditando?.ordem ?? 0

  const ativoGroup = $('#categoria-ativo-group')
  if (categoriaEditando) {
    ativoGroup.classList.remove('hidden')
    $('#categoria-ativo').checked = categoriaEditando.ativo
  } else {
    ativoGroup.classList.add('hidden')
  }

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
    descricao: $('#categoria-descricao').value.trim() || null,
    ordem: parseInt($('#categoria-ordem').value) || 0,
  }
  if (categoriaEditando) dados.ativo = $('#categoria-ativo').checked

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


/* ══════════════════════════════════════════════════════════
   PRODUTOS
   ══════════════════════════════════════════════════════════ */

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

    const modCount = prod.grupos_modificadores?.length || 0

    return `
      <tr>
        <td>${fotoHtml}</td>
        <td>
          <strong>${esc(prod.nome)}</strong>
          ${prod.descricao ? `<br><span class="text-terc" style="font-size:.82rem">${esc(prod.descricao).substring(0, 60)}${prod.descricao.length > 60 ? '…' : ''}</span>` : ''}
        </td>
        <td>${formatarPreco(prod.preco)}</td>
        <td><span class="badge badge-aviso">${cat ? esc(cat.nome) : '—'}</span></td>
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
        <td>
          <div style="display:flex;gap:6px">
            <button class="btn btn-secondary btn-sm" onclick="abrirModalModificadores(${prod.id})" title="Modificadores">
              ${icons.modificadores}${modCount > 0 ? `<span class="mod-badge">${modCount}</span>` : ''}
            </button>
            <button class="btn btn-secondary btn-sm" onclick="abrirModalProduto(${prod.id})" title="Editar">${icons.editar}</button>
            <button class="btn btn-danger btn-sm" onclick="confirmarExcluirProduto(${prod.id}, '${esc(prod.nome)}')" title="Excluir">${icons.excluir}</button>
          </div>
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
  atualizarPreviewFoto(produtoEditando?.foto_url || null)
  $('#produto-foto-input').value = ''

  $('#modal-produto').classList.remove('hidden')
  $('#produto-nome').focus()
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
   MODIFICADORES
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
            <button class="btn btn-danger btn-sm" onclick="confirmarExcluirGrupo(${grupo.id}, '${esc(grupo.nome)}')" title="Excluir grupo">${icons.excluir}</button>
          </div>
        </div>
        <div class="mod-opcoes">
          ${opcoesHtml || '<p class="text-terc" style="padding:8px 0;font-size:.85rem">Nenhuma opção adicionada.</p>'}
        </div>
      </div>
    `
  }).join('')
}


/* ── Modal Grupo ── */

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
  $('#grupo-ordem').value = grupoEditando?.ordem ?? 0
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
    ordem: parseInt($('#grupo-ordem').value) || 0,
  }

  try {
    if (grupoEditando) {
      await api.put(`/api/admin/modificadores/${grupoEditando.id}`, dados)
      toast.sucesso('Grupo atualizado!')
    } else {
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

function confirmarExcluirGrupo(grupoId, nome) {
  abrirConfirmacao(`Excluir o grupo "${nome}" e todas suas opções?`, async () => {
    try {
      await api.delete(`/api/admin/modificadores/${grupoId}`)
      toast.sucesso('Grupo excluído!')
      await recarregarModificadores()
    } catch (err) { toast.erro(err.message) }
  })
}


/* ── Modal Opção ── */

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

  $('#modal-opcao').classList.remove('hidden')
  $('#opcao-nome').focus()
}

function fecharModalOpcao() {
  $('#modal-opcao').classList.add('hidden')
  opcaoEditando = null
  opcaoGrupoId = null
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
      await api.post(`/api/admin/modificadores/${opcaoGrupoId}/opcoes`, dados)
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


/* ── Recarregar modificadores ── */

async function recarregarModificadores() {
  try {
    const produtosAtualizados = await api.get('/api/admin/produtos')
    produtos = produtosAtualizados
    renderProdutos()
    renderModificadores()
  } catch (err) {
    toast.erro('Erro ao recarregar: ' + err.message)
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