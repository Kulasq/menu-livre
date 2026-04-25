window.addEventListener('DOMContentLoaded', () => {
  window.carrinho.init();
  window.pedido.init();
  window.cardapio.init();

  // Restaurar itens de "pedir igual" vindos de meus-pedidos.html
  const pedirIgual = sessionStorage.getItem('ml_pedir_igual');
  if (pedirIgual) {
    sessionStorage.removeItem('ml_pedir_igual');
    try {
      const itens = JSON.parse(pedirIgual);
      // Aguarda o cardápio carregar antes de popular o carrinho
      window.addEventListener('cardapio:carregado', () => {
        itens.forEach(item => window.carrinho.adicionarDireto(item));
        window.carrinho.abrirDrawer();
      }, { once: true });
    } catch { /* */ }
  }
});