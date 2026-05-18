/* frontend/admin/js/notificacao-pedidos.js
 *
 * Sistema de notificação de novos pedidos.
 * Combina HTML5 Audio loop (alarme persistente em background) com
 * Server-Sent Events (push em tempo real, zero latência, zero polling throttle).
 *
 * Por que HTML5 Audio e não Web Audio API:
 *   Web Audio API → AudioContext é suspenso pelo Chrome quando a aba perde foco.
 *   HTML5 <audio> com loop=true → tratado como mídia (igual ao YouTube/Spotify),
 *   NÃO é throttled em background. Funciona com browser minimizado ou em outra aba.
 *
 * Por que SSE e não setInterval:
 *   setInterval é throttled para ~1/min em abas background (Chrome 86+).
 *   EventSource é uma conexão TCP persistente — o callback dispara imediatamente
 *   ao receber o evento, independente do estado de visibilidade da aba.
 *
 * Autoplay policy (browsers modernos):
 *   Browsers bloqueiam audio.play() sem gesto do usuário. Solução em 2 camadas:
 *   1. Pre-warm no login (form submit é gesto válido) → aumenta MEI do Chrome.
 *   2. Unlock no primeiro click/keydown de qualquer página admin → silencioso.
 *   Uma vez destravado, permanece destravado pela vida inteira da página.
 *
 * Depende de: config.js (CONFIG), auth.js (api, auth)
 * Incluir em todas as páginas admin autenticadas.
 */

(function () {
  'use strict'

  /* ── Constantes ─────────────────────────────────────────────── */
  const STORAGE_KEY    = 'notif_ids_pendentes_vistos'
  const ALARME_MAX_MS  = 30_000   // para automaticamente após 30s sem ação
  const SSE_POLL_MS    = 60_000   // polling de backup (caso SSE falhe silenciosamente)

  /* ── Estado ─────────────────────────────────────────────────── */
  let _idsVistos      = new Set()
  let _primeiroPoll   = true
  let _audio          = null        // HTMLAudioElement
  let _audioUnlocked  = false       // autoplay policy desbloqueada
  let _alarmeTimer    = null        // setTimeout para parar alarme em 30s
  let _eventSource    = null        // EventSource SSE
  let _backupTimer    = null        // setInterval de polling de backup
  let _modalInjected  = false       // modal já injetado no DOM

  /* ══════════════════════════════════════════════════════════════
     ÁUDIO — MP3 externo
     frontend/admin/audio/notificacao-pedido.mp3  (~2s por loop)
     Toca em loop por ALARME_MAX_MS (30s ≈ 15 repetições).
  ══════════════════════════════════════════════════════════════ */

  /* ── Inicializar o elemento de áudio (uma vez) ──────────────── */
  function _inicializarAudio() {
    if (_audio) return

    // Resolve o caminho relativo à página atual, não ao script.
    // Funciona tanto em desenvolvimento (python -m http.server) quanto em
    // produção (Nginx serve /admin/ com try_files).
    _audio         = new Audio(new URL('audio/notificacao-pedido.mp3', location.href).href)
    _audio.loop    = true
    _audio.volume  = 0.6
    _audio.preload = 'auto'
  }

  /* ── Unlock de autoplay (transparente, sem UI) ──────────────── */
  function _tentarUnlock() {
    if (_audioUnlocked || !_audio) return

    _audio.muted = true
    _audio.play()
      .then(() => {
        _audio.pause()
        _audio.currentTime = 0
        _audio.muted = false
        _audioUnlocked = true
        // Remove listeners — não precisa mais tentar
        document.removeEventListener('click',   _tentarUnlock)
        document.removeEventListener('keydown', _tentarUnlock)
      })
      .catch(() => {
        // Ainda não autorizado — tenta no próximo gesto
        _audio.muted = false
      })
  }

  /* ── Alarme ──────────────────────────────────────────────────── */
  function _iniciarAlarme() {
    if (!_audio) return

    // Para alarme anterior se ainda estava tocando
    _pararAlarme()

    _audio.currentTime = 0
    _audio.play().catch(() => {
      // Autoplay não destravado ainda — silencioso. Modal continua visível.
    })

    // Para automaticamente após 30s
    _alarmeTimer = setTimeout(_pararAlarme, ALARME_MAX_MS)
  }

  function _pararAlarme() {
    if (_alarmeTimer) { clearTimeout(_alarmeTimer); _alarmeTimer = null }
    if (_audio && !_audio.paused) {
      _audio.pause()
      _audio.currentTime = 0
    }
  }

  /* ══════════════════════════════════════════════════════════════
     MODAL POPUP
  ══════════════════════════════════════════════════════════════ */

  function _injetarModal() {
    if (_modalInjected) return
    _modalInjected = true

    const overlay = document.createElement('div')
    overlay.id        = 'notif-pedido-overlay'
    overlay.className = 'notif-pedido-overlay hidden'
    overlay.setAttribute('role', 'alertdialog')
    overlay.setAttribute('aria-modal', 'true')
    overlay.setAttribute('aria-labelledby', 'notif-titulo')
    overlay.innerHTML = `
      <div class="notif-pedido-box">
        <div class="notif-pedido-icone" aria-hidden="true">🛎️</div>
        <h2 id="notif-titulo" class="notif-pedido-titulo">Novo pedido!</h2>
        <p  id="notif-subtitulo" class="notif-pedido-subtitulo"></p>
        <div class="notif-pedido-acoes">
          <button type="button" class="btn btn-primary"   id="notif-btn-ver">Ver pedido</button>
          <button type="button" class="btn btn-secondary" id="notif-btn-dispensar">Dispensar</button>
        </div>
      </div>
    `
    document.body.appendChild(overlay)

    document.getElementById('notif-btn-dispensar').addEventListener('click', _dispensarModal)
    document.getElementById('notif-btn-ver').addEventListener('click', () => {
      _dispensarModal()
      _irParaPedido(_ultimoPedidoId)
    })
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && !overlay.classList.contains('hidden')) {
        _dispensarModal()
      }
    })
  }

  let _ultimoPedidoId = null

  function _exibirModal(count, pedidoId) {
    _ultimoPedidoId = pedidoId
    const overlay   = document.getElementById('notif-pedido-overlay')
    if (!overlay) return

    document.getElementById('notif-titulo').textContent =
      count === 1 ? 'Novo pedido!' : `${count} novos pedidos!`
    document.getElementById('notif-subtitulo').textContent =
      count === 1
        ? 'Um pedido está aguardando sua atenção.'
        : `${count} pedidos estão aguardando sua atenção.`

    overlay.classList.remove('hidden')
  }

  function _dispensarModal() {
    _pararAlarme()
    const overlay = document.getElementById('notif-pedido-overlay')
    overlay?.classList.add('hidden')
  }

  function _irParaPedido(id) {
    if (_naTelaDePedidos()) {
      window.dispatchEvent(new CustomEvent('pedido:highlight', { detail: { id } }))
    } else {
      window.location.href = `pedidos.html?highlight=${id}`
    }
  }

  /* ══════════════════════════════════════════════════════════════
     SSE — EventSource em tempo real
  ══════════════════════════════════════════════════════════════ */

  function _conectarSSE() {
    if (!auth.isAutenticado()) return

    // Precisa de access token em memória para a query string.
    // Se ainda não há token (page reload antes do refresh terminar),
    // aguarda 500ms e tenta novamente — o _tryRefresh() terá concluído.
    const token = auth.getToken()
    if (!token) {
      setTimeout(_conectarSSE, 500)
      return
    }

    // Fecha conexão anterior se houver (ex: token renovado)
    _eventSource?.close()

    _eventSource = new EventSource(
      `${CONFIG.API_URL}/api/admin/pedidos/stream?token=${encodeURIComponent(token)}`
    )

    _eventSource.addEventListener('connected', () => {
      // Ao (re)conectar, faz um poll para buscar pedidos que chegaram
      // durante o período de desconexão (catch-up).
      _poll()
    })

    _eventSource.addEventListener('novo-pedido', (e) => {
      try {
        const pedido = JSON.parse(e.data)
        if (_idsVistos.has(pedido.id)) return   // deduplicação
        _idsVistos.add(pedido.id)
        _salvarVistos()
        _exibirModal(1, pedido.id)
        _iniciarAlarme()
      } catch (_) { /* parse error — descarta */ }
    })

    _eventSource.onerror = () => {
      // EventSource reconecta automaticamente com backoff exponencial (RFC 6202).
      // Não fazemos nada aqui — apenas deixamos o browser gerenciar.
      // O polling de backup garante que pedidos não sejam perdidos durante
      // o período de reconexão.
    }
  }

  /* ══════════════════════════════════════════════════════════════
     POLLING DE BACKUP
     Cobre: falha silenciosa do SSE, período entre desconexão e reconnect,
     abas que ficaram abertas com token expirado e ainda não recarregaram.
  ══════════════════════════════════════════════════════════════ */

  async function _poll() {
    try {
      const pendentes = await api.get('/api/admin/pedidos?status=pendente')
      if (!Array.isArray(pendentes)) return

      if (_primeiroPoll) {
        // Primeiro poll: registra IDs existentes como "vistos" para não disparar
        // notificação de pedidos antigos ao abrir o painel.
        pendentes.forEach(p => _idsVistos.add(p.id))
        _primeiroPoll = false
        _salvarVistos()
        return
      }

      const novos = pendentes.filter(p => !_idsVistos.has(p.id))
      if (novos.length > 0) {
        novos.forEach(p => _idsVistos.add(p.id))
        _salvarVistos()
        _exibirModal(novos.length, novos[0].id)
        _iniciarAlarme()
      }
    } catch (_) { /* falha silenciosa — não interrompe o ciclo */ }
  }

  /* ── Persistência dos IDs vistos (sessionStorage por aba) ──── */
  function _carregarVistos() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY)
      if (raw) {
        const arr = JSON.parse(raw)
        if (Array.isArray(arr)) {
          _idsVistos    = new Set(arr)
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

  /* ── Helpers de navegação ────────────────────────────────────── */
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

  /* ── Inicialização ───────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', () => {
    if (typeof auth === 'undefined' || !auth.isAutenticado()) return

    _inicializarAudio()
    _injetarModal()
    _carregarVistos()
    _consumirHighlightUrl()

    // Unlock de autoplay no primeiro gesto (click ou tecla)
    document.addEventListener('click',   _tentarUnlock)
    document.addEventListener('keydown', _tentarUnlock)

    // Conexão SSE principal
    _conectarSSE()

    // Polling de backup: a cada 60s + ao voltar para a aba
    _backupTimer = setInterval(_poll, SSE_POLL_MS)
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) _poll()
    })

    // Renovação de token (access token dura 15min) — SSE precisa reconectar
    // com o novo token. Observa o evento de refresh disparado por auth.js.
    // Crítica: auth.js não emite evento de refresh hoje — quando a feature de
    // auto-refresh for adicionada, conectar aqui. Por ora, o EventSource
    // reconecta automaticamente e o servidor revalida o token na query string.
  })

})()
