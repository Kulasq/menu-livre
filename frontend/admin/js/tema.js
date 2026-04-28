/* frontend/admin/js/tema.js
 *
 * Gerencia o tema claro/escuro/sistema no painel admin.
 * Aplica o tema ANTES do render (sem flash) e injeta o botão de toggle no header.
 *
 * Depende de: — (nenhum; carrega antes de todos os outros scripts)
 * Incluir em todas as páginas admin autenticadas, antes de conta.js.
 *
 * Preferência salva em localStorage['ml-tema'] = 'light' | 'dark' | 'system'
 * data-theme no <html> sempre recebe o valor resolvido: 'light' | 'dark'
 */

;(function () {
  'use strict'

  var STORAGE_KEY = 'ml-tema'
  var CICLO = ['light', 'dark', 'system']

  var ICONES = {
    light: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" /></svg>',
    dark:  '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z" /></svg>',
    system:'<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0H3" /></svg>'
  }

  var TOOLTIP = { light: 'Tema claro', dark: 'Tema escuro', system: 'Seguir sistema' }

  // ── Aplica tema imediatamente (antes do DOMContentLoaded) ─────────────────

  var _pref = localStorage.getItem(STORAGE_KEY) || 'system'
  if (CICLO.indexOf(_pref) === -1) _pref = 'system'

  function _resolver(pref) {
    if (pref !== 'system') return pref
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }

  document.documentElement.dataset.theme = _resolver(_pref)

  // ── Botão de toggle ───────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', function () {
    _injetarBotao()
    _escutarSistema()
    _escutarStorage()
  })

  function _injetarBotao() {
    var wrapper = document.querySelector('.admin-header-usuario')
    if (!wrapper) return

    var btn = document.createElement('button')
    btn.id = 'btn-tema'
    btn.className = 'btn-tema'
    btn.setAttribute('type', 'button')
    _atualizarBotao(btn, _pref)

    btn.addEventListener('click', function (e) {
      e.stopPropagation()
      var idx = CICLO.indexOf(_pref)
      _pref = CICLO[(idx + 1) % CICLO.length]
      localStorage.setItem(STORAGE_KEY, _pref)
      document.documentElement.dataset.theme = _resolver(_pref)
      _atualizarBotao(btn, _pref)
    })

    var avatar = document.getElementById('header-usuario-avatar')
    if (avatar) {
      wrapper.insertBefore(btn, avatar)
    } else {
      wrapper.appendChild(btn)
    }
  }

  function _atualizarBotao(btn, pref) {
    btn.setAttribute('aria-label', TOOLTIP[pref])
    btn.setAttribute('title', TOOLTIP[pref])
    btn.innerHTML = ICONES[pref]
  }

  function _escutarSistema() {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
      if (_pref === 'system') {
        document.documentElement.dataset.theme = _resolver('system')
      }
    })
  }

  function _escutarStorage() {
    window.addEventListener('storage', function (e) {
      if (e.key !== STORAGE_KEY) return
      _pref = e.newValue || 'system'
      if (CICLO.indexOf(_pref) === -1) _pref = 'system'
      document.documentElement.dataset.theme = _resolver(_pref)
      var btn = document.getElementById('btn-tema')
      if (btn) _atualizarBotao(btn, _pref)
    })
  }
})()
