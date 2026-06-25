window.carrinho = (() => {
  // ─── estado ───────────────────────────────────────────────
  let _itens = _carregar();

  // ─── persistência ─────────────────────────────────────────
  function _carregar() {
    try {
      return JSON.parse(localStorage.getItem(CONFIG.STORAGE_KEYS.CARRINHO)) || [];
    } catch {
      return [];
    }
  }

  function _salvar() {
    localStorage.setItem(CONFIG.STORAGE_KEYS.CARRINHO, JSON.stringify(_itens));
  }

  // ─── utilitários ──────────────────────────────────────────
  // brl() e _initDragFechar() são globais, definidos em utils.js.

  function fotoUrl(url) {
    if (!url) return null;
    if (url.startsWith('http')) return url;
    return `${CONFIG.API_URL}${url}`;
  }

  function _gerarId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2);
  }

  function total() {
    return _itens.reduce((acc, item) => {
      const extrasTotal = item.modificadores.reduce((s, m) => {
        const grupo = item._grupos?.find(g => g.modificadores.some(mod => mod.id === m.modificador_id));
        const mod   = grupo?.modificadores.find(mod => mod.id === m.modificador_id);
        return s + (mod?.preco_adicional || 0);
      }, 0);
      return acc + (item.preco + extrasTotal) * item.quantidade;
    }, 0);
  }

  function quantidade() {
    return _itens.reduce((acc, item) => acc + item.quantidade, 0);
  }

  // ─── ações ────────────────────────────────────────────────
  function adicionar(item) {
    _itens.push({ ...item, _id: _gerarId() });
    _salvar();
    _atualizar();
  }

  function remover(itemId) {
    _itens = _itens.filter(i => i._id !== itemId);
    _salvar();
    _atualizar();
  }

  function alterarQuantidade(itemId, delta) {
    const item = _itens.find(i => i._id === itemId);
    if (!item) return;
    item.quantidade += delta;
    if (item.quantidade <= 0) {
      remover(itemId);
      return;
    }
    _salvar();
    _atualizar();
  }

  function limpar() {
    _itens = [];
    _salvar();
    _atualizar();
  }

  function obterItens() {
    return [..._itens];
  }

  // ─── atualizar UI ─────────────────────────────────────────
  function _atualizar() {
    _atualizarBotaoFlutuante();
    _renderDrawer();
  }

  function _atualizarBotaoFlutuante() {
    const btn   = document.getElementById('btn-flutuante-carrinho');
    const qty   = document.getElementById('btn-flutuante-qty');
    const total = document.getElementById('btn-flutuante-total');
    const q     = quantidade();

    if (q > 0) {
      qty.textContent   = q;
      total.textContent = brl(window.carrinho.total());
      btn.classList.remove('hidden');
    } else {
      btn.classList.add('hidden');
    }
  }


  // ─── drawer ───────────────────────────────────────────────
  function abrirDrawer() {
    _renderDrawer();
    const drawer = document.getElementById('drawer-carrinho');
    const box = drawer.querySelector('.drawer-box');
    box.style.maxHeight = `${Math.round(window.innerHeight * 0.90)}px`;
    drawer.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  function fecharDrawer(skipAnim = false, callback = null) {
    const drawer = document.getElementById('drawer-carrinho');
    const box = drawer.querySelector('.drawer-box');
    if (skipAnim) {
      box.style.maxHeight = '';
      drawer.classList.add('hidden');
      document.body.style.overflow = '';
      if (callback) callback();
      return;
    }
    if (box.classList.contains('fechando')) return;
    drawer.classList.add('fechando');
    box.classList.add('fechando');
    box.addEventListener('animationend', () => {
      box.style.maxHeight = '';
      box.classList.remove('fechando');
      drawer.classList.remove('fechando');
      drawer.classList.add('hidden');
      document.body.style.overflow = '';
      if (callback) callback();
    }, { once: true });
  }

  function _renderDrawer() {
    const drawerItens  = document.getElementById('drawer-itens');
    const drawerVazio  = document.getElementById('drawer-vazio');
    const drawerRodape = document.getElementById('drawer-rodape');
    const totalEl      = document.getElementById('drawer-total-valor');

    drawerItens.innerHTML = '';

    if (_itens.length === 0) {
      drawerVazio.classList.remove('hidden');
      drawerRodape.classList.add('hidden');
      return;
    }

    drawerVazio.classList.add('hidden');
    drawerRodape.classList.remove('hidden');
    totalEl.textContent = brl(total());

    _itens.forEach(item => {
      const el = document.createElement('div');
      el.className = 'drawer-item';

      const foto = fotoUrl(item.foto_url);
      if (foto) {
        const img = document.createElement('img');
        img.className = 'drawer-item-foto';
        img.src = foto;
        img.alt = item.nome;
        el.appendChild(img);
      } else {
        const ph = document.createElement('div');
        ph.className = 'drawer-item-foto-placeholder';
        ph.textContent = '🍔';
        el.appendChild(ph);
      }

      const info = document.createElement('div');
      info.className = 'drawer-item-info';

      const nomeLine = document.createElement('div');
      nomeLine.className = 'drawer-item-nome';
      nomeLine.textContent = item.nome;
      info.appendChild(nomeLine);

      if (item.modificadores?.length > 0) {
        const modNomes = item.modificadores.map(m => {
          const grupo = item._grupos?.find(g => g.modificadores.some(mod => mod.id === m.modificador_id));
          return grupo?.modificadores.find(mod => mod.id === m.modificador_id)?.nome || '';
        }).filter(Boolean).join(', ');

        if (modNomes) {
          const modsLine = document.createElement('div');
          modsLine.className = 'drawer-item-mods';
          modsLine.textContent = modNomes;
          info.appendChild(modsLine);
        }
      }

      const precoItem = item.modificadores.reduce((s, m) => {
        const grupo = item._grupos?.find(g => g.modificadores.some(mod => mod.id === m.modificador_id));
        const mod   = grupo?.modificadores.find(mod => mod.id === m.modificador_id);
        return s + (mod?.preco_adicional || 0);
      }, item.preco);

      const precoLine = document.createElement('div');
      precoLine.className = 'drawer-item-preco';
      precoLine.textContent = brl(precoItem * item.quantidade);
      info.appendChild(precoLine);

      el.appendChild(info);

      const controles = document.createElement('div');
      controles.className = 'drawer-item-controles';

      const btnMenos = document.createElement('button');
      btnMenos.className = 'qty-btn';
      btnMenos.textContent = '−';
      btnMenos.setAttribute('aria-label', 'Diminuir quantidade');
      btnMenos.addEventListener('click', () => alterarQuantidade(item._id, -1));

      const qty = document.createElement('span');
      qty.className = 'drawer-item-qty';
      qty.textContent = item.quantidade;

      const btnMais = document.createElement('button');
      btnMais.className = 'qty-btn';
      btnMais.textContent = '+';
      btnMais.setAttribute('aria-label', 'Aumentar quantidade');
      btnMais.addEventListener('click', () => alterarQuantidade(item._id, 1));

      const btnRemover = document.createElement('button');
      btnRemover.className = 'btn-item-remover';
      btnRemover.textContent = '🗑';
      btnRemover.setAttribute('aria-label', 'Remover item');
      btnRemover.addEventListener('click', () => remover(item._id));

      controles.appendChild(btnRemover);
      controles.appendChild(btnMenos);
      controles.appendChild(qty);
      controles.appendChild(btnMais);
      el.appendChild(controles);

      drawerItens.appendChild(el);
    });
  }

  // ─── eventos ──────────────────────────────────────────────
  function _initEventos() {
    document.getElementById('drawer-overlay').addEventListener('click', () => fecharDrawer());
    document.getElementById('drawer-fechar').addEventListener('click', () => fecharDrawer());
    document.getElementById('btn-flutuante-inner').addEventListener('click', abrirDrawer);

    document.querySelectorAll('.btn-tipo-servico').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.btn-tipo-servico').forEach(b => b.classList.remove('ativo'));
        btn.classList.add('ativo');
        const tipo = btn.dataset.tipo;
        // fecha o drawer com animação e abre o checkout só após terminar
        fecharDrawer(false, () => window.pedido.abrirModal(tipo));
      });
    });

    const drawerBox = document.querySelector('#drawer-carrinho .drawer-box');
    _initDragFechar(
      document.getElementById('drawer-handle'),
      drawerBox,
      (skip) => fecharDrawer(skip)
    );
  }

  function init() {
    _initEventos();
    _atualizar();
  }

  function adicionarDireto(item) {
    // Adiciona item com dados já prontos (vindo de "pedir igual")
    _itens.push({
      _id:           _gerarId(),
      produto_id:    item.produto_id,
      nome:          item.nome,
      preco:         item.preco,
      foto_url:      item.foto_url || null,
      quantidade:    item.quantidade,
      observacao:    item.observacao || null,
      modificadores: item.modificadores || [],
      _grupos:       [],
    });
    _salvar();
    _atualizar();
  }

  return { init, adicionar, adicionarDireto, remover, alterarQuantidade, limpar, obterItens, total, quantidade, abrirDrawer, fecharDrawer };
})();