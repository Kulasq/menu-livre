window.cardapio = (() => {
  // ─── estado ───────────────────────────────────────────────
  let _dados = [];         // [{ categoria, produtos }]
  let _config = null;      // configuração da loja vinda da API
  let _produtoAtual = null;
  let _quantidade = 1;
  let _modificadoresSelecionados = {}; // { grupo_id: [modificador_id, ...] }

  // ─── elementos ────────────────────────────────────────────
  const els = {
    loading:          () => document.getElementById('loading'),
    erro:             () => document.getElementById('erro'),
    container:        () => document.getElementById('cardapio-container'),
    navLista:         () => document.getElementById('nav-lista'),
    banner:           () => document.getElementById('banner'),
    bannerImg:        () => document.getElementById('banner-img'),
    headerLogo:       () => document.getElementById('header-logo'),
    headerNome:       () => document.getElementById('header-nome'),
    headerEntrega:    () => document.getElementById('header-entrega'),
    statusBadge:      () => document.getElementById('status-badge'),
    headerWhatsapp:   () => document.getElementById('header-whatsapp'),
    headerInstagram:  () => document.getElementById('header-instagram'),
    avisoFechado:     () => document.getElementById('aviso-fechado'),
    avisoFechadoMsg:  () => document.getElementById('aviso-fechado-msg'),
    modal:            () => document.getElementById('modal-produto'),
    modalNome:        () => document.getElementById('modal-produto-nome'),
    modalDesc:        () => document.getElementById('modal-produto-desc'),
    modalPreco:       () => document.getElementById('modal-produto-preco'),
    modalFotoWrap:    () => document.getElementById('modal-produto-foto-wrap'),
    modalFoto:        () => document.getElementById('modal-produto-foto'),
    modalMods:        () => document.getElementById('modal-modificadores'),
    modalObs:         () => document.getElementById('modal-obs-input'),
    modalQtyValor:    () => document.getElementById('modal-qty-valor'),
    modalQtyMenos:    () => document.getElementById('modal-qty-menos'),
    modalQtyMais:     () => document.getElementById('modal-qty-mais'),
    modalBtnAdicionar:() => document.getElementById('modal-btn-adicionar'),
    modalOverlay:     () => document.getElementById('modal-produto-overlay'),
    modalFechar:      () => document.getElementById('modal-produto-fechar'),
  };

  // ─── utilitários ──────────────────────────────────────────
  function brl(valor) {
    return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  function fotoUrl(url) {
    if (!url) return null;
    if (url.startsWith('http')) return url;
    return `${CONFIG.API_URL}${url}`;
  }

  // ─── carregar dados da API ────────────────────────────────
  async function carregar() {
    els.loading().classList.remove('hidden');
    els.erro().classList.add('hidden');
    els.container().innerHTML = '';
    els.navLista().innerHTML = '';
    document.getElementById('nav-categorias').classList.add('nav-categorias--carregando');

    try {
      const [resCardapio, resConfig] = await Promise.all([
        fetch(`${CONFIG.API_URL}/api/cardapio`),
        fetch(`${CONFIG.API_URL}/api/configuracao`),
      ]);

      if (!resCardapio.ok) throw new Error('Erro ao carregar cardápio');

      const dataCardapio = await resCardapio.json();
      _dados = dataCardapio.categorias || [];

      if (resConfig.ok) {
        _config = await resConfig.json();
        _aplicarConfig(_config);
      }

      _renderNav();
      _renderCardapio();
    } catch (err) {
      console.error(err);
      els.erro().classList.remove('hidden');
    } finally {
      els.loading().classList.add('hidden');
      document.getElementById('nav-categorias').classList.remove('nav-categorias--carregando');
      if (_dados.length === 0) {
        document.getElementById('nav-categorias').style.display = 'none';
      }
    }
  }

  // ─── aplicar configuração da loja no header ───────────────
  function _aplicarConfig(config) {
    if (config.nome_loja) els.headerNome().textContent = config.nome_loja;

    if (config.logo_url) {
      els.headerLogo().src = fotoUrl(config.logo_url);
      els.headerLogo().classList.remove('hidden');
    }

    if (config.banner_url) {
      els.bannerImg().src = fotoUrl(config.banner_url);
      els.banner().classList.remove('hidden');
    }

    const tempoMin = config.tempo_entrega_min ?? 30;
    const tempoMax = config.tempo_entrega_max ?? 50;
    els.headerEntrega().textContent = `🕐 ${tempoMin}–${tempoMax} min`;

    if (config.whatsapp) {
      els.headerWhatsapp().href = `https://wa.me/55${config.whatsapp}`;
    }

    if (config.instagram_url) {
      els.headerInstagram().href = config.instagram_url;
    }

    const aberto = config.aceitar_pedidos !== false;
    const badge = els.statusBadge();
    badge.textContent = aberto ? '● Aberto' : '● Fechado';
    badge.className = `status-badge ${aberto ? 'status-aberto' : 'status-fechado'}`;

    if (!aberto) {
      els.avisoFechadoMsg().textContent =
        config.mensagem_fechado || 'Estamos fechados no momento.';
      els.avisoFechado().classList.remove('hidden');
    }
  }

  // ─── renderizar nav de categorias ────────────────────────
  function _renderNav() {
    const lista = els.navLista();
    lista.innerHTML = '';

    _dados.forEach((cat, idx) => {
      const btn = document.createElement('button');
      btn.className = `nav-item${idx === 0 ? ' ativo' : ''}`;
      btn.textContent = cat.nome;
      btn.dataset.id = cat.id;
      btn.addEventListener('click', () => _scrollParaCategoria(cat.id));
      lista.appendChild(btn);
    });
  }

  function _scrollParaCategoria(categoriaId) {
    const secao = document.getElementById(`cat-${categoriaId}`);
    if (!secao) return;
    const offsetTop = secao.getBoundingClientRect().top + window.scrollY;
    const headerH = document.getElementById('header').offsetHeight;
    const navH = document.getElementById('nav-categorias').offsetHeight;
    window.scrollTo({ top: offsetTop - headerH - navH - 8, behavior: 'smooth' });
  }

  function _renderCardapio() {
    const container = els.container();
    container.innerHTML = '';

    _dados.forEach((cat) => {
      const secao = document.createElement('section');
      secao.className = 'categoria-secao';
      secao.id = `cat-${cat.id}`;

      const titulo = document.createElement('h2');
      titulo.className = 'categoria-titulo';
      titulo.textContent = cat.nome;
      secao.appendChild(titulo);

      const destaques = cat.produtos.filter(p => p.destaque);
      const normais   = cat.produtos.filter(p => !p.destaque);

      if (destaques.length > 0) {
        const grade = document.createElement('div');
        grade.className = 'destaques-grid';
        destaques.forEach(p => grade.appendChild(_criarCardDestaque(p)));
        secao.appendChild(grade);
      }

      if (normais.length > 0) {
        const lista = document.createElement('div');
        lista.className = 'produtos-lista';
        normais.forEach(p => lista.appendChild(_criarCardProduto(p)));
        secao.appendChild(lista);
      }

      container.appendChild(secao);
    });

    _observarSecoes();
  }

  // ─── card destaque ────────────────────────────────────────
  function _criarCardDestaque(produto) {
    const card = document.createElement('div');
    card.className = 'card-destaque';
    card.addEventListener('click', () => abrirModal(produto));

    const foto = fotoUrl(produto.foto_url);
    if (foto) {
      const img = document.createElement('img');
      img.className = 'card-destaque-foto';
      img.src = foto;
      img.alt = produto.nome;
      img.loading = 'lazy';
      card.appendChild(img);
    } else {
      const ph = document.createElement('div');
      ph.className = 'card-destaque-foto-placeholder';
      ph.textContent = '🍔';
      card.appendChild(ph);
    }

    const info = document.createElement('div');
    info.className = 'card-destaque-info';
    info.innerHTML = `
      <div class="card-destaque-preco">${brl(produto.preco)}</div>
      <div class="card-destaque-nome">${produto.nome}</div>
    `;
    card.appendChild(info);

    const mais = document.createElement('div');
    mais.className = 'card-destaque-mais';
    mais.textContent = '+';
    card.appendChild(mais);

    return card;
  }

  // ─── card produto normal ──────────────────────────────────
  function _criarCardProduto(produto) {
    const card = document.createElement('div');
    card.className = 'card-produto';
    card.addEventListener('click', () => abrirModal(produto));

    const info = document.createElement('div');
    info.className = 'card-produto-info';
    info.innerHTML = `
      <div class="card-produto-nome">${produto.nome}</div>
      ${produto.descricao ? `<div class="card-produto-desc">${produto.descricao}</div>` : ''}
      <div class="card-produto-preco">${brl(produto.preco)}</div>
    `;
    card.appendChild(info);

    const fotoWrap = document.createElement('div');
    fotoWrap.className = 'card-produto-foto-wrap';

    const foto = fotoUrl(produto.foto_url);
    if (foto) {
      const img = document.createElement('img');
      img.className = 'card-produto-foto';
      img.src = foto;
      img.alt = produto.nome;
      img.loading = 'lazy';
      fotoWrap.appendChild(img);
    } else {
      const ph = document.createElement('div');
      ph.className = 'card-produto-foto-placeholder';
      ph.textContent = '🍔';
      fotoWrap.appendChild(ph);
    }

    const mais = document.createElement('div');
    mais.className = 'card-produto-mais';
    mais.textContent = '+';
    fotoWrap.appendChild(mais);

    card.appendChild(fotoWrap);
    return card;
  }

  // ─── observer para destacar categoria ativa no nav ────────
  function _observarSecoes() {
    const headerH = document.getElementById('header').offsetHeight;
    const navH    = document.getElementById('nav-categorias').offsetHeight;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const id = entry.target.id.replace('cat-', '');
        document.querySelectorAll('.nav-item').forEach(btn => {
          btn.classList.toggle('ativo', btn.dataset.id === id);
        });
        // centraliza o item ativo no nav
        const ativo = document.querySelector(`.nav-item[data-id="${id}"]`);
        if (ativo) ativo.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      });
    }, {
      rootMargin: `-${headerH + navH + 8}px 0px -60% 0px`,
    });

    document.querySelectorAll('.categoria-secao').forEach(s => observer.observe(s));
  }

  // ─── modal produto ────────────────────────────────────────
  function abrirModal(produto) {
    _produtoAtual = produto;
    _quantidade = 1;
    _modificadoresSelecionados = {};

    els.modalNome().textContent = produto.nome;
    els.modalDesc().textContent = produto.descricao || '';
    els.modalPreco().textContent = brl(produto.preco);
    els.modalObs().value = '';
    els.modalQtyValor().textContent = '1';

    const foto = fotoUrl(produto.foto_url);
    if (foto) {
      els.modalFoto().src = foto;
      els.modalFoto().alt = produto.nome;
      els.modalFotoWrap().classList.remove('hidden');
    } else {
      els.modalFotoWrap().classList.add('hidden');
    }

    _renderModificadores(produto.grupos_modificadores || []);
    _atualizarBtnAdicionar();

    els.modal().classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  function fecharModal() {
    els.modal().classList.add('hidden');
    document.body.style.overflow = '';
    _produtoAtual = null;
  }

  function _renderModificadores(grupos) {
    const container = els.modalMods();
    container.innerHTML = '';

    grupos.forEach(grupo => {
      const wrap = document.createElement('div');
      wrap.className = `grupo-modificador${grupo.obrigatorio ? ' grupo-obrigatorio' : ''}`;

      const header = document.createElement('div');
      header.className = 'grupo-modificador-header';

      const nome = document.createElement('span');
      nome.className = 'grupo-modificador-nome';
      nome.textContent = grupo.nome;

      const hint = document.createElement('span');
      hint.className = 'grupo-modificador-hint';
      const max = grupo.selecao_maxima;
      hint.textContent = max === 1 ? 'Selecione 1 opção' : `Selecione até ${max} opções`;

      header.appendChild(nome);
      header.appendChild(hint);
      wrap.appendChild(header);

      const tipo = grupo.selecao_maxima === 1 ? 'radio' : 'checkbox';

      grupo.modificadores.forEach(mod => {
        const label = document.createElement('label');
        label.className = 'modificador-opcao';

        const input = document.createElement('input');
        input.type = tipo;
        input.name = `grupo-${grupo.id}`;
        input.value = mod.id;
        input.addEventListener('change', () => _onModificadorChange(grupo, mod, input.checked));

        const labelTxt = document.createElement('span');
        labelTxt.className = 'modificador-label';
        labelTxt.textContent = mod.nome;

        const preco = document.createElement('span');
        preco.className = 'modificador-preco';
        preco.textContent = mod.preco_adicional > 0 ? `+${brl(mod.preco_adicional)}` : '';

        label.appendChild(input);
        label.appendChild(labelTxt);
        label.appendChild(preco);
        wrap.appendChild(label);
      });

      container.appendChild(wrap);
    });
  }

  function _onModificadorChange(grupo, mod, checked) {
    if (!_modificadoresSelecionados[grupo.id]) {
      _modificadoresSelecionados[grupo.id] = [];
    }

    if (grupo.selecao_maxima === 1) {
      // radio — substitui
      _modificadoresSelecionados[grupo.id] = checked ? [mod.id] : [];
    } else {
      // checkbox — adiciona ou remove
      if (checked) {
        _modificadoresSelecionados[grupo.id].push(mod.id);
      } else {
        _modificadoresSelecionados[grupo.id] =
          _modificadoresSelecionados[grupo.id].filter(id => id !== mod.id);
      }
    }

    _atualizarBtnAdicionar();
  }

  function _calcularPrecoAtual() {
    if (!_produtoAtual) return 0;
    let preco = _produtoAtual.preco;

    Object.values(_modificadoresSelecionados).flat().forEach(modId => {
      _produtoAtual.grupos_modificadores?.forEach(grupo => {
        const mod = grupo.modificadores.find(m => m.id === modId);
        if (mod) preco += mod.preco_adicional;
      });
    });

    return preco * _quantidade;
  }

  function _atualizarBtnAdicionar() {
    const btn = els.modalBtnAdicionar();
    const preco = _calcularPrecoAtual();
    btn.textContent = `Adicionar ${brl(preco)}`;

    // desabilitar se grupo obrigatório não preenchido
    const grupos = _produtoAtual?.grupos_modificadores || [];
    const invalido = grupos.some(grupo => {
      if (!grupo.obrigatorio) return false;
      const selecionados = (_modificadoresSelecionados[grupo.id] || []).length;
      return selecionados < grupo.selecao_minima;
    });

    btn.disabled = invalido;
  }

  // ─── eventos ──────────────────────────────────────────────
  function _initEventos() {
    els.modalFechar().addEventListener('click', fecharModal);
    els.modalOverlay().addEventListener('click', fecharModal);

    els.modalQtyMenos().addEventListener('click', () => {
      if (_quantidade <= 1) return;
      _quantidade--;
      els.modalQtyValor().textContent = _quantidade;
      _atualizarBtnAdicionar();
    });

    els.modalQtyMais().addEventListener('click', () => {
      _quantidade++;
      els.modalQtyValor().textContent = _quantidade;
      _atualizarBtnAdicionar();
    });

    els.modalBtnAdicionar().addEventListener('click', () => {
      if (!_produtoAtual) return;

      const modificadores = Object.values(_modificadoresSelecionados)
        .flat()
        .map(id => ({ modificador_id: id }));

      window.carrinho.adicionar({
        produto_id:   _produtoAtual.id,
        nome:         _produtoAtual.nome,
        preco:        _produtoAtual.preco,
        foto_url:     _produtoAtual.foto_url,
        quantidade:   _quantidade,
        observacao:   els.modalObs().value.trim() || null,
        modificadores,
        _grupos:      _produtoAtual.grupos_modificadores || [],
      });

      fecharModal();
    });

    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') fecharModal();
    });
  }

  // ─── init ─────────────────────────────────────────────────
  function init() {
    _initEventos();
    carregar();
  }

  return { init, carregar, abrirModal, fecharModal };
})();