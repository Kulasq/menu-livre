window.pedido = (() => {
  // ─── estado ───────────────────────────────────────────────
  let _tipo   = 'retirada'; // 'retirada' | 'delivery'
  let _config = null;       // config pública carregada no init
  let _pixBrCode = null;    // payload Pix Copia e Cola do pedido confirmado
  let _pixWhatsappUrl = null;

  // ─── estado do cupom ──────────────────────────────────────
  let _cupomCodigo = null;      // código validado e aceito
  let _descontoCupom = 0;       // valor em R$ a descontar do subtotal
  let _freteGratisCupom = false; // se cupom zera taxa de entrega

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
    blocoTroco:         () => document.getElementById('bloco-troco'),
    inputTrocoPara:     () => document.getElementById('input-troco-para'),
    erroTroco:          () => document.getElementById('erro-troco'),
    inputObs:           () => document.getElementById('input-obs-pedido'),
    btnConfirmar:       () => document.getElementById('btn-confirmar-pedido'),
    modalHandle:        () => document.getElementById('modal-pedido-handle'),
  };

  // ─── estado de sessão do cliente (em memória — sem localStorage) ──────────
  let _clienteId = null;
  let _clienteToken = null;
  let _enderecoSalvoSelecionado = null; // endereço escolhido via radio salvo

  // ─── utilitários ──────────────────────────────────────────
  function brl(valor) {
    return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  function _limparTelefone(tel) {
    return tel.replace(/\D/g, '');
  }

  function _aplicarMascaraMoeda(input) {
    input.addEventListener('input', () => {
      const digits = input.value.replace(/\D/g, '');
      if (!digits) { input.value = ''; return; }
      const centavos = parseInt(digits, 10);
      const reais = centavos / 100;
      input.value = reais.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    });
  }

  function _parseMoeda(valor) {
    if (!valor) return null;
    const num = parseFloat(valor.replace(/[R$\s.]/g, '').replace(',', '.'));
    return isNaN(num) ? null : num;
  }

  function _obterEnderecoEntrega() {
    return _enderecoSalvoSelecionado || els.inputEndereco().value.trim();
  }

  function _totalFinal() {
    const subtotal = window.carrinho.total();
    const taxa = (_freteGratisCupom || _tipo !== 'delivery') ? 0 : (_config?.taxa_entrega || 0);
    return Math.max(0, subtotal - _descontoCupom) + taxa;
  }

  // ─── cupom ────────────────────────────────────────────────
  function _resetarCupom() {
    _cupomCodigo = null;
    _descontoCupom = 0;
    _freteGratisCupom = false;
    const inputCupom = document.getElementById('input-cupom');
    if (inputCupom) inputCupom.value = '';
    _atualizarFeedbackCupom(null);
    _atualizarTotalHeader();
  }

  function _atualizarFeedbackCupom(validacao) {
    const fb = document.getElementById('cupom-feedback');
    if (!fb) return;
    if (!validacao) { fb.className = 'cupom-feedback hidden'; fb.textContent = ''; return; }
    fb.classList.remove('hidden');
    if (validacao.valido) {
      fb.className = 'cupom-feedback cupom-valido';
      const descTxt = validacao.frete_gratis
        ? 'Frete grátis aplicado!'
        : validacao.produto_brinde_nome
          ? `🎁 Brinde: ${validacao.produto_brinde_nome}`
          : `✅ Desconto de ${brl(validacao.desconto)} aplicado!`
      fb.textContent = descTxt;
    } else {
      fb.className = 'cupom-feedback cupom-invalido';
      fb.textContent = `❌ ${validacao.motivo || 'Cupom inválido'}`;
    }
  }

  function _atualizarTotalHeader() {
    const el = els.totalHeader();
    if (el) el.textContent = brl(_totalFinal());
  }

  async function _aplicarCupom() {
    const inputEl = document.getElementById('input-cupom');
    const codigo = (inputEl?.value || '').trim().toUpperCase();
    if (!codigo) return;

    const btn = document.getElementById('btn-aplicar-cupom');
    if (btn) { btn.disabled = true; btn.textContent = '…'; }

    // Se o mesmo código já está aplicado, apenas feedback
    if (_cupomCodigo === codigo) {
      if (btn) { btn.disabled = false; btn.textContent = 'Aplicar'; }
      return;
    }

    // Resetar desconto anterior antes de validar o novo
    _descontoCupom = 0;
    _freteGratisCupom = false;
    _cupomCodigo = null;

    const subtotal = window.carrinho.total();
    const telefone = _limparTelefone(els.inputTelefone().value) || null;

    try {
      const res = await fetch(`${CONFIG.API_URL}/api/cupons/validar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ codigo, subtotal, telefone: telefone || undefined }),
      });
      const validacao = await res.json();

      if (validacao.valido) {
        _cupomCodigo = codigo;
        _descontoCupom = validacao.desconto || 0;
        _freteGratisCupom = validacao.frete_gratis || false;
      }

      _atualizarFeedbackCupom(validacao);
      _atualizarTotalHeader();
    } catch {
      _atualizarFeedbackCupom({ valido: false, motivo: 'Erro ao validar cupom. Tente novamente.' });
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Aplicar'; }
    }
  }

  // ─── máscara de telefone BR ───────────────────────────────
  function _aplicarMascaraTelefone(input) {
    input.addEventListener('input', () => {
      let digits = _limparTelefone(input.value).slice(0, 11);
      if (digits.length === 0) { input.value = ''; return; }
      if (digits.length <= 2) {
        input.value = `(${digits}`;
      } else if (digits.length <= 6) {
        input.value = `(${digits.slice(0,2)}) ${digits.slice(2)}`;
      } else if (digits.length <= 10) {
        input.value = `(${digits.slice(0,2)}) ${digits.slice(2,6)}-${digits.slice(6)}`;
      } else {
        // 11 dígitos — celular
        input.value = `(${digits.slice(0,2)}) ${digits.slice(2,7)}-${digits.slice(7)}`;
      }
      _validarTelefoneInput(input);
    });
  }

  function _validarTelefoneInput(input) {
    const digits = _limparTelefone(input.value);
    const valido = digits.length === 10 || digits.length === 11;
    input.classList.toggle('input-invalido', input.value.length > 0 && !valido);
    const erroEl = document.getElementById('erro-telefone');
    if (erroEl) erroEl.classList.toggle('hidden', !input.value.length || valido);
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

  // ─── helpers de validação inline ────────────────────────

  function _mostrarErroInline(id, inputEl) {
    const erroEl = document.getElementById(id);
    if (erroEl) erroEl.classList.remove('hidden');
    if (inputEl) {
      inputEl.classList.add('input-invalido');
      // Foca apenas se o elemento estiver visível (evita scroll para campos ocultos)
      if (inputEl.offsetParent !== null) inputEl.focus();
    }
  }

  function _limparErrosValidacao() {
    ['erro-nome', 'erro-telefone', 'erro-endereco', 'erro-agendamento',
     'erro-pagamento', 'erro-envio-pedido'].forEach(id => {
      document.getElementById(id)?.classList.add('hidden');
    });
    [els.inputNome(), els.inputTelefone(), els.inputEndereco(),
     els.inputHora(), els.inputPagamento()].forEach(el => {
      el?.classList.remove('input-invalido');
    });
  }

  function _validar() {
    const nome = els.inputNome().value.trim();
    const tel  = _limparTelefone(els.inputTelefone().value);

    if (!nome) {
      _mostrarErroInline('erro-nome', els.inputNome());
      return false;
    }

    if (tel.length !== 10 && tel.length !== 11) {
      _mostrarErroInline('erro-telefone', els.inputTelefone());
      return false;
    }

    if (_tipo === 'delivery' && !_obterEnderecoEntrega()) {
      _mostrarErroInline('erro-endereco', els.inputEndereco());
      return false;
    }

    if (els.inputTipoPedido().value === 'agendado') {
      if (!els.inputHora().value) {
        _mostrarErroInline('erro-agendamento', els.inputHora());
        return false;
      }
    }

    if (!els.inputPagamento().value) {
      _mostrarErroInline('erro-pagamento', els.inputPagamento());
      return false;
    }

    if (els.inputPagamento().value === 'dinheiro') {
      const precisaTroco = document.querySelector('input[name="precisa-troco"]:checked')?.value === 'sim';
      if (precisaTroco) {
        const total = _totalFinal();
        const troco = _parseMoeda(els.inputTrocoPara().value);
        if (!troco || troco < total) {
          els.erroTroco().classList.remove('hidden');
          els.inputTrocoPara().focus();
          return false;
        }
      }
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

    els.totalHeader().textContent = brl(_totalFinal());

    els.passoEndereco().classList.toggle('hidden', _tipo !== 'delivery');

    // Reseta estado de endereços ao abrir
    _enderecoSalvoSelecionado = null;
    const endSalvos = document.getElementById('enderecos-salvos');
    if (endSalvos) { endSalvos.innerHTML = ''; endSalvos.classList.add('hidden'); }
    _mostrarCampoEndereco(true);
    els.inputEndereco().value = '';

    const clienteSalvo = _carregarCliente();
    if (clienteSalvo) {
      els.inputNome().value     = clienteSalvo.nome || '';
      els.inputTelefone().value = clienteSalvo.telefone || '';
    }

    // Se delivery e telefone já preenchido, carrega endereços automaticamente
    if (_tipo === 'delivery' && els.inputTelefone().value) {
      if (_clienteId && _clienteToken) {
        _carregarEnderecosSalvos();
      } else {
        _lookupClienteBlur();
      }
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

    // Reseta cupom
    _resetarCupom();

    // Reseta pagamento e troco
    els.inputPagamento().value = '';
    els.blocoTroco().classList.add('hidden');
    els.inputTrocoPara().classList.add('hidden');
    els.inputTrocoPara().value = '';
    els.erroTroco().classList.add('hidden');
    const naoTroco = document.querySelector('input[name="precisa-troco"][value="nao"]');
    if (naoTroco) naoTroco.checked = true;

    _limparErrosValidacao();

    const box = els.modal().querySelector('.modal-box');
    box.style.maxHeight = `${Math.round(window.innerHeight * 0.92)}px`;
    els.modal().classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  // ─── drag-to-close ───────────────────────────────────────
  function _initDragFechar(handleEl, boxEl, fecharFn) {
    let startY = 0, deltaY = 0;

    handleEl.addEventListener('touchstart', e => {
      if (boxEl.classList.contains('fechando')) return;
      startY = e.touches[0].clientY;
      deltaY = 0;
      boxEl.style.transition = 'none';
    }, { passive: true });

    handleEl.addEventListener('touchmove', e => {
      const d = e.touches[0].clientY - startY;
      if (d > 0) {
        deltaY = d;
        boxEl.style.transform = `translateY(${d}px)`;
      }
    }, { passive: true });

    handleEl.addEventListener('touchend', () => {
      if (deltaY > 100) {
        boxEl.style.transition = 'transform .2s ease-in';
        boxEl.style.transform  = 'translateY(110%)';
        boxEl.addEventListener('transitionend', () => {
          boxEl.style.transition = '';
          boxEl.style.transform  = '';
          fecharFn(true);
        }, { once: true });
      } else {
        boxEl.addEventListener('transitionend', () => {
          boxEl.style.transition = '';
        }, { once: true });
        boxEl.style.transition = 'transform .25s cubic-bezier(.2,.8,.3,1)';
        boxEl.style.transform  = '';
      }
    });
  }

  function fecharModal(skipAnim = false) {
    const modal = els.modal();
    const box = modal.querySelector('.modal-box');
    if (skipAnim) {
      box.style.maxHeight = '';
      modal.classList.add('hidden');
      document.body.style.overflow = '';
      return;
    }
    if (box.classList.contains('fechando')) return;
    modal.classList.add('fechando');
    box.classList.add('fechando');
    box.addEventListener('animationend', () => {
      box.style.maxHeight = '';
      box.classList.remove('fechando');
      modal.classList.remove('fechando');
      modal.classList.add('hidden');
      document.body.style.overflow = '';
    }, { once: true });
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

  // ─── endereços salvos ────────────────────────────────────
  async function _carregarEnderecosSalvos() {
    if (!_clienteId || !_clienteToken || _tipo !== 'delivery') return;

    try {
      const res = await fetch(`${CONFIG.API_URL}/api/clientes/${_clienteId}/enderecos`, {
        headers: { 'Authorization': `Bearer ${_clienteToken}` },
      });
      if (!res.ok) return;
      const enderecos = await res.json();
      _renderEnderecosSalvos(enderecos);
    } catch {
      // silencioso
    }
  }

  function _mostrarCampoEndereco(visivel) {
    const wrap = document.getElementById('wrap-endereco-novo');
    if (wrap) wrap.classList.toggle('hidden', !visivel);
  }

  function _renderEnderecosSalvos(enderecos) {
    const container = document.getElementById('enderecos-salvos');
    if (!container) return;
    container.innerHTML = '';
    _enderecoSalvoSelecionado = null;

    if (!enderecos.length) {
      container.classList.add('hidden');
      _mostrarCampoEndereco(true);
      return;
    }

    // Com endereços salvos: esconde o campo de texto até "Outro endereço" ser selecionado
    _mostrarCampoEndereco(false);
    els.inputEndereco().value = '';

    const titulo = document.createElement('p');
    titulo.className = 'enderecos-salvos-titulo';
    titulo.textContent = 'Endereços salvos:';
    container.appendChild(titulo);

    const SVG_LIXEIRA = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="16" height="16"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" /></svg>`;

    enderecos.forEach((e, idx) => {
      const radioId = `end-salvo-${idx}`;
      const item = document.createElement('div');
      item.className = 'endereco-salvo-item';

      const radio = document.createElement('input');
      radio.type = 'radio';
      radio.name = 'endereco-salvo';
      radio.id = radioId;
      radio.className = 'endereco-salvo-radio';
      radio.value = e.endereco;
      radio.addEventListener('change', () => {
        _enderecoSalvoSelecionado = e.endereco;
        _mostrarCampoEndereco(false);
        els.inputEndereco().value = '';
      });

      const label = document.createElement('label');
      label.htmlFor = radioId;
      label.className = 'endereco-salvo-texto';
      label.textContent = e.endereco;

      const btnDel = document.createElement('button');
      btnDel.type = 'button';
      btnDel.className = 'endereco-salvo-del';
      btnDel.setAttribute('aria-label', 'Remover endereço');
      btnDel.innerHTML = SVG_LIXEIRA;
      btnDel.addEventListener('click', async () => {
        try {
          const res = await fetch(`${CONFIG.API_URL}/api/clientes/enderecos/${e.id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${_clienteToken}` },
          });
          if (res.ok || res.status === 204) {
            if (radio.checked) {
              _enderecoSalvoSelecionado = null;
            }
            item.remove();
            // Se não há mais salvos (exceto o "Outro"), mostra campo diretamente
            if (!container.querySelectorAll('.endereco-salvo-item').length) {
              container.classList.add('hidden');
              _mostrarCampoEndereco(true);
            }
          }
        } catch { /* silencioso */ }
      });

      item.appendChild(radio);
      item.appendChild(label);
      item.appendChild(btnDel);
      container.appendChild(item);
    });

    // Opção "Outro endereço"
    const outroId = 'end-salvo-outro';
    const outroItem = document.createElement('div');
    outroItem.className = 'endereco-salvo-item';

    const outroRadio = document.createElement('input');
    outroRadio.type = 'radio';
    outroRadio.name = 'endereco-salvo';
    outroRadio.id = outroId;
    outroRadio.className = 'endereco-salvo-radio';
    outroRadio.addEventListener('change', () => {
      _enderecoSalvoSelecionado = null;
      _mostrarCampoEndereco(true);
      setTimeout(() => els.inputEndereco().focus(), 50);
    });

    const outroLabel = document.createElement('label');
    outroLabel.htmlFor = outroId;
    outroLabel.className = 'endereco-salvo-texto endereco-salvo-outro';
    outroLabel.textContent = '+ Outro endereço';

    outroItem.appendChild(outroRadio);
    outroItem.appendChild(outroLabel);
    container.appendChild(outroItem);

    container.classList.remove('hidden');
  }

  // ─── lookup silencioso no blur do telefone ────────────────
  async function _lookupClienteBlur() {
    const tel = _limparTelefone(els.inputTelefone().value);
    if (tel.length !== 10 && tel.length !== 11) return;

    try {
      const nome = els.inputNome().value.trim() || undefined;
      const body = { telefone: tel };
      if (nome) body.nome = nome;

      const res = await fetch(`${CONFIG.API_URL}/api/clientes/identificar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      // 400 = novo cliente sem nome — silencioso (sem chips para mostrar)
      if (!res.ok) return;
      const { cliente, access_token } = await res.json();

      // Preenche nome apenas se o campo estiver vazio (cliente retornou da API)
      if (!els.inputNome().value.trim()) {
        els.inputNome().value = cliente.nome;
      }

      // Guarda em memória para uso nos chips e no envio
      _clienteId = cliente.id;
      _clienteToken = access_token;

      _carregarEnderecosSalvos();
    } catch {
      // silencioso — não interrompe o fluxo
    }
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

    const precisaTroco = els.inputPagamento().value === 'dinheiro' &&
      document.querySelector('input[name="precisa-troco"]:checked')?.value === 'sim';

    const body = {
      tipo:              _tipo,
      endereco_entrega:  _tipo === 'delivery' ? _obterEnderecoEntrega() : null,
      metodo_pagamento:  els.inputPagamento().value,
      troco_para:        precisaTroco ? _parseMoeda(els.inputTrocoPara().value) : null,
      observacao:        els.inputObs().value.trim() || null,
      agendado_para:     _montarAgendadoPara(),
      cupom_codigo:      _cupomCodigo || null,
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

      // 3. limpar carrinho e fechar modal
      window.carrinho.limpar();
      fecharModal();

      if (resultado.pix_br_code && resultado.pix_qr_code_base64) {
        _abrirModalPix(resultado);
      } else if (resultado.pedido.agendado_para) {
        const dt = new Date(resultado.pedido.agendado_para);
        const formatado = dt.toLocaleString('pt-BR', {
          timeZone: 'America/Recife',
          day: '2-digit', month: '2-digit',
          hour: '2-digit', minute: '2-digit',
        });
        _mostrarConfirmacaoAgendamento(formatado, () => {
          window.open(resultado.whatsapp_url, '_blank');
        });
      } else {
        window.open(resultado.whatsapp_url, '_blank');
        _mostrarConfirmacaoPedido(resultado.pedido.numero);
      }

    } catch (err) {
      _mostrarModalErroPedido(err.message);
      btn.disabled = false;
      btn.textContent = 'Confirmar pedido';
    }
  }

  function _mostrarModalErroPedido(mensagem) {
    const modal = document.getElementById('modal-erro-pedido');
    const msgEl = document.getElementById('modal-erro-pedido-msg');
    const fecharBtn = document.getElementById('modal-erro-pedido-fechar');
    const overlay = document.getElementById('modal-erro-pedido-overlay');
    if (!modal) return;

    msgEl.textContent = mensagem;
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    function _fechar() {
      modal.classList.add('hidden');
      document.body.style.overflow = '';
      fecharBtn.removeEventListener('click', _fechar);
      overlay.removeEventListener('click', _fechar);
    }

    fecharBtn.addEventListener('click', _fechar, { once: true });
    overlay.addEventListener('click', _fechar, { once: true });
  }

  function _abrirModalPix(resultado) {
    _pixBrCode = resultado.pix_br_code;
    _pixWhatsappUrl = resultado.whatsapp_url;

    document.getElementById('pix-num-pedido').textContent = resultado.pedido.numero;
    document.getElementById('pix-valor').textContent = brl(resultado.pedido.total);
    document.getElementById('pix-qr-img').src = resultado.pix_qr_code_base64;

    const modalPix = document.getElementById('modal-pix-pagamento');
    modalPix.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    document.getElementById('modal-pix-overlay').addEventListener('click', _fecharModalPix, { once: true });
    document.getElementById('modal-pix-fechar').addEventListener('click', _fecharModalPix, { once: true });

    const btnCopiar = document.getElementById('btn-copiar-pix');
    btnCopiar.onclick = async () => {
      try {
        await navigator.clipboard.writeText(_pixBrCode);
      } catch {
        const ta = document.createElement('textarea');
        ta.value = _pixBrCode;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
      }
      const original = btnCopiar.textContent;
      btnCopiar.textContent = '✓ Copiado!';
      setTimeout(() => { btnCopiar.textContent = original; }, 2000);
    };

    document.getElementById('btn-pix-whatsapp').onclick = () => {
      const url = _pixWhatsappUrl;
      _fecharModalPix();
      window.open(url, '_blank');
    };

    _initDragFechar(
      modalPix.querySelector('.modal-drag-handle'),
      modalPix.querySelector('.modal-box'),
      _fecharModalPix
    );
  }

  function _fecharModalPix() {
    const modalPix = document.getElementById('modal-pix-pagamento');
    modalPix.classList.add('hidden');
    document.body.style.overflow = '';
    _pixBrCode = null;
    _pixWhatsappUrl = null;
  }

  function _mostrarConfirmacaoPedido(numero) {
    const modal  = document.getElementById('modal-pedido-enviado');
    const msgEl  = document.getElementById('modal-enviado-msg');
    const fechar = document.getElementById('modal-enviado-fechar');

    msgEl.innerHTML = `Pedido <strong>${numero}</strong> enviado! Acompanhe o status em <em>Meus Pedidos</em>.`;
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    const _fechar = () => {
      modal.classList.add('hidden');
      document.body.style.overflow = '';
    };
    document.getElementById('modal-enviado-overlay').addEventListener('click', _fechar, { once: true });
    fechar.addEventListener('click', _fechar, { once: true });
  }

  function _mostrarConfirmacaoAgendamento(formatado, onOk) {
    const modal = document.getElementById('modal-aviso-fechado');
    const msgEl = document.getElementById('modal-aviso-msg');
    const btn   = document.getElementById('modal-aviso-ok');

    msgEl.innerHTML = `Seu pedido foi <strong>agendado para ${formatado}</strong>.<br>Você será atendido nesse horário!`;
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    btn.addEventListener('click', () => {
      modal.classList.add('hidden');
      document.body.style.overflow = '';
      onOk();
    }, { once: true });
  }

  // ─── eventos ──────────────────────────────────────────────
  function _initEventos() {
    els.voltar().addEventListener('click', () => {
      fecharModal();
      window.carrinho.abrirDrawer();
    });

    els.overlay().addEventListener('click', () => fecharModal());
    document.getElementById('modal-pedido-fechar').addEventListener('click', () => fecharModal());

    // O drag handle do checkout é visual — eventos de toque ficam no cabeçalho
    // para não bloquear o botão ← (stacking context do header confina qualquer z-index filho)
    _initDragFechar(
      document.querySelector('#modal-pedido .modal-pedido-header'),
      document.querySelector('#modal-pedido .modal-box'),
      (skip) => fecharModal(skip)
    );

    // Máscara de telefone + lookup silencioso no blur
    const telInput = els.inputTelefone();
    _aplicarMascaraTelefone(telInput);
    telInput.addEventListener('blur', _lookupClienteBlur);

    // Limpa erros inline ao corrigir os campos
    els.inputNome().addEventListener('input', () => {
      document.getElementById('erro-nome')?.classList.add('hidden');
      els.inputNome().classList.remove('input-invalido');
    });
    els.inputEndereco().addEventListener('input', () => {
      document.getElementById('erro-endereco')?.classList.add('hidden');
      els.inputEndereco().classList.remove('input-invalido');
    });
    els.inputHora().addEventListener('change', () => {
      document.getElementById('erro-agendamento')?.classList.add('hidden');
      els.inputHora().classList.remove('input-invalido');
    });

    els.inputTipoPedido().addEventListener('change', () => {
      const agendado = els.inputTipoPedido().value === 'agendado';
      els.campoAgendamento().classList.toggle('hidden', !agendado);
      if (agendado && _config?.horarios) {
        const [y, m, d] = _hojeBRT().split('-').map(Number);
        const slots = _gerarSlots(_config.horarios, new Date(y, m - 1, d).getDay());
        _popularSelectHora(slots, _config.proxima_abertura);
      }
    });

    _aplicarMascaraMoeda(els.inputTrocoPara());

    els.inputPagamento().addEventListener('change', () => {
      document.getElementById('erro-pagamento')?.classList.add('hidden');
      els.inputPagamento().classList.remove('input-invalido');
      const val = els.inputPagamento().value;
      els.blocoTroco().classList.toggle('hidden', val !== 'dinheiro');
      if (val !== 'dinheiro') {
        // reset troco ao sair do dinheiro
        document.querySelector('input[name="precisa-troco"][value="nao"]').checked = true;
        els.inputTrocoPara().classList.add('hidden');
        els.inputTrocoPara().value = '';
        els.erroTroco().classList.add('hidden');
      }
    });

    els.blocoTroco().addEventListener('change', (e) => {
      if (e.target.name !== 'precisa-troco') return;
      const sim = e.target.value === 'sim';
      els.inputTrocoPara().classList.toggle('hidden', !sim);
      els.erroTroco().classList.add('hidden');
      if (sim) {
        els.inputTrocoPara().value = '';
        setTimeout(() => els.inputTrocoPara().focus(), 50);
      } else {
        els.inputTrocoPara().value = '';
      }
    });

    els.inputTrocoPara().addEventListener('input', () => {
      els.erroTroco().classList.add('hidden');
    });

    els.btnConfirmar().addEventListener('click', _confirmar);

    // Cupom — aplicar via botão ou Enter no input
    const btnCupom = document.getElementById('btn-aplicar-cupom');
    if (btnCupom) btnCupom.addEventListener('click', _aplicarCupom);

    const inputCupom = document.getElementById('input-cupom');
    if (inputCupom) {
      inputCupom.addEventListener('keydown', e => {
        if (e.key === 'Enter') { e.preventDefault(); _aplicarCupom(); }
      });
      // Normalizar para maiúsculas durante digitação
      inputCupom.addEventListener('input', e => {
        const sel = e.target.selectionStart;
        e.target.value = e.target.value.toUpperCase().replace(/\s/g, '');
        e.target.setSelectionRange(sel, sel);
      });
      // Limpar feedback se o campo for apagado manualmente
      inputCupom.addEventListener('input', () => {
        if (!inputCupom.value) _resetarCupom();
      });
    }
  }

  // ─── init ─────────────────────────────────────────────────
  async function _carregarConfig() {
    try {
      const res = await fetch(`${CONFIG.API_URL}/api/configuracao`);
      if (!res.ok) return;
      _config = await res.json();
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