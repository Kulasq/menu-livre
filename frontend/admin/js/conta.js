/* frontend/admin/js/conta.js
 *
 * Gerencia o menu de conta do usuário no header do admin.
 * Injeta o dropdown e o modal no DOM — nenhuma página precisa ter HTML extra.
 *
 * Depende de: config.js, auth.js, utils.js (toast)
 * Adicionar em todas as páginas admin: <script src="js/conta.js"></script>
 */

(function () {
  'use strict'

  // ── Estado local ───────────────────────────────────────────────────────────

  let _dropdownAberto = false
  let _dropdownEl = null
  let _modalEl = null
  let _dadosUsuario = null   // cache: { id, nome, email, role }

  // ── Inicialização ──────────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', () => {
    _preencherHeaderUsuario()
    _configurarAvatar()
    _injetarModal()
  })

  // ── Header: nome + inicial do avatar ──────────────────────────────────────

  function _preencherHeaderUsuario() {
    const usuario = auth.getUsuario()
    const elNome = document.getElementById('header-usuario-nome')
    const elAvatar = document.getElementById('header-usuario-avatar')

    if (elNome) elNome.textContent = usuario.nome || 'Admin'
    if (elAvatar) elAvatar.textContent = _inicial(usuario.nome)
  }

  function _inicial(nome) {
    return (nome || 'A').trim().charAt(0).toUpperCase()
  }

  // ── Avatar: abre/fecha dropdown ───────────────────────────────────────────

  function _configurarAvatar() {
    const avatar = document.getElementById('header-usuario-avatar')
    if (!avatar) return

    avatar.setAttribute('role', 'button')
    avatar.setAttribute('aria-label', 'Menu da conta')
    avatar.setAttribute('tabindex', '0')

    avatar.addEventListener('click', (e) => {
      e.stopPropagation()
      _dropdownAberto ? _fecharDropdown() : _abrirDropdown(avatar)
    })

    avatar.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault()
        _dropdownAberto ? _fecharDropdown() : _abrirDropdown(avatar)
      }
    })

    document.addEventListener('click', () => {
      if (_dropdownAberto) _fecharDropdown()
    })

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && _dropdownAberto) _fecharDropdown()
    })
  }

  function _abrirDropdown(avatar) {
    _fecharDropdown()

    const usuario = auth.getUsuario()
    const wrapper = document.querySelector('.admin-header-usuario')
    if (!wrapper) return

    const dropdown = document.createElement('div')
    dropdown.className = 'conta-dropdown'
    dropdown.setAttribute('role', 'menu')
    dropdown.innerHTML = `
      <div class="conta-dropdown-header">
        <span class="conta-dropdown-nome">${_esc(usuario.nome || 'Admin')}</span>
        <span class="conta-dropdown-email" id="dropdown-email">—</span>
      </div>
      <button class="conta-dropdown-item" id="dd-minha-conta" role="menuitem">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
        </svg>
        Minha conta
      </button>
      <button class="conta-dropdown-item danger" id="dd-sair" role="menuitem">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 9V5.25A2.25 2.25 0 0 1 10.5 3h6a2.25 2.25 0 0 1 2.25 2.25v13.5A2.25 2.25 0 0 1 16.5 21h-6a2.25 2.25 0 0 1-2.25-2.25V15m-3 0-3-3m0 0 3-3m-3 3H15" />
        </svg>
        Sair
      </button>
    `

    wrapper.appendChild(dropdown)
    _dropdownEl = dropdown
    _dropdownAberto = true

    // Preenche e-mail via API (sem bloquear a abertura do dropdown)
    _carregarEmailNoDropdown()

    dropdown.getElementById = (id) => dropdown.querySelector('#' + id)
    dropdown.querySelector('#dd-minha-conta').addEventListener('click', (e) => {
      e.stopPropagation()
      _fecharDropdown()
      _abrirModal()
    })

    dropdown.querySelector('#dd-sair').addEventListener('click', (e) => {
      e.stopPropagation()
      auth.logout()
    })

    dropdown.addEventListener('click', (e) => e.stopPropagation())
  }

  function _fecharDropdown() {
    if (_dropdownEl) {
      _dropdownEl.remove()
      _dropdownEl = null
    }
    _dropdownAberto = false
  }

  async function _carregarEmailNoDropdown() {
    try {
      const me = await api.get('/api/auth/me')
      _dadosUsuario = me
      const elEmail = document.getElementById('dropdown-email')
      if (elEmail) elEmail.textContent = me.email
    } catch (_) {
      // Silencioso — e-mail simplesmente não aparece
    }
  }

  // ── Modal de Minha Conta ───────────────────────────────────────────────────

  function _injetarModal() {
    const overlay = document.createElement('div')
    overlay.className = 'modal-overlay hidden'
    overlay.id = 'modal-conta'
    overlay.setAttribute('role', 'dialog')
    overlay.setAttribute('aria-modal', 'true')
    overlay.setAttribute('aria-labelledby', 'modal-conta-titulo')

    overlay.innerHTML = `
      <div class="modal-box" id="modal-conta-box">

        <div class="modal-header">
          <h2 id="modal-conta-titulo">Minha conta</h2>
          <button class="modal-close" id="btn-fechar-conta" aria-label="Fechar">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="modal-body">

          <!-- Seção 1: Dados pessoais -->
          <div class="modal-secao">
            <h3>Dados pessoais</h3>
            <form class="modal-form" id="form-dados" novalidate>
              <div class="form-group">
                <label class="form-label" for="input-nome">Nome</label>
                <input class="form-input" type="text" id="input-nome" autocomplete="name" maxlength="100" required />
              </div>
              <div class="form-group">
                <label class="form-label" for="input-email">E-mail</label>
                <input class="form-input" type="email" id="input-email" autocomplete="email" required />
              </div>
              <div id="erro-dados" class="modal-erro hidden"></div>
              <div class="modal-form-actions">
                <button type="submit" class="btn btn-primary" id="btn-salvar-dados">Salvar dados</button>
              </div>
            </form>
          </div>

          <hr class="modal-divider" />

          <!-- Seção 2: Alterar senha -->
          <div class="modal-secao">
            <h3>Alterar senha</h3>
            <form class="modal-form" id="form-senha" novalidate>
              <div class="form-group">
                <label class="form-label" for="input-senha-atual">Senha atual</label>
                <div class="input-senha-wrapper">
                  <input class="form-input" type="password" id="input-senha-atual" autocomplete="current-password" required />
                  <button type="button" class="btn-toggle-senha" aria-label="Mostrar senha" data-alvo="input-senha-atual">${_svgOlhoAberto()}</button>
                </div>
              </div>
              <div class="form-group">
                <label class="form-label" for="input-senha-nova">Nova senha</label>
                <div class="input-senha-wrapper">
                  <input class="form-input" type="password" id="input-senha-nova" autocomplete="new-password" minlength="8" required />
                  <button type="button" class="btn-toggle-senha" aria-label="Mostrar senha" data-alvo="input-senha-nova">${_svgOlhoAberto()}</button>
                </div>
              </div>
              <div class="form-group">
                <label class="form-label" for="input-senha-confirmar">Confirmar nova senha</label>
                <div class="input-senha-wrapper">
                  <input class="form-input" type="password" id="input-senha-confirmar" autocomplete="new-password" minlength="8" required />
                  <button type="button" class="btn-toggle-senha" aria-label="Mostrar senha" data-alvo="input-senha-confirmar">${_svgOlhoAberto()}</button>
                </div>
              </div>
              <div id="erro-senha" class="modal-erro hidden"></div>
              <div class="modal-form-actions">
                <button type="submit" class="btn btn-primary" id="btn-salvar-senha">Alterar senha</button>
              </div>
            </form>
          </div>

        </div>
      </div>
    `

    document.body.appendChild(overlay)
    _modalEl = overlay

    // Fechar
    overlay.querySelector('#btn-fechar-conta').addEventListener('click', _fecharModal)
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) _fecharModal()
    })
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !overlay.classList.contains('hidden')) _fecharModal()
    })

    // Forms
    overlay.querySelector('#form-dados').addEventListener('submit', _submitDados)
    overlay.querySelector('#form-senha').addEventListener('submit', _submitSenha)

    // Toggle de visibilidade de senha (delegado ao form)
    overlay.querySelector('#form-senha').addEventListener('click', (e) => {
      const btn = e.target.closest('.btn-toggle-senha')
      if (!btn) return
      const inputId = btn.getAttribute('data-alvo')
      const input = overlay.querySelector('#' + inputId)
      if (!input) return
      const visivel = input.type === 'text'
      input.type = visivel ? 'password' : 'text'
      btn.innerHTML = visivel ? _svgOlhoAberto() : _svgOlhoFechado()
      btn.setAttribute('aria-label', visivel ? 'Mostrar senha' : 'Ocultar senha')
    })
  }

  async function _abrirModal() {
    if (!_modalEl) return

    _modalEl.classList.remove('hidden')
    document.body.style.overflow = 'hidden'

    // Foca no primeiro campo
    setTimeout(() => {
      _modalEl.querySelector('#input-nome')?.focus()
    }, 50)

    // Carrega dados da API (ou usa cache)
    await _carregarDadosNoModal()
  }

  function _fecharModal() {
    if (!_modalEl) return
    _modalEl.classList.add('hidden')
    document.body.style.overflow = ''
    // Limpa formulários, erros e reseta visibilidade das senhas
    _modalEl.querySelector('#form-dados').reset()
    _modalEl.querySelector('#form-senha').reset()
    _esconderErro('erro-dados')
    _esconderErro('erro-senha')
    _resetarTogglesSenha()
  }

  async function _carregarDadosNoModal() {
    try {
      const me = _dadosUsuario || await api.get('/api/auth/me')
      _dadosUsuario = me

      const inputNome = _modalEl.querySelector('#input-nome')
      const inputEmail = _modalEl.querySelector('#input-email')
      if (inputNome) inputNome.value = me.nome
      if (inputEmail) inputEmail.value = me.email
    } catch (err) {
      _mostrarErro('erro-dados', 'Não foi possível carregar seus dados.')
    }
  }

  // ── Submit: dados pessoais ─────────────────────────────────────────────────

  async function _submitDados(e) {
    e.preventDefault()
    _esconderErro('erro-dados')

    const nome = _modalEl.querySelector('#input-nome').value.trim()
    const email = _modalEl.querySelector('#input-email').value.trim()
    const btn = _modalEl.querySelector('#btn-salvar-dados')

    if (!nome) { _mostrarErro('erro-dados', 'O nome não pode ser vazio.'); return }
    if (!_emailValido(email)) { _mostrarErro('erro-dados', 'E-mail inválido.'); return }

    btn.disabled = true
    btn.textContent = 'Salvando…'

    try {
      const atualizado = await api.put('/api/auth/me', { nome, email })
      _dadosUsuario = atualizado

      // Atualiza localStorage e header
      localStorage.setItem(CONFIG.STORAGE.USUARIO_NOME, atualizado.nome)
      _atualizarHeaderNome(atualizado.nome)

      toast.sucesso('Dados atualizados com sucesso!')
      _fecharModal()
    } catch (err) {
      const msg = err?.message || 'Erro ao salvar dados.'
      _mostrarErro('erro-dados', msg)
    } finally {
      btn.disabled = false
      btn.textContent = 'Salvar dados'
    }
  }

  // ── Submit: alterar senha ──────────────────────────────────────────────────

  async function _submitSenha(e) {
    e.preventDefault()
    _esconderErro('erro-senha')

    const senhaAtual   = _modalEl.querySelector('#input-senha-atual').value
    const senhaNova    = _modalEl.querySelector('#input-senha-nova').value
    const senhaConfirm = _modalEl.querySelector('#input-senha-confirmar').value
    const btn = _modalEl.querySelector('#btn-salvar-senha')

    if (!senhaAtual) { _mostrarErro('erro-senha', 'Informe a senha atual.'); return }
    if (senhaNova.length < 8) { _mostrarErro('erro-senha', 'A nova senha deve ter pelo menos 8 caracteres.'); return }
    if (senhaNova !== senhaConfirm) { _mostrarErro('erro-senha', 'As senhas não conferem.'); return }

    btn.disabled = true
    btn.textContent = 'Salvando…'

    try {
      await api.put('/api/auth/alterar-senha', {
        senha_atual: senhaAtual,
        senha_nova: senhaNova,
        confirmar_senha: senhaConfirm,
      })
      toast.sucesso('Senha alterada com sucesso!')
      _fecharModal()
    } catch (err) {
      const msg = err?.message || 'Erro ao alterar senha.'
      _mostrarErro('erro-senha', msg)
    } finally {
      btn.disabled = false
      btn.textContent = 'Alterar senha'
    }
  }

  // ── Helpers DOM ───────────────────────────────────────────────────────────

  function _mostrarErro(id, msg) {
    const el = _modalEl?.querySelector('#' + id)
    if (!el) return
    el.textContent = msg
    el.classList.remove('hidden')
  }

  function _esconderErro(id) {
    const el = _modalEl?.querySelector('#' + id)
    if (el) el.classList.add('hidden')
  }

  function _resetarTogglesSenha() {
    if (!_modalEl) return
    _modalEl.querySelectorAll('.btn-toggle-senha').forEach((btn) => {
      const inputId = btn.getAttribute('data-alvo')
      const input = _modalEl.querySelector('#' + inputId)
      if (input) input.type = 'password'
      btn.innerHTML = _svgOlhoAberto()
      btn.setAttribute('aria-label', 'Mostrar senha')
    })
  }

  function _atualizarHeaderNome(nome) {
    const elNome = document.getElementById('header-usuario-nome')
    const elAvatar = document.getElementById('header-usuario-avatar')
    if (elNome) elNome.textContent = nome
    if (elAvatar) elAvatar.textContent = _inicial(nome)
  }

  function _emailValido(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  }

  // Ícones de olho para toggle de senha (Heroicons outline)
  function _svgOlhoAberto() {
    return `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
      <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.641 0-8.573-3.007-9.963-7.178Z" />
      <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
    </svg>`
  }

  function _svgOlhoFechado() {
    return `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
      <path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.451 10.451 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.522 10.522 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88" />
    </svg>`
  }

  // Escape HTML simples para uso interno
  function _esc(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
  }
})()
