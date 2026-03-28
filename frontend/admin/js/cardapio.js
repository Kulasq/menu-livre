/* ── Estado ─────────────────────────────────────────────── */

let categorias = []
let produtos = []
let categoriaEditando = null   // null = criando, obj = editando
let produtoEditando = null     // null = criando, obj = editando
let fotoParaUpload = null      // File selecionado para upload
let filtroCategoria = ''       // id da categoria para filtrar produtos
let confirmacaoCallback = null // callback do modal de confirmação


/* ── Inicialização ──────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {
  if (!auth.proteger()) return

  setupUsuario()
  setupSidebar()
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

  /* Filtro de categoria */
  $('#filtro-categoria').addEventListener('change', (e) => {
    filtroCategoria = e.target.value
    renderProdutos()
  })

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


/* ── Renderização — Categorias ──────────────────────────── */

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
          <button class="btn btn-secondary btn-sm" onclick="abrirModalCategoria(${cat.id})" title="Editar">✏️</button>
          <button class="btn btn-danger btn-sm" onclick="confirmarExcluirCategoria(${cat.id}, '${esc(cat.nome)}')" title="Excluir">🗑️</button>
        </div>
      </td>
    </tr>
  `).join('')
}


/* ── Renderização — Produtos ────────────────────────────── */

function renderProdutos() {
  const tbody = $('#produtos-tbody')
  const vazio = $('#produtos-vazio')

  let lista = produtos
  if (filtroCategoria) {
    lista = lista.filter(p => p.categoria_id === Number(filtroCategoria))
  }

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
      : `<div style="width:48px;height:48px;border-radius:6px;background:var(--borda);display:flex;align-items:center;justify-content:center;font-size:1.2rem">🍔</div>`

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
          <button class="btn btn-sm ${prod.disponivel ? 'btn-secondary' : 'btn-danger'}" onclick="toggleDisponivel(${prod.id})" title="${prod.disponivel ? 'Desativar' : 'Ativar'}">
            ${prod.disponivel ? '✅' : '❌'}
          </button>
        </td>
        <td>
          <button class="btn btn-sm ${prod.destaque ? 'btn-primary' : 'btn-secondary'}" onclick="toggleDestaque(${prod.id})" title="${prod.destaque ? 'Remover destaque' : 'Destacar'}">
            ${prod.destaque ? '⭐' : '☆'}
          </button>
        </td>
        <td>
          <div style="display:flex;gap:6px">
            <button class="btn btn-secondary btn-sm" onclick="abrirModalProduto(${prod.id})" title="Editar">✏️</button>
            <button class="btn btn-danger btn-sm" onclick="confirmarExcluirProduto(${prod.id}, '${esc(prod.nome)}')" title="Excluir">🗑️</button>
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


/* ── Modal Categoria ────────────────────────────────────── */

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

  if (categoriaEditando) {
    dados.ativo = $('#categoria-ativo').checked
  }

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


/* ── Modal Produto ──────────────────────────────────────── */

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

  /* Foto preview */
  atualizarPreviewFoto(produtoEditando?.foto_url || null)

  /* Resetar file input */
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
    const src = url.startsWith('blob:') ? url : `${CONFIG.API_URL}${url}`
    preview.src = src
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

  const tipos = ['image/jpeg', 'image/png', 'image/webp']
  if (!tipos.includes(file.type)) {
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

  /* Marca para remover a foto ao salvar */
  if (produtoEditando && produtoEditando.foto_url) {
    produtoEditando._removerFoto = true
  }
}

async function uploadImagem(file) {
  const token = localStorage.getItem(CONFIG.STORAGE.ACCESS_TOKEN)
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${CONFIG.API_URL}/api/admin/upload`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData,
  })

  if (!res.ok) {
    const erro = await res.json().catch(() => null)
    throw new Error(erro?.detail || 'Erro no upload da imagem')
  }

  const data = await res.json()
  return data.url
}

async function handleSubmitProduto(e) {
  e.preventDefault()
  const btn = $('#btn-salvar-produto')
  btn.disabled = true
  btn.textContent = 'Salvando…'

  try {
    /* Upload da foto se houver */
    let fotoUrl = produtoEditando?.foto_url || null
    if (fotoParaUpload) {
      fotoUrl = await uploadImagem(fotoParaUpload)
    } else if (produtoEditando?._removerFoto) {
      fotoUrl = null
    }

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

    if (!dados.categoria_id) {
      toast.erro('Selecione uma categoria.')
      return
    }

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


/* ── Toggles rápidos ────────────────────────────────────── */

async function toggleDisponivel(id) {
  const prod = produtos.find(p => p.id === id)
  if (!prod) return
  try {
    await api.put(`/api/admin/produtos/${id}`, { disponivel: !prod.disponivel })
    prod.disponivel = !prod.disponivel
    renderProdutos()
    toast.sucesso(prod.disponivel ? 'Produto ativado!' : 'Produto desativado!')
  } catch (err) {
    toast.erro(err.message)
  }
}

async function toggleDestaque(id) {
  const prod = produtos.find(p => p.id === id)
  if (!prod) return
  try {
    await api.put(`/api/admin/produtos/${id}`, { destaque: !prod.destaque })
    prod.destaque = !prod.destaque
    renderProdutos()
    toast.sucesso(prod.destaque ? 'Produto destacado!' : 'Destaque removido!')
  } catch (err) {
    toast.erro(err.message)
  }
}


/* ── Exclusão ───────────────────────────────────────────── */

function confirmarExcluirCategoria(id, nome) {
  abrirConfirmacao(`Excluir a categoria "${nome}"?`, async () => {
    try {
      await api.delete(`/api/admin/categorias/${id}`)
      toast.sucesso('Categoria excluída!')
      await carregarDados()
    } catch (err) {
      toast.erro(err.message)
    }
  })
}

function confirmarExcluirProduto(id, nome) {
  abrirConfirmacao(`Excluir o produto "${nome}"?`, async () => {
    try {
      await api.delete(`/api/admin/produtos/${id}`)
      toast.sucesso('Produto excluído!')
      await carregarDados()
    } catch (err) {
      toast.erro(err.message)
    }
  })
}


/* ── Modal Confirmação ──────────────────────────────────── */

function abrirConfirmacao(mensagem, callback) {
  confirmacaoCallback = callback
  $('#modal-confirmar-msg').textContent = mensagem
  $('#modal-confirmar').classList.remove('hidden')
}

function fecharConfirmacao() {
  $('#modal-confirmar').classList.add('hidden')
  confirmacaoCallback = null
}


/* ── Helpers ────────────────────────────────────────────── */

function esc(str) {
  if (!str) return ''
  const el = document.createElement('span')
  el.textContent = str
  return el.innerHTML
}