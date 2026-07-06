/* frontend/admin/js/configuracoes.js */

const DIAS = [
  { key: 'domingo', label: 'Domingo' },
  { key: 'segunda', label: 'Segunda' },
  { key: 'terca',   label: 'Terça'   },
  { key: 'quarta',  label: 'Quarta'  },
  { key: 'quinta',  label: 'Quinta'  },
  { key: 'sexta',   label: 'Sexta'   },
  { key: 'sabado',  label: 'Sábado'  },
]

// Paleta padrão Menu Livre — espelha o admin.css
const CORES_PADRAO = {
  cor_primaria:   '#f59e0b',
  cor_secundaria: '#d97706',
  cor_fundo:      '#f1f5f9',
  cor_fonte:      '#0f172a',
  cor_banner:     '#0f172a',
}

// Mapeamento campo → CSS variable do preview
const PREVIEW_MAP = {
  cor_primaria:   '--preview-primaria',
  cor_secundaria: '--preview-secundaria',
  cor_fundo:      '--preview-fundo',
  cor_fonte:      '--preview-fonte',
  cor_banner:     '--preview-banner',
}

document.addEventListener('DOMContentLoaded', () => {
  if (!auth.proteger()) return

  _setupUsuario()
  _setupSidebar()
  _buildHorarios()
  _setupCores()
  _carregarConfiguracoes()
  _setupImpressao()
  _setupVerificarEndereco()

  $('#form-config').addEventListener('submit', _salvarConfiguracoes)
  $('#btn-toggle-loja').addEventListener('click', _toggleStatusLoja)
  $('#btn-restaurar-cores').addEventListener('click', _restaurarCoresPadrao)
})

function _setupVerificarEndereco() {
  $('#btn-verificar-endereco').addEventListener('click', () => {
    const endereco = $('#inp-endereco').value.trim()
    if (!endereco) {
      toast.aviso('Preencha o endereço antes de verificar.')
      return
    }
    window.open('https://maps.google.com/?q=' + encodeURIComponent(endereco), '_blank', 'noopener')
  })
}

function _setupImpressao() {
  const salvo = localStorage.getItem('impressao_largura') || '80mm'
  const radio = document.querySelector(`input[name="impressao-largura"][value="${salvo}"]`)
  if (radio) radio.checked = true

  document.querySelectorAll('input[name="impressao-largura"]').forEach(r => {
    r.addEventListener('change', () => {
      localStorage.setItem('impressao_largura', r.value)
    })
  })
}

// ── Usuário / Sidebar ─────────────────────────────────────────────────────────

function _setupUsuario() {
  const u = auth.getUsuario()
  $('#header-usuario-nome').textContent = u.nome
  const iniciais = u.nome.split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase()
  $('#header-usuario-avatar').textContent = iniciais
}

function _setupSidebar() {
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

// ── Horários ──────────────────────────────────────────────────────────────────

function _buildHorarios() {
  const lista = $('#horarios-lista')
  lista.innerHTML = DIAS.map(({ key, label }) => `
    <div class="horario-dia">
      <div class="horario-dia-header">
        <label class="toggle" aria-label="${label} aberto">
          <input type="checkbox" id="dia-${key}-aberto" data-dia="${key}" class="dia-toggle" />
          <span class="toggle-slider"></span>
        </label>
        <span class="horario-dia-nome">${label}</span>
      </div>
      <div class="horario-dia-campos hidden" id="dia-${key}-campos">
        <div class="intervalos-lista" id="dia-${key}-intervalos"></div>
        <button type="button" class="btn-add-intervalo" data-dia="${key}">+ Adicionar horário</button>
      </div>
    </div>
  `).join('')

  lista.addEventListener('change', (e) => {
    const input = e.target.closest('.dia-toggle')
    if (!input) return
    const key = input.dataset.dia
    $(`#dia-${key}-campos`).classList.toggle('hidden', !input.checked)
    // ao abrir um dia sem intervalos, garante ao menos uma linha
    if (input.checked && $(`#dia-${key}-intervalos`).children.length === 0) {
      _addIntervalo(key)
    }
  })

  lista.addEventListener('click', (e) => {
    const add = e.target.closest('.btn-add-intervalo')
    if (add) { _addIntervalo(add.dataset.dia); return }

    const remover = e.target.closest('.btn-remover-intervalo')
    if (remover) {
      const container = remover.closest('.intervalos-lista')
      // mantém no mínimo 1 intervalo por dia aberto
      if (container.children.length > 1) remover.closest('.intervalo-linha').remove()
    }
  })
}

/** Cria uma linha de intervalo (início — fim — remover) como elemento DOM. */
function _criarLinhaIntervalo(inicio = '18:00', fim = '23:00') {
  const linha = document.createElement('div')
  linha.className = 'intervalo-linha'
  linha.innerHTML = `
    <input type="time" class="form-input intervalo-inicio" value="${inicio}" aria-label="Abertura" />
    <span class="intervalo-sep">às</span>
    <input type="time" class="form-input intervalo-fim" value="${fim}" aria-label="Fechamento" />
    <button type="button" class="btn-remover-intervalo" aria-label="Remover horário">${icons.excluir}</button>
  `
  return linha
}

/** Adiciona uma linha de intervalo ao container do dia. */
function _addIntervalo(key, inicio, fim) {
  $(`#dia-${key}-intervalos`).appendChild(_criarLinhaIntervalo(inicio, fim))
}

// ── Cores ─────────────────────────────────────────────────────────────────────

/**
 * Normaliza qualquer formato CSS de cor para hex (#rrggbb).
 * Usa o truque do canvas: o browser faz a conversão nativamente,
 * sem nenhuma biblioteca externa.
 */
function _normalizarParaHex(cor) {
  if (!cor || !cor.trim()) return null
  try {
    const canvas = document.createElement('canvas')
    canvas.width = canvas.height = 1
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#000000' // reset para detectar cor inválida
    ctx.fillStyle = cor.trim()
    const hex = ctx.fillStyle  // retorna '#rrggbb' ou 'rgba(r,g,b,a)'
    // ctx.fillStyle retorna '#000000' se a cor for inválida — checamos se mudou
    if (hex === '#000000' && cor.trim().toLowerCase() !== '#000000'
        && cor.trim().toLowerCase() !== 'black'
        && cor.trim().toLowerCase() !== 'rgb(0,0,0)'
        && cor.trim().toLowerCase() !== 'rgb(0, 0, 0)') {
      return null // cor inválida
    }
    // Se vier rgba, converte para hex (ignora alpha)
    if (hex.startsWith('rgba') || hex.startsWith('rgb')) {
      const m = hex.match(/\d+/g)
      if (!m || m.length < 3) return null
      return '#' + [m[0], m[1], m[2]]
        .map(n => parseInt(n).toString(16).padStart(2, '0'))
        .join('')
    }
    return hex // já é hex
  } catch {
    return null
  }
}

/** Configura os 5 pares de inputs (swatch + texto) */
function _setupCores() {
  const campos = Object.keys(CORES_PADRAO)

  campos.forEach(campo => {
    const swatch = $(`#swatch-${campo.replace(/_/g, '-')}`)
    const texto  = $(`#inp-${campo.replace(/_/g, '-')}`)

    // Swatch → texto (o picker sempre retorna hex)
    swatch.addEventListener('input', () => {
      texto.value = swatch.value
      _atualizarPreview(campo, swatch.value)
    })

    // Texto → swatch + preview (aceita qualquer formato CSS)
    texto.addEventListener('input', () => {
      const hex = _normalizarParaHex(texto.value)
      if (hex) {
        swatch.value = hex
        _atualizarPreview(campo, hex)
      }
    })

    // Ao sair do campo texto, normaliza o valor para hex
    texto.addEventListener('blur', () => {
      const hex = _normalizarParaHex(texto.value)
      if (hex) {
        texto.value = hex
        swatch.value = hex
      }
    })
  })
}

/** Atualiza a CSS variable do preview ao vivo */
function _atualizarPreview(campo, hex) {
  const cssVar = PREVIEW_MAP[campo]
  if (cssVar) {
    document.getElementById('preview-cores').style.setProperty(cssVar, hex)
  }
}

/** Preenche os inputs de cor a partir dos dados da API */
function _preencherCores(c) {
  const campos = Object.keys(CORES_PADRAO)
  campos.forEach(campo => {
    const valor = c[campo] || CORES_PADRAO[campo]
    const hex   = _normalizarParaHex(valor) || CORES_PADRAO[campo]
    const swatch = $(`#swatch-${campo.replace(/_/g, '-')}`)
    const texto  = $(`#inp-${campo.replace(/_/g, '-')}`)
    swatch.value = hex
    texto.value  = hex
    _atualizarPreview(campo, hex)
  })
}

function _confirmar(titulo, texto, onConfirmar) {
  const modal      = document.getElementById('modal-confirmacao')
  const overlay    = document.getElementById('modal-confirmacao-overlay')
  const btnOk      = document.getElementById('btn-confirmacao-ok')
  const btnCancelar = document.getElementById('btn-confirmacao-cancelar')

  document.getElementById('confirmacao-titulo').textContent = titulo
  document.getElementById('confirmacao-texto').textContent  = texto
  modal.classList.remove('hidden')

  function fechar() {
    modal.classList.add('hidden')
    btnOk.removeEventListener('click', handleOk)
    btnCancelar.removeEventListener('click', fechar)
    overlay.removeEventListener('click', fechar)
  }

  function handleOk() { fechar(); onConfirmar() }

  btnOk.addEventListener('click', handleOk)
  btnCancelar.addEventListener('click', fechar)
  overlay.addEventListener('click', fechar)
}

/** Restaura todos os campos de cor para os padrões Menu Livre */
function _restaurarCoresPadrao() {
  _confirmar(
    'Restaurar cores padrão',
    'Isso vai sobrescrever todas as cores personalizadas. A mudança só é salva quando você clicar em "Salvar configurações".',
    () => {
      Object.entries(CORES_PADRAO).forEach(([campo, hex]) => {
        const swatch = $(`#swatch-${campo.replace(/_/g, '-')}`)
        const texto  = $(`#inp-${campo.replace(/_/g, '-')}`)
        swatch.value = hex
        texto.value  = hex
        _atualizarPreview(campo, hex)
      })
      toast.sucesso('Cores restauradas para o padrão. Salve para aplicar.')
    }
  )
}

// ── Configurações ─────────────────────────────────────────────────────────────

async function _carregarConfiguracoes() {
  try {
    const config = await api.get('/api/admin/configuracoes')
    _preencherForm(config)
    _preencherCores(config)
    atualizarNomeLojaSidebar(config.nome_loja)
    $('#config-loading').classList.add('hidden')
    $('#form-config').classList.remove('hidden')
  } catch (err) {
    toast.erro('Erro ao carregar configurações: ' + err.message)
  }
}

function _atualizarStatusLoja(fechadoManualmente) {
  const btn  = $('#btn-toggle-loja')
  const desc = $('#loja-status-desc')
  btn._fechadoManualmente = fechadoManualmente
  if (fechadoManualmente) {
    desc.textContent = 'Loja fechada manualmente. Clientes não podem fazer pedidos.'
    btn.textContent  = 'Abrir loja'
    btn.className    = 'btn btn-sm btn-primary'
  } else {
    desc.textContent = 'Loja operando normalmente conforme os horários configurados.'
    btn.textContent  = 'Fechar loja agora'
    btn.className    = 'btn btn-sm btn-danger'
  }
}

async function _toggleStatusLoja() {
  const btn = $('#btn-toggle-loja')
  const novoEstado = !btn._fechadoManualmente
  btn.disabled = true
  try {
    await api.put('/api/admin/configuracoes', { fechado_manualmente: novoEstado })
    _atualizarStatusLoja(novoEstado)
    toast.sucesso(novoEstado ? 'Loja fechada manualmente.' : 'Loja aberta.')
  } catch (err) {
    toast.erro('Erro: ' + err.message)
  } finally {
    btn.disabled = false
  }
}

function _preencherForm(c) {
  $('#inp-nome-loja').value              = c.nome_loja             ?? ''
  $('#inp-whatsapp').value               = c.whatsapp              ?? ''
  $('#inp-instagram').value              = c.instagram_url         ?? ''
  $('#inp-endereco').value               = c.endereco              ?? ''
  $('#inp-maps-url').value               = c.maps_url              ?? ''
  $('#inp-chave-pix').value              = c.chave_pix             ?? ''
  $('#inp-tipo-pix').value               = c.tipo_chave_pix        ?? ''
  $('#inp-taxa').value                   = c.taxa_entrega          ?? 0
  $('#inp-minimo').value                 = c.pedido_minimo         ?? 0
  $('#inp-tempo-min').value              = c.tempo_entrega_min     ?? 30
  $('#inp-tempo-max').value              = c.tempo_entrega_max     ?? 50
  $('#inp-aceitar-agendamentos').checked = c.aceitar_agendamentos  ?? true
  $('#inp-limite-agendamentos').value    = c.limite_agendamentos   ?? 10
  $('#inp-msg-fechado').value            = c.mensagem_fechado      ?? ''
  _atualizarStatusLoja(c.fechado_manualmente ?? false)

  if (c.horarios) {
    DIAS.forEach(({ key }) => {
      const diaConfig = c.horarios[key]
      if (!diaConfig) return
      const toggle = $(`#dia-${key}-aberto`)
      toggle.checked = diaConfig.aberto
      $(`#dia-${key}-campos`).classList.toggle('hidden', !diaConfig.aberto)

      const container = $(`#dia-${key}-intervalos`)
      container.innerHTML = ''
      const intervalos = diaConfig.horarios || []
      intervalos.forEach(iv => _addIntervalo(key, iv.inicio, iv.fim))
      // dia aberto sem intervalos salvos: garante uma linha default para edição
      if (diaConfig.aberto && container.children.length === 0) _addIntervalo(key)
    })
  }
}

async function _salvarConfiguracoes(e) {
  e.preventDefault()

  const whatsapp = $('#inp-whatsapp').value.trim()
  if (!whatsapp) {
    toast.erro('WhatsApp é obrigatório.')
    $('#inp-whatsapp').focus()
    return
  }

  const horarios = {}
  for (const { key, label } of DIAS) {
    const aberto = $(`#dia-${key}-aberto`).checked
    if (!aberto) {
      horarios[key] = { aberto: false, horarios: [] }
      continue
    }

    // coleta os intervalos preenchidos do dia
    const intervalos = [...document.querySelectorAll(`#dia-${key}-intervalos .intervalo-linha`)]
      .map(linha => ({
        inicio: linha.querySelector('.intervalo-inicio').value,
        fim:    linha.querySelector('.intervalo-fim').value,
      }))
      .filter(iv => iv.inicio && iv.fim)

    if (intervalos.length === 0) {
      toast.erro(`${label}: adicione ao menos um horário ou desmarque o dia.`)
      return
    }
    if (intervalos.some(iv => iv.inicio >= iv.fim)) {
      toast.erro(`${label}: o horário de abertura deve ser antes do fechamento.`)
      return
    }

    intervalos.sort((a, b) => a.inicio.localeCompare(b.inicio))
    horarios[key] = { aberto: true, horarios: intervalos }
  }

  // Normaliza as cores para hex antes de enviar ao backend
  const cores = {}
  Object.keys(CORES_PADRAO).forEach(campo => {
    const raw = $(`#inp-${campo.replace(/_/g, '-')}`).value.trim()
    cores[campo] = _normalizarParaHex(raw) || CORES_PADRAO[campo]
  })

  const body = {
    nome_loja:            $('#inp-nome-loja').value.trim()              || null,
    whatsapp,
    instagram_url:        $('#inp-instagram').value.trim()              || null,
    endereco:             $('#inp-endereco').value.trim()               || null,
    maps_url:             $('#inp-maps-url').value.trim()               || null,
    chave_pix:            $('#inp-chave-pix').value.trim()              || null,
    tipo_chave_pix:       $('#inp-tipo-pix').value                      || null,
    taxa_entrega:         parseFloat($('#inp-taxa').value)              || 0,
    pedido_minimo:        parseFloat($('#inp-minimo').value)            || 0,
    tempo_entrega_min:    parseInt($('#inp-tempo-min').value)           || 30,
    tempo_entrega_max:    parseInt($('#inp-tempo-max').value)           || 50,
    aceitar_agendamentos: $('#inp-aceitar-agendamentos').checked,
    limite_agendamentos:  parseInt($('#inp-limite-agendamentos').value) || 0,
    mensagem_fechado:     $('#inp-msg-fechado').value.trim()            || null,
    horarios,
    ...cores,
  }

  const btn = $('#btn-salvar')
  btn.disabled = true
  btn.textContent = 'Salvando…'

  try {
    await api.put('/api/admin/configuracoes', body)
    toast.sucesso('Configurações salvas com sucesso.')
    atualizarNomeLojaSidebar(body.nome_loja)
  } catch (err) {
    toast.erro('Erro ao salvar: ' + err.message)
  } finally {
    btn.disabled = false
    btn.textContent = 'Salvar configurações'
  }
}
