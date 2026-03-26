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
  function brl(valor) {
    return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

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
    _atualizarBotaoHeader();
    _renderDrawer();
  }

  function _atualizarBotaoHeader() {
    const btn   = document.getElementById('btn-carrinho');
    const count = document.getElementById('carrinho-count');
    const qty   = quantidade();

    if (qty > 0) {
      count.textContent = qty;
      count.classList.remove('hidden');
    } else {
      count.classList.add('hidden');
    }
  }

  // ─── drawer ───────────────────────────────────────────────
  function abrirDrawer() {
    _renderDrawer();
    document.getElementById('drawer-carrinho').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  function fecharDrawer() {
    document.getElementById('drawer-carrinho').classList.add('hidden');
    document.body.style.overflow = '';
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
    document.getElementById('btn-carrinho').addEventListener('click', abrirDrawer);
    document.getElementById('drawer-fechar').addEventListener('click', fecharDrawer);
    document.getElementById('drawer-overlay').addEventListener('click', fecharDrawer);

    document.querySelectorAll('.btn-tipo-servico').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.btn-tipo-servico').forEach(b => b.classList.remove('ativo'));
        btn.classList.add('ativo');
        const tipo = btn.dataset.tipo;
        window.pedido.abrirModal(tipo);
        fecharDrawer();
      });
    });
  }

  function init() {
    _initEventos();
    _atualizar();
  }

  return { init, adicionar, remover, alterarQuantidade, limpar, obterItens, total, quantidade, abrirDrawer, fecharDrawer };
})();