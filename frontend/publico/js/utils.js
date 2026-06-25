/* frontend/publico/js/utils.js — utilitários compartilhados do cardápio público */

/**
 * Escapa caracteres HTML especiais para evitar XSS ao inserir strings via innerHTML.
 * Usar sempre que interpolar dados vindos da API (nomes, endereços, observações)
 * dentro de template strings. Para texto puro, prefira textContent.
 */
function esc(str) {
  if (!str) return '';
  const el = document.createElement('span');
  el.textContent = str;
  return el.innerHTML;
}

/** Formata um número como moeda brasileira (R$). Aceita number ou string numérica. */
function brl(valor) {
  return Number(valor).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

/** Formata uma data ISO no fuso de Recife (BRT), formato dd/mm/aaaa hh:mm. */
function _formatarData(iso) {
  return new Date(iso).toLocaleString('pt-BR', {
    timeZone: 'America/Recife',
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

/**
 * Aplica máscara de telefone BR (DDD + 8/9 dígitos) a um input enquanto digita.
 * `onInput` (opcional) é chamado após cada formatação, com o próprio input —
 * útil para validação inline (ex.: marcar o campo como inválido).
 */
function _aplicarMascaraTelefone(input, onInput) {
  input.addEventListener('input', () => {
    const d = input.value.replace(/\D/g, '').slice(0, 11);
    if (!d)                  input.value = '';
    else if (d.length <= 2)  input.value = `(${d}`;
    else if (d.length <= 6)  input.value = `(${d.slice(0, 2)}) ${d.slice(2)}`;
    else if (d.length <= 10) input.value = `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
    else                     input.value = `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
    if (typeof onInput === 'function') onInput(input);
  });
}

/**
 * Habilita gesto de arrastar-para-baixo que fecha um modal/drawer no mobile.
 * `handleEl` é a alça que captura o toque, `boxEl` é o container animado e
 * `fecharFn(skipAnim)` é a função de fechamento (recebe true quando já houve
 * animação de saída, para não re-animar).
 */
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
