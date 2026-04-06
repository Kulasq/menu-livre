window.pedido = (() => {
  // ─── estado ───────────────────────────────────────────────
  let _tipo = 'retirada'; // 'retirada' | 'delivery'

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
    inputTipoPedido:    () => document.getElementById('input-tipo-pedido'),
    campoAgendamento:   () => document.getElementById('campo-agendamento'),
    inputData:          () => document.getElementById('input-data'),
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
      if (!els.inputData().value) {
        alert('Por favor, selecione a data do agendamento.');
        els.inputData().focus();
        return false;
      }
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

  function _montarAgendadoPara() {
    if (els.inputTipoPedido().value !== 'agendado') return null;
    const data = els.inputData().value;
    const hora = els.inputHora().value;
    if (!data || !hora) return null;
    // converte de BRT para UTC antes de enviar
    const localDate = new Date(`${data}T${hora}:00`);
    return new Date(localDate.getTime() + 3 * 60 * 60 * 1000).toISOString();
  }

  // ─── abrir modal ──────────────────────────────────────────
  function abrirModal(tipo) {
    _tipo = tipo || 'retirada';

    // preencher total no header
    els.totalHeader().textContent = brl(window.carrinho.total());

    // mostrar/ocultar endereço
    if (_tipo === 'delivery') {
      els.passoEndereco().classList.remove('hidden');
    } else {
      els.passoEndereco().classList.add('hidden');
    }

    // pré-preencher dados salvos do cliente
    const clienteSalvo = _carregarCliente();
    if (clienteSalvo) {
      els.inputNome().value      = clienteSalvo.nome || '';
      els.inputTelefone().value  = clienteSalvo.telefone || '';
    }

    // data mínima = hoje
    const hoje = new Date().toISOString().split('T')[0];
    els.inputData().min = hoje;
    els.inputData().value = hoje;

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
    });

    els.inputPagamento().addEventListener('change', () => {
      const pix = els.inputPagamento().value === 'pix';
      els.infoPix().classList.toggle('hidden', !pix);
    });

    els.btnConfirmar().addEventListener('click', _confirmar);
  }

  // ─── init ─────────────────────────────────────────────────
  async function _carregarChavePix() {
    try {
      const res = await fetch(`${CONFIG.API_URL}/api/configuracao`);
      if (!res.ok) return;
      const config = await res.json();
      if (config.chave_pix) {
        els.infoPixChave().textContent = config.chave_pix;
      } else if (config.whatsapp) {
        els.infoPixChave().textContent = config.whatsapp;
      }
    } catch {
      // silencioso — chave pix não é crítica
    }
  }

  function init() {
    _initEventos();
    _carregarChavePix();
  }

  return { init, abrirModal, fecharModal };
})();