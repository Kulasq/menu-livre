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
