(() => {
  // ─── constantes ───────────────────────────────────────────
  const STATUS_LABEL = {
    pendente:    { texto: 'Pendente',    cor: 'amarelo' },
    confirmado:  { texto: 'Confirmado',  cor: 'azul'    },
    em_preparo:  { texto: 'Em preparo',  cor: 'azul'    },
    pronto:      { texto: 'Pronto!',     cor: 'verde-claro' },
    entregue:    { texto: 'Entregue',    cor: 'verde'   },
    cancelado:   { texto: 'Cancelado',   cor: 'cinza'   },
  };

  const STATUS_ATIVOS = new Set(['pendente', 'confirmado', 'em_preparo', 'pronto']);

  const LIMITE = 5;

  // ─── estado ───────────────────────────────────────────────
  let _token     = null;
  let _clienteId = null;
  let _polling   = null;
  let _whatsapp  = null; // número da loja, carregado da config

  // ─── utilitários ──────────────────────────────────────────
  // brl(), _formatarData() e _aplicarMascaraTelefone() são globais (utils.js).
  function _limparTel(v) { return v.replace(/\D/g, ''); }

  // ─── banner inline de mensagens ──────────────────────────

  function _banner(msg, tipo = 'info', persistente = false) {
    const el   = document.getElementById('mp-banner');
    const span = document.getElementById('mp-banner-msg');
    if (!el || !span) return;
    span.textContent = msg;
    el.className = `mp-banner mp-banner-${tipo}`;
    if (!persistente) {
      setTimeout(() => el.classList.add('hidden'), 6000);
    }
  }

  function _bannerHtml(html, tipo = 'info') {
    const el   = document.getElementById('mp-banner');
    const span = document.getElementById('mp-banner-msg');
    if (!el || !span) return;
    span.innerHTML = html;
    el.className = `mp-banner mp-banner-${tipo}`;
    // mensagens com HTML (ex: link) são persistentes — o usuário deve agir
  }

  // ─── localStorage ─────────────────────────────────────────
  function _carregarSessao() {
    try {
      const token = localStorage.getItem(CONFIG.STORAGE_KEYS.TOKEN);
      const cli   = JSON.parse(localStorage.getItem(CONFIG.STORAGE_KEYS.CLIENTE) || 'null');
      if (token && cli?.id) {
        _token     = token;
        _clienteId = cli.id;
        return true;
      }
    } catch { /* */ }
    return false;
  }

  function _salvarSessao(cliente, token) {
    _token     = token;
    _clienteId = cliente.id;
    localStorage.setItem(CONFIG.STORAGE_KEYS.TOKEN, token);
    localStorage.setItem(CONFIG.STORAGE_KEYS.CLIENTE, JSON.stringify({
      id: cliente.id, nome: cliente.nome, telefone: cliente.telefone,
    }));
  }

  // ─── mostrar/ocultar estados ───────────────────────────────
  function _mostrar(id) {
    ['mp-nao-identificado','mp-carregando','mp-vazio','mp-lista'].forEach(i => {
      document.getElementById(i).classList.toggle('hidden', i !== id);
    });
  }

  // ─── carregar config da loja ──────────────────────────────
  async function _carregarConfig() {
    try {
      const r = await fetch(`${CONFIG.API_URL}/api/configuracao`);
      if (r.ok) {
        const cfg = await r.json();
        _whatsapp = cfg.whatsapp || null;
      }
    } catch { /* silencioso */ }
  }

  // ─── identificar via API ──────────────────────────────────
  async function _identificar(telefone) {
    const r = await fetch(`${CONFIG.API_URL}/api/clientes/identificar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ telefone }),
    });
    if (!r.ok) {
      const e = await r.json().catch(() => ({}));
      throw new Error(e.detail || 'Erro ao identificar');
    }
    return r.json();
  }

  // ─── carregar pedidos ──────────────────────────────────────
  async function _carregar() {
    try {
      const r = await fetch(`${CONFIG.API_URL}/api/pedidos?limite=${LIMITE}`, {
        headers: { 'Authorization': `Bearer ${_token}` },
      });
      if (r.status === 401 || r.status === 403) {
        _token = null;
        _mostrar('mp-nao-identificado');
        return;
      }
      if (!r.ok) throw new Error('Falha ao carregar');
      const pedidos = await r.json();
      _renderizar(pedidos);
    } catch { /* silencioso no poll */ }
  }

  // ─── polling ──────────────────────────────────────────────
  function _iniciarPolling(pedidos) {
    clearInterval(_polling);
    const temAtivo = pedidos.some(p => STATUS_ATIVOS.has(p.status));
    if (!temAtivo) return;
    _polling = setInterval(() => _carregar(), 10_000);
  }

  // ─── renderizar lista ─────────────────────────────────────
  function _renderizar(pedidos) {
    if (!pedidos.length) {
      _mostrar('mp-vazio');
      return;
    }

    _mostrar('mp-lista');

    const nome = JSON.parse(localStorage.getItem(CONFIG.STORAGE_KEYS.CLIENTE) || '{}')?.nome;
    const saud = document.getElementById('mp-saudacao');
    if (nome) {
      saud.textContent = `Olá, ${nome}!`;
      saud.classList.remove('hidden');
    }

    const container = document.getElementById('mp-cards');

    // Atualiza badges e botões dos cards existentes sem recriar (mantém estado no poll)
    const existentes = new Map(
      [...container.querySelectorAll('.mp-card')].map(el => [Number(el.dataset.id), el])
    );

    // Remove cards que saíram da lista
    existentes.forEach((el, id) => {
      if (!pedidos.find(p => p.id === id)) el.remove();
    });

    pedidos.forEach((pedido, idx) => {
      if (existentes.has(pedido.id)) {
        _atualizarCard(existentes.get(pedido.id), pedido);
      } else {
        const card = _criarCard(pedido);
        // Insere na posição correta
        const refEl = container.children[idx];
        if (refEl) container.insertBefore(card, refEl);
        else container.appendChild(card);
      }
    });

    _iniciarPolling(pedidos);
  }

  function _criarCard(pedido) {
    const card = document.createElement('div');
    card.className = 'mp-card';
    card.dataset.id = pedido.id;
    _preencherCard(card, pedido);
    return card;
  }

  function _atualizarCard(card, pedido) {
    const badge = card.querySelector('.mp-badge');
    const info  = STATUS_LABEL[pedido.status] || { texto: pedido.status, cor: 'cinza' };
    if (badge) {
      badge.textContent = info.texto;
      badge.className = `mp-badge mp-badge-${info.cor}`;
    }
    // Atualiza botões contextuais
    const acoes = card.querySelector('.mp-acoes');
    if (acoes) _preencherAcoes(acoes, pedido);
  }

  function _preencherCard(card, pedido) {
    const info     = STATUS_LABEL[pedido.status] || { texto: pedido.status, cor: 'cinza' };
    const tipoLabel = { delivery: 'Delivery', retirada: 'Retirada', balcao: 'Balcão' }[pedido.tipo] || pedido.tipo;
    const pgto      = { pix: 'PIX', dinheiro: 'Dinheiro', cartao: 'Cartão' }[pedido.metodo_pagamento] || '—';

    card.innerHTML = `
      <div class="mp-card-header">
        <div class="mp-card-linha1">
          <span class="mp-numero">#${pedido.numero}</span>
          <span class="mp-badge mp-badge-${info.cor}">${info.texto}</span>
        </div>
        <div class="mp-card-linha2">
          <span class="mp-data">${_formatarData(pedido.criado_em)}</span>
          <span class="mp-total">${brl(pedido.total)}</span>
        </div>
      </div>
      <div class="mp-card-corpo">
        <div class="mp-detalhe-linha"><span>Tipo</span><span>${tipoLabel}</span></div>
        ${pedido.endereco_entrega ? `<div class="mp-detalhe-linha"><span>Endereço</span><span>${esc(pedido.endereco_entrega)}</span></div>` : ''}
        <div class="mp-detalhe-linha"><span>Pagamento</span><span>${pgto}</span></div>
        ${pedido.observacao ? `<div class="mp-detalhe-obs">Obs: ${esc(pedido.observacao)}</div>` : ''}
        <div class="mp-itens">${_renderItens(pedido.itens)}</div>
        <div class="mp-acoes"></div>
      </div>
    `;

    _preencherAcoes(card.querySelector('.mp-acoes'), pedido);
  }

  function _preencherAcoes(container, pedido) {
    container.innerHTML = '';

    if (pedido.status === 'entregue') {
      const btn = document.createElement('button');
      btn.className = 'mp-btn-pedir-igual';
      btn.textContent = 'Pedir novamente';
      btn.addEventListener('click', () => _pedirIgual(pedido));
      container.appendChild(btn);
      return;
    }

    if (STATUS_ATIVOS.has(pedido.status) && _whatsapp) {
      const msg = encodeURIComponent(`Olá! Tenho uma dúvida sobre o meu pedido ${pedido.numero}.`);
      const url = `https://api.whatsapp.com/send/?phone=${_whatsapp}&text=${msg}`;
      const link = document.createElement('a');
      link.href = url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.className = 'mp-btn-contato';
      link.innerHTML = `
        <svg viewBox="0 0 24 24" fill="currentColor" width="17" height="17"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 0C5.373 0 0 5.373 0 12c0 2.127.558 4.126 1.533 5.859L.057 23.428a.75.75 0 0 0 .921.921l5.569-1.476A11.946 11.946 0 0 0 12 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22c-1.853 0-3.601-.5-5.112-1.376l-.366-.214-3.802 1.007 1.007-3.802-.214-.366A9.944 9.944 0 0 1 2 12C2 6.477 6.477 2 12 2s10 4.477 10 10-4.477 10-10 10z"/></svg>
        Entrar em contato
      `;
      container.appendChild(link);
    }
  }

  function _renderItens(itens) {
    return itens.map(item => {
      const mods = item.modificadores.length
        ? `<ul class="mp-mods">${item.modificadores.map(m => `<li>${esc(m.nome_snapshot)}</li>`).join('')}</ul>`
        : '';
      return `<div class="mp-item">
        <span class="mp-item-nome">${item.quantidade}× ${esc(item.nome_snapshot)}</span>
        <span class="mp-item-preco">${brl(item.subtotal)}</span>
        ${mods}
      </div>`;
    }).join('');
  }

  // ─── pedir igual ─────────────────────────────────────────

  // Brinde do cupom: gravado pelo backend com preco_snapshot=0 e
  // nome no formato "Produto (CODIGO)". Não deve voltar no "pedir igual"
  // porque o preço seria recalculado pelo backend a partir do produto real
  // e o cliente precisaria aplicar o cupom novamente para realmente ganhar.
  function _ehBrindeCupom(item, cupomCodigo) {
    if (!cupomCodigo) return false;
    if (item.preco_snapshot !== 0) return false;
    return item.nome_snapshot.endsWith(`(${cupomCodigo})`);
  }

  async function _pedirIgual(pedido) {
    let cardapio = null;
    try {
      const r = await fetch(`${CONFIG.API_URL}/api/cardapio`);
      if (r.ok) cardapio = await r.json();
    } catch { /* */ }

    const disponiveis = new Map();
    if (cardapio) {
      cardapio.categorias?.forEach(cat => {
        cat.produtos?.forEach(p => { if (p.disponivel) disponiveis.set(p.id, p); });
      });
    }

    const itensParaCarrinho = [];
    let pulados = 0;

    for (const item of pedido.itens) {
      if (_ehBrindeCupom(item, pedido.cupom_codigo)) continue;
      if (!item.produto_id) { pulados++; continue; }
      if (cardapio && !disponiveis.has(item.produto_id)) { pulados++; continue; }
      const produtoAtual = disponiveis.get(item.produto_id);
      itensParaCarrinho.push({
        produto_id:    item.produto_id,
        nome:          item.nome_snapshot,
        preco:         item.preco_snapshot,
        foto_url:      produtoAtual?.foto_url || null,
        quantidade:    item.quantidade,
        observacao:    item.observacao || null,
        modificadores: item.modificadores.map(m => ({
          modificador_id: m.modificador_id,
          nome:           m.nome_snapshot,
          preco_adicional: m.preco_snapshot,
        })),
      });
    }

    if (!itensParaCarrinho.length) {
      _banner('Nenhum item deste pedido está disponível no momento.', 'erro');
      return;
    }

    if (pulados > 0) {
      // Mostra aviso antes de redirecionar para o usuário ter tempo de ler
      _banner(
        `${itensParaCarrinho.length} ${itensParaCarrinho.length === 1 ? 'item adicionado' : 'itens adicionados'} ao carrinho. ` +
        `(${pulados} ${pulados === 1 ? 'item indisponível foi pulado' : 'itens indisponíveis foram pulados'}.)`,
        'info'
      );
      setTimeout(() => {
        sessionStorage.setItem('ml_pedir_igual', JSON.stringify(itensParaCarrinho));
        window.location.href = 'index.html';
      }, 2500);
    } else {
      sessionStorage.setItem('ml_pedir_igual', JSON.stringify(itensParaCarrinho));
      window.location.href = 'index.html';
    }
  }

  // ─── inicialização ────────────────────────────────────────
  async function _init() {
    await _carregarConfig();

    const inputTel = document.getElementById('mp-input-telefone');
    _aplicarMascaraTelefone(inputTel);

    document.getElementById('mp-btn-identificar').addEventListener('click', async () => {
      const tel   = _limparTel(inputTel.value);
      const erroEl = document.getElementById('mp-erro-tel');
      if (tel.length !== 10 && tel.length !== 11) {
        erroEl.classList.remove('hidden');
        return;
      }
      erroEl.classList.add('hidden');

      const btn = document.getElementById('mp-btn-identificar');
      btn.disabled = true;
      btn.textContent = 'Aguardando…';
      try {
        const { cliente, access_token } = await _identificar(tel);
        _salvarSessao(cliente, access_token);
        _mostrar('mp-carregando');
        await _carregar();
      } catch (err) {
        const msg = err.message || '';
        if (msg.toLowerCase().includes('nome obrigatório')) {
          // Telefone não cadastrado — mensagem amigável com botão para o cardápio
          _bannerHtml(
            'Não encontramos pedidos para esse telefone.' +
            '<a href="index.html" class="mp-banner-btn">Ver o cardápio</a>',
            'info'
          );
        } else {
          _banner(msg || 'Erro ao identificar. Tente novamente.', 'erro');
        }
      } finally {
        btn.disabled = false;
        btn.textContent = 'Ver meus pedidos';
      }
    });

    inputTel.addEventListener('keydown', e => {
      if (e.key === 'Enter') document.getElementById('mp-btn-identificar').click();
    });

    if (_carregarSessao()) {
      _mostrar('mp-carregando');
      await _carregar();
    } else {
      _mostrar('mp-nao-identificado');
    }
  }

  window.addEventListener('beforeunload', () => clearInterval(_polling));

  _init();
})();
