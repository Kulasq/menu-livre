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

document.addEventListener('DOMContentLoaded', () => {
  if (!auth.proteger()) return

  _setupUsuario()
  _setupSidebar()
  _buildHorarios()
  _carregarConfiguracoes()

  $('#form-config').addEventListener('submit', _salvarConfiguracoes)
  $('#btn-toggle-loja').addEventListener('click', _toggleStatusLoja)
})

function _setupUsuario() {
  const u = auth.getUsuario()
  $('#header-usuario-nome').textContent = u.nome
  const iniciais = u.nome.split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase()
  $('#header-usuario-avatar').textContent = iniciais
}

function _setupSidebar() {
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
        <div class="form-group">
          <label class="form-label" for="dia-${key}-inicio">Abertura</label>
          <input type="time" class="form-input" id="dia-${key}-inicio" value="18:00" />
        </div>
        <div class="form-group">
          <label class="form-label" for="dia-${key}-fim">Fechamento</label>
          <input type="time" class="form-input" id="dia-${key}-fim" value="23:00" />
        </div>
      </div>
    </div>
  `).join('')

  lista.addEventListener('change', (e) => {
    const input = e.target.closest('.dia-toggle')
    if (!input) return
    $(`#dia-${input.dataset.dia}-campos`).classList.toggle('hidden', !input.checked)
  })
}

async function _carregarConfiguracoes() {
  try {
    const config = await api.get('/api/admin/configuracoes')
    _preencherForm(config)
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
      const intervalo = diaConfig.horarios?.[0]
      if (intervalo) {
        $(`#dia-${key}-inicio`).value = intervalo.inicio
        $(`#dia-${key}-fim`).value    = intervalo.fim
      }
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
  DIAS.forEach(({ key }) => {
    const aberto = $(`#dia-${key}-aberto`).checked
    horarios[key] = {
      aberto,
      horarios: aberto
        ? [{ inicio: $(`#dia-${key}-inicio`).value, fim: $(`#dia-${key}-fim`).value }]
        : [],
    }
  })

  const body = {
    nome_loja:            $('#inp-nome-loja').value.trim()              || null,
    whatsapp,
    instagram_url:        $('#inp-instagram').value.trim()              || null,
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
  }

  const btn = $('#btn-salvar')
  btn.disabled = true
  btn.textContent = 'Salvando…'

  try {
    await api.put('/api/admin/configuracoes', body)
    toast.sucesso('Configurações salvas com sucesso.')
  } catch (err) {
    toast.erro('Erro ao salvar: ' + err.message)
  } finally {
    btn.disabled = false
    btn.textContent = 'Salvar configurações'
  }
}
