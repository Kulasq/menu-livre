/* frontend/admin/js/utils.js */

/**
 * Utilitários compartilhados do painel admin.
 * Depende de: admin.css (estilos de .toast)
 */

/* ── Toast notifications ── */

const toast = {
  _container: null,

  _getContainer() {
    if (!this._container) {
      this._container = document.createElement('div')
      this._container.className = 'toast-container'
      document.body.appendChild(this._container)
    }
    return this._container
  },

  show(msg, tipo = 'sucesso', duracao = 3000) {
    const container = this._getContainer()
    const el = document.createElement('div')
    el.className = `toast toast-${tipo}`
    el.textContent = msg
    container.appendChild(el)

    setTimeout(() => {
      el.style.opacity = '0'
      el.style.transform = 'translateX(20px)'
      el.style.transition = 'opacity .2s, transform .2s'
      setTimeout(() => el.remove(), 200)
    }, duracao)
  },

  sucesso(msg) { this.show(msg, 'sucesso') },
  erro(msg) { this.show(msg, 'erro', 4000) },
}


/* ── Formatadores ── */

function formatarPreco(valor) {
  return `R$ ${Number(valor).toFixed(2).replace('.', ',')}`
}

function formatarData(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('pt-BR')
}


/* ── Helpers DOM ── */

function $(seletor) {
  return document.querySelector(seletor)
}

function $$(seletor) {
  return document.querySelectorAll(seletor)
}


/* ── Nome da loja na sidebar ─────────────────────────────────────────────────
 * Atualiza o <h2 id="sidebar-nome-loja"> em todas as páginas admin.
 * Usa sessionStorage para cachear o valor e evitar chamadas redundantes.
 * O cache é limpo automaticamente quando a aba/sessão é fechada.
 */

const _CACHE_KEY_NOME = 'ml_nome_loja'

function atualizarNomeLojaSidebar(nome) {
  if (!nome) return
  const el = document.getElementById('sidebar-nome-loja')
  if (el) el.textContent = nome
  try { sessionStorage.setItem(_CACHE_KEY_NOME, nome) } catch (_) { /* storage bloqueado */ }
}

/**
 * Carrega o nome da loja para a sidebar.
 * Usa cache de sessão — só faz fetch se o valor ainda não estiver guardado.
 * Chamar no DOMContentLoaded de cada página admin (exceto login).
 */
async function carregarNomeLojaSidebar() {
  // 1. Tenta o cache primeiro (resposta imediata, sem latência)
  try {
    const cached = sessionStorage.getItem(_CACHE_KEY_NOME)
    if (cached) {
      atualizarNomeLojaSidebar(cached)
      return
    }
  } catch (_) { /* storage bloqueado */ }

  // 2. Sem cache: faz o fetch autenticado
  try {
    const config = await api.get('/api/admin/configuracoes')
    if (config?.nome_loja) atualizarNomeLojaSidebar(config.nome_loja)
  } catch (_) {
    // Silencioso — sidebar continua com o texto padrão do HTML
  }
}