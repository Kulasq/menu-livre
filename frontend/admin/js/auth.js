const api = {
  _refreshPromise: null,

  async request(path, options = {}) {
    const token = localStorage.getItem(CONFIG.STORAGE.ACCESS_TOKEN)

    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const res = await fetch(`${CONFIG.API_URL}${path}`, {
      ...options,
      headers,
    })

    /* 401 → tenta refresh uma única vez */
    if (res.status === 401 && token) {
      const refreshed = await this._tryRefresh()
      if (refreshed) {
        return this.request(path, options)
      }
      auth.logout()
      return
    }

    if (!res.ok) {
      const erro = await res.json().catch(() => null)
      const msg = erro?.detail ?? `Erro ${res.status}`
      throw new ApiError(res.status, msg)
    }

    if (res.status === 204) return null
    return res.json()
  },

  get(path) {
    return this.request(path)
  },

  post(path, data) {
    return this.request(path, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  put(path, data) {
    return this.request(path, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },

  patch(path, data) {
    return this.request(path, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  },

  delete(path) {
    return this.request(path, { method: 'DELETE' })
  },

  /**
   * Refresh do token — garante que só uma chamada ocorra por vez.
   * Se múltiplas requests receberem 401 simultaneamente,
   * todas aguardam o mesmo refresh.
   */
  async _tryRefresh() {
    if (this._refreshPromise) return this._refreshPromise

    this._refreshPromise = (async () => {
      const refreshToken = localStorage.getItem(CONFIG.STORAGE.REFRESH_TOKEN)
      if (!refreshToken) return false

      try {
        const res = await fetch(`${CONFIG.API_URL}/api/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        })

        if (!res.ok) return false

        const data = await res.json()
        localStorage.setItem(CONFIG.STORAGE.ACCESS_TOKEN, data.access_token)
        return true
      } catch {
        return false
      } finally {
        this._refreshPromise = null
      }
    })()

    return this._refreshPromise
  },
}


/**
 * Erro tipado para respostas da API.
 */
class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}


/**
 * Módulo de autenticação — login, logout, verificação de sessão.
 */
const auth = {
  /**
   * Faz login e armazena tokens + dados do usuário.
   * @returns {{ usuario_nome: string, usuario_role: string }}
   */
  async login(email, senha) {
    const data = await api.post('/api/auth/login', { email, senha })

    localStorage.setItem(CONFIG.STORAGE.ACCESS_TOKEN, data.access_token)
    localStorage.setItem(CONFIG.STORAGE.REFRESH_TOKEN, data.refresh_token)
    localStorage.setItem(CONFIG.STORAGE.USUARIO_NOME, data.usuario_nome)
    localStorage.setItem(CONFIG.STORAGE.USUARIO_ROLE, data.usuario_role)

    return {
      usuario_nome: data.usuario_nome,
      usuario_role: data.usuario_role,
    }
  },

  /** Limpa sessão e redireciona para o login. */
  logout() {
    localStorage.removeItem(CONFIG.STORAGE.ACCESS_TOKEN)
    localStorage.removeItem(CONFIG.STORAGE.REFRESH_TOKEN)
    localStorage.removeItem(CONFIG.STORAGE.USUARIO_NOME)
    localStorage.removeItem(CONFIG.STORAGE.USUARIO_ROLE)
    window.location.href = CONFIG.PAGINAS.LOGIN
  },

  /** Verifica se há token salvo. */
  isAutenticado() {
    return !!localStorage.getItem(CONFIG.STORAGE.ACCESS_TOKEN)
  },

  /** Retorna dados do usuário logado. */
  getUsuario() {
    return {
      nome: localStorage.getItem(CONFIG.STORAGE.USUARIO_NOME) || '',
      role: localStorage.getItem(CONFIG.STORAGE.USUARIO_ROLE) || '',
    }
  },

  /**
   * Proteção de rota — chamar no topo de cada página protegida.
   * Se não autenticado, redireciona para login.
   */
  proteger() {
    if (!this.isAutenticado()) {
      window.location.href = CONFIG.PAGINAS.LOGIN
      return false
    }
    return true
  },
}


/**
 * Inicialização da página de login.
 * Se já autenticado, redireciona direto para o dashboard.
 */
function initLogin() {
  if (auth.isAutenticado()) {
    window.location.href = CONFIG.PAGINAS.DASHBOARD
    return
  }

  const form = document.getElementById('form-login')
  const inputEmail = document.getElementById('input-email')
  const inputSenha = document.getElementById('input-senha')
  const btnEntrar = document.getElementById('btn-entrar')
  const msgErro = document.getElementById('login-erro')

  form.addEventListener('submit', async (e) => {
    e.preventDefault()
    msgErro.classList.add('hidden')

    const email = inputEmail.value.trim()
    const senha = inputSenha.value

    if (!email || !senha) {
      mostrarErro('Preencha e-mail e senha.')
      return
    }

    btnEntrar.disabled = true
    btnEntrar.textContent = 'Entrando…'

    try {
      await auth.login(email, senha)
      window.location.href = CONFIG.PAGINAS.DASHBOARD
    } catch (err) {
      const msg = err instanceof ApiError
        ? err.message
        : 'Não foi possível conectar ao servidor.'
      mostrarErro(msg)
    } finally {
      btnEntrar.disabled = false
      btnEntrar.textContent = 'Entrar'
    }
  })

  function mostrarErro(texto) {
    msgErro.textContent = texto
    msgErro.classList.remove('hidden')
  }
}

document.addEventListener('DOMContentLoaded', initLogin)