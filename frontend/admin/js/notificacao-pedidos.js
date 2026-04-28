/* frontend/admin/js/notificacao-pedidos.js
 *
 * Notificação global de novos pedidos pendentes — funciona em qualquer tela do admin.
 * Injeta um modal central chamativo, toca beep-beep por 30s e navega para pedidos.html
 * com highlight do pedido novo.
 *
 * Depende de: config.js, auth.js (api, auth)
 * Adicionar em todas as páginas admin autenticadas.
 */

(function () {
  'use strict'

  const POLL_MS = 5000
  const STORAGE_KEY = 'notif_ids_pendentes_vistos'
  const BEEP_DURACAO_MS = 30000
  const BEEP_INTERVALO_MS = 3000

  let _idsVistos = new Set()
  let _primeiroPoll = true
  let _novos = []
  let _audioCtx = null
  let _beepTimer = null
  let _beepStop = null
  let _modalEl = null
  let _timer = null

  document.addEventListener('DOMContentLoaded', () => {
    if (typeof auth === 'undefined' || !auth.isAutenticado()) return

    _carregarVistos()
    _injetarModal()
    _destravarAudioNaPrimeiraInteracao()
    _poll()
    _timer = setInterval(_poll, POLL_MS)
    _consumirHighlightUrl()
  })

  /* ── Persistência dos IDs vistos (sessionStorage) ───────── */

  function _carregarVistos() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY)
      if (raw) {
        const arr = JSON.parse(raw)
        if (Array.isArray(arr)) {
          _idsVistos = new Set(arr)
          _primeiroPoll = false
        }
      }
    } catch (_) { /* storage indisponível */ }
  }

  function _salvarVistos() {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify([..._idsVistos]))
    } catch (_) { /* silencioso */ }
  }

  /* ── Polling ────────────────────────────────────────────── */

  async function _poll() {
    try {
      const pendentes = await api.get('/api/admin/pedidos?status=pendente')
      if (!Array.isArray(pendentes)) return

      if (_primeiroPoll) {
        pendentes.forEach(p => _idsVistos.add(p.id))
        _primeiroPoll = false
        _salvarVistos()
        return
      }

      const novos = pendentes.filter(p => !_idsVistos.has(p.id))
      if (novos.length > 0) {
        novos.forEach(p => _idsVistos.add(p.id))
        _novos = novos
        _salvarVistos()
        _exibirModal(novos.length, novos[0].id)
        _iniciarBeep()
      }
    } catch (_) { /* falha silenciosa */ }
  }

  /* ── Áudio ──────────────────────────────────────────────── */

  function _getAudioContext() {
    if (!_audioCtx) {
      const AC = window.AudioContext || window.webkitAudioContext
      if (!AC) return null
      _audioCtx = new AC()
    }
    return _audioCtx
  }

  function _destravarAudioNaPrimeiraInteracao() {
    const destravar = () => {
      const ctx = _getAudioContext()
      if (ctx && ctx.state === 'suspended') ctx.resume()
    }
    // Sem { once: true } — o navegador pode re-suspender o AudioContext após
    // inatividade prolongada; precisamos destravá-lo em qualquer interação futura.
    document.addEventListener('click', destravar)
    document.addEventListener('keydown', destravar)
  }

  async function _tocarBeepUnico() {
    try {
      const ctx = _getAudioContext()
      if (!ctx) return
      if (ctx.state === 'suspended') await ctx.resume()

      const tocar = (startTime) => {
        const osc = ctx.createOscillator()
        const gain = ctx.createGain()
        osc.connect(gain)
        gain.connect(ctx.destination)
        osc.frequency.value = 880
        osc.type = 'sine'
        gain.gain.setValueAtTime(0.3, startTime)
        gain.gain.exponentialRampToValueAtTime(0.01, startTime + 0.15)
        osc.start(startTime)
        osc.stop(startTime + 0.15)
      }
      const now = ctx.currentTime
      tocar(now)
      tocar(now + 0.2)
    } catch (_) { /* navegador bloqueou */ }
  }

  function _iniciarBeep() {
    _pararBeep()
    _tocarBeepUnico()
    _beepTimer = setInterval(_tocarBeepUnico, BEEP_INTERVALO_MS)
    _beepStop = setTimeout(_pararBeep, BEEP_DURACAO_MS)
  }

  function _pararBeep() {
    if (_beepTimer) { clearInterval(_beepTimer); _beepTimer = null }
    if (_beepStop)  { clearTimeout(_beepStop);  _beepStop  = null }
  }

  /* ── Modal central de notificação ───────────────────────── */

  function _injetarModal() {
    const overlay = document.createElement('div')
    overlay.id = 'notif-pedido-overlay'
    overlay.className = 'notif-pedido-overlay hidden'
    overlay.innerHTML = `
      <div class="notif-pedido-box" role="alertdialog" aria-modal="true" aria-labelledby="notif-titulo">
        <div class="notif-pedido-icone">🛎️</div>
        <h2 class="notif-pedido-titulo" id="notif-titulo">Novo pedido!</h2>
        <p class="notif-pedido-subtitulo" id="notif-subtitulo">1 pedido pendente</p>
        <div class="notif-pedido-acoes">
          <button class="btn btn-primary notif-btn-ver" id="notif-btn-ver" type="button">
            Ver pedido
          </button>
          <button class="btn btn-secondary notif-btn-dispensar" id="notif-btn-dispensar" type="button">
            Dispensar
          </button>
        </div>
      </div>
    `
    overlay.querySelector('#notif-btn-ver').addEventListener('click', _aoClicarVer)
    overlay.querySelector('#notif-btn-dispensar').addEventListener('click', _dispensarModal)
    document.body.appendChild(overlay)
    _modalEl = overlay
  }

  function _exibirModal(count, primeiroId) {
    if (!_modalEl) return
    const subtitulo = _modalEl.querySelector('#notif-subtitulo')
    const titulo = _modalEl.querySelector('#notif-titulo')
    if (titulo) titulo.textContent = count === 1 ? 'Novo pedido!' : `${count} novos pedidos!`
    if (subtitulo) subtitulo.textContent = count === 1 ? '1 pedido pendente' : `${count} pedidos pendentes`
    _modalEl.dataset.primeiroId = String(primeiroId)
    _modalEl.classList.remove('hidden')
    document.body.style.overflow = 'hidden'
  }

  function _dispensarModal() {
    if (!_modalEl) return
    _modalEl.classList.add('hidden')
    document.body.style.overflow = ''
    _pararBeep()
    _novos = []
    delete _modalEl.dataset.primeiroId
  }

  /* ── ESC dispensa o modal de notificação ─────────────── */

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && _modalEl && !_modalEl.classList.contains('hidden')) {
      _dispensarModal()
    }
  })

  function _aoClicarVer() {
    const id = _modalEl?.dataset?.primeiroId
    _dispensarModal()
    if (!id) return
    if (_naTelaDePedidos()) {
      window.dispatchEvent(new CustomEvent('pedido:highlight', { detail: { id: Number(id) } }))
    } else {
      window.location.href = `pedidos.html?highlight=${id}`
    }
  }

  /* ── Navegação com highlight ────────────────────────────── */

  function _naTelaDePedidos() {
    return /pedidos\.html?$/i.test(window.location.pathname) ||
           window.location.pathname.endsWith('/pedidos')
  }

  function _consumirHighlightUrl() {
    if (!_naTelaDePedidos()) return
    const id = new URLSearchParams(window.location.search).get('highlight')
    if (!id) return
    window.addEventListener('pedidos:renderizados', () => {
      window.dispatchEvent(new CustomEvent('pedido:highlight', { detail: { id: Number(id) } }))
    }, { once: true })
  }
})()
