window.pedido = (() => {
  // ─── estado ───────────────────────────────────────────────
  let _tipo   = 'retirada'; // 'retirada' | 'delivery'
  let _config = null;       // config pública carregada no init

  // ─── elementos ────────────────────────────────────────────
  const els = {
    modal:              () => document.getElementById('modal-pedido'),
    overlay:            () => document.getElementById('modal-pedido-overlay'),
    voltar:             () => document.getElementById('modal-pedido-voltar'),
    titulo:             () => document.getElementById('modal-pedido-titulo'),
    totalHeader:        () => document.getElementById('modal-pedido-total-header'),
    inputNome:          () => document.getElementById('input-nome'),
    inputTelefone:      () => document.getElementById('input-telefone'),
    passoEndereco:      () => document.getElementById('passo-endereco'),
    inputEndereco:      () => document.getElementById('input-endereco'),
    rowTipoPedido:      () => document.getElementById('row-tipo-pedido'),
    inputTipoPedido:    () => document.getElementById('input-tipo-pedido'),
    campoAgendamento:   () => document.getElementById('campo-agendamento'),
    inputHora:          () => document.getElementById('input-hora'),
    inputPagamento:     () => document.getElementById('input-pagamento'),
    infoPix:            () => document.getElementById('info-pix'),
    infoPixChave:       () => document.getElementById('info-pix-chave'),
    inputObs:           () => document.getElementById('input-obs-pedido'),
    btnConfirmar:       () => document.getElementById('btn-confirmar-pedido'),
  };

  // ─── utilitários ──────────────────────────────────────────
  function brl(valor) {
    return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  function _limparTelefone(tel) {
    return tel.replace(/\D/g, '');
  }

  // ─── slots de horário ────────────────────────────────────
  function _gerarSlots(horarios, diaSemana) {
    const nomes = ['domingo', 'segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado'];
    const dia   = horarios?.[nomes[diaSemana]];
    if (!dia?.aberto || !dia.horarios?.length) return [];

    const slots = [];
    dia.horarios.forEach(({ inicio, fim }) => {
      let min = _hhmmParaMin(inicio);
      const fimMin = _hhmmParaMin(fim);
      if (min === null || fimMin === null) return;
      while (min <= fimMin) {
        slots.push(`${String(Math.floor(min / 60)).padStart(2, '0')}:${String(min % 60).padStart(2, '0')}`);
        min += 30;
      }
    });
    return slots;
  }

  function _hhmmParaMin(str) {
    if (!str) return null;
    const [h, m] = str.split(':').map(Number);
    return (isNaN(h) || isNaN(m)) ? null : h * 60 + m;
  }

  function _popularSelectHora(slots, padrao) {
    const sel = els.inputHora();
    sel.innerHTML = '';
    if (!slots.length) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'Sem horários disponíveis';
      sel.appendChild(opt);
      return;
    }
    slots.forEach(slot => {
      const opt = document.createElement('option');
      opt.value = slot;
      opt.textContent = slot;
      if (slot === padrao) opt.selected = true;
      sel.appendChild(opt);
    });
    // se nenhum foi marcado como padrão, seleciona o primeiro
    if (!sel.value && slots.length) sel.value = slots[0];
  }

  function _validar() {
    const nome = els.inputNome().value.trim();
    const tel  = _limparTelefone(els.inputTelefone().value);

    if (!nome) {
      alert('Por favor, informe seu nome.');
      els.inputNome().focus();
      return false;
    }

    if (tel.length < 10 || tel.length > 11) {
      alert('Telefone inválido. Informe DDD + número.');
      els.inputTelefone().focus();
      return false;
    }

    if (_tipo === 'delivery' && !els.inputEndereco().value.trim()) {
      alert('Por favor, informe o endereço de entrega.');
      els.inputEndereco().focus();
      return false;
    }

    if (els.inputTipoPedido().value === 'agendado') {
      if (!els.inputHora().value) {
        alert('Por favor, selecione o horário do agendamento.');
        els.inputHora().focus();
        return false;
      }
    }

    if (!els.inputPagamento().value) {
      alert('Por favor, selecione a forma de pagamento.');
      els.inputPagamento().focus();
      return false;
    }

    return true;
  }

  function _hojeBRT() {
    // Retorna "YYYY-MM-DD" no fuso de Recife (UTC-3), independente do browser
    return new Date().toLocaleDateString('en-CA', { timeZone: 'America/Recife' });
  }

  function _montarAgendadoPara() {
    if (els.inputTipoPedido().value !== 'agendado') return null;
    const hora = els.inputHora().value;
    if (!hora) return null;
    // sufixo -03:00 força interpretação BRT antes da conversão para UTC
    return new Date(`${_hojeBRT()}T${hora}:00-03:00`).toISOString();
  }

  // ─── abrir modal ──────────────────────────────────────────
  function abrirModal(tipo) {
    _tipo = tipo || 'retirada';

    els.totalHeader().textContent = brl(window.carrinho.total());

    els.passoEndereco().classList.toggle('hidden', _tipo !== 'delivery');

    const clienteSalvo = _carregarCliente();
    if (clienteSalvo) {
      els.inputNome().value     = clienteSalvo.nome || '';
      els.inputTelefone().value = clienteSalvo.telefone || '';
    }

    const lojaFechada = _config && !_config.aberto;

    if (lojaFechada) {
      // loja fechada → agendamento obrigatório, sem escolha de tipo
      els.inputTipoPedido().value = 'agendado';
      els.rowTipoPedido().classList.add('hidden');
      els.campoAgendamento().classList.remove('hidden');

      // dia da semana em Recife (0=dom … 6=sab)
      const [y, m, d] = _hojeBRT().split('-').map(Number);
      const diaRecife = new Date(y, m - 1, d).getDay();
      const slots = _gerarSlots(_config.horarios, diaRecife);
      _popularSelectHora(slots, _config.proxima_abertura);
    } else {
      // loja aberta → fluxo normal
      els.inputTipoPedido().value = 'imediato';
      els.rowTipoPedido().classList.remove('hidden');
      els.campoAgendamento().classList.add('hidden');
    }

    els.modal().classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  function fecharModal() {
    els.modal().classList.add('hidden');
    document.body.style.overflow = '';
  }

  // ─── cliente no localStorage ──────────────────────────────
  function _carregarCliente() {
    try {
      return JSON.parse(localStorage.getItem(CONFIG.STORAGE_KEYS.CLIENTE));
    } catch {
      return null;
    }
  }

  function _salvarCliente(dados) {
    localStorage.setItem(CONFIG.STORAGE_KEYS.CLIENTE, JSON.stringify(dados));
  }

  function _salvarToken(token) {
    localStorage.setItem(CONFIG.STORAGE_KEYS.TOKEN, token);
  }

  // ─── identificar cliente na API ───────────────────────────
  async function _identificarCliente(nome, telefone) {
    const res = await fetch(`${CONFIG.API_URL}/api/clientes/identificar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nome, telefone }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Erro ao identificar cliente');
    }

    return res.json(); // { cliente, token }
  }

  // ─── enviar pedido ────────────────────────────────────────
  async function _enviarPedido(clienteId, token) {
    const itens = window.carrinho.obterItens().map(item => ({
      produto_id:    item.produto_id,
      variante_id:   item.variante_id || null,
      quantidade:    item.quantidade,
      observacao:    item.observacao || null,
      modificadores: item.modificadores || [],
    }));

    const body = {
      tipo:              _tipo,
      endereco_entrega:  _tipo === 'delivery' ? els.inputEndereco().value.trim() : null,
      metodo_pagamento:  els.inputPagamento().value,
      observacao:        els.inputObs().value.trim() || null,
      agendado_para:     _montarAgendadoPara(),
      itens,
    };

    const res = await fetch(`${CONFIG.API_URL}/api/pedidos`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Erro ao enviar pedido');
    }

    return res.json(); // { pedido, mensagem_whatsapp, whatsapp_url }
  }

  // ─── confirmar pedido ─────────────────────────────────────
  async function _confirmar() {
    if (!_validar()) return;

    const btn = els.btnConfirmar();
    btn.disabled = true;
    btn.textContent = 'Enviando…';

    try {
      const nome     = els.inputNome().value.trim();
      const telefone = _limparTelefone(els.inputTelefone().value);

      // 1. identificar/criar cliente
      const { cliente, access_token: token } = await _identificarCliente(nome, telefone);
      _salvarCliente({ id: cliente.id, nome: cliente.nome, telefone: cliente.telefone });
      _salvarToken(token);

      // 2. enviar pedido
      const resultado = await _enviarPedido(cliente.id, token);

      // 3. limpar carrinho e redirecionar para WhatsApp
      window.carrinho.limpar();
      fecharModal();

      if (resultado.pedido.agendado_para) {
        const dt = new Date(resultado.pedido.agendado_para);
        const formatado = dt.toLocaleString('pt-BR', {
          timeZone: 'America/Recife',
          day: '2-digit', month: '2-digit', year: 'numeric',
          hour: '2-digit', minute: '2-digit',
        });
        alert(`Pedido agendado para ${formatado}. Você será atendido nesse horário!`);
      }

      window.open(resultado.whatsapp_url, '_blank');

    } catch (err) {
      alert(`Erro: ${err.message}`);
      btn.disabled = false;
      btn.textContent = 'Confirmar pedido';
    }
  }

  // ─── eventos ──────────────────────────────────────────────
  function _initEventos() {
    els.voltar().addEventListener('click', () => {
      fecharModal();
      window.carrinho.abrirDrawer();
    });

    els.overlay().addEventListener('click', fecharModal);

    els.inputTipoPedido().addEventListener('change', () => {
      const agendado = els.inputTipoPedido().value === 'agendado';
      els.campoAgendamento().classList.toggle('hidden', !agendado);
      if (agendado && _config?.horarios) {
        const [y, m, d] = _hojeBRT().split('-').map(Number);
        const slots = _gerarSlots(_config.horarios, new Date(y, m - 1, d).getDay());
        _popularSelectHora(slots, _config.proxima_abertura);
      }
    });

    els.inputPagamento().addEventListener('change', () => {
      const pix = els.inputPagamento().value === 'pix';
      els.infoPix().classList.toggle('hidden', !pix);
    });

    els.btnConfirmar().addEventListener('click', _confirmar);
  }

  // ─── init ─────────────────────────────────────────────────
  async function _carregarConfig() {
    try {
      const res = await fetch(`${CONFIG.API_URL}/api/configuracao`);
      if (!res.ok) return;
      _config = await res.json();
      if (_config.chave_pix) {
        els.infoPixChave().textContent = _config.chave_pix;
      } else if (_config.whatsapp) {
        els.infoPixChave().textContent = _config.whatsapp;
      }
    } catch {
      // silencioso — config não é crítica para abrir o modal
    }
  }

  function init() {
    _initEventos();
    _carregarConfig();
  }

  return { init, abrirModal, fecharModal };
})();