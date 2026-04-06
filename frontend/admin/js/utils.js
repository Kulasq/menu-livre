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