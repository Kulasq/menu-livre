window.cardapio = (() => {
  // ─── estado ───────────────────────────────────────────────
  let _dados = [];         // [{ categoria, produtos }]
  let _config = null;      // configuração da loja vinda da API
  let _produtoAtual = null;
  let _quantidade = 1;
  let _modificadoresSelecionados = {}; // { grupo_id: [modificador_id, ...] }
  let _scrollProgramatico = false;
  let _scrollProgTimer = null;

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
    btnInfoLoja:      () => document.getElementById('btn-info-loja'),
    headerWhatsapp:   () => document.getElementById('header-whatsapp'),
    headerInstagram:  () => document.getElementById('header-instagram'),
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
    modalHandle:      () => document.getElementById('modal-produto-handle'),
  };

  // ─── utilitários ──────────────────────────────────────────
  function brl(valor) {
    return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  /**
   * Escapa caracteres HTML especiais para evitar XSS ao usar innerHTML.
   * Usar sempre que inserir strings vindas da API dentro de innerHTML.
   * Para texto puro, prefira textContent — mais seguro e sem necessidade de escape.
   */
  function esc(str) {
    if (!str) return '';
    const el = document.createElement('span');
    el.textContent = str;
    return el.innerHTML;
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
        _aplicarCores(_config);
      }

      _renderNav();
      _renderCardapio();
      window.dispatchEvent(new CustomEvent('cardapio:carregado'));
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
    const nome = config.nome_loja || 'Cardápio';

    // Atualiza nome visível no header
    els.headerNome().textContent = nome;

    // Atualiza <title> e <meta description> dinamicamente
    document.title = nome + ' — Cardápio';
    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) metaDesc.content = `Cardápio digital de ${nome}. Faça seu pedido pelo WhatsApp.`;

    if (config.logo_url) {
      els.headerLogo().src = fotoUrl(config.logo_url);
      els.headerLogo().alt = `Logo ${nome}`;
      els.headerLogo().classList.remove('hidden');
    }

    if (config.banner_url) {
      els.bannerImg().src = fotoUrl(config.banner_url);
      els.bannerImg().alt = `Banner ${nome}`;
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

    const aberto = config.aberto;
    const badge = els.statusBadge();
    const textoEl = badge.querySelector('.status-texto');
    textoEl.textContent = aberto ? 'Aberto' : 'Fechado';
    badge.className = `status-badge ${aberto ? 'status-aberto' : 'status-fechado'}`;

    // Listener no botão dedicado (registrado uma única vez via flag no elemento)
    const btnInfo = els.btnInfoLoja();
    if (btnInfo && !btnInfo.dataset.infoListenerAdded) {
      btnInfo.addEventListener('click', _abrirModalInfoLoja);
      btnInfo.dataset.infoListenerAdded = '1';
    }

    if (!aberto && config.aceitar_agendamentos) {
      _mostrarAvisoAgendamento(config.mensagem_fechado);
    }
  }

  // ─── modal info da loja (horários + endereço) ─────────────

  const _DIAS_NOMES = {
    domingo: 'Domingo',
    segunda: 'Segunda',
    terca:   'Terça',
    quarta:  'Quarta',
    quinta:  'Quinta',
    sexta:   'Sexta',
    sabado:  'Sábado',
  };

  const _DIAS_ORDEM = ['domingo', 'segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado'];

  function _formatarHora(hhmm) {
    const [h, m] = hhmm.split(':');
    return m === '00' ? `${h}h` : `${h}h${m}`;
  }

  function _abrirModalInfoLoja() {
    const modal    = document.getElementById('modal-info-loja');
    const overlay  = document.getElementById('modal-info-loja-overlay');
    const btnFechar = document.getElementById('modal-info-fechar');
    const lista    = document.getElementById('modal-info-horarios');
    const endWrap  = document.getElementById('modal-info-endereco-wrap');
    const endTexto = document.getElementById('modal-info-endereco');
    const btnInfo  = els.btnInfoLoja();

    // Renderizar horários — começar pelo dia de hoje
    lista.innerHTML = '';
    const hojeIdx = new Date().getDay(); // 0=dom, 1=seg...
    const ordemHoje = [
      ..._DIAS_ORDEM.slice(hojeIdx),
      ..._DIAS_ORDEM.slice(0, hojeIdx),
    ];

    const horarios = _config?.horarios ?? null;

    ordemHoje.forEach((slug, i) => {
      const diaConfig = horarios?.[slug];
      const li = document.createElement('li');
      li.className = `modal-info-dia${i === 0 ? ' hoje' : ''}`;

      const nomeEl = document.createElement('span');
      nomeEl.className = 'modal-info-dia-nome';
      nomeEl.textContent = _DIAS_NOMES[slug];
      if (i === 0) {
        const hoje = document.createElement('span');
        hoje.className = 'hoje-label';
        hoje.textContent = 'Hoje';
        nomeEl.appendChild(hoje);
      }

      const horasEl = document.createElement('span');
      horasEl.className = 'modal-info-dia-horas';

      if (!diaConfig || !diaConfig.aberto || !diaConfig.horarios?.length) {
        horasEl.textContent = 'Fechado';
      } else {
        horasEl.textContent = diaConfig.horarios
          .map(iv => `${_formatarHora(iv.inicio)} às ${_formatarHora(iv.fim)}`)
          .join(' e ');
      }

      li.appendChild(nomeEl);
      li.appendChild(horasEl);
      lista.appendChild(li);
    });

    // Endereço + botão Como chegar
    const endereco  = _config?.endereco;
    const mapsUrl   = _config?.maps_url;
    const btnChegar = document.getElementById('modal-info-como-chegar');
    if (endereco) {
      endTexto.textContent = endereco;
      endWrap.classList.remove('hidden');
      btnChegar.href = mapsUrl || ('https://maps.google.com/?q=' + encodeURIComponent(endereco));
      btnChegar.classList.remove('hidden');
    } else {
      endWrap.classList.add('hidden');
      btnChegar.classList.add('hidden');
    }

    // Abrir modal
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    if (btnInfo) btnInfo.setAttribute('aria-expanded', 'true');

    // Foco no botão fechar (a11y)
    btnFechar.focus();

    const boxInfo = modal.querySelector('.modal-box-info-loja');

    function fechar() {
      // remove listeners imediatamente para não disparar duas vezes
      overlay.removeEventListener('click', fechar);
      btnFechar.removeEventListener('click', fechar);
      document.removeEventListener('keydown', onEsc);

      // animação de saída
      boxInfo.classList.add('fechando');
      boxInfo.addEventListener('animationend', () => {
        boxInfo.classList.remove('fechando');
        modal.classList.add('hidden');
        document.body.style.overflow = '';
        if (btnInfo) btnInfo.setAttribute('aria-expanded', 'false');
        if (btnInfo) btnInfo.focus();
      }, { once: true });
    }

    function onEsc(e) {
      if (e.key === 'Escape') fechar();
    }

    overlay.addEventListener('click', fechar);
    btnFechar.addEventListener('click', fechar);
    document.addEventListener('keydown', onEsc);
  }

  function _mostrarAvisoAgendamento(mensagem) {
    const modal  = document.getElementById('modal-aviso-fechado');
    const msgEl  = document.getElementById('modal-aviso-msg');
    const btn    = document.getElementById('modal-aviso-ok');

    msgEl.textContent = mensagem || 'Estamos fechados no momento.';
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    btn.addEventListener('click', () => {
      modal.classList.add('hidden');
      document.body.style.overflow = '';
    }, { once: true });
  }

  // ─── aplicar paleta de cores via CSS variables ───────────
  function _aplicarCores(config) {
    const root = document.documentElement;

    // Mapeamento: campo da API → CSS variable(s) que controla
    const mapa = [
      { campo: 'cor_primaria',   vars: ['--marrom-btn', '--marrom-hover'] },
      { campo: 'cor_secundaria', vars: ['--marrom'] },
      { campo: 'cor_fundo',      vars: ['--bg'] },
      { campo: 'cor_fonte',      vars: ['--texto'] },
      { campo: 'cor_banner',     vars: ['--banner-bg'] },
    ];

    mapa.forEach(({ campo, vars }) => {
      const valor = config[campo];
      if (valor) {
        vars.forEach(v => root.style.setProperty(v, valor));
      }
    });
  }

  // ─── renderizar nav de categorias ────────────────────────
  function _renderNav() {
    const lista = els.navLista();
    lista.innerHTML = '';

    const temDestaques = _dados.some(cat => cat.produtos.some(p => p.destaque));
    const catsComItens = _dados.filter(cat => cat.produtos.length > 0);

    if (temDestaques) {
      const btn = document.createElement('button');
      btn.className = 'nav-item ativo';
      btn.textContent = 'Destaques';
      btn.dataset.id = 'destaques';
      btn.addEventListener('click', () => _scrollParaCategoria('destaques'));
      lista.appendChild(btn);
    }

    catsComItens.forEach((cat, idx) => {
      const btn = document.createElement('button');
      btn.className = `nav-item${!temDestaques && idx === 0 ? ' ativo' : ''}`;
      btn.textContent = cat.nome;
      btn.dataset.id = cat.id;
      btn.addEventListener('click', () => _scrollParaCategoria(cat.id));
      lista.appendChild(btn);
    });
  }

  function _destacarNav(id) {
    document.querySelectorAll('.nav-item').forEach(btn => {
      btn.classList.toggle('ativo', btn.dataset.id === String(id));
    });
    const ativo = document.querySelector(`.nav-item[data-id="${id}"]`);
    if (ativo) ativo.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
  }

  function _scrollParaCategoria(categoriaId) {
    const secao = document.getElementById(`cat-${categoriaId}`);
    if (!secao) return;

    _destacarNav(categoriaId);

    _scrollProgramatico = true;
    if (_scrollProgTimer) clearTimeout(_scrollProgTimer);

    const offsetTop = secao.getBoundingClientRect().top + window.scrollY;
    const headerH = document.getElementById('header').offsetHeight;
    const navH = document.getElementById('nav-categorias').offsetHeight;
    window.scrollTo({ top: offsetTop - headerH - navH - 8, behavior: 'smooth' });

    const liberar = () => { _scrollProgramatico = false; };
    if ('onscrollend' in window) {
      window.addEventListener('scrollend', liberar, { once: true });
    } else {
      _scrollProgTimer = setTimeout(liberar, 700);
    }
  }

  function _renderCardapio() {
    const container = els.container();
    container.innerHTML = '';

    // Seção "Destaques" fixa no topo — produtos destaque=true de todas as categorias
    const todosDestaques = _dados.flatMap(cat => cat.produtos.filter(p => p.destaque));
    if (todosDestaques.length > 0) {
      const secao = document.createElement('section');
      secao.className = 'categoria-secao';
      secao.id = 'cat-destaques';

      const titulo = document.createElement('h2');
      titulo.className = 'categoria-titulo';
      titulo.textContent = 'Destaques';
      secao.appendChild(titulo);

      const grade = document.createElement('div');
      grade.className = 'destaques-grid';
      todosDestaques.forEach(p => grade.appendChild(_criarCardDestaque(p)));
      secao.appendChild(grade);

      container.appendChild(secao);
    }

    _dados.filter(cat => cat.produtos.length > 0).forEach((cat) => {
      const secao = document.createElement('section');
      secao.className = 'categoria-secao';
      secao.id = `cat-${cat.id}`;

      const titulo = document.createElement('h2');
      titulo.className = 'categoria-titulo';
      titulo.textContent = cat.nome;
      secao.appendChild(titulo);

      const lista = document.createElement('div');
      lista.className = 'produtos-lista';
      cat.produtos.forEach(p => lista.appendChild(_criarCardProduto(p)));
      secao.appendChild(lista);

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
      <div class="card-destaque-nome">${esc(produto.nome)}</div>
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
      <div class="card-produto-nome">${esc(produto.nome)}</div>
      ${produto.descricao ? `<div class="card-produto-desc">${esc(produto.descricao)}</div>` : ''}
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

  // ─── detectar categoria ativa com histerese por direção ────
  function _observarSecoes() {
    let _ultimoScrollY = window.scrollY;

    function _atualizarCategoriaAtiva() {
      if (_scrollProgramatico) return;

      const secoes = document.querySelectorAll('.categoria-secao');
      const scrollY = window.scrollY;
      const subindo = scrollY < _ultimoScrollY;
      _ultimoScrollY = scrollY;

      // quando a página bate no fundo, destaca a última seção (categorias curtas no final)
      const distanciaDoFundo = document.documentElement.scrollHeight - window.innerHeight - scrollY;
      if (distanciaDoFundo <= 4) {
        if (secoes.length) _destacarNav(secoes[secoes.length - 1].id.replace('cat-', ''));
        return;
      }

      // se o topo da primeira seção ainda está visível, ela é dominante — não depende da linha de histerese
      if (secoes.length && secoes[0].getBoundingClientRect().top > 0) {
        _destacarNav(secoes[0].id.replace('cat-', ''));
        return;
      }

      // histerese: linha de detecção diferente por direção de scroll
      // descendo → 20%: ativa cedo, assim que a seção aparece no topo
      // subindo  → 60%: só ativa quando a seção anterior já ocupa boa parte da tela
      const linha = window.innerHeight * (subindo ? 0.60 : 0.20);

      // categoria ativa: última cujo TOPO está acima da linha de referência
      let ativa = null;
      for (const secao of secoes) {
        const rect = secao.getBoundingClientRect();
        if (rect.top > linha) break;
        ativa = secao;
      }

      if (ativa) _destacarNav(ativa.id.replace('cat-', ''));
    }

    let _raf = null;
    window.addEventListener('scroll', () => {
      if (_raf) return;
      _raf = requestAnimationFrame(() => {
        _raf = null;
        _atualizarCategoriaAtiva();
      });
    }, { passive: true });

    // estado inicial correto ao carregar a página
    _atualizarCategoriaAtiva();
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
        // continua o movimento e fecha sem re-animar
        boxEl.style.transition = 'transform .2s ease-in';
        boxEl.style.transform  = 'translateY(110%)';
        boxEl.addEventListener('transitionend', () => {
          boxEl.style.transition = '';
          boxEl.style.transform  = '';
          fecharFn(true); // skipAnim = true
        }, { once: true });
      } else {
        // snap back
        boxEl.addEventListener('transitionend', () => {
          boxEl.style.transition = '';
        }, { once: true });
        boxEl.style.transition = 'transform .25s cubic-bezier(.2,.8,.3,1)';
        boxEl.style.transform  = '';
      }
    });
  }

  function fecharModal(skipAnim = false) {
    const isMobile = window.matchMedia('(max-width: 599px)').matches;
    const modal = els.modal();
    const box = modal.querySelector('.modal-box');
    if (!isMobile || skipAnim) {
      box.style.maxHeight = '';
      modal.classList.add('hidden');
      document.body.style.overflow = '';
      _produtoAtual = null;
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
      _produtoAtual = null;
    }, { once: true });
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

      // Filtra opções indisponíveis (esgotadas pelo admin) — não exibe ao cliente
      const opcoesDisponiveis = grupo.modificadores.filter(m => m.disponivel !== false);
      // Se todas as opções do grupo estiverem esgotadas, omite o grupo inteiro
      if (opcoesDisponiveis.length === 0) return;

      opcoesDisponiveis.forEach(mod => {
        const label = document.createElement('label');
        label.className = 'modificador-opcao';

        const input = document.createElement('input');
        input.type = tipo;
        input.name = `grupo-${grupo.id}`;
        input.value = mod.id;
        input.addEventListener('change', () => _onModificadorChange(grupo, mod, input.checked));

        // Permite desmarcar radio em grupos não-obrigatórios
        if (tipo === 'radio' && !grupo.obrigatorio) {
          let _estavaMarcado = false;
          input.addEventListener('mousedown', () => { _estavaMarcado = input.checked; });
          input.addEventListener('touchstart', () => { _estavaMarcado = input.checked; }, { passive: true });
          input.addEventListener('click', () => {
            if (_estavaMarcado) {
              input.checked = false;
              _onModificadorChange(grupo, mod, false);
            }
          });
        }

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
      // checkbox — adiciona ou remove com limite de selecao_maxima
      if (checked) {
        if (_modificadoresSelecionados[grupo.id].length >= grupo.selecao_maxima) {
          // Atingiu o máximo — desfaz visualmente e ignora
          const input = document.querySelector(`input[name="grupo-${grupo.id}"][value="${mod.id}"]`);
          if (input) input.checked = false;
          return;
        }
        _modificadoresSelecionados[grupo.id].push(mod.id);
      } else {
        _modificadoresSelecionados[grupo.id] =
          _modificadoresSelecionados[grupo.id].filter(id => id !== mod.id);
      }
      // Atualiza visual dos checkboxes restantes (desabilita quando no máximo)
      _atualizarEstadoCheckboxesGrupo(grupo);
    }

    _atualizarBtnAdicionar();
  }

  // Desabilita checkboxes não marcados quando o grupo atingiu selecao_maxima
  function _atualizarEstadoCheckboxesGrupo(grupo) {
    const qtd     = _modificadoresSelecionados[grupo.id]?.length || 0;
    const noMax   = qtd >= grupo.selecao_maxima;
    document.querySelectorAll(`input[name="grupo-${grupo.id}"]`).forEach(input => {
      const label = input.closest('label');
      if (input.checked) {
        input.disabled = false;
        if (label) label.style.opacity = '';
      } else {
        input.disabled = noMax;
        if (label) label.style.opacity = noMax ? '0.4' : '';
      }
    });
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
    els.modalOverlay().addEventListener('click', () => fecharModal());
    _initDragFechar(
      els.modalHandle(),
      document.querySelector('#modal-produto .modal-box'),
      (skip) => fecharModal(skip)
    );

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